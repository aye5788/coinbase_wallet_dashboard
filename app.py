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
            last_line = list(csv.reader(f))[-1]
            last_ts = datetime.fromisoformat(last_line[0])
            now = datetime.now(timezone.utc)

            elapsed = (now - last_ts).total_seconds()
            return elapsed >= SNAPSHOT_INTERVAL_SECONDS
    except Exception:
        # If anything goes wrong, fail safe and write
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
# Compute totals (ASSET AGGREGATED)
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
st.metric("Total Portfolio Value", usd(total_usd))
st.subheader("Holdings")
st.dataframe(rows, width="stretch")
