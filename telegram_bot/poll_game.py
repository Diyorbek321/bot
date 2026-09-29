"""Vaqtli quiz: savollar Telegram quiz poll ko'rinishida yuboriladi.

Shaxsiy chatda — yakka o'yin. Guruhda — jamoaviy: qatnashchilar jamoalarga bo'linadi,
har bir a'zoning tezlikka qarab olgan bali jamoasiga qo'shiladi.
"""

import asyncio
from dataclasses import dataclass, field

from config import QUESTION_TIME, TEAMS
from quiz import MODE_DEFINITION, MODE_EN_UZ, MODE_SENTENCE, MODE_SYNONYM, Question, speed_points
from vocab import VOCAB

# Telegram cheklovlari
POLL_QUESTION_LIMIT = 300
POLL_EXPLANATION_LIMIT = 200


@dataclass
class Player:
    user_id: int
    name: str
    team: str | None = None
    score: int = 0
    correct: int = 0
    answered: int = 0
    streak: int = 0
    best_streak: int = 0
    last_question: int = -2


@dataclass(frozen=True)
class TeamScore:
    key: str
    title: str
    score: int
    correct: int
    members: tuple[Player, ...]


@dataclass
class PollGame:
    chat_id: int
    is_group: bool
    mode: str
    questions: list[Question]
    started_by: int
    open_period: int = QUESTION_TIME
    index: int = 0
    idle_questions: int = 0
    started: bool = False
    stopped: bool = False
    # Guruhdagi jamoa tanlash xabari
    lobby_message: int | None = None
    players: dict[int, Player] = field(default_factory=dict)
    # poll_id -> savol raqami
    polls: dict[str, int] = field(default_factory=dict)
    # savol raqami -> yuborilgan vaqt (loop.time())
    sent_at: dict[int, float] = field(default_factory=dict)
    # Joriy savolga kimdir javob berganda o'rnatiladi (shaxsiy chatda darhol keyingi savolga o'tish uchun)
    answered: asyncio.Event = field(default_factory=asyncio.Event)

    @property
    def total(self) -> int:
        return len(self.questions)

    @property
    def current(self) -> Question:
        return self.questions[self.index]

    # ───────────── Jamoalar ─────────────

    def join_team(self, user_id: int, name: str, team: str) -> bool:
        """Qatnashchini jamoaga qo'shadi (boshqa jamoadan ko'chiradi). O'zgarish bo'lsa True."""
        if team not in TEAMS:
            return False
        player = self.players.setdefault(user_id, Player(user_id, name))
        player.name = name
        if player.team == team:
            return False
        player.team = team
        return True

    def members(self, team: str) -> list[Player]:
        return [p for p in self.players.values() if p.team == team]

    def active_teams(self) -> list[str]:
        return [key for key in TEAMS if self.members(key)]

    def _auto_team(self) -> str:
        """Kechikib qo'shilgan qatnashchi uchun eng kam a'zoli (faol) jamoa."""
        candidates = self.active_teams() or list(TEAMS)
        return min(candidates, key=lambda key: len(self.members(key)))

    # ───────────── Javoblar ─────────────

    def record_answer(
        self, poll_id: str, user_id: int, name: str, option: int, now: float
    ) -> tuple[Question, bool, int] | None:
        """Javobni hisoblaydi. (savol, to'g'rimi, ball) yoki eski/noma'lum poll bo'lsa None qaytaradi."""
        number = self.polls.get(poll_id)
        if number is None or self.stopped:
            return None
        player = self.players.get(user_id)
        if player is None:
            player = Player(user_id, name)
            if self.is_group:
                player.team = self._auto_team()
            self.players[user_id] = player
        if player.last_question == number:
            return None  # quiz poll'da javobni o'zgartirib bo'lmaydi, lekin baribir himoya
        if player.last_question != number - 1:
            player.streak = 0
        player.last_question = number
        player.answered += 1

        question = self.questions[number]
        is_correct = option == question.correct_index
        gained = 0
        if is_correct:
            player.streak += 1
            player.best_streak = max(player.best_streak, player.streak)
            gained = speed_points(now - self.sent_at.get(number, now), self.open_period)
            player.score += gained
            player.correct += 1
        else:
            player.streak = 0
        if number == self.index:
            self.answered.set()
        return question, is_correct, gained

    def ranking(self) -> list[Player]:
        return sorted(self.players.values(), key=lambda p: (-p.score, -p.correct, p.answered))

    def team_ranking(self) -> list[TeamScore]:
        scores = []
        for key in self.active_teams():
            members = tuple(p for p in self.ranking() if p.team == key)
            scores.append(
                TeamScore(
                    key=key,
                    title=TEAMS[key],
                    score=sum(p.score for p in members),
                    correct=sum(p.correct for p in members),
                    members=members,
                )
            )
        return sorted(scores, key=lambda t: (-t.score, -t.correct))


def poll_question(question: Question, number: int, total: int) -> str:
    """Poll sarlavhasi: "[3/50] After sitting for hours, I went outside to ____."."""
    if question.direction == MODE_SENTENCE:
        body = question.prompt
    elif question.direction == MODE_EN_UZ:
        body = f"🇬🇧 {question.prompt} — o'zbekcha tarjimasi?"
    elif question.direction == MODE_DEFINITION:
        body = f"📘 Which word means: \"{question.prompt}\""
    elif question.direction == MODE_SYNONYM:
        body = f"🔁 Which word is a synonym of \"{question.prompt}\"?"
    else:
        body = f"🇺🇿 {question.prompt} — inglizcha tarjimasi?"
    return f"[{number}/{total}] {body}"[:POLL_QUESTION_LIMIT]


def poll_explanation(question: Question) -> str:
    """Javobdan keyin chiqadigan izoh: so'z, tarjimasi va assotsiatsiya."""
    hint = f"📖 {question.word_hint}"
    association = VOCAB[question.word_id]["association"]
    full = f"{hint}\n💡 {association}"
    return full if len(full) <= POLL_EXPLANATION_LIMIT else hint[:POLL_EXPLANATION_LIMIT]
