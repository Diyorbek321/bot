"""PDF lug'atdan words.json faylini yaratadi.

Foydalanish:
    python extract_words.py lugat.pdf

PDF ichidagi qatorlar "1. achieve — erishmoq" ko'rinishida bo'lishi kerak.
"""
import json
import re
import sys

from pypdf import PdfReader

from config import WORDS_PATH

ENTRY = re.compile(r"^\s*(\d+)\.\s*(.+?)\s+[—–-]\s+(.+?)\s*$")


def normalize(text: str) -> str:
    # PDF'dagi turli apostroflarni bitta ko'rinishga keltiramiz
    return re.sub(r"\s+", " ", text.replace("‘", "'").replace("’", "'").replace("ʻ", "'")).strip()


def extract(pdf_path: str) -> list[dict]:
    text = "\n".join(page.extract_text() or "" for page in PdfReader(pdf_path).pages)
    words: list[dict] = []
    for line in text.splitlines():
        match = ENTRY.match(line)
        if match:
            _, en, uz = match.groups()
            words.append({"en": normalize(en), "uz": normalize(uz)})
        elif words and line.strip() and not line.strip()[0].isdigit():
            # Keyingi qatorga o'tib ketgan tarjima davomi
            words[-1]["uz"] = normalize(f"{words[-1]['uz']} {line}")
    return words


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Foydalanish: python extract_words.py lugat.pdf")
    result = extract(sys.argv[1])
    with open(WORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"{len(result)} ta so'z {WORDS_PATH} fayliga yozildi")
