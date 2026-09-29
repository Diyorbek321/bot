import asyncio
import logging
import socket
import sys
from html import escape

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ChatType, ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import BotCommand, CallbackQuery, InlineKeyboardMarkup, Message, User

import admin
import database as db
import day_handlers
import group_link
import groups
import groups_db as gdb
import keyboards as kb
import poll_handlers
from branding import BRAND_FOOTER, BRAND_HEADER, DIVIDER, MEDALS, short_name
from config import BRAND_NAME, DAY_COUNT, DAY_SIZE, LEADERBOARD_SIZE, POINTS_MAX, POINTS_MIN, QUESTION_TIME, TOKEN
from quiz import WORDS

dp = Dispatcher()
dp.include_router(poll_handlers.router)
dp.include_router(day_handlers.router)
dp.include_router(admin.router)
dp.include_router(groups.router)
dp.include_router(group_link.router)
PRIVATE = F.chat.type == ChatType.PRIVATE


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
        f"📝 {DAY_COUNT} ta test, har biri {DAY_SIZE} savol — so'zlari kartochka va PDF bilan\n"
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
    "4️⃣ Savollar Telegram ovoz berish (quiz) ko'rinishida chiqadi — 4 ta variantdan to'g'risiga ovoz bering\n"
    f"5️⃣ Har bir savolga <b>{QUESTION_TIME} soniya</b> — vaqt tugasa keyingi savolga o'tiladi\n\n"
    f"{DIVIDER}\n"
    "⚡ <b>Ball tizimi — tezlikka qarab</b>\n"
    f"• Darhol to'g'ri javob — <b>{POINTS_MAX} ball</b>\n"
    f"• Oxirgi soniyada to'g'ri javob — <b>{POINTS_MIN} ball</b>\n"
    "• Xato javob yoki vaqt tugasa — 0 ball\n\n"
    f"📝 <b>{DAY_COUNT} ta test</b> — har biri {DAY_SIZE} ta so'zdan {DAY_SIZE} savol. Har bir so'z: "
    "definition, tarjima, sinonim, antonim, kulgili misol va 💡 assotsiatsiya. Testning PDF jadvalini "
    f"yuklab oling va {DAY_SIZE} savollik testni ishlang.\n\n"
    "🧠 <b>Xatolarim</b> bo'limida xato qilgan so'zlaringiz saqlanadi. "
    "To'g'ri topsangiz, ro'yxatdan o'chadi.\n"
    f"{DIVIDER}\n"
    "👥 <b>Jamoaviy quiz</b> — botni guruhga qo'shing, <b>/quiz</b> yozing, o'quvchilar jamoalarga "
    "bo'linadi. Har bir a'zoning bali jamoasiga qo'shiladi, oxirida g'olib jamoa e'lon qilinadi!\n"
    f"{DIVIDER}\n\n"
    "⌨️ <b>Buyruqlar</b>\n"
    "/start — bosh menyu\n"
    "/quiz — yangi test\n"
    "/test — 10 ta test va ularning so'zlari (/test 3 — 3-test)\n"
    "/stop — quizni to'xtatish\n"
    "/top — reyting\n"
    "/me — profilim\n"
    "/help — yordam\n\n"
    f"{BRAND_FOOTER}"
)


def profile_text(user: User) -> str:
    row = db.get_user(user.id)
    mistakes = len(db.get_mistakes(user.id))
    if not row or row["quizzes"] == 0:
        return (
            f"{BRAND_HEADER}\n\n"
            f"👤 <b>{escape(user.full_name)}</b>\n"
            f"{group_link.group_line(user.id, hint=' — /guruh')}\n\n"
            "Siz hali birorta ham test ishlamadingiz.\n"
            "🎯 Birinchi testni boshlang va reytingga kiring!"
        )
    accuracy = row["correct"] * 100 / row["answered"] if row["answered"] else 0
    rank, participants = db.get_rank(user.id)
    return (
        f"{BRAND_HEADER}\n\n"
        f"👤 <b>{escape(row['full_name'])}</b>\n"
        f"{group_link.group_line(user.id, hint=' — /guruh')}\n\n"
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
async def cmd_start(message: Message, command: CommandObject) -> None:
    register(message.from_user)
    # Guruhdagi "📝 Testlarni botda ishlash" tugmasi: /start g<chat_id> — o'quvchini guruhga biriktiradi
    group_id = group_link.parse_join_payload(command.args)
    if group_id is not None:
        await message.answer(await group_link.link_student(message.bot, message.from_user, group_id))
    await message.answer(welcome_text(message.from_user), reply_markup=await main_menu(message.bot))


@dp.message(Command("top"))
async def cmd_top(message: Message) -> None:
    register(message.from_user)
    if message.chat.type in poll_handlers.GROUP_CHATS:
        # Guruhda — shu guruh o'quvchilari va guruhning boshqa guruhlar orasidagi o'rni
        group_link.remember_group(message.chat)
        gdb.set_group_if_missing(message.from_user.id, message.chat.id)
        me = await message.bot.me()
        await message.answer(
            groups.group_top_text(message.chat.id, message.chat.title or "", message.from_user.id),
            reply_markup=group_link.join_keyboard(me.username, message.chat.id),
        )
        return
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
            BotCommand(command="test", description="📝 10 ta test (50 savoldan)"),
            BotCommand(command="stop", description="⛔ Quizni to'xtatish"),
            BotCommand(command="top", description="🏆 Reyting"),
            BotCommand(command="guruh", description="🏫 Guruhim / guruh havolasi"),
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
