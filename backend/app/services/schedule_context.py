from datetime import datetime, timedelta

import aiosqlite

from core.sqlite import DB_PATH

BUFFER_MINUTES = 5


async def get_room_context(room_id: str) -> dict:
    now        = datetime.utcnow() + timedelta(hours=7)  # WIB
    today_str  = now.strftime("%Y-%m-%d")
    today_dow  = now.weekday()                            # 0 = Monday
    cur_time   = now.strftime("%H:%M")
    buf_time   = (now - timedelta(minutes=BUFFER_MINUTES)).strftime("%H:%M")

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        c = await db.execute(
            "SELECT * FROM holidays WHERE date = ?", (today_str,)
        )
        holiday = await c.fetchone()

        c = await db.execute(
            """SELECT * FROM schedules
               WHERE room_id = ? AND day_of_week = ?
               AND start_time <= ? AND end_time > ?
               ORDER BY start_time LIMIT 1""",
            (room_id, today_dow, cur_time, cur_time),
        )
        active_sched = await c.fetchone()

        c = await db.execute(
            """SELECT * FROM bookings
               WHERE room_id = ? AND date = ? AND status = 'APPROVED'
               AND start_time <= ? AND end_time > ?
               ORDER BY start_time LIMIT 1""",
            (room_id, today_str, cur_time, cur_time),
        )
        active_booking = await c.fetchone()

        c = await db.execute(
            """SELECT * FROM schedules
               WHERE room_id = ? AND day_of_week = ?
               AND end_time > ? AND end_time <= ?
               ORDER BY end_time DESC LIMIT 1""",
            (room_id, today_dow, buf_time, cur_time),
        )
        ended_sched = await c.fetchone()

        c = await db.execute(
            """SELECT * FROM bookings
               WHERE room_id = ? AND date = ? AND status = 'APPROVED'
               AND end_time > ? AND end_time <= ?
               ORDER BY end_time DESC LIMIT 1""",
            (room_id, today_str, buf_time, cur_time),
        )
        ended_booking = await c.fetchone()

    as_d      = dict(active_sched)   if active_sched   else None
    ab_d      = dict(active_booking) if active_booking else None
    is_active = (as_d is not None) or (ab_d is not None)

    label = None
    if as_d:
        label = f"{as_d['start_time']}-{as_d['end_time']} · {as_d['subject']}"
    elif ab_d:
        label = f"{ab_d['start_time']}-{ab_d['end_time']} · {ab_d['purpose']}"

    return {
        "is_holiday":      holiday is not None,
        "holiday_name":    dict(holiday)["name"] if holiday else None,
        "active_schedule": as_d,
        "active_booking":  ab_d,
        "in_buffer":       (ended_sched is not None or ended_booking is not None) and not is_active,
        "is_active":       is_active,
        "window_label":    label,
    }
