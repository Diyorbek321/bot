import sqlite3

import pytest

import database as db


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "quiz.db"))
    db.init_db()


def add_student(user_id: int, name: str, results: list[tuple]) -> None:
    db.upsert_user(user_id, name, name.lower())
    for score, correct, total, mode in results:
        db.save_result(user_id, score, correct, total, 3, mode=mode, chat_id=-100)


def test_migration_adds_mode_to_old_results_table(tmp_path, monkeypatch):
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as conn:  # eski sxema: mode va chat_id yo'q
        conn.execute(
            "CREATE TABLE results (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, "
            "score INTEGER NOT NULL, correct INTEGER NOT NULL, total INTEGER NOT NULL, finished_at TEXT NOT NULL)"
        )
        conn.execute("INSERT INTO results (user_id, score, correct, total, finished_at) VALUES (1, 10, 1, 2, 'x')")
    monkeypatch.setattr(db, "DB_PATH", str(path))
    db.init_db()
    db.init_db()  # qayta ishga tushirish xavfsiz
    with sqlite3.connect(path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(results)")}
        assert {"mode", "chat_id"} <= columns
        assert conn.execute("SELECT COUNT(*) FROM results").fetchone()[0] == 1


def test_stats_and_student_list_sorted_by_score():
    add_student(1, "Ali", [(900, 40, 50, "day1")])
    add_student(2, "Vali", [(1500, 45, 50, "day1"), (300, 5, 10, "sent")])
    db.upsert_user(3, "Mehmon", None)  # test ishlamagan — ro'yxatda chiqmaydi
    stats = db.admin_stats()
    assert stats == {"users": 3, "students": 2, "active_week": 2, "tests": 3, "groups": 0}
    students = db.list_students(limit=10, offset=0)
    assert [s["full_name"] for s in students] == ["Vali", "Ali"]
    assert students[0]["total_score"] == 1800 and students[0]["quizzes"] == 2
    assert students[0]["last_active"]
    assert db.count_students() == 2
    assert [s["full_name"] for s in db.list_students(limit=1, offset=1)] == ["Ali"]


def test_student_tests_keep_best_and_attempts():
    add_student(1, "Ali", [(500, 20, 50, "day2"), (1200, 42, 50, "day2"), (100, 3, 50, "day5")])
    by_mode = {row["mode"]: row for row in db.student_tests(1)}
    assert by_mode["day2"]["best_correct"] == 42 and by_mode["day2"]["attempts"] == 2
    assert by_mode["day5"]["best_correct"] == 3
    assert len(db.recent_results(1, limit=2)) == 2


def test_test_ranking_orders_by_best_result():
    add_student(1, "Ali", [(900, 30, 50, "day3"), (1300, 44, 50, "day3")])
    add_student(2, "Vali", [(1400, 47, 50, "day3")])
    add_student(3, "Soli", [(2000, 50, 50, "day4")])  # boshqa test
    ranking = db.ranking_for_test("day3", limit=10)
    assert [(r["full_name"], r["best_correct"], r["attempts"]) for r in ranking] == [("Vali", 47, 1), ("Ali", 44, 2)]


def test_best_by_mode_for_export():
    add_student(1, "Ali", [(900, 30, 50, "day3"), (1300, 44, 50, "day3"), (10, 1, 5, None)])
    rows = {(r["user_id"], r["mode"]): r["best_correct"] for r in db.best_by_mode()}
    assert rows[(1, "day3")] == 44
