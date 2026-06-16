from app.database import connect, create_job_run, fetch_recent_job_runs, finish_job_run, init_db


def test_job_run_lifecycle(tmp_path) -> None:
    database_path = tmp_path / "test.db"
    init_db(database_path)

    with connect(database_path) as conn:
        job_run_id = create_job_run(conn, "run_daily", "20260616")
        finish_job_run(
            conn,
            job_run_id,
            status="success",
            fetched_count=12,
            inserted_count=3,
            document_count=4,
            metric_count=5,
            ai_count=2,
            report_path="reports/daily-20260616.md",
        )
        rows = fetch_recent_job_runs(conn)

    assert len(rows) == 1
    assert rows[0]["job_name"] == "run_daily"
    assert rows[0]["target_date"] == "20260616"
    assert rows[0]["status"] == "success"
    assert rows[0]["fetched_count"] == 12
    assert rows[0]["inserted_count"] == 3
    assert rows[0]["document_count"] == 4
    assert rows[0]["metric_count"] == 5
    assert rows[0]["ai_count"] == 2
    assert rows[0]["report_path"] == "reports/daily-20260616.md"
    assert rows[0]["finished_at"] is not None
