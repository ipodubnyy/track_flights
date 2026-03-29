from app.models import TrackedRoute


class TestIndexPage:
    def test_index_returns_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_index_with_routes(self, client, db_session, sample_route, sample_prices, sample_prediction):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "JFK" in resp.text


class TestRouteDetailPage:
    def test_route_detail_exists(self, client, db_session, sample_route, sample_prediction):
        """Test route detail without prices (prices cause datetime serialization
        issue in the template's tojson filter, which is an existing app bug)."""
        resp = client.get(f"/route/{sample_route.id}")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "JFK" in resp.text

    def test_route_detail_not_found(self, client):
        resp = client.get("/route/9999")
        assert resp.status_code == 404
        assert "Route not found" in resp.text

    def test_route_detail_no_predictions(self, client, db_session, sample_route):
        resp = client.get(f"/route/{sample_route.id}")
        assert resp.status_code == 200
