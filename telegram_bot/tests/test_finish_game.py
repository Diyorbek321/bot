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
