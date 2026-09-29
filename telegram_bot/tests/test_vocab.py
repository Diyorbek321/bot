import re

import pytest

from poll_game import POLL_EXPLANATION_LIMIT, POLL_QUESTION_LIMIT, poll_explanation, poll_question
from quiz import MODE_DEFINITION, MODE_SYNONYM, MODE_TITLES, WORDS, mode_title
from vocab import (
    DAY_COUNT,
    DAY_SIZE,
    VOCAB,
    build_day_questions,
    card_text,
    day_mode,
    day_word_ids,
    parse_day_mode,
)

FIELDS = ("en", "uz", "definition", "synonym", "antonym", "example", "association")


def test_vocab_matches_word_list():
    assert len(VOCAB) == len(WORDS) == DAY_COUNT * DAY_SIZE == 500
    for entry, word in zip(VOCAB, WORDS):
        assert entry["en"] == word["en"] and entry["uz"] == word["uz"]
        assert set(FIELDS) <= entry.keys()
        assert entry["definition"] and entry["association"]
        assert "**" in entry["example"]  # so'z misolda qalin bo'lib turadi


def test_days_split_words_into_fifty():
    all_ids = [i for day in range(1, DAY_COUNT + 1) for i in day_word_ids(day)]
    assert all_ids == list(range(500))
    assert list(day_word_ids(3)) == list(range(100, 150))


@pytest.mark.parametrize("day", [0, 11, -1])
def test_day_out_of_range(day):
    with pytest.raises(ValueError):
        day_word_ids(day)


def test_day_mode_round_trip():
    assert parse_day_mode(day_mode(7)) == 7
    assert parse_day_mode("sent") is None
    assert parse_day_mode("day99") is None
    assert mode_title(day_mode(7)) == "📝 Test 7"
    assert mode_title("sent") == MODE_TITLES["sent"]


@pytest.mark.parametrize("day", range(1, DAY_COUNT + 1))
def test_day_test_asks_every_word_once(day):
    questions = build_day_questions(day)
    ids = sorted(q.word_id for q in questions)
    assert ids == list(day_word_ids(day))
    for q in questions:
        assert len(q.options) == 4 == len(set(o.lower() for o in q.options))
        assert 0 <= q.correct_index < 4


def test_day_test_mixes_question_types():
    directions = {q.direction for day in range(1, 4) for q in build_day_questions(day)}
    assert {MODE_DEFINITION, MODE_SYNONYM} <= directions
    assert len(directions) >= 4


def test_distractors_never_repeat_the_answer_meaning():
    for _ in range(5):
        for day in range(1, DAY_COUNT + 1):
            for q in build_day_questions(day):
                target = VOCAB[q.word_id]
                wrong = [o for i, o in enumerate(q.options) if i != q.correct_index]
                if q.direction in (MODE_DEFINITION, MODE_SYNONYM):
                    assert q.correct_answer == target["en"]
                    others = [e for e in VOCAB if e["en"] in wrong]
                    # bir xil tarjimali yoki sinonimli so'z noto'g'ri variant bo'lmasligi kerak
                    assert all(e["uz"].lower() != target["uz"].lower() for e in others)
                    if q.direction == MODE_SYNONYM:
                        assert all(e["synonym"].lower() != target["synonym"].lower() for e in others)
                    for option in wrong:
                        assert not re.search(rf"\b{re.escape(option.lower())}\b", q.prompt.lower())


def test_poll_texts_fit_telegram_limits():
    for day in range(1, DAY_COUNT + 1):
        for number, q in enumerate(build_day_questions(day), start=1):
            assert len(poll_question(q, number, DAY_SIZE)) <= POLL_QUESTION_LIMIT
            assert len(poll_explanation(q)) <= POLL_EXPLANATION_LIMIT


def test_explanation_includes_association():
    q = next(q for q in build_day_questions(1) if q.word_id == 0)
    assert "💡" in poll_explanation(q)


def test_card_text_has_all_columns_and_bold_word():
    text = card_text(0)
    assert "1. achieve</b>" in text and "erishmoq" in text
    assert "Reach" in text and "Fail" in text and "💡" in text
    assert "<b>achieved</b>" in text and "**" not in text


def test_card_text_escapes_html():
    assert "<" not in card_text(0).replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")
