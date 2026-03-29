import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PriceRecord, Prediction, TrackedRoute
from app.routers.auth import require_login
from app.schemas import (
    PredictionResponse,
    PriceResponse,
    RouteCreate,
    RouteResponse,
)

router = APIRouter(prefix="/api", dependencies=[Depends(require_login)])


def _latest_prices_per_cabin(db: Session, route_id: int) -> list[PriceRecord]:
    """Return the most recent price record for each cabin_type on a route."""
    all_prices = (
        db.query(PriceRecord)
        .filter(PriceRecord.route_id == route_id)
        .order_by(PriceRecord.fetched_at.desc())
        .all()
    )
    seen: dict[str, PriceRecord] = {}
    for p in all_prices:
        if p.cabin_type not in seen:
            seen[p.cabin_type] = p
    return list(seen.values())


@router.post("/routes", response_model=RouteResponse)
def create_route(payload: RouteCreate, db: Session = Depends(get_db)):
    route = TrackedRoute(
        origin=payload.origin.upper(),
        destination=payload.destination.upper(),
        departure_date=payload.departure_date,
        return_date=payload.return_date,
        is_round_trip=payload.is_round_trip,
        airlines=json.dumps(payload.airlines),
        alliances=json.dumps(payload.alliances),
        cabin_types=json.dumps(payload.cabin_types),
        travelers=json.dumps(payload.travelers),
    )
    db.add(route)
    db.commit()
    db.refresh(route)
    return RouteResponse.from_model(route)


@router.get("/routes", response_model=list[RouteResponse])
def list_routes(db: Session = Depends(get_db)):
    routes = db.query(TrackedRoute).order_by(TrackedRoute.created_at.desc()).all()
    result = []
    for route in routes:
        prices = _latest_prices_per_cabin(db, route.id)
        prediction = (
            db.query(Prediction)
            .filter(Prediction.route_id == route.id)
            .order_by(Prediction.created_at.desc())
            .first()
        )
        result.append(RouteResponse.from_model(route, prices, prediction))
    return result


@router.get("/routes/{route_id}", response_model=RouteResponse)
def get_route(route_id: int, db: Session = Depends(get_db)):
    route = db.query(TrackedRoute).filter(TrackedRoute.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    prices = _latest_prices_per_cabin(db, route.id)
    prediction = (
        db.query(Prediction)
        .filter(Prediction.route_id == route.id)
        .order_by(Prediction.created_at.desc())
        .first()
    )
    return RouteResponse.from_model(route, prices, prediction)


@router.delete("/routes/{route_id}")
def delete_route(route_id: int, db: Session = Depends(get_db)):
    route = db.query(TrackedRoute).filter(TrackedRoute.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    db.delete(route)
    db.commit()
    return {"ok": True}


@router.patch("/routes/{route_id}/toggle", response_model=RouteResponse)
def toggle_route(route_id: int, db: Session = Depends(get_db)):
    route = db.query(TrackedRoute).filter(TrackedRoute.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    route.is_active = not route.is_active
    db.commit()
    db.refresh(route)
    return RouteResponse.from_model(route)


@router.post("/routes/{route_id}/check", response_model=RouteResponse)
def check_route(route_id: int, request: Request, db: Session = Depends(get_db)):
    route = db.query(TrackedRoute).filter(TrackedRoute.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    price_tracker = request.app.state.price_tracker
    price_tracker.check_route(db, route)

    prices = _latest_prices_per_cabin(db, route.id)
    prediction = (
        db.query(Prediction)
        .filter(Prediction.route_id == route.id)
        .order_by(Prediction.created_at.desc())
        .first()
    )
    return RouteResponse.from_model(route, prices, prediction)


@router.get("/routes/{route_id}/prices", response_model=list[PriceResponse])
def get_route_prices(route_id: int, db: Session = Depends(get_db)):
    route = db.query(TrackedRoute).filter(TrackedRoute.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    prices = (
        db.query(PriceRecord)
        .filter(PriceRecord.route_id == route.id)
        .order_by(PriceRecord.fetched_at.desc())
        .all()
    )
    return [PriceResponse.model_validate(p) for p in prices]


@router.get("/routes/{route_id}/predictions", response_model=list[PredictionResponse])
def get_route_predictions(route_id: int, db: Session = Depends(get_db)):
    route = db.query(TrackedRoute).filter(TrackedRoute.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    predictions = (
        db.query(Prediction)
        .filter(Prediction.route_id == route.id)
        .order_by(Prediction.created_at.desc())
        .all()
    )
    return [PredictionResponse.model_validate(p) for p in predictions]
