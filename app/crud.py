from datetime import datetime
from sqlalchemy.orm import Session

from app.models import Station, Reading


def get_or_create_station(db: Session, node_id: str) -> Station:
    """Get existing station or create new one with default location 'NIHSA'."""
    station = db.query(Station).filter(Station.node_id == node_id).first()
    if not station:
        station = Station(
            node_id=node_id,
            location="NIHSA",
            created_at=datetime.utcnow(),
        )
        db.add(station)
        db.flush()
    return station


def get_station(db: Session, node_id: str):
    return db.query(Station).filter(Station.node_id == node_id).first()


def get_all_stations(db: Session):
    return db.query(Station).order_by(Station.node_id).all()


def update_station_location(db: Session, node_id: str, location: str):
    station = get_station(db, node_id)
    if station:
        station.location = location
        db.commit()
        db.refresh(station)
    return station


def create_reading(db: Session, station_id: int, level_cm: float, recorded_at: datetime):
    reading = Reading(
        station_id=station_id,
        level_cm=level_cm,
        recorded_at=recorded_at,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


def get_latest_readings(db: Session):
    stations = get_all_stations(db)
    result = []
    for s in stations:
        r = (
            db.query(Reading)
            .filter(Reading.station_id == s.id)
            .order_by(Reading.recorded_at.desc())
            .first()
        )
        if r:
            result.append({
                "node_id": s.node_id,
                "level_cm": r.level_cm,
                "recorded_at": r.recorded_at,
                "location": s.location
            })
    return result


def get_readings_for_station(db: Session, node_id: str, limit: int = 100):
    station = get_station(db, node_id)
    if not station:
        return None, None

    readings = (
        db.query(Reading)
        .filter(Reading.station_id == station.id)
        .order_by(Reading.recorded_at.desc())
        .limit(limit)
        .all()
    )
    return station, readings


def get_all_readings(db: Session, node_id: str = None, limit: int = 500):
    q = db.query(Reading).order_by(Reading.recorded_at.desc())

    if node_id:
        station = get_station(db, node_id)
        if not station:
            return []
        q = q.filter(Reading.station_id == station.id)

    return q.limit(limit).all()


def get_station_stats(db: Session, node_id: str):
    station = get_station(db, node_id)
    if not station:
        return None

    rows = db.query(Reading).filter(Reading.station_id == station.id).all()
    if not rows:
        return {
            "node_id": node_id,
            "location": station.location,
            "count": 0
        }

    levels = [r.level_cm for r in rows]
    return {
        "node_id": node_id,
        "location": station.location,
        "count": len(rows),
        "level_min_cm": round(min(levels), 2),
        "level_max_cm": round(max(levels), 2),
        "level_avg_cm": round(sum(levels) / len(levels), 2),
        "first_reading": rows[0].recorded_at,
        "last_reading": rows[-1].recorded_at,
    }