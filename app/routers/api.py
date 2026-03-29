import json
import threading
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PriceRecord, Prediction, TrackedRoute, UserPreference
from app.routers.auth import require_login
from app.schemas import (
    CurrencyUpdate,
    PredictionResponse,
    PriceResponse,
    RouteCreate,
    RouteResponse,
    RouteUpdate,
)

router = APIRouter(prefix="/api", dependencies=[Depends(require_login)])


def _latest_prices_per_cabin(db: Session, route_id: int) -> list[PriceRecord]:
    """Return the most recent price record for each (departure_date, cabin_type) on a route."""
    route = db.query(TrackedRoute).filter(TrackedRoute.id == route_id).first()
    route_dep = route.departure_date if route else None
    all_prices = (
        db.query(PriceRecord)
        .filter(PriceRecord.route_id == route_id)
        .order_by(PriceRecord.fetched_at.desc())
        .all()
    )
    seen: dict[tuple, PriceRecord] = {}
    for p in all_prices:
        # Treat NULL departure_date as the route's requested date
        dep = p.departure_date or route_dep
        key = (dep, p.cabin_type)
        if key not in seen:
            seen[key] = p
    return sorted(seen.values(), key=lambda p: (p.departure_date or route_dep or date.min, p.cabin_type))


def _run_check_in_background(app_state, route_id: int, get_db_func) -> None:
    """Run price check in a background thread so route creation returns immediately."""
    db_gen = get_db_func()
    db = next(db_gen)
    try:
        route = db.query(TrackedRoute).filter(TrackedRoute.id == route_id).first()
        if route:
            pref = db.query(UserPreference).first()
            currency = pref.currency if pref else "USD"
            app_state.price_tracker.check_route(db, route, currency=currency)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Background check failed for route %s", route_id)
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


@router.post("/routes", response_model=RouteResponse)
def create_route(payload: RouteCreate, request: Request, db: Session = Depends(get_db)):
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

    # Auto-check prices in background
    threading.Thread(
        target=_run_check_in_background,
        args=(request.app.state, route.id, get_db),
        daemon=True,
    ).start()

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
    pref = db.query(UserPreference).first()
    currency = pref.currency if pref else "USD"
    price_tracker.check_route(db, route, currency=currency)

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


@router.get("/currency")
def get_currency(db: Session = Depends(get_db)):
    pref = db.query(UserPreference).first()
    if not pref:
        pref = UserPreference(id=1, currency="USD")
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return {"currency": pref.currency}


@router.patch("/currency")
def set_currency(payload: CurrencyUpdate, db: Session = Depends(get_db)):
    if payload.currency not in ("USD", "RUB"):
        raise HTTPException(status_code=400, detail="Unsupported currency")
    pref = db.query(UserPreference).first()
    if not pref:
        pref = UserPreference(id=1, currency=payload.currency)
        db.add(pref)
    else:
        pref.currency = payload.currency
    db.commit()
    db.refresh(pref)
    return {"currency": pref.currency}


@router.patch("/routes/{route_id}", response_model=RouteResponse)
def update_route(route_id: int, payload: RouteUpdate, db: Session = Depends(get_db)):
    route = db.query(TrackedRoute).filter(TrackedRoute.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    if payload.airlines is not None:
        route.airlines = json.dumps(payload.airlines)
    if payload.alliances is not None:
        route.alliances = json.dumps(payload.alliances)
    if payload.cabin_types is not None:
        route.cabin_types = json.dumps(payload.cabin_types)
    if payload.travelers is not None:
        route.travelers = json.dumps(payload.travelers)
    if payload.departure_date is not None:
        route.departure_date = payload.departure_date
    if payload.return_date is not None:
        route.return_date = payload.return_date
    if payload.is_round_trip is not None:
        route.is_round_trip = payload.is_round_trip
    db.commit()
    db.refresh(route)
    return RouteResponse.from_model(route)
