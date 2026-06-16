from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path

from app.ai_classifier import classify_with_openai
from app.config import load_settings
from app.dart_client import DartClient
from app.database import (
    connect,
    create_job_run,
    fetch_ai_pending_disclosures,
    fetch_document_pending_disclosures,
    fetch_metric_rebuild_disclosures,
    fetch_report_rows,
    fetch_unclassified_disclosures,
    finish_job_run,
    init_db,
    insert_disclosures,
    update_document_text,
    update_document_error,
    update_ai_classification,
    upsert_metrics,
    upsert_rule_classification,
)
from app.document_parser import extract_metrics
from app.reporting import build_daily_report, write_report
from app.rule_classifier import classify_report


def parse_date(value: str | None) -> date:
    if not value:
        return date.today()
    return datetime.strptime(value, "%Y-%m-%d").date()


def dart_date(value: date) -> str:
    return value.strftime("%Y%m%d")


def cmd_init_db() -> None:
    settings = load_settings()
    init_db(settings.database_path)
    print(f"Initialized database: {settings.database_path}")


def cmd_fetch_disclosures(args: argparse.Namespace) -> tuple[int, int]:
    settings = load_settings()
    client = DartClient(settings.dart_api_key)
    target_date = parse_date(args.date)
    disclosures = client.list_disclosures(target_date)

    init_db(settings.database_path)
    with connect(settings.database_path) as conn:
        inserted = insert_disclosures(conn, disclosures)

    print(f"Fetched {len(disclosures)} disclosures, inserted {inserted}.")
    return len(disclosures), inserted


def cmd_classify_rules() -> int:
    settings = load_settings()
    init_db(settings.database_path)

    with connect(settings.database_path) as conn:
        rows = fetch_unclassified_disclosures(conn)
        for row in rows:
            classification = classify_report(row["report_name"])
            upsert_rule_classification(
                conn,
                disclosure_id=row["id"],
                category=classification.category,
                event_type=classification.event_type,
                recommended_action=classification.recommended_action,
                reason=classification.reason,
            )

    print(f"Rule-classified {len(rows)} disclosures.")
    return len(rows)


def cmd_classify_ai(args: argparse.Namespace) -> int:
    settings = load_settings()
    init_db(settings.database_path)

    updated = 0
    with connect(settings.database_path) as conn:
        rows = fetch_ai_pending_disclosures(conn, args.limit, include_existing=args.force)
        for row in rows:
            disclosure = dict(row)
            result = classify_with_openai(
                disclosure,
                api_key=settings.openai_api_key,
                model=settings.openai_model,
            )
            update_ai_classification(
                conn,
                disclosure_id=row["id"],
                ai_category=result.primary_category,
                ai_event_type=result.event_type,
                sentiment=result.sentiment,
                risk_level=result.risk_level,
                confidence=result.confidence,
                summary=result.summary,
                reason=result.reason,
                watch_points=result.watch_points,
                recommended_action=result.recommended_action,
            )
            updated += 1
            print(f"AI-classified {row['corp_name']} / {row['report_name']}")

    print(f"AI-classified {updated} disclosures.")
    return updated


def cmd_fetch_documents(args: argparse.Namespace) -> int:
    settings = load_settings()
    init_db(settings.database_path)
    client = DartClient(settings.dart_api_key)

    updated = 0
    with connect(settings.database_path) as conn:
        rows = fetch_document_pending_disclosures(conn, args.limit)
        for row in rows:
            try:
                document_text = client.get_document_text(row["receipt_no"])
            except Exception as exc:
                update_document_error(conn, row["id"], str(exc))
                print(f"Skipped document {row['corp_name']} / {row['report_name']}: {exc}")
                continue
            update_document_text(conn, row["id"], document_text)
            save_extracted_metrics(conn, row, document_text)
            updated += 1
            print(f"Fetched document {row['corp_name']} / {row['report_name']}")

    print(f"Fetched {updated} disclosure documents.")
    return updated


def save_extracted_metrics(conn, row, document_text: str) -> None:
    metrics = extract_metrics(row["report_name"], document_text)
    upsert_metrics(
        conn,
        row["id"],
        contract_amount=metrics.contract_amount,
        recent_sales=metrics.recent_sales,
        sales_ratio=metrics.sales_ratio,
        treasury_buyback_amount=metrics.treasury_buyback_amount,
        facility_investment_amount=metrics.facility_investment_amount,
        equity_capital=metrics.equity_capital,
        equity_ratio=metrics.equity_ratio,
        new_share_count=metrics.new_share_count,
        existing_share_count=metrics.existing_share_count,
        dilution_ratio=metrics.dilution_ratio,
        metric_details=metrics.details,
    )


def cmd_rebuild_metrics(args: argparse.Namespace) -> int:
    settings = load_settings()
    init_db(settings.database_path)

    updated = 0
    with connect(settings.database_path) as conn:
        rows = fetch_metric_rebuild_disclosures(conn, args.limit)
        for row in rows:
            save_extracted_metrics(conn, row, row["document_text"])
            updated += 1
            print(f"Rebuilt metrics {row['corp_name']} / {row['report_name']}")

    print(f"Rebuilt metrics for {updated} disclosures.")
    return updated


def cmd_run_daily(args: argparse.Namespace) -> None:
    settings = load_settings()
    init_db(settings.database_path)
    target_date = dart_date(parse_date(args.date))
    stats = {
        "fetched_count": 0,
        "inserted_count": 0,
        "document_count": 0,
        "metric_count": 0,
        "ai_count": 0,
        "report_path": None,
    }

    with connect(settings.database_path) as conn:
        job_run_id = create_job_run(conn, "run_daily", target_date)

    try:
        print("Step 1/6: fetch disclosures")
        fetched_count, inserted_count = cmd_fetch_disclosures(args)
        stats["fetched_count"] = fetched_count
        stats["inserted_count"] = inserted_count

        print("Step 2/6: classify rules")
        cmd_classify_rules()

        print("Step 3/6: fetch documents")
        document_args = argparse.Namespace(limit=args.document_limit)
        stats["document_count"] = cmd_fetch_documents(document_args)

        print("Step 4/6: rebuild metrics")
        rebuild_args = argparse.Namespace(limit=args.metric_limit)
        stats["metric_count"] = cmd_rebuild_metrics(rebuild_args)

        print("Step 5/6: classify AI")
        ai_args = argparse.Namespace(limit=args.ai_limit, force=args.force_ai)
        stats["ai_count"] = cmd_classify_ai(ai_args)

        print("Step 6/6: write daily report")
        report_args = argparse.Namespace(date=args.date, output=args.report_output)
        report_path = cmd_daily_report(report_args)
        stats["report_path"] = str(report_path)
    except Exception as exc:
        with connect(settings.database_path) as conn:
            finish_job_run(conn, job_run_id, status="failed", error_message=str(exc), **stats)
        print(f"Daily job failed: {exc}")
        raise

    with connect(settings.database_path) as conn:
        finish_job_run(conn, job_run_id, status="success", **stats)
    print(f"Daily job recorded: #{job_run_id}")


def cmd_daily_report(args: argparse.Namespace) -> Path:
    settings = load_settings()
    init_db(settings.database_path)
    target_date = dart_date(parse_date(args.date))

    with connect(settings.database_path) as conn:
        rows = [dict(row) for row in fetch_report_rows(conn, target_date)]

    report_text = build_daily_report(rows, target_date)
    output_path = Path(args.output or f"reports/daily-{target_date}.md")
    write_report(report_text, output_path)
    print(f"Wrote report: {output_path}")
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Disclosure investing tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="Initialize the SQLite database")

    fetch_parser = subparsers.add_parser("fetch-disclosures", help="Fetch DART disclosures")
    fetch_parser.add_argument("--date", help="Target date in YYYY-MM-DD format. Defaults to today.")

    document_parser = subparsers.add_parser("fetch-documents", help="Fetch DART disclosure documents")
    document_parser.add_argument("--limit", type=int, default=10, help="Maximum number of documents to fetch")

    rebuild_parser = subparsers.add_parser("rebuild-metrics", help="Rebuild metrics from stored documents")
    rebuild_parser.add_argument("--limit", type=int, default=100, help="Maximum number of stored documents to rebuild")

    subparsers.add_parser("classify-rules", help="Classify unclassified disclosures with local rules")

    ai_parser = subparsers.add_parser("classify-ai", help="Classify disclosures with OpenAI")
    ai_parser.add_argument("--limit", type=int, default=10, help="Maximum number of disclosures to classify")
    ai_parser.add_argument("--force", action="store_true", help="Reclassify disclosures that already have AI results")

    daily_parser = subparsers.add_parser("run-daily", help="Run daily disclosure collection and classification")
    daily_parser.add_argument("--date", help="Target date in YYYY-MM-DD format. Defaults to today.")
    daily_parser.add_argument("--document-limit", type=int, default=20, help="Maximum number of documents to fetch")
    daily_parser.add_argument("--metric-limit", type=int, default=100, help="Maximum number of stored documents to rebuild")
    daily_parser.add_argument("--ai-limit", type=int, default=10, help="Maximum number of disclosures to classify with AI")
    daily_parser.add_argument("--force-ai", action="store_true", help="Reclassify disclosures that already have AI results")
    daily_parser.add_argument("--report-output", help="Output markdown path for daily report")

    report_parser = subparsers.add_parser("daily-report", help="Write a daily disclosure summary report")
    report_parser.add_argument("--date", help="Target date in YYYY-MM-DD format. Defaults to today.")
    report_parser.add_argument("--output", help="Output markdown path. Defaults to reports/daily-YYYYMMDD.md")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init-db":
        cmd_init_db()
    elif args.command == "fetch-disclosures":
        cmd_fetch_disclosures(args)
    elif args.command == "fetch-documents":
        cmd_fetch_documents(args)
    elif args.command == "rebuild-metrics":
        cmd_rebuild_metrics(args)
    elif args.command == "classify-rules":
        cmd_classify_rules()
    elif args.command == "classify-ai":
        cmd_classify_ai(args)
    elif args.command == "run-daily":
        cmd_run_daily(args)
    elif args.command == "daily-report":
        cmd_daily_report(args)
    else:
        parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
