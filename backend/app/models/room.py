from typing import Literal

from pydantic import BaseModel

# Mode  = who controls the room
# AUTO    → system follows the class schedule
# OVERRIDE → staff controls manually per component
# HOLIDAY  → everything off, schedule ignored, system dormant
RoomMode = Literal["AUTO", "OVERRIDE", "HOLIDAY"]

# Status = what state the room is in right now (derived from mode + schedule)
# ACTIVE   → AUTO mode, class is currently in session
# DORMANT  → AUTO mode, no class right now
# OVERRIDED → staff is in manual OVERRIDE
# HOLIDAY  → HOLIDAY mode, public/university holiday
RoomStatus = Literal["ACTIVE", "OVERRIDED", "DORMANT", "HOLIDAY"]


class RoomCreate(BaseModel):
    """Body for POST /rooms"""
    room_id:     str
    name:        str
    building_id: str
    floor:       int


class RoomModeUpdate(BaseModel):
    """Body for PATCH /rooms/{room_id}/mode"""
    mode: RoomMode


class Room(BaseModel):
    """Full room object returned by the API"""
    room_id:     str
    name:        str
    building_id: str
    floor:       int
    mode:        RoomMode
    status:      RoomStatus
