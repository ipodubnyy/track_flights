import pytest

from app.services.airport_lookup import resolve_airport, _resolve_country


class TestResolveAirport:
    """Tests for the resolve_airport function."""

    # --- IATA code input ---

    def test_valid_iata_uppercase(self):
        assert resolve_airport("JFK") == "JFK"

    def test_valid_iata_lowercase(self):
        assert resolve_airport("jfk") == "JFK"

    def test_valid_iata_mixed_case(self):
        assert resolve_airport("Nrt") == "NRT"

    def test_valid_iata_with_whitespace(self):
        assert resolve_airport("  SFO  ") == "SFO"

    def test_unknown_iata_code(self):
        with pytest.raises(ValueError, match="Unknown IATA code: ZZZ"):
            resolve_airport("ZZZ")

    # --- City name input ---

    def test_city_with_country_name(self):
        result = resolve_airport("Tokyo, Japan")
        assert result in ("NRT", "HND")  # Tokyo has multiple airports

    def test_city_with_country_code(self):
        result = resolve_airport("Moscow, RU")
        assert result in ("SVO", "DME", "VKO", "ZIA", "BKA")

    def test_city_without_country(self):
        result = resolve_airport("London")
        assert len(result) == 3  # Returns some London airport

    def test_city_case_insensitive(self):
        result = resolve_airport("TOKYO, JAPAN")
        assert result in ("NRT", "HND")

    def test_city_with_whitespace(self):
        result = resolve_airport("  Tokyo ,  Japan  ")
        assert result in ("NRT", "HND")

    def test_city_russian_country_name(self):
        result = resolve_airport("Moscow, Россия")
        assert result in ("SVO", "DME", "VKO", "ZIA", "BKA")

    # --- Error cases ---

    def test_empty_string(self):
        with pytest.raises(ValueError, match="Airport code or city name is required"):
            resolve_airport("")

    def test_whitespace_only(self):
        with pytest.raises(ValueError, match="Airport code or city name is required"):
            resolve_airport("   ")

    def test_unknown_city(self):
        with pytest.raises(ValueError, match="No airports found for city"):
            resolve_airport("Xyzzyville")

    def test_unknown_country(self):
        with pytest.raises(ValueError, match="Unknown country"):
            resolve_airport("Tokyo, Atlantis")

    def test_city_not_in_country(self):
        with pytest.raises(ValueError, match="No airports found for"):
            resolve_airport("Tokyo, France")

    def test_empty_city_with_comma(self):
        with pytest.raises(ValueError, match="City name is required"):
            resolve_airport(", Japan")


class TestResolveCountry:
    """Tests for the _resolve_country helper."""

    def test_iso_code(self):
        assert _resolve_country("US") == "US"

    def test_iso_code_lowercase(self):
        assert _resolve_country("us") == "US"

    def test_country_name(self):
        assert _resolve_country("Japan") == "JP"

    def test_country_name_lowercase(self):
        assert _resolve_country("japan") == "JP"

    def test_country_alias(self):
        assert _resolve_country("USA") == "US"

    def test_country_alias_uk(self):
        assert _resolve_country("UK") == "GB"

    def test_russian_country_name(self):
        assert _resolve_country("Россия") == "RU"

    def test_unknown_country(self):
        assert _resolve_country("Atlantis") is None

    def test_whitespace(self):
        assert _resolve_country("  Japan  ") == "JP"


class TestSchemaIntegration:
    """Test that RouteCreate schema uses the airport resolver."""

    def test_create_route_with_iata(self):
        from app.schemas import RouteCreate

        route = RouteCreate(
            origin="JFK",
            destination="LAX",
            departure_date="2026-06-15",
        )
        assert route.origin == "JFK"
        assert route.destination == "LAX"

    def test_create_route_with_city_name(self):
        from app.schemas import RouteCreate

        route = RouteCreate(
            origin="Tokyo, Japan",
            destination="San Francisco, US",
            departure_date="2026-06-15",
        )
        assert route.origin in ("NRT", "HND")
        assert route.destination == "SFO"

    def test_create_route_invalid_city(self):
        from app.schemas import RouteCreate

        with pytest.raises(Exception):
            RouteCreate(
                origin="Xyzzyville",
                destination="LAX",
                departure_date="2026-06-15",
            )
