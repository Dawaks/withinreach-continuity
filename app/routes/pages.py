"""Jinja2 page routes for WithinReach Continuity.

Phase 3: organization setup flow, dashboard, people list, asset list, and
labeled placeholder pages for features implemented in later phases.
"""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from urllib.parse import quote

from app.database import get_db
from app.demo.reset import reset_demo_data
from app.demo.seed import seed_demo_data
from app.security import input_validation
from app.services import asset_service, organization_service, person_service, risk_scoring
from app.templating import templates

router = APIRouter()


@router.get("/")
def index(db: Session = Depends(get_db)):
    """Route to setup if no organization exists, otherwise the dashboard."""
    if organization_service.organization_exists(db):
        return RedirectResponse(url="/dashboard", status_code=303)
    return RedirectResponse(url="/setup", status_code=303)


@router.get("/setup")
def setup_form(request: Request, db: Session = Depends(get_db)):
    """Show the organization setup form. If an org already exists, go to dashboard."""
    if organization_service.organization_exists(db):
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(
        request,
        "organization_setup.html",
        {"organization": None, "active": "setup", "flash_messages": []},
    )


@router.post("/setup")
def setup_submit(
    request: Request,
    name: str = Form(...),
    org_type: str = Form(...),
    size: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    """Create the organization and redirect to the dashboard."""
    if organization_service.organization_exists(db):
        return RedirectResponse(url="/dashboard", status_code=303)

    result = input_validation.validate_fields(
        {
            "name": (name, "name"),
            "size": (size, "size"),
            "description": (description, "description"),
        }
    )
    if not name.strip():
        result.errors["name"] = "Name is required."
        result.valid = False
    if not result.valid:
        return templates.TemplateResponse(
            request,
            "organization_setup.html",
            {
                "organization": None,
                "active": "setup",
                "error": next(iter(result.errors.values())),
                "flash_messages": [],
            },
            status_code=400,
        )

    organization_service.create_organization(
        db, name=name, org_type=org_type, size=size, description=description
    )
    return RedirectResponse(url="/dashboard", status_code=303)


@router.post("/setup/load-demo")
def setup_load_demo(db: Session = Depends(get_db)):
    """Seed the Grace Community Church demo dataset and go to the dashboard."""
    seed_demo_data(db)
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/demo/reset")
def demo_reset_confirm(request: Request, db: Session = Depends(get_db)):
    """Confirmation page before the destructive demo reset."""
    org = organization_service.get_organization(db)
    return templates.TemplateResponse(
        request,
        "demo_reset_confirm.html",
        {
            "organization": org,
            "active": "dashboard",
            "flash_messages": [],
        },
    )


@router.post("/demo/reset")
def demo_reset(db: Session = Depends(get_db)):
    """Reset the database to the approved Grace Community Church demo dataset."""
    reset_demo_data(db)
    message = quote("Demo data restored successfully.")
    return RedirectResponse(url=f"/dashboard?flash={message}", status_code=303)


@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    """The main dashboard with counts, quick actions, and messaging."""
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)

    # Optional one-shot flash message passed via query param (e.g., after reset).
    flash_messages = []
    flash = request.query_params.get("flash")
    if flash:
        flash_messages.append(("success", flash))

    people_count = person_service.count_people(db, org.id)
    asset_count = asset_service.count_assets(db, org.id)

    org_risk = risk_scoring.calculate_org_risk(db, org.id)

    # Build a short plain-language explanation for each top risk from its factors.
    top_risks = [
        {
            "asset_id": r.asset_id,
            "asset_name": r.asset_name,
            "score": r.score,
            "risk_level": r.risk_level,
            "summary": _top_factor_summary(r),
        }
        for r in org_risk.top_risks
    ]

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "organization": org,
            "active": "dashboard",
            "people_count": people_count,
            "asset_count": asset_count,
            "org_risk": org_risk,
            "top_risks": top_risks,
            "flash_messages": flash_messages,
        },
    )


def _top_factor_summary(asset_risk) -> str:
    """Compose a short explanation from an asset's most significant factors."""
    # Skip the criticality base factor, then take the highest-point issues.
    issues = [
        f for f in asset_risk.contributing_factors
        if f.detail != "Criticality base score"
    ]
    issues.sort(key=lambda f: -f.points)
    labels = [f.label for f in issues[:2]]
    if not labels:
        return f"{asset_risk.criticality.capitalize()} asset with good coverage."
    return "; ".join(labels) + "."


