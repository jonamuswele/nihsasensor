from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import get_db, Base, engine
from app import crud, schemas

# ── App init ──────────────────────────────────────────────────────────────────
app = FastAPI(
    title="River Monitor API",
    description="Backend for multi-sensor river water-level monitoring.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Create tables on startup
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════════════════════════════════════

# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "time": datetime.utcnow()}


# ── Ingest ─────────────────────────────────────────────────────────────────────
@app.post("/api/water-level", tags=["Ingest"])
def receive_water_level(data: schemas.WaterLevelIn, db: Session = Depends(get_db)):
    """Receive water level data from Raspberry Pi."""
    try:
        recorded_at = datetime.strptime(data.recorded_at, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        recorded_at = datetime.utcnow()

    station = crud.get_or_create_station(db, data.node_id)
    station.last_seen = datetime.utcnow()
    db.commit()

    crud.create_reading(db, station.id, data.level_cm, recorded_at)

    return {
        "message": "Reading saved",
        "node_id": data.node_id,
        "level_cm": data.level_cm,
        "recorded_at": recorded_at.strftime("%Y-%m-%d %H:%M:%S"),
    }


# ── Stations ───────────────────────────────────────────────────────────────────
@app.get("/api/stations", tags=["Stations"], response_model=list[schemas.StationOut])
def list_stations(db: Session = Depends(get_db)):
    return crud.get_all_stations(db)


@app.get("/api/stations/{node_id}", tags=["Stations"], response_model=schemas.StationOut)
def get_station(node_id: str, db: Session = Depends(get_db)):
    station = crud.get_station(db, node_id)
    if not station:
        raise HTTPException(404, f"Station '{node_id}' not found")
    return station


@app.put("/api/stations/{node_id}", tags=["Stations"])
def update_station_location(node_id: str, data: schemas.StationUpdate, db: Session = Depends(get_db)):
    """Update the location of a station."""
    station = crud.update_station_location(db, node_id, data.location)
    if not station:
        raise HTTPException(404, f"Station '{node_id}' not found")
    return {
        "message": "Station location updated",
        "node_id": node_id,
        "location": station.location
    }


# ── Readings ──────────────────────────────────────────────────────────────────
@app.get("/api/readings/latest", tags=["Readings"])
def get_latest_all(db: Session = Depends(get_db)):
    """Latest reading from EVERY station."""
    return crud.get_latest_readings(db)


@app.get("/api/readings/{node_id}", tags=["Readings"])
def get_readings_for_station(
        node_id: str,
        limit: int = Query(100, ge=1, le=5000),
        db: Session = Depends(get_db),
):
    """Full reading history for one station."""
    station, readings = crud.get_readings_for_station(db, node_id, limit)
    if not station:
        raise HTTPException(404, f"Station '{node_id}' not found")

    return [
        {
            "id": r.id,
            "node_id": station.node_id,
            "level_cm": r.level_cm,
            "recorded_at": r.recorded_at
        }
        for r in readings
    ]


@app.get("/api/readings", tags=["Readings"])
def get_all_readings(
        node_id: Optional[str] = Query(None),
        limit: int = Query(500, ge=1, le=5000),
        db: Session = Depends(get_db),
):
    """All readings, optionally filtered by node_id."""
    rows = crud.get_all_readings(db, node_id, limit)

    result = []
    for r in rows:
        result.append({
            "id": r.id,
            "node_id": r.station.node_id,
            "level_cm": r.level_cm,
            "recorded_at": r.recorded_at,
            "location": r.station.location
        })
    return result


# ── Stats ─────────────────────────────────────────────────────────────────────
@app.get("/api/stats/{node_id}", tags=["Analytics"])
def get_stats(node_id: str, db: Session = Depends(get_db)):
    """Summary statistics for a station."""
    stats = crud.get_station_stats(db, node_id)
    if stats is None:
        raise HTTPException(404, f"Station '{node_id}' not found")
    return stats