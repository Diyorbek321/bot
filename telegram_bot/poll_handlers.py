"""Quiz (savollar Telegram ovoz berish — quiz poll ko'rinishida): shaxsiy chatda yakka, guruhda jamoaviy."""

import asyncio
import logging
import random

from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus, ChatType, PollType
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramRetryAfter
from aiogram.filters import JOIN_TRANSITION, ChatMemberUpdatedFilter, Command, CommandStart
from aiogram.types import CallbackQuery, Chat, ChatMemberUpdated, InlineKeyboardMarkup, Message, PollAnswer

import database as db
import groups_db as gdb
import keyboards as kb
from group_link import join_button, remember_group
from branding import BRAND_FOOTER, BRAND_HEADER, DIVIDER, MEDALS, short_name
from config import (
    BRAND_NAME,
    LEADERBOARD_SIZE,
    MISTAKES_QUIZ_SIZE,
    POINTS_MAX,
    POINTS_MIN,
    POLL_IDLE_LIMIT,
    POLL_PAUSE,
    QUESTION_COUNTS,
    TEAMS,
)
from poll_game import PollGame, poll_explanation, poll_question
from quiz import MODE_MISTAKES, MODE_TITLES, Question, build_questions, level_for, mode_title, pick_words

router = Router()
GROUP_CHATS = {ChatType.GROUP, ChatType.SUPERGROUP}
ADMIN_STATUSES = {ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR}
START_DELAY = 3
# Jamoa tanlash xabarini yangilashdan oldin kutish (ko'p odam birdan bosganda flood limitga tushmaslik uchun)
LOBBY_REFRESH_DELAY = 1.5

# Faol o'yinlar: chat_id -> PollGame, poll_id -> chat_id
games: dict[int, PollGame] = {}
poll_chats: dict[str, int] = {}
tasks: dict[int, asyncio.Task] = {}
lobby_refreshes: dict[int, asyncio.Task] = {}

log = logging.getLogger(__name__)


# ─────────────────────────── Matnlar ───────────────────────────

GROUP_WELCOME = (
    f"{BRAND_HEADER}\n\n"
    f"👋 Salom! Men <b>{BRAND_NAME}</b> quiz botiman.\n\n"
    f"{DIVIDER}\n"
    "👥 Jamoaviy quiz — guruh jamoalarga bo'linib bellashadi\n"
    "⏱ Har bir savolga 20 soniya, savollar birin-ketin poll ko'rinishida\n"
    f"⚡ Tez javob — ko'p ball ({POINTS_MAX} → {POINTS_MIN})\n"
    "🏆 Oxirida g'olib jamoa va eng yaxshi o'yinchilar e'lon qilinadi\n"
    f"{DIVIDER}\n\n"
    "📝 10 ta test, har biri 50 savol — so'zlari PDF va kartochkalarda\n"
    "🏫 <b>Testlarni botda ishlash</b> tugmasini bosgan o'quvchining natijalari shu guruh reytingiga "
    "qo'shiladi\n\n"
    "Test: /test · Guruh reytingi: /top · Havola: /guruh · To'xtatish: /stop\n\n"
    f"{BRAND_FOOTER}"
)

SETUP_MODE_TEXT = "🎯 <b>Quiz</b>\n\nSavol turini tanlang 👇"


def setup_count_text(mode: str) -> str:
    return f"🎯 <b>Quiz</b> · {MODE_TITLES[mode]}\n\n📊 <b>Nechta savol?</b>"


def rules_line(game: PollGame) -> str:
    return (
        f"⏳ Har bir savolga: <b>{game.open_period} soniya</b>\n"
        f"⚡ Tez javob — ko'p ball: <b>{POINTS_MAX} → {POINTS_MIN}</b>"
    )


def lobby_text(game: PollGame) -> str:
    lines = [
        BRAND_HEADER,
        "",
        "👥 <b>Jamoaviy quiz</b>",
        f"<i>{mode_title(game.mode)} · {game.total} ta savol</i>",
        rules_line(game),
        "",
        DIVIDER,
    ]
    for key, title in TEAMS.items():
        members = game.members(key)
        names = ", ".join(short_name(p.name) for p in members) or "—"
        lines.append(f"{title} ({len(members)}): {names}")
    lines += [DIVIDER, ""]
    if game.started:
        lines.append("🚀 Jamoalar tuzildi, quiz boshlandi!")
    else:
        lines.append(
            "Jamoangizni tanlang 👇\n"
            "Hamma tayyor bo'lgach, quizni ochgan odam yoki admin <b>▶️ Boshlash</b> tugmasini bosadi."
        )
    return "\n".join(lines)


def intro_text(game: PollGame) -> str:
    kind = "Jamoaviy quiz" if game.is_group else "Quiz"
    return (
        f"{BRAND_HEADER}\n\n"
        f"🚀 <b>{kind} boshlanmoqda!</b>\n\n"
        f"{DIVIDER}\n"
        f"📝 {mode_title(game.mode)}\n"
        f"📊 Savollar: <b>{game.total}</b>\n"
        f"{rules_line(game)}\n"
        f"{DIVIDER}\n\n"
        f"Birinchi savol {START_DELAY} soniyadan keyin… Tayyormisiz? 🔥"
    )


def player_line(place: int, player, asked: int) -> str:
    badge = MEDALS.get(place, f"<b>{place}.</b>")
    team = f" {TEAMS[player.team].split()[0]}" if player.team else ""
    return f"{badge}{team} {short_name(player.name)} — <b>{player.score}</b> ⭐ · ✅ {player.correct}/{asked}"


def team_results(game: PollGame) -> list[str]:
    teams = game.team_ranking()
    if not teams:
        return []
    if len(teams) > 1 and teams[0].score == teams[1].score:
        lines = ["🤝 <b>Durang!</b>"]
    else:
        lines = [f"🏆 G'olib: <b>{teams[0].title}</b> jamoasi!"]
    lines.append("")
    for place, team in enumerate(teams, start=1):
        badge = MEDALS.get(place, f"<b>{place}.</b>")
        lines.append(
            f"{badge} {team.title} — <b>{team.score}</b> ⭐ · ✅ {team.correct} · 👥 {len(team.members)}"
        )
    return lines + [DIVIDER, "⚡ <b>Eng yaxshi o'yinchilar</b>"]


def private_summary(player, asked: int) -> list[str]:
    percent = player.correct * 100 / asked if asked else 0
    level, comment = level_for(percent)
    return [
        f"{level}\n<i>{comment}</i>",
        "",
        f"✅ To'g'ri javoblar: <b>{player.correct} / {asked}</b>",
        f"🎯 Aniqlik: <b>{percent:.0f}%</b>",
        f"⭐ Olingan ball: <b>+{player.score}</b>",
    ]


def results_text(game: PollGame, asked: int) -> str:
    lines = [
        BRAND_HEADER,
        "",
        "🏁 <b>Quiz yakunlandi!</b>",
        f"<i>{mode_title(game.mode)} · {asked} ta savol</i>",
        "",
        DIVIDER,
    ]
    ranking = [p for p in game.ranking() if p.answered]
    if not ranking:
        lines.append("Hech kim javob bermadi 🤷")
    elif game.is_group:
        lines += team_results(game)
        for place, player in enumerate(ranking[:LEADERBOARD_SIZE], start=1):
            lines.append(player_line(place, player, asked))
    else:
        lines += private_summary(ranking[0], asked)
    lines += [DIVIDER, "", BRAND_FOOTER]
    return "\n".join(lines)


# ─────────────────────────── Yordamchilar ───────────────────────────

async def edit_or_send(query: CallbackQuery, text: str, markup: InlineKeyboardMarkup | None) -> None:
    try:
        await query.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as e:
        if "not modified" not in str(e):
            await query.message.answer(text, reply_markup=markup)


async def is_admin(bot: Bot, chat: Chat, user_id: int) -> bool:
    if chat.type not in GROUP_CHATS:
        return True
    try:
        member = await bot.get_chat_member(chat.id, user_id)
    except TelegramAPIError:
        return False
    return member.status in ADMIN_STATUSES


async def can_stop(bot: Bot, chat: Chat, user_id: int, game: PollGame) -> bool:
    return game.started_by == user_id or await is_admin(bot, chat, user_id)


async def send_with_retry(call):
    """Telegram flood limitiga tushsa, ko'rsatilgan vaqt kutib bir marta qayta yuboradi."""
    try:
        return await call()
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        return await call()


# ─────────────────────────── O'yin jarayoni ───────────────────────────

async def wait_for_answers(game: PollGame) -> bool:
    """Savol vaqti tugashini kutadi. Kimdir javob berganmi — shuni qaytaradi.

    Shaxsiy chatda javob berilishi bilan keyingi savolga o'tiladi, guruhda esa hamma ulgurishi uchun
    vaqt to'liq kutiladi.
    """
    if game.is_group:
        await asyncio.sleep(game.open_period)
        return game.answered.is_set()
    try:
        await asyncio.wait_for(game.answered.wait(), timeout=game.open_period)
    except asyncio.TimeoutError:
        return False
    return True


async def run_game(bot: Bot, game: PollGame) -> None:
    asked = 0
    last_poll_message: int | None = None
    try:
        await send_with_retry(lambda: bot.send_message(game.chat_id, intro_text(game)))
        await asyncio.sleep(START_DELAY)
        for number, question in enumerate(game.questions):
            game.index = number
            game.answered.clear()
            message = await send_with_retry(
                lambda: bot.send_poll(
                    chat_id=game.chat_id,
                    question=poll_question(question, number + 1, game.total),
                    options=question.options,
                    type=PollType.QUIZ,
                    correct_option_id=question.correct_index,
                    is_anonymous=False,
                    open_period=game.open_period,
                    explanation=poll_explanation(question),
                    reply_markup=kb.poll_stop(),
                )
            )
            last_poll_message = message.message_id
            game.sent_at[number] = asyncio.get_running_loop().time()
            game.polls[message.poll.id] = number
            poll_chats[message.poll.id] = game.chat_id
            asked = number + 1

            if await wait_for_answers(game):
                game.idle_questions = 0
            else:
                game.idle_questions += 1
                if game.idle_questions >= POLL_IDLE_LIMIT:
                    await bot.send_message(
                        game.chat_id,
                        f"😴 Ketma-ket {POLL_IDLE_LIMIT} ta savolga javob bo'lmadi — quiz to'xtatildi.",
                    )
                    break
            await asyncio.sleep(POLL_PAUSE)
            last_poll_message = None
    except asyncio.CancelledError:
        pass  # /stop yoki tugma orqali to'xtatildi — natijalar baribir e'lon qilinadi
    except TelegramAPIError:
        log.exception("Quiz xatolik bilan to'xtadi (chat %s)", game.chat_id)
    finally:
        await finish_game(bot, game, asked, last_poll_message)


async def finish_game(bot: Bot, game: PollGame, asked: int, open_poll: int | None) -> None:
    game.stopped = True
    games.pop(game.chat_id, None)
    tasks.pop(game.chat_id, None)
    for poll_id in game.polls:
        poll_chats.pop(poll_id, None)

    for player in game.players.values():
        if not player.answered:
            continue  # jamoaga qo'shilgan, lekin birorta savolga javob bermagan
        db.save_result(
            player.user_id,
            player.score,
            player.correct,
            player.answered,
            player.best_streak,
            mode=game.mode,
            chat_id=game.chat_id,
        )
    if game.is_group and any(player.answered for player in game.players.values()):
        gdb.add_group_game(game.chat_id)
        for player in game.players.values():
            if player.answered:  # guruhda o'ynagan — demak shu guruh a'zosi
                gdb.set_group_if_missing(player.user_id, game.chat_id)

    if open_poll is not None:
        try:
            await bot.stop_poll(game.chat_id, open_poll)
        except TelegramAPIError:
            pass  # vaqti tugagan poll'ni yopib bo'lmaydi — natijalar baribir yuboriladi
    try:
        if asked:
            await bot.send_message(game.chat_id, results_text(game, asked), reply_markup=kb.after_poll_quiz(game.is_group))
    except TelegramAPIError:
        log.exception("Quiz natijasini yuborib bo'lmadi (chat %s)", game.chat_id)


async def stop_game(bot: Bot, chat_id: int) -> None:
    game = games.get(chat_id)
    if game and not game.started:
        await cancel_lobby(bot, game)
        return
    task = tasks.get(chat_id)
    if game:
        game.stopped = True
    if task:
        task.cancel()


def start_game(bot: Bot, game: PollGame) -> None:
    game.started = True
    tasks[game.chat_id] = asyncio.create_task(run_game(bot, game))


# ─────────────────────────── Jamoa tanlash ───────────────────────────

async def cancel_lobby(bot: Bot, game: PollGame) -> None:
    games.pop(game.chat_id, None)
    refresh = lobby_refreshes.pop(game.chat_id, None)
    if refresh:
        refresh.cancel()
    try:
        await bot.edit_message_text("❌ Jamoaviy quiz bekor qilindi.", chat_id=game.chat_id,
                                    message_id=game.lobby_message)
    except TelegramAPIError:
        await bot.send_message(game.chat_id, "❌ Jamoaviy quiz bekor qilindi.")


async def render_lobby(bot: Bot, game: PollGame) -> None:
    markup = None if game.started else kb.team_lobby()
    try:
        await send_with_retry(
            lambda: bot.edit_message_text(
                lobby_text(game), chat_id=game.chat_id, message_id=game.lobby_message, reply_markup=markup
            )
        )
    except TelegramBadRequest as e:
        if "not modified" not in str(e):
            log.warning("Jamoa ro'yxatini yangilab bo'lmadi (chat %s): %s", game.chat_id, e)


def schedule_lobby_refresh(bot: Bot, game: PollGame) -> None:
    """Bir necha soniya ichidagi barcha tanlovlarni bitta tahrir bilan ko'rsatadi."""
    if game.chat_id in lobby_refreshes:
        return

    async def refresh() -> None:
        try:
            await asyncio.sleep(LOBBY_REFRESH_DELAY)
            if games.get(game.chat_id) is game and not game.started:
                await render_lobby(bot, game)
        finally:
            lobby_refreshes.pop(game.chat_id, None)

    lobby_refreshes[game.chat_id] = asyncio.create_task(refresh())


# ─────────────────────────── Guruh ───────────────────────────

async def group_menu(bot: Bot, chat: Chat) -> InlineKeyboardMarkup:
    me = await bot.me()
    return kb.group_menu(join_button(me.username, chat.id))


@router.my_chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION), F.chat.type.in_(GROUP_CHATS))
async def on_added_to_group(event: ChatMemberUpdated) -> None:
    remember_group(event.chat)
    await event.bot.send_message(event.chat.id, GROUP_WELCOME, reply_markup=await group_menu(event.bot, event.chat))


@router.message(CommandStart(), F.chat.type.in_(GROUP_CHATS))
async def cmd_start_group(message: Message) -> None:
    remember_group(message.chat)
    await message.answer(GROUP_WELCOME, reply_markup=await group_menu(message.bot, message.chat))


@router.message(Command("quiz"))
async def cmd_quiz(message: Message) -> None:
    if message.chat.id in games:
        await message.reply("⏳ Bu guruhda quiz allaqachon davom etmoqda. To'xtatish: /stop")
        return
    db.upsert_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    await message.answer(SETUP_MODE_TEXT, reply_markup=kb.poll_modes(message.chat.type in GROUP_CHATS))


@router.message(Command("stop"))
async def cmd_stop(message: Message) -> None:
    game = games.get(message.chat.id)
    if game is None:
        await message.reply("Hozir faol quiz yo'q. Boshlash: /quiz")
        return
    if not await can_stop(message.bot, message.chat, message.from_user.id, game):
        await message.reply("⛔ Quizni faqat uni boshlagan odam yoki admin to'xtata oladi.")
        return
    await stop_game(message.bot, message.chat.id)


# ─────────────────────────── Sozlash tugmalari ───────────────────────────

@router.callback_query(F.data == "pq:menu")
async def on_poll_menu(query: CallbackQuery) -> None:
    await edit_or_send(query, SETUP_MODE_TEXT, kb.poll_modes(query.message.chat.type in GROUP_CHATS))
    await query.answer()


@router.callback_query(F.data.startswith("pq:m:"))
async def on_poll_mode(query: CallbackQuery) -> None:
    mode = query.data.split(":")[2]
    if mode not in MODE_TITLES:
        await query.answer()
        return
    await edit_or_send(query, setup_count_text(mode), kb.poll_counts(mode))
    await query.answer()


@router.callback_query(F.data.startswith("pq:c:"))
async def on_poll_count(query: CallbackQuery) -> None:
    parts = query.data.split(":")
    if len(parts) != 4 or parts[2] not in MODE_TITLES or not parts[3].isdigit():
        await query.answer()
        return
    mode, count = parts[2], int(parts[3])
    if count not in QUESTION_COUNTS:
        await query.answer()
        return
    await launch(query, mode, build_questions(mode, pick_words(count)))


@router.callback_query(F.data == "pq:mistakes")
async def on_poll_mistakes(query: CallbackQuery) -> None:
    if query.message.chat.type in GROUP_CHATS:
        await query.answer("🧠 Xatolar ustida ishlash — bot bilan shaxsiy chatda.", show_alert=True)
        return
    mistakes = db.get_mistakes(query.from_user.id)
    if not mistakes:
        await query.answer("🎉 Sizda hozircha xato qilingan so'zlar yo'q!", show_alert=True)
        return
    word_ids = random.sample(mistakes, k=min(MISTAKES_QUIZ_SIZE, len(mistakes)))
    await launch(query, MODE_MISTAKES, build_questions(MODE_MISTAKES, word_ids))


async def launch(query: CallbackQuery, mode: str, questions: list[Question]) -> None:
    """Shaxsiy chatda quizni darhol boshlaydi, guruhda jamoa tanlashni ochadi."""
    chat = query.message.chat
    if chat.id in games:
        await query.answer("⏳ Bu chatda quiz allaqachon davom etmoqda.", show_alert=True)
        return

    user = query.from_user
    db.upsert_user(user.id, user.full_name, user.username)
    game = PollGame(
        chat_id=chat.id,
        is_group=chat.type in GROUP_CHATS,
        mode=mode,
        questions=questions,
        started_by=user.id,
    )
    games[chat.id] = game

    if game.is_group:
        remember_group(chat)
        game.lobby_message = query.message.message_id
        await render_lobby(query.bot, game)
        await query.answer("👥 Jamoalarni tanlang")
        return

    await query.answer(f"🚀 {game.total} ta savol. Omad!")
    try:
        await query.message.delete()
    except TelegramBadRequest:
        pass
    start_game(query.bot, game)


def lobby_game(query: CallbackQuery) -> PollGame | None:
    game = games.get(query.message.chat.id)
    if game is None or game.started or game.lobby_message != query.message.message_id:
        return None
    return game


@router.callback_query(F.data.startswith("tm:join:"))
async def on_team_join(query: CallbackQuery) -> None:
    game = lobby_game(query)
    if game is None:
        await query.answer("Jamoa tanlash yopilgan.")
        return
    team = query.data.split(":")[2]
    if team not in TEAMS:
        await query.answer()
        return
    user = query.from_user
    db.upsert_user(user.id, user.full_name, user.username)
    if game.join_team(user.id, user.full_name, team):
        schedule_lobby_refresh(query.bot, game)
    await query.answer(f"✅ Siz {TEAMS[team]} jamoasidasiz")


@router.callback_query(F.data == "tm:start")
async def on_team_start(query: CallbackQuery) -> None:
    game = lobby_game(query)
    if game is None:
        await query.answer("Quiz allaqachon boshlangan yoki bekor qilingan.")
        return
    if not await can_stop(query.bot, query.message.chat, query.from_user.id, game):
        await query.answer("⛔ Quizni faqat uni ochgan odam yoki admin boshlay oladi.", show_alert=True)
        return
    if len(game.active_teams()) < 2:
        await query.answer("👥 Kamida 2 ta jamoada o'yinchi bo'lishi kerak.", show_alert=True)
        return
    refresh = lobby_refreshes.pop(game.chat_id, None)
    if refresh:
        refresh.cancel()
    start_game(query.bot, game)
    await query.answer("🚀 Boshladik!")
    await render_lobby(query.bot, game)


@router.callback_query(F.data == "tm:cancel")
async def on_team_cancel(query: CallbackQuery) -> None:
    game = lobby_game(query)
    if game is None:
        await query.answer()
        return
    if not await can_stop(query.bot, query.message.chat, query.from_user.id, game):
        await query.answer("⛔ Faqat quizni ochgan odam yoki admin bekor qila oladi.", show_alert=True)
        return
    await query.answer("❌ Bekor qilindi")
    await cancel_lobby(query.bot, game)


@router.callback_query(F.data == "pq:stop")
async def on_poll_stop(query: CallbackQuery) -> None:
    chat = query.message.chat
    game = games.get(chat.id)
    if game is None:
        await query.answer("Quiz allaqachon tugagan.")
        return
    if not await can_stop(query.bot, chat, query.from_user.id, game):
        await query.answer("⛔ Faqat quizni boshlagan odam yoki admin to'xtata oladi.", show_alert=True)
        return
    await query.answer("⛔ Quiz to'xtatildi")
    await stop_game(query.bot, chat.id)


# ─────────────────────────── Javoblar ───────────────────────────

@router.poll_answer()
async def on_poll_answer(answer: PollAnswer) -> None:
    now = asyncio.get_running_loop().time()  # javob tezligi uchun — bazaga yozishdan oldin olinadi
    game = games.get(poll_chats.get(answer.poll_id, 0))
    # user bo'lmasa — guruh nomidan anonim javob; bunday javoblar hisobga olinmaydi
    if game is None or answer.user is None or not answer.option_ids:
        return
    user = answer.user
    db.upsert_user(user.id, user.full_name, user.username)
    result = game.record_answer(answer.poll_id, user.id, user.full_name, answer.option_ids[0], now)
    if result is None:
        return
    question, is_correct, _ = result
    if is_correct:
        db.remove_mistake(user.id, question.word_id)
    else:
        db.add_mistake(user.id, question.word_id)
