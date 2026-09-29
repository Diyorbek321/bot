"""vocab.json dan har bir kun uchun PDF lug'at yaratadi (pdf/day01.pdf … pdf/day10.pdf).

Andoza: "Day 26 intermediate" jadvali + Association ustuni.
Foydalanish (fpdf2 va DejaVu shrifti kerak, faqat PDF'larni qayta yaratishda):
    pip install fpdf2
    python build_pdfs.py
"""

from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace

from config import BRAND_NAME, DAY_COUNT
from vocab import VOCAB, day_pdf_path, day_word_ids

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
HEADERS = ("Word/Phrase", "Definition", "Uzbek Translation", "Synonym", "Antonym",
           "Funnier & Memorable Example", "Association (eslab qolish)")
# A4 albom: 277 mm ishchi kenglik
COL_WIDTHS = (30, 38, 32, 25, 25, 65, 62)


def markdown_safe(text: str) -> str:
    # fpdf2 markdown'ida "__" va "--" formatlash belgisi — oddiy matnda ular uchramasligi kerak
    return text.replace("__", "_ _").replace("--", "- -")


def build_day(day: int) -> Path:
    pdf = FPDF(orientation="L", format="A4")
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(True, margin=10)
    pdf.add_font("DejaVu", "", FONT_DIR / "DejaVuSans.ttf")
    pdf.add_font("DejaVu", "B", FONT_DIR / "DejaVuSans-Bold.ttf")
    pdf.add_font("DejaVu", "I", FONT_DIR / "DejaVuSans-Oblique.ttf")
    pdf.set_title(f"{BRAND_NAME} — Day {day} vocabulary")
    pdf.add_page()

    ids = day_word_ids(day)
    pdf.set_font("DejaVu", "B", 15)
    pdf.cell(0, 9, f"{BRAND_NAME} · Day {day} · Vocabulary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "I", 9)
    pdf.cell(0, 6, f"So'zlar {ids[0] + 1}–{ids[-1] + 1} · 50 ta so'z · Test: botda \"Day {day} testi\"",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("DejaVu", "", 8)
    heading = FontFace(emphasis="BOLD", fill_color=(230, 236, 245))
    with pdf.table(col_widths=COL_WIDTHS, headings_style=heading, line_height=4,
                   markdown=True, repeat_headings=1, padding=1.5, text_align="LEFT") as table:
        table.row(HEADERS)
        for word_id in ids:
            entry = VOCAB[word_id]
            table.row((
                f"**{markdown_safe(entry['en'])}**",
                markdown_safe(entry["definition"]),
                markdown_safe(entry["uz"]),
                markdown_safe(entry["synonym"] or "—"),
                markdown_safe(entry["antonym"] or "—"),
                markdown_safe(entry["example"]),
                markdown_safe(entry["association"]),
            ))

    path = day_pdf_path(day)
    path.parent.mkdir(exist_ok=True)
    pdf.output(str(path))
    return path


if __name__ == "__main__":
    for day in range(1, DAY_COUNT + 1):
        print(build_day(day))
