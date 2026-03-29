from __future__ import annotations

import logging
from datetime import datetime, timedelta

import httpx

logger = logging.getLogger(__name__)

CABIN_TYPE_MAP = {
    "economy_plus": "PREMIUM_ECONOMY",
    "premium_economy": "PREMIUM_ECONOMY",
    "business": "BUSINESS",
}

ALLIANCE_AIRLINES: dict[str, list[str]] = {
    "Star Alliance": [
        "UA", "LH", "NH", "AC", "TK", "SQ", "AV", "ET", "SK", "OS", "LO", "TP", "MS",
    ],
    "oneworld": [
        "AA", "BA", "QF", "CX", "JL", "IB", "AY", "MH", "QR", "RJ", "AT",
    ],
    "SkyTeam": [
        "DL", "AF", "KL", "KE", "AM", "AR", "CI", "CZ", "SU", "VN", "ME",
    ],
}


class AmadeusClient:
    AUTH_URL = "https://api.amadeus.com/v1/security/oauth2/token"
    SEARCH_URL = "https://api.amadeus.com/v2/shopping/flight-offers"

    def __init__(self, api_key: str, api_secret: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.token: str | None = None
        self.token_expires: datetime | None = None

    def _authenticate(self) -> None:
        with httpx.Client() as client:
            response = client.post(
                self.AUTH_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.api_key,
                    "client_secret": self.api_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            data = response.json()
            self.token = data["access_token"]
            expires_in = data.get("expires_in", 1799)
            self.token_expires = datetime.utcnow() + timedelta(seconds=expires_in - 60)

    def _get_token(self) -> str:
        if self.token is None or (
            self.token_expires and datetime.utcnow() >= self.token_expires
        ):
            self._authenticate()
        return self.token  # type: ignore[return-value]

    @staticmethod
    def resolve_airline_codes(
        airlines: list[str], alliances: list[str]
    ) -> list[str]:
        codes: set[str] = set(airlines)
        for alliance in alliances:
            codes.update(ALLIANCE_AIRLINES.get(alliance, []))
        return sorted(codes)

    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        adults: int = 1,
        cabin_class: str | None = None,
        airline_codes: list[str] | None = None,
    ) -> list[dict]:
        token = self._get_token()
        params: dict = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "adults": adults,
            "max": 20,
        }
        if cabin_class:
            amadeus_class = CABIN_TYPE_MAP.get(cabin_class, cabin_class.upper())
            params["travelClass"] = amadeus_class
        if airline_codes:
            params["includedAirlineCodes"] = ",".join(airline_codes)

        results: list[dict] = []
        try:
            with httpx.Client() as client:
                response = client.get(
                    self.SEARCH_URL,
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

            for offer in data.get("data", []):
                price = float(offer.get("price", {}).get("total", 0))
                currency = offer.get("price", {}).get("currency", "USD")
                # Extract airline from first segment
                segments = (
                    offer.get("itineraries", [{}])[0].get("segments", [])
                )
                airline = segments[0].get("carrierCode", "??") if segments else "??"
                cabin = cabin_class or "economy"
                results.append(
                    {
                        "airline": airline,
                        "price": price,
                        "currency": currency,
                        "cabin_type": cabin,
                    }
                )
        except Exception:
            logger.exception("Amadeus flight search failed")

        return results
