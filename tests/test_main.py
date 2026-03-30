from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app, lifespan


class TestAppSetup:
    def test_app_has_api_routes(self):
        route_paths = [route.path for route in app.routes]
        assert "/api/routes" in route_paths or any(
            "/api" in getattr(r, "path", "") for r in app.routes
        )

    def test_app_has_web_routes(self):
        route_paths = [getattr(r, "path", "") for r in app.routes]
        assert "/" in route_paths

    def test_app_has_static_mount(self):
        route_paths = [getattr(r, "path", "") for r in app.routes]
        assert "/static" in route_paths

    def test_app_title(self):
        assert app.title == "Flight Price Tracker"

    def test_docs_disabled(self):
        assert app.docs_url is None
        assert app.redoc_url is None
        assert app.openapi_url is None

    def test_app_has_auth_routes(self):
        route_paths = [getattr(r, "path", "") for r in app.routes]
        assert "/login" in route_paths
        assert "/logout" in route_paths
        assert "/auth/callback" in route_paths

    def test_all_api_endpoints_registered(self):
        paths = set()
        for route in app.routes:
            p = getattr(route, "path", "")
            if p:
                paths.add(p)
        expected = [
            "/api/routes",
            "/api/routes/{route_id}",
            "/api/routes/{route_id}/toggle",
            "/api/routes/{route_id}/check",
            "/api/routes/{route_id}/prices",
            "/api/routes/{route_id}/predictions",
            "/api/currency",
            "/",
            "/route/{route_id}",
            "/static",
            "/login",
            "/login/google",
            "/auth/callback",
            "/logout",
            "/profile",
        ]
        for ep in expected:
            assert ep in paths, f"Missing endpoint: {ep}"


class TestLoginRequiredHandler:
    def test_unauthenticated_request_redirects_to_login(self):
        """Covers the _LoginRequired exception handler in main.py."""

        @asynccontextmanager
        async def test_lifespan(app_instance: FastAPI):
            app_instance.state.price_tracker = MagicMock()
            yield

        original_lifespan = app.router.lifespan_context
        app.router.lifespan_context = test_lifespan
        # Do NOT override require_login -- let it raise _LoginRequired
        app.dependency_overrides.pop(
            __import__("app.routers.auth", fromlist=["require_login"]).require_login,
            None,
        )

        try:
            with TestClient(app) as c:
                resp = c.get("/", follow_redirects=False)
                assert resp.status_code == 302
                assert resp.headers["location"] == "/login"
        finally:
            app.dependency_overrides.clear()
            app.router.lifespan_context = original_lifespan


class TestLifespan:
    @pytest.mark.asyncio
    @patch("app.main.stop_scheduler")
    @patch("app.main.start_scheduler")
    @patch("app.main.TelegramNotifier")
    @patch("app.main.PricePredictor")
    @patch("app.main.GoogleFlightsClient")
    @patch("app.main.FlightApiClient")
    @patch("app.main.setup_oauth")
    @patch("app.main.Base")
    @patch("app.main.get_settings")
    @patch("app.schemas.fetch_exchange_rate", return_value=92.0)
    async def test_lifespan_startup_and_shutdown(
        self,
        mock_fetch_exchange_rate,
        mock_get_settings,
        mock_base,
        mock_setup_oauth,
        mock_flight_api_cls,
        mock_google_flights_cls,
        mock_predictor_cls,
        mock_notifier_cls,
        mock_start_scheduler,
        mock_stop_scheduler,
    ):
        settings = MagicMock()
        settings.FLIGHTAPI_KEY = "fkey"
        settings.SERPAPI_KEY = "serpkey"
        settings.GROK_API_KEY = "grok"
        settings.TELEGRAM_BOT_TOKEN = "bot"
        settings.TELEGRAM_CHAT_ID = "chat"
        settings.CHECK_INTERVAL_HOURS = 6
        mock_get_settings.return_value = settings

        mock_scheduler = MagicMock()
        mock_start_scheduler.return_value = mock_scheduler

        mock_app = MagicMock()
        mock_app.state = MagicMock()

        async with lifespan(mock_app):
            mock_base.metadata.create_all.assert_called_once()
            mock_setup_oauth.assert_called_once_with(settings)
            mock_flight_api_cls.assert_called_once_with("fkey")
            mock_google_flights_cls.assert_called_once_with("serpkey")
            mock_predictor_cls.assert_called_once_with("grok")
            mock_notifier_cls.assert_called_once_with("bot", "chat")
            mock_start_scheduler.assert_called_once()
            assert mock_app.state.price_tracker is not None
            assert mock_app.state.scheduler is mock_scheduler

        mock_stop_scheduler.assert_called_once_with(mock_scheduler)
        mock_fetch_exchange_rate.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.main.stop_scheduler")
    @patch("app.main.start_scheduler")
    @patch("app.main.TelegramNotifier")
    @patch("app.main.PricePredictor")
    @patch("app.main.GoogleFlightsClient")
    @patch("app.main.FlightApiClient")
    @patch("app.main.setup_oauth")
    @patch("app.main.Base")
    @patch("app.main.get_settings")
    @patch("app.schemas.fetch_exchange_rate", side_effect=Exception("network error"))
    async def test_lifespan_exchange_rate_failure(
        self,
        mock_fetch_exchange_rate,
        mock_get_settings,
        mock_base,
        mock_setup_oauth,
        mock_flight_api_cls,
        mock_google_flights_cls,
        mock_predictor_cls,
        mock_notifier_cls,
        mock_start_scheduler,
        mock_stop_scheduler,
    ):
        settings = MagicMock()
        settings.FLIGHTAPI_KEY = "fkey"
        settings.SERPAPI_KEY = ""
        settings.GROK_API_KEY = "grok"
        settings.TELEGRAM_BOT_TOKEN = "bot"
        settings.TELEGRAM_CHAT_ID = "chat"
        settings.CHECK_INTERVAL_HOURS = 6
        mock_get_settings.return_value = settings

        mock_scheduler = MagicMock()
        mock_start_scheduler.return_value = mock_scheduler

        mock_app = MagicMock()
        mock_app.state = MagicMock()

        # Should not raise even though fetch_exchange_rate raises
        async with lifespan(mock_app):
            pass

        mock_stop_scheduler.assert_called_once_with(mock_scheduler)


class TestCSRFMiddleware:
    """Tests for the CSRF middleware in main.py."""

    def _setup_app(self):
        """Set up test lifespan and auth bypass, return original lifespan for cleanup."""
        from app.routers.auth import require_login

        @asynccontextmanager
        async def test_lifespan(app_instance: FastAPI):
            app_instance.state.price_tracker = MagicMock()
            yield

        original_lifespan = app.router.lifespan_context
        app.router.lifespan_context = test_lifespan
        fake_user = {"email": "test@example.com", "name": "Test", "picture": ""}
        app.dependency_overrides[require_login] = lambda: fake_user
        return original_lifespan

    def test_post_without_csrf_token_returns_403(self):
        """A POST without the CSRF header should be rejected with 403."""
        original_lifespan = self._setup_app()
        try:
            with TestClient(app, raise_server_exceptions=False) as c:
                c.cookies.set("csrf_token", "some-token")
                resp = c.post("/logout")
                assert resp.status_code == 403
                assert "CSRF" in resp.json()["detail"]
        finally:
            app.dependency_overrides.clear()
            app.router.lifespan_context = original_lifespan

    def test_post_with_valid_csrf_token_passes(self):
        """A POST with matching CSRF cookie and header should succeed."""
        original_lifespan = self._setup_app()
        try:
            with TestClient(app, raise_server_exceptions=False) as c:
                token = "valid-test-token"
                c.cookies.set("csrf_token", token)
                c.headers.update({"x-csrf-token": token})
                resp = c.post("/logout", follow_redirects=False)
                assert resp.status_code == 302
        finally:
            app.dependency_overrides.clear()
            app.router.lifespan_context = original_lifespan

    def test_get_sets_csrf_cookie(self):
        """A GET request should always have csrf_token cookie set in response."""
        original_lifespan = self._setup_app()
        try:
            with TestClient(app, raise_server_exceptions=False) as c:
                resp = c.get("/login")
                assert "csrf_token" in resp.cookies
        finally:
            app.dependency_overrides.clear()
            app.router.lifespan_context = original_lifespan

    def test_get_without_csrf_cookie_generates_new_one(self):
        """A GET without existing csrf cookie generates a new token (covers line 77)."""
        original_lifespan = self._setup_app()
        try:
            with TestClient(app, raise_server_exceptions=False, cookies={}) as c:
                resp = c.get("/login")
                assert resp.status_code == 200
                assert "csrf_token" in resp.cookies
                assert len(resp.cookies["csrf_token"]) == 64
        finally:
            app.dependency_overrides.clear()
            app.router.lifespan_context = original_lifespan

    def test_csrf_exempt_path_callback(self):
        """Requests to /auth/callback should bypass CSRF check."""
        original_lifespan = self._setup_app()
        try:
            with TestClient(app, raise_server_exceptions=False) as c:
                resp = c.get("/auth/callback")
                assert resp.status_code != 403
        finally:
            app.dependency_overrides.clear()
            app.router.lifespan_context = original_lifespan
