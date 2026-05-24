from datetime import datetime, timedelta

import asyncpg
from fastapi import Request


# -----------------------------------------------------------------------------
# Dependency — used with FastAPI's Depends()
# Retrieves the db pool that was stored in app.state during startup
# -----------------------------------------------------------------------------
def get_db_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.db_pool


# -----------------------------------------------------------------------------
# Queries
# -----------------------------------------------------------------------------
async def get_latest_reading(pool: asyncpg.Pool, room_id: str) -> dict | None:
    """Get the single most recent sensor reading for a room."""
    row = await pool.fetchrow(
        """
        SELECT *
        FROM room_telemetry
        WHERE room_id = $1
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        room_id,
    )
    return dict(row) if row else None


async def get_room_history(
    pool: asyncpg.Pool,
    room_id: str,
    hours: int = 24,
) -> list[dict]:
    """Get all sensor readings for a room within the last N hours."""
    since = datetime.utcnow() - timedelta(hours=hours)  # naive UTC — what QuestDB expects

    rows = await pool.fetch(
        """
        SELECT *
        FROM room_telemetry
        WHERE room_id = $1
          AND timestamp > $2
        ORDER BY timestamp DESC
        """,
        room_id,
        since,
    )
    return [dict(row) for row in rows]
