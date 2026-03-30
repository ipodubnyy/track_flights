from datetime import date
from unittest.mock import MagicMock

import httpx
import respx

from app.services.notifier import TelegramNotifier


class TestSendMessage:
    @respx.mock
    def test_send_message_success(self):
        respx.post("https://api.telegram.org/botTEST_TOKEN/sendMessage").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        notifier = TelegramNotifier("TEST_TOKEN", "12345")
        result = notifier.send_message("Hello!")
        assert result is True

    def test_send_message_missing_token(self):
        notifier = TelegramNotifier("", "12345")
        result = notifier.send_message("Hello!")
        assert result is False

    def test_send_message_missing_chat_id(self):
        notifier = TelegramNotifier("TOKEN", "")
        result = notifier.send_message("Hello!")
        assert result is False

    def test_send_message_both_missing(self):
        notifier = TelegramNotifier("", "")
        result = notifier.send_message("Hello!")
        assert result is False

    @respx.mock
    def test_send_message_api_error(self):
        respx.post("https://api.telegram.org/botTOKEN/sendMessage").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        notifier = TelegramNotifier("TOKEN", "12345")
        result = notifier.send_message("Hello!")
        assert result is False

    @respx.mock
    def test_send_message_network_error(self):
        respx.post("https://api.telegram.org/botTOKEN/sendMessage").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        notifier = TelegramNotifier("TOKEN", "12345")
        result = notifier.send_message("Hello!")
        assert result is False


class TestFormatPriceAlert:
    def test_format_with_return_date(self):
        route = MagicMock()
        route.origin = "JFK"
        route.destination = "LAX"
        route.departure_date = date(2026, 6, 15)
        route.return_date = date(2026, 6, 22)

        prices = [
            {"airline": "AA", "cabin_type": "economy", "price": 350.0, "currency": "USD"},
        ]
        prediction = {
            "trend": "down",
            "summary": "Prices falling",
            "buy_recommendation": "wait",
            "predicted_best_buy_date": "2026-05-01",
            "confidence": 0.85,
        }

        notifier = TelegramNotifier("", "")
        msg = notifier.format_price_alert(route, prices, prediction)

        assert "JFK -> LAX" in msg
        assert "2026-06-15" in str(msg)
        assert "<b>Return:</b>" in msg
        assert "AA" in msg
        assert "350" in msg
        assert "Falling" in msg
        assert "Prices falling" in msg
        assert "wait" in msg
        assert "2026-05-01" in msg
        assert "85%" in msg

    def test_format_without_return_date(self):
        route = MagicMock()
        route.origin = "SFO"
        route.destination = "LHR"
        route.departure_date = date(2026, 7, 1)
        route.return_date = None

        prices = []
        prediction = {
            "trend": "up",
            "summary": "Going up",
            "buy_recommendation": "buy now",
            "confidence": 0.6,
        }

        notifier = TelegramNotifier("", "")
        msg = notifier.format_price_alert(route, prices, prediction)

        assert "SFO -> LHR" in msg
        assert "<b>Return:</b>" not in msg
        assert "Rising" in msg
        assert "Best buy date" not in msg

    def test_format_stable_trend(self):
        route = MagicMock()
        route.origin = "A"
        route.destination = "B"
        route.departure_date = date(2026, 1, 1)
        route.return_date = None

        prediction = {"trend": "stable", "summary": "ok", "buy_recommendation": "uncertain", "confidence": 0.5}
        notifier = TelegramNotifier("", "")
        msg = notifier.format_price_alert(route, [], prediction)
        assert "Stable" in msg

    def test_format_unknown_trend(self):
        route = MagicMock()
        route.origin = "A"
        route.destination = "B"
        route.departure_date = date(2026, 1, 1)
        route.return_date = None

        prediction = {"trend": "unknown_value", "summary": "ok", "buy_recommendation": "uncertain", "confidence": 0.0}
        notifier = TelegramNotifier("", "")
        msg = notifier.format_price_alert(route, [], prediction)
        # unknown trend falls through to itself
        assert "unknown_value" in msg

    def test_format_with_missing_price_fields(self):
        route = MagicMock()
        route.origin = "A"
        route.destination = "B"
        route.departure_date = date(2026, 1, 1)
        route.return_date = None

        prices = [{}]
        prediction = {"trend": "stable", "summary": "ok", "buy_recommendation": "uncertain", "confidence": 0.0}
        notifier = TelegramNotifier("", "")
        msg = notifier.format_price_alert(route, prices, prediction)
        assert "??" in msg
        assert "0" in msg

    def test_format_with_google_flights_source(self):
        route = MagicMock()
        route.origin = "JFK"
        route.destination = "FRA"
        route.departure_date = date(2026, 6, 15)
        route.return_date = None

        prices = [
            {
                "airline": "UA",
                "cabin_type": "economy",
                "price": 500.0,
                "currency": "USD",
                "source": "google_flights",
            },
        ]
        prediction = {"trend": "stable", "summary": "ok", "buy_recommendation": "uncertain", "confidence": 0.5}
        notifier = TelegramNotifier("", "")
        msg = notifier.format_price_alert(route, prices, prediction)
        assert "[G]" in msg

    def test_format_with_flight_info_and_departure_date(self):
        route = MagicMock()
        route.origin = "JFK"
        route.destination = "LAX"
        route.departure_date = date(2026, 6, 15)
        route.return_date = None

        prices = [
            {
                "airline": "UA",
                "cabin_type": "economy",
                "price": 400.0,
                "currency": "USD",
                "flight_info": "UA123 via ORD",
                "departure_date": "2026-06-15",
            },
        ]
        prediction = {"trend": "down", "summary": "ok", "buy_recommendation": "wait", "confidence": 0.7}
        notifier = TelegramNotifier("", "")
        msg = notifier.format_price_alert(route, prices, prediction)
        assert "(UA123 via ORD)" in msg
        assert "[dep 2026-06-15]" in msg
