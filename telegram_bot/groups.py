"""Guruhlar reytingi: qaysi guruh qanday natija ko'rsatyapti.

Admin panelda — barcha guruhlar (aniqlik yoki ball bo'yicha), guruh ichidagi o'quvchilar va Test 1–10
natijalari, CSV. Guruhning o'zida /top — shu guruh o'quvchilari va guruhning umumiy o'rni.
"""

import csv
import io
from datetime import datetime
from html import escape

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

import database as db
from admin import TASHKENT, accuracy, is_admin, local_time, student_name
from branding import BRAND_FOOTER, BRAND_HEADER, DIVIDER, MEDALS
from config import BRAND_NAME, DAY_COUNT, LEADERBOARD_SIZE
from poll_handlers import edit_or_send
from vocab import day_mode

router = Router()
PAGE_SIZE = 10
GROUP_STUDENTS_SIZE = 20
ORDERS = {"acc": "🎯 Aniqlik", "score": "⭐ Ball"}


def place_line(chat_id: int) -> str:
    place = db.group_place(chat_id)
    if place is None:
        return "📍 Guruhlar reytingiga kirish uchun test ishlang!"
    return f"📍 Guruhlar orasida: <b>{place[0]}</b>-o'rin / {place[1]}"


# ─────────────────────────── Matnlar ───────────────────────────

def groups_text(order: str, page: int) -> str:
    rows = db.group_ranking(order)
    pages = max(1, -(-len(rows) // PAGE_SIZE))
    lines = [
        f"🏫 <b>Guruhlar reytingi</b> · {len(rows)} ta · {page + 1}/{pages}",
        f"<i>Saralash: {ORDERS[order]}</i>",
        "",
        DIVIDER,
    ]
    if not rows:
        lines.append("Bot hali birorta guruhga qo'shilmagan.")
    for place, row in enumerate(rows[page * PAGE_SIZE:(page + 1) * PAGE_SIZE], start=page * PAGE_SIZE + 1):
        badge = MEDALS.get(place, f"<b>{place}.</b>") if row["answered"] else "▫️"
        lines.append(
            f"{badge} <b>{escape(row['title'])}</b>\n"
            f"      🎯 {accuracy(row['correct'], row['answered'])}% · ⭐ {row['total_score']} · "
            f"👥 {row['students']} · 🎮 {row['games']} · 🕒 {local_time(row['last_active'])}"
        )
    lines += [DIVIDER, "🎯 aniqlik · ⭐ ball · 👥 o'quvchilar · 🎮 o'yinlar · 🕒 oxirgi faollik"]
    return "\n".join(lines)


def group_detail_text(chat_id: int) -> str | None:
    group = db.get_group(chat_id)
    if group is None:
        return None
    students = db.group_students(chat_id, GROUP_STUDENTS_SIZE)
    correct = sum(s["correct"] for s in students)
    answered = sum(s["answered"] for s in students)
    lines = [
        f"🏫 <b>{escape(group['title'])}</b>",
        place_line(chat_id),
        f"🎮 O'yinlar: <b>{group['games']}</b> · 👥 O'quvchilar: <b>{len(students)}</b> · "
        f"🎯 {accuracy(correct, answered)}%",
        "",
        DIVIDER,
        "👥 <b>Guruh ichidagi reyting</b>",
    ]
    if not students:
        lines.append("Bu guruhda hali test ishlanmagan.")
    for place, row in enumerate(students, start=1):
        badge = MEDALS.get(place, f"<b>{place}.</b>")
        lines.append(
            f"{badge} {student_name(row)} — ⭐ <b>{row['score']}</b> · "
            f"🎯 {accuracy(row['correct'], row['answered'])}% · 🎮 {row['games']}"
        )
    tests = {row["mode"]: row for row in db.group_tests(chat_id)}
    lines += [DIVIDER, "📝 <b>Testlar bo'yicha (o'rtacha eng yaxshi natija)</b>"]
    for day in range(1, DAY_COUNT + 1):
        row = tests.get(day_mode(day))
        if row:
            lines.append(f"Test {day}: ✅ <b>{row['avg_best']:.0f}/{row['total']}</b> · 👥 {row['participants']}")
        else:
            lines.append(f"Test {day}: —")
    return "\n".join(lines)


def group_top_text(chat_id: int, title: str, viewer_id: int) -> str:
    """Guruhning o'zida /top: shu guruh o'quvchilari va guruhning umumiy o'rni."""
    lines = [BRAND_HEADER, "", f"🏫 <b>{escape(title)}</b> — guruh reytingi", place_line(chat_id), "", DIVIDER]
    rows = db.group_students(chat_id, LEADERBOARD_SIZE)
    if not rows:
        lines.append("Bu guruhda hali test ishlanmagan.\nBoshlash: /test")
    for place, row in enumerate(rows, start=1):
        badge = MEDALS.get(place, f"<b>{place}.</b>")
        me = " 👈" if row["user_id"] == viewer_id else ""
        lines.append(
            f"{badge} {escape(row['full_name'])} — <b>{row['score']}</b> ⭐ · "
            f"🎯 {accuracy(row['correct'], row['answered'])}%{me}"
        )
    lines += [DIVIDER, "", BRAND_FOOTER]
    return "\n".join(lines)


def groups_csv() -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["#", "Guruh", "Chat ID", "O'quvchilar", "O'yinlar", "Umumiy ball", "To'g'ri", "Javoblar",
                     "Aniqlik %", "Oxirgi faollik"])
    for place, row in enumerate(db.group_ranking("acc"), start=1):
        writer.writerow([place, row["title"], row["chat_id"], row["students"], row["games"], row["total_score"],
                         row["correct"], row["answered"], accuracy(row["correct"], row["answered"]),
                         local_time(row["last_active"])])
    return buffer.getvalue().encode("utf-8-sig")


# ─────────────────────────── Tugmalar ───────────────────────────

def groups_keyboard(order: str, page: int) -> InlineKeyboardMarkup:
    rows = db.group_ranking(order)
    kb = InlineKeyboardBuilder()
    kb.row(*[
        InlineKeyboardButton(text=f"• {title} •" if key == order else title, callback_data=f"grp:l:{key}:0")
        for key, title in ORDERS.items()
    ])
    for row in rows[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]:
        kb.row(InlineKeyboardButton(text=f"🏫 {row['title'][:40]}", callback_data=f"grp:i:{row['chat_id']}:{order}:{page}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"grp:l:{order}:{page - 1}"))
    if (page + 1) * PAGE_SIZE < len(rows):
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"grp:l:{order}:{page + 1}"))
    if nav:
        kb.row(*nav)
    kb.row(InlineKeyboardButton(text="📥 Guruhlar (CSV)", callback_data="grp:csv"))
    kb.row(InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:home"))
    return kb.as_markup()


def back_to_groups(order: str, page: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="⬅️ Guruhlar", callback_data=f"grp:l:{order}:{page}"))
    return kb.as_markup()


# ─────────────────────────── Handlerlar ───────────────────────────

def parse_int(value: str) -> int | None:
    return int(value) if value.lstrip("-").isdigit() else None


@router.callback_query(F.data.startswith("grp:"))
async def on_groups(query: CallbackQuery) -> None:
    if not is_admin(query.from_user.id) or query.message.chat.type != ChatType.PRIVATE:
        await query.answer("⛔ Faqat adminlar uchun.", show_alert=True)
        return
    parts = query.data.split(":")
    if parts[1] == "l" and len(parts) == 4 and parts[2] in ORDERS and parts[3].isdigit():
        order, page = parts[2], int(parts[3])
        total = len(db.group_ranking(order))
        page = min(page, max(0, (total - 1) // PAGE_SIZE))
        await edit_or_send(query, groups_text(order, page), groups_keyboard(order, page))
    elif parts[1] == "i" and len(parts) == 5 and parts[3] in ORDERS and parts[4].isdigit():
        chat_id = parse_int(parts[2])
        text = group_detail_text(chat_id) if chat_id is not None else None
        if text is None:
            await query.answer("Guruh topilmadi.", show_alert=True)
            return
        await edit_or_send(query, text, back_to_groups(parts[3], int(parts[4])))
    elif parts[1] == "csv":
        stamp = datetime.now(TASHKENT).strftime("%Y-%m-%d")
        await query.message.answer_document(
            BufferedInputFile(groups_csv(), filename=f"{BRAND_NAME} - guruhlar {stamp}.csv"),
            caption="📥 Guruhlar reytingi — Excel'da oching",
        )
    await query.answer()
