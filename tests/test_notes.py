from app.database import connect, get_note, init_db, insert_disclosures, upsert_note


def test_upsert_note(tmp_path) -> None:
    database_path = tmp_path / "test.db"
    init_db(database_path)

    with connect(database_path) as conn:
        insert_disclosures(
            conn,
            [
                {
                    "rcept_no": "202606160001",
                    "rcept_dt": "20260616",
                    "corp_name": "테스트",
                    "report_nm": "단일판매ㆍ공급계약체결",
                }
            ],
        )
        disclosure_id = conn.execute("SELECT id FROM disclosures").fetchone()["id"]

        upsert_note(conn, disclosure_id, user_note="처음 메모", status="watch")
        note = get_note(conn, disclosure_id)
        assert note is not None
        assert note["user_note"] == "처음 메모"
        assert note["status"] == "watch"

        upsert_note(conn, disclosure_id, user_note="수정 메모", status="reviewed")
        updated_note = get_note(conn, disclosure_id)
        assert updated_note is not None
        assert updated_note["user_note"] == "수정 메모"
        assert updated_note["status"] == "reviewed"
