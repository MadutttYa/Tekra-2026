import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from core.sqlite import get_sqlite
from models.room import Room, RoomCreate, RoomModeUpdate
from services.schedule_context import get_room_context

router = APIRouter(prefix="/rooms", tags=["Rooms"])


@router.get("", response_model=list[Room])
async def list_rooms(db: aiosqlite.Connection = Depends(get_sqlite)):
    cursor = await db.execute("SELECT * FROM rooms ORDER BY building_id, floor, room_id")
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


@router.post("", response_model=Room, status_code=201)
async def create_room(body: RoomCreate, db: aiosqlite.Connection = Depends(get_sqlite)):
    try:
        await db.execute(
            "INSERT INTO rooms (room_id, name, building_id, floor) VALUES (?, ?, ?, ?)",
            (body.room_id, body.name, body.building_id, body.floor),
        )
        await db.commit()
    except aiosqlite.IntegrityError:
        raise HTTPException(status_code=409, detail=f"Room '{body.room_id}' already exists")

    cursor = await db.execute("SELECT * FROM rooms WHERE room_id = ?", (body.room_id,))
    return dict(await cursor.fetchone())


@router.get("/{room_id}", response_model=Room)
async def get_room(room_id: str, db: aiosqlite.Connection = Depends(get_sqlite)):
    cursor = await db.execute("SELECT * FROM rooms WHERE room_id = ?", (room_id,))
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Room '{room_id}' not found")
    return dict(row)


@router.get("/{room_id}/context")
async def room_context(room_id: str, db: aiosqlite.Connection = Depends(get_sqlite)):
    cursor = await db.execute("SELECT room_id FROM rooms WHERE room_id = ?", (room_id,))
    if await cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail=f"Room '{room_id}' not found")
    return await get_room_context(room_id)


@router.patch("/{room_id}/mode", response_model=Room)
async def update_mode(
    room_id: str,
    body: RoomModeUpdate,
    db: aiosqlite.Connection = Depends(get_sqlite),
):
    cursor = await db.execute("SELECT * FROM rooms WHERE room_id = ?", (room_id,))
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Room '{room_id}' not found")

    new_status = "HOLIDAY" if body.mode == "HOLIDAY" else dict(row)["status"]

    await db.execute(
        "UPDATE rooms SET mode = ?, status = ? WHERE room_id = ?",
        (body.mode, new_status, room_id),
    )
    await db.commit()

    cursor = await db.execute("SELECT * FROM rooms WHERE room_id = ?", (room_id,))
    return dict(await cursor.fetchone())
