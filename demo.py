import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timedelta, timezone


def ingest(db, event):
    with db:
        result = db.execute(
            """INSERT INTO events VALUES (?, ?, ?, ?)
               ON CONFLICT(event_id) DO NOTHING""",
            event,
        )
        if result.rowcount:
            return "сохранено"
        stored = db.execute(
            "SELECT * FROM events WHERE event_id = ?", (event[0],)
        ).fetchone()
        if stored != event:
            raise ValueError(f"Конфликт содержимого для ID {event[0]}")
        return "повтор"


def daily_report(db, day):
    start = datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return db.execute(
        """SELECT COUNT(*), ROUND(AVG(temperature), 2)
           FROM events WHERE event_time >= ? AND event_time < ?""",
        (start.isoformat(), end.isoformat()),
    ).fetchone()


def latest_reading(db, sensor_id):
    return db.execute(
        """SELECT event_id, temperature FROM events WHERE sensor_id = ?
           ORDER BY event_time DESC, event_id DESC LIMIT 1""",
        (sensor_id,),
    ).fetchone()


def run(db):
    db.execute("""CREATE TABLE IF NOT EXISTS events (
        event_id TEXT PRIMARY KEY NOT NULL,
        sensor_id TEXT NOT NULL,
        event_time TEXT NOT NULL,
        temperature REAL NOT NULL
    )""")
    day = "2026-11-15"
    first = ("demo-1", "sensor-1", day + "T22:00:00+00:00", 20)
    next_day = ("demo-2", "sensor-1", "2026-11-16T00:00:00+00:00", 30)
    late = ("demo-3", "sensor-1", day + "T18:00:00+00:00", 24)

    print("Первое событие:", ingest(db, first))
    print("Следующий день:", ingest(db, next_day))
    assert ingest(db, first) == "повтор"
    print("Отчёт до поздней доставки:", daily_report(db, day))
    print("Позднее событие:", ingest(db, late))
    print("Отчёт после поздней доставки:", daily_report(db, day))
    print("Последнее показание:", latest_reading(db, "sensor-1"))
    assert daily_report(db, day) == (2, 22.0)
    assert latest_reading(db, "sensor-1") == ("demo-2", 30.0)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else ":memory:"
    with closing(sqlite3.connect(path)) as database:
        run(database)
