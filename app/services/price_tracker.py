import logging
from datetime import date

from sqlalchemy.orm import Session

from app.models import PriceRecord, Prediction, TrackedRoute
from app.services.amadeus_client import AmadeusClient
from app.services.notifier import TelegramNotifier
from app.services.predictor import PricePredictor

logger = logging.getLogger(__name__)


class PriceTracker:
    def __init__(
        self,
        amadeus: AmadeusClient,
        predictor: PricePredictor,
        notifier: TelegramNotifier,
    ) -> None:
        self.amadeus = amadeus
        self.predictor = predictor
        self.notifier = notifier

    def check_route(self, db: Session, route: TrackedRoute) -> None:
        cabin_types = route.get_cabin_types() or ["economy"]
        airlines = route.get_airlines()
        alliances = route.get_alliances()
        travelers = route.get_travelers() or [30]
        adults = len(travelers)

        airline_codes = AmadeusClient.resolve_airline_codes(airlines, alliances)

        all_prices: list[dict] = []

        for cabin in cabin_types:
            results = self.amadeus.search_flights(
                origin=route.origin,
                destination=route.destination,
                departure_date=route.departure_date.isoformat(),
                adults=adults,
                cabin_class=cabin,
                airline_codes=airline_codes or None,
            )

            for r in results:
                record = PriceRecord(
                    route_id=route.id,
                    cabin_type=r.get("cabin_type", cabin),
                    airline=r.get("airline", "??"),
                    price=r.get("price", 0),
                    currency=r.get("currency", "USD"),
                )
                db.add(record)
                all_prices.append(r)

        db.commit()

        # Build price history for prediction (last 30 per cabin type)
        history_records = (
            db.query(PriceRecord)
            .filter(PriceRecord.route_id == route.id)
            .order_by(PriceRecord.fetched_at.desc())
            .limit(30)
            .all()
        )
        price_history = [
            {
                "date": rec.fetched_at.isoformat() if rec.fetched_at else "N/A",
                "price": rec.price,
                "currency": rec.currency,
                "airline": rec.airline,
                "cabin_type": rec.cabin_type,
            }
            for rec in history_records
        ]

        route_info = {
            "origin": route.origin,
            "destination": route.destination,
            "departure_date": route.departure_date.isoformat(),
            "return_date": route.return_date.isoformat() if route.return_date else None,
            "cabin_types": cabin_types,
            "travelers": travelers,
        }

        prediction = self.predictor.predict(route_info, price_history)

        # Parse predicted_best_buy_date
        best_buy_date = None
        raw_date = prediction.get("predicted_best_buy_date")
        if raw_date and raw_date != "null":
            try:
                best_buy_date = date.fromisoformat(str(raw_date))
            except (ValueError, TypeError):
                best_buy_date = None

        pred_record = Prediction(
            route_id=route.id,
            trend=prediction.get("trend", "stable"),
            summary=prediction.get("summary", ""),
            buy_recommendation=prediction.get("buy_recommendation", "uncertain"),
            predicted_best_buy_date=best_buy_date,
            confidence=prediction.get("confidence", 0.0),
        )
        db.add(pred_record)
        db.commit()

        # Send notification
        message = self.notifier.format_price_alert(route, all_prices, prediction)
        self.notifier.send_message(message)

    def check_all_routes(self, db: Session) -> None:
        routes = db.query(TrackedRoute).filter(TrackedRoute.is_active.is_(True)).all()
        for route in routes:
            try:
                self.check_route(db, route)
            except Exception:
                logger.exception("Failed to check route %s", route.id)
