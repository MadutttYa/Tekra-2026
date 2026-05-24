import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from core.sqlite import get_sqlite
from models.schedule import Schedule, ScheduleCreate

router = APIRouter(
    prefix="/rooms/{room_id}/schedules",
    tags=["Schedules"],
)


async def _room_exists(room_id: str, db: aiosqlite.Connection) -> None:
    """Raise 404 if the room doesn't exist."""
    cursor = await db.execute("SELECT room_id FROM rooms WHERE room_id = ?", (room_id,))
    if await cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail=f"Room '{room_id}' not found")


@router.get("", response_model=list[Schedule])
async def list_schedules(
    room_id: str,
    db: aiosqlite.Connection = Depends(get_sqlite),
):
    """List all class schedules for a room, ordered by day and start time."""
    await _room_exists(room_id, db)

    cursor = await db.execute(
        """
        SELECT * FROM schedules
        WHERE room_id = ?
        ORDER BY day_of_week, start_time
        """,
        (room_id,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


@router.post("", response_model=Schedule, status_code=201)
async def add_schedule(
    room_id: str,
    body: ScheduleCreate,
    db: aiosqlite.Connection = Depends(get_sqlite),
):
    """Add a class schedule slot to a room."""
    await _room_exists(room_id, db)

    cursor = await db.execute(
        """
        INSERT INTO schedules (room_id, day_of_week, start_time, end_time, subject, lecturer)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (room_id, body.day_of_week, body.start_time, body.end_time, body.subject, body.lecturer),
    )
    await db.commit()

    cursor = await db.execute("SELECT * FROM schedules WHERE id = ?", (cursor.lastrowid,))
    row = await cursor.fetchone()
    return dict(row)


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(
    room_id: str,
    schedule_id: int,
    db: aiosqlite.Connection = Depends(get_sqlite),
):
    """Remove a schedule slot from a room."""
    await _room_exists(room_id, db)

    cursor = await db.execute(
        "SELECT id FROM schedules WHERE id = ? AND room_id = ?",
        (schedule_id, room_id),
    )
    if await cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail=f"Schedule '{schedule_id}' not found")

    await db.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    await db.commit()
