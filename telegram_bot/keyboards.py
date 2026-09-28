from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import QUESTION_COUNTS
from quiz import MODE_EN_UZ, MODE_MISTAKES, MODE_MIXED, MODE_TITLES, MODE_UZ_EN, OPTION_LETTERS, Question


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🎯 Testni boshlash", callback_data="menu:quiz"))
    kb.row(
        InlineKeyboardButton(text="🏆 Reyting", callback_data="top:all"),
        InlineKeyboardButton(text="👤 Profilim", callback_data="menu:me"),
    )
    kb.row(
        InlineKeyboardButton(text="🧠 Xatolarim", callback_data=f"mode:{MODE_MISTAKES}"),
        InlineKeyboardButton(text="ℹ️ Yordam", callback_data="menu:help"),
    )
    return kb.as_markup()


def modes() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for mode in (MODE_EN_UZ, MODE_UZ_EN, MODE_MIXED):
        kb.row(InlineKeyboardButton(text=MODE_TITLES[mode], callback_data=f"mode:{mode}"))
    kb.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="menu:home"))
    return kb.as_markup()


def counts(mode: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        *[
            InlineKeyboardButton(text=f"{n} ta savol", callback_data=f"start:{mode}:{n}")
            for n in QUESTION_COUNTS
        ]
    )
    kb.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="menu:quiz"))
    return kb.as_markup()


def question(q: Question, number: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i, option in enumerate(q.options):
        kb.row(
            InlineKeyboardButton(
                text=f"{OPTION_LETTERS[i]})  {option}",
                callback_data=f"ans:{number}:{i}",
            )
        )
    kb.row(InlineKeyboardButton(text="⛔ Testni tugatish", callback_data="quiz:stop"))
    return kb.as_markup()


def after_quiz() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔁 Yana test", callback_data="menu:quiz"))
    kb.row(
        InlineKeyboardButton(text="🏆 Reyting", callback_data="top:all"),
        InlineKeyboardButton(text="🧠 Xatolarim", callback_data=f"mode:{MODE_MISTAKES}"),
    )
    kb.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="menu:home"))
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
