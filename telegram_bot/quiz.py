import json
import random
from dataclasses import dataclass, field

from config import POINTS_MAX, POINTS_MIN, QUESTION_TIME, SENTENCES_PATH, WORDS_PATH

# Test yo'nalishlari
MODE_EN_UZ = "en_uz"
MODE_UZ_EN = "uz_en"
MODE_SENTENCE = "sent"
MODE_MIXED = "mix"
MODE_MISTAKES = "mistakes"

MODE_TITLES = {
    MODE_EN_UZ: "🇬🇧 → 🇺🇿 Inglizcha → O'zbekcha",
    MODE_UZ_EN: "🇺🇿 → 🇬🇧 O'zbekcha → Inglizcha",
    MODE_SENTENCE: "✍️ Gap to'ldirish",
    MODE_MIXED: "🔀 Aralash",
    MODE_MISTAKES: "🧠 Xatolar ustida ishlash",
}

OPTION_LETTERS = ("A", "B", "C", "D")


def load_words() -> list[dict]:
    with open(WORDS_PATH, encoding="utf-8") as f:
        words = json.load(f)
    return [w for w in words if w.get("en") and w.get("uz")]


def load_sentences(words: list[dict]) -> dict[int, list[dict]]:
    """word_id -> shu so'z ishlatilgan gaplar ("____" o'rniga to'g'ri javob qo'yiladi)."""
    with open(SENTENCES_PATH, encoding="utf-8") as f:
        bank = {item["word"]: item["sentences"] for item in json.load(f)}
    return {i: bank[w["en"]] for i, w in enumerate(words) if bank.get(w["en"])}


WORDS = load_words()
SENTENCES = load_sentences(WORDS)
DIRECTIONS = (MODE_EN_UZ, MODE_UZ_EN, MODE_SENTENCE)


@dataclass
class Question:
    word_id: int
    prompt: str
    direction: str  # MODE_EN_UZ, MODE_UZ_EN yoki MODE_SENTENCE
    options: list[str]
    correct_index: int

    @property
    def correct_answer(self) -> str:
        return self.options[self.correct_index]

    @property
    def word_hint(self) -> str:
        """So'z va tarjimasi: "achieve — erishmoq"."""
        word = WORDS[self.word_id]
        return f"{word['en']} — {word['uz']}"


def speed_points(elapsed: float, limit: float = QUESTION_TIME) -> int:
    """To'g'ri javob uchun ball: qancha tez javob berilsa, shuncha ko'p (POINTS_MAX → POINTS_MIN)."""
    share = min(max(elapsed / limit, 0.0), 1.0)
    return round(POINTS_MAX - (POINTS_MAX - POINTS_MIN) * share)


@dataclass
class QuizSession:
    mode: str
    questions: list[Question]
    index: int = 0
    score: int = 0
    correct: int = 0
    streak: int = 0
    best_streak: int = 0
    last_feedback: str = ""
    # Joriy savol ko'rsatilgan vaqt (event loop vaqti)
    asked_at: float = 0.0
    # Ketma-ket vaqti tugagan savollar (foydalanuvchi ketib qolgan bo'lsa testni to'xtatish uchun)
    timeouts_in_row: int = 0
    wrong_words: list[int] = field(default_factory=list)

    @property
    def current(self) -> Question:
        return self.questions[self.index]

    @property
    def finished(self) -> bool:
        return self.index >= len(self.questions)

    def answer(self, option_index: int, elapsed: float) -> tuple[bool, int]:
        """Javobni tekshiradi. (to'g'rimi, olingan ball) qaytaradi."""
        question = self.current
        is_correct = option_index == question.correct_index
        gained = 0
        self.timeouts_in_row = 0
        if is_correct:
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
            gained = speed_points(elapsed)
            self.score += gained
            self.correct += 1
        else:
            self._miss()
        self.index += 1
        return is_correct, gained

    def timeout(self) -> None:
        """Vaqt tugadi — savol javobsiz qoldi, keyingisiga o'tiladi."""
        self.timeouts_in_row += 1
        self._miss()
        self.index += 1

    def _miss(self) -> None:
        self.streak = 0
        self.wrong_words.append(self.current.word_id)


def _make_sentence_question(word_id: int) -> Question:
    sentence = random.choice(SENTENCES[word_id])
    options = [sentence["answer"], *sentence["wrong"]]
    random.shuffle(options)
    return Question(
        word_id=word_id,
        prompt=sentence["text"],
        direction=MODE_SENTENCE,
        options=options,
        correct_index=options.index(sentence["answer"]),
    )


def make_question(word_id: int, direction: str) -> Question:
    if direction == MODE_SENTENCE:
        if word_id in SENTENCES:
            return _make_sentence_question(word_id)
        direction = MODE_EN_UZ  # bu so'z uchun gap yo'q — tarjima savoli beriladi
    word = WORDS[word_id]
    if direction == MODE_EN_UZ:
        prompt_key, answer_key = "en", "uz"
    else:
        prompt_key, answer_key = "uz", "en"
    prompt = word[prompt_key]

    correct = word[answer_key]
    distractors: list[str] = []
    candidates = random.sample(range(len(WORDS)), k=min(len(WORDS), 40))
    for other_id in candidates:
        other = WORDS[other_id]
        text = other[answer_key]
        # Lug'atda bir xil tarjimali so'zlar bor (masalan, "ayniqsa" = particularly / especially),
        # shuning uchun ular noto'g'ri variant sifatida chiqmasligi kerak
        same_meaning = other[prompt_key].lower() == prompt.lower()
        if (
            other_id != word_id
            and not same_meaning
            and text.lower() != correct.lower()
            and text not in distractors
        ):
            distractors.append(text)
        if len(distractors) == 3:
            break

    options = distractors + [correct]
    random.shuffle(options)
    return Question(
        word_id=word_id,
        prompt=prompt,
        direction=direction,
        options=options,
        correct_index=options.index(correct),
    )


def build_session(mode: str, count: int, word_ids: list[int] | None = None) -> QuizSession:
    """Yangi test sessiyasini yaratadi.

    word_ids berilsa (masalan, xatolar rejimida) savollar faqat shu so'zlardan tuziladi.
    """
    pool = word_ids if word_ids else list(range(len(WORDS)))
    chosen = random.sample(pool, k=min(count, len(pool)))
    return QuizSession(mode=mode, questions=build_questions(mode, chosen))


def build_questions(mode: str, word_ids: list[int]) -> list[Question]:
    """Rejimga qarab savollar: aniq yo'nalish yoki aralash (xatolar rejimi ham aralash)."""
    return [
        make_question(word_id, mode if mode in DIRECTIONS else random.choice(DIRECTIONS))
        for word_id in word_ids
    ]


def pick_words(count: int) -> list[int]:
    return random.sample(range(len(WORDS)), k=min(count, len(WORDS)))


def progress_bar(done: int, total: int, width: int = 10) -> str:
    filled = round(width * done / total) if total else 0
    return "🟩" * filled + "⬜" * (width - filled)


def level_for(percent: float) -> tuple[str, str]:
    """Natija foiziga qarab daraja nomi va izoh."""
    if percent >= 90:
        return "🏆 Ajoyib!", "Siz haqiqiy B2 ustasisiz!"
    if percent >= 75:
        return "🥇 Zo'r!", "Juda yaxshi natija, shu tarzda davom eting!"
    if percent >= 50:
        return "🥈 Yaxshi", "Yomon emas, yana biroz mashq qiling."
    if percent >= 30:
        return "🥉 O'rtacha", "So'zlarni takrorlash foydali bo'ladi."
    return "📚 Mashq kerak", "Xafa bo'lmang, har bir urinish sizni oldinga siljitadi!"
