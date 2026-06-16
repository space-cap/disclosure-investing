from app.reporting import build_daily_report


def test_build_daily_report() -> None:
    report = build_daily_report(
        [
            {
                "corp_name": "테스트",
                "stock_code": "123456",
                "report_name": "단일판매ㆍ공급계약체결",
                "rule_category": "short_term_event",
                "ai_category": "short_term_event",
                "recommended_action": "watch",
                "risk_level": "medium",
                "contract_amount": 1208000000,
                "sales_ratio": 5.13,
                "summary": "공급계약 공시입니다.",
                "dart_url": "https://dart.example",
            }
        ],
        "20260616",
    )

    assert "일일 공시 요약 - 20260616" in report
    assert "단기 이벤트 후보" in report
    assert "계약금액 12.1억" in report
    assert "매출대비 5.13%" in report


def test_build_daily_report_omits_nan_metrics() -> None:
    report = build_daily_report(
        [
            {
                "corp_name": "테스트",
                "stock_code": "123456",
                "report_name": "주요사항보고서",
                "rule_category": "risk",
                "ai_category": None,
                "recommended_action": "manual_review",
                "risk_level": "high",
                "contract_amount": float("nan"),
                "sales_ratio": float("nan"),
                "treasury_buyback_amount": None,
                "summary": "검토가 필요합니다.",
            }
        ],
        "20260616",
    )

    assert "nan" not in report.lower()
    assert "숫자:" not in report
    assert "검토가 필요합니다." in report
