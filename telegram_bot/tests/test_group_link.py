import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest

import database as db
import group_link
import groups_db as gdb

GROUP = -1001234567890


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "quiz.db"))
    db.init_db()
    gdb.upsert_group(GROUP, "IELTS 1")


def user(user_id: int = 7):
    u = MagicMock(id=user_id, username="ali")
    u.full_name = "Ali"
    return u


def bot_with_status(status=None, error: bool = False, is_member: bool = False):
    bot = MagicMock()
    if error:
        bot.get_chat_member = AsyncMock(side_effect=TelegramBadRequest(MagicMock(), "chat not found"))
    else:
        bot.get_chat_member = AsyncMock(return_value=MagicMock(status=status, is_member=is_member))
    return bot


def test_join_url_round_trip():
    url = group_link.join_url("my_bot", GROUP)
    assert url == f"https://t.me/my_bot?start=g{GROUP}"
    payload = url.split("start=")[1]
    assert len(payload) <= 64  # Telegram deep link cheklovi
    assert group_link.parse_join_payload(payload) == GROUP


@pytest.mark.parametrize("args", [None, "", "quiz", "g", "g123", "g-", "g-12a", "x-100"])
def test_bad_payloads(args):
    assert group_link.parse_join_payload(args) is None


@pytest.mark.parametrize("status", [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR,
                                    ChatMemberStatus.CREATOR])
def test_member_is_linked(status):
    text = asyncio.run(group_link.link_student(bot_with_status(status), user(), GROUP))
    assert "biriktirildingiz" in text
    assert gdb.user_group(7)["title"] == "IELTS 1"


@pytest.mark.parametrize("bot", [bot_with_status(ChatMemberStatus.LEFT), bot_with_status(ChatMemberStatus.KICKED),
                                 bot_with_status(ChatMemberStatus.RESTRICTED, is_member=False),
                                 bot_with_status(error=True)])
def test_non_member_is_refused(bot):
    text = asyncio.run(group_link.link_student(bot, user(), GROUP))
    assert "a'zosi emassiz" in text
    assert gdb.user_group(7) is None


def test_restricted_member_is_linked():
    bot = bot_with_status(ChatMemberStatus.RESTRICTED, is_member=True)
    assert "biriktirildingiz" in asyncio.run(group_link.link_student(bot, user(), GROUP))


def test_unknown_group():
    text = asyncio.run(group_link.link_student(bot_with_status(ChatMemberStatus.MEMBER), user(), -555))
    assert "topilmadi" in text


def test_relinking_moves_student():
    gdb.upsert_group(-2002, "Kids 2")
    bot = bot_with_status(ChatMemberStatus.MEMBER)
    asyncio.run(group_link.link_student(bot, user(), GROUP))
    asyncio.run(group_link.link_student(bot, user(), -2002))
    assert gdb.user_group(7)["title"] == "Kids 2"


def test_my_group_text():
    assert "biriktirilmagansiz" in group_link.my_group_text(7)
    db.upsert_user(7, "Ali", None)
    gdb.set_user_group(7, GROUP)
    assert "IELTS 1" in group_link.my_group_text(7)
    assert "IELTS 1" in group_link.group_line(7)


def test_group_join_command_posts_link():
    message = MagicMock()
    message.chat.id = GROUP
    message.chat.title = "IELTS 1 (yangi nom)"
    message.bot.me = AsyncMock(return_value=MagicMock(username="my_bot"))
    message.answer = AsyncMock()
    asyncio.run(group_link.cmd_group_join(message))
    markup = message.answer.await_args.kwargs["reply_markup"]
    assert markup.inline_keyboard[0][0].url.endswith(f"start=g{GROUP}")
    assert gdb.get_group(GROUP)["title"] == "IELTS 1 (yangi nom)"
