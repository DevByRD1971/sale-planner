import os
import hmac
from datetime import date
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session

from model import Inputs, run, SCENARIOS
from rental_model import RentalInputs, compute as rental_compute
from super_model import SuperInputs, project as super_project

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


def read_rental():
    d = RentalInputs()
    e = []
    n = lambda name, default, label, lo=0, hi=100_000_000: _num(name, default, lo, hi, e, label)
    status = request.args.get("status", d.status)
    if status not in ("before", "after", "new"):
        status = d.status
    fy = int(_num("tax_fy", d.tax_fy, 2027, 2028, e, "Tax year", True))
    r = RentalInputs(
        weekly_rent=n("weekly_rent", d.weekly_rent, "Rent per week", 0, 100_000),
        vacant_weeks=n("vacant_weeks", d.vacant_weeks, "Vacant weeks", 0, 52),
        agent_pct=n("agent_pct", d.agent_pct, "Agent fee (%)", 0, 30),
        mgmt_extra=n("mgmt_extra", d.mgmt_extra, "Additional management expenses"),
        council=n("council", d.council, "Council rates"),
        esl=n("esl", d.esl, "Emergency Services Levy"),
        water=n("water", d.water, "Water"),
        insurance=n("insurance", d.insurance, "Insurance"),
        building_mgmt=n("building_mgmt", d.building_mgmt, "Building management"),
        repairs=n("repairs", d.repairs, "General repairs"),
        land_tax=n("land_tax", d.land_tax, "Land tax"),
        loan=n("loan", d.loan, "Bank loan"),
        rate=n("rate", d.rate, "Loan interest rate (%)", 0, 30),
        depreciation=n("depreciation", d.depreciation, "Depreciation"),
        salary=n("salary", d.salary, "Annual taxable income"),
        tax_fy=fy,
        status=status,
        property_value=n("property_value", d.property_value, "Property value", 0, 100_000_000),
    )
    return r, e


@app.route("/rental")
@login_required
def rental():
    r, errors = read_rental()
    return render_template("rental.html", r=r, c=rental_compute(r), errors=errors, active="rental")


def read_super():
    d = SuperInputs()
    e = []
    n = lambda name, default, label, lo=0, hi=100_000_000, integer=False: _num(
        name, default, lo, hi, e, label, integer)
    age = n("age", d.age, "Current age", 16, 90, True)
    s = SuperInputs(
        balance=n("balance", d.balance, "Super balance"),
        salary=n("salary", d.salary, "Salary"),
        employer_pct=n("employer_pct", d.employer_pct, "Employer contribution (%)", 0, 50),
        personal=n("personal", d.personal, "Personal contribution"),
        age=age,
        retire_age=n("retire_age", d.retire_age, "Retirement age", 16, 100, True),
        show_until=n("show_until", d.show_until, "Show projection until age", 17, 100, True),
        contrib_tax=n("contrib_tax", d.contrib_tax, "Contributions tax (%)", 0, 50),
        salary_growth=n("salary_growth", d.salary_growth, "Salary growth (%)", -10, 20),
    )
    if s.show_until <= s.age:
        s.show_until = s.age + 1
        e.append("The projection must run past your current age, so it was extended by one year.")
    if s.show_until - s.age > 60:
        s.show_until = s.age + 60
        e.append("The table is limited to 60 years.")
    return s, e


@app.route("/super")
@login_required
def superannuation():
    s, errors = read_super()
    return render_template(
        "super.html", s=s, t=super_project(s, date.today()), errors=errors, active="super"
    )


@app.route("/healthz")
def healthz():
    return "ok"


if __name__ == "__main__":
    app.run(debug=True)
