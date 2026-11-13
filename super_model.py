"""Superannuation projection: balance at 30 June each financial year for several growth rates.

Each year:  balance = previous balance x (1 + growth) + contributions x (1 + growth / 2)
(contributions arrive through the year, so they earn about half a year of growth).
Growth rates are treated as the net return after investment fees and earnings tax.
"""
from dataclasses import dataclass
from datetime import date

RATES = list(range(3, 13))          # 3% ... 12%
HIGHLIGHT = (4, 7, 10)              # rates shown in the cards and chart


@dataclass
class SuperInputs:
    balance: float = 500_000        # balance at the last 30 June
    salary: float = 150_000
    employer_pct: float = 13.0      # employer contribution, % of salary
    personal: float = 0.0           # extra personal contribution per year ($)
    age: int = 55
    retire_age: int = 60            # contributions stop after the year you reach this age
    show_until: int = 67
    contrib_tax: float = 15.0       # tax the fund takes from employer contributions
    salary_growth: float = 0.0      # % a year


def project(p: SuperInputs, today: date):
    first_fy = today.year + (1 if today.month >= 7 else 0)   # FY ending 30 June, e.g. 2027
    years = max(p.show_until - p.age, 1)

    balances = {r: p.balance for r in RATES}
    rows = [{
        "fy": first_fy - 1, "age": p.age, "contrib": None, "start": True,
        "balances": dict(balances),
    }]
    total_contrib = 0.0
    retire_row = None

    for i in range(1, years + 1):
        age = p.age + i
        working = age <= p.retire_age
        salary_i = p.salary * (1 + p.salary_growth / 100) ** (i - 1)
        employer = salary_i * p.employer_pct / 100 if working else 0.0
        net_employer = employer * (1 - p.contrib_tax / 100)
        personal = p.personal if working else 0.0
        contrib = net_employer + personal
        total_contrib += contrib

        for r in RATES:
            g = r / 100
            balances[r] = balances[r] * (1 + g) + contrib * (1 + g / 2)

        row = {
            "fy": first_fy + i - 1, "age": age, "contrib": contrib, "start": False,
            "working": working, "retire": age == p.retire_age,
            "balances": dict(balances),
        }
        rows.append(row)
        if age == p.retire_age:
            retire_row = row

    return {
        "rows": rows,
        "rates": RATES,
        "highlight": HIGHLIGHT,
        "retire_row": retire_row,
        "total_contrib_to_retire": sum(
            (r["contrib"] or 0) for r in rows if not r["start"] and r["age"] <= p.retire_age
        ),
        "first_fy": first_fy,
    }
