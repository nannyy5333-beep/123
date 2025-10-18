
from flask import Blueprint, render_template, request
from db import DataStore
from utils.auth import require_role

bp = Blueprint("customers", __name__)
db = DataStore()

@bp.route("/")
def list_():
    items = db.list_customers(limit=300)
    return render_template("customers/list.html", items=items)

@bp.route("/export.csv")
def export_csv():
    from flask import request, send_file
    from utils.exporter import to_csv_bytes
    q = request.args.get("q")
    date_from = request.args.get("date_from"); date_to = request.args.get("date_to")
    import datetime, io
    df = datetime.date.fromisoformat(date_from) if date_from else None
    dt = datetime.date.fromisoformat(date_to) if date_to else None
    rows = db.list_customers_filtered(q=q, date_from=df, date_to=dt)
    bio = io.BytesIO(to_csv_bytes(rows))
    bio.seek(0)
    return send_file(bio, mimetype="text/csv", as_attachment=True, download_name="customers.csv")

@bp.route("/export.xlsx")
def export_xlsx():
    from flask import request, send_file
    from utils.exporter import to_xlsx_bytes
    q = request.args.get("q")
    date_from = request.args.get("date_from"); date_to = request.args.get("date_to")
    import datetime, io
    df = datetime.date.fromisoformat(date_from) if date_from else None
    dt = datetime.date.fromisoformat(date_to) if date_to else None
    rows = db.list_customers_filtered(q=q, date_from=df, date_to=dt)
    bio = io.BytesIO(to_xlsx_bytes(rows))
    bio.seek(0)
    return send_file(bio, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="customers.xlsx")
