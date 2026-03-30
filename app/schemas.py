from __future__ import annotations

import json
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator


CABIN_DISPLAY_NAMES = {
    "economy": "Economy",
    "economy_plus": "Economy Plus",
    "premium_economy": "Premium Economy",
    "business": "Business",
    "first": "First",
}

CURRENCY_SYMBOLS = {
    "USD": ("$", "before"),  # $123
    "RUB": ("₽", "after"),   # 123 ₽
}

# Approximate USD/RUB rate; updated by the app periodically
_exchange_cache: dict[str, float] = {"USD_TO_RUB": 92.0}


def fetch_exchange_rate() -> float:
    """Fetch current USD->RUB rate. Falls back to cached value."""
    import httpx
    try:
        resp = httpx.get(
            "https://api.exchangerate-api.com/v4/latest/USD",
            timeout=5.0,
        )
        resp.raise_for_status()
        rate = resp.json().get("rates", {}).get("RUB", 92.0)
        _exchange_cache["USD_TO_RUB"] = float(rate)
    except Exception:
        pass
    return _exchange_cache["USD_TO_RUB"]


def convert_price(amount: float, from_cur: str, to_cur: str) -> float:
    """Convert between USD and RUB."""
    if from_cur == to_cur:
        return amount
    rate = _exchange_cache["USD_TO_RUB"]
    if from_cur == "USD" and to_cur == "RUB":
        return amount * rate
    if from_cur == "RUB" and to_cur == "USD":
        return amount / rate if rate else amount
    return amount


class CurrencyUpdate(BaseModel):
    currency: str  # "USD" or "RUB"


class RouteUpdate(BaseModel):
    airlines: list[str] | None = None
    alliances: list[str] | None = None
    cabin_types: list[str] | None = None
    travelers: list[int] | None = None
    departure_date: date | None = None
    return_date: date | None = None
    is_round_trip: bool | None = None

    @field_validator("cabin_types")
    @classmethod
    def validate_cabins(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        valid = {"economy", "economy_plus", "premium_economy", "business", "first"}
        for c in v:
            if c not in valid:
                raise ValueError(f"Invalid cabin type: {c}")
        return v

    @field_validator("travelers")
    @classmethod
    def validate_travelers(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return v
        if len(v) > 9:
            raise ValueError("Maximum 9 travelers")
        if len(v) < 1:
            raise ValueError("At least 1 traveler required")
        for age in v:
            if age < 0 or age > 120:
                raise ValueError(f"Invalid age: {age}")
        return v


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

    @field_validator("origin", "destination")
    @classmethod
    def validate_iata(cls, v: str) -> str:
        v = v.strip().upper()
        if not v.isalpha() or len(v) != 3:
            raise ValueError("Must be a 3-letter IATA code")
        return v

    @field_validator("cabin_types")
    @classmethod
    def validate_cabins(cls, v: list[str]) -> list[str]:
        valid = {"economy", "economy_plus", "premium_economy", "business", "first"}
        for c in v:
            if c not in valid:
                raise ValueError(f"Invalid cabin type: {c}")
        return v

    @field_validator("travelers")
    @classmethod
    def validate_travelers(cls, v: list[int]) -> list[int]:
        if len(v) > 9:
            raise ValueError("Maximum 9 travelers")
        if len(v) < 1:
            raise ValueError("At least 1 traveler required")
        for age in v:
            if age < 0 or age > 120:
                raise ValueError(f"Invalid age: {age}")
        return v

    @field_validator("airlines")
    @classmethod
    def validate_airlines(cls, v: list[str]) -> list[str]:
        for code in v:
            code = code.strip().upper()
            if not code.isalpha() or len(code) < 2 or len(code) > 3:
                raise ValueError(f"Invalid airline code: {code}")
        return [c.strip().upper() for c in v]


class PriceResponse(BaseModel):
    id: int
    departure_date: date | None = None
    cabin_type: str
    airline: str
    price: float
    currency: str
    flight_info: str = ""
    source: str = "flightapi"
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
