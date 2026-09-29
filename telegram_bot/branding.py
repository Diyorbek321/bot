"""Bot matnlarida umumiy ishlatiladigan bezaklar."""

from html import escape

from config import BRAND_NAME, BRAND_SLOGAN

MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}
DIVIDER = "━━━━━━━━━━━━━━━━━━"
BRAND_HEADER = f"🏫 <b>{BRAND_NAME.upper()}</b> · <i>English Quiz</i>"
BRAND_FOOTER = f"<i>🏫 {BRAND_NAME} — {BRAND_SLOGAN}</i>"


def short_name(name: str, limit: int = 18) -> str:
    name = name.strip() or "Foydalanuvchi"
    return escape(name if len(name) <= limit else name[: limit - 1] + "…")
