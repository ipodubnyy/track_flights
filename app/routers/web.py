from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PriceRecord, Prediction, TrackedRoute, UserPreference
from app.routers.api import _latest_prices_per_cabin
from app.routers.auth import require_login
from app.schemas import CABIN_DISPLAY_NAMES, CURRENCY_SYMBOLS, RouteResponse

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def index(request: Request, user: dict = Depends(require_login), db: Session = Depends(get_db)):
    routes_orm = db.query(TrackedRoute).order_by(TrackedRoute.created_at.desc()).all()
    routes = []
    for r in routes_orm:
        prices = _latest_prices_per_cabin(db, r.id)
        prediction = (
            db.query(Prediction)
            .filter(Prediction.route_id == r.id)
            .order_by(Prediction.created_at.desc())
            .first()
        )
        routes.append(RouteResponse.from_model(r, prices, prediction))
    pref = db.query(UserPreference).first()
    currency = pref.currency if pref else "USD"
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "routes": routes,
            "user": user,
            "currency": currency,
            "CABIN_DISPLAY_NAMES": CABIN_DISPLAY_NAMES,
            "CURRENCY_SYMBOLS": CURRENCY_SYMBOLS,
        },
    )


@router.get("/route/{route_id}", response_class=HTMLResponse)
def route_detail(route_id: int, request: Request, user: dict = Depends(require_login), db: Session = Depends(get_db)):
    route_orm = db.query(TrackedRoute).filter(TrackedRoute.id == route_id).first()
    if not route_orm:
        return HTMLResponse("Route not found", status_code=404)
    latest_prices = _latest_prices_per_cabin(db, route_orm.id)
    all_prices = (
        db.query(PriceRecord)
        .filter(PriceRecord.route_id == route_orm.id)
        .order_by(PriceRecord.fetched_at.desc())
        .all()
    )
    predictions = (
        db.query(Prediction)
        .filter(Prediction.route_id == route_orm.id)
        .order_by(Prediction.created_at.desc())
        .all()
    )
    route = RouteResponse.from_model(route_orm, latest_prices, predictions[0] if predictions else None)
    pref = db.query(UserPreference).first()
    currency = pref.currency if pref else "USD"
    return templates.TemplateResponse(
        "route_detail.html",
        {
            "request": request,
            "route": route,
            "user": user,
            "currency": currency,
            "CABIN_DISPLAY_NAMES": CABIN_DISPLAY_NAMES,
            "CURRENCY_SYMBOLS": CURRENCY_SYMBOLS,
            "all_prices": [
                {
                    "id": p.id,
                    "departure_date": p.departure_date,
                    "cabin_type": p.cabin_type,
                    "airline": p.airline,
                    "price": p.price,
                    "currency": p.currency,
                    "fetched_at": p.fetched_at,
                }
                for p in all_prices
            ],
            "all_predictions": [
                {
                    "id": pr.id,
                    "trend": pr.trend,
                    "summary": pr.summary,
                    "buy_recommendation": pr.buy_recommendation,
                    "predicted_best_buy_date": pr.predicted_best_buy_date,
                    "confidence": pr.confidence,
                    "created_at": pr.created_at,
                }
                for pr in predictions
            ],
        },
    )
