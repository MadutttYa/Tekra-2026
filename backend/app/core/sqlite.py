import aiosqlite

DB_PATH = "tekra.db"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
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

        await db.execute("""
            CREATE TABLE IF NOT EXISTS holidays (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT NOT NULL UNIQUE,
                name        TEXT NOT NULL,
                created_at  TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id     TEXT NOT NULL,
                date        TEXT NOT NULL,
                start_time  TEXT NOT NULL,
                end_time    TEXT NOT NULL,
                requester   TEXT NOT NULL,
                purpose     TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'PENDING',
                created_at  TEXT NOT NULL,
                FOREIGN KEY (room_id) REFERENCES rooms(room_id)
            )
        """)

        await db.commit()


async def get_sqlite():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db
