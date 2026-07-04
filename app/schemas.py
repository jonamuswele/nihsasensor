from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ── Request Schemas ───────────────────────────────────────────────────────────

class WaterLevelIn(BaseModel):
    """Payload sent by each Raspberry Pi."""
    node_id: str
    level_cm: float
    recorded_at: str  # ISO format timestamp from Pi


class StationUpdate(BaseModel):
    """Update station location."""
    location: str


# ── Response Schemas ──────────────────────────────────────────────────────────

class StationOut(BaseModel):
    id: int
    node_id: str
    location: Optional[str]
    created_at: datetime
    last_seen: Optional[datetime]

    class Config:
        from_attributes = True


class ReadingOut(BaseModel):
    id: int
    station_id: int
    node_id: str
    level_cm: float
    recorded_at: datetime

    class Config:
        from_attributes = True


class ReadingSimpleOut(BaseModel):
    id: int
    node_id: str
    level_cm: float
    recorded_at: datetime
    location: Optional[str]

    class Config:
        from_attributes = True