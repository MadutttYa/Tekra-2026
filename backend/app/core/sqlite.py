import aiosqlite

# SQLite database file — created automatically next to main.py
DB_PATH = "tekra.db"


async def init_db() -> None:
    """
    Create tables if they don't exist yet.
    Called once on app startup.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # Rooms — one row per physical room
        await db.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                room_id     TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                building_id TEXT NOT NULL,
                floor       INTEGER NOT NULL,
                mode        TEXT NOT NULL DEFAULT 'AUTO',
                status      TEXT NOT NULL DEFAULT 'DORMANT'
            )
        """)

        # Schedules — many rows per room (one per class slot)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id      TEXT NOT NULL,
                day_of_week  INTEGER NOT NULL,
                start_time   TEXT NOT NULL,
                end_time     TEXT NOT NULL,
                subject      TEXT NOT NULL,
                lecturer     TEXT,
                FOREIGN KEY (room_id) REFERENCES rooms(room_id)
            )
        """)

        # Notifications — anomaly alerts waiting for staff acknowledgement
        await db.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id      TEXT NOT NULL,
                type         TEXT NOT NULL,
                message      TEXT NOT NULL,
                severity     TEXT NOT NULL,
                acknowledged INTEGER NOT NULL DEFAULT 0,
                created_at   TEXT NOT NULL
            )
        """)

        await db.commit()


async def get_sqlite():
    """
    Dependency — yields an open SQLite connection for the duration of a request.
    Use with FastAPI's Depends():

        db: aiosqlite.Connection = Depends(get_sqlite)
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row   # lets us access columns by name: row["room_id"]
        yield db
