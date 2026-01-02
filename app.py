import streamlit as st
import pandas as pd

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
# Snapshot handling
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
# Compute P/L
# --------------------
asset_pl = compute_asset_pl(snapshots, current_values)

pl_since_start = sum(v["since_start"] for v in asset_pl.values()) if asset_pl else 0.0
pl_since_last = sum(v["since_last"] for v in asset_pl.values()) if asset_pl else 0.0

start_base = total_usd - pl_since_start
pl_start_pct = (pl_since_start / start_base * 100) if start_base > 0 else 0.0


# --------------------
# Display top metrics
# --------------------
c1, c2, c3 = st.columns(3)

c1.metric("Total Portfolio Value", usd(total_usd))
c2.metric("P/L Since Start", usd(pl_since_start), f"{pl_start_pct:.2f}%")
c3.metric("P/L Since Last Snapshot", usd(pl_since_last))


# --------------------
# Equity curve
# --------------------
if snapshots:
    df_snap = pd.DataFrame(snapshots)
    df_snap["usd_value"] = df_snap["usd_value"].astype(float)

    equity = (
        df_snap.groupby("timestamp")["usd_value"]
        .sum()
        .reset_index()
        .sort_values("timestamp")
    )

    st.subheader("📈 Portfolio Equity Curve")
    st.line_chart(
        equity.set_index("timestamp")["usd_value"],
        height=300,
    )


# --------------------
# Build holdings table
# --------------------
rows = []

for asset, info in balances.items():
    pl_start = asset_pl.get(asset, {}).get("since_start", 0.0)
    pl_recent = asset_pl.get(asset, {}).get("since_last", 0.0)

    base_val = current_values[asset] - pl_start
    pl_pct = (pl_start / base_val * 100) if base_val > 0 else 0.0

    recent_pct = (
        pl_recent / (current_values[asset] - pl_recent) * 100
        if current_values[asset] - pl_recent > 0
        else 0.0
    )

    rows.append({
        "Asset": asset,
        "Balance": round(info["total"], 6),
        "USD Value": current_values[asset],
        "P/L $ (Start)": pl_start,
        "P/L % (Start)": pl_pct,
        "P/L $ (Recent)": pl_recent,
        "P/L % (Recent)": recent_pct,
        "Networks": " • ".join(
            f"{chain}: {round(amount, 6)}"
            for chain, amount in info["chains"].items()
        ),
    })

df = pd.DataFrame(rows)


# --------------------
# Formatting + color
# --------------------
def color_pl(val):
    if val > 0:
        return "color: green"
    if val < 0:
        return "color: red"
    return "color: gray"


styled = df.style.format({
    "USD Value": usd,
    "P/L $ (Start)": usd,
    "P/L $ (Recent)": usd,
    "P/L % (Start)": "{:.2f}%",
    "P/L % (Recent)": "{:.2f}%",
}).applymap(
    color_pl,
    subset=["P/L $ (Start)", "P/L $ (Recent)", "P/L % (Start)", "P/L % (Recent)"]
)

st.subheader("Holdings")
st.dataframe(styled, width="stretch")


# --------------------
# Snapshot inspector
# --------------------
with st.expander("🧪 Snapshot Inspector (Debug)"):
    if snapshots:
        st.dataframe(df_snap, width="stretch")
    else:
        st.write("No snapshots yet.")
with st.expander("🧪 Snapshot Inspector (Debug)"):
    ...
from data.coinbase import get_coinbase_balances

st.markdown("---")
st.markdown("### Coinbase connection test (temporary)")

try:
    cb_balances = get_coinbase_balances()
    st.write(cb_balances)
except Exception as e:
    st.error(str(e))


