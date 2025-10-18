
from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import DataStore
from utils.auth import require_role

bp = Blueprint("inventory", __name__)
db = DataStore()

@bp.route("/")
def stock():
    items = db.list_stock(limit=300)
    return render_template("inventory/stock.html", items=items)

@bp.route("/adjust/<int:pid>", methods=["POST"])
def adjust(pid: int):
    delta = int(request.form.get("delta") or 0)
    reason = request.form.get("reason") or "manual"
    db.adjust_stock(pid, delta, reason)
    flash("Склад скорректирован", "success")
    return redirect(url_for("inventory.stock"))

@bp.route("/export.csv")
def export_csv():
    from flask import send_file
    from utils.exporter import to_csv_bytes
    rows = db.list_stock(limit=2000)
    import io
    bio = io.BytesIO(to_csv_bytes(rows))
    bio.seek(0)
    return send_file(bio, mimetype="text/csv", as_attachment=True, download_name="inventory.csv")

@bp.route("/export.xlsx")
def export_xlsx():
    from flask import send_file
    from utils.exporter import to_xlsx_bytes
    rows = db.list_stock(limit=2000)
    import io
    bio = io.BytesIO(to_xlsx_bytes(rows))
    bio.seek(0)
    return send_file(bio, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="inventory.xlsx")
