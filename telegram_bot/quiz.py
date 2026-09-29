import json
import random
from dataclasses import dataclass

from config import POINTS_MAX, POINTS_MIN, QUESTION_TIME, SENTENCES_PATH, WORDS_PATH

# Test yo'nalishlari
MODE_EN_UZ = "en_uz"
MODE_UZ_EN = "uz_en"
MODE_SENTENCE = "sent"
MODE_MIXED = "mix"
MODE_MISTAKES = "mistakes"
# Kunlik test savollari uchun qo'shimcha turlar
MODE_DEFINITION = "def"
MODE_SYNONYM = "syn"
MODE_ANTONYM = "ant"
# 50 savollik test rejimi: "day1" … "day10" (Test 1 … Test 10)
MODE_DAY = "day"

MODE_TITLES = {
    MODE_EN_UZ: "🇬🇧 → 🇺🇿 Inglizcha → O'zbekcha",
    MODE_UZ_EN: "🇺🇿 → 🇬🇧 O'zbekcha → Inglizcha",
    MODE_SENTENCE: "✍️ Gap to'ldirish",
    MODE_MIXED: "🔀 Aralash",
    MODE_MISTAKES: "🧠 Xatolar ustida ishlash",
}


def mode_title(mode: str) -> str:
    if mode.startswith(MODE_DAY):
        return f"📝 Test {mode[len(MODE_DAY):]}"
    return MODE_TITLES[mode]


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
    direction: str  # MODE_EN_UZ, MODE_UZ_EN, MODE_SENTENCE, MODE_DEFINITION, MODE_SYNONYM yoki MODE_ANTONYM
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


def build_questions(mode: str, word_ids: list[int]) -> list[Question]:
    """Rejimga qarab savollar: aniq yo'nalish yoki aralash (xatolar rejimi ham aralash)."""
    return [
        make_question(word_id, mode if mode in DIRECTIONS else random.choice(DIRECTIONS))
        for word_id in word_ids
    ]


def pick_words(count: int) -> list[int]:
    return random.sample(range(len(WORDS)), k=min(count, len(WORDS)))


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
