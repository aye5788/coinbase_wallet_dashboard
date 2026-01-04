import csv
import os
from datetime import datetime, timezone

SNAPSHOT_FILE = "data/snapshots.csv"
SNAPSHOT_INTERVAL_SECONDS = 2 * 60 * 60  # 2 hours


def should_write_snapshot():
    if not os.path.exists(SNAPSHOT_FILE):
        return True

    try:
        with open(SNAPSHOT_FILE, "r") as f:
            rows = list(csv.reader(f))
            if len(rows) < 2:
                return True

            last_ts = datetime.fromisoformat(rows[-1][0])
            now = datetime.now(timezone.utc)
            return (now - last_ts).total_seconds() >= SNAPSHOT_INTERVAL_SECONDS
    except Exception:
        return True


def write_snapshot(balances, prices):
    os.makedirs("data", exist_ok=True)
    file_exists = os.path.exists(SNAPSHOT_FILE)

    ts = datetime.now(timezone.utc).isoformat()

    with open(SNAPSHOT_FILE, "a", newline="") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(["timestamp", "asset", "balance", "usd_value"])

        for asset, info in balances.items():
            total = info["total"]

            if asset == "ETH":
                price = prices["ethereum"]["usd"]
            elif asset == "SOL":
                price = prices["solana"]["usd"]
            else:
                price = prices.get(asset.lower(), {}).get("usd", 0)

            writer.writerow([ts, asset, total, total * price])


def read_snapshots():
    if not os.path.exists(SNAPSHOT_FILE):
        return []

    with open(SNAPSHOT_FILE, "r") as f:
        return list(csv.DictReader(f))


def compute_asset_pl(snapshots, current_values):
    if not snapshots:
        return {}

    by_ts = {}

    for row in snapshots:
        # Skip malformed or header rows
        try:
            ts = row["timestamp"]
            asset = row["asset"]
            val = float(row["usd_value"])
        except (ValueError, TypeError, KeyError):
            continue

        by_ts.setdefault(ts, {})
        by_ts[ts][asset] = val

    if not by_ts:
        return {}

    timestamps = sorted(by_ts.keys())
    first = by_ts[timestamps[0]]
    last = by_ts[timestamps[-1]]

    pl = {}

    for asset, current_val in current_values.items():
        start_val = first.get(asset, 0.0)
        last_val = last.get(asset, 0.0)

        pl[asset] = {
            "since_start": current_val - start_val,
            "since_last": current_val - last_val,
        }

    return pl


