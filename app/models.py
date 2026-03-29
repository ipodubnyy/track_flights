import json

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class TrackedRoute(Base):
    __tablename__ = "tracked_routes"

    id = Column(Integer, primary_key=True, index=True)
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    departure_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=True)
    is_round_trip = Column(Boolean, default=False)
    airlines = Column(String, default="[]")
    alliances = Column(String, default="[]")
    cabin_types = Column(String, default="[]")
    travelers = Column(String, default="[]")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    price_records = relationship(
        "PriceRecord", back_populates="route", cascade="all, delete-orphan"
    )
    predictions = relationship(
        "Prediction", back_populates="route", cascade="all, delete-orphan"
    )

    # --- JSON helpers ---

    def get_airlines(self) -> list[str]:
        return json.loads(self.airlines) if self.airlines else []

    def set_airlines(self, vals: list[str]) -> None:
        self.airlines = json.dumps(vals)

    def get_alliances(self) -> list[str]:
        return json.loads(self.alliances) if self.alliances else []

    def set_alliances(self, vals: list[str]) -> None:
        self.alliances = json.dumps(vals)

    def get_cabin_types(self) -> list[str]:
        return json.loads(self.cabin_types) if self.cabin_types else []

    def set_cabin_types(self, vals: list[str]) -> None:
        self.cabin_types = json.dumps(vals)

    def get_travelers(self) -> list[int]:
        return json.loads(self.travelers) if self.travelers else []

    def set_travelers(self, vals: list[int]) -> None:
        self.travelers = json.dumps(vals)


class PriceRecord(Base):
    __tablename__ = "price_records"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("tracked_routes.id"), nullable=False)
    departure_date = Column(Date, nullable=True)  # actual date checked (may differ from route by ±3 days)
    cabin_type = Column(String, nullable=False)
    airline = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    flight_info = Column(String, default="")  # e.g. "UA123" or "UA123 via ORD"
    fetched_at = Column(DateTime, default=func.now())

    route = relationship("TrackedRoute", back_populates="price_records")


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("tracked_routes.id"), nullable=False)
    trend = Column(String, nullable=False)
    summary = Column(String, nullable=False)
    buy_recommendation = Column(String, nullable=False)
    predicted_best_buy_date = Column(Date, nullable=True)
    confidence = Column(Float, default=0.0)
    created_at = Column(DateTime, default=func.now())

    route = relationship("TrackedRoute", back_populates="predictions")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, default=1)
    currency = Column(String, default="USD")  # "USD" or "RUB"
