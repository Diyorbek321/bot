from os import getenv
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TOKEN = getenv("TOKEN")
# Admin panel (/admin) — Telegram ID'lar vergul bilan: ADMIN_IDS=123456789,987654321
ADMIN_IDS = frozenset(int(x) for x in getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x.isdigit())
DB_PATH = getenv("DB_PATH", str(BASE_DIR / "quiz.db"))
WORDS_PATH = BASE_DIR / "words.json"
SENTENCES_PATH = BASE_DIR / "sentences.json"
# So'zlar kartochkasi: definition, sinonim, antonim, misol, assotsiatsiya
VOCAB_PATH = BASE_DIR / "vocab.json"
PDF_DIR = BASE_DIR / "pdf"

# Bir testdagi savollar soni uchun variantlar (eng kamida 50 ta)
QUESTION_COUNTS = (50, 75, 100)
# "Xatolarim" rejimida bir martada beriladigan savollar soni
MISTAKES_QUIZ_SIZE = 50

# Kunlik lug'at: DAY_COUNT kun × DAY_SIZE so'z, har kunga bitta test
DAY_SIZE = 50
DAY_COUNT = 10
# "So'zlar" bo'limida bir sahifadagi kartochkalar soni
CARDS_PER_PAGE = 5

# Har bir savolga beriladigan vaqt, soniyada — tugasa keyingi savolga o'tiladi
QUESTION_TIME = 20
# Savol yopilgach keyingisigacha pauza
POLL_PAUSE = 2
# Shuncha savolga ketma-ket hech kim javob bermasa, quiz o'zi to'xtaydi
POLL_IDLE_LIMIT = 3

# Ball tizimi — tezlikka qarab: darhol to'g'ri javob POINTS_MAX, oxirgi soniyada POINTS_MIN
POINTS_MAX = 100
POINTS_MIN = 50

# Guruhdagi jamoalar: kalit -> nomi
TEAMS = {
    "red": "🔴 Qizil",
    "blue": "🔵 Ko'k",
    "green": "🟢 Yashil",
    "yellow": "🟡 Sariq",
}

LEADERBOARD_SIZE = 10

# Brend
BRAND_NAME = "Shanghai School"
BRAND_SLOGAN = "Bilim sari birga! 🚀"
