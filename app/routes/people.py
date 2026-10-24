"""People routes — list, detail, add, edit, delete."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import input_validation
from app.services import organization_service, person_service, responsibility_service
from app.templating import templates

router = APIRouter()


def _validate_person(name: str, role_title: str, email: str) -> str | None:
    """Return a friendly error message, or None if valid."""
    if not name.strip():
        return "Name is required."
    result = input_validation.validate_fields(
        {
            "name": (name, "name"),
            "role_title": (role_title, "title"),
            "email": (email, "email"),
        }
    )
    if not result.valid:
        return next(iter(result.errors.values()))
    return None


@router.get("/people")
def people_list(request: Request, db: Session = Depends(get_db)):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)

    people = person_service.get_all_people(db, org.id)
    rows = [
        {
            "person": p,
            "primary_count": person_service.primary_responsibility_count(p),
            "backup_count": person_service.backup_responsibility_count(p),
        }
        for p in people
    ]
    return templates.TemplateResponse(
        request,
        "people/list.html",
        {"organization": org, "active": "people", "rows": rows, "flash_messages": []},
    )


@router.get("/people/new")
def person_new(request: Request, db: Session = Depends(get_db)):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)
    return templates.TemplateResponse(
        request,
        "people/form.html",
        {
            "organization": org,
            "active": "people",
            "person": None,
            "form_action": "/people/new",
            "error": None,
            "flash_messages": [],
        },
    )


@router.post("/people/new")
def person_create(
    request: Request,
    name: str = Form(""),
    role_title: str = Form(""),
    email: str = Form(""),
    db: Session = Depends(get_db),
):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)

    error = _validate_person(name, role_title, email)
    if error:
        return templates.TemplateResponse(
            request,
            "people/form.html",
            {
                "organization": org,
                "active": "people",
                "person": {"name": name, "role_title": role_title, "email": email},
                "form_action": "/people/new",
                "error": error,
                "flash_messages": [],
            },
            status_code=400,
        )

    person = person_service.create_person(
        db, org.id, name=name, role_title=role_title, email=email
    )
    return RedirectResponse(url=f"/people/{person.id}", status_code=303)


@router.get("/people/{person_id}")
def person_detail(person_id: int, request: Request, db: Session = Depends(get_db)):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)

    person = person_service.get_person(db, org.id, person_id)
    if person is None:
        return templates.TemplateResponse(
            request,
            "not_found.html",
            {"organization": org, "active": "people", "what": "person",
             "back_url": "/people", "flash_messages": []},
            status_code=404,
        )

    spof = person_service.single_point_of_failure_assets(db, person)
    return templates.TemplateResponse(
        request,
        "people/detail.html",
        {
            "organization": org,
            "active": "people",
            "person": person,
            "spof": spof,
            "type_label": responsibility_service.responsibility_type_label,
            "status_label": responsibility_service.backup_status_label,
            "flash_messages": [],
        },
    )


@router.get("/people/{person_id}/edit")
def person_edit(person_id: int, request: Request, db: Session = Depends(get_db)):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)
    person = person_service.get_person(db, org.id, person_id)
    if person is None:
        return RedirectResponse(url="/people", status_code=303)
    return templates.TemplateResponse(
        request,
        "people/form.html",
        {
            "organization": org,
            "active": "people",
            "person": person,
            "form_action": f"/people/{person.id}/edit",
            "error": None,
            "flash_messages": [],
        },
    )


@router.post("/people/{person_id}/edit")
def person_update(
    person_id: int,
    request: Request,
    name: str = Form(""),
    role_title: str = Form(""),
    email: str = Form(""),
    db: Session = Depends(get_db),
):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)
    person = person_service.get_person(db, org.id, person_id)
    if person is None:
        return RedirectResponse(url="/people", status_code=303)

    error = _validate_person(name, role_title, email)
    if error:
        return templates.TemplateResponse(
            request,
            "people/form.html",
            {
                "organization": org,
                "active": "people",
                "person": person,
                "form_action": f"/people/{person.id}/edit",
                "error": error,
                "flash_messages": [],
            },
            status_code=400,
        )

    person_service.update_person(db, person, name=name, role_title=role_title, email=email)
    return RedirectResponse(url=f"/people/{person.id}", status_code=303)


@router.get("/people/{person_id}/delete")
def person_delete_confirm(person_id: int, request: Request, db: Session = Depends(get_db)):
    """Show a confirmation page warning which responsibilities would be affected."""
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)
    person = person_service.get_person(db, org.id, person_id)
    if person is None:
        return RedirectResponse(url="/people", status_code=303)

    impact = person_service.delete_impact(person)
    return templates.TemplateResponse(
        request,
        "people/delete_confirm.html",
        {
            "organization": org,
            "active": "people",
            "person": person,
            "impact": impact,
            "type_label": responsibility_service.responsibility_type_label,
            "flash_messages": [],
        },
    )


@router.post("/people/{person_id}/delete")
def person_delete(person_id: int, db: Session = Depends(get_db)):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)
    person = person_service.get_person(db, org.id, person_id)
    if person is not None:
        person_service.delete_person(db, person)
    return RedirectResponse(url="/people", status_code=303)
