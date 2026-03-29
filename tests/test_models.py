import json
from datetime import date, datetime

from app.database import Base
from app.models import Prediction, PriceRecord, TrackedRoute


class TestTrackedRouteJsonHelpers:
    def test_get_airlines_populated(self, sample_route):
        assert sample_route.get_airlines() == ["AA", "UA"]

    def test_get_airlines_empty_string(self, db_session):
        route = TrackedRoute(
            origin="A",
            destination="B",
            departure_date=date(2026, 1, 1),
            airlines="",
            created_at=datetime(2026, 1, 1),
        )
        db_session.add(route)
        db_session.commit()
        assert route.get_airlines() == []

    def test_get_airlines_empty_list(self, db_session):
        route = TrackedRoute(
            origin="A",
            destination="B",
            departure_date=date(2026, 1, 1),
            airlines="[]",
            created_at=datetime(2026, 1, 1),
        )
        db_session.add(route)
        db_session.commit()
        assert route.get_airlines() == []

    def test_set_airlines(self, sample_route):
        sample_route.set_airlines(["DL", "SQ"])
        assert json.loads(sample_route.airlines) == ["DL", "SQ"]

    def test_get_alliances_populated(self, sample_route):
        assert sample_route.get_alliances() == ["oneworld"]

    def test_get_alliances_empty_string(self, db_session):
        route = TrackedRoute(
            origin="A",
            destination="B",
            departure_date=date(2026, 1, 1),
            alliances="",
            created_at=datetime(2026, 1, 1),
        )
        db_session.add(route)
        db_session.commit()
        assert route.get_alliances() == []

    def test_set_alliances(self, sample_route):
        sample_route.set_alliances(["SkyTeam"])
        assert json.loads(sample_route.alliances) == ["SkyTeam"]

    def test_get_cabin_types_populated(self, sample_route):
        assert sample_route.get_cabin_types() == ["economy", "business"]

    def test_get_cabin_types_empty_string(self, db_session):
        route = TrackedRoute(
            origin="A",
            destination="B",
            departure_date=date(2026, 1, 1),
            cabin_types="",
            created_at=datetime(2026, 1, 1),
        )
        db_session.add(route)
        db_session.commit()
        assert route.get_cabin_types() == []

    def test_set_cabin_types(self, sample_route):
        sample_route.set_cabin_types(["first"])
        assert json.loads(sample_route.cabin_types) == ["first"]

    def test_get_travelers_populated(self, sample_route):
        assert sample_route.get_travelers() == [30, 25]

    def test_get_travelers_empty_string(self, db_session):
        route = TrackedRoute(
            origin="A",
            destination="B",
            departure_date=date(2026, 1, 1),
            travelers="",
            created_at=datetime(2026, 1, 1),
        )
        db_session.add(route)
        db_session.commit()
        assert route.get_travelers() == []

    def test_set_travelers(self, sample_route):
        sample_route.set_travelers([40, 35, 10])
        assert json.loads(sample_route.travelers) == [40, 35, 10]


class TestPriceRecord:
    def test_creation(self, sample_prices):
        assert len(sample_prices) == 2
        assert sample_prices[0].cabin_type == "economy"
        assert sample_prices[0].airline == "AA"
        assert sample_prices[0].price == 350.0
        assert sample_prices[0].currency == "USD"
        assert sample_prices[1].price == 1200.0


class TestPrediction:
    def test_creation(self, sample_prediction):
        assert sample_prediction.trend == "down"
        assert sample_prediction.summary == "Prices are falling"
        assert sample_prediction.buy_recommendation == "wait"
        assert sample_prediction.predicted_best_buy_date == date(2026, 5, 1)
        assert sample_prediction.confidence == 0.85

    def test_relationship(self, sample_prediction, sample_route):
        assert sample_prediction.route_id == sample_route.id
