"""Kunlik lug'at: 500 so'z 10 kunga (har kunda 50 tadan) bo'linadi.

Har bir so'z kartochkasi PDF andozasi bo'yicha: definition, o'zbekcha tarjima, sinonim, antonim,
kulgili misol va assotsiatsiya (eslab qolish usuli). Har bir kun uchun 50 savollik test bor.
"""

import json
import random
import re
from functools import partial
from html import escape as html_escape
from pathlib import Path

from config import DAY_COUNT, DAY_SIZE, PDF_DIR, VOCAB_PATH
from quiz import (
    MODE_DAY,
    MODE_DEFINITION,
    MODE_EN_UZ,
    MODE_SENTENCE,
    MODE_SYNONYM,
    MODE_UZ_EN,
    SENTENCES,
    Question,
    make_question,
)

# Kunlik testda savol turlari navbat bilan beriladi — har biridan taxminan teng miqdorda
DAY_DIRECTIONS = (MODE_SENTENCE, MODE_DEFINITION, MODE_SYNONYM, MODE_EN_UZ, MODE_UZ_EN)
BOLD = re.compile(r"\*\*(.+?)\*\*")
# Telegram HTML uchun faqat <, > va & almashtiriladi — qo'shtirnoqlar o'z holicha qoladi
escape = partial(html_escape, quote=False)


def load_vocab() -> list[dict]:
    with open(VOCAB_PATH, encoding="utf-8") as f:
        return json.load(f)


VOCAB = load_vocab()


def day_word_ids(day: int) -> range:
    if not 1 <= day <= DAY_COUNT:
        raise ValueError(f"Kun 1..{DAY_COUNT} oralig'ida bo'lishi kerak: {day}")
    start = (day - 1) * DAY_SIZE
    return range(start, min(start + DAY_SIZE, len(VOCAB)))


def day_pdf_path(day: int) -> Path:
    return PDF_DIR / f"day{day:02d}.pdf"


def day_mode(day: int) -> str:
    return f"{MODE_DAY}{day}"


def parse_day_mode(mode: str) -> int | None:
    suffix = mode[len(MODE_DAY):] if mode.startswith(MODE_DAY) else ""
    if suffix.isdigit() and 1 <= int(suffix) <= DAY_COUNT:
        return int(suffix)
    return None


def day_range_label(day: int) -> str:
    ids = day_word_ids(day)
    return f"{VOCAB[ids[0]]['en']} – {VOCAB[ids[-1]]['en']}"


# ─────────────────────────── Kartochka ───────────────────────────

def bold_html(text: str) -> str:
    """"**so'z**" belgisini Telegram HTML'dagi qalin yozuvga aylantiradi."""
    return BOLD.sub(r"<b>\1</b>", escape(text))


def card_text(word_id: int) -> str:
    entry = VOCAB[word_id]
    lines = [
        f"<b>{word_id % DAY_SIZE + 1}. {escape(entry['en'])}</b> — <i>{escape(entry['uz'])}</i>",
        f"📘 {escape(entry['definition'])}",
    ]
    pairs = []
    if entry["synonym"]:
        pairs.append(f"🔁 {escape(entry['synonym'])}")
    if entry["antonym"]:
        pairs.append(f"↔️ {escape(entry['antonym'])}")
    if pairs:
        lines.append(" · ".join(pairs))
    lines.append(f"😂 {bold_html(entry['example'])}")
    lines.append(f"💡 {escape(entry['association'])}")
    return "\n".join(lines)


# ─────────────────────────── Test savollari ───────────────────────────

def _meanings(entry: dict) -> set[str]:
    return {part.strip().lower() for part in re.split(r"[,;/]", entry["uz"]) if part.strip()}


def _confusable(target: dict, other: dict) -> bool:
    """Noto'g'ri variant ham to'g'ri bo'lib ko'rinishi mumkin bo'lgan so'zlar."""
    if _meanings(target) & _meanings(other):
        return True  # masalan, occupation va profession — ikkalasi ham "kasb"
    if target["en"][:5].lower() == other["en"][:5].lower():
        return True  # employee / employer, recycle / recycling
    synonyms = {target["synonym"].lower(), other["synonym"].lower()} - {""}
    if target["synonym"] and target["synonym"].lower() == other["synonym"].lower():
        return True
    return target["en"].lower() in synonyms or other["en"].lower() in synonyms


def _mentions(prompt: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word.lower())}\b", prompt.lower()) is not None


def _distractors(word_id: int, pool: list[int], answer_key: str, prompt: str) -> list[str]:
    target = VOCAB[word_id]
    correct = target[answer_key].lower()
    chosen: list[str] = []
    for other_id in random.sample(pool, k=len(pool)):
        other = VOCAB[other_id]
        text = other[answer_key]
        if (
            other_id == word_id
            or text.lower() == correct
            or text.lower() in {c.lower() for c in chosen}
            or _confusable(target, other)
            or (answer_key == "en" and _mentions(prompt, text))
        ):
            continue
        chosen.append(text)
        if len(chosen) == 3:
            break
    return chosen


def _choice_question(word_id: int, direction: str, pool: list[int]) -> Question:
    entry = VOCAB[word_id]
    prompt_key, answer_key = {
        MODE_DEFINITION: ("definition", "en"),
        MODE_SYNONYM: ("synonym", "en"),
        MODE_EN_UZ: ("en", "uz"),
        MODE_UZ_EN: ("uz", "en"),
    }[direction]
    prompt = entry[prompt_key]
    distractors = _distractors(word_id, pool, answer_key, prompt)
    if len(distractors) < 3:  # kun ichida mos variant yetmasa — butun lug'atdan olinadi
        distractors = _distractors(word_id, list(range(len(VOCAB))), answer_key, prompt)
    options = distractors + [entry[answer_key]]
    random.shuffle(options)
    return Question(
        word_id=word_id,
        prompt=prompt,
        direction=direction,
        options=options,
        correct_index=options.index(entry[answer_key]),
    )


def make_day_question(word_id: int, direction: str, pool: list[int]) -> Question:
    if direction == MODE_SENTENCE:
        if word_id in SENTENCES:
            return make_question(word_id, MODE_SENTENCE)
        direction = MODE_DEFINITION  # bu so'z uchun gap yo'q
    if direction == MODE_SYNONYM and not VOCAB[word_id]["synonym"]:
        direction = MODE_DEFINITION
    return _choice_question(word_id, direction, pool)


def build_day_questions(day: int) -> list[Question]:
    """Kunning 50 ta so'zi — har biri bittadan savol, turlari aralash, tartibi tasodifiy."""
    pool = list(day_word_ids(day))
    order = random.sample(pool, k=len(pool))
    return [
        make_day_question(word_id, DAY_DIRECTIONS[number % len(DAY_DIRECTIONS)], pool)
        for number, word_id in enumerate(order)
    ]
