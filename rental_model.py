"""Rental property gearing and tax position (annual figures, Australian resident).

Gearing is judged on the tax result: rent minus ALL deductible costs, including
loan interest and depreciation. Cash flow is shown separately because depreciation
is a deduction you don't actually pay out.

Negative gearing rule modelled (Budget 2026-27, reported as passed June 2026):
from 1 July 2027, losses on ESTABLISHED residential property bought after 12 May 2026
can no longer be deducted against salary (they are carried forward instead).
Properties bought before then, and new builds, keep the normal treatment.
"""
from dataclasses import dataclass

from model import brackets_for, bracket_rows, tax_on, allocate, MEDICARE


@dataclass
class RentalInputs:
    weekly_rent: float = 600
    vacant_weeks: float = 0
    agent_pct: float = 7.0          # % of rent collected (incl. GST), typical 5-8%
    mgmt_extra: float = 1200        # letting fee share, advertising, inspections, admin
    council: float = 1800
    esl: float = 150
    water: float = 700
    insurance: float = 1000
    building_mgmt: float = 3000
    repairs: float = 1000
    land_tax: float = 400
    loan: float = 560_000
    rate: float = 5.6
    depreciation: float = 5000
    salary: float = 150_000
    tax_fy: int = 2027              # 2027 = 2026-27, 2028 = 2027-28 onwards
    status: str = "before"          # before | after | new
    property_value: float = 500_000


def compute(r: RentalInputs):
    weeks = max(52 - r.vacant_weeks, 0)
    gross = r.weekly_rent * weeks
    agent_fee = gross * r.agent_pct / 100
    mgmt_total = agent_fee + r.mgmt_extra
    interest = r.loan * r.rate / 100

    other = [
        ("Council rates", r.council),
        ("Emergency Services Levy", r.esl),
        ("Water", r.water),
        ("Insurance", r.insurance),
        ("Building management", r.building_mgmt),
        ("General repairs", r.repairs),
        ("Land tax", r.land_tax),
    ]
    other_total = sum(v for _, v in other)

    cash_costs = mgmt_total + other_total + interest
    total_deductions = cash_costs + r.depreciation
    net_rental = gross - total_deductions          # tax result
    cash_before_tax = gross - cash_costs           # what actually hits your bank account

    if net_rental > 0.5:
        gearing = "positive"
    elif net_rental < -0.5:
        gearing = "negative"
    else:
        gearing = "neutral"

    fy = r.tax_fy
    quarantined = gearing == "negative" and r.status == "after" and fy >= 2028
    taxable_rental = 0.0 if quarantined else net_rental

    tax_without = tax_on(r.salary, fy)
    medicare_without = MEDICARE * r.salary
    tax_with = tax_on(r.salary + taxable_rental, fy)
    medicare_with = MEDICARE * (r.salary + taxable_rental)
    total_without = tax_without + medicare_without
    total_with = tax_with + medicare_with
    tax_effect = total_with - total_without         # + extra tax, - refund / saving

    after_tax_cash = cash_before_tax - tax_effect

    rows = bracket_rows(fy)

    def rate_at(income):
        for row in rows:
            if income <= row["upper"]:
                return row["rate"]
        return rows[-1]["rate"]

    marginal_salary = rate_at(r.salary)
    marginal_with = rate_at(r.salary + taxable_rental)

    # break-even rents (per week): one where the bank account balances, one where the tax result is zero
    fixed_cash = r.mgmt_extra + other_total + interest
    keep = (1 - r.agent_pct / 100) * weeks if weeks else 0
    be_cash = fixed_cash / keep if keep else 0
    be_tax = (fixed_cash + r.depreciation) / keep if keep else 0

    yield_gross = gross / r.property_value * 100 if r.property_value else 0
    yield_net = (gross - mgmt_total - other_total) / r.property_value * 100 if r.property_value else 0
    lvr = r.loan / r.property_value * 100 if r.property_value else 0

    groups = [
        ("Management fees", mgmt_total),
        ("Loan interest", interest),
        ("Rates, levies, water, land tax", r.council + r.esl + r.water + r.land_tax),
        ("Insurance", r.insurance),
        ("Building management", r.building_mgmt),
        ("Repairs", r.repairs),
        ("Depreciation (non-cash)", r.depreciation),
    ]

    return {
        "weeks": weeks,
        "gross": gross,
        "agent_fee": agent_fee,
        "mgmt_extra": r.mgmt_extra,
        "mgmt_total": mgmt_total,
        "other": other,
        "other_total": other_total,
        "interest": interest,
        "depreciation": r.depreciation,
        "cash_costs": cash_costs,
        "total_deductions": total_deductions,
        "net_rental": net_rental,
        "cash_before_tax": cash_before_tax,
        "gearing": gearing,
        "quarantined": quarantined,
        "taxable_rental": taxable_rental,
        "tax_without": total_without,
        "tax_with": total_with,
        "tax_effect": tax_effect,
        "after_tax_cash": after_tax_cash,
        "marginal_salary": marginal_salary,
        "marginal_with": marginal_with,
        "bracket_rows": rows,
        "alloc_without": allocate(0, r.salary, fy),
        "alloc_with": allocate(0, max(r.salary + taxable_rental, 0), fy),
        "be_cash": be_cash,
        "be_tax": be_tax,
        "yield_gross": yield_gross,
        "yield_net": yield_net,
        "lvr": lvr,
        "expense_ratio": (cash_costs / gross * 100) if gross else 0,
        "interest_share": (interest / gross * 100) if gross else 0,
        "groups": groups,
    }
