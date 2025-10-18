
from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import DataStore
from utils.auth import require_role

bp = Blueprint("scheduled", __name__)
db = DataStore()

@bp.route("/")
def list_():
    items = db.list_scheduled_posts()
    return render_template("scheduled/list.html", items=items)

@bp.route("/new", methods=["GET","POST"])
def new():
    info = None
    if request.method == "POST":
        product_id = int(request.form.get("product_id"))
        run_at = request.form.get("run_at")  # 'YYYY-MM-DD HH:MM'
        caption = request.form.get("caption")
        db.create_scheduled_post(product_id, run_at, caption=caption)
        flash("Задание добавлено", "success")
        return redirect(url_for("scheduled.list_"))
    return render_template("scheduled/form.html")

@bp.route("/<int:sid>/delete", methods=["POST"])
def delete(sid: int):
    db.delete_scheduled_post(sid)
    flash("Удалено", "info")
    return redirect(url_for("scheduled.list_"))

@bp.route("/post_now/<int:pid>", methods=["POST"])
def post_now(pid: int):
    ok = db.post_product_to_channel(pid, caption=request.form.get("caption") or None)
    flash("Отправлено" if ok else "Не удалось отправить (проверь токен/канал)", "success" if ok else "warning")
    return redirect(request.referrer or url_for("scheduled.list_"))
