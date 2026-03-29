import json
from datetime import date, datetime
from unittest.mock import MagicMock, patch

from app.models import Prediction, PriceRecord, TrackedRoute, UserPreference
from app.routers.api import _run_check_in_background


class TestCreateRoute:
    def test_create_route(self, client, sample_route_data):
        resp = client.post("/api/routes", json=sample_route_data)
        assert resp.status_code == 200
        data = resp.json()
        assert data["origin"] == "JFK"
        assert data["destination"] == "LAX"
        assert data["is_round_trip"] is True
        assert data["airlines"] == ["AA", "UA"]


class TestListRoutes:
    def test_list_routes_empty(self, client):
        resp = client.get("/api/routes")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_routes_with_data(self, client, db_session, sample_route, sample_prices, sample_prediction):
        resp = client.get("/api/routes")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["origin"] == "JFK"
        assert len(data[0]["latest_prices"]) > 0
        assert data[0]["latest_prediction"] is not None


class TestGetRoute:
    def test_get_route_exists(self, client, db_session, sample_route, sample_prices, sample_prediction):
        resp = client.get(f"/api/routes/{sample_route.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["origin"] == "JFK"
        assert len(data["latest_prices"]) == 2

    def test_get_route_not_found(self, client):
        resp = client.get("/api/routes/9999")
        assert resp.status_code == 404


class TestDeleteRoute:
    def test_delete_route_exists(self, client, db_session, sample_route):
        resp = client.delete(f"/api/routes/{sample_route.id}")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    def test_delete_route_not_found(self, client):
        resp = client.delete("/api/routes/9999")
        assert resp.status_code == 404


class TestToggleRoute:
    def test_toggle_route_exists(self, client, db_session, sample_route):
        assert sample_route.is_active is True
        resp = client.patch(f"/api/routes/{sample_route.id}/toggle")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_active"] is False

    def test_toggle_route_not_found(self, client):
        resp = client.patch("/api/routes/9999/toggle")
        assert resp.status_code == 404


class TestCheckRoute:
    def test_check_route_exists(self, client, db_session, sample_route):
        resp = client.post(f"/api/routes/{sample_route.id}/check")
        assert resp.status_code == 200
        # price_tracker.check_route was called (it's a mock)
        from app.main import app
        app.state.price_tracker.check_route.assert_called_once()

    def test_check_route_not_found(self, client):
        resp = client.post("/api/routes/9999/check")
        assert resp.status_code == 404


class TestGetRoutePrices:
    def test_get_prices_exists(self, client, db_session, sample_route, sample_prices):
        resp = client.get(f"/api/routes/{sample_route.id}/prices")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_get_prices_not_found(self, client):
        resp = client.get("/api/routes/9999/prices")
        assert resp.status_code == 404


class TestRunCheckInBackground:
    def test_run_check_in_background_success(self, db_session, sample_route):
        mock_tracker = MagicMock()
        app_state = MagicMock()
        app_state.price_tracker = mock_tracker

        def fake_get_db():
            yield db_session

        _run_check_in_background(app_state, sample_route.id, fake_get_db)
        mock_tracker.check_route.assert_called_once()
        call_args = mock_tracker.check_route.call_args
        assert call_args[0][1].id == sample_route.id

    def test_run_check_in_background_route_not_found(self, db_session):
        mock_tracker = MagicMock()
        app_state = MagicMock()
        app_state.price_tracker = mock_tracker

        def fake_get_db():
            yield db_session

        _run_check_in_background(app_state, 99999, fake_get_db)
        mock_tracker.check_route.assert_not_called()

    def test_run_check_in_background_exception(self, db_session, sample_route):
        mock_tracker = MagicMock()
        mock_tracker.check_route.side_effect = Exception("boom")
        app_state = MagicMock()
        app_state.price_tracker = mock_tracker

        def fake_get_db():
            yield db_session

        # Should not raise
        _run_check_in_background(app_state, sample_route.id, fake_get_db)


class TestGetRoutePredictions:
    def test_get_predictions_exists(self, client, db_session, sample_route, sample_prediction):
        resp = client.get(f"/api/routes/{sample_route.id}/predictions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["trend"] == "down"

    def test_get_predictions_not_found(self, client):
        resp = client.get("/api/routes/9999/predictions")
        assert resp.status_code == 404


class TestGetCurrency:
    def test_get_currency_default(self, client, db_session):
        resp = client.get("/api/currency")
        assert resp.status_code == 200
        assert resp.json()["currency"] == "USD"
        # Should have created the preference row
        assert db_session.query(UserPreference).count() == 1

    def test_get_currency_existing(self, client, db_session):
        db_session.add(UserPreference(id=1, currency="RUB"))
        db_session.commit()
        resp = client.get("/api/currency")
        assert resp.status_code == 200
        assert resp.json()["currency"] == "RUB"


class TestSetCurrency:
    def test_set_currency_usd(self, client, db_session):
        resp = client.patch("/api/currency", json={"currency": "USD"})
        assert resp.status_code == 200
        assert resp.json()["currency"] == "USD"

    def test_set_currency_rub(self, client, db_session):
        resp = client.patch("/api/currency", json={"currency": "RUB"})
        assert resp.status_code == 200
        assert resp.json()["currency"] == "RUB"

    def test_set_currency_existing_pref(self, client, db_session):
        db_session.add(UserPreference(id=1, currency="USD"))
        db_session.commit()
        resp = client.patch("/api/currency", json={"currency": "RUB"})
        assert resp.status_code == 200
        assert resp.json()["currency"] == "RUB"

    def test_set_currency_invalid(self, client, db_session):
        resp = client.patch("/api/currency", json={"currency": "EUR"})
        assert resp.status_code == 400


class TestUpdateRoute:
    def test_update_route_cabin_types(self, client, db_session, sample_route):
        resp = client.patch(f"/api/routes/{sample_route.id}", json={"cabin_types": ["business"]})
        assert resp.status_code == 200
        assert resp.json()["cabin_types"] == ["business"]

    def test_update_route_travelers(self, client, db_session, sample_route):
        resp = client.patch(f"/api/routes/{sample_route.id}", json={"travelers": [35, 33, 5]})
        assert resp.status_code == 200
        assert resp.json()["travelers"] == [35, 33, 5]

    def test_update_route_dates(self, client, db_session, sample_route):
        resp = client.patch(f"/api/routes/{sample_route.id}", json={
            "departure_date": "2026-07-01",
            "return_date": "2026-07-10",
            "is_round_trip": True,
        })
        assert resp.status_code == 200
        assert resp.json()["departure_date"] == "2026-07-01"
        assert resp.json()["return_date"] == "2026-07-10"

    def test_update_route_airlines_alliances(self, client, db_session, sample_route):
        resp = client.patch(f"/api/routes/{sample_route.id}", json={
            "airlines": ["DL"],
            "alliances": ["SkyTeam"],
        })
        assert resp.status_code == 200
        assert resp.json()["airlines"] == ["DL"]
        assert resp.json()["alliances"] == ["SkyTeam"]

    def test_update_route_not_found(self, client):
        resp = client.patch("/api/routes/9999", json={"travelers": [30]})
        assert resp.status_code == 404

    def test_update_route_partial(self, client, db_session, sample_route):
        """Only the fields provided should change; others stay the same."""
        original = client.get(f"/api/routes/{sample_route.id}").json()
        resp = client.patch(f"/api/routes/{sample_route.id}", json={"travelers": [40]})
        data = resp.json()
        assert data["travelers"] == [40]
        assert data["airlines"] == original["airlines"]  # unchanged
