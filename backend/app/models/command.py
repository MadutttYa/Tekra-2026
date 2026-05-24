from typing import Literal

from pydantic import BaseModel

from models.room import RoomMode


class ActuatorState(BaseModel):
    master_relay: bool = False   # True = emergency cutoff for entire room
    lights:       bool = False
    ac:           bool = False


class RoomCommand(BaseModel):
    mode:        RoomMode | None = None
    actuators:   ActuatorState   = ActuatorState()
    ac_setpoint: float           = 24.0
