import json

from app.ai_classifier import CLASSIFICATION_SCHEMA, build_input


def test_schema_has_required_fields() -> None:
    required = set(CLASSIFICATION_SCHEMA["required"])

    assert "primary_category" in required
    assert "event_type" in required
    assert "recommended_action" in required
    assert CLASSIFICATION_SCHEMA["additionalProperties"] is False


def test_build_input_uses_metadata_only() -> None:
    payload = build_input(
        {
            "corp_name": "테스트",
            "report_name": "유상증자결정",
            "rule_category": "risk",
            "rule_event_type": "paid_capital_increase",
        }
    )

    data = json.loads(payload)
    assert data["corp_name"] == "테스트"
    assert data["report_name"] == "유상증자결정"
    assert data["rule_category"] == "risk"
