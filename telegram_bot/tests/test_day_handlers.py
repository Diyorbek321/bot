import asyncio
from unittest.mock import AsyncMock, MagicMock

import day_handlers
import keyboards as kb
from config import DAY_COUNT
from day_handlers import PAGES, cards_text, day_list_text, day_text, parse_day
from vocab import day_mode, day_pdf_path

TELEGRAM_TEXT_LIMIT = 4096


def callbacks(markup) -> list[str]:
    return [b.callback_data for row in markup.inline_keyboard for b in row if b.callback_data]


def test_every_card_page_fits_one_message():
    for day in range(1, DAY_COUNT + 1):
        for page in range(PAGES):
            assert len(cards_text(day, page)) < TELEGRAM_TEXT_LIMIT


def test_texts_fit_one_message():
    assert len(day_list_text(True)) < TELEGRAM_TEXT_LIMIT
    assert all(len(day_text(day)) < TELEGRAM_TEXT_LIMIT for day in range(1, DAY_COUNT + 1))


def test_callback_data_within_telegram_limit():
    markups = [kb.day_list(False), kb.day_list(True), kb.poll_modes(True), kb.main_menu("bot")]
    markups += [kb.day_menu(day) for day in range(1, DAY_COUNT + 1)]
    markups += [kb.day_cards(10, page, PAGES) for page in range(PAGES)]
    assert all(len(data.encode()) <= 64 for m in markups for data in callbacks(m))


def test_card_pages_navigation():
    first, last = callbacks(kb.day_cards(3, 0, PAGES)), callbacks(kb.day_cards(3, PAGES - 1, PAGES))
    assert "day:w:3:1" in first and not any(d.startswith("day:w:3:-") for d in first)
    assert f"day:w:3:{PAGES - 2}" in last and f"day:w:3:{PAGES}" not in last


def test_group_day_list_has_no_private_home_button():
    assert "menu:home" not in callbacks(kb.day_list(True))
    assert "menu:home" in callbacks(kb.day_list(False))


def test_parse_day_rejects_bad_input():
    assert parse_day("3") == 3
    assert parse_day("0") is None and parse_day("11") is None and parse_day("x") is None


def test_pdfs_exist_for_every_day():
    for day in range(1, DAY_COUNT + 1):
        assert day_pdf_path(day).stat().st_size > 10_000


def test_day_test_launches_fifty_questions(monkeypatch):
    launch = AsyncMock()
    monkeypatch.setattr(day_handlers, "launch", launch)
    query = MagicMock(data="day:t:4")
    asyncio.run(day_handlers.on_day_test(query))
    _, mode, questions = launch.await_args.args
    assert mode == day_mode(4) and len(questions) == 50
