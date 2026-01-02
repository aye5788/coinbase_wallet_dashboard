import streamlit as st
import requests
from web3 import Web3
from utils.cache import cache

# -------------------------
# CONFIG
# -------------------------

# Whitelist: ONLY assets you care about
MAINSTREAM_SYMBOLS = {
    "ETH",
    "SOL",
    "DAI",
    "USDC",
    "SUSDS",
    "KIBBLE",
    "TOSHI",
    "AAVE",
    "UNI",
    "CRV",
}

# Alchemy token balance endpoint
ALCHEMY_TOKEN_URL = "https://eth-mainnet.g.alchemy.com/v2/{key}"
ALCHEMY_BASE_TOKEN_URL = "https://base-mainnet.g.alchemy.com/v2/{key}"

# -------------------------
# HELPERS
# -------------------------

def _add_balance(store, symbol, chain, amount):
    symbol = symbol.upper()
    if symbol not in MAINSTREAM_SYMBOLS:
        return

    if symbol not in store:
        store[symbol] = {"total": 0.0, "chains": {}}

    store[symbol]["total"] += amount
    store[symbol]["chains"][chain] = store[symbol]["chains"].get(chain, 0) + amount


@cache()
def _eth_native(address, rpc_url):
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    return w3.eth.get_balance(address) / 1e18


@cache()
def _sol_native(address):
    url = f"https://rpc.helius.xyz/?api-key={st.secrets['HELIUS_KEY']}"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [address],
    }
    r = requests.post(url, json=payload).json()
    return r["result"]["value"] / 1e9


@cache()
def _erc20_balances(address, chain):
    if chain == "ethereum":
        url = ALCHEMY_TOKEN_URL.format(key=st.secrets["ALCHEMY_KEY"])
    elif chain == "base":
        url = ALCHEMY_BASE_TOKEN_URL.format(key=st.secrets["ALCHEMY_KEY"])
    else:
        return []

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "alchemy_getTokenBalances",
        "params": [address],
    }

    res = requests.post(url, json=payload).json()
    tokens = res.get("result", {}).get("tokenBalances", [])

    results = []

    for t in tokens:
        if t.get("tokenBalance") in ("0x0", None):
            continue

        meta_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "alchemy_getTokenMetadata",
            "params": [t["contractAddress"]],
        }
        meta = requests.post(url, json=meta_payload).json().get("result", {})

        symbol = meta.get("symbol")
        decimals = meta.get("decimals")

        if not symbol or decimals is None:
            continue

        balance = int(t["tokenBalance"], 16) / (10 ** decimals)
        results.append((symbol.upper(), balance))

    return results


# -------------------------
# MAIN ENTRY
# -------------------------

def get_all_balances():
    """
    Returns balances aggregated by ASSET, with per-chain breakdown.

    Example:
    {
      "ETH": {
        "total": 0.0016,
        "chains": {"ethereum": 0.0009, "base": 0.0007}
      },
      "SUSDS": {
        "total": 80.62,
        "chains": {"base": 80.62}
      }
    }
    """

    store = {}

    # ---- Native ETH ----
    eth_addr = st.secrets["ETH_ADDRESS"]
    base_addr = st.secrets["BASE_ADDRESS"]

    eth_balance = _eth_native(
        eth_addr,
        f"https://eth-mainnet.g.alchemy.com/v2/{st.secrets['ALCHEMY_KEY']}",
    )
    _add_balance(store, "ETH", "ethereum", eth_balance)

    base_eth = _eth_native(
        base_addr,
        f"https://base-mainnet.g.alchemy.com/v2/{st.secrets['ALCHEMY_KEY']}",
    )
    _add_balance(store, "ETH", "base", base_eth)

    # ---- Native SOL ----
    sol_balance = _sol_native(st.secrets["SOL_ADDRESS"])
    _add_balance(store, "SOL", "solana", sol_balance)

    # ---- ERC-20s (ETH + Base) ----
    for chain, addr in [("ethereum", eth_addr), ("base", base_addr)]:
        tokens = _erc20_balances(addr, chain)
        for symbol, amount in tokens:
            _add_balance(store, symbol, chain, amount)

    return store

