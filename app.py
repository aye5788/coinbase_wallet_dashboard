import streamlit as st
from data.balances import get_all_balances
from data.prices import get_prices
from utils.chains import CHAINS
from utils.formatting import usd



st.set_page_config(page_title="Wallet Dashboard", layout="wide")
st.title("📊 Private Wallet Dashboard")

# --------------------
# Load data
# --------------------
balances = get_all_balances()

rows = []
total_usd = 0

price_ids = set()
for asset in balances:
    if asset == "ETH":
        price_ids.add("ethereum")
    elif asset == "SOL":
        price_ids.add("solana")
    else:
        price_ids.add(asset.lower())

prices = get_prices(list(price_ids))

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
        "USD Value": f"${value:,.2f}",
        "Networks": ", ".join(info["chains"].keys()),
    })


# --------------------
# Build price list
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
