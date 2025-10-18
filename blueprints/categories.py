
from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import DataStore
from utils.auth import require_role

bp = Blueprint("categories", __name__)
db = DataStore()

@bp.route("/")
@require_role("admin","manager","support")
def list_():
    cats = db.list_categories()
    subs = db.list_subcategories()
    # group subs by category_id
    by_cat = {}
    for s in subs:
        by_cat.setdefault(s.get("category_id"), []).append(s)
    return render_template("categories/list.html", cats=cats, by_cat=by_cat)

@bp.route("/new", methods=["GET","POST"])
@require_role("admin","manager")
def new():
    if request.method == "POST":
        name = request.form.get("name")
        db.create_category(name)
        flash("Категория создана", "success")
        return redirect(url_for("categories.list_"))
    return render_template("categories/cat_form.html", item=None)

@bp.route("/<int:cid>/edit", methods=["GET","POST"])
@require_role("admin","manager")
def edit(cid: int):
    item = db.get_category(cid)
    if not item:
        flash("Категория не найдена", "warning")
        return redirect(url_for("categories.list_"))
    if request.method == "POST":
        name = request.form.get("name")
        db.update_category(cid, name)
        flash("Сохранено", "success")
        return redirect(url_for("categories.list_"))
    return render_template("categories/cat_form.html", item=item)

@bp.route("/<int:cid>/delete", methods=["POST"])
@require_role("admin")
def delete(cid: int):
    db.delete_category(cid)
    flash("Удалено", "info")
    return redirect(url_for("categories.list_"))

# ----- Subcategories -----
@bp.route("/sub/new", methods=["GET","POST"])
@require_role("admin","manager")
def sub_new():
    if request.method == "POST":
        category_id = int(request.form.get("category_id"))
        name = request.form.get("name")
        db.create_subcategory(category_id, name)
        flash("Подкатегория создана", "success")
        return redirect(url_for("categories.list_"))
    cats = db.list_categories()
    return render_template("categories/sub_form.html", cats=cats, item=None)

@bp.route("/sub/<int:sid>/edit", methods=["GET","POST"])
@require_role("admin","manager")
def sub_edit(sid: int):
    subs = db.list_subcategories()
    item = next((s for s in subs if s.get("id")==sid), None)
    if not item:
        flash("Подкатегория не найдена", "warning")
        return redirect(url_for("categories.list_"))
    if request.method == "POST":
        category_id = int(request.form.get("category_id"))
        name = request.form.get("name")
        db.update_subcategory(sid, category_id, name)
        flash("Сохранено", "success")
        return redirect(url_for("categories.list_"))
    cats = db.list_categories()
    return render_template("categories/sub_form.html", cats=cats, item=item)

@bp.route("/sub/<int:sid>/delete", methods=["POST"])
@require_role("admin")
def sub_delete(sid: int):
    db.delete_subcategory(sid)
    flash("Удалено", "info")
    return redirect(url_for("categories.list_"))
