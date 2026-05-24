from datetime import datetime

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from core.sqlite import get_sqlite
from models.schedule import Booking, BookingCreate, BookingStatusUpdate

router = APIRouter(tags=["Bookings"])


async def _room_exists(room_id: str, db: aiosqlite.Connection) -> None:
    cursor = await db.execute("SELECT room_id FROM rooms WHERE room_id = ?", (room_id,))
    if await cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail=f"Room '{room_id}' not found")


@router.get("/rooms/{room_id}/bookings", response_model=list[Booking])
async def list_bookings(
    room_id: str,
    status: str | None = None,
    db: aiosqlite.Connection = Depends(get_sqlite),
):
    """List bookings for a room. Optional ?status=PENDING|APPROVED|REJECTED filter."""
    await _room_exists(room_id, db)
    if status:
        cursor = await db.execute(
            "SELECT * FROM bookings WHERE room_id = ? AND status = ? ORDER BY date, start_time",
            (room_id, status.upper()),
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM bookings WHERE room_id = ? ORDER BY date DESC, start_time",
            (room_id,),
        )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


@router.get("/bookings", response_model=list[Booking])
async def list_all_bookings(
    status: str | None = None,
    db: aiosqlite.Connection = Depends(get_sqlite),
):
    """List all bookings across all rooms (for admin view)."""
    if status:
        cursor = await db.execute(
            "SELECT * FROM bookings WHERE status = ? ORDER BY date, start_time",
            (status.upper(),),
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM bookings ORDER BY date DESC, start_time"
        )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


@router.post("/rooms/{room_id}/bookings", response_model=Booking, status_code=201)
async def create_booking(
    room_id: str,
    body: BookingCreate,
    db: aiosqlite.Connection = Depends(get_sqlite),
):
    """Submit a room booking request (starts as PENDING, needs staff approval)."""
    await _room_exists(room_id, db)

    cursor = await db.execute(
        """INSERT INTO bookings (room_id, date, start_time, end_time, requester, purpose, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?)""",
        (room_id, body.date, body.start_time, body.end_time, body.requester, body.purpose,
         datetime.utcnow().isoformat()),
    )
    await db.commit()

    cursor = await db.execute("SELECT * FROM bookings WHERE id = ?", (cursor.lastrowid,))
    return dict(await cursor.fetchone())


@router.patch("/bookings/{booking_id}/status", response_model=Booking)
async def update_booking_status(
    booking_id: int,
    body: BookingStatusUpdate,
    db: aiosqlite.Connection = Depends(get_sqlite),
):
    """Approve or reject a booking request."""
    cursor = await db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    await db.execute(
        "UPDATE bookings SET status = ? WHERE id = ?",
        (body.status, booking_id),
    )
    await db.commit()

    cursor = await db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
    return dict(await cursor.fetchone())


@router.delete("/bookings/{booking_id}", status_code=204)
async def delete_booking(
    booking_id: int,
    db: aiosqlite.Connection = Depends(get_sqlite),
):
    cursor = await db.execute("SELECT id FROM bookings WHERE id = ?", (booking_id,))
    if await cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    await db.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    await db.commit()
