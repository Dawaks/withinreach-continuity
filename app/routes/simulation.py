"""What If simulator routes (design §11.9).

GET /simulator  — person selector form
POST /simulator — run the simulation and render results (no DB writes)
"""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import organization_service, person_service, simulator
from app.templating import templates

router = APIRouter()


@router.get("/simulator")
def simulator_form(request: Request, db: Session = Depends(get_db)):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)

    people = person_service.get_all_people(db, org.id)
    return templates.TemplateResponse(
        request,
        "simulator.html",
        {
            "organization": org,
            "active": "simulator",
            "people": people,
            "result": None,
            "selected_person_id": None,
            "error": None,
            "flash_messages": [],
        },
    )


@router.post("/simulator")
def simulator_run(
    request: Request,
    person_id: int = Form(...),
    db: Session = Depends(get_db),
):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)

    people = person_service.get_all_people(db, org.id)
    result = simulator.simulate_person_unavailable(db, org.id, person_id)

    error = None
    if result is None:
        error = "Please select a valid person."

    return templates.TemplateResponse(
        request,
        "simulator.html",
        {
            "organization": org,
            "active": "simulator",
            "people": people,
            "result": result,
            "selected_person_id": person_id,
            "error": error,
            "flash_messages": [],
        },
    )
