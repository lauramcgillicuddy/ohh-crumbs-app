"""Standalone first-run Square sync + audit (no Streamlit needed).

Pulls a date range of real Square data into a local SQLite DB and prints the
live profitability audit — a direct cross-check against the CSV audit.

Credentials are read from the environment or .streamlit/secrets.toml; this
script never asks for or echoes your token.

    # PowerShell — set creds for this shell, then run:
    $env:SQUARE_ACCESS_TOKEN = "<your production token>"
    $env:SQUARE_LOCATION_ID  = "<your location id>"
    python sync_cli.py --days 365

Options: --days N | --from YYYY-MM-DD --to YYYY-MM-DD | --db <url> | --window-days N
"""
import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # so £ prints on Windows
except Exception:
    pass


def load_credentials():
    token = os.getenv("SQUARE_ACCESS_TOKEN")
    location = os.getenv("SQUARE_LOCATION_ID")
    environment = os.getenv("SQUARE_ENVIRONMENT", "production")
    if token and location:
        return token, location, environment
    # Fall back to .streamlit/secrets.toml [square]
    secrets = Path(__file__).with_name(".streamlit") / "secrets.toml"
    if secrets.exists():
        try:
            import tomllib
            data = tomllib.loads(secrets.read_text(encoding="utf-8"))
            sq = data.get("square", {})
            token = token or sq.get("ACCESS_TOKEN")
            location = location or sq.get("LOCATION_ID")
            environment = sq.get("ENVIRONMENT", environment)
        except Exception as e:
            print(f"(couldn't read .streamlit/secrets.toml: {e})")
    return token, location, environment


def make_engine(db_url):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def print_audit(session, audit_core):
    res = audit_core.compute_audit_live_from_db(session)
    k = res["kpis"]
    print("=== Live profitability audit ===")
    print(f"  Net sales          £{k['net_sales']:,.2f}")
    print(f"  Transactions        {k['transactions']:,}")
    print(f"  Avg sale           £{k['avg_sale']:,.2f}")
    print(f"  Discounts          £{k['discounts_total']:,.2f}  ({k['discount_rate_pct']:.1f}% of gross)")
    print(f"  Square fees        £{k['fees_total']:,.2f}  ({k['fee_rate_pct']:.1f}% of collected)")
    print(f"  Card / Cash         {k['card_pct']:.1f}% / {k['cash_pct']:.1f}%")
    print(f"  Take-home          £{k['take_home']:,.2f}")

    if not res["discounts"].empty:
        print("\n  Discount leakage (top):")
        for _, r in res["discounts"].head(8).iterrows():
            print(f"    {r['name']:<22} £{r['amount']:>9,.2f}  "
                  f"({r['pct_of_discounts']:.0f}%, £{r['avg_per_use']:.2f}/use)")

    top = res.get("top_items")
    if top is not None and not top.empty:
        print("\n  Top items by net revenue:")
        for _, r in top.head(8).iterrows():
            print(f"    {r['name']:<24} {r['units']:>6.0f} units   £{r['net']:>9,.2f} net")

    print("\nDone. Cross-check these against the CSV audit — they should line up.")


def main():
    ap = argparse.ArgumentParser(description="Sync Square data and print the live audit.")
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--from", dest="date_from")
    ap.add_argument("--to", dest="date_to")
    ap.add_argument("--db", default=f"sqlite:///{Path(__file__).with_name('ohh_crumbs.db')}")
    ap.add_argument("--window-days", type=int, default=30)
    ap.add_argument("--report-only", action="store_true",
                    help="skip syncing; just print the audit from the existing DB")
    args = ap.parse_args()

    if args.report_only:
        import audit_core
        print_audit(make_engine(args.db), audit_core)
        return 0

    token, location, environment = load_credentials()
    if not token:
        print("✗ Square access token not found.\n"
              "  Set SQUARE_ACCESS_TOKEN (env var) or add a [square] section to\n"
              "  .streamlit/secrets.toml, then re-run. (Location is auto-discovered.)")
        return 2

    if args.date_from:
        start = datetime.fromisoformat(args.date_from)
        end = datetime.fromisoformat(args.date_to) if args.date_to else datetime.utcnow()
    else:
        end = datetime.utcnow()
        start = end - timedelta(days=args.days)

    try:
        from square import Square
    except Exception as e:
        print(f"✗ Square SDK not importable ({e}). Run: pip install squareup")
        return 2

    client = Square(token=token) if environment == "production" else Square(token=token, environment=environment)

    # Auto-discover the location if one wasn't supplied.
    if not location:
        try:
            resp = client.locations.list()
            locs = getattr(resp, "locations", None) or []
            active = [L for L in locs if getattr(L, "status", "ACTIVE") == "ACTIVE"] or locs
            if not active:
                print("✗ No locations found on this Square account.")
                return 2
            location = active[0].id
            print("Locations found:")
            for L in locs:
                mark = "→" if L.id == location else " "
                print(f"  {mark} {getattr(L, 'name', '?')}  ({L.id})  {getattr(L, 'status', '')}")
            print(f"Using location {location}. Set SQUARE_LOCATION_ID to choose another.\n")
        except Exception as e:
            print(f"✗ Couldn't list locations ({e}). Set SQUARE_LOCATION_ID manually.")
            return 2

    import square_sync
    import audit_core

    session = make_engine(args.db)
    print(f"Syncing {start:%Y-%m-%d} → {end:%Y-%m-%d}  (location {location})\n")

    def progress(frac, msg):
        print(f"  [{int(frac * 100):3d}%] {msg}")

    try:
        counts = square_sync.sync(session, client, location, start, end,
                                  window_days=args.window_days, progress=progress)
    except Exception as e:
        print(f"\n✗ Sync failed: {e}")
        print("  (If this is an SDK method/auth error, tell Claude the message and we'll adjust.)")
        return 1

    print(f"\n✓ {counts['orders_seen']} orders seen, {counts['orders_new']} new; "
          f"{counts['payments_seen']} payments seen, {counts['payments_new']} new.\n")

    print_audit(session, audit_core)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
