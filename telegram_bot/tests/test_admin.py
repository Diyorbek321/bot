import asyncio
import csv
import io
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.enums import ChatType

import admin
import database as db

ADMIN, STUDENT = 111, 222


@pytest.fixture(autouse=True)
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "quiz.db"))
    monkeypatch.setattr(admin, "ADMIN_IDS", frozenset({ADMIN}))
    db.init_db()
    db.upsert_user(1, "Ali <b>", "ali")
    db.save_result(1, 1300, 44, 50, 5, mode="day3", chat_id=-100)
    db.save_result(1, 200, 8, 10, 2, mode="sent", chat_id=1)
    db.upsert_user(2, "Vali", None)
    db.save_result(2, 900, 30, 50, 4, mode="day3", chat_id=-100)


def query(data: str, user_id: int, chat_type: str = ChatType.PRIVATE):
    q = MagicMock(data=data)
    q.from_user.id = user_id
    q.message.chat.type = chat_type
    q.answer = AsyncMock()
    q.message.edit_text = AsyncMock()
    q.message.answer_document = AsyncMock()
    return q


def test_student_is_refused():
    q = query("adm:s:0", STUDENT)
    asyncio.run(admin.on_admin(q))
    q.message.edit_text.assert_not_awaited()
    assert "Faqat adminlar" in q.answer.await_args.args[0]


def test_admin_panel_is_private_only():
    q = query("adm:home", ADMIN, ChatType.SUPERGROUP)
    asyncio.run(admin.on_admin(q))
    q.message.edit_text.assert_not_awaited()


def test_admin_command_refuses_student():
    message = MagicMock()
    message.from_user.id = STUDENT
    message.reply = AsyncMock()
    message.answer = AsyncMock()
    asyncio.run(admin.cmd_admin(message))
    message.answer.assert_not_awaited()


@pytest.mark.parametrize("data", ["adm:home", "adm:s:0", "adm:s:99", "adm:u:1:0", "adm:t", "adm:t:3", "adm:t:10"])
def test_admin_screens_render(data):
    q = query(data, ADMIN)
    asyncio.run(admin.on_admin(q))
    q.message.edit_text.assert_awaited_once()


@pytest.mark.parametrize("data", ["adm:u:x:0", "adm:t:0", "adm:t:11", "adm:s:-1", "adm:zzz"])
def test_bad_callbacks_are_ignored(data):
    q = query(data, ADMIN)
    asyncio.run(admin.on_admin(q))
    q.message.edit_text.assert_not_awaited()


def test_panel_stats():
    text = admin.panel_text()
    assert "Test ishlagan o'quvchilar: <b>2</b>" in text and "testlar: <b>3</b>" in text


def test_students_list_is_sorted_and_escaped():
    text = admin.students_text(0, db.count_students())
    assert text.index("Ali") < text.index("Vali")
    assert "Ali &lt;b&gt;" in text and "@ali" in text


def test_student_detail_shows_tests():
    text = admin.student_text(1)
    assert "Test 3: ✅ <b>44/50</b>" in text and "Test 1: —" in text
    assert "✍️ Gap to'ldirish" in text  # so'nggi natijalarda oddiy quiz ham ko'rinadi
    assert admin.student_text(999) is None


def test_test_ranking():
    text = admin.test_ranking_text(3)
    assert text.index("Ali") < text.index("Vali") and "44/50" in text
    assert "hech kim" in admin.test_ranking_text(7)


def test_csv_export():
    data = admin.students_csv()
    assert data.startswith("﻿".encode())
    rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig")), delimiter=";"))
    header, first = rows[0], rows[1]
    assert header[9] == "Test 1" and header[11] == "Test 3"
    assert first[1] == "Ali <b>" and first[11] == "44/50" and first[9] == ""
    assert len(rows) == 3


def test_csv_button_sends_document():
    q = query("adm:csv", ADMIN)
    asyncio.run(admin.on_admin(q))
    document = q.message.answer_document.await_args.args[0]
    assert document.filename.endswith(".csv")


def test_old_results_without_mode_are_shown():
    db.save_result(2, 10, 1, 5, 1)
    assert "🎯 Quiz" in admin.student_text(2)
