import sqlite3
from datetime import datetime, timedelta, timezone

DB_PATH = "gut_clock.db"


def init_db():
    """Инициализация базы данных: только необходимые поля, работаем строго по UTC"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stool_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            username TEXT,
            first_name TEXT,
            stool_type INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


# Автоматически создаем базу и таблицу при импорте
init_db()


def save_event(
    telegram_id: int, username: str, first_name: str, stool_type: int
) -> dict:
    """Сохраняет событие в базу с фиксацией времени по UTC"""
    now_utc = datetime.now(timezone.utc).isoformat()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO stool_events (telegram_id, username, first_name, stool_type, created_at) VALUES (?, ?, ?, ?, ?)",
            (telegram_id, username, first_name, stool_type, now_utc),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

    return {
        "telegram_id": telegram_id,
        "username": username,
        "stool_type": stool_type,
        "created_at": now_utc,
    }


def _get_stats_by_raw_date(telegram_id: int, date_limit_iso: str = None) -> dict:
    """Вспомогательная функция для подсчета количества записей по типам"""
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
    """Высчитывает статистику на основе системного времени UTC"""
    now_utc = datetime.now(timezone.utc)

    # Полночь текущих суток строго по UTC
    today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    # Временные лимиты для недели и месяца
    weekly_limit = (now_utc - timedelta(days=7)).isoformat()
    monthly_limit = (now_utc - timedelta(days=30)).isoformat()

    return {
        "today": _get_stats_by_raw_date(telegram_id, today_start),
        "weekly": _get_stats_by_raw_date(telegram_id, weekly_limit),
        "monthly": _get_stats_by_raw_date(telegram_id, monthly_limit),
        "total": _get_stats_by_raw_date(telegram_id, None),
    }


def clear_history(telegram_id: int):
    """Полное удаление истории записей пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM stool_events WHERE telegram_id = ?", (telegram_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
