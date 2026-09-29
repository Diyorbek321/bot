"""Guruhlar va o'quvchilarning guruhga biriktirilishi.

O'quvchilar testni odatda bot bilan shaxsiy chatda ishlaydi, shuning uchun guruh natijasi — guruhga
biriktirilgan o'quvchilarning (users.group_id) barcha natijalari, qayerda ishlanganidan qat'i nazar.
"""

import sqlite3
from contextlib import closing

from database import _connect, _now

# Aniqlik — guruhlar kattaligi har xil bo'lgani uchun adolatli ko'rsatkich; natijasiz guruhlar oxirida
GROUP_ORDER = {
    "acc": "(answered = 0), CAST(correct AS REAL) / MAX(answered, 1) DESC, total_score DESC",
    "score": "total_score DESC, CAST(correct AS REAL) / MAX(answered, 1) DESC",
}


def upsert_group(chat_id: int, title: str) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(
            """
            INSERT INTO groups (chat_id, title, added_at) VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET title = excluded.title
            """,
            (chat_id, title, _now()),
        )


def add_group_game(chat_id: int) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("UPDATE groups SET games = games + 1 WHERE chat_id = ?", (chat_id,))


def get_group(chat_id: int) -> sqlite3.Row | None:
    with closing(_connect()) as conn:
        return conn.execute("SELECT * FROM groups WHERE chat_id = ?", (chat_id,)).fetchone()


# ─────────────────────────── A'zolik ───────────────────────────

def set_user_group(user_id: int, chat_id: int) -> None:
    """O'quvchini guruhga biriktiradi (oldingi guruh o'rniga)."""
    with closing(_connect()) as conn, conn:
        conn.execute("UPDATE users SET group_id = ? WHERE user_id = ?", (chat_id, user_id))


def set_group_if_missing(user_id: int, chat_id: int) -> None:
    """Guruhda faollik ko'rsatgan, lekin hali hech qaysi guruhga biriktirilmagan o'quvchi uchun."""
    with closing(_connect()) as conn, conn:
        conn.execute(
            "UPDATE users SET group_id = ? WHERE user_id = ? AND group_id IS NULL", (chat_id, user_id)
        )


def user_group(user_id: int) -> sqlite3.Row | None:
    with closing(_connect()) as conn:
        return conn.execute(
            "SELECT g.* FROM users u JOIN groups g ON g.chat_id = u.group_id WHERE u.user_id = ?",
            (user_id,),
        ).fetchone()


def ungrouped_students() -> int:
    """Test ishlagan, lekin hech qaysi guruhga biriktirilmagan o'quvchilar soni."""
    with closing(_connect()) as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM users WHERE quizzes > 0 AND group_id IS NULL"
        ).fetchone()[0]


# ─────────────────────────── Reytinglar ───────────────────────────

def group_ranking(order: str) -> list[sqlite3.Row]:
    """Guruhlar reytingi: a'zolar, test ishlaganlar, testlar soni, ball va aniqlik."""
    with closing(_connect()) as conn:
        return conn.execute(
            f"""
            SELECT * FROM (
                SELECT g.chat_id, g.title, g.games,
                       COUNT(DISTINCT u.user_id) AS members,
                       COUNT(DISTINCT r.user_id) AS students,
                       COUNT(r.id) AS tests,
                       COALESCE(SUM(r.score), 0) AS total_score,
                       COALESCE(SUM(r.correct), 0) AS correct,
                       COALESCE(SUM(r.total), 0) AS answered,
                       MAX(r.finished_at) AS last_active
                FROM groups g
                LEFT JOIN users u ON u.group_id = g.chat_id
                LEFT JOIN results r ON r.user_id = u.user_id
                GROUP BY g.chat_id
            )
            ORDER BY {GROUP_ORDER[order]}
            """
        ).fetchall()


def group_place(chat_id: int) -> tuple[int, int] | None:
    """Guruhning aniqlik bo'yicha o'rni va natijasi bor guruhlar soni."""
    ranked = [row["chat_id"] for row in group_ranking("acc") if row["answered"]]
    if chat_id not in ranked:
        return None
    return ranked.index(chat_id) + 1, len(ranked)


def group_students(chat_id: int, limit: int) -> list[sqlite3.Row]:
    """Guruh a'zolari reytingi — hali test ishlamaganlar ham (oxirida, 0 ball bilan)."""
    with closing(_connect()) as conn:
        return conn.execute(
            """
            SELECT u.user_id, u.full_name, u.username,
                   COALESCE(SUM(r.score), 0) AS score, COALESCE(SUM(r.correct), 0) AS correct,
                   COALESCE(SUM(r.total), 0) AS answered, COUNT(r.id) AS games,
                   MAX(r.finished_at) AS last_active
            FROM users u
            LEFT JOIN results r ON r.user_id = u.user_id
            WHERE u.group_id = ?
            GROUP BY u.user_id
            ORDER BY score DESC, correct DESC, u.full_name
            LIMIT ?
            """,
            (chat_id, limit),
        ).fetchall()


def group_tests(chat_id: int) -> list[sqlite3.Row]:
    """Guruhning har bir test bo'yicha natijasi: a'zolar eng yaxshi natijalarining o'rtachasi."""
    with closing(_connect()) as conn:
        return conn.execute(
            """
            SELECT mode, COUNT(*) AS participants, AVG(best) AS avg_best, MAX(total) AS total
            FROM (
                SELECT r.mode, r.user_id, MAX(r.correct) AS best, MAX(r.total) AS total
                FROM results r
                JOIN users u ON u.user_id = r.user_id
                WHERE u.group_id = ? AND r.mode IS NOT NULL
                GROUP BY r.mode, r.user_id
            )
            GROUP BY mode
            """,
            (chat_id,),
        ).fetchall()
