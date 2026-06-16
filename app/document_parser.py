from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.metrics import dilution_ratio, equity_ratio, sales_ratio


@dataclass(frozen=True)
class ExtractedMetrics:
    contract_amount: float | None = None
    recent_sales: float | None = None
    sales_ratio: float | None = None
    treasury_buyback_amount: float | None = None
    facility_investment_amount: float | None = None
    equity_capital: float | None = None
    equity_ratio: float | None = None
    new_share_count: float | None = None
    existing_share_count: float | None = None
    dilution_ratio: float | None = None
    details: dict[str, Any] = field(default_factory=dict)


def parse_number(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = value.replace(",", "").replace("%", "").strip()
    if cleaned in {"", "-", "해당사항없음", "해당사항 없음"}:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    return float(match.group(0))


def document_lines(document_text: str) -> list[str]:
    return [line.strip() for line in document_text.splitlines() if line.strip()]


def lines_from_label(lines: list[str], label: str) -> list[str]:
    normalized_label = label.replace(" ", "")
    for index, line in enumerate(lines):
        if line.replace(" ", "") == normalized_label:
            return lines[index:]
    for index, line in enumerate(lines):
        if normalized_label in line.replace(" ", ""):
            return lines[index:]
    return lines


def value_after_label(lines: list[str], labels: list[str]) -> str | None:
    normalized_labels = [label.replace(" ", "") for label in labels]
    for index, line in enumerate(lines):
        normalized_line = line.replace(" ", "")
        if any(label in normalized_line for label in normalized_labels):
            for candidate in lines[index + 1 : index + 6]:
                if candidate and not any(label in candidate.replace(" ", "") for label in normalized_labels):
                    return candidate
    return None


def value_after_sequence(lines: list[str], labels: list[str]) -> str | None:
    if not labels:
        return None
    normalized_labels = [label.replace(" ", "") for label in labels]
    for start in range(len(lines)):
        cursor = start
        matched = True
        for label in normalized_labels:
            while cursor < len(lines) and label not in lines[cursor].replace(" ", ""):
                cursor += 1
            if cursor >= len(lines):
                matched = False
                break
            cursor += 1
        if matched:
            for candidate in lines[cursor : cursor + 6]:
                if candidate and candidate != "-":
                    return candidate
    return None


def number_after_label(lines: list[str], labels: list[str]) -> float | None:
    return parse_number(value_after_label(lines, labels))


def number_after_sequence(lines: list[str], labels: list[str]) -> float | None:
    return parse_number(value_after_sequence(lines, labels))


def extract_metrics(report_name: str, document_text: str) -> ExtractedMetrics:
    lines = document_lines(document_text)
    normalized_report = report_name.replace(" ", "")

    if "단일판매" in normalized_report or "공급계약" in normalized_report:
        return extract_supply_contract_metrics(lines)
    if "유상증자" in normalized_report:
        return extract_paid_capital_increase_metrics(lines)
    if "전환사채" in normalized_report:
        return extract_convertible_bond_metrics(lines)
    if "전환가액의조정" in normalized_report or "전환가액조정" in normalized_report:
        return extract_conversion_price_adjustment_metrics(lines)
    if "자기주식취득" in normalized_report:
        return extract_treasury_stock_metrics(lines)
    if "신규시설투자" in normalized_report:
        return extract_facility_investment_metrics(lines)

    return ExtractedMetrics()


def extract_supply_contract_metrics(lines: list[str]) -> ExtractedMetrics:
    contract_amount = number_after_label(lines, ["계약금액 총액(원)", "계약금액(원)", "확정 계약금액"])
    recent_sales = number_after_label(lines, ["최근 매출액(원)"])
    reported_sales_ratio = number_after_label(lines, ["매출액 대비(%)", "매출액대비(%)"])
    computed_sales_ratio = sales_ratio(contract_amount, recent_sales)
    counterparty = value_after_label(lines, ["계약상대방", "계약상대"])
    start_date = value_after_label(lines, ["시작일"])
    end_date = value_after_label(lines, ["종료일"])

    return ExtractedMetrics(
        contract_amount=contract_amount,
        recent_sales=recent_sales,
        sales_ratio=reported_sales_ratio or computed_sales_ratio,
        details={
            "contract_counterparty": counterparty,
            "contract_start_date": start_date,
            "contract_end_date": end_date,
        },
    )


def extract_paid_capital_increase_metrics(lines: list[str]) -> ExtractedMetrics:
    lines = lines_from_label(lines, "유상증자 결정")
    new_share_count = number_after_sequence(lines, ["신주의 종류와 수", "보통주식"])
    existing_share_count = number_after_sequence(lines, ["증자전 발행주식총수", "보통주식"])
    issue_price = number_after_sequence(lines, ["신주 발행가액", "보통주식"])
    facility_funds = number_after_label(lines, ["시설자금 (원)", "시설자금"])
    operating_funds = number_after_label(lines, ["운영자금 (원)", "운영자금"])
    debt_repayment_funds = number_after_label(lines, ["채무상환자금 (원)", "채무상환자금"])
    other_funds = number_after_label(lines, ["기타자금 (원)", "기타자금"])
    issue_amount = sum(
        value or 0
        for value in [facility_funds, operating_funds, debt_repayment_funds, other_funds]
    ) or None

    details = {
        "issue_price": issue_price,
        "issue_amount": issue_amount,
        "facility_funds": facility_funds,
        "operating_funds": operating_funds,
        "debt_repayment_funds": debt_repayment_funds,
        "other_funds": other_funds,
        "capital_increase_method": value_after_label(lines, ["증자방식"]),
        "payment_date": value_after_label(lines, ["납입일"]),
        "listing_date": value_after_label(lines, ["신주의 상장 예정일"]),
    }
    return ExtractedMetrics(
        new_share_count=new_share_count,
        existing_share_count=existing_share_count,
        dilution_ratio=compute_dilution(new_share_count, existing_share_count),
        details=details,
    )


def extract_treasury_stock_metrics(lines: list[str]) -> ExtractedMetrics:
    lines = lines_from_label(lines, "자기주식 취득 결정")
    treasury_share_count = number_after_sequence(lines, ["취득예정주식", "보통주식"])
    treasury_amount = number_after_sequence(lines, ["취득예정금액", "보통주식"])
    start_date = value_after_label(lines, ["시작일"])
    end_date = value_after_label(lines, ["종료일"])
    return ExtractedMetrics(
        treasury_buyback_amount=treasury_amount,
        details={
            "treasury_share_count": treasury_share_count,
            "treasury_start_date": start_date,
            "treasury_end_date": end_date,
        },
    )


def extract_convertible_bond_metrics(lines: list[str]) -> ExtractedMetrics:
    issue_amount = number_after_label(lines, ["사채의 권면(전자등록)총액", "사채의 권면총액"])
    conversion_price = number_after_label(lines, ["전환가액", "전환가격"])
    conversion_start = value_after_label(lines, ["전환청구기간", "시작일"])
    conversion_end = value_after_label(lines, ["종료일"])

    return ExtractedMetrics(
        details={
            "issue_amount": issue_amount,
            "conversion_price": conversion_price,
            "conversion_start_date": conversion_start,
            "conversion_end_date": conversion_end,
        }
    )


def extract_conversion_price_adjustment_metrics(lines: list[str]) -> ExtractedMetrics:
    before_price, after_price = extract_two_numbers_after_headers(
        lines,
        ["조정전 전환가액", "조정후 전환가액"],
    )
    before_shares, after_shares = extract_two_numbers_after_headers(
        lines,
        ["조정전 전환가능 주식수", "조정후 전환가능 주식수"],
        skip_large_amount=True,
    )
    bond_amount = number_after_label(lines, ["미전환사채의 권면(전자등록)총액", "미전환사채의 권면총액"])

    return ExtractedMetrics(
        new_share_count=after_shares,
        details={
            "bond_amount": bond_amount,
            "conversion_price_before": before_price,
            "conversion_price_after": after_price,
            "convertible_shares_before": before_shares,
            "convertible_shares_after": after_shares,
            "adjustment_reason": value_after_label(lines, ["조정사유"]),
            "adjustment_effective_date": value_after_label(lines, ["조정가액 적용일"]),
        },
    )


def extract_two_numbers_after_headers(
    lines: list[str],
    headers: list[str],
    *,
    skip_large_amount: bool = False,
    min_value: float = 100,
) -> tuple[float | None, float | None]:
    normalized_headers = [header.replace(" ", "") for header in headers]
    for index in range(len(lines)):
        normalized_line = lines[index].replace(" ", "")
        if normalized_headers[0] not in normalized_line:
            continue
        window = lines[index + 1 : index + 20]
        if not any(normalized_headers[1] in line.replace(" ", "") for line in window[:4]):
            continue
        numbers = []
        for candidate in window:
            normalized_candidate = candidate.replace(" ", "")
            if numbers and (
                re.match(r"^\d+\.", candidate)
                or "전환가능" in normalized_candidate
                or "조정사유" in normalized_candidate
            ):
                break
            value = parse_number(candidate)
            if value is None:
                continue
            if skip_large_amount and value >= 100_000_000:
                continue
            if value < min_value:
                continue
            numbers.append(value)
        if len(numbers) >= 2:
            return numbers[0], numbers[1]
    return None, None


def extract_facility_investment_metrics(lines: list[str]) -> ExtractedMetrics:
    investment_amount = number_after_label(lines, ["투자금액(원)", "투자금액"])
    equity_capital = number_after_label(lines, ["자기자본(원)", "자기자본"])
    reported_equity_ratio = number_after_label(lines, ["자기자본대비(%)", "자기자본 대비(%)"])
    computed_equity_ratio = equity_ratio(investment_amount, equity_capital)
    investment_purpose = value_after_label(lines, ["투자목적"])

    return ExtractedMetrics(
        facility_investment_amount=investment_amount,
        equity_capital=equity_capital,
        equity_ratio=reported_equity_ratio or computed_equity_ratio,
        details={"investment_purpose": investment_purpose},
    )


def compute_dilution(new_share_count: float | None, existing_share_count: float | None) -> float | None:
    return dilution_ratio(new_share_count, existing_share_count)
