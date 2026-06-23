import os
import sqlite3
from datetime import datetime, timedelta, timezone

OS_DATA_DIR = "data"
os.makedirs(OS_DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(OS_DATA_DIR, "gut_clock.db")

# Екатеринбург (UTC+5)
LOCAL_TZ = timezone(timedelta(hours=5))


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stool_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            username TEXT,
            first_name TEXT,
            stool_type INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


def save_event(
    telegram_id: int, username: str, first_name: str, stool_type: int
) -> dict:
    # Записываем местное время (Екб)
    now_local = datetime.now(LOCAL_TZ).isoformat()

    conn = sqlite3.connect(DB_PATH)
    with conn:  # Менеджер контекста автоматически сделает commit() при успехе
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO stool_events (telegram_id, username, first_name, "
            "stool_type, created_at) VALUES (?, ?, ?, ?, ?)",
            (telegram_id, username, first_name, stool_type, now_local),
        )
    conn.close()

    return {
        "telegram_id": telegram_id,
        "username": username,
        "stool_type": stool_type,
        "created_at": now_local,
    }


def _get_stats_by_raw_date(telegram_id: int, date_limit_iso: str | None = None) -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = "SELECT stool_type, COUNT(*) FROM stool_events WHERE telegram_id = ?"
    params = [telegram_id]

    if date_limit_iso is not None:
        query += " AND created_at >= ?"
        params.append(date_limit_iso)

    query += " GROUP BY stool_type"

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    result_types = {1: 0, 2: 0, 3: 0}
    total_count = 0

    for stool_type, count in rows:
        if stool_type in result_types:
            result_types[stool_type] = count
            total_count += count

    return {"count": total_count, "types": result_types}


def calculate_stats(telegram_id: int) -> dict:
    # Получаем объект datetime для Екб (без isoformat на этом этапе)
    now_local = datetime.now(LOCAL_TZ)

    today_start = now_local.replace(
        hour=0, minute=0, second=0, microsecond=0
    ).isoformat()

    weekly_limit = (now_local - timedelta(days=7)).isoformat()
    monthly_limit = (now_local - timedelta(days=30)).isoformat()

    return {
        "today": _get_stats_by_raw_date(telegram_id, today_start),
        "weekly": _get_stats_by_raw_date(telegram_id, weekly_limit),
        "monthly": _get_stats_by_raw_date(telegram_id, monthly_limit),
        "total": _get_stats_by_raw_date(telegram_id, None),
    }


def clear_history(telegram_id: int):
    conn = sqlite3.connect(DB_PATH)
    with conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM stool_events WHERE telegram_id = ?", (telegram_id,))
    conn.close()


def get_all_events(telegram_id: int) -> list:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT stool_type, created_at FROM stool_events WHERE telegram_id = ? "
        "ORDER BY created_at DESC",
        (telegram_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows
