
from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import DataStore
from utils.auth import require_role

bp = Blueprint("orders", __name__)
db = DataStore()

def require_support(view):
    from functools import wraps
    from flask import session, redirect, url_for, flash
    @wraps(view)
    def wrapper(*args, **kwargs):
        if session.get("role") not in ("admin","manager","support"):
            flash("Недостаточно прав", "warning")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapper

@bp.route("/")
@require_support
def list_():
    status = request.args.get("status")
    items = db.list_orders(status=status, limit=200)
    return render_template("orders/list.html", items=items, status=status)

@bp.route("/<int:oid>")
@require_support
def details(oid: int):
    o = db.get_order(oid)
    if not o:
        flash("Заказ не найден", "warning")
        return redirect(url_for("orders.list_"))
    return render_template("orders/details.html", o=o)

@bp.route("/<int:oid>/update", methods=["POST"])
@require_support
def update(oid: int):
    status = request.form.get("status")
    payment_status = request.form.get("payment_status")
    db.update_order_status(oid, status, payment_status)
    flash("Статус заказа обновлён", "success")
    return redirect(url_for("orders.details", oid=oid))

@bp.route("/export.csv")
def export_csv():
    from flask import send_file
    from utils.exporter import to_csv_bytes
    status = request.args.get("status"); pay = request.args.get("pay")
    date_from = request.args.get("date_from"); date_to = request.args.get("date_to")
    import datetime
    df = datetime.date.fromisoformat(date_from) if date_from else None
    dt = datetime.date.fromisoformat(date_to) if date_to else None
    rows = db.list_orders_filtered(status=status, pay=pay, date_from=df, date_to=dt)
    import io
    bio = io.BytesIO(to_csv_bytes(rows))
    bio.seek(0)
    return send_file(bio, mimetype="text/csv", as_attachment=True, download_name="orders.csv")

@bp.route("/export.xlsx")
def export_xlsx():
    from flask import send_file
    from utils.exporter import to_xlsx_bytes
    status = request.args.get("status"); pay = request.args.get("pay")
    date_from = request.args.get("date_from"); date_to = request.args.get("date_to")
    import datetime, io
    df = datetime.date.fromisoformat(date_from) if date_from else None
    dt = datetime.date.fromisoformat(date_to) if date_to else None
    rows = db.list_orders_filtered(status=status, pay=pay, date_from=df, date_to=dt)
    bio = io.BytesIO(to_xlsx_bytes(rows))
    bio.seek(0)
    return send_file(bio, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="orders.xlsx")
