from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database import (
    delete_recommendation,
    get_dashboard_stats,
    get_recent_recommendations,
    get_recommendation_by_id,
)
from app.routes.auth import get_session_user, require_login

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """Main landing page introducing PocketSmart AI features and quick planners."""
    user = get_session_user(request)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"user": user},
    )


@router.get("/testimonials", response_class=HTMLResponse)
async def testimonials_page(request: Request):
    """Showcases real user reviews and success stories across all planning domains."""
    user = get_session_user(request)
    return templates.TemplateResponse(
        request=request,
        name="testimonials.html",
        context={"user": user},
    )


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """User dashboard showing analytics, recent activity, and quick access to planners."""
    user = require_login(request)
    stats = get_dashboard_stats(user["id"])
    recent_history = get_recent_recommendations(user["id"], limit=6)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": user,
            "stats": stats,
            "history": recent_history,
        },
    )


@router.get("/history", response_class=HTMLResponse)
async def history_page(request: Request, category: Optional[str] = Query(None)):
    """Retrieves user's past recommendation queries and results with optional category filtering."""
    user = require_login(request)
    history = get_recent_recommendations(user["id"], limit=50, category=category)
    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={
            "user": user,
            "history": history,
            "selected_category": category or "All",
        },
    )


@router.post("/history/delete/{rec_id}")
async def delete_history_item(request: Request, rec_id: int):
    """Deletes a saved plan from history."""
    user = require_login(request)
    delete_recommendation(rec_id, user["id"])
    return RedirectResponse(url="/history", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/recommendations-details", response_class=HTMLResponse)
async def recommendation_details(request: Request, id: Optional[int] = Query(None)):
    """Displays detailed AI-generated product recommendations for a specific saved plan."""
    user = get_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    if id:
        rec = get_recommendation_by_id(id, user["id"])
        if rec:
            return templates.TemplateResponse(
                request=request,
                name="recommendations.html",
                context={
                    "user": user,
                    "category": rec["category"],
                    "result": rec["result_payload"],
                    "input_data": rec["input_payload"],
                    "rec_id": rec["id"],
                    "created_at": rec["created_at"],
                },
            )

    # If no ID provided, get the latest one or redirect to dashboard
    recent = get_recent_recommendations(user["id"], limit=1)
    if recent:
        latest = recent[0]
        return templates.TemplateResponse(
            request=request,
            name="recommendations.html",
            context={
                "user": user,
                "category": latest["category"],
                "result": latest["result_payload"],
                "input_data": latest["input_payload"],
                "rec_id": latest["id"],
                "created_at": latest["created_at"],
            },
        )

    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
