import time
import json
import secrets
import base64
import requests

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.hashes import SHA256

import streamlit as st


COINBASE_API_BASE = "https://api.coinbase.com"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _load_private_key():
    pem = st.secrets["COINBASE_PRIVATE_KEY"]
    return serialization.load_pem_private_key(
        pem.encode(),
        password=None,
    )


def _build_jwt(method: str, path: str) -> str:
    """
    Build ES256 JWT for Coinbase Advanced API
    """

    key_id = st.secrets["COINBASE_KEY_ID"]
    private_key = _load_private_key()

    header = {
        "alg": "ES256",
        "kid": key_id,
        "nonce": secrets.token_hex(16),
    }

    payload = {
        "iss": "cdp",
        "sub": key_id,
        "aud": ["api.coinbase.com"],
        "iat": int(time.time()),
        "exp": int(time.time()) + 120,
        "uri": f"{method} api.coinbase.com{path}",
    }

    header_b64 = _b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":")).encode())

    signing_input = f"{header_b64}.{payload_b64}".encode()

    signature_der = private_key.sign(
        signing_input,
        ec.ECDSA(SHA256())
    )

    r, s = decode_dss_signature(signature_der)
    r_bytes = r.to_bytes(32, "big")
    s_bytes = s.to_bytes(32, "big")
    signature_raw = r_bytes + s_bytes

    signature_b64 = _b64url(signature_raw)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def get_coinbase_balances() -> dict[str, float]:
    """
    Returns raw Coinbase balances by asset symbol.
    Example:
        {"BTC": 0.01, "ETH": 1.2, "USD": 350.0}
    """

    path = "/v2/accounts"
    jwt = _build_jwt("GET", path)

    headers = {
        "Authorization": f"Bearer {jwt}",
        "Content-Type": "application/json",
    }

    balances: dict[str, float] = {}
    url = f"{COINBASE_API_BASE}{path}"

    while url:
        resp = requests.get(url, headers=headers, timeout=30)

        if resp.status_code != 200:
            raise RuntimeError(
                f"Coinbase API error {resp.status_code}: {resp.text}"
            )

        data = resp.json()

        for acct in data.get("data", []):
            bal = acct.get("balance", {})
            amount = float(bal.get("amount", 0))
            symbol = bal.get("currency")

            if amount != 0 and symbol:
                balances[symbol] = balances.get(symbol, 0) + amount

        pagination = data.get("pagination", {})
        next_uri = pagination.get("next_uri")

        if next_uri:
            url = f"{COINBASE_API_BASE}{next_uri}"
        else:
            url = None

    return balances

