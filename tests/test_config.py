from app.config import Settings, get_settings


class TestSettings:
    def test_defaults(self):
        s = Settings(
            FLIGHTAPI_KEY="",
            GROK_API_KEY="",
            TELEGRAM_BOT_TOKEN="",
            TELEGRAM_CHAT_ID="",
        )
        assert s.FLIGHTAPI_KEY == ""
        assert s.DATABASE_URL == "sqlite:///./track_flights.db"
        assert s.CHECK_INTERVAL_HOURS == 6

    def test_custom_values(self):
        s = Settings(
            FLIGHTAPI_KEY="fkey",
            GROK_API_KEY="grok",
            TELEGRAM_BOT_TOKEN="bot",
            TELEGRAM_CHAT_ID="123",
            DATABASE_URL="sqlite:///test.db",
            CHECK_INTERVAL_HOURS=12,
        )
        assert s.FLIGHTAPI_KEY == "fkey"
        assert s.DATABASE_URL == "sqlite:///test.db"
        assert s.CHECK_INTERVAL_HOURS == 12


class TestGetSettings:
    def test_get_settings_returns_instance(self):
        s = get_settings()
        assert isinstance(s, Settings)

    def test_get_settings_cached(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
