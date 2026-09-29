"""10 ta test × 50 so'z: har bir testning so'z kartochkalari, PDF jadvali va 50 savollik testi.

Ichki nomlarda "day" = test raqami (Test 1 … Test 10).
"""

import logging

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, FSInputFile, Message

import keyboards as kb
from branding import BRAND_FOOTER, BRAND_HEADER, DIVIDER
from config import BRAND_NAME, CARDS_PER_PAGE, DAY_COUNT, DAY_SIZE, QUESTION_TIME
from poll_handlers import edit_or_send, launch
from vocab import build_day_questions, card_text, day_mode, day_pdf_path, day_range_label, day_word_ids

router = Router()
GROUP_CHATS = {ChatType.GROUP, ChatType.SUPERGROUP}
PAGES = -(-DAY_SIZE // CARDS_PER_PAGE)
# Bir marta yuborilgan PDF'ning Telegram file_id'si — keyingi safar fayl qayta yuklanmaydi
pdf_file_ids: dict[int, str] = {}

log = logging.getLogger(__name__)


# ─────────────────────────── Matnlar ───────────────────────────

def day_list_text(is_group: bool) -> str:
    lines = [
        BRAND_HEADER,
        "",
        f"📝 <b>{DAY_COUNT} ta test</b> — har biri {DAY_SIZE} savol",
        "",
        DIVIDER,
    ]
    for day in range(1, DAY_COUNT + 1):
        lines.append(f"📝 <b>Test {day}</b> · {day_range_label(day)}")
    lines += [
        DIVIDER,
        "",
        f"Har bir testda: 🎯 {DAY_SIZE} savol, 📖 so'z kartochkalari va 📄 PDF jadval.",
    ]
    if is_group:
        lines.append("👥 Guruhda test jamoaviy o'tadi — testni tanlang 👇")
    else:
        lines.append("Testni tanlang 👇")
    return "\n".join(lines)


def day_text(day: int) -> str:
    return (
        f"{BRAND_HEADER}\n\n"
        f"📝 <b>Test {day}</b> · {DAY_SIZE} ta savol\n"
        f"<i>{day_range_label(day)}</i>\n\n"
        f"{DIVIDER}\n"
        "📖 <b>So'zlar</b> — definition, 🇺🇿 tarjima, 🔁 sinonim, ↔️ antonim, 😂 kulgili misol "
        "va 💡 assotsiatsiya\n"
        "📄 <b>PDF</b> — hammasi bitta jadvalda, chop etish uchun\n"
        f"🎯 <b>Test</b> — {DAY_SIZE} ta savol (gap to'ldirish, definition, sinonim, tarjima), "
        f"har biriga {QUESTION_TIME} soniya\n"
        f"{DIVIDER}\n\n"
        "💡 Avval so'zlarni o'qing, keyin testni ishlang!\n\n"
        f"{BRAND_FOOTER}"
    )


def cards_text(day: int, page: int) -> str:
    ids = day_word_ids(day)[page * CARDS_PER_PAGE:(page + 1) * CARDS_PER_PAGE]
    cards = "\n\n".join(card_text(word_id) for word_id in ids)
    return f"📝 <b>Test {day}</b> · So'zlar {page + 1}/{PAGES}\n\n{cards}"


# ─────────────────────────── Yordamchilar ───────────────────────────

def parse_day(value: str) -> int | None:
    return int(value) if value.isdigit() and 1 <= int(value) <= DAY_COUNT else None


def is_group(chat_type: str) -> bool:
    return chat_type in GROUP_CHATS


# ─────────────────────────── Buyruq va tugmalar ───────────────────────────

@router.message(Command("test", "lugat"))
async def cmd_test(message: Message, command: CommandObject) -> None:
    """/test — testlar ro'yxati, /test 3 — 3-testni darhol ochadi."""
    day = parse_day((command.args or "").strip())
    if day is not None:
        await message.answer(day_text(day), reply_markup=kb.day_menu(day))
        return
    group = is_group(message.chat.type)
    await message.answer(day_list_text(group), reply_markup=kb.day_list(group))


@router.callback_query(F.data == "day:list")
async def on_day_list(query: CallbackQuery) -> None:
    group = is_group(query.message.chat.type)
    await edit_or_send(query, day_list_text(group), kb.day_list(group))
    await query.answer()


@router.callback_query(F.data.startswith("day:open:"))
async def on_day_open(query: CallbackQuery) -> None:
    day = parse_day(query.data.split(":")[2])
    if day is None:
        await query.answer()
        return
    await edit_or_send(query, day_text(day), kb.day_menu(day))
    await query.answer()


@router.callback_query(F.data.startswith("day:w:"))
async def on_day_words(query: CallbackQuery) -> None:
    parts = query.data.split(":")
    day = parse_day(parts[2]) if len(parts) == 4 else None
    if day is None or not parts[3].isdigit() or int(parts[3]) >= PAGES:
        await query.answer()
        return
    page = int(parts[3])
    await edit_or_send(query, cards_text(day, page), kb.day_cards(day, page, PAGES))
    await query.answer()


@router.callback_query(F.data.startswith("day:pdf:"))
async def on_day_pdf(query: CallbackQuery) -> None:
    day = parse_day(query.data.split(":")[2])
    if day is None:
        await query.answer()
        return
    path = day_pdf_path(day)
    if day not in pdf_file_ids and not path.exists():
        log.error("PDF topilmadi: %s", path)
        await query.answer("📄 PDF hozircha mavjud emas.", show_alert=True)
        return
    await query.answer("📄 Yuborilmoqda…")
    document = pdf_file_ids.get(day) or FSInputFile(path, filename=f"{BRAND_NAME} - Test {day:02d}.pdf")
    caption = f"📝 <b>Test {day}</b> so'zlari · {day_range_label(day)}\n🎯 Testni boshlash: /test {day}"
    try:
        sent = await query.message.answer_document(document, caption=caption)
    except TelegramAPIError:
        log.exception("PDF yuborilmadi (chat %s, day %s)", query.message.chat.id, day)
        return
    pdf_file_ids[day] = sent.document.file_id


@router.callback_query(F.data.startswith("day:t:"))
async def on_day_test(query: CallbackQuery) -> None:
    day = parse_day(query.data.split(":")[2])
    if day is None:
        await query.answer()
        return
    await launch(query, day_mode(day), build_day_questions(day))
