import json
from contextlib import asynccontextmanager
from datetime import date, datetime
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import Prediction, PriceRecord, TrackedRoute
from app.routers.auth import require_login


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    Session = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def override_get_db(db_session):
    def _get_db():
        try:
            yield db_session
        finally:
            pass

    return _get_db


@pytest.fixture()
def client(override_get_db):
    from app.main import app

    mock_tracker = MagicMock()

    @asynccontextmanager
    async def test_lifespan(app_instance: FastAPI):
        app_instance.state.price_tracker = mock_tracker
        yield

    fake_user = {"email": "test@example.com", "name": "Test User", "picture": ""}

    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = test_lifespan
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_login] = lambda: fake_user

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()
    app.router.lifespan_context = original_lifespan


@pytest.fixture()
def sample_route_data():
    return {
        "origin": "JFK",
        "destination": "LAX",
        "departure_date": "2026-06-15",
        "return_date": "2026-06-22",
        "is_round_trip": True,
        "airlines": ["AA", "UA"],
        "alliances": ["oneworld"],
        "cabin_types": ["economy", "business"],
        "travelers": [30, 25],
    }


@pytest.fixture()
def sample_route(db_session):
    route = TrackedRoute(
        origin="JFK",
        destination="LAX",
        departure_date=date(2026, 6, 15),
        return_date=date(2026, 6, 22),
        is_round_trip=True,
        airlines=json.dumps(["AA", "UA"]),
        alliances=json.dumps(["oneworld"]),
        cabin_types=json.dumps(["economy", "business"]),
        travelers=json.dumps([30, 25]),
        is_active=True,
        created_at=datetime(2026, 1, 1, 12, 0, 0),
        updated_at=datetime(2026, 1, 1, 12, 0, 0),
    )
    db_session.add(route)
    db_session.commit()
    db_session.refresh(route)
    return route


@pytest.fixture()
def sample_prices(db_session, sample_route):
    prices = []
    for i, (cabin, airline, price) in enumerate(
        [("economy", "AA", 350.0), ("business", "UA", 1200.0)]
    ):
        record = PriceRecord(
            route_id=sample_route.id,
            cabin_type=cabin,
            airline=airline,
            price=price,
            currency="USD",
            fetched_at=datetime(2026, 1, 1, 12, 0, i),
        )
        db_session.add(record)
        prices.append(record)
    db_session.commit()
    for p in prices:
        db_session.refresh(p)
    return prices


@pytest.fixture()
def sample_prediction(db_session, sample_route):
    pred = Prediction(
        route_id=sample_route.id,
        trend="down",
        summary="Prices are falling",
        buy_recommendation="wait",
        predicted_best_buy_date=date(2026, 5, 1),
        confidence=0.85,
        created_at=datetime(2026, 1, 1, 12, 0, 0),
    )
    db_session.add(pred)
    db_session.commit()
    db_session.refresh(pred)
    return pred
