
from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import DataStore
from utils.auth import require_role

bp = Blueprint("products", __name__)
db = DataStore()

def require_manager(view):
    from functools import wraps
    from flask import session, redirect, url_for, flash
    @wraps(view)
    def wrapper(*args, **kwargs):
        if session.get("role") not in ("admin","manager"):
            flash("Недостаточно прав", "warning")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapper

@bp.route("/")
def list_():
    q = request.args.get("q")
    items = db.list_products(q=q, limit=200)
    return render_template("products/list.html", items=items, q=q)

@bp.route("/new", methods=["GET","POST"])
@require_manager
def new():
    cats = db.list_categories(); subs = db.list_subcategories()
    if request.method == "POST":
        data = {
            "name": request.form.get("name"),
            "price": float(request.form.get("price") or 0),
            "stock": int(request.form.get("stock") or 0),
            "category": request.form.get("category") or None,
            "subcategory_id": int(request.form.get("subcategory_id")) if request.form.get("subcategory_id") else None,
            "description": request.form.get("description") or None,
        }
        db.create_product(data)
        flash("Товар создан", "success")
        return redirect(url_for("products.list_"))
    return render_template("products/form.html", item=None, cats=cats, subs=subs)

@bp.route("/<int:pid>/edit", methods=["GET","POST"])
@require_manager
def edit(pid: int):
    item = db.get_product(pid)
    cats = db.list_categories(); subs = db.list_subcategories()
    if not item:
        flash("Товар не найден", "warning")
        return redirect(url_for("products.list_"))
    if request.method == "POST":
        data = {
            "name": request.form.get("name"),
            "price": float(request.form.get("price") or 0),
            "stock": int(request.form.get("stock") or 0),
            "category": request.form.get("category") or None,
            "subcategory_id": int(request.form.get("subcategory_id")) if request.form.get("subcategory_id") else None,
            "description": request.form.get("description") or None,
        }
        db.update_product(pid, data)
        flash("Сохранено", "success")
        return redirect(url_for("products.list_"))
    return render_template("products/form.html", item=item, cats=cats, subs=subs)

@bp.route("/<int:pid>/delete", methods=["POST"])
@require_manager
def delete(pid: int):
    db.delete_product(pid)
    flash("Удалено", "info")
    return redirect(url_for("products.list_"))

@bp.route("/export.csv")
def export_csv():
    from flask import send_file
    from utils.exporter import to_csv_bytes
    q = request.args.get("q"); category = request.args.get("category")
    price_min = request.args.get("price_min", type=float)
    price_max = request.args.get("price_max", type=float)
    in_stock = request.args.get("in_stock")
    in_stock = (in_stock == "1") if in_stock is not None else None
    rows = db.list_products_filtered(q=q, category=category, price_min=price_min, price_max=price_max, in_stock=in_stock)
    import io
    bio = io.BytesIO(to_csv_bytes(rows))
    bio.seek(0)
    return send_file(bio, mimetype="text/csv", as_attachment=True, download_name="products.csv")

@bp.route("/export.xlsx")
def export_xlsx():
    from flask import send_file
    from utils.exporter import to_xlsx_bytes
    q = request.args.get("q"); category = request.args.get("category")
    price_min = request.args.get("price_min", type=float)
    price_max = request.args.get("price_max", type=float)
    in_stock = request.args.get("in_stock")
    in_stock = (in_stock == "1") if in_stock is not None else None
    rows = db.list_products_filtered(q=q, category=category, price_min=price_min, price_max=price_max, in_stock=in_stock)
    import io
    bio = io.BytesIO(to_xlsx_bytes(rows))
    bio.seek(0)
    return send_file(bio, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="products.xlsx")

@bp.route("/bulk", methods=["GET","POST"])
@require_manager
def bulk():
    from flask import render_template
    info = None
    if request.method == "POST":
        f = request.files.get("file")
        mode = request.form.get("mode")  # 'upsert' or 'price_pct' or 'stock_set'
        if f and f.filename:
            import pandas as pd
            df = pd.read_excel(f) if f.filename.lower().endswith("xlsx") else pd.read_csv(f)
            # expect columns: id(optional), name, price, stock, category, description
            applied = 0
            if mode == "upsert":
                for _, r in df.iterrows():
                    data = {k: r.get(k) for k in ["name","price","stock","category","description"] if k in df.columns}
                    if "id" in df.columns and not pd.isna(r.get("id")):
                        db.update_product(int(r.get("id")), data)
                    else:
                        db.create_product(data)
                    applied += 1
            elif mode == "price_pct":
                pct = float(request.form.get("pct") or 0)
                for _, r in df.iterrows():
                    pid = int(r.get("id"))
                    p = db.get_product(pid)
                    if p:
                        new_price = round(float(p.get("price") or 0) * (1 + pct/100.0), 2)
                        db.update_product(pid, {"price": new_price})
                        applied += 1
            elif mode == "stock_set":
                for _, r in df.iterrows():
                    pid = int(r.get("id"))
                    st = int(r.get("stock"))
                    db.update_product(pid, {"stock": st})
                    applied += 1
            info = f"Применено: {applied}"
    return render_template("products/bulk.html", info=info)
