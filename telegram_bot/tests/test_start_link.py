import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.enums import ChatMemberStatus

import bot
import database as db
import groups_db as gdb

GROUP = -1001


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "quiz.db"))
    db.init_db()
    gdb.upsert_group(GROUP, "IELTS 1")


def start_message(args: str | None):
    message = MagicMock()
    message.from_user.id = 7
    message.from_user.full_name = "Ali"
    message.from_user.first_name = "Ali"
    message.from_user.username = "ali"
    message.bot.me = AsyncMock(return_value=MagicMock(username="my_bot"))
    message.bot.get_chat_member = AsyncMock(return_value=MagicMock(status=ChatMemberStatus.MEMBER))
    message.answer = AsyncMock()
    asyncio.run(bot.cmd_start(message, MagicMock(args=args)))
    return message


def test_start_with_group_link_attaches_student():
    message = start_message(f"g{GROUP}")
    texts = [call.args[0] for call in message.answer.await_args_list]
    assert "biriktirildingiz" in texts[0] and len(texts) == 2  # biriktirish + bosh menyu
    assert gdb.user_group(7)["chat_id"] == GROUP


def test_plain_start_does_not_touch_group():
    message = start_message(None)
    assert message.answer.await_count == 1
    assert gdb.user_group(7) is None


def test_profile_shows_group():
    start_message(f"g{GROUP}")
    assert "IELTS 1" in bot.profile_text(MagicMock(id=7, full_name="Ali"))
