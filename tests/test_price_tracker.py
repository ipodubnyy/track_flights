from datetime import date, datetime
from unittest.mock import MagicMock

from app.models import Prediction, PriceRecord, TrackedRoute
from app.services.price_tracker import PriceTracker


class TestCheckRoute:
    def test_check_route_full_flow(self, db_session, sample_route):
        amadeus = MagicMock()
        amadeus.search_flights.return_value = [
            {"airline": "AA", "price": 350.0, "currency": "USD", "cabin_type": "economy"},
        ]
        amadeus.resolve_airline_codes.return_value = ["AA", "UA"]

        predictor = MagicMock()
        predictor.predict.return_value = {
            "trend": "down",
            "summary": "Falling",
            "buy_recommendation": "wait",
            "predicted_best_buy_date": "2026-05-01",
            "confidence": 0.8,
        }

        notifier = MagicMock()
        notifier.format_price_alert.return_value = "alert message"
        notifier.send_message.return_value = True

        tracker = PriceTracker(amadeus, predictor, notifier)
        tracker.check_route(db_session, sample_route)

        prices = db_session.query(PriceRecord).filter(PriceRecord.route_id == sample_route.id).all()
        assert len(prices) >= 1

        preds = db_session.query(Prediction).filter(Prediction.route_id == sample_route.id).all()
        assert len(preds) == 1
        assert preds[0].trend == "down"
        assert preds[0].predicted_best_buy_date == date(2026, 5, 1)

        notifier.format_price_alert.assert_called_once()
        notifier.send_message.assert_called_once_with("alert message")

    def test_check_route_empty_cabin_types_and_travelers(self, db_session):
        route = TrackedRoute(
            origin="JFK",
            destination="LAX",
            departure_date=date(2026, 6, 15),
            return_date=None,
            is_round_trip=False,
            airlines="[]",
            alliances="[]",
            cabin_types="[]",
            travelers="[]",
            is_active=True,
            created_at=datetime(2026, 1, 1),
        )
        db_session.add(route)
        db_session.commit()
        db_session.refresh(route)

        amadeus = MagicMock()
        amadeus.search_flights.return_value = []
        amadeus.resolve_airline_codes.return_value = []

        predictor = MagicMock()
        predictor.predict.return_value = {
            "trend": "stable",
            "summary": "No data",
            "buy_recommendation": "uncertain",
            "predicted_best_buy_date": None,
            "confidence": 0.0,
        }

        notifier = MagicMock()
        notifier.format_price_alert.return_value = "msg"

        tracker = PriceTracker(amadeus, predictor, notifier)
        tracker.check_route(db_session, route)

        amadeus.search_flights.assert_called_once_with(
            origin="JFK",
            destination="LAX",
            departure_date="2026-06-15",
            adults=1,
            children=0,
            infants=0,
            cabin_class="economy",
            airline_codes=None,
            return_date=None,
        )

    def test_check_route_with_mixed_age_travelers(self, db_session):
        """Test that travelers are split into adults/children/infants by age."""
        route = TrackedRoute(
            origin="JFK",
            destination="LAX",
            departure_date=date(2026, 6, 15),
            return_date=None,
            is_round_trip=False,
            airlines="[]",
            alliances="[]",
            cabin_types="[]",
            travelers='[35, 33, 8, 1]',  # 2 adults, 1 child, 1 infant
            is_active=True,
            created_at=datetime(2026, 1, 1),
        )
        db_session.add(route)
        db_session.commit()
        db_session.refresh(route)

        amadeus = MagicMock()
        amadeus.search_flights.return_value = []
        amadeus.resolve_airline_codes.return_value = []

        predictor = MagicMock()
        predictor.predict.return_value = {
            "trend": "stable", "summary": "ok",
            "buy_recommendation": "uncertain",
            "predicted_best_buy_date": None, "confidence": 0.0,
        }

        notifier = MagicMock()
        notifier.format_price_alert.return_value = "msg"

        tracker = PriceTracker(amadeus, predictor, notifier)
        tracker.check_route(db_session, route)

        call_kwargs = amadeus.search_flights.call_args[1]
        assert call_kwargs["adults"] == 2
        assert call_kwargs["children"] == 1
        assert call_kwargs["infants"] == 1

    def test_check_route_invalid_best_buy_date(self, db_session, sample_route):
        amadeus = MagicMock()
        amadeus.search_flights.return_value = []
        amadeus.resolve_airline_codes.return_value = []

        predictor = MagicMock()
        predictor.predict.return_value = {
            "trend": "stable",
            "summary": "ok",
            "buy_recommendation": "uncertain",
            "predicted_best_buy_date": "not-a-date",
            "confidence": 0.0,
        }

        notifier = MagicMock()
        notifier.format_price_alert.return_value = "msg"

        tracker = PriceTracker(amadeus, predictor, notifier)
        tracker.check_route(db_session, sample_route)

        pred = db_session.query(Prediction).filter(Prediction.route_id == sample_route.id).first()
        assert pred.predicted_best_buy_date is None

    def test_check_route_null_string_best_buy_date(self, db_session, sample_route):
        amadeus = MagicMock()
        amadeus.search_flights.return_value = []
        amadeus.resolve_airline_codes.return_value = []

        predictor = MagicMock()
        predictor.predict.return_value = {
            "trend": "stable",
            "summary": "ok",
            "buy_recommendation": "uncertain",
            "predicted_best_buy_date": "null",
            "confidence": 0.0,
        }

        notifier = MagicMock()
        notifier.format_price_alert.return_value = "msg"

        tracker = PriceTracker(amadeus, predictor, notifier)
        tracker.check_route(db_session, sample_route)

        pred = db_session.query(Prediction).filter(Prediction.route_id == sample_route.id).first()
        assert pred.predicted_best_buy_date is None

    def test_check_route_with_return_date(self, db_session, sample_route):
        amadeus = MagicMock()
        amadeus.search_flights.return_value = []
        amadeus.resolve_airline_codes.return_value = []

        predictor = MagicMock()
        predictor.predict.return_value = {
            "trend": "stable",
            "summary": "ok",
            "buy_recommendation": "uncertain",
            "predicted_best_buy_date": None,
            "confidence": 0.0,
        }

        notifier = MagicMock()
        notifier.format_price_alert.return_value = "msg"

        tracker = PriceTracker(amadeus, predictor, notifier)
        tracker.check_route(db_session, sample_route)

        # sample_route has return_date set
        call_kwargs = amadeus.search_flights.call_args[1]
        assert call_kwargs["return_date"] == "2026-06-22"

        call_args = predictor.predict.call_args
        route_info = call_args[0][0]
        assert route_info["return_date"] == "2026-06-22"


class TestCheckAllRoutes:
    def test_check_all_routes(self, db_session):
        for i in range(3):
            route = TrackedRoute(
                origin=f"O{i}",
                destination=f"D{i}",
                departure_date=date(2026, 6, 15),
                is_active=True,
                created_at=datetime(2026, 1, 1),
            )
            db_session.add(route)
        inactive = TrackedRoute(
            origin="X",
            destination="Y",
            departure_date=date(2026, 6, 15),
            is_active=False,
            created_at=datetime(2026, 1, 1),
        )
        db_session.add(inactive)
        db_session.commit()

        tracker = PriceTracker(MagicMock(), MagicMock(), MagicMock())
        tracker.check_route = MagicMock()

        tracker.check_all_routes(db_session)
        assert tracker.check_route.call_count == 3

    def test_check_all_routes_exception_doesnt_stop(self, db_session):
        for i in range(2):
            route = TrackedRoute(
                origin=f"O{i}",
                destination=f"D{i}",
                departure_date=date(2026, 6, 15),
                is_active=True,
                created_at=datetime(2026, 1, 1),
            )
            db_session.add(route)
        db_session.commit()

        tracker = PriceTracker(MagicMock(), MagicMock(), MagicMock())
        tracker.check_route = MagicMock(side_effect=[Exception("fail"), None])

        tracker.check_all_routes(db_session)
        assert tracker.check_route.call_count == 2
