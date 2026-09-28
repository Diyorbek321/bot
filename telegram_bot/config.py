from os import getenv
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TOKEN = getenv("TOKEN")
DB_PATH = getenv("DB_PATH", str(BASE_DIR / "quiz.db"))
WORDS_PATH = BASE_DIR / "words.json"

# Bir testdagi savollar soni uchun variantlar
QUESTION_COUNTS = (10, 20, 30)
# "Xatolarim" rejimida bir martada beriladigan savollar soni
MISTAKES_QUIZ_SIZE = 20

# Ball tizimi
POINTS_CORRECT = 10
STREAK_BONUS_STEP = 2
STREAK_BONUS_MAX = 10

LEADERBOARD_SIZE = 10

# Brend
BRAND_NAME = "Shanghai School"
BRAND_SLOGAN = "Bilim sari birga! 🚀"
