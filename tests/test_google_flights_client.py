import httpx
import respx

from app.services.google_flights_client import (
    CABIN_CLASS_MAP,
    CABIN_CLASS_REVERSE,
    GoogleFlightsClient,
)


class TestSearchFlights:
    SAMPLE_RESPONSE = {
        "best_flights": [
            {
                "price": 450,
                "flights": [
                    {
                        "airline": "United",
                        "flight_number": "UA 123",
                        "arrival_airport": {"id": "LAX", "name": "Los Angeles"},
                    }
                ],
            }
        ],
        "other_flights": [],
    }

    @respx.mock
    def test_search_oneway_success(self):
        respx.get("https://serpapi.com/search").mock(
            return_value=httpx.Response(200, json=self.SAMPLE_RESPONSE)
        )
        client = GoogleFlightsClient("testkey")
        results = client.search_flights("JFK", "LAX", "2026-06-15")
        assert len(results) == 1
        assert results[0]["airline"] == "UA"
        assert results[0]["price"] == 450.0
        assert results[0]["currency"] == "USD"
        assert results[0]["cabin_type"] == "economy"
        assert results[0]["flight_info"] == "UA123"
        assert results[0]["source"] == "google_flights"

    @respx.mock
    def test_search_roundtrip(self):
        respx.get("https://serpapi.com/search").mock(
            return_value=httpx.Response(200, json=self.SAMPLE_RESPONSE)
        )
        client = GoogleFlightsClient("testkey")
        results = client.search_flights(
            "JFK", "LAX", "2026-06-15", return_date="2026-06-22"
        )
        assert len(results) == 1
        # Verify params were built correctly (type=1 for roundtrip)
        request = respx.calls.last.request
        assert "return_date" in str(request.url)

    @respx.mock
    def test_search_with_airline_filter(self):
        response = {
            "best_flights": [
                {
                    "price": 450,
                    "flights": [
                        {
                            "airline": "United",
                            "flight_number": "UA 123",
                            "arrival_airport": {"id": "LAX"},
                        }
                    ],
                },
                {
                    "price": 500,
                    "flights": [
                        {
                            "airline": "American",
                            "flight_number": "AA 456",
                            "arrival_airport": {"id": "LAX"},
                        }
                    ],
                },
            ],
            "other_flights": [],
        }
        respx.get("https://serpapi.com/search").mock(
            return_value=httpx.Response(200, json=response)
        )
        client = GoogleFlightsClient("testkey")
        results = client.search_flights(
            "JFK", "LAX", "2026-06-15", airline_codes=["UA"]
        )
        assert len(results) == 1
        assert results[0]["airline"] == "UA"

    @respx.mock
    def test_search_http_error_returns_empty(self):
        respx.get("https://serpapi.com/search").mock(
            return_value=httpx.Response(500, text="Server Error")
        )
        client = GoogleFlightsClient("testkey")
        results = client.search_flights("JFK", "LAX", "2026-06-15")
        assert results == []

    def test_parse_response_multi_leg_via_stop(self):
        """Multi-leg flights with intermediate stops."""
        data = {
            "best_flights": [
                {
                    "price": 450,
                    "flights": [
                        {
                            "airline": "United",
                            "flight_number": "UA 123",
                            "arrival_airport": {"id": "ORD", "name": "Chicago O'Hare"},
                        },
                        {
                            "airline": "United",
                            "flight_number": "UA 456",
                            "arrival_airport": {"id": "FRA", "name": "Frankfurt"},
                        },
                    ],
                }
            ],
            "other_flights": [],
        }
        client = GoogleFlightsClient("testkey")
        results = client._parse_response(data, "economy", None)
        assert len(results) == 1
        assert results[0]["flight_info"] == "UA123, UA456 via ORD"
        assert results[0]["source"] == "google_flights"

    def test_parse_response_no_price_skipped(self):
        """Flight groups without a price should be skipped."""
        data = {
            "best_flights": [
                {
                    "flights": [
                        {
                            "airline": "United",
                            "flight_number": "UA 123",
                            "arrival_airport": {"id": "LAX"},
                        }
                    ],
                }
            ],
            "other_flights": [],
        }
        client = GoogleFlightsClient("testkey")
        results = client._parse_response(data, "economy", None)
        assert results == []

    def test_parse_response_no_flights_skipped(self):
        """Flight groups with empty flights list should be skipped."""
        data = {
            "best_flights": [
                {"price": 450, "flights": []},
            ],
            "other_flights": [],
        }
        client = GoogleFlightsClient("testkey")
        results = client._parse_response(data, "economy", None)
        assert results == []

    def test_parse_response_flight_number_extraction(self):
        """Airline code extracted from flight_number field."""
        data = {
            "best_flights": [
                {
                    "price": 300,
                    "flights": [
                        {
                            "airline": "Lufthansa",
                            "flight_number": "LH 401",
                            "arrival_airport": {"id": "FRA"},
                        }
                    ],
                }
            ],
            "other_flights": [],
        }
        client = GoogleFlightsClient("testkey")
        results = client._parse_response(data, "business", None)
        assert results[0]["airline"] == "LH"
        assert results[0]["cabin_type"] == "business"

    def test_parse_response_google_flights_source_tag(self):
        """All results should have source='google_flights'."""
        data = {
            "best_flights": [],
            "other_flights": [
                {
                    "price": 600,
                    "flights": [
                        {
                            "airline": "Delta",
                            "flight_number": "DL 100",
                            "arrival_airport": {"id": "ATL"},
                        }
                    ],
                }
            ],
        }
        client = GoogleFlightsClient("testkey")
        results = client._parse_response(data, "economy", None)
        assert len(results) == 1
        assert results[0]["source"] == "google_flights"

    def test_parse_response_short_flight_number_uses_airline(self):
        """When flight_number is too short, use airline field as-is."""
        data = {
            "best_flights": [
                {
                    "price": 200,
                    "flights": [
                        {
                            "airline": "SomeAirline",
                            "flight_number": "X",
                            "arrival_airport": {"id": "LAX"},
                        }
                    ],
                }
            ],
            "other_flights": [],
        }
        client = GoogleFlightsClient("testkey")
        results = client._parse_response(data, "economy", None)
        assert results[0]["airline"] == "SomeAirline"

    def test_parse_response_no_flight_number(self):
        """When flight_number is missing, airline field is used."""
        data = {
            "best_flights": [
                {
                    "price": 200,
                    "flights": [
                        {
                            "airline": "Mystery",
                            "arrival_airport": {"id": "LAX"},
                        }
                    ],
                }
            ],
            "other_flights": [],
        }
        client = GoogleFlightsClient("testkey")
        results = client._parse_response(data, "economy", None)
        assert results[0]["airline"] == "Mystery"

    def test_parse_response_with_currency(self):
        """Currency parameter is passed through to results."""
        data = {
            "best_flights": [
                {
                    "price": 100,
                    "flights": [
                        {
                            "airline": "AA",
                            "flight_number": "AA 1",
                            "arrival_airport": {"id": "LAX"},
                        }
                    ],
                }
            ],
            "other_flights": [],
        }
        client = GoogleFlightsClient("testkey")
        results = client._parse_response(data, "economy", None, currency="RUB")
        assert results[0]["currency"] == "RUB"


class TestCabinClassMap:
    def test_all_mappings(self):
        assert CABIN_CLASS_MAP["economy"] == 1
        assert CABIN_CLASS_MAP["economy_plus"] == 2
        assert CABIN_CLASS_MAP["premium_economy"] == 2
        assert CABIN_CLASS_MAP["business"] == 3
        assert CABIN_CLASS_MAP["first"] == 4

    def test_reverse_mappings(self):
        assert CABIN_CLASS_REVERSE[1] == "economy"
        assert CABIN_CLASS_REVERSE[2] == "premium_economy"
        assert CABIN_CLASS_REVERSE[3] == "business"
        assert CABIN_CLASS_REVERSE[4] == "first"
