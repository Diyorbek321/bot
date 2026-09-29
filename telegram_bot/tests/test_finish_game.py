import asyncio
from unittest.mock import AsyncMock, MagicMock

from aiogram.exceptions import TelegramBadRequest

import poll_handlers
from poll_game import PollGame
from quiz import MODE_SENTENCE, Question


def test_results_sent_even_if_poll_cannot_be_stopped(monkeypatch):
    monkeypatch.setattr(poll_handlers, "db", MagicMock())
    questions = [Question(0, "word ____", MODE_SENTENCE, ["a", "b", "c", "d"], 1)]
    game = PollGame(chat_id=1, is_group=False, mode=MODE_SENTENCE, questions=questions, started_by=7)
    bot = MagicMock()
    bot.stop_poll = AsyncMock(side_effect=TelegramBadRequest(MagicMock(), "poll can't be stopped"))
    bot.send_message = AsyncMock()

    asyncio.run(poll_handlers.finish_game(bot, game, asked=1, open_poll=42))

    bot.send_message.assert_awaited_once()


def test_group_game_is_counted_with_mode_and_chat(monkeypatch):
    fake_db = MagicMock()
    monkeypatch.setattr(poll_handlers, "db", fake_db)
    questions = [Question(0, "word ____", MODE_SENTENCE, ["a", "b", "c", "d"], 1)]
    game = PollGame(chat_id=-100, is_group=True, mode="day2", questions=questions, started_by=7)
    game.polls = {"p0": 0}
    game.sent_at = {0: 0.0}
    game.join_team(7, "Ali", "red")
    game.record_answer("p0", 7, "Ali", 1, now=1.0)
    bot = MagicMock(send_message=AsyncMock())

    asyncio.run(poll_handlers.finish_game(bot, game, asked=1, open_poll=None))

    assert fake_db.save_result.call_args.kwargs == {"mode": "day2", "chat_id": -100}
    fake_db.add_group_game.assert_called_once_with(-100)


def test_group_game_without_answers_is_not_counted(monkeypatch):
    fake_db = MagicMock()
    monkeypatch.setattr(poll_handlers, "db", fake_db)
    questions = [Question(0, "word ____", MODE_SENTENCE, ["a", "b", "c", "d"], 1)]
    game = PollGame(chat_id=-100, is_group=True, mode="day2", questions=questions, started_by=7)
    game.join_team(7, "Ali", "red")

    asyncio.run(poll_handlers.finish_game(MagicMock(send_message=AsyncMock()), game, asked=1, open_poll=None))

    fake_db.add_group_game.assert_not_called()
