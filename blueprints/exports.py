
from flask import Blueprint, send_file, request
from db import DataStore
from utils.auth import require_role
from utils.exporter import export_all_zip
import datetime, io

bp = Blueprint("exports", __name__)
db = DataStore()

@bp.route("/all.zip")
def all_zip():
    # optional period filters for orders/customers
    df = request.args.get("date_from"); dt = request.args.get("date_to")
    d_from = datetime.date.fromisoformat(df) if df else None
    d_to = datetime.date.fromisoformat(dt) if dt else None

    datasets = {}
    # products
    datasets["products_csv"] = db.list_products_filtered(limit=5000)
    datasets["products_xlsx"] = datasets["products_csv"]
    # orders
    datasets["orders_csv"] = db.list_orders_filtered(date_from=d_from, date_to=d_to, limit=100000)
    datasets["orders_xlsx"] = datasets["orders_csv"]
    # customers
    datasets["customers_csv"] = db.list_customers_filtered(date_from=d_from, date_to=d_to, limit=100000)
    datasets["customers_xlsx"] = datasets["customers_csv"]
    # inventory snapshot
    datasets["inventory_csv"] = db.list_stock(limit=5000)
    datasets["inventory_xlsx"] = datasets["inventory_csv"]

    data = export_all_zip(datasets)
    bio = io.BytesIO(data); bio.seek(0)
    return send_file(bio, mimetype="application/zip", as_attachment=True, download_name="export_all.zip")


@bp.route("/pricelist.pdf")
def pricelist_pdf():
    from utils.exporter import pricelist_pdf_bytes
    rows = db.products_with_subcat(limit=10000)
    data = pricelist_pdf_bytes(rows)
    import io
    bio = io.BytesIO(data); bio.seek(0)
    return send_file(bio, mimetype="application/pdf", as_attachment=True, download_name="pricelist.pdf")

@bp.route("/price_stock.csv")
def price_stock_csv():
    from utils.exporter import to_csv_bytes
    rows = db.products_with_subcat(limit=10000)
    import io
    bio = io.BytesIO(to_csv_bytes(rows))
    bio.seek(0)
    return send_file(bio, mimetype="text/csv", as_attachment=True, download_name="price_stock.csv")

@bp.route("/price_stock.xlsx")
def price_stock_xlsx():
    from utils.exporter import to_xlsx_bytes
    rows = db.products_with_subcat(limit=10000)
    import io
    bio = io.BytesIO(to_xlsx_bytes(rows))
    bio.seek(0)
    return send_file(bio, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="price_stock.xlsx")
