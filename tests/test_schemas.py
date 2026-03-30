from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.schemas import (
    PredictionResponse,
    PriceResponse,
    RouteCreate,
    RouteResponse,
    RouteUpdate,
    convert_price,
    fetch_exchange_rate,
    _exchange_cache,
)


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
        mock_price.flight_info = "AA123"
        mock_price.source = "flightapi"
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


class TestFetchExchangeRate:
    @patch("httpx.get")
    def test_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"rates": {"RUB": 95.5}}
        mock_get.return_value = mock_resp
        _exchange_cache["USD_TO_RUB"] = 92.0  # reset
        rate = fetch_exchange_rate()
        assert rate == 95.5
        assert _exchange_cache["USD_TO_RUB"] == 95.5

    @patch("httpx.get", side_effect=Exception("network error"))
    def test_failure_uses_cached(self, mock_get):
        _exchange_cache["USD_TO_RUB"] = 88.0
        rate = fetch_exchange_rate()
        assert rate == 88.0


class TestConvertPrice:
    def test_same_currency(self):
        assert convert_price(100.0, "USD", "USD") == 100.0

    def test_usd_to_rub(self):
        _exchange_cache["USD_TO_RUB"] = 90.0
        assert convert_price(10.0, "USD", "RUB") == 900.0

    def test_rub_to_usd(self):
        _exchange_cache["USD_TO_RUB"] = 90.0
        result = convert_price(900.0, "RUB", "USD")
        assert result == 10.0

    def test_unknown_currency_pair(self):
        assert convert_price(100.0, "EUR", "GBP") == 100.0


class TestRouteCreateValidateIata:
    def test_valid_iata(self):
        rc = RouteCreate(origin="jfk", destination="lax", departure_date="2026-06-15")
        assert rc.origin == "JFK"
        assert rc.destination == "LAX"

    def test_invalid_iata_too_long(self):
        with pytest.raises(ValidationError, match="3-letter IATA"):
            RouteCreate(origin="JFKX", destination="LAX", departure_date="2026-06-15")

    def test_invalid_iata_numbers(self):
        with pytest.raises(ValidationError, match="3-letter IATA"):
            RouteCreate(origin="J2K", destination="LAX", departure_date="2026-06-15")

    def test_invalid_iata_empty(self):
        with pytest.raises(ValidationError, match="3-letter IATA"):
            RouteCreate(origin="", destination="LAX", departure_date="2026-06-15")

    def test_invalid_iata_two_letters(self):
        with pytest.raises(ValidationError, match="3-letter IATA"):
            RouteCreate(origin="JF", destination="LAX", departure_date="2026-06-15")


class TestRouteCreateValidateCabins:
    def test_valid_cabin_types(self):
        rc = RouteCreate(
            origin="JFK", destination="LAX", departure_date="2026-06-15",
            cabin_types=["economy", "business", "first", "premium_economy", "economy_plus"],
        )
        assert len(rc.cabin_types) == 5

    def test_invalid_cabin_type(self):
        with pytest.raises(ValidationError, match="Invalid cabin type"):
            RouteCreate(
                origin="JFK", destination="LAX", departure_date="2026-06-15",
                cabin_types=["coach"],
            )


class TestRouteCreateValidateTravelers:
    def test_too_many_travelers(self):
        with pytest.raises(ValidationError, match="Maximum 9"):
            RouteCreate(
                origin="JFK", destination="LAX", departure_date="2026-06-15",
                travelers=[30] * 10,
            )

    def test_empty_travelers(self):
        with pytest.raises(ValidationError, match="At least 1"):
            RouteCreate(
                origin="JFK", destination="LAX", departure_date="2026-06-15",
                travelers=[],
            )

    def test_negative_age(self):
        with pytest.raises(ValidationError, match="Invalid age"):
            RouteCreate(
                origin="JFK", destination="LAX", departure_date="2026-06-15",
                travelers=[-1],
            )

    def test_age_over_120(self):
        with pytest.raises(ValidationError, match="Invalid age"):
            RouteCreate(
                origin="JFK", destination="LAX", departure_date="2026-06-15",
                travelers=[121],
            )


class TestRouteCreateValidateAirlines:
    def test_valid_airline_codes(self):
        rc = RouteCreate(
            origin="JFK", destination="LAX", departure_date="2026-06-15",
            airlines=["AA", "UAL"],
        )
        assert rc.airlines == ["AA", "UAL"]

    def test_invalid_airline_too_long(self):
        with pytest.raises(ValidationError, match="Invalid airline code"):
            RouteCreate(
                origin="JFK", destination="LAX", departure_date="2026-06-15",
                airlines=["AAAA"],
            )

    def test_invalid_airline_numbers(self):
        with pytest.raises(ValidationError, match="Invalid airline code"):
            RouteCreate(
                origin="JFK", destination="LAX", departure_date="2026-06-15",
                airlines=["A1"],
            )

    def test_invalid_airline_single_char(self):
        with pytest.raises(ValidationError, match="Invalid airline code"):
            RouteCreate(
                origin="JFK", destination="LAX", departure_date="2026-06-15",
                airlines=["A"],
            )


class TestRouteUpdateValidateCabins:
    def test_none_passthrough(self):
        ru = RouteUpdate(cabin_types=None)
        assert ru.cabin_types is None

    def test_valid_cabins(self):
        ru = RouteUpdate(cabin_types=["business"])
        assert ru.cabin_types == ["business"]

    def test_invalid_cabin(self):
        with pytest.raises(ValidationError, match="Invalid cabin type"):
            RouteUpdate(cabin_types=["invalid"])


class TestRouteUpdateValidateTravelers:
    def test_none_passthrough(self):
        ru = RouteUpdate(travelers=None)
        assert ru.travelers is None

    def test_valid_travelers(self):
        ru = RouteUpdate(travelers=[30, 25])
        assert ru.travelers == [30, 25]

    def test_too_many(self):
        with pytest.raises(ValidationError, match="Maximum 9"):
            RouteUpdate(travelers=[30] * 10)

    def test_empty(self):
        with pytest.raises(ValidationError, match="At least 1"):
            RouteUpdate(travelers=[])

    def test_negative_age(self):
        with pytest.raises(ValidationError, match="Invalid age"):
            RouteUpdate(travelers=[-5])

    def test_age_over_120(self):
        with pytest.raises(ValidationError, match="Invalid age"):
            RouteUpdate(travelers=[200])
