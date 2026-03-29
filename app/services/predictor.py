import json
import logging

import httpx

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a flight price analyst. Analyze the provided route and price history, then respond with ONLY a JSON object (no markdown, no extra text) in this exact format:
{"trend": "up|down|stable", "summary": "brief analysis", "buy_recommendation": "buy now / wait / uncertain", "predicted_best_buy_date": "YYYY-MM-DD or null", "confidence": 0.0-1.0}"""


class PricePredictor:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base_url = "https://api.x.ai/v1"

    def predict(self, route_info: dict, price_history: list[dict]) -> dict:
        default = {
            "trend": "stable",
            "summary": "Insufficient data for prediction.",
            "buy_recommendation": "uncertain",
            "predicted_best_buy_date": None,
            "confidence": 0.0,
        }

        if not self.api_key:
            return default

        history_text = "\n".join(
            f"  {p.get('date', 'N/A')}: {p.get('price', 'N/A')} {p.get('currency', 'USD')} ({p.get('airline', '')} / {p.get('cabin_type', '')})"
            for p in price_history
        )

        user_prompt = (
            f"Route: {route_info.get('origin', '')} -> {route_info.get('destination', '')}\n"
            f"Departure: {route_info.get('departure_date', '')}\n"
            f"Return: {route_info.get('return_date', 'one-way')}\n"
            f"Cabin types: {route_info.get('cabin_types', [])}\n"
            f"Travelers: {route_info.get('travelers', [])}\n\n"
            f"Price history (most recent first):\n{history_text}\n\n"
            "Analyze the price trend and provide your prediction."
        )

        try:
            with httpx.Client() as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": "grok-4.1-fast",
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=60.0,
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                # Strip markdown code fences if present
                content = content.strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[-1]
                    content = content.rsplit("```", 1)[0]
                prediction = json.loads(content.strip())
                # Validate required keys
                for key in ("trend", "summary", "buy_recommendation"):
                    if key not in prediction:
                        return default
                return prediction
        except Exception:
            logger.exception("Grok prediction failed")
            return default
