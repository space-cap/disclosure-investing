from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from openai import OpenAI


CLASSIFICATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "primary_category": {
            "type": "string",
            "enum": [
                "short_term_event",
                "long_term_candidate",
                "risk",
                "manual_review",
                "ignore",
            ],
        },
        "event_type": {
            "type": "string",
            "enum": [
                "supply_contract",
                "treasury_stock",
                "stock_retirement",
                "bonus_issue",
                "dividend",
                "earnings_guidance",
                "facility_investment",
                "regular_report",
                "ir_event",
                "insider_buying",
                "major_shareholder_change_positive",
                "paid_capital_increase",
                "convertible_bond",
                "bond_with_warrant",
                "conversion_price_adjustment",
                "capital_reduction",
                "largest_shareholder_change",
                "audit_opinion_risk",
                "delisting_risk",
                "embezzlement_breach",
                "unknown",
            ],
        },
        "sentiment": {
            "type": "string",
            "enum": ["positive", "neutral", "negative", "mixed", "unknown"],
        },
        "risk_level": {
            "type": "string",
            "enum": ["low", "medium", "high", "unknown"],
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
        },
        "summary": {
            "type": "string",
            "maxLength": 300,
        },
        "reason": {
            "type": "string",
            "maxLength": 500,
        },
        "watch_points": {
            "type": "array",
            "items": {"type": "string", "maxLength": 120},
            "minItems": 1,
            "maxItems": 6,
        },
        "recommended_action": {
            "type": "string",
            "enum": ["watch", "manual_review", "avoid", "ignore", "hold_for_more_data"],
        },
    },
    "required": [
        "primary_category",
        "event_type",
        "sentiment",
        "risk_level",
        "confidence",
        "summary",
        "reason",
        "watch_points",
        "recommended_action",
    ],
}


INSTRUCTIONS = """
너는 한국 주식 공시 분류 보조 엔진이다.
제공된 공시 메타데이터와 기존 규칙 분류만 사용한다.
제공되지 않은 정보는 추측하지 않는다.
매수, 매도, 목표가, 수익률 예측을 제시하지 않는다.
투자 추천이 아니라 검토 우선순위를 분류한다.
위험 공시는 보수적으로 판단한다.
공시 제목만으로 확정하기 어려우면 manual_review 또는 hold_for_more_data를 사용한다.
""".strip()


@dataclass(frozen=True)
class AIClassification:
    primary_category: str
    event_type: str
    sentiment: str
    risk_level: str
    confidence: float
    summary: str
    reason: str
    watch_points: list[str]
    recommended_action: str


def build_input(disclosure: dict[str, Any]) -> str:
    payload = {
        "corp_name": disclosure.get("corp_name"),
        "stock_code": disclosure.get("stock_code"),
        "market": disclosure.get("market"),
        "report_name": disclosure.get("report_name"),
        "receipt_date": disclosure.get("receipt_date"),
        "is_correction": bool(disclosure.get("is_correction")),
        "rule_category": disclosure.get("rule_category"),
        "rule_event_type": disclosure.get("rule_event_type"),
        "rule_recommended_action": disclosure.get("rule_recommended_action"),
        "rule_reason": disclosure.get("rule_reason"),
        "metrics": {
            "contract_amount": disclosure.get("contract_amount"),
            "recent_sales": disclosure.get("recent_sales"),
            "sales_ratio": disclosure.get("sales_ratio"),
            "treasury_buyback_amount": disclosure.get("treasury_buyback_amount"),
            "facility_investment_amount": disclosure.get("facility_investment_amount"),
            "equity_capital": disclosure.get("equity_capital"),
            "equity_ratio": disclosure.get("equity_ratio"),
            "new_share_count": disclosure.get("new_share_count"),
            "existing_share_count": disclosure.get("existing_share_count"),
            "dilution_ratio": disclosure.get("dilution_ratio"),
            "metric_details_json": disclosure.get("metric_details_json"),
        },
        "document_excerpt": str(disclosure.get("document_text") or "")[:3000],
    }
    return json.dumps(payload, ensure_ascii=False)


def classify_with_openai(
    disclosure: dict[str, Any],
    api_key: str,
    model: str,
) -> AIClassification:
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required.")

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=model,
        instructions=INSTRUCTIONS,
        input=build_input(disclosure),
        text={
            "format": {
                "type": "json_schema",
                "name": "disclosure_classification",
                "schema": CLASSIFICATION_SCHEMA,
                "strict": True,
            }
        },
        max_output_tokens=900,
    )

    output_text = getattr(response, "output_text", "")
    if not output_text:
        raise RuntimeError("OpenAI response did not contain output_text.")

    data = json.loads(output_text)
    return AIClassification(
        primary_category=data["primary_category"],
        event_type=data["event_type"],
        sentiment=data["sentiment"],
        risk_level=data["risk_level"],
        confidence=float(data["confidence"]),
        summary=data["summary"],
        reason=data["reason"],
        watch_points=list(data["watch_points"]),
        recommended_action=data["recommended_action"],
    )
