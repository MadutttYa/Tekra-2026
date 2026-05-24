import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from core.sqlite import get_sqlite
from models.room import Room, RoomCreate, RoomModeUpdate

router = APIRouter(
    prefix="/rooms",
    tags=["Rooms"],
)


@router.get("", response_model=list[Room])
async def list_rooms(db: aiosqlite.Connection = Depends(get_sqlite)):
    """Return all registered rooms."""
    cursor = await db.execute("SELECT * FROM rooms ORDER BY building_id, floor, room_id")
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


@router.post("", response_model=Room, status_code=201)
async def create_room(
    body: RoomCreate,
    db: aiosqlite.Connection = Depends(get_sqlite),
):
    """Register a new room."""
    try:
        await db.execute(
            """
            INSERT INTO rooms (room_id, name, building_id, floor)
            VALUES (?, ?, ?, ?)
            """,
            (body.room_id, body.name, body.building_id, body.floor),
        )
        await db.commit()
    except aiosqlite.IntegrityError:
        raise HTTPException(status_code=409, detail=f"Room '{body.room_id}' already exists")

    cursor = await db.execute("SELECT * FROM rooms WHERE room_id = ?", (body.room_id,))
    row = await cursor.fetchone()
    return dict(row)


@router.get("/{room_id}", response_model=Room)
async def get_room(
    room_id: str,
    db: aiosqlite.Connection = Depends(get_sqlite),
):
    """Get details for a single room."""
    cursor = await db.execute("SELECT * FROM rooms WHERE room_id = ?", (room_id,))
    row = await cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Room '{room_id}' not found")

    return dict(row)


@router.patch("/{room_id}/mode", response_model=Room)
async def update_mode(
    room_id: str,
    body: RoomModeUpdate,
    db: aiosqlite.Connection = Depends(get_sqlite),
):
    """
    Switch a room mode:
    AUTO     → system follows the class schedule
    OVERRIDE → staff controls everything manually
    HOLIDAY  → everything off, schedule ignored (public/university holiday)
    """
    cursor = await db.execute("SELECT * FROM rooms WHERE room_id = ?", (room_id,))
    row = await cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Room '{room_id}' not found")

    # When switching to HOLIDAY, immediately reflect it in status too
    # Other statuses (ACTIVE, DORMANT, OVERRIDED) are set by the automation logic later
    new_status = "HOLIDAY" if body.mode == "HOLIDAY" else dict(row)["status"]

    await db.execute(
        "UPDATE rooms SET mode = ?, status = ? WHERE room_id = ?",
        (body.mode, new_status, room_id),
    )
    await db.commit()

    cursor = await db.execute("SELECT * FROM rooms WHERE room_id = ?", (room_id,))
    row = await cursor.fetchone()
    return dict(row)
