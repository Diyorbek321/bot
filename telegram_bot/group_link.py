"""O'quvchini guruhga biriktirish.

O'quvchilar testni botda (shaxsiy chatda) ishlaydi, shuning uchun bot qaysi o'quvchi qaysi guruhdan
ekanini shu yerda bilib oladi: guruhdagi "📝 Testlarni botda ishlash" tugmasi botni
/start g<chat_id> bilan ochadi, bot o'quvchi haqiqatan shu guruh a'zosi ekanini tekshirib, biriktiradi.
"""

import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import Chat, InlineKeyboardButton, InlineKeyboardMarkup, Message, User

import database as db
import groups_db as gdb
from branding import BRAND_HEADER, DIVIDER

router = Router()
GROUP_CHATS = {ChatType.GROUP, ChatType.SUPERGROUP}
JOIN_PREFIX = "g"
NOT_MEMBER = {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}

log = logging.getLogger(__name__)


def remember_group(chat: Chat) -> None:
    """Guruhni reyting uchun ro'yxatga oladi (nomi o'zgargan bo'lsa yangilaydi)."""
    gdb.upsert_group(chat.id, chat.title or f"Guruh {chat.id}")


def join_url(bot_username: str, chat_id: int) -> str:
    return f"https://t.me/{bot_username}?start={JOIN_PREFIX}{chat_id}"


def parse_join_payload(args: str | None) -> int | None:
    """"/start g-100123" → -100123. Guruh ID'lari doim manfiy."""
    if not args or not args.startswith(JOIN_PREFIX):
        return None
    value = args[len(JOIN_PREFIX):]
    return int(value) if value.startswith("-") and value[1:].isdigit() else None


def join_button(bot_username: str, chat_id: int) -> InlineKeyboardButton:
    return InlineKeyboardButton(text="📝 Testlarni botda ishlash", url=join_url(bot_username, chat_id))


def join_keyboard(bot_username: str, chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[join_button(bot_username, chat_id)]])


def join_text(title: str) -> str:
    return (
        f"{BRAND_HEADER}\n\n"
        f"📌 <b>{escape(title)}</b> o'quvchilari!\n\n"
        f"{DIVIDER}\n"
        "1️⃣ Pastdagi <b>📝 Testlarni botda ishlash</b> tugmasini bosing\n"
        "2️⃣ Bot ochiladi va sizni shu guruhga biriktiradi\n"
        "3️⃣ Testlarni botda ishlang — natijalaringiz guruh reytingiga qo'shiladi 🏆\n"
        f"{DIVIDER}\n\n"
        "👩‍🏫 O'qituvchi: bu xabarni <b>pin</b> qiling. Guruh reytingi: /top"
    )


async def is_member(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
    except TelegramAPIError:
        log.warning("A'zolikni tekshirib bo'lmadi (chat %s, user %s)", chat_id, user_id)
        return False
    if member.status == ChatMemberStatus.RESTRICTED:
        return bool(getattr(member, "is_member", False))
    return member.status not in NOT_MEMBER


async def link_student(bot: Bot, user: User, chat_id: int) -> str:
    """O'quvchini guruhga biriktiradi va unga ko'rsatiladigan javob matnini qaytaradi."""
    group = gdb.get_group(chat_id)
    if group is None:
        return "❌ Guruh topilmadi. Guruhdagi yangi havoladan foydalaning yoki o'qituvchidan so'rang."
    title = escape(group["title"])
    if not await is_member(bot, chat_id, user.id):
        return f"⛔ Siz <b>{title}</b> guruhi a'zosi emassiz. Avval guruhga qo'shiling."
    db.upsert_user(user.id, user.full_name, user.username)
    gdb.set_user_group(user.id, chat_id)
    return (
        f"✅ Siz <b>{title}</b> guruhiga biriktirildingiz!\n"
        "Endi botda ishlagan barcha testlaringiz guruh reytingiga qo'shiladi 🏆"
    )


def group_line(user_id: int, hint: str = "") -> str:
    group = gdb.user_group(user_id)
    if group is None:
        return f"🏫 Guruh: <i>biriktirilmagan</i>{hint}"
    return f"🏫 Guruh: <b>{escape(group['title'])}</b>"


def my_group_text(user_id: int) -> str:
    group = gdb.user_group(user_id)
    if group is None:
        return (
            "🏫 Siz hali hech qaysi guruhga biriktirilmagansiz.\n\n"
            "Guruhingizdagi <b>📝 Testlarni botda ishlash</b> tugmasini bosing "
            "(o'qituvchi guruhda /guruh yozib, uni pin qiladi)."
        )
    return f"🏫 Sizning guruhingiz: <b>{escape(group['title'])}</b>"


# ─────────────────────────── Handlerlar ───────────────────────────

@router.message(Command("guruh"), F.chat.type.in_(GROUP_CHATS))
async def cmd_group_join(message: Message) -> None:
    """Guruhda: o'quvchilarni botga biriktiruvchi xabar (o'qituvchi uni pin qiladi)."""
    remember_group(message.chat)
    me = await message.bot.me()
    await message.answer(join_text(message.chat.title or ""), reply_markup=join_keyboard(me.username, message.chat.id))


@router.message(Command("guruh"), F.chat.type == ChatType.PRIVATE)
async def cmd_my_group(message: Message) -> None:
    await message.answer(my_group_text(message.from_user.id))
