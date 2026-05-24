from typing import Literal

from pydantic import BaseModel

from models.room import RoomMode


class ActuatorState(BaseModel):
    master_relay: bool = False   # True = emergency cutoff for entire room
    lights:       bool = False
    ac:           bool = False
    outlets:      bool = False


class RoomCommand(BaseModel):
    """
    Body for POST /rooms/{room_id}/command
    Mirrors payload_server_to_esp.json
    """
    mode:        RoomMode
    actuators:   ActuatorState
    ac_setpoint: float = 24.0   # Target °C — adjusts setpoint, doesn't just on/off the AC
