from datetime import date, datetime
from unittest.mock import MagicMock

from app.schemas import PredictionResponse, PriceResponse, RouteCreate, RouteResponse


class TestRouteCreate:
    def test_valid_data(self):
        data = {
            "origin": "JFK",
            "destination": "LAX",
            "departure_date": "2026-06-15",
            "return_date": "2026-06-22",
            "is_round_trip": True,
            "airlines": ["AA"],
            "alliances": ["oneworld"],
            "cabin_types": ["business"],
            "travelers": [30, 25],
        }
        rc = RouteCreate(**data)
        assert rc.origin == "JFK"
        assert rc.departure_date == date(2026, 6, 15)
        assert rc.return_date == date(2026, 6, 22)
        assert rc.is_round_trip is True
        assert rc.airlines == ["AA"]

    def test_defaults(self):
        rc = RouteCreate(origin="JFK", destination="LAX", departure_date="2026-06-15")
        assert rc.return_date is None
        assert rc.is_round_trip is False
        assert rc.airlines == []
        assert rc.alliances == []
        assert rc.cabin_types == []
        assert rc.travelers == [30]


class TestRouteResponse:
    def test_from_model_basic(self):
        mock_route = MagicMock()
        mock_route.id = 1
        mock_route.origin = "JFK"
        mock_route.destination = "LAX"
        mock_route.departure_date = date(2026, 6, 15)
        mock_route.return_date = None
        mock_route.is_round_trip = False
        mock_route.airlines = '["AA"]'
        mock_route.alliances = "[]"
        mock_route.cabin_types = '["economy"]'
        mock_route.travelers = "[30]"
        mock_route.is_active = True
        mock_route.created_at = datetime(2026, 1, 1, 12, 0, 0)

        resp = RouteResponse.from_model(mock_route)
        assert resp.id == 1
        assert resp.origin == "JFK"
        assert resp.airlines == ["AA"]
        assert resp.cabin_types == ["economy"]
        assert resp.travelers == [30]
        assert resp.latest_prices == []
        assert resp.latest_prediction is None

    def test_from_model_with_empty_strings(self):
        mock_route = MagicMock()
        mock_route.id = 2
        mock_route.origin = "SFO"
        mock_route.destination = "LHR"
        mock_route.departure_date = date(2026, 7, 1)
        mock_route.return_date = date(2026, 7, 10)
        mock_route.is_round_trip = True
        mock_route.airlines = ""
        mock_route.alliances = ""
        mock_route.cabin_types = ""
        mock_route.travelers = ""
        mock_route.is_active = True
        mock_route.created_at = datetime(2026, 1, 1)

        resp = RouteResponse.from_model(mock_route)
        assert resp.airlines == []
        assert resp.alliances == []
        assert resp.cabin_types == []
        assert resp.travelers == []

    def test_from_model_with_prices_and_prediction(self):
        mock_route = MagicMock()
        mock_route.id = 1
        mock_route.origin = "JFK"
        mock_route.destination = "LAX"
        mock_route.departure_date = date(2026, 6, 15)
        mock_route.return_date = None
        mock_route.is_round_trip = False
        mock_route.airlines = "[]"
        mock_route.alliances = "[]"
        mock_route.cabin_types = "[]"
        mock_route.travelers = "[]"
        mock_route.is_active = True
        mock_route.created_at = datetime(2026, 1, 1)

        mock_price = MagicMock()
        mock_price.id = 10
        mock_price.departure_date = date(2026, 6, 15)
        mock_price.cabin_type = "economy"
        mock_price.airline = "AA"
        mock_price.price = 350.0
        mock_price.currency = "USD"
        mock_price.fetched_at = datetime(2026, 1, 1, 12, 0, 0)

        mock_pred = MagicMock()
        mock_pred.id = 20
        mock_pred.trend = "down"
        mock_pred.summary = "Falling"
        mock_pred.buy_recommendation = "wait"
        mock_pred.predicted_best_buy_date = date(2026, 5, 1)
        mock_pred.confidence = 0.8
        mock_pred.created_at = datetime(2026, 1, 1, 12, 0, 0)

        resp = RouteResponse.from_model(mock_route, [mock_price], mock_pred)
        assert len(resp.latest_prices) == 1
        assert resp.latest_prices[0].price == 350.0
        assert resp.latest_prediction is not None
        assert resp.latest_prediction.trend == "down"


class TestPriceResponse:
    def test_validation(self):
        pr = PriceResponse(
            id=1,
            cabin_type="economy",
            airline="AA",
            price=350.0,
            currency="USD",
            fetched_at=datetime(2026, 1, 1),
        )
        assert pr.price == 350.0
        assert pr.departure_date is None

    def test_validation_with_departure_date(self):
        pr = PriceResponse(
            id=2,
            departure_date=date(2026, 6, 15),
            cabin_type="business",
            airline="UA",
            price=1200.0,
            currency="USD",
            fetched_at=datetime(2026, 1, 1),
        )
        assert pr.departure_date == date(2026, 6, 15)


class TestPredictionResponse:
    def test_validation(self):
        pred = PredictionResponse(
            id=1,
            trend="up",
            summary="Rising",
            buy_recommendation="buy now",
            predicted_best_buy_date=None,
            confidence=0.7,
            created_at=datetime(2026, 1, 1),
        )
        assert pred.trend == "up"
        assert pred.predicted_best_buy_date is None
