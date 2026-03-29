import httpx
import respx

from app.services.amadeus_client import (
    ALLIANCE_AIRLINES,
    CABIN_TYPE_MAP,
    FlightApiClient,
)


class TestSearchFlights:
    SAMPLE_RESPONSE = {
        "itineraries": [
            {
                "id": "it1",
                "leg_ids": ["leg1"],
                "pricing_options": [
                    {
                        "price": {"amount": 450.0},
                        "items": [],
                    }
                ],
            }
        ],
        "legs": [
            {
                "id": "leg1",
                "marketing_carrier_ids": [1],
                "segment_ids": ["seg1"],
            }
        ],
        "segments": [{"id": "seg1"}],
        "carriers": [{"id": 1, "alt_id": "AA", "name": "American Airlines"}],
    }

    @respx.mock
    def test_search_oneway_basic(self):
        respx.get("https://api.flightapi.io/onewaytrip/testkey/JFK/LAX/2026-06-15/1/0/0/Economy/USD").mock(
            return_value=httpx.Response(200, json=self.SAMPLE_RESPONSE)
        )
        client = FlightApiClient("testkey")
        results = client.search_flights("JFK", "LAX", "2026-06-15")
        assert len(results) == 1
        assert results[0]["airline"] == "AA"
        assert results[0]["price"] == 450.0
        assert results[0]["currency"] == "USD"
        assert results[0]["cabin_type"] == "economy"

    @respx.mock
    def test_search_roundtrip(self):
        respx.get("https://api.flightapi.io/roundtrip/testkey/JFK/LAX/2026-06-15/2026-06-22/1/0/0/Economy/USD").mock(
            return_value=httpx.Response(200, json=self.SAMPLE_RESPONSE)
        )
        client = FlightApiClient("testkey")
        results = client.search_flights(
            "JFK", "LAX", "2026-06-15", return_date="2026-06-22"
        )
        assert len(results) == 1

    @respx.mock
    def test_search_with_cabin_class_business(self):
        respx.get("https://api.flightapi.io/onewaytrip/testkey/JFK/LAX/2026-06-15/1/0/0/Business/USD").mock(
            return_value=httpx.Response(200, json={"itineraries": [], "legs": [], "carriers": []})
        )
        client = FlightApiClient("testkey")
        results = client.search_flights("JFK", "LAX", "2026-06-15", cabin_class="business")
        assert results == []

    @respx.mock
    def test_search_with_cabin_class_economy_plus(self):
        respx.get("https://api.flightapi.io/onewaytrip/testkey/JFK/LAX/2026-06-15/1/0/0/Premium_Economy/USD").mock(
            return_value=httpx.Response(200, json={"itineraries": [], "legs": [], "carriers": []})
        )
        client = FlightApiClient("testkey")
        results = client.search_flights("JFK", "LAX", "2026-06-15", cabin_class="economy_plus")
        assert results == []

    @respx.mock
    def test_search_with_cabin_class_premium_economy(self):
        respx.get("https://api.flightapi.io/onewaytrip/testkey/JFK/LAX/2026-06-15/1/0/0/Premium_Economy/USD").mock(
            return_value=httpx.Response(200, json={"itineraries": [], "legs": [], "carriers": []})
        )
        client = FlightApiClient("testkey")
        results = client.search_flights("JFK", "LAX", "2026-06-15", cabin_class="premium_economy")
        assert results == []

    @respx.mock
    def test_search_with_cabin_class_first(self):
        respx.get("https://api.flightapi.io/onewaytrip/testkey/JFK/LAX/2026-06-15/1/0/0/First/USD").mock(
            return_value=httpx.Response(200, json={"itineraries": [], "legs": [], "carriers": []})
        )
        client = FlightApiClient("testkey")
        results = client.search_flights("JFK", "LAX", "2026-06-15", cabin_class="first")
        assert results == []

    @respx.mock
    def test_search_with_children_and_infants(self):
        respx.get("https://api.flightapi.io/onewaytrip/testkey/JFK/LAX/2026-06-15/2/1/1/Economy/USD").mock(
            return_value=httpx.Response(200, json={"itineraries": [], "legs": [], "carriers": []})
        )
        client = FlightApiClient("testkey")
        results = client.search_flights("JFK", "LAX", "2026-06-15", adults=2, children=1, infants=1)
        assert results == []

    @respx.mock
    def test_search_with_airline_filter(self):
        response = {
            "itineraries": [
                {
                    "id": "it1",
                    "leg_ids": ["leg1"],
                    "pricing_options": [{"price": {"amount": 300.0}}],
                },
                {
                    "id": "it2",
                    "leg_ids": ["leg2"],
                    "pricing_options": [{"price": {"amount": 500.0}}],
                },
            ],
            "legs": [
                {"id": "leg1", "marketing_carrier_ids": [1]},
                {"id": "leg2", "marketing_carrier_ids": [2]},
            ],
            "carriers": [
                {"id": 1, "alt_id": "AA"},
                {"id": 2, "alt_id": "UA"},
            ],
        }
        respx.get("https://api.flightapi.io/onewaytrip/testkey/JFK/LAX/2026-06-15/1/0/0/Economy/USD").mock(
            return_value=httpx.Response(200, json=response)
        )
        client = FlightApiClient("testkey")
        results = client.search_flights("JFK", "LAX", "2026-06-15", airline_codes=["AA"])
        assert len(results) == 1
        assert results[0]["airline"] == "AA"

    @respx.mock
    def test_search_http_error(self):
        respx.get("https://api.flightapi.io/onewaytrip/testkey/JFK/LAX/2026-06-15/1/0/0/Economy/USD").mock(
            return_value=httpx.Response(500, text="Server Error")
        )
        client = FlightApiClient("testkey")
        results = client.search_flights("JFK", "LAX", "2026-06-15")
        assert results == []

    @respx.mock
    def test_search_parse_error(self):
        respx.get("https://api.flightapi.io/onewaytrip/testkey/JFK/LAX/2026-06-15/1/0/0/Economy/USD").mock(
            return_value=httpx.Response(200, text="not json")
        )
        client = FlightApiClient("testkey")
        results = client.search_flights("JFK", "LAX", "2026-06-15")
        assert results == []

    @respx.mock
    def test_search_no_pricing_options(self):
        response = {
            "itineraries": [{"id": "it1", "leg_ids": ["leg1"], "pricing_options": []}],
            "legs": [{"id": "leg1", "marketing_carrier_ids": [1]}],
            "carriers": [{"id": 1, "alt_id": "AA"}],
        }
        respx.get("https://api.flightapi.io/onewaytrip/testkey/JFK/LAX/2026-06-15/1/0/0/Economy/USD").mock(
            return_value=httpx.Response(200, json=response)
        )
        client = FlightApiClient("testkey")
        results = client.search_flights("JFK", "LAX", "2026-06-15")
        assert results == []

    @respx.mock
    def test_search_no_carrier_ids_in_leg(self):
        response = {
            "itineraries": [
                {
                    "id": "it1",
                    "leg_ids": ["leg1"],
                    "pricing_options": [{"price": {"amount": 200.0}}],
                }
            ],
            "legs": [{"id": "leg1", "marketing_carrier_ids": []}],
            "carriers": [],
        }
        respx.get("https://api.flightapi.io/onewaytrip/testkey/JFK/LAX/2026-06-15/1/0/0/Economy/USD").mock(
            return_value=httpx.Response(200, json=response)
        )
        client = FlightApiClient("testkey")
        results = client.search_flights("JFK", "LAX", "2026-06-15")
        assert len(results) == 1
        assert results[0]["airline"] == "??"

    @respx.mock
    def test_search_no_leg_ids(self):
        response = {
            "itineraries": [
                {
                    "id": "it1",
                    "leg_ids": [],
                    "pricing_options": [{"price": {"amount": 200.0}}],
                }
            ],
            "legs": [],
            "carriers": [],
        }
        respx.get("https://api.flightapi.io/onewaytrip/testkey/JFK/LAX/2026-06-15/1/0/0/Economy/USD").mock(
            return_value=httpx.Response(200, json=response)
        )
        client = FlightApiClient("testkey")
        results = client.search_flights("JFK", "LAX", "2026-06-15")
        assert len(results) == 1
        assert results[0]["airline"] == "??"

    @respx.mock
    def test_search_carrier_uses_name_fallback(self):
        response = {
            "itineraries": [
                {
                    "id": "it1",
                    "leg_ids": ["leg1"],
                    "pricing_options": [{"price": {"amount": 300.0}}],
                }
            ],
            "legs": [{"id": "leg1", "marketing_carrier_ids": [1]}],
            "carriers": [{"id": 1, "name": "Delta"}],
        }
        respx.get("https://api.flightapi.io/onewaytrip/testkey/JFK/LAX/2026-06-15/1/0/0/Economy/USD").mock(
            return_value=httpx.Response(200, json=response)
        )
        client = FlightApiClient("testkey")
        results = client.search_flights("JFK", "LAX", "2026-06-15")
        assert results[0]["airline"] == "Delta"

    @respx.mock
    def test_search_with_currency(self):
        respx.get("https://api.flightapi.io/onewaytrip/testkey/JFK/LAX/2026-06-15/1/0/0/Economy/EUR").mock(
            return_value=httpx.Response(200, json={"itineraries": [], "legs": [], "carriers": []})
        )
        client = FlightApiClient("testkey")
        results = client.search_flights("JFK", "LAX", "2026-06-15", currency="EUR")
        assert results == []


class TestResolveAirlineCodes:
    def test_airlines_only(self):
        codes = FlightApiClient.resolve_airline_codes(["AA", "UA"], [])
        assert codes == ["AA", "UA"]

    def test_alliances_only(self):
        codes = FlightApiClient.resolve_airline_codes([], ["Star Alliance"])
        assert set(codes) == set(ALLIANCE_AIRLINES["Star Alliance"])

    def test_combined(self):
        codes = FlightApiClient.resolve_airline_codes(["QF"], ["oneworld"])
        assert "QF" in codes
        assert "AA" in codes

    def test_unknown_alliance(self):
        codes = FlightApiClient.resolve_airline_codes(["AA"], ["Unknown Alliance"])
        assert codes == ["AA"]

    def test_empty(self):
        codes = FlightApiClient.resolve_airline_codes([], [])
        assert codes == []

    def test_deduplication(self):
        codes = FlightApiClient.resolve_airline_codes(["AA"], ["oneworld"])
        assert codes.count("AA") == 1


class TestCabinTypeMap:
    def test_all_mappings(self):
        assert CABIN_TYPE_MAP["economy_plus"] == "Premium_Economy"
        assert CABIN_TYPE_MAP["premium_economy"] == "Premium_Economy"
        assert CABIN_TYPE_MAP["business"] == "Business"
        assert CABIN_TYPE_MAP["first"] == "First"
        assert CABIN_TYPE_MAP["economy"] == "Economy"
