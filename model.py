"""Property sale + capital gains tax model (Australian resident, investment property).

Rules modelled
--------------
* Sale on or before 30 June 2027  -> 50% CGT discount on the whole gain.
* Sale after 1 July 2027          -> 2026-27 Budget CGT reform (passed Parliament June 2026):
    - gain up to the market value on 1 July 2027 keeps the 50% discount
    - gain after 1 July 2027 is "real" (value above the CPI-indexed 1 July 2027 value)
      and is taxed at your marginal rate, but never less than 30% (minimum tax)
* Resident income tax rates: 2026-27 (15% second bracket), 14% from 2027-28.
  Brackets held flat.
* 2% Medicare levy added on the taxable gain.

All of this is a planning estimate, not tax advice.
"""
from dataclasses import dataclass
from datetime import date

TRANSITION = date(2027, 7, 1)
MEDICARE = 0.02
MIN_TAX = 0.30
DISCOUNT = 0.5

SCENARIOS = ("Conservative", "Realistic", "Optimistic")


@dataclass
class Inputs:
    purchase_price: float = 300_000
    purchase_year: int = 2015
    purchase_costs: float = 0          # stamp duty, legal fees paid when buying
    current_price: float = 500_000
    renovation: float = 15_000
    agent_pct: float = 2.5             # agent commission + marketing, % of sale price
    sale_year: int = 2030
    other_income: float = 10_000
    g_conservative: float = 3.0        # % p.a.
    g_realistic: float = 5.0
    g_optimistic: float = 7.0
    cpi: float = 2.5                   # % p.a. used for indexation


def financial_year(d: date) -> int:
    """Financial year ending 30 June (e.g. 15 Nov 2026 -> 2027)."""
    return d.year + (1 if d.month >= 7 else 0)


def brackets_for(fy):
    """(upper limit, rate) for the financial year ending 30 June of `fy`."""
    r2 = 0.14 if fy >= 2028 else 0.15
    return [(18_200, 0.0), (45_000, r2), (135_000, 0.30), (190_000, 0.37), (float("inf"), 0.45)]


def bracket_rows(fy):
    rows, lower = [], 0
    for upper, rate in brackets_for(fy):
        rows.append({"lower": lower, "upper": upper, "rate": rate})
        lower = upper
    return rows


def tax_on(income, fy):
    tax, lower = 0.0, 0.0
    for upper, rate in brackets_for(fy):
        if income > lower:
            tax += (min(income, upper) - lower) * rate
        lower = upper
    return tax


def allocate(base, amount, fy):
    """How much of `amount`, stacked on top of `base` income, lands in each bracket."""
    out, lower = [], 0
    for upper, rate in brackets_for(fy):
        start, end = max(base, lower), min(base + amount, upper)
        out.append(max(0.0, end - start))
        lower = upper
    return out


def value_at(current, growth_pct, when, today):
    years = max((when - today).days / 365.25, 0)
    return current * (1 + growth_pct / 100) ** years


def evaluate(p: Inputs, growth_pct: float, sale_date: date, today: date):
    fy = financial_year(sale_date)
    sale_price = value_at(p.current_price, growth_pct, sale_date, today)
    v2027 = value_at(p.current_price, growth_pct, TRANSITION, today)

    agent_fees = sale_price * p.agent_pct / 100
    selling_costs = agent_fees + p.renovation
    cost_base = p.purchase_price + p.purchase_costs
    profit_before_tax = sale_price - selling_costs - cost_base

    base = p.other_income
    new_rules = sale_date >= TRANSITION
    pre_gain = post_nominal = real_post = indexed_base = 0.0

    if not new_rules:
        pre_adj = max(profit_before_tax, 0.0)
    else:
        n = (sale_date - TRANSITION).days / 365.25
        pre_gain = v2027 - cost_base
        post_nominal = (sale_price - selling_costs) - v2027
        indexed_base = v2027 * (1 + p.cpi / 100) ** n
        real_post = max(0.0, (sale_price - selling_costs) - indexed_base)
        if post_nominal < 0:                       # a real loss after 2027 offsets the older gain
            real_post = 0.0
            pre_adj = max(pre_gain + post_nominal, 0.0)
        else:
            pre_adj = max(pre_gain, 0.0)
            if pre_gain < 0:                       # older loss offsets the newer gain
                real_post = max(0.0, real_post + pre_gain)

    pre_taxable = pre_adj * DISCOUNT
    taxable_gain = pre_taxable + real_post

    tax_pre = tax_on(base + pre_taxable, fy) - tax_on(base, fy)
    tax_post = tax_on(base + taxable_gain, fy) - tax_on(base + pre_taxable, fy)
    bracket_tax = tax_pre + tax_post
    min_tax_amount = MIN_TAX * real_post
    topup = max(0.0, min_tax_amount - tax_post) if real_post > 0 else 0.0
    if topup < 0.5:
        topup = 0.0
    medicare = MEDICARE * taxable_gain
    cgt = bracket_tax + topup + medicare

    alloc = allocate(base, taxable_gain, fy)
    rows = bracket_rows(fy)
    top_idx = 0
    for i, amt in enumerate(alloc):
        if amt > 0:
            top_idx = i
    if taxable_gain <= 0:
        top_idx = next(i for i, r in enumerate(rows) if base <= r["upper"])
    top_rate = rows[top_idx]["rate"]

    return {
        "growth": growth_pct,
        "sale_price": sale_price,
        "v2027": v2027,
        "agent_fees": agent_fees,
        "renovation": p.renovation,
        "selling_costs": selling_costs,
        "cost_base": cost_base,
        "profit_before_tax": profit_before_tax,
        "new_rules": new_rules,
        "pre_gain": pre_gain if new_rules else profit_before_tax,
        "pre_taxable": pre_taxable,
        "indexed_base": indexed_base,
        "real_post": real_post,
        "tax_post": tax_post,
        "min_tax_amount": min_tax_amount,
        "taxable_gain": taxable_gain,
        "total_taxable_income": base + taxable_gain,
        "alloc": alloc,
        "bracket_tax": bracket_tax,
        "topup": topup,
        "medicare": medicare,
        "cgt": cgt,
        "top_rate": top_rate,
        "effective_rate": (cgt / profit_before_tax) if profit_before_tax > 0 else 0.0,
        "net_profit": profit_before_tax - cgt,
        "cash_after_tax": sale_price - selling_costs - cgt,
    }


def run(p: Inputs, today: date):
    growth = {
        "Conservative": p.g_conservative,
        "Realistic": p.g_realistic,
        "Optimistic": p.g_optimistic,
    }
    final_date = date(p.sale_year, 6, 30)
    final = {k: evaluate(p, g, final_date, today) for k, g in growth.items()}

    # Year-by-year: a sale today, then the chosen year of sale and the next three years.
    points = [(f"Now ({today.year})", today)]
    points += [(str(y), date(y, 6, 30)) for y in range(p.sale_year, p.sale_year + 4)]
    table = []
    for label, d in points:
        row = {"year": label}
        for k, g in growth.items():
            r = evaluate(p, g, d, today)
            row[k] = {"price": r["sale_price"], "cgt": r["cgt"], "net": r["net_profit"]}
        table.append(row)

    years_held = max(today.year - p.purchase_year, 1)
    hist = (p.current_price / p.purchase_price) ** (1 / years_held) - 1 if p.purchase_price > 0 else 0
    return {
        "final": final,
        "table": table,
        "bracket_rows": bracket_rows(financial_year(final_date)),
        "hist_growth": hist * 100,
        "gain_to_date": p.current_price - p.purchase_price,
        "years_held": years_held,
    }
