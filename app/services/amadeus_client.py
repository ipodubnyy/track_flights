from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

CABIN_TYPE_MAP = {
    "economy_plus": "Premium_Economy",
    "premium_economy": "Premium_Economy",
    "business": "Business",
    "first": "First",
    "economy": "Economy",
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


class FlightApiClient:
    BASE_URL = "https://api.flightapi.io"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

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
        children: int = 0,
        infants: int = 0,
        cabin_class: str | None = None,
        airline_codes: list[str] | None = None,
        return_date: str | None = None,
        currency: str = "USD",
    ) -> list[dict]:
        cabin = CABIN_TYPE_MAP.get(cabin_class or "economy", "Economy")

        if return_date:
            url = (
                f"{self.BASE_URL}/roundtrip/{self.api_key}"
                f"/{origin}/{destination}/{departure_date}/{return_date}"
                f"/{adults}/{children}/{infants}/{cabin}/{currency}"
            )
        else:
            url = (
                f"{self.BASE_URL}/onewaytrip/{self.api_key}"
                f"/{origin}/{destination}/{departure_date}"
                f"/{adults}/{children}/{infants}/{cabin}/{currency}"
            )

        results: list[dict] = []
        try:
            with httpx.Client() as client:
                response = client.get(url, timeout=60.0)
                response.raise_for_status()
                data = response.json()

            results = self._parse_response(data, cabin_class or "economy", airline_codes, currency)
        except Exception:
            logger.exception("FlightAPI search failed")

        return results

    def _parse_response(
        self, data: dict, cabin_type: str, airline_codes: list[str] | None, currency: str = "USD"
    ) -> list[dict]:
        carriers = {c["id"]: c for c in data.get("carriers", [])}
        legs = {leg["id"]: leg for leg in data.get("legs", [])}
        segments = {s["id"]: s for s in data.get("segments", [])}
        places = {p["id"]: p for p in data.get("places", [])}

        results: list[dict] = []
        for itin in data.get("itineraries", []):
            pricing_options = itin.get("pricing_options", [])
            if not pricing_options:
                continue

            cheapest = pricing_options[0]
            price_amount = cheapest.get("price", {}).get("amount", 0)

            leg_ids = itin.get("leg_ids", [])
            airline_code = "??"
            if leg_ids:
                leg = legs.get(leg_ids[0], {})
                carrier_ids = leg.get("marketing_carrier_ids", [])
                if carrier_ids:
                    carrier = carriers.get(carrier_ids[0], {})
                    airline_code = carrier.get("alt_id", carrier.get("name", "??"))

            if airline_codes and airline_code not in airline_codes:
                continue

            # Extract flight info from segments
            flight_parts = []
            via_airports = []
            if leg_ids:
                leg = legs.get(leg_ids[0], {})
                seg_ids = leg.get("segment_ids", [])
                for sid in seg_ids:
                    seg = segments.get(sid, {})
                    carrier_id = seg.get("marketing_carrier_id")
                    flight_num = seg.get("marketing_flight_number", "")
                    carrier_code = ""
                    if carrier_id and carrier_id in carriers:
                        carrier_code = carriers[carrier_id].get("alt_id", "")
                    if carrier_code and flight_num:
                        flight_parts.append(f"{carrier_code}{flight_num}")
                    # If multiple segments, intermediate destinations are "via" points
                    if len(seg_ids) > 1:
                        dest_id = seg.get("destination_place_id")
                        if dest_id and dest_id in places:
                            place = places[dest_id]
                            via_airports.append(place.get("alt_id", place.get("name", "")))
                # Remove final destination from via list (it's not a stop)
                if via_airports:
                    via_airports = via_airports[:-1]

            flight_str = ", ".join(flight_parts)
            if via_airports:
                flight_str += " via " + ", ".join(via_airports)

            results.append({
                "airline": airline_code,
                "price": float(price_amount),
                "currency": currency,
                "cabin_type": cabin_type,
                "flight_info": flight_str,
            })

        return results
