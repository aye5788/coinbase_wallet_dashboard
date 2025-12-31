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

price_ids = list({
    CHAINS[c]["coingecko_id"] for c in balances
})
prices = get_prices(price_ids)

# --------------------
# Compute totals
# --------------------
rows = []
total_usd = 0

for chain, amount in balances.items():
    cg_id = CHAINS[chain]["coingecko_id"]
    price = prices[cg_id]["usd"]
    value = amount * price
    total_usd += value

    rows.append({
        "Chain": chain.title(),
        "Balance": round(amount, 4),
        "Price": usd(price),
        "Value": usd(value),
    })

# --------------------
# Display
# --------------------
st.metric("Total Portfolio Value", usd(total_usd))

st.subheader("Holdings")
st.dataframe(rows, use_container_width=True)

