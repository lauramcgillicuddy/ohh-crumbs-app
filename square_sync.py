"""Live Square sync — the richer ingestion the audit needs.

Pulls Orders (line items + applied discounts) and Payments (tender type +
processing fees) across an arbitrary date range, normalises them into plain
dicts, and upserts them into the transaction-level tables in models.py.

Design notes
------------
* Normalisation (`normalize_order`, `normalize_payment`) reads values through
  `_get`, which works on both Square SDK objects (attribute access) and plain
  dicts. That lets the logic be unit-tested with dict fixtures without a token.
* Money arrives in minor units (pence) — `_money` divides by 100.
* Fetch windows are chunked (default 30 days) and paginated by cursor, so a
  full year backfills safely.
"""
from datetime import datetime, timedelta, timezone

try:  # Streamlit is optional for the pure functions / tests
    import streamlit as st
except Exception:  # pragma: no cover
    st = None


# ---------------------------------------------------------------------------
# Accessors (work on SDK objects OR dict fixtures)
# ---------------------------------------------------------------------------
def _get(obj, key, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _money(m):
    """A Square *_money object/dict -> float in major units."""
    amount = _get(m, "amount")
    if amount is None:
        return 0.0
    try:
        return float(amount) / 100.0
    except (TypeError, ValueError):
        return 0.0


def _parse_ts(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------
def normalize_line_item(item):
    qty = _get(item, "quantity", "1")
    try:
        qty = float(qty)
    except (TypeError, ValueError):
        qty = 1.0
    return {
        "uid": _get(item, "uid"),
        "name": _get(item, "name") or "Unknown item",
        "variation": _get(item, "variation_name"),
        "category": _get(item, "category_name") or _get(item, "catalog_object_id"),
        "quantity": qty,
        "gross_sales": _money(_get(item, "gross_sales_money")),
        "discount_amount": _money(_get(item, "total_discount_money")),
        "tax_amount": _money(_get(item, "total_tax_money")),
        "net_amount": _money(_get(item, "total_money")),
    }


def normalize_discounts(order):
    out = []
    for d in _get(order, "discounts", []) or []:
        # Percentage discounts (e.g. Friends & Family) leave amount_money empty
        # and report the real figure in applied_money.
        out.append({
            "uid": _get(d, "uid"),
            "name": _get(d, "name") or "Unnamed discount",
            "amount": _money(_get(d, "applied_money") or _get(d, "amount_money")),
            "scope": _get(d, "scope") or "ORDER",
        })
    return out


def normalize_tenders(order):
    out = []
    for t in _get(order, "tenders", []) or []:
        card = _get(_get(t, "card_details"), "card")
        out.append({
            "type": _get(t, "type") or "UNKNOWN",
            "amount": _money(_get(t, "amount_money")),
            "card_brand": _get(card, "card_brand"),
        })
    return out


def normalize_order(order):
    line_items = [normalize_line_item(li) for li in (_get(order, "line_items", []) or [])]
    gross = sum(li["gross_sales"] for li in line_items)
    return {
        "order_id": _get(order, "id"),
        "location_id": _get(order, "location_id"),
        "created_at": _get(order, "created_at"),
        "state": _get(order, "state") or "UNKNOWN",
        "source": _get(_get(order, "source"), "name"),
        "gross_sales": gross,
        "total_discount": _money(_get(order, "total_discount_money")),
        "total_tax": _money(_get(order, "total_tax_money")),
        "net_amount": _money(_get(order, "total_money")),
        "line_items": line_items,
        "discounts": normalize_discounts(order),
        "tenders": normalize_tenders(order),
    }


def normalize_payment(payment):
    fees = 0.0
    for f in _get(payment, "processing_fee", []) or []:
        fees += _money(_get(f, "amount_money"))
    card = _get(_get(payment, "card_details"), "card")
    return {
        "payment_id": _get(payment, "id"),
        "order_id": _get(payment, "order_id"),
        "tender_type": _get(payment, "source_type") or "UNKNOWN",
        "card_brand": _get(card, "card_brand"),
        "amount": _money(_get(payment, "total_money")),
        "processing_fee": fees,
        "status": _get(payment, "status"),
        "created_at": _get(payment, "created_at"),
    }


# ---------------------------------------------------------------------------
# Fetch (talks to the Square SDK)
# ---------------------------------------------------------------------------
def _iso(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _windows(start, end, days=30):
    cur = start
    step = timedelta(days=days)
    while cur < end:
        nxt = min(cur + step, end)
        yield cur, nxt
        cur = nxt


def fetch_orders(client, location_id, start, end, window_days=30):
    """Return normalised order dicts for [start, end), chunked + paginated."""
    orders = []
    for w_start, w_end in _windows(start, end, window_days):
        cursor = None
        while True:
            query = {"filter": {"date_time_filter": {
                "created_at": {"start_at": _iso(w_start), "end_at": _iso(w_end)}}}}
            params = {"location_ids": [location_id], "query": query, "limit": 100}
            if cursor:
                params["cursor"] = cursor
            result = client.orders.search(**params)
            for o in (_get(result, "orders", []) or []):
                orders.append(normalize_order(o))
            cursor = _get(result, "cursor")
            if not cursor:
                break
    return orders


def _iter_results(result, attr):
    """Yield items from either a response object (with `.<attr>`) or a SyncPager.

    Newer Square SDKs return an auto-paginating SyncPager for list endpoints
    (iterate it to walk every page); older ones return a page object exposing
    a list attribute. This handles both.
    """
    items = _get(result, attr)
    if items is not None:
        return list(items)
    try:
        return list(result)  # SyncPager — iterates across all pages
    except TypeError:
        return []


def fetch_payments(client, location_id, start, end, window_days=30):
    """Return normalised payment dicts for [start, end), chunked across windows.

    `payments.list` returns a SyncPager, so each window's pager is iterated to
    completion (it fetches subsequent pages itself).
    """
    payments = []
    for w_start, w_end in _windows(start, end, window_days):
        result = client.payments.list(
            begin_time=_iso(w_start), end_time=_iso(w_end),
            location_id=location_id, limit=100,
        )
        for p in _iter_results(result, "payments"):
            payments.append(normalize_payment(p))
    return payments


# ---------------------------------------------------------------------------
# Upsert into the DB
# ---------------------------------------------------------------------------
def upsert_orders(session, orders):
    """Idempotently store normalised orders + their line items + discounts."""
    from models import SalesOrder, SalesLineItem, SalesDiscountApplied

    stored = 0
    for o in orders:
        oid = o.get("order_id")
        if not oid:
            continue
        created = _parse_ts(o.get("created_at"))
        existing = session.query(SalesOrder).filter_by(square_order_id=oid).first()
        if existing:
            existing.state = o["state"]
            existing.gross_sales = o["gross_sales"]
            existing.total_discount = o["total_discount"]
            existing.total_tax = o["total_tax"]
            existing.net_amount = o["net_amount"]
            existing.synced_at = datetime.utcnow()
        else:
            session.add(SalesOrder(
                square_order_id=oid, location_id=o.get("location_id"),
                created_at=created, state=o["state"], source=o.get("source"),
                gross_sales=o["gross_sales"], total_discount=o["total_discount"],
                total_tax=o["total_tax"], net_amount=o["net_amount"],
            ))
            stored += 1

        # Replace child rows for this order so re-syncs stay consistent.
        session.query(SalesLineItem).filter_by(square_order_id=oid).delete()
        session.query(SalesDiscountApplied).filter_by(square_order_id=oid).delete()
        for li in o["line_items"]:
            session.add(SalesLineItem(
                square_order_id=oid, square_uid=li.get("uid"), name=li["name"],
                variation=li.get("variation"), category=li.get("category"),
                quantity=li["quantity"], gross_sales=li["gross_sales"],
                discount_amount=li["discount_amount"], tax_amount=li["tax_amount"],
                net_amount=li["net_amount"], created_at=created,
            ))
        for d in o["discounts"]:
            session.add(SalesDiscountApplied(
                square_order_id=oid, square_uid=d.get("uid"), name=d["name"],
                amount=d["amount"], scope=d.get("scope"), created_at=created,
            ))
    session.commit()
    return stored


def upsert_payments(session, payments):
    from models import SalesPayment

    stored = 0
    for p in payments:
        pid = p.get("payment_id")
        if not pid:
            continue
        created = _parse_ts(p.get("created_at"))
        existing = session.query(SalesPayment).filter_by(square_payment_id=pid).first()
        if existing:
            existing.processing_fee = p["processing_fee"]
            existing.status = p.get("status")
        else:
            session.add(SalesPayment(
                square_payment_id=pid, square_order_id=p.get("order_id"),
                tender_type=p["tender_type"], card_brand=p.get("card_brand"),
                amount=p["amount"], processing_fee=p["processing_fee"],
                status=p.get("status"), created_at=created,
            ))
            stored += 1
    session.commit()
    return stored


def sync(session, client, location_id, start, end, window_days=30, progress=None):
    """Full sync for a date range. Returns a counts dict. `progress` is an
    optional callable(fraction, message) for UI feedback."""
    from models import SyncLog

    if progress:
        progress(0.1, "Fetching orders from Square…")
    orders = fetch_orders(client, location_id, start, end, window_days)

    if progress:
        progress(0.45, "Fetching payments…")
    payments = fetch_payments(client, location_id, start, end, window_days)

    if progress:
        progress(0.75, "Saving to database…")
    n_orders = upsert_orders(session, orders)
    n_payments = upsert_payments(session, payments)

    session.add(SyncLog(
        window_start=start, window_end=end,
        orders_synced=n_orders, payments_synced=n_payments,
        status="ok", message=f"{len(orders)} orders / {len(payments)} payments seen",
    ))
    session.commit()

    if progress:
        progress(1.0, "Done")
    return {
        "orders_seen": len(orders), "orders_new": n_orders,
        "payments_seen": len(payments), "payments_new": n_payments,
    }
