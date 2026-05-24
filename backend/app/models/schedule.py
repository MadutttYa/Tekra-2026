from typing import Literal

from pydantic import BaseModel, field_validator


class ScheduleCreate(BaseModel):
    day_of_week: int  # 0 = Monday, 6 = Sunday
    start_time:  str  # "HH:MM"
    end_time:    str  # "HH:MM"
    subject:     str
    lecturer:    str | None = None

    @field_validator("day_of_week")
    @classmethod
    def valid_day(cls, v: int) -> int:
        if not (0 <= v <= 6):
            raise ValueError("day_of_week must be 0 (Monday) to 6 (Sunday)")
        return v


class Schedule(BaseModel):
    id:          int
    room_id:     str
    day_of_week: int
    start_time:  str
    end_time:    str
    subject:     str
    lecturer:    str | None


class HolidayCreate(BaseModel):
    date: str  # "YYYY-MM-DD"
    name: str


class Holiday(BaseModel):
    id:         int
    date:       str
    name:       str
    created_at: str


BookingStatus = Literal["PENDING", "APPROVED", "REJECTED"]


class BookingCreate(BaseModel):
    date:       str  # "YYYY-MM-DD"
    start_time: str  # "HH:MM"
    end_time:   str  # "HH:MM"
    requester:  str
    purpose:    str


class BookingStatusUpdate(BaseModel):
    status: BookingStatus


class Booking(BaseModel):
    id:         int
    room_id:    str
    date:       str
    start_time: str
    end_time:   str
    requester:  str
    purpose:    str
    status:     BookingStatus
    created_at: str
