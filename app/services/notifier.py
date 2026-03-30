import logging

import httpx

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram bot token or chat ID not configured; skipping notification.")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        try:
            with httpx.Client() as client:
                response = client.post(
                    url,
                    json={
                        "chat_id": self.chat_id,
                        "text": text,
                        "parse_mode": parse_mode,
                    },
                    timeout=15.0,
                )
                response.raise_for_status()
                return True
        except Exception:
            logger.exception("Failed to send Telegram message")
            return False

    def format_price_alert(self, route, prices: list[dict], prediction: dict) -> str:
        direction = f"{route.origin} -> {route.destination}"
        dep = route.departure_date
        ret = route.return_date

        lines = [
            f"<b>Flight Price Alert</b>",
            f"<b>Route:</b> {direction}",
            f"<b>Departure:</b> {dep}",
        ]
        if ret:
            lines.append(f"<b>Return:</b> {ret}")

        lines.append("")
        lines.append("<b>Current prices:</b>")
        for p in prices:
            line = f"  {p.get('airline', '??')} | {p.get('cabin_type', '')} | "
            line += f"{p.get('price', 0):.0f} {p.get('currency', 'USD')}"
            flight_info = p.get('flight_info', '')
            if flight_info:
                line += f" ({flight_info})"
            if p.get('departure_date'):
                line += f" [dep {p.get('departure_date')}]"
            if p.get('source') == 'google_flights':
                line += " [G]"
            lines.append(line)

        lines.append("")
        trend = prediction.get("trend", "stable")
        trend_emoji = {"up": "Rising", "down": "Falling", "stable": "Stable"}.get(trend, trend)
        lines.append(f"<b>Trend:</b> {trend_emoji}")
        lines.append(f"<b>Summary:</b> {prediction.get('summary', 'N/A')}")
        lines.append(f"<b>Recommendation:</b> {prediction.get('buy_recommendation', 'N/A')}")

        best_date = prediction.get("predicted_best_buy_date")
        if best_date:
            lines.append(f"<b>Best buy date:</b> {best_date}")

        confidence = prediction.get("confidence", 0)
        lines.append(f"<b>Confidence:</b> {confidence:.0%}")

        return "\n".join(lines)
