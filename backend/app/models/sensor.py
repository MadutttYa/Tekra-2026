from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class EnvironmentData(BaseModel):
    temperature: float
    humidity: float
    heat_index: float
    air_quality: float
    lux: float
    comfort_score: float


class PowerData(BaseModel):
    voltage: float
    current: float
    power: float
    energy: float
    frequency: float
    pf: float


class OccupancyData(BaseModel):
    pir_triggered: bool
    estimated_people: int
    activity_score: float
    state: Literal["EMPTY", "OCCUPIED", "TRANSITIONING"]


class SensorPayload(BaseModel):
    device_id: str
    building_id: str
    floor: int
    room_id: str
    timestamp: datetime
    environment: EnvironmentData
    power: PowerData
    occupancy: OccupancyData
