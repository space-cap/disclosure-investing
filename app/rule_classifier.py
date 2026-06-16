from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuleClassification:
    category: str
    event_type: str
    recommended_action: str
    reason: str


RULES: list[tuple[str, RuleClassification]] = [
    ("유상증자결정", RuleClassification("risk", "paid_capital_increase", "avoid", "유상증자는 기존 주주 지분 희석 가능성이 있어 위험 공시로 우선 분류합니다.")),
    ("전환사채권발행결정", RuleClassification("risk", "convertible_bond", "avoid", "전환사채는 향후 주식 전환에 따른 희석과 매물 부담 가능성이 있습니다.")),
    ("신주인수권부사채권발행결정", RuleClassification("risk", "bond_with_warrant", "avoid", "신주인수권부사채는 향후 신주 발행에 따른 희석 가능성이 있습니다.")),
    ("전환가액의조정", RuleClassification("risk", "conversion_price_adjustment", "manual_review", "전환가액 조정은 잠재 희석 규모를 키울 수 있어 확인이 필요합니다.")),
    ("감자결정", RuleClassification("risk", "capital_reduction", "avoid", "감자는 재무구조 악화나 기존 주주 손실 가능성을 먼저 확인해야 합니다.")),
    ("관리종목", RuleClassification("risk", "delisting_risk", "avoid", "관리종목 관련 공시는 거래정지와 상장폐지 리스크를 먼저 봐야 합니다.")),
    ("상장폐지", RuleClassification("risk", "delisting_risk", "avoid", "상장폐지 관련 공시는 최우선 회피 대상으로 분류합니다.")),
    ("감사의견", RuleClassification("risk", "audit_opinion_risk", "avoid", "감사의견 관련 리스크는 거래정지와 상장 유지에 직접 영향을 줄 수 있습니다.")),
    ("횡령", RuleClassification("risk", "embezzlement_breach", "avoid", "횡령 혐의는 회사 신뢰와 거래 안정성을 크게 훼손할 수 있습니다.")),
    ("배임", RuleClassification("risk", "embezzlement_breach", "avoid", "배임 혐의는 회사 신뢰와 거래 안정성을 크게 훼손할 수 있습니다.")),
    ("최대주주 변경", RuleClassification("risk", "largest_shareholder_change", "manual_review", "최대주주 변경은 기대와 위험이 모두 커서 수동 검토가 필요합니다.")),
    ("단일판매ㆍ공급계약체결", RuleClassification("short_term_event", "supply_contract", "watch", "공급계약은 계약금액, 기간, 상대방에 따라 단기 이벤트가 될 수 있습니다.")),
    ("단일판매·공급계약체결", RuleClassification("short_term_event", "supply_contract", "watch", "공급계약은 계약금액, 기간, 상대방에 따라 단기 이벤트가 될 수 있습니다.")),
    ("자기주식취득결정", RuleClassification("short_term_event", "treasury_stock", "watch", "자사주 취득은 주주환원 및 수급 개선 신호로 볼 수 있습니다.")),
    ("자기주식소각", RuleClassification("short_term_event", "stock_retirement", "watch", "자사주 소각은 주당 가치 개선 효과를 확인할 만한 공시입니다.")),
    ("무상증자결정", RuleClassification("short_term_event", "bonus_issue", "manual_review", "무상증자는 단기 이벤트가 될 수 있지만 본질 가치 증가는 아니므로 확인이 필요합니다.")),
    ("현금ㆍ현물배당결정", RuleClassification("short_term_event", "dividend", "watch", "배당 결정은 주주환원 신호이며 지속 가능성을 함께 봐야 합니다.")),
    ("영업실적", RuleClassification("short_term_event", "earnings_guidance", "watch", "실적 관련 공시는 가격 재평가 요인이 될 수 있습니다.")),
    ("신규시설투자", RuleClassification("long_term_candidate", "facility_investment", "watch", "신규시설투자는 향후 성장성과 재무 부담을 함께 검토해야 합니다.")),
    ("기업설명회", RuleClassification("long_term_candidate", "ir_event", "watch", "IR 공시는 회사가 제시하는 성장 가설과 핵심 지표를 확인할 기회입니다.")),
    ("분기보고서", RuleClassification("long_term_candidate", "regular_report", "watch", "정기보고서는 중장기 투자 가설을 점검하는 핵심 자료입니다.")),
    ("반기보고서", RuleClassification("long_term_candidate", "regular_report", "watch", "정기보고서는 중장기 투자 가설을 점검하는 핵심 자료입니다.")),
    ("사업보고서", RuleClassification("long_term_candidate", "regular_report", "watch", "정기보고서는 중장기 투자 가설을 점검하는 핵심 자료입니다.")),
]


DEFAULT_CLASSIFICATION = RuleClassification(
    category="manual_review",
    event_type="unknown",
    recommended_action="manual_review",
    reason="등록된 규칙으로 확정 분류되지 않아 수동 검토가 필요합니다.",
)


def classify_report(report_name: str) -> RuleClassification:
    normalized = report_name.replace(" ", "")

    for keyword, classification in RULES:
        if keyword.replace(" ", "") in normalized:
            return classification

    return DEFAULT_CLASSIFICATION

