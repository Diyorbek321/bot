import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id        INTEGER PRIMARY KEY,
    full_name      TEXT NOT NULL,
    username       TEXT,
    total_score    INTEGER NOT NULL DEFAULT 0,
    correct        INTEGER NOT NULL DEFAULT 0,
    answered       INTEGER NOT NULL DEFAULT 0,
    quizzes        INTEGER NOT NULL DEFAULT 0,
    best_streak    INTEGER NOT NULL DEFAULT 0,
    joined_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS results (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    score       INTEGER NOT NULL,
    correct     INTEGER NOT NULL,
    total       INTEGER NOT NULL,
    finished_at TEXT NOT NULL,
    mode        TEXT,     -- test turi: "day3" = Test 3, "sent", "mix", …
    chat_id     INTEGER   -- qaysi chatda (guruh yoki shaxsiy) ishlangan
);

CREATE TABLE IF NOT EXISTS mistakes (
    user_id  INTEGER NOT NULL,
    word_id  INTEGER NOT NULL,
    count    INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id, word_id)
);

CREATE TABLE IF NOT EXISTS groups (
    chat_id   INTEGER PRIMARY KEY,
    title     TEXT NOT NULL,
    games     INTEGER NOT NULL DEFAULT 0,  -- guruhda o'tkazilgan quizlar soni
    added_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_results_time ON results (finished_at);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# Eski bazalarga qo'shiladigan ustunlar (ALTER TABLE — ma'lumotlar saqlanib qoladi)
MIGRATIONS = {"results": {"mode": "TEXT", "chat_id": "INTEGER"}}


def init_db() -> None:
    with closing(_connect()) as conn, conn:
        conn.executescript(SCHEMA)
        for table, columns in MIGRATIONS.items():
            existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
            for column, kind in columns.items():
                if column not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {kind}")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_results_user_mode ON results (user_id, mode)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_results_chat ON results (chat_id)")


def upsert_user(user_id: int, full_name: str, username: str | None) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(
            """
            INSERT INTO users (user_id, full_name, username, joined_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                full_name = excluded.full_name,
                username  = excluded.username
            """,
            (user_id, full_name, username, _now()),
        )


def save_result(
    user_id: int,
    score: int,
    correct: int,
    total: int,
    best_streak: int,
    mode: str | None = None,
    chat_id: int | None = None,
) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO results (user_id, score, correct, total, finished_at, mode, chat_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, score, correct, total, _now(), mode, chat_id),
        )
        conn.execute(
            """
            UPDATE users SET
                total_score = total_score + ?,
                correct     = correct + ?,
                answered    = answered + ?,
                quizzes     = quizzes + 1,
                best_streak = MAX(best_streak, ?)
            WHERE user_id = ?
            """,
            (score, correct, total, best_streak, user_id),
        )


def add_mistake(user_id: int, word_id: int) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(
            """
            INSERT INTO mistakes (user_id, word_id) VALUES (?, ?)
            ON CONFLICT(user_id, word_id) DO UPDATE SET count = count + 1
            """,
            (user_id, word_id),
        )


def remove_mistake(user_id: int, word_id: int) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM mistakes WHERE user_id = ? AND word_id = ?", (user_id, word_id))


def get_mistakes(user_id: int) -> list[int]:
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT word_id FROM mistakes WHERE user_id = ? ORDER BY count DESC", (user_id,)
        ).fetchall()
    return [row["word_id"] for row in rows]


def get_user(user_id: int) -> sqlite3.Row | None:
    with closing(_connect()) as conn:
        return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()


def get_rank(user_id: int) -> tuple[int, int]:
    """Foydalanuvchining umumiy reytingdagi o'rni va jami ishtirokchilar soni."""
    with closing(_connect()) as conn:
        total = conn.execute("SELECT COUNT(*) FROM users WHERE quizzes > 0").fetchone()[0]
        row = conn.execute(
            """
            SELECT COUNT(*) + 1 FROM users
            WHERE quizzes > 0
              AND total_score > (SELECT total_score FROM users WHERE user_id = ?)
            """,
            (user_id,),
        ).fetchone()
    return row[0], total


def top_all_time(limit: int) -> list[sqlite3.Row]:
    with closing(_connect()) as conn:
        return conn.execute(
            """
            SELECT user_id, full_name, username, total_score AS score, correct, answered
            FROM users
            WHERE quizzes > 0
            ORDER BY total_score DESC, correct DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()


def top_weekly(limit: int) -> list[sqlite3.Row]:
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    with closing(_connect()) as conn:
        return conn.execute(
            """
            SELECT u.user_id, u.full_name, u.username,
                   SUM(r.score) AS score, SUM(r.correct) AS correct, SUM(r.total) AS answered
            FROM results r
            JOIN users u ON u.user_id = r.user_id
            WHERE r.finished_at >= ?
            GROUP BY r.user_id
            ORDER BY score DESC, correct DESC
            LIMIT ?
            """,
            (since, limit),
        ).fetchall()


# ─────────────────────────── Admin panel ───────────────────────────

def admin_stats() -> dict[str, int]:
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    with closing(_connect()) as conn:
        users, students = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(quizzes > 0), 0) FROM users"
        ).fetchone()
        active_week, tests = conn.execute(
            "SELECT COUNT(DISTINCT CASE WHEN finished_at >= ? THEN user_id END), COUNT(*) FROM results",
            (since,),
        ).fetchone()
        groups = conn.execute("SELECT COUNT(*) FROM groups").fetchone()[0]
    return {"users": users, "students": students, "active_week": active_week, "tests": tests, "groups": groups}


def count_students() -> int:
    with closing(_connect()) as conn:
        return conn.execute("SELECT COUNT(*) FROM users WHERE quizzes > 0").fetchone()[0]


def list_students(limit: int, offset: int) -> list[sqlite3.Row]:
    """Test ishlagan o'quvchilar — umumiy ball bo'yicha, oxirgi faollik vaqti bilan."""
    with closing(_connect()) as conn:
        return conn.execute(
            """
            SELECT u.user_id, u.full_name, u.username, u.total_score, u.quizzes, u.correct, u.answered,
                   (SELECT MAX(r.finished_at) FROM results r WHERE r.user_id = u.user_id) AS last_active
            FROM users u
            WHERE u.quizzes > 0
            ORDER BY u.total_score DESC, u.correct DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()


def student_tests(user_id: int) -> list[sqlite3.Row]:
    """O'quvchining har bir test turi bo'yicha eng yaxshi natijasi va urinishlar soni."""
    with closing(_connect()) as conn:
        return conn.execute(
            """
            SELECT mode, COUNT(*) AS attempts, MAX(correct) AS best_correct, MAX(total) AS total,
                   MAX(score) AS best_score, MAX(finished_at) AS last_at
            FROM results
            WHERE user_id = ?
            GROUP BY mode
            """,
            (user_id,),
        ).fetchall()


def recent_results(user_id: int, limit: int) -> list[sqlite3.Row]:
    with closing(_connect()) as conn:
        return conn.execute(
            "SELECT mode, score, correct, total, finished_at FROM results "
            "WHERE user_id = ? ORDER BY finished_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()


def ranking_for_test(mode: str, limit: int) -> list[sqlite3.Row]:
    """Bitta test bo'yicha reyting: har bir o'quvchining eng yaxshi natijasi."""
    with closing(_connect()) as conn:
        return conn.execute(
            """
            SELECT u.user_id, u.full_name, u.username, MAX(r.correct) AS best_correct,
                   MAX(r.total) AS total, MAX(r.score) AS best_score, COUNT(*) AS attempts
            FROM results r
            JOIN users u ON u.user_id = r.user_id
            WHERE r.mode = ?
            GROUP BY r.user_id
            ORDER BY best_correct DESC, best_score DESC
            LIMIT ?
            """,
            (mode, limit),
        ).fetchall()


def best_by_mode() -> list[sqlite3.Row]:
    """Excel eksporti uchun: (o'quvchi, test) juftligi bo'yicha eng yaxshi to'g'ri javoblar."""
    with closing(_connect()) as conn:
        return conn.execute(
            "SELECT user_id, mode, MAX(correct) AS best_correct, MAX(total) AS total "
            "FROM results WHERE mode IS NOT NULL GROUP BY user_id, mode"
        ).fetchall()


# ─────────────────────────── Guruhlar ───────────────────────────

# Aniqlik — guruhlar kattaligi har xil bo'lgani uchun adolatli ko'rsatkich; javobsiz guruhlar oxirida
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


def group_ranking(order: str) -> list[sqlite3.Row]:
    """Guruhlar reytingi: o'quvchilar, o'yinlar, ball va aniqlik (faqat shu guruhda ishlangan testlar)."""
    with closing(_connect()) as conn:
        return conn.execute(
            f"""
            SELECT * FROM (
                SELECT g.chat_id, g.title, g.games,
                       COUNT(DISTINCT r.user_id) AS students,
                       COALESCE(SUM(r.score), 0) AS total_score,
                       COALESCE(SUM(r.correct), 0) AS correct,
                       COALESCE(SUM(r.total), 0) AS answered,
                       MAX(r.finished_at) AS last_active
                FROM groups g
                LEFT JOIN results r ON r.chat_id = g.chat_id
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
    """Guruh ichidagi reyting: faqat shu guruhda to'plangan ballar."""
    with closing(_connect()) as conn:
        return conn.execute(
            """
            SELECT u.user_id, u.full_name, u.username, SUM(r.score) AS score, SUM(r.correct) AS correct,
                   SUM(r.total) AS answered, COUNT(*) AS games, MAX(r.finished_at) AS last_active
            FROM results r
            JOIN users u ON u.user_id = r.user_id
            WHERE r.chat_id = ?
            GROUP BY r.user_id
            ORDER BY score DESC, correct DESC
            LIMIT ?
            """,
            (chat_id, limit),
        ).fetchall()


def group_tests(chat_id: int) -> list[sqlite3.Row]:
    """Guruhning har bir test bo'yicha natijasi: o'quvchilar eng yaxshi natijalarining o'rtachasi."""
    with closing(_connect()) as conn:
        return conn.execute(
            """
            SELECT mode, COUNT(*) AS participants, AVG(best) AS avg_best, MAX(total) AS total
            FROM (
                SELECT mode, user_id, MAX(correct) AS best, MAX(total) AS total
                FROM results
                WHERE chat_id = ? AND mode IS NOT NULL
                GROUP BY mode, user_id
            )
            GROUP BY mode
            """,
            (chat_id,),
        ).fetchall()
