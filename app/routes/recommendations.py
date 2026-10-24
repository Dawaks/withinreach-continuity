"""Recommendations routes (design §8.3, §11.10).

GET  /recommendations  — page with a Generate button
POST /recommendations  — generate and display (AI-assisted or rule-based)
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import organization_service, recommendation_service
from app.templating import templates

router = APIRouter()


@router.get("/recommendations")
def recommendations_page(request: Request, db: Session = Depends(get_db)):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)
    return templates.TemplateResponse(
        request,
        "recommendations.html",
        {
            "organization": org,
            "active": "recommendations",
            "mode": None,
            "recommendations": None,
            "flash_messages": [],
        },
    )


@router.post("/recommendations")
def recommendations_generate(request: Request, db: Session = Depends(get_db)):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)

    mode, recommendations = recommendation_service.get_recommendations(db, org.id)

    return templates.TemplateResponse(
        request,
        "recommendations.html",
        {
            "organization": org,
            "active": "recommendations",
            "mode": mode,  # "ai" | "rule_based"
            "recommendations": recommendations,
            "flash_messages": [],
        },
    )
