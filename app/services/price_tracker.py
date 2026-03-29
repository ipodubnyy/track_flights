import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import PriceRecord, Prediction, TrackedRoute
from app.services.amadeus_client import FlightApiClient
from app.services.notifier import TelegramNotifier
from app.services.predictor import PricePredictor

logger = logging.getLogger(__name__)

DATE_OFFSETS = [-3, -2, -1, 0, 1, 2, 3]


class PriceTracker:
    def __init__(
        self,
        amadeus: FlightApiClient,
        predictor: PricePredictor,
        notifier: TelegramNotifier,
    ) -> None:
        self.amadeus = amadeus
        self.predictor = predictor
        self.notifier = notifier

    def check_route(self, db: Session, route: TrackedRoute, currency: str = "USD") -> None:
        cabin_types = route.get_cabin_types() or ["economy"]
        airlines = route.get_airlines()
        alliances = route.get_alliances()
        travelers = route.get_travelers() or [30]
        adults = sum(1 for age in travelers if age >= 12)
        children = sum(1 for age in travelers if 2 <= age < 12)
        infants = sum(1 for age in travelers if age < 2)
        adults = adults or 1

        airline_codes = FlightApiClient.resolve_airline_codes(airlines, alliances)
        trip_duration = None
        if route.return_date and route.departure_date:
            trip_duration = (route.return_date - route.departure_date).days

        all_prices: list[dict] = []

        for offset in DATE_OFFSETS:
            dep_date = route.departure_date + timedelta(days=offset)
            if dep_date < date.today():
                continue

            ret_date_str = None
            if trip_duration is not None:
                ret_date_str = (dep_date + timedelta(days=trip_duration)).isoformat()

            for cabin in cabin_types:
                results = self.amadeus.search_flights(
                    origin=route.origin,
                    destination=route.destination,
                    departure_date=dep_date.isoformat(),
                    adults=adults,
                    children=children,
                    infants=infants,
                    cabin_class=cabin,
                    airline_codes=airline_codes or None,
                    return_date=ret_date_str,
                    currency=currency,
                )

                for r in results:
                    record = PriceRecord(
                        route_id=route.id,
                        departure_date=dep_date,
                        cabin_type=r.get("cabin_type", cabin),
                        airline=r.get("airline", "??"),
                        price=r.get("price", 0),
                        currency=r.get("currency", "USD"),
                        flight_info=r.get("flight_info", ""),
                    )
                    db.add(record)
                    all_prices.append({**r, "departure_date": dep_date.isoformat()})

        db.commit()

        # Build price history for prediction (last 60 records for this route)
        history_records = (
            db.query(PriceRecord)
            .filter(PriceRecord.route_id == route.id)
            .order_by(PriceRecord.fetched_at.desc())
            .limit(60)
            .all()
        )
        price_history = [
            {
                "date": rec.fetched_at.isoformat() if rec.fetched_at else "N/A",
                "departure_date": rec.departure_date.isoformat() if rec.departure_date else "N/A",
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

        message = self.notifier.format_price_alert(route, all_prices, prediction)
        self.notifier.send_message(message)

    def check_all_routes(self, db: Session) -> None:
        from app.models import UserPreference

        pref = db.query(UserPreference).first()
        currency = pref.currency if pref else "USD"
        routes = db.query(TrackedRoute).filter(TrackedRoute.is_active.is_(True)).all()
        for route in routes:
            try:
                self.check_route(db, route, currency=currency)
            except Exception:
                logger.exception("Failed to check route %s", route.id)
