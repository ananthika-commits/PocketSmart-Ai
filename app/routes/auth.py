import secrets
from typing import Any, Dict, Optional

# Compatibility fix for passlib with bcrypt >= 4.1.0
try:
    import bcrypt
    if not hasattr(bcrypt, "__about__"):
        class _BcryptAbout:
            __version__ = getattr(bcrypt, "__version__", "4.1.2")
        bcrypt.__about__ = _BcryptAbout()
except ImportError:
    pass

from fastapi import APIRouter, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext

from app.database import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_session_user(request: Request) -> Optional[Dict[str, Any]]:
    """Retrieves authenticated user from session cookie."""
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    user = get_user_by_id(int(user_id))
    if user is None:
        request.session.clear()
        return None
    return {"id": user["id"], "username": user["username"], "email": user["email"]}


def require_login(request: Request) -> Dict[str, Any]:
    """Dependency / guard ensuring user is logged in."""
    user = get_session_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access this resource",
        )
    return user


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = get_session_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"user": None, "error": None},
    )


@router.post("/login")
async def login_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    user = get_user_by_username(username.strip())
    # Also allow logging in with email address
    if user is None and "@" in username:
        user = get_user_by_email(username.strip())

    if user is None or not pwd_context.verify(password, user["password_hash"]):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Invalid username or password. Please verify your credentials.",
                "user": None,
                "username_input": username,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Establish session
    request.session["user_id"] = user["id"]
    request.session["username"] = user["username"]
    request.session["email"] = user["email"]
    # Generate ephemeral token for API calls
    request.session["api_token"] = secrets.token_urlsafe(32)

    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    user = get_session_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={"user": None, "error": None},
    )


@router.post("/register")
async def register_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: Optional[str] = Form(None),
):
    cleaned_user = username.strip()
    cleaned_email = email.strip().lower()

    if len(cleaned_user) < 3:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={"error": "Username must be at least 3 characters long.", "user": None},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if len(password) < 4:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={"error": "Password must be at least 4 characters long.", "user": None},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if confirm_password and password != confirm_password:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={"error": "Passwords do not match.", "user": None},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if get_user_by_username(cleaned_user) is not None:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={"error": "This username is already taken. Please choose another.", "user": None},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if get_user_by_email(cleaned_email) is not None:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={"error": "An account with this email already exists.", "user": None},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    hashed = pwd_context.hash(password)
    new_user = create_user(cleaned_user, cleaned_email, hashed)

    # Automatically log the user in after registration
    request.session["user_id"] = new_user["id"]
    request.session["username"] = new_user["username"]
    request.session["email"] = new_user["email"]
    request.session["api_token"] = secrets.token_urlsafe(32)

    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/logout")
@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login?logged_out=1", status_code=status.HTTP_303_SEE_OTHER)


# ---------------- API & Session Endpoints (Milestones 2.4 & 3.1) ----------------

@router.get("/token")
@router.get("/api/token")
async def get_token(request: Request):
    """Issues a secure token for authorized API access."""
    user = get_session_user(request)
    if not user:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"authenticated": False, "message": "Not authenticated. Log in first."},
        )
    token = request.session.get("api_token") or secrets.token_urlsafe(32)
    request.session["api_token"] = token
    return {
        "access_token": token,
        "token_type": "bearer",
        "authenticated": True,
        "user": user,
    }


@router.get("/session-info")
@router.get("/api/session-info")
async def session_info(request: Request):
    """Retrieves metadata about current user session."""
    user = get_session_user(request)
    return {
        "logged_in": user is not None,
        "session_active": bool(request.session),
        "user": user,
    }


@router.get("/session-data")
@router.get("/api/session-data")
async def session_data(request: Request):
    """Returns detailed session-specific data for personalization."""
    user = get_session_user(request)
    return {
        "session_keys": list(request.session.keys()),
        "user_id": request.session.get("user_id"),
        "username": request.session.get("username"),
        "user": user,
    }
