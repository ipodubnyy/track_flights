from datetime import datetime, timedelta

import httpx
import respx

from app.services.amadeus_client import (
    ALLIANCE_AIRLINES,
    CABIN_TYPE_MAP,
    AmadeusClient,
)


class TestAuthenticate:
    @respx.mock
    def test_authenticate_success(self):
        respx.post(AmadeusClient.AUTH_URL).mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "test-token-123", "expires_in": 1799},
            )
        )
        client = AmadeusClient("key", "secret")
        client._authenticate()
        assert client.token == "test-token-123"
        assert client.token_expires is not None

    @respx.mock
    def test_authenticate_default_expires(self):
        respx.post(AmadeusClient.AUTH_URL).mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "tok"},
            )
        )
        client = AmadeusClient("key", "secret")
        client._authenticate()
        assert client.token == "tok"
        assert client.token_expires is not None


class TestGetToken:
    @respx.mock
    def test_get_token_no_cache(self):
        respx.post(AmadeusClient.AUTH_URL).mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "fresh-token", "expires_in": 1799},
            )
        )
        client = AmadeusClient("key", "secret")
        token = client._get_token()
        assert token == "fresh-token"

    @respx.mock
    def test_get_token_cached(self):
        client = AmadeusClient("key", "secret")
        client.token = "cached-token"
        client.token_expires = datetime.utcnow() + timedelta(minutes=10)
        token = client._get_token()
        assert token == "cached-token"

    @respx.mock
    def test_get_token_expired(self):
        respx.post(AmadeusClient.AUTH_URL).mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "new-token", "expires_in": 1799},
            )
        )
        client = AmadeusClient("key", "secret")
        client.token = "old-token"
        client.token_expires = datetime.utcnow() - timedelta(minutes=1)
        token = client._get_token()
        assert token == "new-token"


class TestSearchFlights:
    @respx.mock
    def test_search_flights_basic(self):
        respx.post(AmadeusClient.AUTH_URL).mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "tok", "expires_in": 1799},
            )
        )
        respx.get(AmadeusClient.SEARCH_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "price": {"total": "450.00", "currency": "USD"},
                            "itineraries": [
                                {
                                    "segments": [
                                        {"carrierCode": "AA"}
                                    ]
                                }
                            ],
                        }
                    ]
                },
            )
        )
        client = AmadeusClient("key", "secret")
        results = client.search_flights("JFK", "LAX", "2026-06-15")
        assert len(results) == 1
        assert results[0]["airline"] == "AA"
        assert results[0]["price"] == 450.0
        assert results[0]["currency"] == "USD"
        assert results[0]["cabin_type"] == "economy"

    @respx.mock
    def test_search_flights_with_cabin_class_mapped(self):
        respx.post(AmadeusClient.AUTH_URL).mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "tok", "expires_in": 1799},
            )
        )
        respx.get(AmadeusClient.SEARCH_URL).mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        client = AmadeusClient("key", "secret")
        results = client.search_flights(
            "JFK", "LAX", "2026-06-15", cabin_class="business"
        )
        assert results == []
        # Verify travelClass was sent
        req = respx.calls.last.request
        assert "travelClass=BUSINESS" in str(req.url)

    @respx.mock
    def test_search_flights_with_cabin_class_unmapped(self):
        respx.post(AmadeusClient.AUTH_URL).mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "tok", "expires_in": 1799},
            )
        )
        respx.get(AmadeusClient.SEARCH_URL).mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        client = AmadeusClient("key", "secret")
        results = client.search_flights(
            "JFK", "LAX", "2026-06-15", cabin_class="first"
        )
        req = respx.calls.last.request
        assert "travelClass=FIRST" in str(req.url)

    @respx.mock
    def test_search_flights_with_airline_codes(self):
        respx.post(AmadeusClient.AUTH_URL).mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "tok", "expires_in": 1799},
            )
        )
        respx.get(AmadeusClient.SEARCH_URL).mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        client = AmadeusClient("key", "secret")
        results = client.search_flights(
            "JFK", "LAX", "2026-06-15", airline_codes=["AA", "UA"]
        )
        req = respx.calls.last.request
        assert "includedAirlineCodes=AA%2CUA" in str(req.url)

    @respx.mock
    def test_search_flights_no_segments(self):
        respx.post(AmadeusClient.AUTH_URL).mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "tok", "expires_in": 1799},
            )
        )
        respx.get(AmadeusClient.SEARCH_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "price": {"total": "100.00", "currency": "EUR"},
                            "itineraries": [{"segments": []}],
                        }
                    ]
                },
            )
        )
        client = AmadeusClient("key", "secret")
        results = client.search_flights("JFK", "LAX", "2026-06-15")
        assert results[0]["airline"] == "??"

    @respx.mock
    def test_search_flights_missing_price(self):
        respx.post(AmadeusClient.AUTH_URL).mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "tok", "expires_in": 1799},
            )
        )
        respx.get(AmadeusClient.SEARCH_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "price": {},
                            "itineraries": [{}],
                        }
                    ]
                },
            )
        )
        client = AmadeusClient("key", "secret")
        results = client.search_flights("JFK", "LAX", "2026-06-15")
        assert results[0]["price"] == 0.0
        assert results[0]["currency"] == "USD"
        assert results[0]["airline"] == "??"

    @respx.mock
    def test_search_flights_http_error(self):
        respx.post(AmadeusClient.AUTH_URL).mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "tok", "expires_in": 1799},
            )
        )
        respx.get(AmadeusClient.SEARCH_URL).mock(
            return_value=httpx.Response(500, text="Server Error")
        )
        client = AmadeusClient("key", "secret")
        results = client.search_flights("JFK", "LAX", "2026-06-15")
        assert results == []

    @respx.mock
    def test_search_flights_parse_error(self):
        respx.post(AmadeusClient.AUTH_URL).mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "tok", "expires_in": 1799},
            )
        )
        respx.get(AmadeusClient.SEARCH_URL).mock(
            return_value=httpx.Response(200, text="not json")
        )
        client = AmadeusClient("key", "secret")
        results = client.search_flights("JFK", "LAX", "2026-06-15")
        assert results == []


class TestResolveAirlineCodes:
    def test_airlines_only(self):
        codes = AmadeusClient.resolve_airline_codes(["AA", "UA"], [])
        assert codes == ["AA", "UA"]

    def test_alliances_only(self):
        codes = AmadeusClient.resolve_airline_codes([], ["Star Alliance"])
        assert set(codes) == set(ALLIANCE_AIRLINES["Star Alliance"])

    def test_combined(self):
        codes = AmadeusClient.resolve_airline_codes(["QF"], ["oneworld"])
        assert "QF" in codes
        assert "AA" in codes  # from oneworld

    def test_unknown_alliance(self):
        codes = AmadeusClient.resolve_airline_codes(["AA"], ["Unknown Alliance"])
        assert codes == ["AA"]

    def test_empty(self):
        codes = AmadeusClient.resolve_airline_codes([], [])
        assert codes == []

    def test_deduplication(self):
        # AA is in oneworld alliance
        codes = AmadeusClient.resolve_airline_codes(["AA"], ["oneworld"])
        assert codes.count("AA") == 1
