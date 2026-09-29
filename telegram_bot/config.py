from os import getenv
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TOKEN = getenv("TOKEN")
DB_PATH = getenv("DB_PATH", str(BASE_DIR / "quiz.db"))
WORDS_PATH = BASE_DIR / "words.json"
SENTENCES_PATH = BASE_DIR / "sentences.json"

# Bir testdagi savollar soni uchun variantlar (eng kamida 50 ta)
QUESTION_COUNTS = (50, 75, 100)
# "Xatolarim" rejimida bir martada beriladigan savollar soni
MISTAKES_QUIZ_SIZE = 50

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
