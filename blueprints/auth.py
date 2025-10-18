
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import os

bp = Blueprint("auth", __name__)

def _role_for(password: str) -> str|None:
    if password == os.getenv("ADMIN_PASSWORD", "admin123"):
        return "admin"
    if password == os.getenv("MANAGER_PASSWORD", "manager123"):
        return "manager"
    if password == os.getenv("SUPPORT_PASSWORD", "support123"):
        return "support"
    return None

@bp.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        role = _role_for(request.form.get("password",""))
        if role:
            session["role"] = role
            flash("Вход выполнен", "success")
            return redirect(url_for("analytics.dashboard"))
        flash("Неверный пароль", "danger")
    return render_template("layouts/login.html")

@bp.route("/logout")
def logout():
    session.clear()
    flash("Вы вышли из системы", "info")
    return redirect(url_for("auth.login"))
