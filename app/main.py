import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse

from app.config import get_settings
from app.database import Base, engine, get_db
from app.routers import api, auth, web
from app.routers.auth import _LoginRequired, setup_oauth
from app.services.amadeus_client import FlightApiClient
from app.services.google_flights_client import GoogleFlightsClient
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

    from app.schemas import fetch_exchange_rate
    try:
        rate = fetch_exchange_rate()
        logger.info("Exchange rate USD->RUB: %.2f", rate)
    except Exception:
        logger.warning("Failed to fetch exchange rate, using cached")

    amadeus = FlightApiClient(settings.FLIGHTAPI_KEY)
    google_flights = GoogleFlightsClient(settings.SERPAPI_KEY) if settings.SERPAPI_KEY else None
    if google_flights:
        logger.info("Google Flights fallback enabled (SerpAPI)")
    predictor = PricePredictor(settings.GROK_API_KEY)
    notifier = TelegramNotifier(settings.TELEGRAM_BOT_TOKEN, settings.TELEGRAM_CHAT_ID)
    price_tracker = PriceTracker(amadeus, predictor, notifier, google_flights=google_flights)

    app.state.price_tracker = price_tracker

    scheduler = start_scheduler(price_tracker, get_db, settings.CHECK_INTERVAL_HOURS)
    app.state.scheduler = scheduler

    logger.info("Application started")
    yield

    # Shutdown
    stop_scheduler(app.state.scheduler)
    logger.info("Application shut down")


app = FastAPI(title="Flight Price Tracker", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

settings = get_settings()
if settings.SECRET_KEY == "change-me-to-a-random-secret":
    import warnings
    warnings.warn("SECRET_KEY is using the default value! Set a unique SECRET_KEY in .env", stacklevel=1)


class CSRFMiddleware(BaseHTTPMiddleware):
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
    EXEMPT_PATHS = {"/auth/callback", "/login/google"}

    async def dispatch(self, request, call_next):
        # Set CSRF cookie if not present
        csrf_cookie = request.cookies.get("csrf_token")
        if not csrf_cookie:
            csrf_cookie = secrets.token_hex(32)

        if request.method not in self.SAFE_METHODS and request.url.path not in self.EXEMPT_PATHS:
            header_token = request.headers.get("x-csrf-token", "")
            if not csrf_cookie or header_token != csrf_cookie:
                return JSONResponse({"detail": "CSRF token missing or invalid"}, status_code=403)

        response = await call_next(request)
        response.set_cookie("csrf_token", csrf_cookie, httponly=False, samesite="lax", secure=True, max_age=86400)
        return response


app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    https_only=True,
    same_site="lax",
)
app.add_middleware(CSRFMiddleware)


@app.exception_handler(_LoginRequired)
async def login_required_handler(request: Request, exc: _LoginRequired):
    return RedirectResponse(url="/login", status_code=302)


app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router)
app.include_router(api.router)
app.include_router(web.router)
