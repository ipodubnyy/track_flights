from unittest.mock import MagicMock, patch

from app.services.scheduler import _job, start_scheduler, stop_scheduler


class TestStartScheduler:
    def test_start_scheduler(self):
        tracker = MagicMock()
        get_db = MagicMock()

        scheduler = start_scheduler(tracker, get_db, 6)
        try:
            assert scheduler.running is True
            jobs = scheduler.get_jobs()
            assert len(jobs) == 1
            assert jobs[0].id == "price_check"
        finally:
            scheduler.shutdown(wait=False)


class TestStopScheduler:
    def test_stop_running_scheduler(self):
        tracker = MagicMock()
        get_db = MagicMock()
        scheduler = start_scheduler(tracker, get_db, 6)
        assert scheduler.running is True
        stop_scheduler(scheduler)
        assert scheduler.running is False

    def test_stop_already_stopped_scheduler(self):
        tracker = MagicMock()
        get_db = MagicMock()
        scheduler = start_scheduler(tracker, get_db, 6)
        scheduler.shutdown(wait=False)
        # Should not raise
        stop_scheduler(scheduler)


class TestJob:
    def test_job_calls_check_all_routes(self):
        mock_db = MagicMock()
        mock_tracker = MagicMock()

        def fake_get_db():
            yield mock_db

        _job(mock_tracker, fake_get_db)
        mock_tracker.check_all_routes.assert_called_once_with(mock_db)

    def test_job_closes_db_on_exception(self):
        mock_db = MagicMock()
        mock_tracker = MagicMock()
        mock_tracker.check_all_routes.side_effect = Exception("boom")

        close_called = False

        def fake_get_db():
            nonlocal close_called
            yield mock_db
            close_called = True

        try:
            _job(mock_tracker, fake_get_db)
        except Exception:
            pass

        # The generator should have been exhausted (finally block runs)
        # close_called will be True because the finally block calls next(db_gen)
        # which resumes the generator past yield, executing the rest
        assert close_called is True
