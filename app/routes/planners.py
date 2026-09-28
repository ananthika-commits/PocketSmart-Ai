from typing import Any, Dict, Optional

from fastapi import APIRouter, File, Form, Request, UploadFile, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.database import get_recent_recommendations, save_recommendation
from app.routes.auth import get_session_user
from gemini_utils import generate_recommendations

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _save_if_logged_in(
    user: Optional[Dict[str, Any]], category: str, payload: Dict[str, Any], result: Dict[str, Any]
) -> Optional[int]:
    """Helper to persist generated recommendation if user is signed in."""
    if user is not None and "id" in user:
        return save_recommendation(user["id"], category, payload, result)
    return None


def _wants_json(request: Request) -> bool:
    """Checks whether the client prefers a JSON API response."""
    accept = request.headers.get("accept", "")
    content_type = request.headers.get("content-type", "")
    return "application/json" in accept or "application/json" in content_type


# ---------------- 1. Home Interior Planner ----------------

@router.get("/home-planner", response_class=HTMLResponse)
async def home_planner_page(request: Request):
    """Home interior budget planner form page."""
    user = get_session_user(request)
    return templates.TemplateResponse(
        request=request,
        name="home_planner.html",
        context={"user": user},
    )


@router.post("/generate-home")
async def generate_home(
    request: Request,
    budget: float = Form(...),
    rooms: str = Form("Living Room, Bedroom"),
    items: str = Form("LED ambient lights, center coffee table, area rug"),
    style: str = Form("Modern Minimalist"),
):
    """Processes home interior budget allocation and product recommendations."""
    user = get_session_user(request)
    payload = {
        "budget": budget,
        "rooms": rooms.strip(),
        "items": items.strip(),
        "style": style.strip(),
    }

    result = generate_recommendations("home", payload)
    rec_id = _save_if_logged_in(user, "Home Interior", payload, result)

    if _wants_json(request):
        return JSONResponse(content={"status": "success", "rec_id": rec_id, "data": result})

    return templates.TemplateResponse(
        request=request,
        name="recommendations.html",
        context={
            "user": user,
            "category": "Home Interior",
            "result": result,
            "input_data": payload,
            "rec_id": rec_id,
        },
    )


# ---------------- 2. Party Budget Planner ----------------

@router.get("/party-planner", response_class=HTMLResponse)
async def party_planner_page(request: Request):
    """Party budget planner form page."""
    user = get_session_user(request)
    return templates.TemplateResponse(
        request=request,
        name="party_planner.html",
        context={"user": user},
    )


@router.post("/generate-party")
async def generate_party(
    request: Request,
    budget: float = Form(...),
    guest_count: int = Form(...),
    event_type: str = Form("Birthday Celebration"),
    venue: str = Form("Banquet Hall / Rooftop"),
    notes: Optional[str] = Form(""),
):
    """Processes party planning details to recommend catering, venue, and decor."""
    user = get_session_user(request)
    payload = {
        "budget": budget,
        "guest_count": max(1, guest_count),
        "event_type": event_type.strip(),
        "venue": venue.strip(),
        "notes": (notes or "").strip(),
    }

    result = generate_recommendations("party", payload)
    rec_id = _save_if_logged_in(user, "Party Planning", payload, result)

    if _wants_json(request):
        return JSONResponse(content={"status": "success", "rec_id": rec_id, "data": result})

    return templates.TemplateResponse(
        request=request,
        name="recommendations.html",
        context={
            "user": user,
            "category": "Party Planning",
            "result": result,
            "input_data": payload,
            "rec_id": rec_id,
        },
    )


# ---------------- 3. Jewelry Budget Planner ----------------

@router.get("/jewelry-planner", response_class=HTMLResponse)
async def jewelry_planner_page(request: Request):
    """Jewelry styling planner form with optional outfit image upload."""
    user = get_session_user(request)
    return templates.TemplateResponse(
        request=request,
        name="jewelry_planner.html",
        context={"user": user},
    )


@router.post("/generate-jewelry")
async def generate_jewelry(
    request: Request,
    budget: float = Form(...),
    occasion: str = Form("Wedding"),
    style: str = Form("Traditional / Ethnic"),
    notes: Optional[str] = Form(""),
    image: Optional[UploadFile] = File(default=None),
):
    """Processes jewelry budget & outfit image with multimodal Gemini AI."""
    user = get_session_user(request)
    payload = {
        "budget": budget,
        "occasion": occasion.strip(),
        "style": style.strip(),
        "notes": (notes or "").strip(),
        "has_image": image is not None and bool(getattr(image, "filename", "")),
    }

    result = generate_recommendations("jewelry", payload, image_file=image)
    rec_id = _save_if_logged_in(user, "Jewelry Styling", payload, result)

    if _wants_json(request):
        return JSONResponse(content={"status": "success", "rec_id": rec_id, "data": result})

    return templates.TemplateResponse(
        request=request,
        name="recommendations.html",
        context={
            "user": user,
            "category": "Jewelry Styling",
            "result": result,
            "input_data": payload,
            "rec_id": rec_id,
        },
    )


# ---------------- API Endpoints ----------------

@router.get("/api/recommendations")
async def api_recommendations(request: Request):
    """Returns past recommendations for the authenticated user."""
    user = get_session_user(request)
    if user is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"authenticated": False, "message": "Sign in to view recommendations."},
        )

    records = get_recent_recommendations(user["id"], limit=20)
    return {
        "authenticated": True,
        "count": len(records),
        "recommendations": records,
    }
