from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import DAY_COUNT, DAY_SIZE, QUESTION_COUNTS, TEAMS
from quiz import MODE_EN_UZ, MODE_MIXED, MODE_SENTENCE, MODE_TITLES, MODE_UZ_EN

# Test yo'nalishlari tartibi
QUIZ_MODES = (MODE_SENTENCE, MODE_EN_UZ, MODE_UZ_EN, MODE_MIXED)


def add_to_group_button(bot_username: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text="➕ Guruhga qo'shish", url=f"https://t.me/{bot_username}?startgroup=quiz"
    )


def main_menu(bot_username: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🎯 Testni boshlash", callback_data="pq:menu"))
    kb.row(InlineKeyboardButton(text=f"📝 {DAY_COUNT} ta test ({DAY_SIZE} savoldan) + lug'at", callback_data="day:list"))
    kb.row(
        InlineKeyboardButton(text="🏆 Reyting", callback_data="top:all"),
        InlineKeyboardButton(text="👤 Profilim", callback_data="menu:me"),
    )
    kb.row(
        InlineKeyboardButton(text="🧠 Xatolarim", callback_data="pq:mistakes"),
        InlineKeyboardButton(text="ℹ️ Yordam", callback_data="menu:help"),
    )
    kb.row(add_to_group_button(bot_username))
    return kb.as_markup()


def group_menu(join: InlineKeyboardButton) -> InlineKeyboardMarkup:
    """Guruh menyusi; join — o'quvchini shu guruhga biriktirib, botni ochadigan tugma."""
    kb = InlineKeyboardBuilder()
    kb.row(join)
    kb.row(InlineKeyboardButton(text="⏱ Quizni boshlash", callback_data="pq:menu"))
    kb.row(InlineKeyboardButton(text=f"📝 {DAY_COUNT} ta test ({DAY_SIZE} savoldan)", callback_data="day:list"))
    kb.row(InlineKeyboardButton(text="🏆 Reyting", callback_data="top:all"))
    return kb.as_markup()


def poll_modes(is_group: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for mode in QUIZ_MODES:
        kb.row(InlineKeyboardButton(text=MODE_TITLES[mode], callback_data=f"pq:m:{mode}"))
    kb.row(InlineKeyboardButton(text=f"📝 {DAY_COUNT} ta test ({DAY_SIZE} savoldan)", callback_data="day:list"))
    if not is_group:
        kb.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="menu:home"))
    return kb.as_markup()


def poll_counts(mode: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        *[
            InlineKeyboardButton(text=f"{n} ta savol", callback_data=f"pq:c:{mode}:{n}")
            for n in QUESTION_COUNTS
        ]
    )
    kb.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="pq:menu"))
    return kb.as_markup()


def day_list(is_group: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for day in range(1, DAY_COUNT + 1):
        kb.button(text=f"📝 Test {day}", callback_data=f"day:open:{day}")
    kb.adjust(2)
    if not is_group:
        kb.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="menu:home"))
    return kb.as_markup()


def day_menu(day: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=f"🎯 Testni boshlash ({DAY_SIZE} savol)", callback_data=f"day:t:{day}"))
    kb.row(InlineKeyboardButton(text="📖 So'zlar (kartochkalar)", callback_data=f"day:w:{day}:0"))
    kb.row(InlineKeyboardButton(text="📄 PDF yuklab olish", callback_data=f"day:pdf:{day}"))
    kb.row(InlineKeyboardButton(text="⬅️ Testlar", callback_data="day:list"))
    return kb.as_markup()


def day_cards(day: int, page: int, pages: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"day:w:{day}:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1} / {pages}", callback_data=f"day:open:{day}"))
    if page < pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"day:w:{day}:{page + 1}"))
    kb.row(*nav)
    kb.row(
        InlineKeyboardButton(text="📄 PDF", callback_data=f"day:pdf:{day}"),
        InlineKeyboardButton(text="🎯 Test", callback_data=f"day:t:{day}"),
    )
    kb.row(InlineKeyboardButton(text=f"⬅️ Test {day}", callback_data=f"day:open:{day}"))
    return kb.as_markup()


def team_lobby() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, title in TEAMS.items():
        kb.button(text=title, callback_data=f"tm:join:{key}")
    kb.adjust(2)
    kb.row(
        InlineKeyboardButton(text="▶️ Boshlash", callback_data="tm:start"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="tm:cancel"),
    )
    return kb.as_markup()


def after_poll_quiz(is_group: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="🔁 Yana quiz", callback_data="pq:menu"),
        InlineKeyboardButton(text="🏆 Reyting", callback_data="top:all"),
    )
    if not is_group:
        kb.row(
            InlineKeyboardButton(text="🧠 Xatolarim", callback_data="pq:mistakes"),
            InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="menu:home"),
        )
    return kb.as_markup()


def poll_stop() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="⛔ Quizni to'xtatish", callback_data="pq:stop"))
    return kb.as_markup()


def leaderboard(active: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(
            text=("• 🏆 Umumiy •" if active == "all" else "🏆 Umumiy"), callback_data="top:all"
        ),
        InlineKeyboardButton(
            text=("• 📅 Haftalik •" if active == "week" else "📅 Haftalik"), callback_data="top:week"
        ),
    )
    kb.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="menu:home"))
    return kb.as_markup()


def back_home() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="menu:home"))
    return kb.as_markup()
