import pytest

import database as db
import groups_db as gdb

GROUP_A, GROUP_B, GROUP_EMPTY = -1001, -1002, -1003
PRIVATE = 1  # shaxsiy chat


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "quiz.db"))
    db.init_db()
    gdb.upsert_group(GROUP_A, "IELTS 1")
    gdb.upsert_group(GROUP_B, "Kids 2")
    gdb.upsert_group(GROUP_EMPTY, "Yangi guruh")
    for user_id, name, group in ((1, "Ali", GROUP_A), (2, "Vali", GROUP_A), (3, "Soli", GROUP_B),
                                 (4, "Dangasa", GROUP_A), (5, "Guruhsiz", None)):
        db.upsert_user(user_id, name, None)
        if group:
            gdb.set_user_group(user_id, group)
    # Testlar botda (shaxsiy chatda) ishlangan — guruhga a'zolik bo'yicha hisoblanadi
    # A: 2 o'quvchi test ishlagan, ko'p ball, aniqlik 60%; Dangasa — a'zo, lekin test ishlamagan
    db.save_result(1, 3000, 30, 50, 3, mode="day1", chat_id=PRIVATE)
    db.save_result(2, 2000, 30, 50, 3, mode="day1", chat_id=PRIVATE)
    # B: 1 o'quvchi, kam ball, aniqlik 85%
    db.save_result(3, 1500, 45, 50, 3, mode="day1", chat_id=PRIVATE)
    db.save_result(3, 900, 40, 50, 3, mode="day1", chat_id=GROUP_B)
    db.save_result(5, 5000, 50, 50, 9, mode="day2", chat_id=PRIVATE)


def test_upsert_group_updates_title():
    gdb.upsert_group(GROUP_A, "IELTS 1 (yangi)")
    assert gdb.get_group(GROUP_A)["title"] == "IELTS 1 (yangi)"
    assert gdb.get_group(-999) is None


def test_group_ranking_counts_private_results_of_members():
    by_acc = gdb.group_ranking("acc")
    assert [row["chat_id"] for row in by_acc] == [GROUP_B, GROUP_A, GROUP_EMPTY]
    by_score = gdb.group_ranking("score")
    assert [row["chat_id"] for row in by_score] == [GROUP_A, GROUP_B, GROUP_EMPTY]
    a = next(row for row in by_score if row["chat_id"] == GROUP_A)
    assert (a["members"], a["students"], a["tests"], a["total_score"], a["correct"], a["answered"]) == (
        3, 2, 2, 5000, 60, 100)
    empty = next(row for row in by_score if row["chat_id"] == GROUP_EMPTY)
    assert (empty["members"], empty["students"], empty["total_score"], empty["answered"]) == (0, 0, 0, 0)


def test_group_place():
    assert gdb.group_place(GROUP_B) == (1, 2)  # faqat natijasi bor guruhlar sanaladi
    assert gdb.group_place(GROUP_A) == (2, 2)
    assert gdb.group_place(GROUP_EMPTY) is None


def test_group_students_include_members_without_tests():
    students = gdb.group_students(GROUP_A, limit=10)
    assert [(s["full_name"], s["score"], s["games"]) for s in students] == [
        ("Ali", 3000, 1), ("Vali", 2000, 1), ("Dangasa", 0, 0)]
    soli = gdb.group_students(GROUP_B, limit=10)[0]
    assert (soli["score"], soli["correct"], soli["answered"], soli["games"]) == (2400, 85, 100, 2)


def test_group_tests_average_best_result():
    tests_b = {row["mode"]: row for row in gdb.group_tests(GROUP_B)}
    assert tests_b["day1"]["participants"] == 1 and tests_b["day1"]["avg_best"] == 45
    tests_a = {row["mode"]: row for row in gdb.group_tests(GROUP_A)}
    assert tests_a["day1"]["participants"] == 2 and tests_a["day1"]["avg_best"] == 30


def test_moving_student_to_another_group():
    gdb.set_user_group(1, GROUP_B)
    assert gdb.user_group(1)["title"] == "Kids 2"
    assert [s["full_name"] for s in gdb.group_students(GROUP_A, 10)] == ["Vali", "Dangasa"]


def test_set_group_if_missing_keeps_existing_group():
    gdb.set_group_if_missing(1, GROUP_B)
    assert gdb.user_group(1)["chat_id"] == GROUP_A
    gdb.set_group_if_missing(5, GROUP_B)
    assert gdb.user_group(5)["chat_id"] == GROUP_B


def test_ungrouped_students():
    assert gdb.ungrouped_students() == 1  # "Guruhsiz" test ishlagan, lekin guruhga biriktirilmagan
    assert gdb.user_group(5) is None
    gdb.set_user_group(5, GROUP_B)
    assert gdb.ungrouped_students() == 0


def test_group_game_counter():
    gdb.add_group_game(GROUP_A)
    gdb.add_group_game(GROUP_A)
    assert gdb.get_group(GROUP_A)["games"] == 2
