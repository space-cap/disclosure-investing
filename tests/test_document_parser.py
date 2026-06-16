from app.document_parser import extract_metrics, parse_number


def test_parse_number() -> None:
    assert parse_number("1,208,000,000") == 1208000000.0
    assert parse_number("5.13") == 5.13
    assert parse_number("-") is None


def test_extract_supply_contract_metrics() -> None:
    text = """
    계약금액 총액(원)
    1,208,000,000
    최근 매출액(원)
    23,532,183,911
    매출액 대비(%)
    5.13
    계약상대방
    케이비밸브상사(주)
    시작일
    2026-06-16
    종료일
    2028-06-30
    """

    result = extract_metrics("단일판매ㆍ공급계약체결", text)

    assert result.contract_amount == 1208000000.0
    assert result.recent_sales == 23532183911.0
    assert result.sales_ratio == 5.13
    assert result.details["contract_counterparty"] == "케이비밸브상사(주)"
    assert result.details["contract_start_date"] == "2026-06-16"
    assert result.details["contract_end_date"] == "2028-06-30"


def test_extract_facility_investment_metrics() -> None:
    text = """
    투자금액(원)
    50,000,000,000
    자기자본(원)
    100,000,000,000
    자기자본 대비(%)
    50.00
    투자목적
    생산능력 확대
    """

    result = extract_metrics("신규시설투자", text)

    assert result.facility_investment_amount == 50000000000.0
    assert result.equity_capital == 100000000000.0
    assert result.equity_ratio == 50.0
    assert result.details["investment_purpose"] == "생산능력 확대"


def test_extract_paid_capital_increase_metrics() -> None:
    text = """
    1. 신주의 종류와 수
    보통주식 (주)
    1,020,403
    기타주식 (주)
    -
    3. 증자전 발행주식총수 (주)
    보통주식 (주)
    20,000,000
    기타주식 (주)
    200,000
    4. 자금조달의 목적
    운영자금 (원)
    -
    채무상환자금 (원)
    -
    기타자금 (원)
    3,563,247,276
    5. 증자방식
    제3자배정증자
    6. 신주 발행가액
    보통주식 (원)
    3,492
    9. 납입일
    2026년 06월 24일
    """

    result = extract_metrics("주요사항보고서(유상증자결정)", text)

    assert result.new_share_count == 1020403.0
    assert result.existing_share_count == 20000000.0
    assert result.dilution_ratio == 5.1
    assert result.details["issue_price"] == 3492.0
    assert result.details["other_funds"] == 3563247276.0
    assert result.details["capital_increase_method"] == "제3자배정증자"


def test_extract_treasury_stock_metrics() -> None:
    text = """
    1. 취득예정주식(주)
    보통주식
    443,951
    기타주식
    -
    2. 취득예정금액(원)
    보통주식
    2,000,000,000
    기타주식
    -
    3. 취득예상기간
    시작일
    2026년 06월 17일
    종료일
    2026년 09월 16일
    """

    result = extract_metrics("주요사항보고서(자기주식취득결정)", text)

    assert result.treasury_buyback_amount == 2000000000.0
    assert result.details["treasury_share_count"] == 443951.0
    assert result.details["treasury_start_date"] == "2026년 06월 17일"


def test_extract_conversion_price_adjustment_metrics() -> None:
    text = """
    조정전 전환가액 (원)
    조정후 전환가액 (원)
    3
    비상장
    2,376
    1,869
    조정전 전환가능 주식수 (주)
    조정후 전환가능 주식수 (주)
    3
    3,000,000,000
    KRW : South-Korean Won
    1,262,626
    1,605,136
    3. 조정사유
    시가하락에 따른 전환가액 조정
    5. 조정가액 적용일
    2026-06-15
    """

    result = extract_metrics("전환가액의조정", text)

    assert result.new_share_count == 1605136.0
    assert result.details["conversion_price_before"] == 2376.0
    assert result.details["conversion_price_after"] == 1869.0
    assert result.details["convertible_shares_before"] == 1262626.0
    assert result.details["convertible_shares_after"] == 1605136.0
