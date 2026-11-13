import os
import hmac
from datetime import date
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session

from model import Inputs, run, SCENARIOS

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

USERNAME = "test"
PASSWORD = "test"


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@app.template_filter("money")
def money(value):
    try:
        v = round(float(value))
    except (TypeError, ValueError):
        return "-"
    return f"-${abs(v):,}" if v < 0 else f"${v:,}"


@app.template_filter("pct")
def pct(value, digits=0):
    return f"{float(value) * 100:.{digits}f}%"


def _num(name, default, lo, hi, errors, label, integer=False):
    raw = request.args.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        val = float(raw.replace(",", "").replace("$", ""))
    except ValueError:
        errors.append(f"{label} must be a number - using {default:,} instead.")
        return default
    if not (lo <= val <= hi):
        errors.append(f"{label} must be between {lo:,} and {hi:,} - using {default:,} instead.")
        return default
    return int(val) if integer else val


def read_inputs(today):
    d = Inputs()
    e = []
    p = Inputs(
        purchase_price=_num("purchase_price", d.purchase_price, 1, 100_000_000, e, "Purchase price"),
        purchase_year=_num("purchase_year", d.purchase_year, 1950, today.year, e, "Year of purchase", True),
        purchase_costs=_num("purchase_costs", d.purchase_costs, 0, 10_000_000, e, "Purchase costs"),
        current_price=_num("current_price", d.current_price, 1, 100_000_000, e, "Current price"),
        renovation=_num("renovation", d.renovation, 0, 10_000_000, e, "Renovation and cleaning cost"),
        agent_pct=_num("agent_pct", d.agent_pct, 0, 10, e, "Agent fees (%)"),
        sale_year=_num("sale_year", d.sale_year, 2027, 2070, e, "Year of sale", True),
        other_income=_num("other_income", d.other_income, 0, 100_000_000, e, "Other income"),
        g_conservative=_num("g_conservative", d.g_conservative, -10, 20, e, "Conservative growth"),
        g_realistic=_num("g_realistic", d.g_realistic, -10, 20, e, "Realistic growth"),
        g_optimistic=_num("g_optimistic", d.g_optimistic, -10, 20, e, "Optimistic growth"),
        cpi=_num("cpi", d.cpi, 0, 15, e, "CPI assumption"),
    )
    if p.purchase_year > p.sale_year:
        e.append("Year of purchase is after the year of sale - please check these.")
    return p, e


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        u = request.form.get("username", "")
        pw = request.form.get("password", "")
        ok = hmac.compare_digest(u.encode(), USERNAME.encode()) & hmac.compare_digest(pw.encode(), PASSWORD.encode())
        if ok:
            session["user"] = u
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("index"))
        error = "Those details don't match. Please try again."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    today = date.today()
    p, errors = read_inputs(today)
    result = run(p, today)
    return render_template(
        "index.html", p=p, r=result, errors=errors, scenarios=SCENARIOS, today=today, active="sale"
    )


@app.route("/rental")
@login_required
def rental():
    return render_template("rental.html", active="rental")


@app.route("/healthz")
def healthz():
    return "ok"


if __name__ == "__main__":
    app.run(debug=True)
