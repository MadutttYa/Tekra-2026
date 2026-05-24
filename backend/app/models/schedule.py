from pydantic import BaseModel, field_validator


class ScheduleCreate(BaseModel):
    """Body for POST /rooms/{room_id}/schedules"""
    day_of_week: int    # 0 = Monday, 6 = Sunday
    start_time:  str    # "08:00"
    end_time:    str    # "10:00"
    subject:     str
    lecturer:    str | None = None

    @field_validator("day_of_week")
    @classmethod
    def valid_day(cls, v: int) -> int:
        if not (0 <= v <= 6):
            raise ValueError("day_of_week must be 0 (Monday) to 6 (Sunday)")
        return v


class Schedule(BaseModel):
    """Full schedule object returned by the API"""
    id:          int
    room_id:     str
    day_of_week: int
    start_time:  str
    end_time:    str
    subject:     str
    lecturer:    str | None
