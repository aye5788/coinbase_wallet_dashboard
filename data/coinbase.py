import time
import json
import requests
import streamlit as st

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.asymmetric.utils import (
    encode_dss_signature
)

import base64
import hashlib


BASE_URL = "https://api.coinbase.com"


# --------------------
# Load private key
# --------------------
def _load_private_key():
    pem = st.secrets["COINBASE_PRIVATE_KEY"].encode()
    return serialization.load_pem_private_key(
        pem,
        password=None,
    )


# --------------------
# Build JWT
# --------------------
def _build_jwt(method: str, path: str):
    key_id = st.secrets["COINBASE_KEY_ID"]
    private_key = _load_private_key()

    header = {
        "alg": "ES256",
        "typ": "JWT",
        "kid": key_id,
    }

    now = int(time.time())
    payload = {
        "iss": "coinbase",
        "sub": key_id,
        "nbf": now,
        "exp": now + 120,
        "uri": f"{method} {path}",
    }

    def b64url(data: bytes) -> bytes:
        return base64.urlsafe_b64encode(data).rstrip(b"=")

    header_b64 = b64url(json.dumps(header).encode())
    payload_b64 = b64url(json.dumps(payload).encode())

    message = header_b64 + b"." + payload_b64

    signature = private_key.sign(
        message,
        ec.ECDSA(SHA256())
    )

    r, s = decode_signature(signature)
    sig_bytes = r + s
    sig_b64 = b64url(sig_bytes)

    return (message + b"." + sig_b64).decode()


def decode_signature(signature: bytes):
    r, s = ec.utils.decode_dss_signature(signature)
    r_bytes = r.to_bytes(32, byteorder="big")
    s_bytes = s.to_bytes(32, byteorder="big")
    return r_bytes, s_bytes


# --------------------
# Public API
# --------------------
def get_coinbase_balances():
    """
    Returns:
      {
        "BTC": usd_value,
        "ETH": usd_value,
        "USD": usd_value,
        ...
      }
    """
    path = "/v2/accounts"
    jwt = _build_jwt("GET", path)

    headers = {
        "Authorization": f"Bearer {jwt}",
        "Content-Type": "application/json",
    }

    resp = requests.get(BASE_URL + path, headers=headers)
    resp.raise_for_status()

    data = resp.json()["data"]

    balances = {}

    for acct in data:
        amount = float(acct["balance"]["amount"])
        if amount == 0:
            continue

        currency = acct["currency"]["code"]
        usd_val = float(acct["balance"]["usd"])

        balances[currency] = usd_val

    return balances
