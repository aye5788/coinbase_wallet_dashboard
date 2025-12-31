from web3 import Web3
import requests
import streamlit as st
from utils.cache import cache

@cache()
def eth_like_balance(address, rpc_url):
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    return w3.eth.get_balance(address) / 1e18

@cache()
def sol_balance(address):
    url = f"https://rpc.helius.xyz/?api-key={st.secrets['HELIUS_KEY']}"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [address],
    }
    r = requests.post(url, json=payload).json()
    return r["result"]["value"] / 1e9

def get_all_balances():
    return {
        "ethereum": eth_like_balance(
            st.secrets["ETH_ADDRESS"],
            f"https://eth-mainnet.g.alchemy.com/v2/{st.secrets['ALCHEMY_KEY']}"
        ),
        "base": eth_like_balance(
            st.secrets["BASE_ADDRESS"],
            f"https://base-mainnet.g.alchemy.com/v2/{st.secrets['ALCHEMY_KEY']}"
        ),
        "solana": sol_balance(st.secrets["SOL_ADDRESS"]),
    }

