import asyncio
import logging
import socket
import sys
from html import escape

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ChatType, ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import BotCommand, CallbackQuery, InlineKeyboardMarkup, Message, User

import database as db
import keyboards as kb
import poll_handlers
from branding import BRAND_FOOTER, BRAND_HEADER, DIVIDER, MEDALS, short_name
from config import (
    BRAND_NAME,
    LEADERBOARD_SIZE,
    MISTAKES_QUIZ_SIZE,
    POINTS_MAX,
    POINTS_MIN,
    POLL_IDLE_LIMIT,
    QUESTION_TIME,
    TOKEN,
)
from quiz import (
    MODE_EN_UZ,
    MODE_MISTAKES,
    MODE_SENTENCE,
    MODE_TITLES,
    WORDS,
    QuizSession,
    build_session,
    level_for,
    progress_bar,
)

dp = Dispatcher()
dp.include_router(poll_handlers.router)
PRIVATE = F.chat.type == ChatType.PRIVATE

# Faol test sessiyalari: user_id -> QuizSession
sessions: dict[int, QuizSession] = {}
# Joriy savol taymerlari: user_id -> Task (QUESTION_TIME soniyadan keyin keyingi savolga o'tkazadi)
timers: dict[int, asyncio.Task] = {}


def register(user: User) -> None:
    db.upsert_user(user.id, user.full_name, user.username)


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
        f"{BRAND_HEADER}\n\n"
        f"👋 Salom, <b>{escape(user.first_name)}</b>!\n\n"
        f"📚 <b>{BRAND_NAME}</b> o'quv markazining quiz botiga xush kelibsiz — B2 darajadagi "
        f"<b>{len(WORDS)} ta</b> inglizcha so'zni o'yin orqali o'rganing!\n\n"
        f"{DIVIDER}\n"
        f"⏱ Har bir savolga {QUESTION_TIME} soniya — tez javob bering, ko'p ball oling\n"
        f"👥 Guruhda jamoa bo'lib bellashing\n"
        f"🏆 Reytingda boshqa o'quvchilar bilan bellashing\n"
        f"🧠 Xato qilgan so'zlaringizni qayta mashq qiling\n"
        f"{DIVIDER}\n\n"
        f"Boshlash uchun pastdagi tugmani bosing 👇\n\n"
        f"{BRAND_FOOTER}"
    )


HELP_TEXT = (
    f"{BRAND_HEADER}\n\n"
    "ℹ️ <b>Qanday o'ynaladi?</b>\n\n"
    "1️⃣ <b>Testni boshlash</b> tugmasini bosing\n"
    "2️⃣ Yo'nalishni tanlang: ✍️ gap to'ldirish, 🇬🇧→🇺🇿, 🇺🇿→🇬🇧 yoki aralash\n"
    "3️⃣ Savollar sonini tanlang (50, 75 yoki 100)\n"
    f"4️⃣ Har bir savolga <b>{QUESTION_TIME} soniya</b> — vaqt tugasa keyingi savolga o'tiladi\n\n"
    f"{DIVIDER}\n"
    "⚡ <b>Ball tizimi — tezlikka qarab</b>\n"
    f"• Darhol to'g'ri javob — <b>{POINTS_MAX} ball</b>\n"
    f"• Oxirgi soniyada to'g'ri javob — <b>{POINTS_MIN} ball</b>\n"
    "• Xato javob yoki vaqt tugasa — 0 ball\n\n"
    "🧠 <b>Xatolarim</b> bo'limida xato qilgan so'zlaringiz saqlanadi. "
    "To'g'ri topsangiz, ro'yxatdan o'chadi.\n"
    f"{DIVIDER}\n"
    "⏱ <b>Vaqtli quiz</b> — savollar Telegram poll ko'rinishida chiqadi.\n"
    "👥 <b>Jamoaviy quiz</b> — botni guruhga qo'shing, <b>/quiz</b> yozing, o'quvchilar jamoalarga "
    "bo'linadi. Har bir a'zoning bali jamoasiga qo'shiladi, oxirida g'olib jamoa e'lon qilinadi!\n"
    f"{DIVIDER}\n\n"
    "⌨️ <b>Buyruqlar</b>\n"
    "/start — bosh menyu\n"
    "/quiz — yangi test\n"
    "/stop — vaqtli quizni to'xtatish\n"
    "/top — reyting\n"
    "/me — profilim\n"
    "/help — yordam\n\n"
    f"{BRAND_FOOTER}"
)


def question_text(session: QuizSession) -> str:
    q = session.current
    number = session.index + 1
    total = len(session.questions)
    if q.direction == MODE_SENTENCE:
        prompt = f"✍️ <b>{escape(q.prompt)}</b>\n\n<i>Bo'sh joyga mos so'zni tanlang 👇</i>"
    elif q.direction == MODE_EN_UZ:
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
        f"⏳ <b>{QUESTION_TIME} soniya</b> · ⚡ tez javob — ko'p ball",
        f"⭐ Ball: <b>{session.score}</b>    🔥 Seriya: <b>{session.streak}</b>",
    ]
    return "\n".join(parts)


def result_text(user: User, session: QuizSession) -> str:
    answered = session.index
    percent = session.correct * 100 / answered if answered else 0
    level, comment = level_for(percent)
    rank, participants = db.get_rank(user.id)
    return (
        f"{BRAND_HEADER}\n\n"
        f"🏁 <b>Test yakunlandi!</b>\n\n"
        f"{level}\n<i>{comment}</i>\n\n"
        f"{DIVIDER}\n"
        f"✅ To'g'ri javoblar: <b>{session.correct} / {answered}</b>\n"
        f"🎯 Aniqlik: <b>{percent:.0f}%</b>\n"
        f"⭐ Olingan ball: <b>+{session.score}</b>\n"
        f"🔥 Eng uzun seriya: <b>{session.best_streak}</b>\n"
        f"{DIVIDER}\n\n"
        f"🏆 Reytingdagi o'rningiz: <b>{rank}</b> / {participants}\n\n"
        f"{BRAND_FOOTER}"
    )


def profile_text(user: User) -> str:
    row = db.get_user(user.id)
    mistakes = len(db.get_mistakes(user.id))
    if not row or row["quizzes"] == 0:
        return (
            f"{BRAND_HEADER}\n\n"
            f"👤 <b>{escape(user.full_name)}</b>\n\n"
            "Siz hali birorta ham test ishlamadingiz.\n"
            "🎯 Birinchi testni boshlang va reytingga kiring!"
        )
    accuracy = row["correct"] * 100 / row["answered"] if row["answered"] else 0
    rank, participants = db.get_rank(user.id)
    return (
        f"{BRAND_HEADER}\n\n"
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

    lines = [BRAND_HEADER, "", title, "", DIVIDER]
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
    lines += ["", BRAND_FOOTER]
    return "\n".join(lines)


# ─────────────────────────── Buyruqlar ───────────────────────────

async def main_menu(bot: Bot) -> InlineKeyboardMarkup:
    me = await bot.me()
    return kb.main_menu(me.username)


@dp.message(CommandStart(), PRIVATE)
async def cmd_start(message: Message) -> None:
    register(message.from_user)
    await message.answer(welcome_text(message.from_user), reply_markup=await main_menu(message.bot))


@dp.message(Command("quiz"), PRIVATE)
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
        await edit_or_send(query, welcome_text(query.from_user), await main_menu(query.bot))
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
    parts = query.data.split(":")
    if len(parts) != 3 or parts[1] not in MODE_TITLES or not parts[2].isdigit():
        await query.answer()
        return
    await start_quiz(query, parts[1], int(parts[2]))


async def edit_message(bot: Bot, chat_id: int, message_id: int, text: str, markup: InlineKeyboardMarkup) -> int:
    """Xabarni tahrirlaydi, bo'lmasa yangisini yuboradi. Ko'rsatilgan xabar id sini qaytaradi."""
    try:
        await bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=markup)
    except TelegramBadRequest as e:
        if "not modified" not in str(e):
            sent = await bot.send_message(chat_id, text, reply_markup=markup)
            return sent.message_id
    return message_id


def cancel_timer(user_id: int) -> None:
    task = timers.pop(user_id, None)
    if task:
        task.cancel()


async def show_question(bot: Bot, chat_id: int, message_id: int, user: User, session: QuizSession) -> None:
    """Savolni ko'rsatadi va QUESTION_TIME soniyalik taymerni ishga tushiradi."""
    cancel_timer(user.id)
    message_id = await edit_message(
        bot, chat_id, message_id, question_text(session), kb.question(session.current, session.index)
    )
    session.asked_at = asyncio.get_running_loop().time()
    index = session.index

    async def expire() -> None:
        await asyncio.sleep(QUESTION_TIME)
        # Shu orada javob berilgan yoki test tugagan bo'lsa — hech narsa qilinmaydi
        if sessions.get(user.id) is not session or session.index != index:
            return
        timers.pop(user.id, None)
        question = session.current
        session.timeout()
        db.add_mistake(user.id, question.word_id)
        session.last_feedback = (
            f"⏰ <b>Vaqt tugadi!</b> To'g'ri javob:\n<i>{escape(question.word_hint)}</i>"
        )
        try:
            if session.timeouts_in_row >= POLL_IDLE_LIMIT:
                session.last_feedback += (
                    f"\n\n😴 Ketma-ket {POLL_IDLE_LIMIT} ta savolga javob bo'lmadi — test to'xtatildi."
                )
                await finish_quiz(bot, chat_id, message_id, user, session)
            else:
                await advance(bot, chat_id, message_id, user, session)
        except TelegramAPIError:
            logging.exception("Savol vaqti tugaganda xabarni yangilab bo'lmadi (user %s)", user.id)

    timers[user.id] = asyncio.create_task(expire())


async def advance(bot: Bot, chat_id: int, message_id: int, user: User, session: QuizSession) -> None:
    if session.finished:
        await finish_quiz(bot, chat_id, message_id, user, session)
    else:
        await show_question(bot, chat_id, message_id, user, session)


async def start_quiz(query: CallbackQuery, mode: str, count: int, word_ids: list[int] | None = None) -> None:
    session = build_session(mode, count, word_ids)
    sessions[query.from_user.id] = session
    await query.answer(f"🚀 {len(session.questions)} ta savol, har biriga {QUESTION_TIME} soniya. Omad!")
    await show_question(query.bot, query.message.chat.id, query.message.message_id, query.from_user, session)


@dp.callback_query(F.data.startswith("ans:"))
async def on_answer(query: CallbackQuery) -> None:
    now = asyncio.get_running_loop().time()
    user_id = query.from_user.id
    session = sessions.get(user_id)
    parts = query.data.split(":")
    if len(parts) != 3 or not parts[1].isdigit() or not parts[2].isdigit():
        await query.answer()
        return
    number, option = int(parts[1]), int(parts[2])

    # Eski xabardagi, vaqti tugagan yoki allaqachon javob berilgan savol tugmasi bosilgan bo'lsa
    if session is None or session.finished or number != session.index:
        await query.answer("⏳ Bu savol allaqachon yopilgan.")
        return

    cancel_timer(user_id)
    question = session.current
    is_correct, gained = session.answer(option, now - session.asked_at)
    pair = f"<i>{escape(question.word_hint)}</i>"
    if is_correct:
        db.remove_mistake(user_id, question.word_id)
        session.last_feedback = f"✅ <b>To'g'ri!</b> +{gained} ⭐\n{pair}"
        toast = f"✅ To'g'ri! +{gained}"
    else:
        db.add_mistake(user_id, question.word_id)
        session.last_feedback = f"❌ <b>Xato!</b> To'g'ri javob:\n{pair}"
        toast = f"❌ Xato! To'g'ri javob: {question.correct_answer}"
    await query.answer(toast)
    await advance(query.bot, query.message.chat.id, query.message.message_id, query.from_user, session)


@dp.callback_query(F.data == "quiz:stop")
async def on_stop(query: CallbackQuery) -> None:
    session = sessions.get(query.from_user.id)
    if session is None:
        await edit_or_send(query, welcome_text(query.from_user), await main_menu(query.bot))
        await query.answer()
        return
    if session.index == 0:
        cancel_timer(query.from_user.id)
        sessions.pop(query.from_user.id, None)
        await edit_or_send(query, "⛔ Test bekor qilindi.", kb.after_quiz())
        await query.answer()
        return
    await query.answer("⛔ Test to'xtatildi")
    await finish_quiz(query.bot, query.message.chat.id, query.message.message_id, query.from_user, session)


async def finish_quiz(bot: Bot, chat_id: int, message_id: int, user: User, session: QuizSession) -> None:
    cancel_timer(user.id)
    sessions.pop(user.id, None)
    db.save_result(user.id, session.score, session.correct, session.index, session.best_streak)
    text = result_text(user, session)
    if session.last_feedback:
        text = f"{session.last_feedback}\n\n{text}"
    await edit_message(bot, chat_id, message_id, text, kb.after_quiz())


# ─────────────────────────── Ishga tushirish ───────────────────────────

class IPv4Session(AiohttpSession):
    """Telegram'ga faqat IPv4 orqali ulanadi: serverda IPv6 beqaror, so'rovlar osilib qoladi."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._connector_init["family"] = socket.AF_INET


async def main() -> None:
    if not TOKEN:
        sys.exit("TOKEN topilmadi. telegram_bot/.env fayliga TOKEN=... qo'shing.")
    db.init_db()
    bot = Bot(
        token=TOKEN,
        session=IPv4Session(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="🏠 Bosh menyu"),
            BotCommand(command="quiz", description="🎯 Yangi test"),
            BotCommand(command="stop", description="⛔ Vaqtli quizni to'xtatish"),
            BotCommand(command="top", description="🏆 Reyting"),
            BotCommand(command="me", description="👤 Profilim"),
            BotCommand(command="help", description="ℹ️ Yordam"),
        ]
    )
    await bot.set_my_short_description(
        f"🏫 {BRAND_NAME} — B2 inglizcha so'zlar bo'yicha quiz va reyting 🏆"
    )
    await bot.set_my_description(
        f"🏫 {BRAND_NAME} o'quv markazining rasmiy quiz boti.\n\n"
        f"📚 B2 darajadagi {len(WORDS)} ta inglizcha so'z\n"
        "🎯 Test savollari va ball tizimi\n"
        "🏆 O'quvchilar reytingi\n\n"
        "Boshlash uchun /start bosing!"
    )
    logging.info("%s boti ishga tushdi. So'zlar soni: %d", BRAND_NAME, len(WORDS))
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
