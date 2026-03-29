import json

import httpx
import respx

from app.services.predictor import PricePredictor


class TestPredict:
    @respx.mock
    def test_predict_valid_response(self):
        prediction_json = {
            "trend": "down",
            "summary": "Prices dropping",
            "buy_recommendation": "wait",
            "predicted_best_buy_date": "2026-05-01",
            "confidence": 0.85,
        }
        respx.post("https://api.x.ai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": json.dumps(prediction_json)}}
                    ]
                },
            )
        )
        predictor = PricePredictor("test-api-key")
        result = predictor.predict(
            {"origin": "JFK", "destination": "LAX", "departure_date": "2026-06-15"},
            [{"date": "2026-01-01", "price": 350, "currency": "USD", "airline": "AA", "cabin_type": "economy"}],
        )
        assert result["trend"] == "down"
        assert result["summary"] == "Prices dropping"
        assert result["buy_recommendation"] == "wait"

    def test_predict_empty_api_key(self):
        predictor = PricePredictor("")
        result = predictor.predict({}, [])
        assert result["trend"] == "stable"
        assert result["confidence"] == 0.0
        assert result["buy_recommendation"] == "uncertain"

    @respx.mock
    def test_predict_api_error(self):
        respx.post("https://api.x.ai/v1/chat/completions").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        predictor = PricePredictor("test-api-key")
        result = predictor.predict({"origin": "JFK"}, [])
        assert result["trend"] == "stable"
        assert result["confidence"] == 0.0

    @respx.mock
    def test_predict_malformed_json(self):
        respx.post("https://api.x.ai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": "not valid json at all"}}
                    ]
                },
            )
        )
        predictor = PricePredictor("test-api-key")
        result = predictor.predict({"origin": "JFK"}, [])
        assert result["trend"] == "stable"
        assert result["confidence"] == 0.0

    @respx.mock
    def test_predict_markdown_wrapped_json(self):
        prediction_json = {
            "trend": "up",
            "summary": "Rising prices",
            "buy_recommendation": "buy now",
            "predicted_best_buy_date": None,
            "confidence": 0.7,
        }
        content = f"```json\n{json.dumps(prediction_json)}\n```"
        respx.post("https://api.x.ai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": content}}]
                },
            )
        )
        predictor = PricePredictor("test-api-key")
        result = predictor.predict({"origin": "JFK"}, [])
        assert result["trend"] == "up"
        assert result["buy_recommendation"] == "buy now"

    @respx.mock
    def test_predict_missing_required_keys(self):
        # Valid JSON but missing required keys
        respx.post("https://api.x.ai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": json.dumps({"trend": "up"})}}
                    ]
                },
            )
        )
        predictor = PricePredictor("test-api-key")
        result = predictor.predict({"origin": "JFK"}, [])
        assert result["trend"] == "stable"
        assert result["confidence"] == 0.0

    @respx.mock
    def test_predict_with_full_route_info(self):
        """Verify the user prompt is built correctly with all route info fields."""
        prediction_json = {
            "trend": "stable",
            "summary": "No change",
            "buy_recommendation": "uncertain",
            "predicted_best_buy_date": None,
            "confidence": 0.5,
        }
        respx.post("https://api.x.ai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": json.dumps(prediction_json)}}]
                },
            )
        )
        predictor = PricePredictor("test-api-key")
        result = predictor.predict(
            {
                "origin": "JFK",
                "destination": "LAX",
                "departure_date": "2026-06-15",
                "return_date": "2026-06-22",
                "cabin_types": ["economy"],
                "travelers": [30],
            },
            [
                {"date": "2026-01-01", "price": 350, "currency": "USD", "airline": "AA", "cabin_type": "economy"},
                {"date": "2026-01-02", "price": 360, "currency": "USD", "airline": "AA", "cabin_type": "economy"},
            ],
        )
        assert result["trend"] == "stable"
