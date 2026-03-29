from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.routers.auth import (
    _LoginRequired,
    get_current_user,
    require_login,
    router,
    setup_oauth,
)


class TestGetCurrentUser:
    def test_returns_user_from_session(self):
        request = MagicMock(spec=Request)
        request.session = {"user": {"email": "a@b.com", "name": "A"}}
        assert get_current_user(request) == {"email": "a@b.com", "name": "A"}

    def test_returns_none_when_no_user(self):
        request = MagicMock(spec=Request)
        request.session = {}
        assert get_current_user(request) is None


class TestRequireLogin:
    def test_returns_user_when_logged_in(self):
        request = MagicMock(spec=Request)
        request.session = {"user": {"email": "a@b.com", "name": "A"}}
        user = require_login(request)
        assert user["email"] == "a@b.com"

    def test_raises_when_not_logged_in(self):
        request = MagicMock(spec=Request)
        request.session = {}
        with pytest.raises(_LoginRequired):
            require_login(request)


class TestSetupOauth:
    @patch("app.routers.auth.oauth")
    def test_registers_google(self, mock_oauth):
        settings = MagicMock()
        settings.GOOGLE_CLIENT_ID = "cid"
        settings.GOOGLE_CLIENT_SECRET = "csec"
        setup_oauth(settings)
        mock_oauth.register.assert_called_once()
        call_kwargs = mock_oauth.register.call_args[1]
        assert call_kwargs["name"] == "google"
        assert call_kwargs["client_id"] == "cid"
        assert call_kwargs["client_secret"] == "csec"


class TestLoginPage:
    def _make_app(self):
        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key="test-secret")
        app.include_router(router)
        return app

    def test_login_page_renders(self):
        app = self._make_app()
        with TestClient(app) as c:
            resp = c.get("/login")
            assert resp.status_code == 200
            assert "Sign in with Google" in resp.text

    @patch("app.routers.auth.oauth")
    def test_login_page_redirects_when_logged_in(self, mock_oauth):
        mock_google = AsyncMock()
        mock_google.authorize_access_token = AsyncMock(
            return_value={
                "userinfo": {"email": "a@b.com", "name": "A", "picture": ""}
            }
        )
        mock_oauth.google = mock_google

        app = self._make_app()
        app.dependency_overrides[get_settings] = lambda: MagicMock(ALLOWED_EMAILS="")
        with TestClient(app) as c:
            # First, establish session via callback
            c.get("/auth/callback", follow_redirects=False)
            # Now /login should redirect to /
            resp = c.get("/login", follow_redirects=False)
            assert resp.status_code == 302
            assert resp.headers["location"] == "/"
        app.dependency_overrides.clear()


class TestLoginGoogle:
    def _make_app(self):
        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key="test-secret")
        app.include_router(router)
        return app

    @patch("app.routers.auth.oauth")
    def test_login_google_redirects(self, mock_oauth):
        from starlette.responses import RedirectResponse

        mock_google = AsyncMock()
        mock_google.authorize_redirect = AsyncMock(
            return_value=RedirectResponse(url="https://accounts.google.com/o/oauth2/auth")
        )
        mock_oauth.google = mock_google

        app = self._make_app()
        mock_settings = MagicMock()
        mock_settings.BASE_URL = "https://flights.cattom.net:5498"
        app.dependency_overrides[get_settings] = lambda: mock_settings
        with TestClient(app) as c:
            resp = c.get("/login/google", follow_redirects=False)
            assert resp.status_code == 307 or resp.status_code == 302
            # Verify the redirect_uri uses BASE_URL
            call_args = mock_google.authorize_redirect.call_args
            assert call_args[0][1] == "https://flights.cattom.net:5498/auth/callback"
        app.dependency_overrides.clear()


class TestAuthCallback:
    def _make_app(self):
        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key="test-secret")
        app.include_router(router)
        return app

    def _make_settings(self, allowed_emails=""):
        settings = MagicMock()
        settings.ALLOWED_EMAILS = allowed_emails
        return settings

    @patch("app.routers.auth.oauth")
    def test_callback_success(self, mock_oauth):
        mock_google = AsyncMock()
        mock_google.authorize_access_token = AsyncMock(
            return_value={
                "userinfo": {
                    "email": "user@example.com",
                    "name": "Test User",
                    "picture": "https://example.com/pic.jpg",
                }
            }
        )
        mock_oauth.google = mock_google

        app = self._make_app()
        app.dependency_overrides[get_settings] = lambda: self._make_settings("")
        with TestClient(app) as c:
            resp = c.get("/auth/callback", follow_redirects=False)
            assert resp.status_code == 302
            assert resp.headers["location"] == "/"
        app.dependency_overrides.clear()

    @patch("app.routers.auth.oauth")
    def test_callback_denied_email(self, mock_oauth):
        mock_google = AsyncMock()
        mock_google.authorize_access_token = AsyncMock(
            return_value={
                "userinfo": {
                    "email": "denied@example.com",
                    "name": "Denied",
                    "picture": "",
                }
            }
        )
        mock_oauth.google = mock_google

        app = self._make_app()
        app.dependency_overrides[get_settings] = lambda: self._make_settings("allowed@example.com")
        with TestClient(app) as c:
            resp = c.get("/auth/callback", follow_redirects=False)
            assert resp.status_code == 403
            assert "Access denied" in resp.text
        app.dependency_overrides.clear()

    @patch("app.routers.auth.oauth")
    def test_callback_allowed_email(self, mock_oauth):
        mock_google = AsyncMock()
        mock_google.authorize_access_token = AsyncMock(
            return_value={
                "userinfo": {
                    "email": "User@Example.com",
                    "name": "User",
                    "picture": "",
                }
            }
        )
        mock_oauth.google = mock_google

        app = self._make_app()
        app.dependency_overrides[get_settings] = lambda: self._make_settings("user@example.com, other@example.com")
        with TestClient(app) as c:
            resp = c.get("/auth/callback", follow_redirects=False)
            assert resp.status_code == 302
        app.dependency_overrides.clear()


class TestLogout:
    def _make_app(self):
        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key="test-secret")
        app.include_router(router)
        return app

    def test_logout_redirects_to_login(self):
        app = self._make_app()
        with TestClient(app) as c:
            resp = c.get("/logout", follow_redirects=False)
            assert resp.status_code == 302
            assert resp.headers["location"] == "/login"


class TestDeleteProfile:
    def test_delete_profile(self, client, db_session, sample_route, sample_prices, sample_prediction):
        """DELETE /profile deletes all routes, prices, predictions and returns ok."""
        from app.models import TrackedRoute, PriceRecord, Prediction

        # Verify data exists before deletion
        assert db_session.query(TrackedRoute).count() == 1
        assert db_session.query(PriceRecord).count() == 2
        assert db_session.query(Prediction).count() == 1

        resp = client.delete("/profile")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

        # All data should be deleted
        assert db_session.query(TrackedRoute).count() == 0
        assert db_session.query(PriceRecord).count() == 0
        assert db_session.query(Prediction).count() == 0

    def test_delete_profile_empty(self, client, db_session):
        """DELETE /profile works even when there's no data."""
        resp = client.delete("/profile")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
