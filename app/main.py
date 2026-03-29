import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.database import Base, engine, get_db
from app.routers import api, auth, web
from app.routers.auth import _LoginRequired, setup_oauth
from app.services.amadeus_client import FlightApiClient
from app.services.notifier import TelegramNotifier
from app.services.predictor import PricePredictor
from app.services.price_tracker import PriceTracker
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")

    setup_oauth(settings)

    amadeus = FlightApiClient(settings.FLIGHTAPI_KEY)
    predictor = PricePredictor(settings.GROK_API_KEY)
    notifier = TelegramNotifier(settings.TELEGRAM_BOT_TOKEN, settings.TELEGRAM_CHAT_ID)
    price_tracker = PriceTracker(amadeus, predictor, notifier)

    app.state.price_tracker = price_tracker

    scheduler = start_scheduler(price_tracker, get_db, settings.CHECK_INTERVAL_HOURS)
    app.state.scheduler = scheduler

    logger.info("Application started")
    yield

    # Shutdown
    stop_scheduler(app.state.scheduler)
    logger.info("Application shut down")


app = FastAPI(title="Flight Price Tracker", lifespan=lifespan)

settings = get_settings()
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)


@app.exception_handler(_LoginRequired)
async def login_required_handler(request: Request, exc: _LoginRequired):
    return RedirectResponse(url="/login", status_code=302)


app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router)
app.include_router(api.router)
app.include_router(web.router)
