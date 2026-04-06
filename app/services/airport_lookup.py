"""Resolve city names (e.g. 'Tokyo, Japan') to IATA airport codes."""

from __future__ import annotations

import airportsdata

# Load once at import time, keyed by IATA code
_AIRPORTS: dict[str, dict] = airportsdata.load("IATA")

# Build city index: lowercase city name → list of (iata, country_code)
_CITY_INDEX: dict[str, list[tuple[str, str]]] = {}
for _code, _info in _AIRPORTS.items():
    _city = _info.get("city", "").strip().lower()
    if _city and _code:
        _CITY_INDEX.setdefault(_city, []).append((_code, _info["country"]))

# Country name → ISO 2-letter code (common names + variations)
_COUNTRY_NAMES: dict[str, str] = {
    "afghanistan": "AF", "albania": "AL", "algeria": "DZ", "argentina": "AR",
    "armenia": "AM", "australia": "AU", "austria": "AT", "azerbaijan": "AZ",
    "bahamas": "BS", "bahrain": "BH", "bangladesh": "BD", "belarus": "BY",
    "belgium": "BE", "bolivia": "BO", "brazil": "BR", "brunei": "BN",
    "bulgaria": "BG", "cambodia": "KH", "cameroon": "CM", "canada": "CA",
    "chile": "CL", "china": "CN", "colombia": "CO", "costa rica": "CR",
    "croatia": "HR", "cuba": "CU", "cyprus": "CY", "czech republic": "CZ",
    "czechia": "CZ", "denmark": "DK", "dominican republic": "DO",
    "ecuador": "EC", "egypt": "EG", "el salvador": "SV", "estonia": "EE",
    "ethiopia": "ET", "fiji": "FJ", "finland": "FI", "france": "FR",
    "georgia": "GE", "germany": "DE", "ghana": "GH", "greece": "GR",
    "guatemala": "GT", "honduras": "HN", "hong kong": "HK", "hungary": "HU",
    "iceland": "IS", "india": "IN", "indonesia": "ID", "iran": "IR",
    "iraq": "IQ", "ireland": "IE", "israel": "IL", "italy": "IT",
    "jamaica": "JM", "japan": "JP", "jordan": "JO", "kazakhstan": "KZ",
    "kenya": "KE", "kuwait": "KW", "kyrgyzstan": "KG", "laos": "LA",
    "latvia": "LV", "lebanon": "LB", "libya": "LY", "lithuania": "LT",
    "luxembourg": "LU", "macau": "MO", "malaysia": "MY", "maldives": "MV",
    "malta": "MT", "mexico": "MX", "moldova": "MD", "mongolia": "MN",
    "montenegro": "ME", "morocco": "MA", "mozambique": "MZ", "myanmar": "MM",
    "namibia": "NA", "nepal": "NP", "netherlands": "NL", "new zealand": "NZ",
    "nicaragua": "NI", "nigeria": "NG", "north korea": "KP",
    "north macedonia": "MK", "norway": "NO", "oman": "OM", "pakistan": "PK",
    "panama": "PA", "paraguay": "PY", "peru": "PE", "philippines": "PH",
    "poland": "PL", "portugal": "PT", "qatar": "QA", "romania": "RO",
    "russia": "RU", "saudi arabia": "SA", "senegal": "SN", "serbia": "RS",
    "singapore": "SG", "slovakia": "SK", "slovenia": "SI",
    "south africa": "ZA", "south korea": "KR", "spain": "ES",
    "sri lanka": "LK", "sudan": "SD", "sweden": "SE", "switzerland": "CH",
    "syria": "SY", "taiwan": "TW", "tajikistan": "TJ", "tanzania": "TZ",
    "thailand": "TH", "trinidad and tobago": "TT", "tunisia": "TN",
    "turkey": "TR", "turkmenistan": "TM", "uganda": "UG", "ukraine": "UA",
    "united arab emirates": "AE", "uae": "AE",
    "united kingdom": "GB", "uk": "GB", "great britain": "GB", "england": "GB",
    "united states": "US", "usa": "US", "us": "US",
    "uruguay": "UY", "uzbekistan": "UZ", "venezuela": "VE", "vietnam": "VN",
    "yemen": "YE", "zambia": "ZM", "zimbabwe": "ZW",
    # Russian names
    "россия": "RU", "япония": "JP", "китай": "CN", "германия": "DE",
    "франция": "FR", "италия": "IT", "испания": "ES", "турция": "TR",
    "таиланд": "TH", "индия": "IN", "сша": "US", "канада": "CA",
    "австралия": "AU", "великобритания": "GB", "бразилия": "BR",
    "мексика": "MX", "аргентина": "AR", "египет": "EG", "оаэ": "AE",
    "южная корея": "KR", "сингапур": "SG", "малайзия": "MY",
    "индонезия": "ID", "вьетнам": "VN", "филиппины": "PH",
    "нидерланды": "NL", "голландия": "NL", "бельгия": "BE",
    "швейцария": "CH", "австрия": "AT", "польша": "PL", "чехия": "CZ",
    "греция": "GR", "португалия": "PT", "норвегия": "NO", "швеция": "SE",
    "финляндия": "FI", "дания": "DK", "ирландия": "IE", "израиль": "IL",
    "казахстан": "KZ", "узбекистан": "UZ", "грузия": "GE",
    "армения": "AM", "азербайджан": "AZ", "беларусь": "BY",
    "украина": "UA", "молдова": "MD", "куба": "CU",
}

# Also build reverse: ISO code → True for quick validation
_VALID_COUNTRY_CODES: set[str] = {info["country"] for info in _AIRPORTS.values()}


def _resolve_country(country_str: str) -> str | None:
    """Resolve a country name or code to ISO 2-letter code."""
    s = country_str.strip().lower()
    # Direct 2-letter code
    if len(s) == 2 and s.upper() in _VALID_COUNTRY_CODES:
        return s.upper()
    return _COUNTRY_NAMES.get(s)


def resolve_airport(value: str) -> str:
    """Resolve an IATA code or 'city, country' string to an IATA airport code.

    Accepts:
        - 3-letter IATA code (e.g. "JFK", "nrt")
        - "city, country" (e.g. "Tokyo, Japan" or "Tokyo, JP")

    Returns the uppercase IATA code.
    Raises ValueError if the input cannot be resolved.
    """
    value = value.strip()
    if not value:
        raise ValueError("Airport code or city name is required")

    # If it looks like a 3-letter IATA code, validate and return
    if len(value) <= 3 and value.isalpha():
        code = value.upper()
        if code in _AIRPORTS:
            return code
        raise ValueError(f"Unknown IATA code: {code}")

    # Parse "city, country" or just "city"
    parts = [p.strip() for p in value.split(",", maxsplit=1)]
    city_query = parts[0].lower()
    country_query = parts[1] if len(parts) > 1 else None

    if not city_query:
        raise ValueError("City name is required")

    candidates = _CITY_INDEX.get(city_query)
    if not candidates:
        raise ValueError(f"No airports found for city: {parts[0].strip()}")

    # Filter by country if provided
    if country_query:
        country_code = _resolve_country(country_query)
        if country_code is None:
            raise ValueError(f"Unknown country: {country_query.strip()}")
        filtered = [(iata, cc) for iata, cc in candidates if cc == country_code]
        if not filtered:
            raise ValueError(
                f"No airports found for {parts[0].strip()} in {country_query.strip()}"
            )
        candidates = filtered

    # Return the first match (airports are in insertion order from airportsdata)
    return candidates[0][0]
