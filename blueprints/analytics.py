
from flask import Blueprint, render_template
from db import DataStore

bp = Blueprint("analytics", __name__)
db = DataStore()

@bp.route("/dashboard")

def dashboard():
    import datetime, os
    # KPIs base
    kpis = db.kpis()
    # Periods
    today = datetime.date.today()
    month_start = today.replace(day=1)

    # Month-to-date analytics
    orders_mt = db.list_orders_filtered(date_from=month_start, date_to=today, limit=100000)
    revenue_mt = float(sum(float(o.get("total") or 0) for o in orders_mt))
    orders_mt_count = len(orders_mt)
    avg_check_mt = (revenue_mt / orders_mt_count) if orders_mt_count else 0.0
    refunds_mt = float(sum(float(o.get("total") or 0) for o in orders_mt if (o.get("payment_status") == "refunded")))

    # Status distribution (last 30 days)
    last30 = today - datetime.timedelta(days=29)
    orders_30 = db.list_orders_filtered(date_from=last30, date_to=today, limit=100000)
    statuses = {}
    for o in orders_30:
        s = (o.get("status") or "created")
        statuses[s] = statuses.get(s, 0) + 1

    # Conversion rate (approx): paid+done / created (last 30 days)
    created = statuses.get("created", 0)
    paid_done = statuses.get("paid", 0) + statuses.get("done", 0)
    conversion = (paid_done / created * 100.0) if created else None

    # Low stock
    low_thr = int(os.getenv("LOW_STOCK_THRESHOLD", "5"))
    stock_rows = db.list_stock(limit=5000)
    low_stock = [p for p in stock_rows if int(p.get("stock") or 0) <= low_thr][:20]

    # Recent orders
    recent_orders = db.list_orders_filtered(limit=20)

    # Top products current month
    top_month = db.top_products(month_start, today, limit=10)

    # Upcoming scheduled posts
    try:
        upcoming_posts = db.list_scheduled_posts(limit=10) or []
    except Exception:
        upcoming_posts = []

    # Env checks (alerts)
    env_alerts = []
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        env_alerts.append("Не задан TELEGRAM_BOT_TOKEN — отправка в канал недоступна")
    if not (os.getenv("POST_CHANNEL_ID") or os.getenv("TELEGRAM_CHANNEL_ID")):
        env_alerts.append("Не задан POST_CHANNEL_ID/TELEGRAM_CHANNEL_ID — неизвестен канал для постинга")
    if not (os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY")) and not os.getenv("DATABASE_URL"):
        env_alerts.append("Нет подключения к БД (SUPABASE_* или DATABASE_URL)")

    # Timeseries (14 days) already used
    ts = db.timeseries_revenue_orders(14)

    # Open orders count
    open_orders = db.count_open_orders()

    return render_template("analytics/dashboard.html",
        kpis=kpis,
        ts=ts,
        month=dict(
            revenue=revenue_mt, orders=orders_mt_count, avg_check=avg_check_mt, refunds=refunds_mt
        ),
        statuses=statuses,
        conversion=conversion,
        low_stock=low_stock,
        recent_orders=recent_orders,
        top_month=top_month,
        upcoming_posts=upcoming_posts,
        env_alerts=env_alerts,
        low_thr=low_thr,
    )

@bp.route("/advanced")
def advanced():
    from flask import request
    import datetime
    df = request.args.get("date_from"); dt = request.args.get("date_to")
    date_from = datetime.date.fromisoformat(df) if df else datetime.date.today().replace(day=1)
    date_to = datetime.date.fromisoformat(dt) if dt else datetime.date.today()
    data = db.analytics_period(date_from, date_to)
    return render_template("analytics/advanced.html", data=data, date_from=date_from.isoformat(), date_to=date_to.isoformat())


@bp.route("/timeseries")
def timeseries():
    from flask import request, render_template
    import datetime
    df = request.args.get("date_from"); dt = request.args.get("date_to"); grp = (request.args.get("group") or "day").lower()
    date_from = datetime.date.fromisoformat(df) if df else datetime.date.today().replace(day=1)
    date_to = datetime.date.fromisoformat(dt) if dt else datetime.date.today()
    ts = db.timeseries_grouped(date_from, date_to, grp)
    return render_template("analytics/timeseries.html", ts=ts, date_from=date_from.isoformat(), date_to=date_to.isoformat(), group=grp)

@bp.route("/top-products")
def top_products():
    from flask import request, render_template
    import datetime
    df = request.args.get("date_from"); dt = request.args.get("date_to")
    date_from = datetime.date.fromisoformat(df) if df else datetime.date.today().replace(day=1)
    date_to = datetime.date.fromisoformat(dt) if dt else datetime.date.today()
    arr = db.top_products(date_from, date_to, limit=20)
    return render_template("analytics/top_products.html", items=arr, date_from=date_from.isoformat(), date_to=date_to.isoformat())
