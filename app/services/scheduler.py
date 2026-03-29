import logging
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler

from app.services.price_tracker import PriceTracker

logger = logging.getLogger(__name__)


def _job(price_tracker: PriceTracker, get_db_func: Callable) -> None:
    logger.info("Running scheduled price check...")
    db_gen = get_db_func()
    db = next(db_gen)
    try:
        price_tracker.check_all_routes(db)
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


def start_scheduler(
    price_tracker: PriceTracker,
    get_db_func: Callable,
    interval_hours: int,
) -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _job,
        "interval",
        hours=interval_hours,
        args=[price_tracker, get_db_func],
        id="price_check",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started (interval: %d hours)", interval_hours)
    return scheduler


def stop_scheduler(scheduler: BackgroundScheduler) -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
