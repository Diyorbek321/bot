import pytest

import database as db

GROUP_A, GROUP_B, GROUP_EMPTY = -1001, -1002, -1003


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "quiz.db"))
    db.init_db()
    db.upsert_group(GROUP_A, "IELTS 1")
    db.upsert_group(GROUP_B, "Kids 2")
    db.upsert_group(GROUP_EMPTY, "Yangi guruh")
    for user_id, name in ((1, "Ali"), (2, "Vali"), (3, "Soli")):
        db.upsert_user(user_id, name, None)
    # A: 2 o'quvchi, ko'p ball, lekin aniqlik 60%
    db.save_result(1, 3000, 30, 50, 3, mode="day1", chat_id=GROUP_A)
    db.save_result(2, 2000, 30, 50, 3, mode="day1", chat_id=GROUP_A)
    db.add_group_game(GROUP_A)
    # B: 1 o'quvchi, kam ball, aniqlik 90%
    db.save_result(3, 1500, 45, 50, 3, mode="day1", chat_id=GROUP_B)
    db.save_result(3, 900, 40, 50, 3, mode="day1", chat_id=GROUP_B)
    db.add_group_game(GROUP_B)
    db.add_group_game(GROUP_B)
    # Shaxsiy chatdagi natija guruhlarga qo'shilmaydi
    db.save_result(1, 5000, 50, 50, 9, mode="day2", chat_id=1)


def test_upsert_group_updates_title():
    db.upsert_group(GROUP_A, "IELTS 1 (yangi)")
    titles = {row["chat_id"]: row["title"] for row in db.group_ranking("score")}
    assert titles[GROUP_A] == "IELTS 1 (yangi)"


def test_group_ranking_by_accuracy_and_by_score():
    by_acc = db.group_ranking("acc")
    assert [row["chat_id"] for row in by_acc] == [GROUP_B, GROUP_A, GROUP_EMPTY]
    by_score = db.group_ranking("score")
    assert [row["chat_id"] for row in by_score] == [GROUP_A, GROUP_B, GROUP_EMPTY]
    a = next(row for row in by_score if row["chat_id"] == GROUP_A)
    assert (a["students"], a["games"], a["total_score"], a["correct"], a["answered"]) == (2, 1, 5000, 60, 100)
    empty = next(row for row in by_score if row["chat_id"] == GROUP_EMPTY)
    assert (empty["students"], empty["total_score"], empty["answered"]) == (0, 0, 0)


def test_group_place():
    assert db.group_place(GROUP_B) == (1, 2)  # faqat natijasi bor guruhlar sanaladi
    assert db.group_place(GROUP_A) == (2, 2)
    assert db.group_place(GROUP_EMPTY) is None


def test_group_students_only_counts_that_group():
    students = db.group_students(GROUP_A, limit=10)
    assert [(s["full_name"], s["score"], s["games"]) for s in students] == [("Ali", 3000, 1), ("Vali", 2000, 1)]
    soli = db.group_students(GROUP_B, limit=10)[0]
    assert (soli["score"], soli["correct"], soli["answered"], soli["games"]) == (2400, 85, 100, 2)


def test_group_tests_average_best_result():
    tests = {row["mode"]: row for row in db.group_tests(GROUP_B)}
    assert tests["day1"]["participants"] == 1 and tests["day1"]["avg_best"] == 45
    tests_a = {row["mode"]: row for row in db.group_tests(GROUP_A)}
    assert tests_a["day1"]["participants"] == 2 and tests_a["day1"]["avg_best"] == 30


def test_get_group():
    assert db.get_group(GROUP_A)["title"] == "IELTS 1"
    assert db.get_group(-999) is None
