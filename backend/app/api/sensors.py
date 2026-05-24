import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from core.database import get_db_pool, get_latest_reading, get_room_history

router = APIRouter(
    prefix="/rooms",
    tags=["Sensors"],
)


@router.get("/{room_id}/latest")
async def latest_reading(
    room_id: str,
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Return the most recent sensor reading for a room."""
    row = await get_latest_reading(pool, room_id)

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for room '{room_id}'",
        )

    return row


@router.get("/{room_id}/history")
async def room_history(
    room_id: str,
    hours: int = 24,
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """
    Return sensor readings for a room over the last N hours.
    Default is 24 hours. Use ?hours=1 to get the last hour only.
    """
    rows = await get_room_history(pool, room_id, hours)

    return {
        "room_id": room_id,
        "hours": hours,
        "count": len(rows),
        "data": rows,
    }
