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

        # Now iterates over 7 date offsets, so search_flights is called 7 times
        assert amadeus.search_flights.call_count == 7
        # Check the center call (offset=0, index=3) has the expected args
        center_call_kwargs = amadeus.search_flights.call_args_list[3][1]
        assert center_call_kwargs["origin"] == "JFK"
        assert center_call_kwargs["destination"] == "LAX"
        assert center_call_kwargs["departure_date"] == "2026-06-15"
        assert center_call_kwargs["adults"] == 1
        assert center_call_kwargs["children"] == 0
        assert center_call_kwargs["infants"] == 0
        assert center_call_kwargs["cabin_class"] == "economy"
        assert center_call_kwargs["airline_codes"] is None
        assert center_call_kwargs["return_date"] is None

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
        """Trip duration is preserved: dep 2026-06-15 + ret 2026-06-22 = 7 days.
        For offset +3 the dep becomes 2026-06-18 and ret becomes 2026-06-25."""
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

        # sample_route has 2 cabin types, so 7 offsets * 2 cabins = 14 calls
        assert amadeus.search_flights.call_count == 14

        # The last call (offset +3): dep=2026-06-18, ret=2026-06-25 (7 day trip)
        last_call_kwargs = amadeus.search_flights.call_args_list[-1][1]
        assert last_call_kwargs["departure_date"] == "2026-06-18"
        assert last_call_kwargs["return_date"] == "2026-06-25"

        # The center call (offset 0) is at index 6 (each offset has 2 cabin calls)
        center_call_kwargs = amadeus.search_flights.call_args_list[6][1]
        assert center_call_kwargs["departure_date"] == "2026-06-15"
        assert center_call_kwargs["return_date"] == "2026-06-22"

        call_args = predictor.predict.call_args
        route_info = call_args[0][0]
        assert route_info["return_date"] == "2026-06-22"

    def test_check_route_skips_past_dates(self, db_session):
        """When departure_date is today, offsets -3,-2,-1 are in the past and skipped."""
        from unittest.mock import patch as mock_patch
        today = date.today()
        route = TrackedRoute(
            origin="JFK",
            destination="LAX",
            departure_date=today,
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
            "summary": "ok",
            "buy_recommendation": "uncertain",
            "predicted_best_buy_date": None,
            "confidence": 0.0,
        }

        notifier = MagicMock()
        notifier.format_price_alert.return_value = "msg"

        tracker = PriceTracker(amadeus, predictor, notifier)
        tracker.check_route(db_session, route)

        # Offsets -3,-2,-1 are past, so only 0,1,2,3 = 4 calls
        assert amadeus.search_flights.call_count == 4
        # First call should be for today (offset 0)
        first_call_kwargs = amadeus.search_flights.call_args_list[0][1]
        assert first_call_kwargs["departure_date"] == today.isoformat()


    def test_check_route_google_flights_fallback(self, db_session):
        """When amadeus returns empty and google_flights is available, fallback is used."""
        route = TrackedRoute(
            origin="JFK",
            destination="FRA",
            departure_date=date(2026, 6, 15),
            return_date=None,
            is_round_trip=False,
            airlines="[]",
            alliances="[]",
            cabin_types="[]",
            travelers="[30]",
            is_active=True,
            created_at=datetime(2026, 1, 1),
        )
        db_session.add(route)
        db_session.commit()
        db_session.refresh(route)

        amadeus = MagicMock()
        amadeus.search_flights.return_value = []
        amadeus.resolve_airline_codes.return_value = []

        google_flights = MagicMock()
        google_flights.search_flights.return_value = [
            {"airline": "UA", "price": 500.0, "currency": "USD", "cabin_type": "economy", "source": "google_flights"},
        ]

        predictor = MagicMock()
        predictor.predict.return_value = {
            "trend": "stable", "summary": "ok",
            "buy_recommendation": "uncertain",
            "predicted_best_buy_date": None, "confidence": 0.0,
        }

        notifier = MagicMock()
        notifier.format_price_alert.return_value = "msg"

        tracker = PriceTracker(amadeus, predictor, notifier, google_flights=google_flights)
        tracker.check_route(db_session, route)

        # Google flights should have been called as fallback
        assert google_flights.search_flights.call_count == 7  # 7 date offsets
        prices = db_session.query(PriceRecord).filter(PriceRecord.route_id == route.id).all()
        assert len(prices) == 7
        assert all(p.source == "google_flights" for p in prices)

    def test_check_route_no_google_fallback_when_amadeus_has_results(self, db_session):
        """When amadeus returns results, google_flights fallback is NOT called."""
        route = TrackedRoute(
            origin="JFK",
            destination="FRA",
            departure_date=date(2026, 6, 15),
            return_date=None,
            is_round_trip=False,
            airlines="[]",
            alliances="[]",
            cabin_types="[]",
            travelers="[30]",
            is_active=True,
            created_at=datetime(2026, 1, 1),
        )
        db_session.add(route)
        db_session.commit()
        db_session.refresh(route)

        amadeus = MagicMock()
        amadeus.search_flights.return_value = [
            {"airline": "AA", "price": 350.0, "currency": "USD", "cabin_type": "economy", "source": "flightapi"},
        ]
        amadeus.resolve_airline_codes.return_value = []

        google_flights = MagicMock()
        google_flights.search_flights.return_value = []

        predictor = MagicMock()
        predictor.predict.return_value = {
            "trend": "stable", "summary": "ok",
            "buy_recommendation": "uncertain",
            "predicted_best_buy_date": None, "confidence": 0.0,
        }

        notifier = MagicMock()
        notifier.format_price_alert.return_value = "msg"

        tracker = PriceTracker(amadeus, predictor, notifier, google_flights=google_flights)
        tracker.check_route(db_session, route)

        # Google flights should NOT have been called
        google_flights.search_flights.assert_not_called()
        prices = db_session.query(PriceRecord).filter(PriceRecord.route_id == route.id).all()
        assert len(prices) == 7
        assert all(p.source == "flightapi" for p in prices)


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
