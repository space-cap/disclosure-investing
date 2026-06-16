from __future__ import annotations


def ratio_percent(numerator: float | int | None, denominator: float | int | None) -> float | None:
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    return round((float(numerator) / float(denominator)) * 100, 2)


def sales_ratio(contract_amount: float | int | None, recent_sales: float | int | None) -> float | None:
    return ratio_percent(contract_amount, recent_sales)


def equity_ratio(amount: float | int | None, equity_capital: float | int | None) -> float | None:
    return ratio_percent(amount, equity_capital)


def dilution_ratio(new_share_count: float | int | None, existing_share_count: float | int | None) -> float | None:
    return ratio_percent(new_share_count, existing_share_count)

