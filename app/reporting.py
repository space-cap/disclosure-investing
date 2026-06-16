from __future__ import annotations

from pathlib import Path
from typing import Iterable


def is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        if value != value:
            return True
    except TypeError:
        pass
    return str(value) in {"nan", "NaN", "NaT", "<NA>"}


def money(value: float | int | None) -> str:
    if is_missing(value):
        return "-"
    number = float(value)
    if abs(number) >= 100_000_000:
        return f"{number / 100_000_000:,.1f}억"
    if abs(number) >= 10_000:
        return f"{number / 10_000:,.0f}만"
    return f"{number:,.0f}"


def percent(value: float | int | None) -> str:
    if is_missing(value):
        return "-"
    return f"{float(value):,.2f}%"


def build_daily_report(rows: Iterable[dict], target_date: str) -> str:
    rows = list(rows)
    risk_rows = [row for row in rows if row.get("rule_category") == "risk" or row.get("ai_category") == "risk"]
    event_rows = [row for row in rows if row.get("rule_category") == "short_term_event" or row.get("ai_category") == "short_term_event"]
    long_rows = [row for row in rows if row.get("rule_category") == "long_term_candidate" or row.get("ai_category") == "long_term_candidate"]
    manual_rows = [row for row in rows if row.get("recommended_action") in {"manual_review", "hold_for_more_data"}]

    lines = [
        f"# 일일 공시 요약 - {target_date}",
        "",
        "## 요약",
        "",
        f"- 전체 공시: {len(rows)}건",
        f"- 위험 공시: {len(risk_rows)}건",
        f"- 단기 이벤트 후보: {len(event_rows)}건",
        f"- 중장기 관심 후보: {len(long_rows)}건",
        f"- 수동검토/추가정보 대기: {len(manual_rows)}건",
        "",
    ]

    append_section(lines, "위험 공시", risk_rows)
    append_section(lines, "단기 이벤트 후보", event_rows)
    append_section(lines, "중장기 관심 후보", long_rows)
    append_section(lines, "수동검토 필요", manual_rows)

    return "\n".join(lines).strip() + "\n"


def append_section(lines: list[str], title: str, rows: list[dict]) -> None:
    lines.extend([f"## {title}", ""])
    if not rows:
        lines.extend(["- 해당 없음", ""])
        return

    for row in rows[:20]:
        metrics = metric_summary(row)
        summary = row.get("summary") or row.get("reason") or ""
        lines.append(
            f"- **{row.get('corp_name')}** `{row.get('stock_code') or '-'}`: "
            f"{row.get('report_name')} "
            f"[{row.get('recommended_action') or '-'} / {row.get('risk_level') or '-'}]"
        )
        if metrics:
            lines.append(f"  - 숫자: {metrics}")
        if summary:
            lines.append(f"  - 근거: {summary}")
        if row.get("dart_url"):
            lines.append(f"  - DART: {row.get('dart_url')}")
    lines.append("")


def metric_summary(row: dict) -> str:
    parts = []
    if not is_missing(row.get("contract_amount")):
        parts.append(f"계약금액 {money(row.get('contract_amount'))}")
    if not is_missing(row.get("sales_ratio")):
        parts.append(f"매출대비 {percent(row.get('sales_ratio'))}")
    if not is_missing(row.get("treasury_buyback_amount")):
        parts.append(f"자사주 {money(row.get('treasury_buyback_amount'))}")
    if not is_missing(row.get("new_share_count")):
        parts.append(f"신주수 {money(row.get('new_share_count'))}주")
    if not is_missing(row.get("dilution_ratio")):
        parts.append(f"희석률 {percent(row.get('dilution_ratio'))}")
    if not is_missing(row.get("equity_ratio")):
        parts.append(f"자기자본대비 {percent(row.get('equity_ratio'))}")
    return ", ".join(parts)


def write_report(report_text: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_text, encoding="utf-8")
