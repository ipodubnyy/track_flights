from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PriceRecord, Prediction, TrackedRoute, UserPreference
from app.routers.api import _latest_prices_per_cabin
from app.routers.auth import require_login
from app.schemas import CABIN_DISPLAY_NAMES, CURRENCY_SYMBOLS, RouteResponse, convert_price

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _convert_route_prices(route_resp: RouteResponse, target_cur: str) -> RouteResponse:
    """Convert latest_prices amounts to target currency in-place."""
    for p in route_resp.latest_prices:
        p.price = convert_price(p.price, p.currency or "USD", target_cur)
        p.currency = target_cur
    return route_resp


@router.get("/", response_class=HTMLResponse)
def index(request: Request, user: dict = Depends(require_login), db: Session = Depends(get_db)):
    routes_orm = db.query(TrackedRoute).order_by(TrackedRoute.created_at.desc()).all()
    pref = db.query(UserPreference).first()
    currency = pref.currency if pref else "USD"
    routes = []
    route_histories: dict[int, list] = {}
    for r in routes_orm:
        prices = _latest_prices_per_cabin(db, r.id)
        prediction = (
            db.query(Prediction)
            .filter(Prediction.route_id == r.id)
            .order_by(Prediction.created_at.desc())
            .first()
        )
        route_resp = RouteResponse.from_model(r, prices, prediction)
        _convert_route_prices(route_resp, currency)
        routes.append(route_resp)
        # Price history for mini chart (primary departure date only, last 50)
        route_dep = r.departure_date
        history = (
            db.query(PriceRecord)
            .filter(
                PriceRecord.route_id == r.id,
                (PriceRecord.departure_date == route_dep) | (PriceRecord.departure_date.is_(None)),
            )
            .order_by(PriceRecord.fetched_at.asc())
            .limit(50)
            .all()
        )
        route_histories[r.id] = [
            {
                "airline": p.airline,
                "price": convert_price(p.price, p.currency or "USD", currency),
                "fetched_at": p.fetched_at.isoformat() if p.fetched_at else "",
                "cabin_type": p.cabin_type,
            }
            for p in history
        ]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "routes": routes,
            "user": user,
            "currency": currency,
            "route_histories": route_histories,
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
    all_prices_orm = (
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
    pref = db.query(UserPreference).first()
    currency = pref.currency if pref else "USD"
    route = RouteResponse.from_model(route_orm, latest_prices, predictions[0] if predictions else None)
    _convert_route_prices(route, currency)
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
                    "price": convert_price(p.price, p.currency or "USD", currency),
                    "currency": currency,
                    "flight_info": p.flight_info or "",
                    "fetched_at": p.fetched_at,
                }
                for p in all_prices_orm
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
