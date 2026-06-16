from app.rule_classifier import classify_report


def test_risk_disclosure_has_priority() -> None:
    result = classify_report("주요사항보고서(유상증자결정)")

    assert result.category == "risk"
    assert result.event_type == "paid_capital_increase"
    assert result.recommended_action == "avoid"


def test_supply_contract() -> None:
    result = classify_report("단일판매ㆍ공급계약체결")

    assert result.category == "short_term_event"
    assert result.event_type == "supply_contract"


def test_regular_report() -> None:
    result = classify_report("분기보고서")

    assert result.category == "long_term_candidate"
    assert result.event_type == "regular_report"


def test_unknown_goes_to_manual_review() -> None:
    result = classify_report("기타 경영사항")

    assert result.category == "manual_review"
    assert result.event_type == "unknown"
