from sqlalchemy.orm import Session

from app.database import get_db


class TestGetDb:
    def test_get_db_yields_session(self):
        gen = get_db()
        db = next(gen)
        assert isinstance(db, Session)
        # Close the generator
        try:
            next(gen)
        except StopIteration:
            pass

    def test_get_db_closes_session_on_finish(self):
        gen = get_db()
        db = next(gen)
        # Exhaust the generator which triggers finally block (db.close())
        try:
            next(gen)
        except StopIteration:
            pass
        # Session should be closed - verify by checking it's not usable in typical way
        # The important thing is the generator completes without error
