from __future__ import annotations

import json
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class RouteCreate(BaseModel):
    origin: str
    destination: str
    departure_date: date
    return_date: date | None = None
    is_round_trip: bool = False
    airlines: list[str] = []
    alliances: list[str] = []
    cabin_types: list[str] = []
    travelers: list[int] = [30]


class PriceResponse(BaseModel):
    id: int
    departure_date: date | None = None
    cabin_type: str
    airline: str
    price: float
    currency: str
    fetched_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PredictionResponse(BaseModel):
    id: int
    trend: str
    summary: str
    buy_recommendation: str
    predicted_best_buy_date: date | None
    confidence: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RouteResponse(BaseModel):
    id: int
    origin: str
    destination: str
    departure_date: date
    return_date: date | None
    is_round_trip: bool
    airlines: list[str]
    alliances: list[str]
    cabin_types: list[str]
    travelers: list[int]
    is_active: bool
    created_at: datetime
    latest_prices: list[PriceResponse] = []
    latest_prediction: PredictionResponse | None = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(
        cls,
        route,
        latest_prices=None,
        latest_prediction=None,
    ) -> RouteResponse:
        return cls(
            id=route.id,
            origin=route.origin,
            destination=route.destination,
            departure_date=route.departure_date,
            return_date=route.return_date,
            is_round_trip=route.is_round_trip,
            airlines=json.loads(route.airlines) if route.airlines else [],
            alliances=json.loads(route.alliances) if route.alliances else [],
            cabin_types=json.loads(route.cabin_types) if route.cabin_types else [],
            travelers=json.loads(route.travelers) if route.travelers else [],
            is_active=route.is_active,
            created_at=route.created_at,
            latest_prices=[
                PriceResponse.model_validate(p) for p in (latest_prices or [])
            ],
            latest_prediction=(
                PredictionResponse.model_validate(latest_prediction)
                if latest_prediction
                else None
            ),
        )
