import asyncio
import csv
import io
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.enums import ChatType

import database as db
import groups
import groups_db as gdb

ADMIN, STUDENT = 111, 222
GROUP_A, GROUP_B = -1001, -1002


@pytest.fixture(autouse=True)
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "quiz.db"))
    monkeypatch.setattr(groups, "is_admin", lambda user_id: user_id == ADMIN)
    db.init_db()
    gdb.upsert_group(GROUP_A, "IELTS <1>")
    gdb.upsert_group(GROUP_B, "Kids 2")
    for user_id, name, username, group in ((1, "Ali", "ali", GROUP_A), (2, "Vali", None, GROUP_B),
                                           (3, "Dangasa", None, GROUP_A)):
        db.upsert_user(user_id, name, username)
        gdb.set_user_group(user_id, group)
    # Testlar botda — shaxsiy chatda ishlangan
    db.save_result(1, 3000, 30, 50, 3, mode="day1", chat_id=1)
    db.save_result(2, 1500, 45, 50, 3, mode="day1", chat_id=2)


def query(data: str, user_id: int = ADMIN, chat_type: str = ChatType.PRIVATE):
    q = MagicMock(data=data)
    q.from_user.id = user_id
    q.message.chat.type = chat_type
    q.answer = AsyncMock()
    q.message.edit_text = AsyncMock()
    q.message.answer_document = AsyncMock()
    return q


def test_groups_text_sorted_by_accuracy_and_escaped():
    text = groups.groups_text("acc", 0)
    assert text.index("Kids 2") < text.index("IELTS &lt;1&gt;")
    assert "🎯 90%" in text and "👥 1/2" in text  # IELTS: 2 a'zodan 1 tasi test ishlagan
    by_score = groups.groups_text("score", 0)
    assert by_score.index("IELTS") < by_score.index("Kids 2")


def test_groups_text_counts_ungrouped_students():
    db.upsert_user(9, "Yolg'iz", None)
    db.save_result(9, 10, 1, 5, 1)
    assert "biriktirilmagan o'quvchilar: <b>1</b>" in groups.groups_text("acc", 0)


def test_group_detail_lists_members_without_tests():
    text = groups.group_detail_text(GROUP_A)
    assert "2</b>-o'rin / 2" in text and "Test 1: ✅ <b>30/50</b>" in text and "Test 2: —" in text
    assert "A'zolar: <b>2</b>" in text
    assert "Dangasa — <i>hali test ishlamagan</i>" in text
    assert groups.group_detail_text(-999) is None


def test_group_top_marks_viewer_and_hides_inactive():
    text = groups.group_top_text(GROUP_A, "IELTS", viewer_id=1)
    assert "2</b>-o'rin / 2" in text and "Ali" in text and "👈" in text
    assert "Dangasa" not in text and "Vali" not in text


def test_group_top_for_new_group():
    gdb.upsert_group(-1003, "Yangi")
    text = groups.group_top_text(-1003, "Yangi", viewer_id=1)
    assert "hech kim test ishlamagan" in text and "reytingiga kirish" in text


def test_groups_csv():
    rows = list(csv.reader(io.StringIO(groups.groups_csv().decode("utf-8-sig")), delimiter=";"))
    assert rows[0][1] == "Guruh" and rows[0][3] == "A'zolar"
    assert rows[1][1] == "Kids 2" and rows[1][9] == "90"
    assert rows[2][3:6] == ["2", "1", "1"]


def test_student_cannot_open_groups():
    q = query("grp:l:acc:0", user_id=STUDENT)
    asyncio.run(groups.on_groups(q))
    q.message.edit_text.assert_not_awaited()


def test_groups_not_shown_in_group_chat():
    q = query("grp:l:acc:0", chat_type=ChatType.SUPERGROUP)
    asyncio.run(groups.on_groups(q))
    q.message.edit_text.assert_not_awaited()


@pytest.mark.parametrize("data", ["grp:l:acc:0", "grp:l:score:0", "grp:l:acc:50", f"grp:i:{GROUP_A}:acc:0"])
def test_group_screens_render(data):
    q = query(data)
    asyncio.run(groups.on_groups(q))
    q.message.edit_text.assert_awaited_once()


@pytest.mark.parametrize("data", ["grp:l:bad:0", "grp:i:abc:acc:0", "grp:i:-999:acc:0", "grp:x"])
def test_bad_group_callbacks_ignored(data):
    q = query(data)
    asyncio.run(groups.on_groups(q))
    q.message.edit_text.assert_not_awaited()


def test_group_callback_data_fits_telegram_limit():
    gdb.upsert_group(-1009999999999, "Katta guruh")
    markup = groups.groups_keyboard("score", 0)
    assert all(len(b.callback_data.encode()) <= 64 for row in markup.inline_keyboard for b in row)


def test_groups_csv_button():
    q = query("grp:csv")
    asyncio.run(groups.on_groups(q))
    assert q.message.answer_document.await_args.args[0].filename.endswith(".csv")
