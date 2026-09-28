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
    finished_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mistakes (
    user_id  INTEGER NOT NULL,
    word_id  INTEGER NOT NULL,
    count    INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id, word_id)
);

CREATE INDEX IF NOT EXISTS idx_results_time ON results (finished_at);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(_connect()) as conn, conn:
        conn.executescript(SCHEMA)


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


def save_result(user_id: int, score: int, correct: int, total: int, best_streak: int) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO results (user_id, score, correct, total, finished_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, score, correct, total, _now()),
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
