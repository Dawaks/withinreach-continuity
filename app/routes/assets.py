"""Asset routes — list, detail, add, edit, delete, documentation, dependency."""

from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.asset import ASSET_CATEGORIES, CRITICALITY_LEVELS
from app.security import input_validation
from app.services import (
    asset_service,
    organization_service,
    person_service,
    responsibility_service,
    risk_scoring,
)
from app.templating import templates

router = APIRouter()


def _validate_asset_fields(name: str, category: str, criticality: str, description: str) -> str | None:
    """Return a friendly error message, or None if valid."""
    if not name.strip():
        return "Name is required."
    if not asset_service.is_valid_category(category):
        return "Please choose a valid category."
    if not asset_service.is_valid_criticality(criticality):
        return "Please choose a valid criticality level."
    result = input_validation.validate_fields(
        {"name": (name, "asset_name"), "description": (description, "description")}
    )
    if not result.valid:
        return next(iter(result.errors.values()))
    return None


def _category_choices():
    return [(c, asset_service.category_label(c)) for c in ASSET_CATEGORIES]


@router.get("/assets")
def assets_list(request: Request, db: Session = Depends(get_db)):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)

    assets = asset_service.get_all_assets(db, org.id)
    rows = []
    for a in assets:
        result = risk_scoring.calculate_asset_risk(
            a, a.responsibilities, a.documentation, a.dependency
        )
        rows.append(
            {
                "asset": a,
                "category_label": asset_service.category_label(a.category),
                "risk": result,
            }
        )
    return templates.TemplateResponse(
        request,
        "assets/list.html",
        {"organization": org, "active": "assets", "rows": rows, "flash_messages": []},
    )


@router.get("/assets/new")
def asset_new(request: Request, db: Session = Depends(get_db)):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)
    return templates.TemplateResponse(
        request,
        "assets/form.html",
        {
            "organization": org,
            "active": "assets",
            "asset": None,
            "form_action": "/assets/new",
            "categories": _category_choices(),
            "criticalities": CRITICALITY_LEVELS,
            "error": None,
            "flash_messages": [],
        },
    )


@router.post("/assets/new")
def asset_create(
    request: Request,
    name: str = Form(""),
    category: str = Form(""),
    criticality: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)

    error = _validate_asset_fields(name, category, criticality, description)
    if error:
        return templates.TemplateResponse(
            request,
            "assets/form.html",
            {
                "organization": org,
                "active": "assets",
                "asset": {"name": name, "category": category,
                          "criticality": criticality, "description": description},
                "form_action": "/assets/new",
                "categories": _category_choices(),
                "criticalities": CRITICALITY_LEVELS,
                "error": error,
                "flash_messages": [],
            },
            status_code=400,
        )

    asset = asset_service.create_asset(
        db, org.id, name=name, category=category,
        criticality=criticality, description=description,
    )
    return RedirectResponse(url=f"/assets/{asset.id}", status_code=303)


@router.get("/assets/{asset_id}")
def asset_detail(asset_id: int, request: Request, db: Session = Depends(get_db)):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)

    asset = asset_service.get_asset(db, org.id, asset_id)
    if asset is None:
        return templates.TemplateResponse(
            request,
            "not_found.html",
            {"organization": org, "active": "assets", "what": "asset",
             "back_url": "/assets", "flash_messages": []},
            status_code=404,
        )

    risk = risk_scoring.calculate_asset_risk(
        asset, asset.responsibilities, asset.documentation, asset.dependency
    )
    all_people = person_service.get_all_people(db, org.id)

    return templates.TemplateResponse(
        request,
        "assets/detail.html",
        {
            "organization": org,
            "active": "assets",
            "asset": asset,
            "risk": risk,
            "category_label": asset_service.category_label(asset.category),
            "all_people": all_people,
            "categories": _category_choices(),
            "criticalities": CRITICALITY_LEVELS,
            "type_label": responsibility_service.responsibility_type_label,
            "status_label": responsibility_service.backup_status_label,
            "error": request.query_params.get("error"),
            "flash_messages": [],
        },
    )


@router.get("/assets/{asset_id}/edit")
def asset_edit(asset_id: int, request: Request, db: Session = Depends(get_db)):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)
    asset = asset_service.get_asset(db, org.id, asset_id)
    if asset is None:
        return RedirectResponse(url="/assets", status_code=303)
    return templates.TemplateResponse(
        request,
        "assets/form.html",
        {
            "organization": org,
            "active": "assets",
            "asset": asset,
            "form_action": f"/assets/{asset.id}/edit",
            "categories": _category_choices(),
            "criticalities": CRITICALITY_LEVELS,
            "error": None,
            "flash_messages": [],
        },
    )


@router.post("/assets/{asset_id}/edit")
def asset_update(
    asset_id: int,
    request: Request,
    name: str = Form(""),
    category: str = Form(""),
    criticality: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)
    asset = asset_service.get_asset(db, org.id, asset_id)
    if asset is None:
        return RedirectResponse(url="/assets", status_code=303)

    error = _validate_asset_fields(name, category, criticality, description)
    if error:
        return templates.TemplateResponse(
            request,
            "assets/form.html",
            {
                "organization": org,
                "active": "assets",
                "asset": asset,
                "form_action": f"/assets/{asset.id}/edit",
                "categories": _category_choices(),
                "criticalities": CRITICALITY_LEVELS,
                "error": error,
                "flash_messages": [],
            },
            status_code=400,
        )

    asset_service.update_asset(
        db, asset, name=name, category=category,
        criticality=criticality, description=description,
    )
    return RedirectResponse(url=f"/assets/{asset.id}", status_code=303)


@router.get("/assets/{asset_id}/delete")
def asset_delete_confirm(asset_id: int, request: Request, db: Session = Depends(get_db)):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)
    asset = asset_service.get_asset(db, org.id, asset_id)
    if asset is None:
        return RedirectResponse(url="/assets", status_code=303)
    return templates.TemplateResponse(
        request,
        "assets/delete_confirm.html",
        {
            "organization": org,
            "active": "assets",
            "asset": asset,
            "type_label": responsibility_service.responsibility_type_label,
            "flash_messages": [],
        },
    )


@router.post("/assets/{asset_id}/delete")
def asset_delete(asset_id: int, db: Session = Depends(get_db)):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)
    asset = asset_service.get_asset(db, org.id, asset_id)
    if asset is not None:
        asset_service.delete_asset(db, asset)
    return RedirectResponse(url="/assets", status_code=303)


# ---------- Documentation ----------

@router.post("/assets/{asset_id}/documentation")
def set_documentation(
    asset_id: int,
    status: str = Form(""),
    location_note: str = Form(""),
    db: Session = Depends(get_db),
):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)
    asset = asset_service.get_asset(db, org.id, asset_id)
    if asset is None:
        return RedirectResponse(url="/assets", status_code=303)
    if not asset_service.is_valid_documentation_status(status):
        return RedirectResponse(
            url=f"/assets/{asset_id}?error=Invalid+documentation+status",
            status_code=303,
        )
    result = input_validation.validate_fields({"location_note": (location_note, "note")})
    if not result.valid:
        return RedirectResponse(
            url=f"/assets/{asset_id}?error={quote(result.errors['location_note'])}",
            status_code=303,
        )
    asset_service.set_documentation(db, asset, status=status, location_note=location_note)
    return RedirectResponse(url=f"/assets/{asset_id}", status_code=303)


# ---------- Dependency flags ----------

@router.post("/assets/{asset_id}/dependency")
def set_dependency(
    asset_id: int,
    personal_account: str = Form("off"),
    personal_account_note: str = Form(""),
    single_device: str = Form("off"),
    single_device_note: str = Form(""),
    db: Session = Depends(get_db),
):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)
    asset = asset_service.get_asset(db, org.id, asset_id)
    if asset is None:
        return RedirectResponse(url="/assets", status_code=303)

    result = input_validation.validate_fields(
        {
            "personal_account_note": (personal_account_note, "note"),
            "single_device_note": (single_device_note, "note"),
        }
    )
    if not result.valid:
        return RedirectResponse(
            url=f"/assets/{asset_id}?error={quote(next(iter(result.errors.values())))}",
            status_code=303,
        )
    asset_service.set_dependency(
        db,
        asset,
        depends_on_personal_account=(personal_account == "on"),
        personal_account_note=personal_account_note,
        depends_on_single_device=(single_device == "on"),
        single_device_note=single_device_note,
    )
    return RedirectResponse(url=f"/assets/{asset_id}", status_code=303)
