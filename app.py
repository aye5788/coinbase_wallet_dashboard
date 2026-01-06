import streamlit as st
import pandas as pd

from data.balances import get_all_balances
from data.coinbase import get_coinbase_balances
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
st.title("📊 Private Portfolio Dashboard")


# =====================================================
# WALLET SECTION
# =====================================================

wallet_balances = get_all_balances()


# --------------------
# Determine required prices (wallet only)
# --------------------
price_ids = set()

for asset in wallet_balances:
    if asset == "ETH":
        price_ids.add("ethereum")
    elif asset == "SOL":
        price_ids.add("solana")
    else:
        price_ids.add(asset.lower())

prices = get_prices(list(price_ids))


# --------------------
# Snapshot handling (wallet only)
# --------------------
if should_write_snapshot():
    write_snapshot(wallet_balances, prices)

snapshots = read_snapshots()


# --------------------
# Compute wallet values
# --------------------
wallet_values = {}
wallet_total_usd = 0.0

for asset, info in wallet_balances.items():
    total = info["total"]

    if asset == "ETH":
        price = prices["ethereum"]["usd"]
    elif asset == "SOL":
        price = prices["solana"]["usd"]
    else:
        price = prices.get(asset.lower(), {}).get("usd", 0)

    value = total * price
    wallet_values[asset] = value
    wallet_total_usd += value


# --------------------
# Wallet P/L
# --------------------
asset_pl = compute_asset_pl(snapshots, wallet_values)

pl_since_start = sum(v["since_start"] for v in asset_pl.values()) if asset_pl else 0.0
pl_since_last = sum(v["since_last"] for v in asset_pl.values()) if asset_pl else 0.0

start_base = wallet_total_usd - pl_since_start
pl_start_pct = (pl_since_start / start_base * 100) if start_base > 0 else 0.0


# --------------------
# Wallet top metrics
# --------------------
st.subheader("🧾 On-Chain Wallets")

c1, c2, c3 = st.columns(3)
c1.metric("Wallet Value", usd(wallet_total_usd))
c2.metric("P/L Since Start", usd(pl_since_start), f"{pl_start_pct:.2f}%")
c3.metric("P/L Since Last Snapshot", usd(pl_since_last))


# --------------------
# Wallet equity curve
# --------------------
if snapshots:
    df_snap = pd.DataFrame(snapshots)
    df_snap["usd_value"] = pd.to_numeric(df_snap["usd_value"], errors="coerce")
    df_snap = df_snap.dropna(subset=["usd_value"])

    equity = (
        df_snap.groupby("timestamp")["usd_value"]
        .sum()
        .reset_index()
        .sort_values("timestamp")
    )

    st.line_chart(equity.set_index("timestamp")["usd_value"], height=300)


# --------------------
# Wallet holdings table
# --------------------
rows = []

for asset, info in wallet_balances.items():
    pl_start = asset_pl.get(asset, {}).get("since_start", 0.0)
    pl_recent = asset_pl.get(asset, {}).get("since_last", 0.0)

    base_val = wallet_values[asset] - pl_start
    pl_pct = (pl_start / base_val * 100) if base_val > 0 else 0.0

    recent_pct = (
        pl_recent / (wallet_values[asset] - pl_recent) * 100
        if wallet_values[asset] - pl_recent > 0
        else 0.0
    )

    rows.append({
        "Asset": asset,
        "Balance": round(info["total"], 6),
        "USD Value": wallet_values[asset],
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

st.dataframe(
    df.style.format({
        "USD Value": usd,
        "P/L $ (Start)": usd,
        "P/L $ (Recent)": usd,
        "P/L % (Start)": "{:.2f}%",
        "P/L % (Recent)": "{:.2f}%",
    }),
    width="stretch",
)


# =====================================================
# COINBASE SECTION (SEPARATE, PRICED CORRECTLY)
# =====================================================

st.divider()
st.subheader("🏦 Coinbase Exchange (Custodial)")


# Coinbase symbol → CoinGecko ID map
COINBASE_PRICE_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "CBETH": "coinbase-wrapped-staked-eth",
    "SOL": "solana",
    "ATOM": "cosmos",
    "USDC": "usd-coin",
    "DAI": "dai",
    "PAXG": "pax-gold",
    "POL": "polygon",
}


try:
    cb_balances = get_coinbase_balances()
except Exception as e:
    st.error(f"Coinbase error: {e}")
    cb_balances = {}


if cb_balances:
    cb_price_ids = [
        COINBASE_PRICE_MAP[s]
        for s in cb_balances
        if s in COINBASE_PRICE_MAP
    ]

    cb_prices = get_prices(cb_price_ids)

    cb_rows = []
    cb_total = 0.0

    for symbol, amount in cb_balances.items():
        gecko_id = COINBASE_PRICE_MAP.get(symbol)
        price = cb_prices.get(gecko_id, {}).get("usd", 0.0) if gecko_id else 0.0
        usd_val = amount * price

        cb_total += usd_val

        cb_rows.append({
            "Asset": symbol,
            "Balance": amount,
            "USD Value": usd_val,
        })

    st.metric("Coinbase Value", usd(cb_total))
    st.dataframe(
        pd.DataFrame(cb_rows).style.format({
            "USD Value": usd,
        }),
        width="stretch",
    )
else:
    st.write("No Coinbase balances found.")


