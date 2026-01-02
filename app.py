import streamlit as st

from data.balances import get_all_balances
from data.prices import get_prices
from data.snapshots import (
    should_write_snapshot,
    write_snapshot,
    read_snapshots,
    compute_asset_pl,
)
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
# Snapshot handling (delegated)
# --------------------
if should_write_snapshot():
    write_snapshot(balances, prices)

snapshots = read_snapshots()


# --------------------
# Compute current values
# --------------------
current_values = {}
total_usd = 0.0

for asset, info in balances.items():
    total = info["total"]

    if asset == "ETH":
        price = prices["ethereum"]["usd"]
    elif asset == "SOL":
        price = prices["solana"]["usd"]
    else:
        price = prices.get(asset.lower(), {}).get("usd", 0)

    value = total * price
    current_values[asset] = value
    total_usd += value


# --------------------
# Compute P/L (per-asset + account)
# --------------------
asset_pl = compute_asset_pl(snapshots, current_values)

pl_since_start = sum(v["since_start"] for v in asset_pl.values()) if asset_pl else 0.0
pl_since_last = sum(v["since_last"] for v in asset_pl.values()) if asset_pl else 0.0


# --------------------
# Build holdings table
# --------------------
rows = []

for asset, info in balances.items():
    pl_start = asset_pl.get(asset, {}).get("since_start", 0.0)
    pl_last = asset_pl.get(asset, {}).get("since_last", 0.0)

    rows.append({
        "Asset": asset,
        "Balance": round(info["total"], 6),
        "USD Value": usd(current_values[asset]),
        "P/L (Start)": usd(pl_start),
        "P/L (Recent)": usd(pl_last),
        "Networks": " • ".join(
            f"{chain}: {round(amount, 6)}"
            for chain, amount in info["chains"].items()
        ),
    })


# --------------------
# Display
# --------------------
c1, c2, c3 = st.columns(3)

c1.metric("Total Portfolio Value", usd(total_usd))
c2.metric("P/L Since Start", usd(pl_since_start))
c3.metric("P/L Since Last Snapshot", usd(pl_since_last))

st.subheader("Holdings")
st.dataframe(rows, width="stretch")
