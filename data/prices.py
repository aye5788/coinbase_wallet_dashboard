import requests
from utils.cache import cache

@cache(ttl=300)
def get_prices(ids):
    r = requests.get(
        "https://api.coingecko.com/api/v3/simple/price",
        params={
            "ids": ",".join(ids),
            "vs_currencies": "usd"
        }
    )
    return r.json()

