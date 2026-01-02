import csv
import os
from datetime import datetime, timezone

SNAPSHOT_FILE = "data/snapshots.csv"

def write_snapshot(balances, prices):
    os.makedirs("data", exist_ok=True)

    file_exists = os.path.exists(SNAPSHOT_FILE)

    with open(SNAPSHOT_FILE, "a", newline="") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(["timestamp", "asset", "balance", "usd_value"])

        ts = datetime.now(timezone.utc).isoformat()

        for asset, info in balances.items():
            total = info["total"]

            if asset == "ETH":
                price = prices["ethereum"]["usd"]
            elif asset == "SOL":
                price = prices["solana"]["usd"]
            else:
                price = prices.get(asset.lower(), {}).get("usd", 0)

            usd_value = total * price

            writer.writerow([ts, asset, total, usd_value])
