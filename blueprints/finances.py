
from flask import Blueprint, render_template
from db import DataStore
from utils.auth import require_role

bp = Blueprint("finances", __name__)
db = DataStore()

@bp.route("/")
def summary():
    # На базовом уровне используем те же KPI — далее можно расширить
    kpis = db.kpis()
    return render_template("finances/summary.html", kpis=kpis)


@bp.route("/period")
def period():
    from flask import request, render_template
    import datetime
    df = request.args.get("date_from"); dt = request.args.get("date_to")
    date_from = datetime.date.fromisoformat(df) if df else datetime.date.today().replace(day=1)
    date_to = datetime.date.fromisoformat(dt) if dt else datetime.date.today()
    comm = request.args.get("comm", type=float)
    data = db.finance_summary(date_from=date_from, date_to=date_to, commission_rate=comm)
    return render_template("finances/period.html", data=data, date_from=date_from.isoformat(), date_to=date_to.isoformat(), comm=comm)
