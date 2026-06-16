from __future__ import annotations

import json
from html import escape
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st

from app.config import load_settings
from app.database import connect, fetch_recent_job_runs, fetch_report_rows, get_note, init_db, upsert_note
from app.reporting import build_daily_report, metric_summary


st.set_page_config(page_title="Disclosure Investing", layout="wide", initial_sidebar_state="collapsed")

st.markdown(
    """
    <style>
    .stApp { background: #f6f7f9; color: #172033; }
    [data-testid="stToolbar"], .stDeployButton, [data-testid="stSidebar"], [data-testid="stHeader"] { display: none !important; }
    .block-container { padding-top: 1.1rem; padding-bottom: 2rem; padding-left: 17rem; padding-right: 1.4rem; max-width: none; }
    .fixed-nav { position: fixed; inset: 0 auto 0 0; width: 15rem; z-index: 999999; background: #ffffff; border-right: 1px solid #e2e6ee; padding: 1.15rem .85rem; box-shadow: 1px 0 2px rgba(16, 24, 40, .04); overflow-y: auto; }
    .fixed-nav .brand { border-bottom: 1px solid #e2e6ee; padding-bottom: .9rem; margin-bottom: .85rem; }
    .fixed-nav .brand-name { color: #172033; font-size: 1.05rem; line-height: 1.25; font-weight: 800; }
    .fixed-nav .brand-sub { color: #667085; font-size: .75rem; font-weight: 700; letter-spacing: .04em; margin-top: .25rem; }
    .fixed-nav .status { color: #475467; background: #f8fafc; border: 1px solid #e2e6ee; border-radius: 8px; padding: .7rem; font-size: .8rem; line-height: 1.45; margin-top: .9rem; }
    .nav-link { display: block; color: #344054 !important; text-decoration: none !important; border: 1px solid transparent; border-radius: 8px; padding: .55rem .7rem; margin: .18rem 0; font-size: .9rem; font-weight: 700; }
    .nav-link:hover { background: #f8fafc; border-color: #e2e6ee; }
    .nav-link.active { color: #172033 !important; background: #eef2f6; border-color: #d7dde8; }
    h1, h2, h3, h4, h5 { letter-spacing: 0; color: #172033; }
    .page-title { display: flex; align-items: end; justify-content: space-between; gap: 1rem; margin-bottom: .7rem; border-bottom: 1px solid #e2e6ee; padding-bottom: .8rem; }
    .page-title h1 { font-size: 1.55rem; line-height: 1.2; margin: 0; color: #172033; }
    .page-title p { margin: .25rem 0 0 0; color: #667085; font-size: .92rem; }
    .page-mark { color: #475467; font-size: .82rem; font-weight: 700; }
    .status-strip { display: grid; grid-template-columns: 1.35fr repeat(5, minmax(6rem, 1fr)); gap: .55rem; margin: .6rem 0 1rem 0; }
    .status-cell { background: #ffffff; border: 1px solid #e2e6ee; border-radius: 8px; padding: .72rem .8rem; min-height: 4.4rem; }
    .status-cell .label { color: #667085; font-size: .76rem; font-weight: 700; text-transform: uppercase; }
    .status-cell .value { color: #172033; font-size: 1.25rem; line-height: 1.3; font-weight: 780; margin-top: .2rem; }
    .status-cell .sub { color: #667085; font-size: .78rem; line-height: 1.35; margin-top: .15rem; }
    .panel { background: #ffffff; border: 1px solid #e2e6ee; border-radius: 8px; padding: .95rem; box-shadow: 0 1px 2px rgba(16, 24, 40, .04); margin-bottom: .75rem; }
    .review-card { background: #ffffff; border: 1px solid #e2e6ee; border-left: 4px solid #d7dde8; border-radius: 8px; padding: .9rem .95rem; margin-bottom: .7rem; }
    .review-card.risk { border-left-color: #b42318; }
    .review-card.watch { border-left-color: #175cd3; }
    .review-card.long { border-left-color: #067647; }
    .review-card.manual { border-left-color: #93370d; }
    .section-label { color: #667085; font-size: .75rem; font-weight: 750; margin-bottom: .35rem; text-transform: uppercase; }
    .selected-title { color: #172033; font-size: 1rem; font-weight: 760; line-height: 1.38; margin-bottom: .35rem; overflow-wrap: anywhere; }
    .selected-meta { color: #667085; font-size: .88rem; margin-bottom: .75rem; }
    .badge { display: inline-block; border-radius: 999px; padding: .16rem .5rem; font-size: .73rem; font-weight: 760; margin-right: .28rem; margin-bottom: .25rem; border: 1px solid transparent; white-space: nowrap; }
    .badge-risk { color: #b42318; background: #fee4e2; border-color: #fecdca; }
    .badge-watch { color: #175cd3; background: #dbeafe; border-color: #bfdbfe; }
    .badge-long { color: #067647; background: #dcfae6; border-color: #abefc6; }
    .badge-manual { color: #93370d; background: #fef0c7; border-color: #fedf89; }
    .badge-muted { color: #344054; background: #eef2f6; border-color: #d7dde8; }
    .kv { display: grid; grid-template-columns: 6.8rem 1fr; gap: .42rem .75rem; font-size: .88rem; margin-top: .7rem; }
    .kv .key { color: #667085; }
    .kv .value { color: #172033; font-weight: 600; overflow-wrap: anywhere; }
    .metric-list { display: grid; grid-template-columns: 1fr 1fr; gap: .4rem .8rem; margin-top: .55rem; }
    .metric-row { display: flex; align-items: baseline; justify-content: space-between; gap: .8rem; border-bottom: 1px solid #eef2f6; padding: .34rem 0; }
    .metric-row .key { color: #667085; font-size: .82rem; }
    .metric-row .value { color: #172033; font-size: .9rem; font-weight: 760; text-align: right; overflow-wrap: anywhere; }
    .note { color: #475467; background: #f8fafc; border: 1px solid #e2e6ee; border-radius: 8px; padding: .75rem; font-size: .88rem; line-height: 1.55; }
    .muted-line { color: #667085; font-size: .86rem; line-height: 1.5; }
    .section-heading { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin: .2rem 0 .55rem; }
    .section-heading h3 { font-size: 1rem; margin: 0; }
    div[data-testid="stMetric"] { background: #ffffff; border: 1px solid #e2e6ee; border-radius: 8px; padding: .75rem .85rem; box-shadow: 0 1px 2px rgba(16, 24, 40, .04); }
    div[data-testid="stMetricLabel"] { color: #667085; }
    div[data-testid="stMetricValue"] { font-size: 1.22rem; }
    @media (max-width: 1000px) {
      .status-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .metric-list { grid-template-columns: 1fr; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

settings = load_settings()
init_db(settings.database_path)

PAGES = {
    "오늘": "오늘 먼저 볼 공시와 자동 실행 상태를 확인합니다.",
    "긍정 공시": "위험 공시를 제외하고 관심 있게 볼 만한 긍정 후보만 모아봅니다.",
    "공시함": "공시 목록을 필터링하고 상세 숫자, AI 요약, 메모를 검토합니다.",
    "관심/메모": "직접 남긴 판단과 복기할 공시를 모아봅니다.",
    "리포트": "날짜별 일일 요약 리포트를 확인하고 다운로드합니다.",
    "운영": "자동 실행, 처리량, 원문 수집 오류 상태를 확인합니다.",
}

DETAIL_LABELS = {
    "contract_counterparty": "계약상대방",
    "contract_start_date": "계약 시작일",
    "contract_end_date": "계약 종료일",
    "issue_price": "발행가",
    "issue_amount": "조달금액",
    "facility_funds": "시설자금",
    "operating_funds": "운영자금",
    "debt_repayment_funds": "채무상환자금",
    "other_funds": "기타자금",
    "capital_increase_method": "증자방식",
    "payment_date": "납입일",
    "listing_date": "상장예정일",
    "treasury_share_count": "취득예정주식수",
    "treasury_start_date": "취득 시작일",
    "treasury_end_date": "취득 종료일",
    "bond_amount": "사채권면총액",
    "conversion_price_before": "조정 전 전환가액",
    "conversion_price_after": "조정 후 전환가액",
    "convertible_shares_before": "조정 전 전환가능주식수",
    "convertible_shares_after": "조정 후 전환가능주식수",
    "adjustment_reason": "조정사유",
    "adjustment_effective_date": "조정가액 적용일",
    "conversion_start_date": "전환 시작일",
    "conversion_end_date": "전환 종료일",
    "investment_purpose": "투자목적",
}


def display_value(value: object, default: str = "-") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except TypeError:
        pass
    text = str(value).strip()
    return text if text else default


def html_value(value: object, default: str = "-") -> str:
    return escape(display_value(value, default))


def badge(label: object, tone: str = "muted") -> str:
    return f'<span class="badge badge-{tone}">{html_value(label)}</span>'


def category_tone(category: object) -> str:
    value = display_value(category)
    if value == "risk":
        return "risk"
    if value == "short_term_event":
        return "watch"
    if value == "long_term_candidate":
        return "long"
    if value == "manual_review":
        return "manual"
    return "muted"


def action_tone(action: object) -> str:
    value = display_value(action)
    if value == "avoid":
        return "risk"
    if value == "watch":
        return "watch"
    if value == "manual_review":
        return "manual"
    return "muted"


def row_tone(row: dict[str, object] | pd.Series) -> str:
    category = display_value(row.get("ai_category") or row.get("rule_category"))
    action = display_value(row.get("recommended_action"))
    risk_level = display_value(row.get("risk_level"))
    if category == "risk" or action == "avoid" or risk_level == "high":
        return "risk"
    if category == "short_term_event" or action == "watch":
        return "watch"
    if category == "long_term_candidate":
        return "long"
    if category == "manual_review" or action in {"manual_review", "hold_for_more_data"}:
        return "manual"
    return "muted"


def latest_receipt_date(df: pd.DataFrame) -> str:
    if df.empty or "receipt_date" not in df.columns:
        return "-"
    dates = sorted(df["receipt_date"].dropna().unique().tolist(), reverse=True)
    return str(dates[0]) if dates else "-"


def status_tone(status: object) -> str:
    value = display_value(status)
    if value == "success":
        return "long"
    if value == "failed":
        return "risk"
    if value == "running":
        return "manual"
    return "muted"


def format_number(value: object, suffix: str = "") -> str:
    if value is None:
        return "-"
    try:
        if pd.isna(value):
            return "-"
        number = float(value)
    except (TypeError, ValueError):
        return display_value(value)
    if abs(number) >= 1_000_000_000:
        formatted = f"{number / 100_000_000:,.1f}억"
    elif abs(number) >= 10_000:
        formatted = f"{number / 10_000:,.0f}만"
    else:
        formatted = f"{number:,.2f}".rstrip("0").rstrip(".")
    return f"{formatted}{suffix}"


def parse_json_dict(raw_value: object) -> dict[str, object]:
    if raw_value is None:
        return {}
    try:
        if pd.isna(raw_value):
            return {}
    except TypeError:
        pass
    try:
        data = json.loads(str(raw_value))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def parse_json_list(raw_value: object) -> list[str]:
    if raw_value is None:
        return []
    try:
        if pd.isna(raw_value):
            return []
    except TypeError:
        pass
    try:
        data = json.loads(str(raw_value))
    except json.JSONDecodeError:
        return []
    return [str(item) for item in data if str(item).strip()] if isinstance(data, list) else []


def has_extracted_metrics(row: pd.Series) -> bool:
    metric_columns = [
        "contract_amount",
        "recent_sales",
        "sales_ratio",
        "treasury_buyback_amount",
        "facility_investment_amount",
        "equity_ratio",
        "new_share_count",
        "dilution_ratio",
    ]
    return any(display_value(row.get(column)) != "-" for column in metric_columns)


def load_rows() -> list[dict[str, object]]:
    with connect(settings.database_path) as conn:
        rows = conn.execute(
            """
            SELECT
                d.id, d.receipt_date, d.corp_name, d.stock_code, d.market,
                d.report_name, d.is_correction, d.dart_url, d.document_text, d.document_error,
                c.rule_category, c.rule_event_type, c.ai_category, c.ai_event_type,
                c.sentiment, c.risk_level, c.confidence, c.summary, c.watch_points_json,
                c.recommended_action, c.reason,
                n.status AS note_status, n.user_note,
                m.contract_amount, m.recent_sales, m.sales_ratio, m.treasury_buyback_amount,
                m.facility_investment_amount, m.equity_capital, m.equity_ratio,
                m.new_share_count, m.existing_share_count, m.dilution_ratio, m.metric_details_json
            FROM disclosures d
            LEFT JOIN classifications c ON c.disclosure_id = d.id
            LEFT JOIN notes n ON n.disclosure_id = d.id
            LEFT JOIN metrics m ON m.disclosure_id = d.id
            ORDER BY d.receipt_date DESC, d.id DESC
            LIMIT 500
            """
        ).fetchall()
    return [dict(row) for row in rows]


def prepare_dataframe(data: list[dict[str, object]]) -> pd.DataFrame:
    df = pd.DataFrame(data)
    df["display_name"] = df["corp_name"].fillna("-") + " | " + df["report_name"].fillna("-")
    df["note_status"] = df["note_status"].fillna("new")
    return df


def render_sidebar_navigation() -> str:
    selected_page = st.query_params.get("page", "오늘")
    if selected_page not in PAGES:
        selected_page = "오늘"
    nav_links = []
    for page_name in PAGES:
        active_class = " active" if selected_page == page_name else ""
        nav_links.append(
            f'<a class="nav-link{active_class}" href="/?page={quote(page_name)}" target="_self">{html_value(page_name)}</a>'
        )

    job_runs, _, ai_pending_count = load_operation_state()
    latest = job_runs[0] if job_runs else {}
    st.markdown(
        f"""
        <div class="fixed-nav">
          <div class="brand">
            <div class="brand-name">Disclosure<br>Investing</div>
            <div class="brand-sub">DART WORKSPACE</div>
          </div>
          <div class="section-label">Menu</div>
          {"".join(nav_links)}
          <div class="status">
            <strong>자동 실행</strong><br>
            상태 {badge(display_value(latest.get("status"), "no_run"), status_tone(latest.get("status")))}<br>
            마지막 {html_value(latest.get("finished_at"))}<br>
            AI 대기 {ai_pending_count:,}건
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return str(selected_page)


def render_header(page_name: str) -> None:
    st.markdown(
        f"""
        <div class="page-title">
          <div>
            <h1>{html_value(page_name)}</h1>
            <p>{html_value(PAGES.get(page_name))}</p>
          </div>
          <div class="page-mark">DART WORKSPACE</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_strip(df: pd.DataFrame, latest_job: dict[str, object] | None, ai_pending_count: int) -> None:
    today = latest_receipt_date(df)
    today_df = df[df["receipt_date"] == today] if today != "-" and not df.empty else df
    status = display_value(latest_job.get("status") if latest_job else None, "no_run")
    last_run = display_value(latest_job.get("finished_at") if latest_job else None)
    job_badge = badge(status, status_tone(status))

    st.markdown(
        f"""
        <div class="status-strip">
          <div class="status-cell">
            <div class="label">Today</div>
            <div class="value">{html_value(today)}</div>
            <div class="sub">자동 실행 {job_badge} · 마지막 {html_value(last_run)}</div>
          </div>
          <div class="status-cell"><div class="label">전체</div><div class="value">{len(today_df):,}</div><div class="sub">오늘 공시</div></div>
          <div class="status-cell"><div class="label">위험</div><div class="value">{(today_df["rule_category"] == "risk").sum() if not today_df.empty else 0:,}</div><div class="sub">우선 회피/검토</div></div>
          <div class="status-cell"><div class="label">단기</div><div class="value">{(today_df["rule_category"] == "short_term_event").sum() if not today_df.empty else 0:,}</div><div class="sub">이벤트 후보</div></div>
          <div class="status-cell"><div class="label">수동검토</div><div class="value">{today_df["recommended_action"].isin(["manual_review", "hold_for_more_data"]).sum() if not today_df.empty else 0:,}</div><div class="sub">사람 판단 필요</div></div>
          <div class="status-cell"><div class="label">AI 대기</div><div class="value">{ai_pending_count:,}</div><div class="sub">추가 분류 필요</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def priority_score(row: pd.Series) -> int:
    score = 0
    if row.get("rule_category") == "risk" or row.get("ai_category") == "risk":
        score += 100
    if row.get("risk_level") == "high":
        score += 80
    if row.get("recommended_action") == "avoid":
        score += 60
    if row.get("rule_category") == "short_term_event" or row.get("ai_category") == "short_term_event":
        score += 40
    if row.get("recommended_action") in {"manual_review", "hold_for_more_data"}:
        score += 35
    if display_value(row.get("sales_ratio")) != "-" or display_value(row.get("dilution_ratio")) != "-":
        score += 15
    return score


def positive_score(row: pd.Series) -> int:
    rule_category = display_value(row.get("rule_category"))
    ai_category = display_value(row.get("ai_category"))
    action = display_value(row.get("recommended_action"))
    risk_level = display_value(row.get("risk_level"))
    sentiment = display_value(row.get("sentiment"))
    event_type = display_value(row.get("ai_event_type") or row.get("rule_event_type"))

    if rule_category == "risk" or ai_category == "risk" or action == "avoid" or risk_level == "high":
        return 0

    score = 0
    if sentiment == "positive":
        score += 100
    if ai_category in {"short_term_event", "long_term_candidate"}:
        score += 60
    if rule_category == "short_term_event":
        score += 45
    if rule_category == "long_term_candidate":
        score += 40
    if action == "watch":
        score += 35
    if event_type in {
        "supply_contract",
        "treasury_stock",
        "stock_retirement",
        "bonus_issue",
        "dividend",
        "earnings_guidance",
        "facility_investment",
        "ir_event",
        "insider_buying",
    }:
        score += 20
    if display_value(row.get("sales_ratio")) != "-":
        score += 15
    if display_value(row.get("contract_amount")) != "-":
        score += 10
    if display_value(row.get("treasury_buyback_amount")) != "-":
        score += 10
    if display_value(row.get("facility_investment_amount")) != "-":
        score += 10
    return score


def positive_reason(row: pd.Series) -> str:
    reasons = []
    if display_value(row.get("sentiment")) == "positive":
        reasons.append("AI 긍정")
    category = display_value(row.get("ai_category") or row.get("rule_category"))
    if category == "short_term_event":
        reasons.append("단기 이벤트")
    if category == "long_term_candidate":
        reasons.append("중장기 후보")
    if display_value(row.get("recommended_action")) == "watch":
        reasons.append("관심 액션")
    metrics = metric_summary(row.to_dict())
    if metrics:
        reasons.append(metrics)
    return " · ".join(reasons) if reasons else "-"


def build_positive_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    work_df = df.copy()
    work_df["positive_score"] = work_df.apply(positive_score, axis=1)
    work_df["positive_reason"] = work_df.apply(positive_reason, axis=1)
    work_df = work_df[work_df["positive_score"] > 0]
    return work_df.sort_values(["positive_score", "receipt_date", "id"], ascending=[False, False, False])


def build_priority_rows(df: pd.DataFrame, limit: int = 7) -> pd.DataFrame:
    if df.empty:
        return df
    today = latest_receipt_date(df)
    work_df = df[df["receipt_date"] == today].copy() if today != "-" else df.copy()
    if work_df.empty:
        work_df = df.copy()
    work_df["priority_score"] = work_df.apply(priority_score, axis=1)
    work_df = work_df[work_df["priority_score"] > 0]
    return work_df.sort_values(["priority_score", "id"], ascending=[False, False]).head(limit)


def render_review_card(row: pd.Series) -> None:
    metrics = metric_summary(row.to_dict())
    summary = display_value(row.get("summary") or row.get("reason"))
    detail = metrics if metrics else summary
    tone = row_tone(row)
    st.markdown(
        f"""
        <div class="review-card {tone}">
          <div class="selected-title">{html_value(row.get("corp_name"))}</div>
          <div class="selected-meta">{html_value(row.get("stock_code"))} · {html_value(row.get("receipt_date"))}</div>
          <div style="margin-bottom:.45rem;">
            {badge(row.get("rule_category"), category_tone(row.get("rule_category")))}
            {badge(row.get("ai_category"), category_tone(row.get("ai_category")))}
            {badge(row.get("risk_level"), "risk" if display_value(row.get("risk_level")) == "high" else "muted")}
            {badge(row.get("recommended_action"), action_tone(row.get("recommended_action")))}
          </div>
          <div class="muted-line"><strong>{html_value(row.get("report_name"))}</strong></div>
          <div class="muted-line" style="margin-top:.35rem;">{html_value(detail)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_today_tab(df: pd.DataFrame) -> None:
    job_runs, document_errors, ai_pending_count = load_operation_state()
    latest_job = job_runs[0] if job_runs else None
    if df.empty:
        render_status_strip(df, latest_job, ai_pending_count)
        st.info("아직 저장된 공시가 없습니다. 자동 실행 또는 `fetch-disclosures` 실행 후 오늘 화면이 채워집니다.")
        return

    render_status_strip(df, latest_job, ai_pending_count)
    priority_rows = build_priority_rows(df)

    left_col, right_col = st.columns([1.4, .9], gap="large")
    with left_col:
        st.markdown('<div class="section-heading"><h3>우선 검토 공시</h3><span class="muted-line">위험, high risk, 단기 이벤트를 먼저 정렬</span></div>', unsafe_allow_html=True)
        if priority_rows.empty:
            st.markdown('<div class="note">오늘 우선 검토할 공시가 없습니다.</div>', unsafe_allow_html=True)
        else:
            for _, row in priority_rows.iterrows():
                render_review_card(row)

    with right_col:
        st.markdown('<div class="section-heading"><h3>처리 상태</h3></div>', unsafe_allow_html=True)
        latest = latest_job or {}
        st.markdown(
            f"""
            <div class="panel">
              <div class="section-label">Automation</div>
              <div class="selected-title">자동 실행 {badge(display_value(latest.get("status"), "no_run"), status_tone(latest.get("status")))}</div>
              <div class="kv">
                <div class="key">마지막 실행</div><div class="value">{html_value(latest.get("finished_at"))}</div>
                <div class="key">원문 수집</div><div class="value">{int(latest.get("document_count") or 0):,}건</div>
                <div class="key">지표 추출</div><div class="value">{int(latest.get("metric_count") or 0):,}건</div>
                <div class="key">AI 분류</div><div class="value">{int(latest.get("ai_count") or 0):,}건</div>
                <div class="key">최근 오류</div><div class="value">{len(document_errors):,}건</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="section-heading"><h3>다음 행동</h3></div>', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="note">
              위험 공시를 먼저 열어 희석, 감자, 전환가 조정 여부를 확인합니다.<br>
              단기 이벤트는 계약금액, 매출대비, 계약상대방을 보고 watch 여부를 남깁니다.<br>
              AI 대기가 많으면 장 후에 `run-daily`의 AI limit을 늘려 다시 실행합니다.
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_positive_tab(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("긍정 공시로 볼 데이터가 아직 없습니다.")
        return

    positive_df = build_positive_rows(df)
    today = latest_receipt_date(df)
    today_positive = positive_df[positive_df["receipt_date"] == today] if today != "-" and not positive_df.empty else positive_df

    cols = st.columns(5)
    cols[0].metric("긍정 후보", f"{len(positive_df):,}")
    cols[1].metric("오늘 후보", f"{len(today_positive):,}")
    cols[2].metric("AI 긍정", f"{(positive_df['sentiment'] == 'positive').sum() if not positive_df.empty else 0:,}")
    cols[3].metric("단기 이벤트", f"{((positive_df['rule_category'] == 'short_term_event') | (positive_df['ai_category'] == 'short_term_event')).sum() if not positive_df.empty else 0:,}")
    cols[4].metric("중장기 후보", f"{((positive_df['rule_category'] == 'long_term_candidate') | (positive_df['ai_category'] == 'long_term_candidate')).sum() if not positive_df.empty else 0:,}")

    if positive_df.empty:
        st.markdown(
            """
            <div class="note">
              현재 기준으로 긍정 후보가 없습니다. AI 분류가 아직 적으면 `classify-ai` 또는 `run-daily`의 AI limit을 늘리면 후보가 더 정교해집니다.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    filter_cols = st.columns([.22, .22, .22, .34])
    date_options = ["all"] + sorted(positive_df["receipt_date"].dropna().unique().tolist(), reverse=True)
    category_options = ["all"] + sorted(
        option for option in positive_df["rule_category"].dropna().unique().tolist()
    )
    selected_date = filter_cols[0].selectbox("접수일", date_options, index=1 if today in date_options else 0)
    selected_category = filter_cols[1].selectbox("분류", category_options)
    min_score = filter_cols[2].selectbox("최소 점수", [0, 40, 60, 80, 100], index=0)
    search_text = filter_cols[3].text_input("회사명/공시명 검색", key="positive-search")

    filtered = positive_df.copy()
    if selected_date != "all":
        filtered = filtered[filtered["receipt_date"] == selected_date]
    if selected_category != "all":
        filtered = filtered[filtered["rule_category"] == selected_category]
    filtered = filtered[filtered["positive_score"] >= min_score]
    if search_text.strip():
        query = search_text.strip()
        filtered = filtered[
            filtered["corp_name"].fillna("").str.contains(query, case=False, regex=False)
            | filtered["report_name"].fillna("").str.contains(query, case=False, regex=False)
        ]

    if filtered.empty:
        st.warning("선택한 조건에 맞는 긍정 후보가 없습니다.")
        return

    top_col, detail_col = st.columns([1.05, .95], gap="large")
    with top_col:
        st.markdown('<div class="section-heading"><h3>긍정 후보 목록</h3><span class="muted-line">위험 공시와 avoid/high를 제외한 후보</span></div>', unsafe_allow_html=True)
        selected_id = st.selectbox(
            "긍정 후보 선택",
            filtered["id"].tolist(),
            format_func=lambda disclosure_id: filtered.loc[
                filtered["id"] == disclosure_id, "display_name"
            ].iloc[0],
            label_visibility="collapsed",
        )
        st.dataframe(
            filtered[
                [
                    "receipt_date",
                    "corp_name",
                    "stock_code",
                    "report_name",
                    "rule_category",
                    "sentiment",
                    "recommended_action",
                    "positive_score",
                    "positive_reason",
                ]
            ].fillna("-"),
            use_container_width=True,
            hide_index=True,
            height=560,
            column_config={
                "receipt_date": st.column_config.TextColumn("접수일", width="small"),
                "corp_name": st.column_config.TextColumn("회사", width="small"),
                "stock_code": st.column_config.TextColumn("코드", width="small"),
                "report_name": st.column_config.TextColumn("공시명", width="large"),
                "rule_category": st.column_config.TextColumn("분류", width="medium"),
                "sentiment": st.column_config.TextColumn("AI 감성", width="small"),
                "recommended_action": st.column_config.TextColumn("액션", width="small"),
                "positive_score": st.column_config.NumberColumn("점수", width="small"),
                "positive_reason": st.column_config.TextColumn("긍정 근거", width="large"),
            },
        )

    selected = filtered.loc[filtered["id"] == selected_id].iloc[0].to_dict()
    with detail_col:
        st.markdown('<div class="section-heading"><h3>후보 상세</h3></div>', unsafe_allow_html=True)
        render_review_card(pd.Series(selected))
        render_disclosure_detail(selected, int(selected_id))
        render_disclosure_insight(selected, int(selected_id))


def render_metrics(df: pd.DataFrame) -> None:
    cols = st.columns(5)
    cols[0].metric("전체 공시", f"{len(df):,}")
    cols[1].metric("위험", f"{(df['rule_category'] == 'risk').sum():,}")
    cols[2].metric("단기 후보", f"{(df['rule_category'] == 'short_term_event').sum():,}")
    cols[3].metric("중장기 후보", f"{(df['rule_category'] == 'long_term_candidate').sum():,}")
    cols[4].metric("AI 분류", f"{df['ai_category'].notna().sum():,}")


def apply_sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.markdown('<div class="section-label">Filters</div>', unsafe_allow_html=True)
    category_options = ["all"] + sorted(option for option in df["rule_category"].dropna().unique().tolist())
    action_options = ["all"] + sorted(option for option in df["recommended_action"].dropna().unique().tolist())
    risk_options = ["all"] + sorted(option for option in df["risk_level"].dropna().unique().tolist())
    status_options = ["all"] + sorted(option for option in df["note_status"].dropna().unique().tolist())

    filter_cols = st.columns([.18, .18, .16, .16, .32])
    selected_category = filter_cols[0].selectbox("규칙 분류", category_options)
    selected_action = filter_cols[1].selectbox("액션", action_options)
    selected_risk = filter_cols[2].selectbox("위험도", risk_options)
    selected_status = filter_cols[3].selectbox("내 상태", status_options)
    search_text = filter_cols[4].text_input("회사명/공시명 검색")

    filtered_df = df.copy()
    if selected_category != "all":
        filtered_df = filtered_df[filtered_df["rule_category"] == selected_category]
    if selected_action != "all":
        filtered_df = filtered_df[filtered_df["recommended_action"] == selected_action]
    if selected_risk != "all":
        filtered_df = filtered_df[filtered_df["risk_level"] == selected_risk]
    if selected_status != "all":
        filtered_df = filtered_df[filtered_df["note_status"] == selected_status]
    if search_text.strip():
        query = search_text.strip()
        filtered_df = filtered_df[
            filtered_df["corp_name"].fillna("").str.contains(query, case=False, regex=False)
            | filtered_df["report_name"].fillna("").str.contains(query, case=False, regex=False)
        ]
    return filtered_df


def render_monitor_tab(df: pd.DataFrame) -> None:
    render_metrics(df)
    filtered_df = apply_sidebar_filters(df)
    if filtered_df.empty:
        st.warning("선택한 조건에 맞는 공시가 없습니다.")
        return

    list_col, detail_col, insight_col = st.columns([.95, 1.08, .9], gap="large")
    with list_col:
        st.markdown('<div class="section-label">Disclosure Inbox</div>', unsafe_allow_html=True)
        selected_id = render_disclosure_list(filtered_df)
    selected = filtered_df.loc[filtered_df["id"] == selected_id].iloc[0].to_dict()
    with detail_col:
        render_disclosure_detail(selected, int(selected_id))
    with insight_col:
        render_disclosure_insight(selected, int(selected_id))


def render_disclosure_list(filtered_df: pd.DataFrame) -> int:
    default_index = 0
    for index, (_, row) in enumerate(filtered_df.iterrows()):
        if has_extracted_metrics(row):
            default_index = index
            break
    selected_id = st.selectbox(
        "공시 선택",
        filtered_df["id"].tolist(),
        index=default_index,
        format_func=lambda disclosure_id: filtered_df.loc[
            filtered_df["id"] == disclosure_id, "display_name"
        ].iloc[0],
        label_visibility="collapsed",
    )

    table_columns = [
        "receipt_date",
        "corp_name",
        "stock_code",
        "report_name",
        "rule_category",
        "risk_level",
        "recommended_action",
        "note_status",
    ]
    st.dataframe(
        filtered_df[table_columns].fillna("-"),
        use_container_width=True,
        hide_index=True,
        height=560,
        column_config={
            "receipt_date": st.column_config.TextColumn("접수일", width="small"),
            "corp_name": st.column_config.TextColumn("회사", width="small"),
            "stock_code": st.column_config.TextColumn("코드", width="small"),
            "report_name": st.column_config.TextColumn("공시명", width="large"),
            "rule_category": st.column_config.TextColumn("분류", width="medium"),
            "risk_level": st.column_config.TextColumn("위험도", width="small"),
            "recommended_action": st.column_config.TextColumn("액션", width="small"),
            "note_status": st.column_config.TextColumn("상태", width="small"),
        },
    )
    return int(selected_id)


def render_disclosure_detail(selected: dict[str, object], selected_id: int) -> None:
    st.markdown('<div class="section-label">Disclosure Detail</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="panel">
          <div class="selected-title">{html_value(selected.get("corp_name"))}</div>
          <div class="selected-meta">{html_value(selected.get("stock_code"))} · {html_value(selected.get("receipt_date"))}</div>
          <div>
            {badge(selected.get("rule_category"), category_tone(selected.get("rule_category")))}
            {badge(selected.get("ai_category"), category_tone(selected.get("ai_category")))}
            {badge(selected.get("risk_level"), "risk" if display_value(selected.get("risk_level")) == "high" else "muted")}
            {badge(selected.get("recommended_action"), action_tone(selected.get("recommended_action")))}
          </div>
          <div class="kv">
            <div class="key">공시명</div><div class="value">{html_value(selected.get("report_name"))}</div>
            <div class="key">규칙 이벤트</div><div class="value">{html_value(selected.get("rule_event_type"))}</div>
            <div class="key">AI 이벤트</div><div class="value">{html_value(selected.get("ai_event_type"))}</div>
            <div class="key">신뢰도</div><div class="value">{'-' if pd.isna(selected.get("confidence")) else f'{selected.get("confidence"):.2f}'}</div>
            <div class="key">DART</div><div class="value"><a href="{html_value(selected.get("dart_url"))}" target="_blank">원문 보기</a></div>
            <div class="key">원문 수집</div><div class="value">{html_value(document_status(selected))}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_metric_detail(selected)


def render_disclosure_insight(selected: dict[str, object], selected_id: int) -> None:
    st.markdown('<div class="section-label">AI & Notes</div>', unsafe_allow_html=True)
    render_ai_detail(selected)
    render_note_form(selected_id)


def document_status(selected: dict[str, object]) -> str:
    if display_value(selected.get("document_text")) != "-":
        return "완료"
    if display_value(selected.get("document_error")) != "-":
        return "오류"
    return "대기"


def render_metric_detail(selected: dict[str, object]) -> None:
    metric_values = [
        ("계약금액", selected.get("contract_amount"), ""),
        ("최근매출", selected.get("recent_sales"), ""),
        ("매출대비", selected.get("sales_ratio"), "%"),
        ("자사주", selected.get("treasury_buyback_amount"), ""),
        ("시설투자", selected.get("facility_investment_amount"), ""),
        ("자기자본대비", selected.get("equity_ratio"), "%"),
        ("신주수", selected.get("new_share_count"), "주"),
        ("희석률", selected.get("dilution_ratio"), "%"),
    ]
    visible_metrics = [(label, value, suffix) for label, value, suffix in metric_values if display_value(value) != "-"]
    metric_details = parse_json_dict(selected.get("metric_details_json"))

    if visible_metrics or metric_details:
        st.markdown("##### 핵심 숫자")
        metric_lines = [
            f'<div class="metric-row"><span class="key">{escape(label)}</span><span class="value">{html_value(format_number(value, suffix))}</span></div>'
            for label, value, suffix in visible_metrics
        ]
        if metric_lines:
            st.markdown('<div class="metric-list">' + "".join(metric_lines) + "</div>", unsafe_allow_html=True)
        detail_lines = [
            f"<strong>{escape(DETAIL_LABELS.get(key, key))}</strong>: {html_value(value)}"
            for key, value in metric_details.items()
            if display_value(value) != "-"
        ]
        if detail_lines:
            st.markdown('<div class="note">' + "<br>".join(detail_lines) + "</div>", unsafe_allow_html=True)

    if display_value(selected.get("document_error")) != "-":
        st.warning(f"원문 수집 오류: {display_value(selected.get('document_error'))}")


def render_ai_detail(selected: dict[str, object]) -> None:
    summary = selected.get("summary")
    if summary and not pd.isna(summary):
        st.markdown("##### AI 요약")
        st.markdown(f'<div class="note">{html_value(summary)}</div>', unsafe_allow_html=True)
    else:
        st.markdown("##### AI 요약")
        st.markdown('<div class="note">AI 요약 대기 상태입니다. 규칙 분류와 핵심 숫자를 먼저 확인하세요.</div>', unsafe_allow_html=True)

    reason = selected.get("reason")
    if reason and not pd.isna(reason):
        st.markdown("##### 분류 근거")
        st.markdown(f'<div class="note">{html_value(reason)}</div>', unsafe_allow_html=True)

    watch_points = parse_json_list(selected.get("watch_points_json"))
    if watch_points:
        st.markdown("##### 확인할 포인트")
        for point in watch_points:
            st.write(f"- {point}")


def render_note_form(selected_id: int) -> None:
    with connect(settings.database_path) as conn:
        note = get_note(conn, selected_id)
    current_note = "" if note is None else note["user_note"] or ""
    current_status = "new" if note is None else note["status"]
    status_values = ["new", "watch", "reviewed", "avoid", "archived"]

    st.markdown("##### 내 판단")
    with st.form(key=f"note-form-{selected_id}"):
        status = st.selectbox(
            "상태",
            status_values,
            index=status_values.index(current_status) if current_status in status_values else 0,
        )
        user_note = st.text_area("메모", value=current_note, height=150)
        submitted = st.form_submit_button("저장", use_container_width=True)

    if submitted:
        with connect(settings.database_path) as conn:
            upsert_note(conn, selected_id, user_note=user_note, status=status)
        st.success("저장했습니다. 새로고침하면 목록 상태에도 반영됩니다.")


def render_summary_tab(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("일일 요약을 만들 공시 데이터가 아직 없습니다.")
        return

    st.markdown('<div class="section-heading"><h3>리포트</h3><span class="muted-line">날짜별 위험, 이벤트, 수동검토 공시를 요약합니다</span></div>', unsafe_allow_html=True)
    available_dates = sorted(df["receipt_date"].dropna().unique().tolist(), reverse=True)
    selected_report_date = st.selectbox("리포트 날짜", available_dates)

    with connect(settings.database_path) as conn:
        report_rows = [dict(row) for row in fetch_report_rows(conn, selected_report_date)]
    report_df = pd.DataFrame(report_rows)

    render_report_metrics(report_df)
    render_summary_cards(report_df)

    report_text = build_daily_report(report_rows, selected_report_date)
    st.download_button(
        "Markdown 다운로드",
        data=report_text,
        file_name=f"daily-{selected_report_date}.md",
        mime="text/markdown",
        use_container_width=True,
    )
    st.markdown("#### 리포트 미리보기")
    st.markdown(report_text)


def render_report_metrics(report_df: pd.DataFrame) -> None:
    cols = st.columns(4)
    if report_df.empty:
        for col, label in zip(cols, ["전체", "위험", "단기", "수동검토"]):
            col.metric(label, "0")
        return
    cols[0].metric("전체", f"{len(report_df):,}")
    cols[1].metric("위험", f"{((report_df['rule_category'] == 'risk') | (report_df['ai_category'] == 'risk')).sum():,}")
    cols[2].metric("단기", f"{((report_df['rule_category'] == 'short_term_event') | (report_df['ai_category'] == 'short_term_event')).sum():,}")
    cols[3].metric("수동검토", f"{report_df['recommended_action'].isin(['manual_review', 'hold_for_more_data']).sum():,}")


def render_summary_cards(report_df: pd.DataFrame) -> None:
    if report_df.empty:
        st.info("해당 날짜에 리포트로 표시할 공시가 없습니다.")
        return
    risk_rows = report_df[(report_df["rule_category"] == "risk") | (report_df["ai_category"] == "risk")]
    event_rows = report_df[(report_df["rule_category"] == "short_term_event") | (report_df["ai_category"] == "short_term_event")]
    manual_rows = report_df[report_df["recommended_action"].isin(["manual_review", "hold_for_more_data"])]

    cols = st.columns(3)
    with cols[0]:
        st.markdown('<div class="section-label">Risk Top</div>', unsafe_allow_html=True)
        render_compact_rows(risk_rows, "위험 공시 없음")
    with cols[1]:
        st.markdown('<div class="section-label">Event Top</div>', unsafe_allow_html=True)
        render_compact_rows(event_rows, "단기 후보 없음")
    with cols[2]:
        st.markdown('<div class="section-label">Manual Review</div>', unsafe_allow_html=True)
        render_compact_rows(manual_rows, "수동검토 없음")


def render_compact_rows(rows: pd.DataFrame, empty_text: str) -> None:
    if rows.empty:
        st.markdown(f'<div class="note">{empty_text}</div>', unsafe_allow_html=True)
        return
    for _, row in rows.head(5).iterrows():
        metrics = metric_summary(row.to_dict())
        st.markdown(
            f"""
            <div class="panel">
              <div class="selected-title">{display_value(row.get("corp_name"))}</div>
              <div class="selected-meta">{display_value(row.get("stock_code"))} · {display_value(row.get("recommended_action"))} · {display_value(row.get("risk_level"))}</div>
              <div>{display_value(row.get("report_name"))}</div>
              <div style="margin-top:.45rem;color:#667085;font-size:.86rem;">{metrics or display_value(row.get("summary") or row.get("reason"))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_notes_tab(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("관심/메모로 볼 공시 데이터가 아직 없습니다.")
        return

    note_df = df[
        (df["note_status"].fillna("new") != "new")
        | (df["user_note"].fillna("").astype(str).str.strip() != "")
    ].copy()

    st.markdown('<div class="section-heading"><h3>관심/메모</h3><span class="muted-line">직접 남긴 판단과 복기 대상을 모아봅니다</span></div>', unsafe_allow_html=True)
    cols = st.columns(5)
    cols[0].metric("전체 메모", f"{len(note_df):,}")
    for index, status in enumerate(["watch", "reviewed", "avoid", "archived"], start=1):
        cols[index].metric(status, f"{(note_df['note_status'] == status).sum() if not note_df.empty else 0:,}")

    filter_col, search_col = st.columns([.35, .65])
    with filter_col:
        status_options = ["all", "watch", "reviewed", "avoid", "archived"]
        selected_status = st.selectbox("상태", status_options, key="notes-status")
    with search_col:
        query = st.text_input("회사명/공시명/메모 검색", key="notes-search")

    filtered = note_df
    if selected_status != "all":
        filtered = filtered[filtered["note_status"] == selected_status]
    if query.strip():
        text = query.strip()
        filtered = filtered[
            filtered["corp_name"].fillna("").str.contains(text, case=False, regex=False)
            | filtered["report_name"].fillna("").str.contains(text, case=False, regex=False)
            | filtered["user_note"].fillna("").str.contains(text, case=False, regex=False)
        ]

    if filtered.empty:
        st.markdown('<div class="note">선택한 조건에 맞는 관심/메모 공시가 없습니다.</div>', unsafe_allow_html=True)
        return

    list_col, detail_col = st.columns([1.05, .95], gap="large")
    with list_col:
        st.dataframe(
            filtered[
                [
                    "receipt_date",
                    "corp_name",
                    "stock_code",
                    "report_name",
                    "rule_category",
                    "recommended_action",
                    "note_status",
                    "user_note",
                ]
            ].fillna("-"),
            use_container_width=True,
            hide_index=True,
            height=520,
            column_config={
                "receipt_date": st.column_config.TextColumn("접수일", width="small"),
                "corp_name": st.column_config.TextColumn("회사", width="small"),
                "stock_code": st.column_config.TextColumn("코드", width="small"),
                "report_name": st.column_config.TextColumn("공시명", width="large"),
                "rule_category": st.column_config.TextColumn("분류", width="medium"),
                "recommended_action": st.column_config.TextColumn("액션", width="small"),
                "note_status": st.column_config.TextColumn("상태", width="small"),
                "user_note": st.column_config.TextColumn("메모", width="large"),
            },
        )
        selected_id = st.selectbox(
            "메모 상세",
            filtered["id"].tolist(),
            format_func=lambda disclosure_id: filtered.loc[
                filtered["id"] == disclosure_id, "display_name"
            ].iloc[0],
        )
    selected = filtered.loc[filtered["id"] == selected_id].iloc[0].to_dict()
    with detail_col:
        render_review_card(pd.Series(selected))
        render_disclosure_insight(selected, int(selected_id))


def load_operation_state() -> tuple[list[dict[str, object]], list[dict[str, object]], int]:
    with connect(settings.database_path) as conn:
        job_runs = [dict(row) for row in fetch_recent_job_runs(conn, limit=20)]
        document_errors = [
            dict(row)
            for row in conn.execute(
                """
                SELECT receipt_date, corp_name, stock_code, report_name, document_error, document_fetched_at
                FROM disclosures
                WHERE document_error IS NOT NULL
                ORDER BY document_fetched_at DESC, id DESC
                LIMIT 20
                """
            ).fetchall()
        ]
        ai_pending_count = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM classifications
            WHERE ai_category IS NULL
            """
        ).fetchone()["count"]
    return job_runs, document_errors, int(ai_pending_count)


def render_operations_tab() -> None:
    job_runs, document_errors, ai_pending_count = load_operation_state()

    st.markdown('<div class="section-heading"><h3>운영</h3><span class="muted-line">자동 실행, 처리량, 오류 상태를 확인합니다</span></div>', unsafe_allow_html=True)

    if not job_runs:
        st.info("아직 자동 실행 이력이 없습니다. `uv run disclosure-investing run-daily --document-limit 20 --ai-limit 10`를 실행하면 기록됩니다.")
        return

    latest = job_runs[0]
    status = display_value(latest.get("status"))
    status_tone = "long" if status == "success" else "risk" if status == "failed" else "manual"
    st.markdown(
        f"""
        <div class="panel">
          <div class="section-label">Latest Job</div>
          <div class="selected-title">자동 실행 {badge(status, status_tone)}</div>
          <div class="selected-meta">
            시작 {display_value(latest.get("started_at"))} · 종료 {display_value(latest.get("finished_at"))} · 대상일 {display_value(latest.get("target_date"))}
          </div>
          <div class="kv">
            <div class="key">리포트</div><div class="value">{display_value(latest.get("report_path"))}</div>
            <div class="key">오류</div><div class="value">{display_value(latest.get("error_message"))}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(6)
    cols[0].metric("수집", f"{int(latest.get('fetched_count') or 0):,}")
    cols[1].metric("신규", f"{int(latest.get('inserted_count') or 0):,}")
    cols[2].metric("원문", f"{int(latest.get('document_count') or 0):,}")
    cols[3].metric("지표", f"{int(latest.get('metric_count') or 0):,}")
    cols[4].metric("AI", f"{int(latest.get('ai_count') or 0):,}")
    cols[5].metric("AI 대기", f"{ai_pending_count:,}")

    report_path = display_value(latest.get("report_path"))
    if report_path != "-":
        path = Path(report_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        if path.exists():
            st.download_button(
                "최근 리포트 다운로드",
                data=path.read_text(encoding="utf-8"),
                file_name=path.name,
                mime="text/markdown",
                use_container_width=True,
            )

    st.markdown("#### 최근 실행 이력")
    st.dataframe(
        pd.DataFrame(job_runs),
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "job_name": st.column_config.TextColumn("작업", width="small"),
            "target_date": st.column_config.TextColumn("대상일", width="small"),
            "started_at": st.column_config.TextColumn("시작", width="medium"),
            "finished_at": st.column_config.TextColumn("종료", width="medium"),
            "status": st.column_config.TextColumn("상태", width="small"),
            "fetched_count": st.column_config.NumberColumn("수집", width="small"),
            "inserted_count": st.column_config.NumberColumn("신규", width="small"),
            "document_count": st.column_config.NumberColumn("원문", width="small"),
            "metric_count": st.column_config.NumberColumn("지표", width="small"),
            "ai_count": st.column_config.NumberColumn("AI", width="small"),
            "report_path": st.column_config.TextColumn("리포트", width="medium"),
            "error_message": st.column_config.TextColumn("오류", width="large"),
        },
    )

    st.markdown("#### 최근 원문 수집 오류")
    if document_errors:
        st.dataframe(pd.DataFrame(document_errors), use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="note">최근 원문 수집 오류가 없습니다.</div>', unsafe_allow_html=True)


data = load_rows()
df = prepare_dataframe(data) if data else pd.DataFrame()
selected_page = render_sidebar_navigation()
render_header(selected_page)

if selected_page == "오늘":
    render_today_tab(df)
elif selected_page == "긍정 공시":
    render_positive_tab(df)
elif selected_page == "공시함":
    if df.empty:
        st.info("아직 저장된 공시가 없습니다. `uv run disclosure-investing fetch-disclosures`를 먼저 실행하세요.")
    else:
        render_monitor_tab(df)
elif selected_page == "관심/메모":
    render_notes_tab(df)
elif selected_page == "리포트":
    render_summary_tab(df)
elif selected_page == "운영":
    render_operations_tab()
