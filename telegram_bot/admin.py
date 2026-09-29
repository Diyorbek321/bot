"""Admin panel (/admin): o'quvchilar ro'yxati va reytingi, har bir test bo'yicha natijalar, Excel (CSV).

Faqat config.ADMIN_IDS dagi foydalanuvchilar uchun va faqat shaxsiy chatda — o'quvchilar
ma'lumotlari guruhda ko'rinmasligi kerak.
"""

import csv
import io
from datetime import datetime, timedelta, timezone
from html import escape

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import database as db
from branding import BRAND_HEADER, DIVIDER, MEDALS
from config import ADMIN_IDS, BRAND_NAME, DAY_COUNT
from poll_handlers import edit_or_send
from quiz import MODE_TITLES, mode_title
from vocab import day_mode, parse_day_mode

router = Router()
PAGE_SIZE = 10
RANKING_SIZE = 30
RECENT_SIZE = 5
TASHKENT = timezone(timedelta(hours=5))


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ─────────────────────────── Formatlash ───────────────────────────

def local_time(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(iso).astimezone(TASHKENT).strftime("%d.%m %H:%M")
    except ValueError:
        return "—"


def result_title(mode: str | None) -> str:
    if mode is None:
        return "🎯 Quiz"
    if parse_day_mode(mode) or mode in MODE_TITLES:
        return mode_title(mode)
    return mode


def accuracy(correct: int, answered: int) -> int:
    return round(correct * 100 / answered) if answered else 0


def student_name(row) -> str:
    username = f" @{escape(row['username'])}" if row["username"] else ""
    return f"{escape(row['full_name'])}{username}"


# ─────────────────────────── Matnlar ───────────────────────────

def panel_text() -> str:
    stats = db.admin_stats()
    return (
        f"{BRAND_HEADER}\n\n"
        "🛠 <b>Admin panel</b>\n\n"
        f"{DIVIDER}\n"
        f"👥 Botdan foydalanuvchilar: <b>{stats['users']}</b>\n"
        f"🎓 Test ishlagan o'quvchilar: <b>{stats['students']}</b>\n"
        f"🔥 So'nggi 7 kunda faol: <b>{stats['active_week']}</b>\n"
        f"📝 Jami ishlangan testlar: <b>{stats['tests']}</b>\n"
        f"{DIVIDER}"
    )


def students_text(page: int, total: int) -> str:
    rows = db.list_students(limit=PAGE_SIZE, offset=page * PAGE_SIZE)
    pages = max(1, -(-total // PAGE_SIZE))
    lines = [f"👥 <b>O'quvchilar reytingi</b> · {total} ta · {page + 1}/{pages}", "", DIVIDER]
    if not rows:
        lines.append("Hozircha test ishlagan o'quvchi yo'q.")
    for place, row in enumerate(rows, start=page * PAGE_SIZE + 1):
        badge = MEDALS.get(place, f"<b>{place}.</b>")
        lines.append(
            f"{badge} {student_name(row)}\n"
            f"      ⭐ {row['total_score']} · 📝 {row['quizzes']} ta · "
            f"🎯 {accuracy(row['correct'], row['answered'])}% · 🕒 {local_time(row['last_active'])}"
        )
    lines += [DIVIDER, "Batafsil ko'rish uchun o'quvchini tanlang 👇"]
    return "\n".join(lines)


def student_text(user_id: int) -> str | None:
    user = db.get_user(user_id)
    if user is None:
        return None
    rank, participants = db.get_rank(user_id)
    by_mode = {row["mode"]: row for row in db.student_tests(user_id)}
    lines = [
        f"👤 <b>{student_name(user)}</b>",
        f"🆔 <code>{user_id}</code>",
        "",
        f"🏆 Reyting: <b>{rank}</b> / {participants} · ⭐ <b>{user['total_score']}</b>",
        f"📝 Testlar: <b>{user['quizzes']}</b> · ✅ {user['correct']}/{user['answered']} · "
        f"🎯 {accuracy(user['correct'], user['answered'])}%",
        f"🧠 Takrorlash kerak so'zlar: <b>{len(db.get_mistakes(user_id))}</b>",
        "",
        DIVIDER,
        "📝 <b>Testlar bo'yicha (eng yaxshi natija)</b>",
    ]
    for day in range(1, DAY_COUNT + 1):
        row = by_mode.get(day_mode(day))
        if row:
            lines.append(
                f"Test {day}: ✅ <b>{row['best_correct']}/{row['total']}</b> · "
                f"{row['attempts']} marta · {local_time(row['last_at'])}"
            )
        else:
            lines.append(f"Test {day}: —")
    recent = db.recent_results(user_id, RECENT_SIZE)
    if recent:
        lines += [DIVIDER, "🕒 <b>So'nggi natijalar</b>"]
        for row in recent:
            lines.append(
                f"{local_time(row['finished_at'])} · {result_title(row['mode'])} · "
                f"✅ {row['correct']}/{row['total']} · ⭐ {row['score']}"
            )
    return "\n".join(lines)


def test_ranking_text(day: int) -> str:
    rows = db.ranking_for_test(day_mode(day), RANKING_SIZE)
    lines = [f"📝 <b>Test {day} — reyting</b>", "<i>Har bir o'quvchining eng yaxshi natijasi</i>", "", DIVIDER]
    if not rows:
        lines.append("Bu testni hali hech kim ishlamagan.")
    for place, row in enumerate(rows, start=1):
        badge = MEDALS.get(place, f"<b>{place}.</b>")
        lines.append(
            f"{badge} {student_name(row)} — ✅ <b>{row['best_correct']}/{row['total']}</b> · "
            f"⭐ {row['best_score']} · {row['attempts']} marta"
        )
    lines.append(DIVIDER)
    return "\n".join(lines)


def students_csv() -> bytes:
    """Excel'da ochiladigan jadval: har bir o'quvchi va Test 1–10 bo'yicha eng yaxshi natija."""
    best = {(row["user_id"], row["mode"]): f"{row['best_correct']}/{row['total']}" for row in db.best_by_mode()}
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")  # Excel (ru/uz lokal) ";" ni ustun ajratuvchi deb oladi
    writer.writerow(
        ["#", "Ism", "Username", "Telegram ID", "Umumiy ball", "Testlar soni", "To'g'ri", "Javoblar",
         "Aniqlik %", *[f"Test {day}" for day in range(1, DAY_COUNT + 1)], "Oxirgi faollik"]
    )
    rows = db.list_students(limit=db.count_students() or 1, offset=0)
    for place, row in enumerate(rows, start=1):
        writer.writerow(
            [place, row["full_name"], f"@{row['username']}" if row["username"] else "", row["user_id"],
             row["total_score"], row["quizzes"], row["correct"], row["answered"],
             accuracy(row["correct"], row["answered"]),
             *[best.get((row["user_id"], day_mode(day)), "") for day in range(1, DAY_COUNT + 1)],
             local_time(row["last_active"])]
        )
    return buffer.getvalue().encode("utf-8-sig")  # BOM — Excel o'zbekcha harflarni to'g'ri ko'rsatadi


# ─────────────────────────── Tugmalar ───────────────────────────

def panel_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="👥 O'quvchilar reytingi", callback_data="adm:s:0"))
    kb.row(InlineKeyboardButton(text="📝 Testlar bo'yicha natijalar", callback_data="adm:t"))
    kb.row(InlineKeyboardButton(text="📥 Excel (CSV) yuklab olish", callback_data="adm:csv"))
    kb.row(InlineKeyboardButton(text="🔄 Yangilash", callback_data="adm:home"))
    return kb.as_markup()


def students_keyboard(page: int, total: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for row in db.list_students(limit=PAGE_SIZE, offset=page * PAGE_SIZE):
        kb.row(InlineKeyboardButton(text=f"👤 {row['full_name'][:40]}", callback_data=f"adm:u:{row['user_id']}:{page}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"adm:s:{page - 1}"))
    if (page + 1) * PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"adm:s:{page + 1}"))
    if nav:
        kb.row(*nav)
    kb.row(InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:home"))
    return kb.as_markup()


def back_keyboard(callback: str, text: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=text, callback_data=callback))
    return kb.as_markup()


def tests_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for day in range(1, DAY_COUNT + 1):
        kb.button(text=f"📝 Test {day}", callback_data=f"adm:t:{day}")
    kb.adjust(2)
    kb.row(InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:home"))
    return kb.as_markup()


# ─────────────────────────── Handlerlar ───────────────────────────

@router.message(Command("myid"), F.chat.type == ChatType.PRIVATE)
async def cmd_myid(message: Message) -> None:
    await message.answer(f"🆔 Sizning Telegram ID: <code>{message.from_user.id}</code>")


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.reply("⛔ Bu bo'lim faqat adminlar uchun.")
        return
    if message.chat.type != ChatType.PRIVATE:
        await message.reply("🛠 Admin panel faqat bot bilan shaxsiy chatda ochiladi.")
        return
    await message.answer(panel_text(), reply_markup=panel_keyboard())


@router.callback_query(F.data.startswith("adm:"))
async def on_admin(query: CallbackQuery) -> None:
    if not is_admin(query.from_user.id) or query.message.chat.type != ChatType.PRIVATE:
        await query.answer("⛔ Faqat adminlar uchun.", show_alert=True)
        return
    parts = query.data.split(":")
    action = parts[1]
    if action == "home":
        await edit_or_send(query, panel_text(), panel_keyboard())
    elif action == "s" and len(parts) == 3 and parts[2].isdigit():
        total = db.count_students()
        page = min(int(parts[2]), max(0, (total - 1) // PAGE_SIZE))
        await edit_or_send(query, students_text(page, total), students_keyboard(page, total))
    elif action == "u" and len(parts) == 4 and parts[2].isdigit() and parts[3].isdigit():
        text = student_text(int(parts[2]))
        if text is None:
            await query.answer("O'quvchi topilmadi.", show_alert=True)
            return
        await edit_or_send(query, text, back_keyboard(f"adm:s:{parts[3]}", "⬅️ O'quvchilar"))
    elif action == "t" and len(parts) == 2:
        await edit_or_send(query, "📝 <b>Qaysi test natijalari?</b>", tests_keyboard())
    elif action == "t" and len(parts) == 3 and parts[2].isdigit() and 1 <= int(parts[2]) <= DAY_COUNT:
        await edit_or_send(query, test_ranking_text(int(parts[2])), back_keyboard("adm:t", "⬅️ Testlar"))
    elif action == "csv":
        stamp = datetime.now(TASHKENT).strftime("%Y-%m-%d")
        await query.message.answer_document(
            BufferedInputFile(students_csv(), filename=f"{BRAND_NAME} - o'quvchilar {stamp}.csv"),
            caption="📥 O'quvchilar natijalari — Excel'da oching",
        )
    await query.answer()
