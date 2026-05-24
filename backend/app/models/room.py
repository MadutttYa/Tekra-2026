from typing import Literal

from pydantic import BaseModel

RoomMode   = Literal["AUTO", "OVERRIDE", "HOLIDAY"]
RoomStatus = Literal["ACTIVE", "OVERRIDED", "DORMANT", "HOLIDAY"]


class RoomCreate(BaseModel):
    room_id:     str
    name:        str
    building_id: str
    floor:       int


class RoomModeUpdate(BaseModel):
    mode: RoomMode


class Room(BaseModel):
    room_id:     str
    name:        str
    building_id: str
    floor:       int
    mode:        RoomMode
    status:      RoomStatus
