import argparse
import json
import os
import sys

from .diff import diff, load_snapshot, read_rows, report, save_snapshot
from .push import push


def main(argv=None):
    ap = argparse.ArgumentParser(prog="sheets_sync", description="Compare a new price list with the last one and upload it to a Google Sheet.")
    ap.add_argument("csv", help="the new price list (CSV)")
    ap.add_argument("--key", default="sku")
    ap.add_argument("--watch", default="price,stock", help="comma-separated columns whose changes are reported")
    ap.add_argument("--snapshot", default="snapshot.json")
    ap.add_argument("--report", default="changes.md")
    ap.add_argument("--webhook", help="Apps Script web app URL; the secret is read from SHEETS_SYNC_SECRET")
    ap.add_argument("--sheet", default="prices")
    args = ap.parse_args(argv)
    new = read_rows(args.csv, args.key)
    old = load_snapshot(args.snapshot)
    d = diff(old, new, args.key, tuple(args.watch.split(","))) if old is not None else None
    if d:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(report(d, args.key))
    if args.webhook:
        secret = os.environ.get("SHEETS_SYNC_SECRET", "")
        if not secret:
            raise ValueError("set SHEETS_SYNC_SECRET")
        print("uploaded rows:", push(args.webhook, secret, new, args.sheet))
    save_snapshot(args.snapshot, new)  # only after a successful upload
    print(json.dumps({"first_run": old is None, **({k: len(v) for k, v in d.items()} if d else {})}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
