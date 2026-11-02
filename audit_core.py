"""Profitability audit — pure analysis core (no Streamlit).

Ingests Square's own report exports (Sales Summary + Discounts) and computes
the audit metrics the live sync currently throws away: discount leakage by
type, cash-vs-card mix, and Square fee drag, plus a gross -> take-home bridge.

Kept free of Streamlit/Plotly imports so the figures can be unit-checked
against the real CSVs with a plain Python run.
"""
import csv
import io
import pandas as pd


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------
def parse_currency(value):
    """'£62,954.26' -> 62954.26 ; '(£19.15)' -> -19.15 ; '£0.00' -> 0.0."""
    if value is None:
        return 0.0
    s = str(value).strip().strip('"').strip()
    if s in ("", "—", "-", "–"):
        return 0.0
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1]
    s = s.replace("£", "").replace(",", "").strip()
    if s.startswith("-"):
        neg = True
        s = s[1:]
    try:
        num = float(s)
    except ValueError:
        return 0.0
    return -num if neg else num


def parse_int(value):
    if value is None:
        return 0
    s = str(value).replace(",", "").strip().strip('"').strip()
    try:
        return int(float(s))
    except ValueError:
        return 0


def load_sales_summary(source):
    """Read a Square 'Sales summary' export into a {label: raw_value} dict.

    `source` may be a file path, a file-like object, or raw text/bytes.
    The export is a two-column key/value sheet with a quoted multi-line header.
    """
    text = _read_text(source)
    rows = csv.reader(io.StringIO(text), delimiter=_sniff_delim(text))
    summary = {}
    for row in rows:
        if len(row) < 2:
            continue
        key = row[0].strip().strip('"').strip()
        val = row[1].strip()
        if key and key not in summary:  # keep first occurrence
            summary[key] = val
    return summary


def load_discounts(source):
    """Read a Square 'Discounts' export into a tidy DataFrame."""
    text = _read_text(source)
    df = pd.read_csv(io.StringIO(text), sep=_sniff_delim(text))
    df = df.dropna(how="all")
    # Normalise expected columns regardless of minor header drift.
    name_col = _find_col(df, "Name")
    count_col = _find_col(df, "Discounts Applied")
    amount_col = _find_col(df, "Amount Discounted")
    out = pd.DataFrame({
        "name": df[name_col].astype(str).str.strip(),
        "count": df[count_col].apply(parse_int),
        "amount": df[amount_col].apply(parse_currency).abs(),
    })
    out = out[(out["name"] != "") & (out["name"].str.lower() != "nan")]
    return out.reset_index(drop=True)


def _read_text(source):
    if hasattr(source, "read"):
        data = source.read()
        return _decode(data) if isinstance(data, (bytes, bytearray)) else data
    if isinstance(source, (bytes, bytearray)):
        return _decode(source)
    if isinstance(source, str) and "\n" in source:
        return source
    with open(source, "rb") as fh:
        return _decode(fh.read())


def _sniff_delim(text):
    """Square mixes comma-CSV and tab-TSV exports; pick whichever the header uses."""
    first = next((ln for ln in text.splitlines() if ln.strip()), "")
    return "\t" if "\t" in first and first.count("\t") >= first.count(",") else ","


def _decode(data):
    """Decode bytes from a Square export, sniffing the BOM (UTF-16 is common)."""
    data = bytes(data)
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16")
    if data[:3] == b"\xef\xbb\xbf":
        return data.decode("utf-8-sig")
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _find_col(df, wanted):
    for c in df.columns:
        if str(c).strip().lower() == wanted.lower():
            return c
    for c in df.columns:  # fall back to substring
        if wanted.lower() in str(c).strip().lower():
            return c
    raise KeyError(f"Column like '{wanted}' not found in {list(df.columns)}")


# ---------------------------------------------------------------------------
# Audit computation
# ---------------------------------------------------------------------------
def compute_audit(summary, discounts):
    """Return a structured audit dict from a summary dict + discounts DataFrame."""
    g = lambda k: parse_currency(summary.get(k))

    product_sales = g("Product sales")
    returns = g("Returns")                 # negative
    discounts_total = abs(g("Discounts"))  # positive magnitude
    net_sales = g("Net sales")
    card = g("Card")
    cash = g("Cash")
    fees = abs(g("Fees"))                   # positive magnitude
    net_total = g("Net total")
    num_sales = parse_int(summary.get("Total number of sales"))
    discount_txns = parse_int(summary.get("Discounts transactions"))

    collected = card + cash
    avg_sale = net_sales / num_sales if num_sales else 0.0

    # Discount leakage table
    disc = discounts.copy()
    total_disc = disc["amount"].sum() or discounts_total or 1.0
    disc["avg_per_use"] = disc.apply(
        lambda r: r["amount"] / r["count"] if r["count"] else 0.0, axis=1)
    disc["pct_of_discounts"] = disc["amount"] / total_disc * 100
    disc["pct_of_sales"] = disc["amount"] / product_sales * 100 if product_sales else 0.0
    disc = disc.sort_values("amount", ascending=False).reset_index(drop=True)

    kpis = {
        "net_sales": net_sales,
        "transactions": num_sales,
        "avg_sale": avg_sale,
        "discounts_total": discounts_total,
        "discount_rate_pct": discounts_total / product_sales * 100 if product_sales else 0.0,
        "fees_total": fees,
        "fee_rate_pct": fees / collected * 100 if collected else 0.0,
        "cash_pct": cash / collected * 100 if collected else 0.0,
        "card_pct": card / collected * 100 if collected else 0.0,
        "effective_discount_per_txn": discounts_total / discount_txns if discount_txns else 0.0,
        "take_home": net_total,
    }

    # Money bridge: Product sales -> ... -> take-home
    bridge = [
        {"label": "Product sales", "value": product_sales, "kind": "start"},
        {"label": "Returns", "value": returns, "kind": "delta"},
        {"label": "Discounts", "value": -discounts_total, "kind": "delta"},
        {"label": "Net sales", "value": net_sales, "kind": "subtotal"},
        {"label": "Square fees", "value": -fees, "kind": "delta"},
        {"label": "Take-home", "value": net_total, "kind": "total"},
    ]

    tender = [
        {"method": "Card", "amount": card, "pct": kpis["card_pct"]},
        {"method": "Cash", "amount": cash, "pct": kpis["cash_pct"]},
    ]

    return {
        "kpis": kpis,
        "discounts": disc,
        "bridge": bridge,
        "tender": tender,
        "insights": _build_insights(kpis, disc, cash, collected),
        "raw": {
            "product_sales": product_sales, "returns": returns,
            "net_sales": net_sales, "card": card, "cash": cash,
            "fees": fees, "take_home": net_total,
        },
    }


def _build_insights(kpis, disc, cash, collected):
    out = []
    if not disc.empty:
        top = disc.iloc[0]
        out.append({
            "level": "serious" if top["pct_of_discounts"] >= 40 else "warning",
            "text": (f"'{top['name']}' is your biggest discount by value: "
                     f"£{top['amount']:,.0f} ({top['pct_of_discounts']:.0f}% of all "
                     f"discounts) across {int(top['count'])} uses "
                     f"— £{top['avg_per_use']:.2f} off each."),
        })
        # A high average give-away flags an uncapped/open discount.
        heavy = disc[disc["avg_per_use"] >= 8].sort_values("avg_per_use", ascending=False)
        if not heavy.empty and heavy.iloc[0]["name"] != top["name"]:
            h = heavy.iloc[0]
            out.append({
                "level": "warning",
                "text": (f"'{h['name']}' averages £{h['avg_per_use']:.2f} off per use "
                         f"— worth checking it isn't open-ended."),
            })
    out.append({
        "level": "info",
        "text": (f"Discounts are {kpis['discount_rate_pct']:.1f}% of product sales "
                 f"(£{kpis['discounts_total']:,.0f} given away)."),
    })
    if kpis["cash_pct"] >= 25:
        out.append({
            "level": "warning",
            "text": (f"Cash is {kpis['cash_pct']:.0f}% of takings "
                     f"(£{cash:,.0f}) — high ratio; worth reconciling for tax."),
        })
    out.append({
        "level": "info",
        "text": (f"Square fees take £{kpis['fees_total']:,.0f} "
                 f"({kpis['fee_rate_pct']:.1f}% of payments collected)."),
    })
    return out


# ---------------------------------------------------------------------------
# Live audit — transaction-level, from the Square sync (or the DB).
# Richer than the CSV path: real discount-by-type, true tender split from
# payments, fees per order, and per-item gross/net/margin.
# ---------------------------------------------------------------------------
def _frames_from_normalized(orders, payments):
    order_rows, line_rows, disc_rows, pay_rows = [], [], [], []
    for o in orders:
        if str(o.get("state", "")).upper() in ("CANCELED", "DRAFT"):
            continue
        oid = o.get("order_id")
        order_rows.append({
            "order_id": oid, "created_at": o.get("created_at"),
            "gross_sales": o.get("gross_sales", 0.0),
            "total_discount": o.get("total_discount", 0.0),
            "net_amount": o.get("net_amount", 0.0),
        })
        for li in o.get("line_items", []):
            line_rows.append({
                "order_id": oid, "name": li.get("name", "Unknown item"),
                "category": li.get("category"), "quantity": li.get("quantity", 0.0),
                "gross_sales": li.get("gross_sales", 0.0),
                "discount_amount": li.get("discount_amount", 0.0),
                "net_amount": li.get("net_amount", 0.0),
            })
        for d in o.get("discounts", []):
            disc_rows.append({"order_id": oid, "name": d.get("name", "Unnamed discount"),
                              "amount": d.get("amount", 0.0)})
    for p in payments:
        pay_rows.append({
            "order_id": p.get("order_id"), "tender_type": (p.get("tender_type") or "UNKNOWN").upper(),
            "amount": p.get("amount", 0.0), "processing_fee": p.get("processing_fee", 0.0),
        })
    return (pd.DataFrame(order_rows), pd.DataFrame(line_rows),
            pd.DataFrame(disc_rows), pd.DataFrame(pay_rows))


def _frames_from_db(session):
    from models import SalesOrder, SalesLineItem, SalesDiscountApplied, SalesPayment

    def frame(rows, cols):
        return pd.DataFrame([{c: getattr(r, c) for c in cols} for r in rows],
                            columns=cols)

    orders = frame(session.query(SalesOrder).all(),
                   ["square_order_id", "created_at", "gross_sales", "total_discount", "net_amount"])
    orders = orders.rename(columns={"square_order_id": "order_id"})
    lines = frame(session.query(SalesLineItem).all(),
                  ["square_order_id", "name", "category", "quantity",
                   "gross_sales", "discount_amount", "net_amount"]).rename(
                      columns={"square_order_id": "order_id"})
    disc = frame(session.query(SalesDiscountApplied).all(),
                 ["square_order_id", "name", "amount"]).rename(
                     columns={"square_order_id": "order_id"})
    pays = frame(session.query(SalesPayment).all(),
                 ["square_order_id", "tender_type", "amount", "processing_fee"]).rename(
                     columns={"square_order_id": "order_id"})
    if not pays.empty:
        pays["tender_type"] = pays["tender_type"].fillna("UNKNOWN").str.upper()
    return orders, lines, disc, pays


def compute_audit_live(orders, payments, recipe_costs=None):
    """Compute the audit from normalised sync data (lists of dicts)."""
    return _compute_from_frames(*_frames_from_normalized(orders, payments), recipe_costs)


def compute_audit_live_from_db(session, recipe_costs=None):
    """Compute the audit from the stored transaction tables."""
    return _compute_from_frames(*_frames_from_db(session), recipe_costs)


def _compute_from_frames(order_df, line_df, disc_df, pay_df, recipe_costs=None):
    net_sales = float(order_df["net_amount"].sum()) if not order_df.empty else 0.0
    transactions = int(order_df["order_id"].nunique()) if not order_df.empty else 0
    discounts_total = float(disc_df["amount"].sum()) if not disc_df.empty else 0.0
    discounted_orders = int(disc_df["order_id"].nunique()) if not disc_df.empty else 0
    # Pre-discount gross = net + discounts. (Returns aren't tracked on the live
    # feed yet; line-level gross_sales_money proved unreliable for this merchant.)
    gross = net_sales + discounts_total

    fees_total = float(pay_df["processing_fee"].sum()) if not pay_df.empty else 0.0
    collected = float(pay_df["amount"].sum()) if not pay_df.empty else 0.0
    cash = float(pay_df.loc[pay_df["tender_type"] == "CASH", "amount"].sum()) if not pay_df.empty else 0.0
    card = float(pay_df.loc[pay_df["tender_type"] == "CARD", "amount"].sum()) if not pay_df.empty else 0.0

    kpis = {
        "net_sales": net_sales,
        "transactions": transactions,
        "avg_sale": net_sales / transactions if transactions else 0.0,
        "discounts_total": discounts_total,
        "discount_rate_pct": discounts_total / gross * 100 if gross else 0.0,
        "fees_total": fees_total,
        "fee_rate_pct": fees_total / collected * 100 if collected else 0.0,
        "cash_pct": cash / collected * 100 if collected else 0.0,
        "card_pct": card / collected * 100 if collected else 0.0,
        "effective_discount_per_txn": discounts_total / discounted_orders if discounted_orders else 0.0,
        "take_home": net_sales - fees_total,
    }

    # Discount leakage by type
    if not disc_df.empty:
        disc = disc_df.groupby("name", as_index=False).agg(
            count=("amount", "size"), amount=("amount", "sum"))
        total_disc = disc["amount"].sum() or 1.0
        disc["avg_per_use"] = disc.apply(
            lambda r: r["amount"] / r["count"] if r["count"] else 0.0, axis=1)
        disc["pct_of_discounts"] = disc["amount"] / total_disc * 100
        disc["pct_of_sales"] = disc["amount"] / gross * 100 if gross else 0.0
        disc = disc.sort_values("amount", ascending=False).reset_index(drop=True)
    else:
        disc = pd.DataFrame(columns=["name", "count", "amount", "avg_per_use",
                                     "pct_of_discounts", "pct_of_sales"])

    # Per-item performance (+ margin where we know recipe cost)
    top_items = pd.DataFrame()
    if not line_df.empty:
        top_items = line_df.groupby("name", as_index=False).agg(
            units=("quantity", "sum"), gross=("gross_sales", "sum"),
            discount=("discount_amount", "sum"), net=("net_amount", "sum"))
        if recipe_costs:
            top_items["unit_cost"] = top_items["name"].map(
                lambda n: float(recipe_costs.get(n, 0.0)))
            top_items["cost"] = top_items["unit_cost"] * top_items["units"]
            top_items["profit"] = top_items["net"] - top_items["cost"]
            top_items["margin_pct"] = top_items.apply(
                lambda r: r["profit"] / r["net"] * 100 if r["net"] else 0.0, axis=1)
        top_items = top_items.sort_values("net", ascending=False).reset_index(drop=True)

    bridge = [
        {"label": "Gross sales", "value": gross, "kind": "start"},
        {"label": "Discounts", "value": -discounts_total, "kind": "delta"},
        {"label": "Net sales", "value": net_sales, "kind": "subtotal"},
        {"label": "Square fees", "value": -fees_total, "kind": "delta"},
        {"label": "Take-home", "value": kpis["take_home"], "kind": "total"},
    ]
    tender = [
        {"method": "Card", "amount": card, "pct": kpis["card_pct"]},
        {"method": "Cash", "amount": cash, "pct": kpis["cash_pct"]},
    ]

    return {
        "kpis": kpis,
        "discounts": disc,
        "top_items": top_items,
        "bridge": bridge,
        "tender": tender,
        "insights": _build_insights(kpis, disc, cash, collected),
        "source": "live",
    }
