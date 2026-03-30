from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

# SerpAPI travel_class mapping
CABIN_CLASS_MAP = {
    "economy": 1,
    "economy_plus": 2,
    "premium_economy": 2,
    "business": 3,
    "first": 4,
}

# Reverse: SerpAPI travel_class int -> our cabin key
CABIN_CLASS_REVERSE = {1: "economy", 2: "premium_economy", 3: "business", 4: "first"}


class GoogleFlightsClient:
    BASE_URL = "https://serpapi.com/search"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        cabin_class: str | None = None,
        airline_codes: list[str] | None = None,
        return_date: str | None = None,
        currency: str = "USD",
    ) -> list[dict]:
        travel_class = CABIN_CLASS_MAP.get(cabin_class or "economy", 1)
        trip_type = 1 if return_date else 2  # 1=round trip, 2=one way

        params: dict = {
            "engine": "google_flights",
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": departure_date,
            "travel_class": travel_class,
            "adults": adults,
            "children": children,
            "infants_in_seat": 0,
            "infants_on_lap": infants,
            "currency": currency,
            "type": trip_type,
            "api_key": self.api_key,
        }
        if return_date:
            params["return_date"] = return_date

        results: list[dict] = []
        try:
            with httpx.Client() as client:
                response = client.get(self.BASE_URL, params=params, timeout=60.0)
                response.raise_for_status()
                data = response.json()

            results = self._parse_response(
                data, cabin_class or "economy", airline_codes, currency
            )
        except Exception:
            logger.exception("Google Flights (SerpAPI) search failed")

        return results

    def _parse_response(
        self,
        data: dict,
        cabin_type: str,
        airline_codes: list[str] | None,
        currency: str = "USD",
    ) -> list[dict]:
        results: list[dict] = []

        # SerpAPI returns best_flights and other_flights
        all_flights = data.get("best_flights", []) + data.get("other_flights", [])

        for flight_group in all_flights:
            price = flight_group.get("price")
            if not price:
                continue

            flights = flight_group.get("flights", [])
            if not flights:
                continue

            # Extract airline from first leg
            first_leg = flights[0]
            airline_code = first_leg.get("airline", "??")
            # SerpAPI sometimes returns full name; try to get from flight_number
            flight_number = first_leg.get("flight_number", "")
            if flight_number and len(flight_number) >= 2:
                # Flight number like "UA 123" or "UA123"
                code_part = flight_number.replace(" ", "")
                extracted = ""
                for ch in code_part:
                    if ch.isalpha():
                        extracted += ch
                    else:
                        break
                if 2 <= len(extracted) <= 3:
                    airline_code = extracted

            # Apply airline filter
            if airline_codes and airline_code not in airline_codes:
                continue

            # Build flight info
            flight_parts = []
            via_airports = []
            for i, leg in enumerate(flights):
                fn = leg.get("flight_number", "")
                if fn:
                    flight_parts.append(fn.replace(" ", ""))
                # Intermediate stops are layover airports
                if i < len(flights) - 1:
                    arr_airport = leg.get("arrival_airport", {})
                    via_code = arr_airport.get("id", arr_airport.get("name", ""))
                    if via_code:
                        via_airports.append(via_code)

            flight_str = ", ".join(flight_parts)
            if via_airports:
                flight_str += " via " + ", ".join(via_airports)

            results.append(
                {
                    "airline": airline_code,
                    "price": float(price),
                    "currency": currency,
                    "cabin_type": cabin_type,
                    "flight_info": flight_str,
                    "source": "google_flights",
                }
            )

        return results
