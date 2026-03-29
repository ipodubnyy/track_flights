from __future__ import annotations

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.config import Settings, get_settings

router = APIRouter()
templates = Jinja2Templates(directory="templates")

oauth = OAuth()


def setup_oauth(settings: Settings) -> None:
    oauth.register(
        name="google",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def get_current_user(request: Request) -> dict | None:
    return request.session.get("user")


def require_login(request: Request) -> dict:
    user = request.session.get("user")
    if not user:
        raise _LoginRequired()
    return user


class _LoginRequired(Exception):
    pass


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    user = request.session.get("user")
    if user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/login/google")
async def login_google(request: Request, settings: Settings = Depends(get_settings)):
    redirect_uri = settings.BASE_URL + "/auth/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/callback")
async def auth_callback(request: Request, settings: Settings = Depends(get_settings)):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo", {})

    email = user_info.get("email", "")
    allowed = settings.ALLOWED_EMAILS.strip()
    if allowed:
        allowed_list = [e.strip().lower() for e in allowed.split(",") if e.strip()]
        if email.lower() not in allowed_list:
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": f"Access denied for {email}"},
                status_code=403,
            )

    request.session["user"] = {
        "email": email,
        "name": user_info.get("name", email),
        "picture": user_info.get("picture", ""),
    }
    return RedirectResponse(url="/", status_code=302)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)
