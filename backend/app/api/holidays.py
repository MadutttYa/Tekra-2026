from datetime import datetime

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from core.sqlite import get_sqlite
from models.schedule import Holiday, HolidayCreate

router = APIRouter(prefix="/holidays", tags=["Holidays"])


@router.get("", response_model=list[Holiday])
async def list_holidays(db: aiosqlite.Connection = Depends(get_sqlite)):
    cursor = await db.execute("SELECT * FROM holidays ORDER BY date")
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


@router.post("", response_model=Holiday, status_code=201)
async def create_holiday(
    body: HolidayCreate,
    db: aiosqlite.Connection = Depends(get_sqlite),
):
    try:
        cursor = await db.execute(
            "INSERT INTO holidays (date, name, created_at) VALUES (?, ?, ?)",
            (body.date, body.name, datetime.utcnow().isoformat()),
        )
        await db.commit()
    except aiosqlite.IntegrityError:
        raise HTTPException(status_code=409, detail=f"Holiday on '{body.date}' already exists")

    cursor = await db.execute("SELECT * FROM holidays WHERE id = ?", (cursor.lastrowid,))
    return dict(await cursor.fetchone())


@router.delete("/{holiday_id}", status_code=204)
async def delete_holiday(
    holiday_id: int,
    db: aiosqlite.Connection = Depends(get_sqlite),
):
    cursor = await db.execute("SELECT id FROM holidays WHERE id = ?", (holiday_id,))
    if await cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Holiday not found")
    await db.execute("DELETE FROM holidays WHERE id = ?", (holiday_id,))
    await db.commit()
