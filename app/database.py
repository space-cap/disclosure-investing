from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS disclosures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_no TEXT NOT NULL UNIQUE,
    receipt_date TEXT NOT NULL,
    receipt_time TEXT,
    corp_code TEXT,
    corp_name TEXT NOT NULL,
    stock_code TEXT,
    report_name TEXT NOT NULL,
    market TEXT,
    dart_url TEXT,
    is_correction INTEGER NOT NULL DEFAULT 0,
    document_text TEXT,
    document_fetched_at TEXT,
    document_error TEXT,
    raw_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS classifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    disclosure_id INTEGER NOT NULL,
    rule_category TEXT,
    rule_event_type TEXT,
    ai_category TEXT,
    ai_event_type TEXT,
    sentiment TEXT,
    risk_level TEXT,
    confidence REAL,
    summary TEXT,
    reason TEXT,
    watch_points_json TEXT,
    recommended_action TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(disclosure_id),
    FOREIGN KEY(disclosure_id) REFERENCES disclosures(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    disclosure_id INTEGER NOT NULL,
    contract_amount REAL,
    recent_sales REAL,
    sales_ratio REAL,
    treasury_buyback_amount REAL,
    facility_investment_amount REAL,
    equity_capital REAL,
    equity_ratio REAL,
    new_share_count REAL,
    existing_share_count REAL,
    dilution_ratio REAL,
    metric_details_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(disclosure_id),
    FOREIGN KEY(disclosure_id) REFERENCES disclosures(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    disclosure_id INTEGER NOT NULL,
    user_note TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(disclosure_id),
    FOREIGN KEY(disclosure_id) REFERENCES disclosures(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS job_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_name TEXT NOT NULL,
    target_date TEXT,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    fetched_count INTEGER NOT NULL DEFAULT 0,
    inserted_count INTEGER NOT NULL DEFAULT 0,
    document_count INTEGER NOT NULL DEFAULT 0,
    metric_count INTEGER NOT NULL DEFAULT 0,
    ai_count INTEGER NOT NULL DEFAULT 0,
    report_path TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(database_path: Path) -> None:
    with connect(database_path) as conn:
        conn.executescript(SCHEMA_SQL)
        ensure_schema(conn)


def ensure_schema(conn: sqlite3.Connection) -> None:
    ensure_columns(
        conn,
        "disclosures",
        {
            "document_text": "TEXT",
            "document_fetched_at": "TEXT",
            "document_error": "TEXT",
        },
    )
    ensure_columns(
        conn,
        "metrics",
        {
            "metric_details_json": "TEXT",
        },
    )
    ensure_columns(
        conn,
        "job_runs",
        {
            "target_date": "TEXT",
            "fetched_count": "INTEGER NOT NULL DEFAULT 0",
            "inserted_count": "INTEGER NOT NULL DEFAULT 0",
            "document_count": "INTEGER NOT NULL DEFAULT 0",
            "metric_count": "INTEGER NOT NULL DEFAULT 0",
            "ai_count": "INTEGER NOT NULL DEFAULT 0",
            "report_path": "TEXT",
            "error_message": "TEXT",
        },
    )


def ensure_columns(conn: sqlite3.Connection, table_name: str, columns: dict[str, str]) -> None:
    existing = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    for column_name, column_type in columns.items():
        if column_name not in existing:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def insert_disclosures(conn: sqlite3.Connection, disclosures: Iterable[dict[str, Any]]) -> int:
    inserted = 0
    for item in disclosures:
        receipt_no = item.get("rcept_no") or item.get("receipt_no")
        if not receipt_no:
            continue

        report_name = item.get("report_nm") or item.get("report_name") or ""
        is_correction = 1 if "정정" in report_name else 0
        dart_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={receipt_no}"

        cur = conn.execute(
            """
            INSERT OR IGNORE INTO disclosures (
                receipt_no, receipt_date, corp_code, corp_name, stock_code,
                report_name, market, dart_url, is_correction, raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                receipt_no,
                item.get("rcept_dt") or item.get("receipt_date") or "",
                item.get("corp_code"),
                item.get("corp_name") or "",
                item.get("stock_code"),
                report_name,
                item.get("corp_cls") or item.get("market"),
                dart_url,
                is_correction,
                json.dumps(item, ensure_ascii=False),
            ),
        )
        inserted += cur.rowcount
    conn.commit()
    return inserted


def fetch_unclassified_disclosures(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT d.*
        FROM disclosures d
        LEFT JOIN classifications c ON c.disclosure_id = d.id
        WHERE c.id IS NULL
        ORDER BY d.receipt_date DESC, d.id DESC
        """
    ).fetchall()


def fetch_ai_pending_disclosures(
    conn: sqlite3.Connection,
    limit: int,
    *,
    include_existing: bool = False,
) -> list[sqlite3.Row]:
    where_clause = "1 = 1" if include_existing else "c.ai_category IS NULL"
    return conn.execute(
        f"""
        SELECT
            d.*,
            c.rule_category,
            c.rule_event_type,
            c.recommended_action AS rule_recommended_action,
            c.reason AS rule_reason,
            m.contract_amount,
            m.recent_sales,
            m.sales_ratio,
            m.treasury_buyback_amount,
            m.facility_investment_amount,
            m.equity_capital,
            m.equity_ratio,
            m.new_share_count,
            m.existing_share_count,
            m.dilution_ratio,
            m.metric_details_json
        FROM disclosures d
        JOIN classifications c ON c.disclosure_id = d.id
        LEFT JOIN metrics m ON m.disclosure_id = d.id
        WHERE {where_clause}
        ORDER BY
            CASE c.rule_category
                WHEN 'risk' THEN 1
                WHEN 'short_term_event' THEN 2
                WHEN 'long_term_candidate' THEN 3
                WHEN 'manual_review' THEN 4
                ELSE 5
            END,
            d.receipt_date DESC,
            d.id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def fetch_document_pending_disclosures(conn: sqlite3.Connection, limit: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
            d.*,
            c.rule_category,
            c.rule_event_type
        FROM disclosures d
        LEFT JOIN classifications c ON c.disclosure_id = d.id
        WHERE d.document_text IS NULL
          AND d.document_error IS NULL
        ORDER BY
            CASE c.rule_category
                WHEN 'risk' THEN 1
                WHEN 'short_term_event' THEN 2
                WHEN 'long_term_candidate' THEN 3
                WHEN 'manual_review' THEN 4
                ELSE 5
            END,
            d.receipt_date DESC,
            d.id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def fetch_metric_rebuild_disclosures(conn: sqlite3.Connection, limit: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT *
        FROM disclosures
        WHERE document_text IS NOT NULL
        ORDER BY document_fetched_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def fetch_report_rows(conn: sqlite3.Connection, target_date: str) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
            d.id,
            d.receipt_date,
            d.corp_name,
            d.stock_code,
            d.report_name,
            d.dart_url,
            c.rule_category,
            c.rule_event_type,
            c.ai_category,
            c.ai_event_type,
            c.risk_level,
            c.confidence,
            c.summary,
            c.reason,
            c.recommended_action,
            m.contract_amount,
            m.recent_sales,
            m.sales_ratio,
            m.treasury_buyback_amount,
            m.facility_investment_amount,
            m.equity_ratio,
            m.new_share_count,
            m.existing_share_count,
            m.dilution_ratio
        FROM disclosures d
        LEFT JOIN classifications c ON c.disclosure_id = d.id
        LEFT JOIN metrics m ON m.disclosure_id = d.id
        WHERE d.receipt_date = ?
        ORDER BY
            CASE c.rule_category
                WHEN 'risk' THEN 1
                WHEN 'short_term_event' THEN 2
                WHEN 'long_term_candidate' THEN 3
                WHEN 'manual_review' THEN 4
                ELSE 5
            END,
            d.id DESC
        """,
        (target_date,),
    ).fetchall()


def update_document_text(
    conn: sqlite3.Connection,
    disclosure_id: int,
    document_text: str,
) -> None:
    conn.execute(
        """
        UPDATE disclosures
        SET document_text = ?, document_fetched_at = CURRENT_TIMESTAMP, document_error = NULL
        WHERE id = ?
        """,
        (document_text, disclosure_id),
    )
    conn.commit()


def update_document_error(
    conn: sqlite3.Connection,
    disclosure_id: int,
    error_message: str,
) -> None:
    conn.execute(
        """
        UPDATE disclosures
        SET document_error = ?, document_fetched_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (error_message[:500], disclosure_id),
    )
    conn.commit()


def upsert_rule_classification(
    conn: sqlite3.Connection,
    disclosure_id: int,
    category: str,
    event_type: str,
    recommended_action: str,
    reason: str,
) -> None:
    conn.execute(
        """
        INSERT INTO classifications (
            disclosure_id, rule_category, rule_event_type, recommended_action, reason
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(disclosure_id) DO UPDATE SET
            rule_category = excluded.rule_category,
            rule_event_type = excluded.rule_event_type,
            recommended_action = excluded.recommended_action,
            reason = excluded.reason
        """,
        (disclosure_id, category, event_type, recommended_action, reason),
    )
    conn.commit()


def update_ai_classification(
    conn: sqlite3.Connection,
    disclosure_id: int,
    *,
    ai_category: str,
    ai_event_type: str,
    sentiment: str,
    risk_level: str,
    confidence: float,
    summary: str,
    reason: str,
    watch_points: list[str],
    recommended_action: str,
) -> None:
    conn.execute(
        """
        UPDATE classifications
        SET
            ai_category = ?,
            ai_event_type = ?,
            sentiment = ?,
            risk_level = ?,
            confidence = ?,
            summary = ?,
            reason = ?,
            watch_points_json = ?,
            recommended_action = ?
        WHERE disclosure_id = ?
        """,
        (
            ai_category,
            ai_event_type,
            sentiment,
            risk_level,
            confidence,
            summary,
            reason,
            json.dumps(watch_points, ensure_ascii=False),
            recommended_action,
            disclosure_id,
        ),
    )
    conn.commit()


def get_note(conn: sqlite3.Connection, disclosure_id: int) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT disclosure_id, user_note, status
        FROM notes
        WHERE disclosure_id = ?
        """,
        (disclosure_id,),
    ).fetchone()


def upsert_note(
    conn: sqlite3.Connection,
    disclosure_id: int,
    *,
    user_note: str,
    status: str,
) -> None:
    conn.execute(
        """
        INSERT INTO notes (disclosure_id, user_note, status)
        VALUES (?, ?, ?)
        ON CONFLICT(disclosure_id) DO UPDATE SET
            user_note = excluded.user_note,
            status = excluded.status,
            updated_at = CURRENT_TIMESTAMP
        """,
        (disclosure_id, user_note, status),
    )
    conn.commit()


def upsert_metrics(
    conn: sqlite3.Connection,
    disclosure_id: int,
    *,
    contract_amount: float | None = None,
    recent_sales: float | None = None,
    sales_ratio: float | None = None,
    treasury_buyback_amount: float | None = None,
    facility_investment_amount: float | None = None,
    equity_capital: float | None = None,
    equity_ratio: float | None = None,
    new_share_count: float | None = None,
    existing_share_count: float | None = None,
    dilution_ratio: float | None = None,
    metric_details: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO metrics (
            disclosure_id,
            contract_amount,
            recent_sales,
            sales_ratio,
            treasury_buyback_amount,
            facility_investment_amount,
            equity_capital,
            equity_ratio,
            new_share_count,
            existing_share_count,
            dilution_ratio,
            metric_details_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(disclosure_id) DO UPDATE SET
            contract_amount = excluded.contract_amount,
            recent_sales = excluded.recent_sales,
            sales_ratio = excluded.sales_ratio,
            treasury_buyback_amount = excluded.treasury_buyback_amount,
            facility_investment_amount = excluded.facility_investment_amount,
            equity_capital = excluded.equity_capital,
            equity_ratio = excluded.equity_ratio,
            new_share_count = excluded.new_share_count,
            existing_share_count = excluded.existing_share_count,
            dilution_ratio = excluded.dilution_ratio,
            metric_details_json = excluded.metric_details_json
        """,
        (
            disclosure_id,
            contract_amount,
            recent_sales,
            sales_ratio,
            treasury_buyback_amount,
            facility_investment_amount,
            equity_capital,
            equity_ratio,
            new_share_count,
            existing_share_count,
            dilution_ratio,
            json.dumps(metric_details or {}, ensure_ascii=False),
        ),
    )
    conn.commit()


def create_job_run(conn: sqlite3.Connection, job_name: str, target_date: str | None = None) -> int:
    cur = conn.execute(
        """
        INSERT INTO job_runs (job_name, target_date)
        VALUES (?, ?)
        """,
        (job_name, target_date),
    )
    conn.commit()
    return int(cur.lastrowid)


def finish_job_run(
    conn: sqlite3.Connection,
    job_run_id: int,
    *,
    status: str,
    fetched_count: int = 0,
    inserted_count: int = 0,
    document_count: int = 0,
    metric_count: int = 0,
    ai_count: int = 0,
    report_path: str | None = None,
    error_message: str | None = None,
) -> None:
    conn.execute(
        """
        UPDATE job_runs
        SET
            finished_at = CURRENT_TIMESTAMP,
            status = ?,
            fetched_count = ?,
            inserted_count = ?,
            document_count = ?,
            metric_count = ?,
            ai_count = ?,
            report_path = ?,
            error_message = ?
        WHERE id = ?
        """,
        (
            status,
            fetched_count,
            inserted_count,
            document_count,
            metric_count,
            ai_count,
            report_path,
            error_message[:1000] if error_message else None,
            job_run_id,
        ),
    )
    conn.commit()


def fetch_recent_job_runs(conn: sqlite3.Connection, limit: int = 20) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT *
        FROM job_runs
        ORDER BY started_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
