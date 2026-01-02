import streamlit as st
from datetime import datetime, timezone
import csv
import os

from data.balances import get_all_balances
from data.prices import get_prices
from utils.formatting import usd


# --------------------
# Page config
# --------------------
st.set_page_config(page_title="Wallet Dashboard", layout="wide")
st.title("📊 Private Wallet Dashboard")


# --------------------
# Load balances
# --------------------
balances = get_all_balances()


# --------------------
# Determine required prices
# --------------------
price_ids = set()

for asset in balances:
    if asset == "ETH":
        price_ids.add("ethereum")
    elif asset == "SOL":
        price_ids.add("solana")
    else:
        price_ids.add(asset.lower())

prices = get_prices(list(price_ids))


# --------------------
# Snapshot logic (2-hour gating)
# --------------------
SNAPSHOT_FILE = "data/snapshots.csv"
SNAPSHOT_INTERVAL_SECONDS = 2 * 60 * 60  # 2 hours

os.makedirs("data", exist_ok=True)

def should_write_snapshot():
    if not os.path.exists(SNAPSHOT_FILE):
        return True

    try:
        with open(SNAPSHOT_FILE, "r") as f:
            rows = list(csv.reader(f))
            if len(rows) < 2:
                return True

            last_ts = datetime.fromisoformat(rows[-1][0])
            now = datetime.now(timezone.utc)
            return (now - last_ts).total_seconds() >= SNAPSHOT_INTERVAL_SECONDS
    except Exception:
        return True


if should_write_snapshot():
    file_exists = os.path.exists(SNAPSHOT_FILE)

    with open(SNAPSHOT_FILE, "a", newline="") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(["timestamp", "asset", "balance", "usd_value"])

        ts = datetime.now(timezone.utc).isoformat()

        for asset, info in balances.items():
            total = info["total"]

            if asset == "ETH":
                price = prices["ethereum"]["usd"]
            elif asset == "SOL":
                price = prices["solana"]["usd"]
            else:
                price = prices.get(asset.lower(), {}).get("usd", 0)

            usd_value = total * price
            writer.writerow([ts, asset, total, usd_value])


# --------------------
# Read snapshots + compute P/L
# --------------------
pl_since_start = 0.0
pl_since_last = 0.0

snapshots = []

if os.path.exists(SNAPSHOT_FILE):
    with open(SNAPSHOT_FILE, "r") as f:
        reader = csv.DictReader(f)
        snapshots = list(reader)

if snapshots:
    # Group snapshots by timestamp
    by_ts = {}
    for row in snapshots:
        ts = row["timestamp"]
        by_ts.setdefault(ts, 0.0)
        by_ts[ts] += float(row["usd_value"])

    timestamps = sorted(by_ts.keys())

    first_value = by_ts[timestamps[0]]
    last_snapshot_value = by_ts[timestamps[-1]]

    current_value = 0.0
    for asset, info in balances.items():
        total = info["total"]

        if asset == "ETH":
            price = prices["ethereum"]["usd"]
        elif asset == "SOL":
            price = prices["solana"]["usd"]
        else:
            price = prices.get(asset.lower(), {}).get("usd", 0)

        current_value += total * price

    pl_since_start = current_value - first_value
    pl_since_last = current_value - last_snapshot_value


# --------------------
# Compute current totals (ASSET AGGREGATED)
# --------------------
rows = []
total_usd = 0

for asset, info in balances.items():
    total = info["total"]

    if asset == "ETH":
        price = prices["ethereum"]["usd"]
    elif asset == "SOL":
        price = prices["solana"]["usd"]
    else:
        price = prices.get(asset.lower(), {}).get("usd", 0)

    value = total * price
    total_usd += value

    rows.append({
        "Asset": asset,
        "Balance": round(total, 6),
        "USD Value": usd(value),
        "Networks": " • ".join(
            f"{chain}: {round(amount, 6)}"
            for chain, amount in info["chains"].items()
        ),
    })


# --------------------
# Display
# --------------------
col1, col2, col3 = st.columns(3)

col1.metric("Total Portfolio Value", usd(total_usd))

if snapshots:
    col2.metric(
        "P/L Since Start",
        usd(pl_since_start),
        delta=f"{(pl_since_start / (total_usd - pl_since_start) * 100):.2f}%" if total_usd != pl_since_start else None,
    )

    col3.metric(
        "P/L Since Last Snapshot",
        usd(pl_since_last),
    )
else:
    col2.metric("P/L Since Start", "—")
    col3.metric("P/L Since Last Snapshot", "—")

st.subheader("Holdings")
st.dataframe(rows, width="stretch")
