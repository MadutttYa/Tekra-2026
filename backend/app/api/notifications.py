import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from core.sqlite import get_sqlite

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


@router.get("")
async def list_notifications(
    room_id: str | None = None,
    acknowledged: bool = False,
    db: aiosqlite.Connection = Depends(get_sqlite),
):
    """
    List notifications.
    - By default returns only unacknowledged alerts.
    - Filter by room with ?room_id=A1.01
    - Show acknowledged ones with ?acknowledged=true
    """
    if room_id:
        cursor = await db.execute(
            """
            SELECT * FROM notifications
            WHERE room_id = ? AND acknowledged = ?
            ORDER BY created_at DESC
            """,
            (room_id, 1 if acknowledged else 0),
        )
    else:
        cursor = await db.execute(
            """
            SELECT * FROM notifications
            WHERE acknowledged = ?
            ORDER BY created_at DESC
            """,
            (1 if acknowledged else 0,),
        )

    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


@router.patch("/{notification_id}/acknowledge")
async def acknowledge(
    notification_id: int,
    db: aiosqlite.Connection = Depends(get_sqlite),
):
    """Mark a notification as acknowledged (staff has seen and handled it)."""
    cursor = await db.execute(
        "SELECT id FROM notifications WHERE id = ?",
        (notification_id,),
    )
    if await cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail=f"Notification {notification_id} not found")

    await db.execute(
        "UPDATE notifications SET acknowledged = 1 WHERE id = ?",
        (notification_id,),
    )
    await db.commit()
    return {"detail": f"Notification {notification_id} acknowledged"}
