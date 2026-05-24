from datetime import datetime, timedelta

import asyncpg
from fastapi import Request


def get_db_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.db_pool


async def get_latest_reading(pool: asyncpg.Pool, room_id: str) -> dict | None:
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
    since = datetime.utcnow() - timedelta(hours=hours)

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
