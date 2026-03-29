from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PriceRecord, Prediction, TrackedRoute
from app.routers.auth import require_login
from app.schemas import RouteResponse

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def index(request: Request, user: dict = Depends(require_login), db: Session = Depends(get_db)):
    routes_orm = db.query(TrackedRoute).order_by(TrackedRoute.created_at.desc()).all()
    routes = []
    for r in routes_orm:
        prices = (
            db.query(PriceRecord)
            .filter(PriceRecord.route_id == r.id)
            .order_by(PriceRecord.fetched_at.desc())
            .limit(5)
            .all()
        )
        prediction = (
            db.query(Prediction)
            .filter(Prediction.route_id == r.id)
            .order_by(Prediction.created_at.desc())
            .first()
        )
        routes.append(RouteResponse.from_model(r, prices, prediction))
    return templates.TemplateResponse(
        "index.html", {"request": request, "routes": routes, "user": user}
    )


@router.get("/route/{route_id}", response_class=HTMLResponse)
def route_detail(route_id: int, request: Request, user: dict = Depends(require_login), db: Session = Depends(get_db)):
    route_orm = db.query(TrackedRoute).filter(TrackedRoute.id == route_id).first()
    if not route_orm:
        return HTMLResponse("Route not found", status_code=404)
    prices = (
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
    route = RouteResponse.from_model(route_orm, prices, predictions[0] if predictions else None)
    return templates.TemplateResponse(
        "route_detail.html",
        {
            "request": request,
            "route": route,
            "user": user,
            "all_prices": [
                {
                    "id": p.id,
                    "cabin_type": p.cabin_type,
                    "airline": p.airline,
                    "price": p.price,
                    "currency": p.currency,
                    "fetched_at": p.fetched_at,
                }
                for p in prices
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
