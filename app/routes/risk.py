"""Risk overview page route (design §11.7)."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import organization_service, risk_scoring
from app.templating import templates

router = APIRouter()

_LEVEL_ORDER = ["critical", "high", "medium", "low"]
_LEVEL_LABELS = {
    "critical": "Critical",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
}


@router.get("/risk")
def risk_overview(request: Request, db: Session = Depends(get_db)):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)

    org_risk = risk_scoring.calculate_org_risk(db, org.id)

    # Group asset risks by level, preserving the score-descending order.
    grouped = {level: [] for level in _LEVEL_ORDER}
    for r in org_risk.asset_risks:
        grouped[r.risk_level].append(r)

    return templates.TemplateResponse(
        request,
        "risk/overview.html",
        {
            "organization": org,
            "active": "risk",
            "org_risk": org_risk,
            "grouped": grouped,
            "level_order": _LEVEL_ORDER,
            "level_labels": _LEVEL_LABELS,
            "flash_messages": [],
        },
    )
