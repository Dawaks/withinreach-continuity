"""Responsibility routes — create, edit, delete (from the asset detail page)."""

from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import asset_service, organization_service, responsibility_service
from app.services.responsibility_service import ValidationError

router = APIRouter()


def _redirect_asset(asset_id: int, error: str | None = None) -> RedirectResponse:
    url = f"/assets/{asset_id}"
    if error:
        url += f"?error={quote(error)}"
    return RedirectResponse(url=url, status_code=303)


@router.post("/assets/{asset_id}/responsibilities")
def create_responsibility(
    asset_id: int,
    request: Request,
    primary_person_id: int = Form(...),
    responsibility_type: str = Form(...),
    backup_status: str = Form(...),
    backup_person_ids: list[int] = Form(default=[]),
    db: Session = Depends(get_db),
):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)
    asset = asset_service.get_asset(db, org.id, asset_id)
    if asset is None:
        return RedirectResponse(url="/assets", status_code=303)

    try:
        responsibility_service.create_responsibility(
            db,
            asset_id=asset_id,
            primary_person_id=primary_person_id,
            responsibility_type=responsibility_type,
            backup_status=backup_status,
            backup_person_ids=backup_person_ids,
        )
    except ValidationError as e:
        return _redirect_asset(asset_id, str(e))
    return _redirect_asset(asset_id)


@router.post("/assets/{asset_id}/responsibilities/{responsibility_id}/edit")
def update_responsibility(
    asset_id: int,
    responsibility_id: int,
    responsibility_type: str = Form(...),
    backup_status: str = Form(...),
    backup_person_ids: list[int] = Form(default=[]),
    db: Session = Depends(get_db),
):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)
    asset = asset_service.get_asset(db, org.id, asset_id)
    if asset is None:
        return RedirectResponse(url="/assets", status_code=303)

    responsibility = responsibility_service.get_responsibility(db, asset_id, responsibility_id)
    if responsibility is None:
        return _redirect_asset(asset_id, "Responsibility not found.")

    try:
        responsibility_service.update_responsibility(
            db,
            responsibility,
            responsibility_type=responsibility_type,
            backup_status=backup_status,
            backup_person_ids=backup_person_ids,
        )
    except ValidationError as e:
        return _redirect_asset(asset_id, str(e))
    return _redirect_asset(asset_id)


@router.post("/assets/{asset_id}/responsibilities/{responsibility_id}/delete")
def delete_responsibility(
    asset_id: int,
    responsibility_id: int,
    db: Session = Depends(get_db),
):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)
    responsibility = responsibility_service.get_responsibility(db, asset_id, responsibility_id)
    if responsibility is not None:
        responsibility_service.delete_responsibility(db, responsibility)
    return _redirect_asset(asset_id)
