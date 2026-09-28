import asyncio
import logging
import sys
from html import escape

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import BotCommand, CallbackQuery, InlineKeyboardMarkup, Message, User

import database as db
import keyboards as kb
from config import LEADERBOARD_SIZE, MISTAKES_QUIZ_SIZE, TOKEN
from quiz import (
    MODE_EN_UZ,
    MODE_MISTAKES,
    MODE_TITLES,
    WORDS,
    QuizSession,
    build_session,
    level_for,
    progress_bar,
)

dp = Dispatcher()

# Faol test sessiyalari: user_id -> QuizSession
sessions: dict[int, QuizSession] = {}

MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}
DIVIDER = "━━━━━━━━━━━━━━━━━━"


def register(user: User) -> None:
    db.upsert_user(user.id, user.full_name, user.username)


def short_name(name: str, limit: int = 18) -> str:
    name = name.strip() or "Foydalanuvchi"
    return escape(name if len(name) <= limit else name[: limit - 1] + "…")


async def edit_or_send(query: CallbackQuery, text: str, markup: InlineKeyboardMarkup) -> None:
    try:
        await query.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as e:
        # "message is not modified" — foydalanuvchi bir tugmani ikki marta bosgan
        if "not modified" not in str(e):
            await query.message.answer(text, reply_markup=markup)


# ─────────────────────────── Matnlar ───────────────────────────

def welcome_text(user: User) -> str:
    return (
        f"👋 Salom, <b>{escape(user.first_name)}</b>!\n\n"
        f"📚 <b>Quiz Bot</b>ga xush kelibsiz — B2 darajadagi "
        f"<b>{len(WORDS)} ta</b> inglizcha so'zni o'yin orqali o'rganing!\n\n"
        f"{DIVIDER}\n"
        f"🎯 Savollarga javob bering va ball to'plang\n"
        f"🔥 Ketma-ket to'g'ri javoblar uchun bonus oling\n"
        f"🏆 Reytingda boshqa o'quvchilar bilan bellashing\n"
        f"🧠 Xato qilgan so'zlaringizni qayta mashq qiling\n"
        f"{DIVIDER}\n\n"
        f"Boshlash uchun pastdagi tugmani bosing 👇"
    )


HELP_TEXT = (
    "ℹ️ <b>Qanday o'ynaladi?</b>\n\n"
    "1️⃣ <b>Testni boshlash</b> tugmasini bosing\n"
    "2️⃣ Yo'nalishni tanlang: 🇬🇧→🇺🇿, 🇺🇿→🇬🇧 yoki aralash\n"
    "3️⃣ Savollar sonini tanlang\n"
    "4️⃣ Har bir savolda 4 ta variantdan to'g'risini tanlang\n\n"
    f"{DIVIDER}\n"
    "⭐ <b>Ball tizimi</b>\n"
    "• To'g'ri javob — <b>10 ball</b>\n"
    "• Ketma-ket to'g'ri javoblar — <b>+2, +4 … +10</b> bonus 🔥\n"
    "• Xato javob — 0 ball, seriya nolga tushadi\n\n"
    "🧠 <b>Xatolarim</b> bo'limida xato qilgan so'zlaringiz saqlanadi. "
    "To'g'ri topsangiz, ro'yxatdan o'chadi.\n"
    f"{DIVIDER}\n\n"
    "⌨️ <b>Buyruqlar</b>\n"
    "/start — bosh menyu\n"
    "/quiz — yangi test\n"
    "/top — reyting\n"
    "/me — profilim\n"
    "/help — yordam"
)


def question_text(session: QuizSession) -> str:
    q = session.current
    number = session.index + 1
    total = len(session.questions)
    if q.direction == MODE_EN_UZ:
        prompt = f"🇬🇧 <b>{escape(q.prompt)}</b>\n\n<i>O'zbekcha tarjimasini tanlang 👇</i>"
    else:
        prompt = f"🇺🇿 <b>{escape(q.prompt)}</b>\n\n<i>Inglizcha tarjimasini tanlang 👇</i>"

    parts = [
        f"📝 <b>Savol {number} / {total}</b>",
        progress_bar(session.index, total),
        "",
    ]
    if session.last_feedback:
        parts += [session.last_feedback, ""]
    parts += [
        DIVIDER,
        prompt,
        DIVIDER,
        f"⭐ Ball: <b>{session.score}</b>    🔥 Seriya: <b>{session.streak}</b>",
    ]
    return "\n".join(parts)


def result_text(user: User, session: QuizSession) -> str:
    answered = session.index
    percent = session.correct * 100 / answered if answered else 0
    level, comment = level_for(percent)
    rank, participants = db.get_rank(user.id)
    return (
        f"🏁 <b>Test yakunlandi!</b>\n\n"
        f"{level}\n<i>{comment}</i>\n\n"
        f"{DIVIDER}\n"
        f"✅ To'g'ri javoblar: <b>{session.correct} / {answered}</b>\n"
        f"🎯 Aniqlik: <b>{percent:.0f}%</b>\n"
        f"⭐ Olingan ball: <b>+{session.score}</b>\n"
        f"🔥 Eng uzun seriya: <b>{session.best_streak}</b>\n"
        f"{DIVIDER}\n\n"
        f"🏆 Reytingdagi o'rningiz: <b>{rank}</b> / {participants}"
    )


def profile_text(user: User) -> str:
    row = db.get_user(user.id)
    mistakes = len(db.get_mistakes(user.id))
    if not row or row["quizzes"] == 0:
        return (
            f"👤 <b>{escape(user.full_name)}</b>\n\n"
            "Siz hali birorta ham test ishlamadingiz.\n"
            "🎯 Birinchi testni boshlang va reytingga kiring!"
        )
    accuracy = row["correct"] * 100 / row["answered"] if row["answered"] else 0
    rank, participants = db.get_rank(user.id)
    return (
        f"👤 <b>{escape(row['full_name'])}</b>\n\n"
        f"{DIVIDER}\n"
        f"🏆 Reyting: <b>{rank}</b>-o'rin ({participants} ta ishtirokchi)\n"
        f"⭐ Umumiy ball: <b>{row['total_score']}</b>\n"
        f"📝 Ishlangan testlar: <b>{row['quizzes']}</b>\n"
        f"✅ To'g'ri javoblar: <b>{row['correct']} / {row['answered']}</b>\n"
        f"🎯 Aniqlik: <b>{accuracy:.0f}%</b>\n"
        f"🔥 Eng uzun seriya: <b>{row['best_streak']}</b>\n"
        f"🧠 Takrorlash kerak bo'lgan so'zlar: <b>{mistakes}</b>\n"
        f"{DIVIDER}"
    )


def leaderboard_text(user: User, period: str) -> str:
    if period == "week":
        title = "📅 <b>HAFTALIK REYTING</b>\n<i>So'nggi 7 kun natijalari</i>"
        rows = db.top_weekly(LEADERBOARD_SIZE)
    else:
        title = "🏆 <b>UMUMIY REYTING</b>\n<i>Barcha vaqt natijalari</i>"
        rows = db.top_all_time(LEADERBOARD_SIZE)

    lines = [title, "", DIVIDER]
    if not rows:
        lines.append("Hozircha hech kim test ishlamagan.\nBirinchi bo'ling! 🚀")
    for place, row in enumerate(rows, start=1):
        badge = MEDALS.get(place, f"<b>{place}.</b>")
        accuracy = row["correct"] * 100 / row["answered"] if row["answered"] else 0
        me = " 👈" if row["user_id"] == user.id else ""
        lines.append(
            f"{badge} {short_name(row['full_name'])} — <b>{row['score']}</b> ⭐ · 🎯{accuracy:.0f}%{me}"
        )
    lines.append(DIVIDER)

    if period == "all":
        me = db.get_user(user.id)
        if me and me["quizzes"] > 0:
            rank, participants = db.get_rank(user.id)
            lines.append(f"\n📍 Sizning o'rningiz: <b>{rank}</b> / {participants} · <b>{me['total_score']}</b> ⭐")
        else:
            lines.append("\n📍 Reytingga kirish uchun test ishlang!")
    return "\n".join(lines)


# ─────────────────────────── Buyruqlar ───────────────────────────

@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    register(message.from_user)
    await message.answer(welcome_text(message.from_user), reply_markup=kb.main_menu())


@dp.message(Command("quiz"))
async def cmd_quiz(message: Message) -> None:
    register(message.from_user)
    await message.answer("🎯 <b>Test yo'nalishini tanlang:</b>", reply_markup=kb.modes())


@dp.message(Command("top"))
async def cmd_top(message: Message) -> None:
    register(message.from_user)
    await message.answer(leaderboard_text(message.from_user, "all"), reply_markup=kb.leaderboard("all"))


@dp.message(Command("me"))
async def cmd_me(message: Message) -> None:
    register(message.from_user)
    await message.answer(profile_text(message.from_user), reply_markup=kb.back_home())


@dp.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=kb.back_home())


# ─────────────────────────── Menyu ───────────────────────────

@dp.callback_query(F.data.startswith("menu:"))
async def on_menu(query: CallbackQuery) -> None:
    register(query.from_user)
    action = query.data.split(":", 1)[1]
    if action == "home":
        await edit_or_send(query, welcome_text(query.from_user), kb.main_menu())
    elif action == "quiz":
        await edit_or_send(query, "🎯 <b>Test yo'nalishini tanlang:</b>", kb.modes())
    elif action == "me":
        await edit_or_send(query, profile_text(query.from_user), kb.back_home())
    elif action == "help":
        await edit_or_send(query, HELP_TEXT, kb.back_home())
    await query.answer()


@dp.callback_query(F.data.startswith("top:"))
async def on_top(query: CallbackQuery) -> None:
    register(query.from_user)
    period = query.data.split(":", 1)[1]
    await edit_or_send(query, leaderboard_text(query.from_user, period), kb.leaderboard(period))
    await query.answer()


@dp.callback_query(F.data.startswith("mode:"))
async def on_mode(query: CallbackQuery) -> None:
    register(query.from_user)
    mode = query.data.split(":", 1)[1]

    if mode == MODE_MISTAKES:
        mistakes = db.get_mistakes(query.from_user.id)
        if not mistakes:
            await query.answer("🎉 Sizda hozircha xato qilingan so'zlar yo'q!", show_alert=True)
            return
        await start_quiz(query, mode, MISTAKES_QUIZ_SIZE, mistakes)
        return

    text = (
        f"{MODE_TITLES[mode]}\n\n"
        f"📊 <b>Nechta savol ishlaysiz?</b>"
    )
    await edit_or_send(query, text, kb.counts(mode))
    await query.answer()


# ─────────────────────────── Test ───────────────────────────

@dp.callback_query(F.data.startswith("start:"))
async def on_start_quiz(query: CallbackQuery) -> None:
    register(query.from_user)
    _, mode, count = query.data.split(":")
    await start_quiz(query, mode, int(count))


async def start_quiz(query: CallbackQuery, mode: str, count: int, word_ids: list[int] | None = None) -> None:
    session = build_session(mode, count, word_ids)
    sessions[query.from_user.id] = session
    await edit_or_send(query, question_text(session), kb.question(session.current, session.index))
    await query.answer(f"🚀 {len(session.questions)} ta savol. Omad!")


@dp.callback_query(F.data.startswith("ans:"))
async def on_answer(query: CallbackQuery) -> None:
    user_id = query.from_user.id
    session = sessions.get(user_id)
    _, number, option = query.data.split(":")

    # Eski xabardagi yoki allaqachon javob berilgan savol tugmasi bosilgan bo'lsa
    if session is None or session.finished or int(number) != session.index:
        await query.answer("⏳ Bu savol allaqachon yopilgan.")
        return

    question = session.current
    is_correct, gained = session.answer(int(option))
    pair = f"<i>{escape(question.prompt)} — {escape(question.correct_answer)}</i>"
    if is_correct:
        db.remove_mistake(user_id, question.word_id)
        session.last_feedback = f"✅ <b>To'g'ri!</b> +{gained} ⭐\n{pair}"
        toast = f"✅ To'g'ri! +{gained}"
    else:
        db.add_mistake(user_id, question.word_id)
        session.last_feedback = f"❌ <b>Xato!</b> To'g'ri javob:\n{pair}"
        toast = f"❌ Xato! To'g'ri javob: {question.correct_answer}"
    await query.answer(toast)

    if session.finished:
        await finish_quiz(query, session)
    else:
        await edit_or_send(query, question_text(session), kb.question(session.current, session.index))


@dp.callback_query(F.data == "quiz:stop")
async def on_stop(query: CallbackQuery) -> None:
    session = sessions.get(query.from_user.id)
    if session is None:
        await edit_or_send(query, welcome_text(query.from_user), kb.main_menu())
        await query.answer()
        return
    if session.index == 0:
        sessions.pop(query.from_user.id, None)
        await edit_or_send(query, "⛔ Test bekor qilindi.", kb.after_quiz())
        await query.answer()
        return
    await query.answer("⛔ Test to'xtatildi")
    await finish_quiz(query, session)


async def finish_quiz(query: CallbackQuery, session: QuizSession) -> None:
    user = query.from_user
    sessions.pop(user.id, None)
    db.save_result(user.id, session.score, session.correct, session.index, session.best_streak)
    text = result_text(user, session)
    if session.last_feedback:
        text = f"{session.last_feedback}\n\n{text}"
    await edit_or_send(query, text, kb.after_quiz())


# ─────────────────────────── Ishga tushirish ───────────────────────────

async def main() -> None:
    if not TOKEN:
        sys.exit("TOKEN topilmadi. telegram_bot/.env fayliga TOKEN=... qo'shing.")
    db.init_db()
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="🏠 Bosh menyu"),
            BotCommand(command="quiz", description="🎯 Yangi test"),
            BotCommand(command="top", description="🏆 Reyting"),
            BotCommand(command="me", description="👤 Profilim"),
            BotCommand(command="help", description="ℹ️ Yordam"),
        ]
    )
    logging.info("Bot ishga tushdi. So'zlar soni: %d", len(WORDS))
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
