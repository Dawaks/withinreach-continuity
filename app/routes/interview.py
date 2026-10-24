"""Guided dependency discovery interview routes (non-AI, Phase 8).

Flow:
  GET  /interview                 -> intro page
  GET  /interview/category/{idx}  -> one category question page
  POST /interview/review          -> build proposals from accumulated answers, render review
  POST /interview/save            -> persist confirmed records
"""

import json

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import secret_check
from app.services import interview_service, organization_service
from app.templating import templates

router = APIRouter()


@router.get("/interview")
def interview_intro(request: Request, db: Session = Depends(get_db)):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)
    return templates.TemplateResponse(
        request,
        "interview/intro.html",
        {
            "organization": org,
            "active": "interview",
            "category_count": interview_service.CATEGORY_COUNT,
            "flash_messages": [],
        },
    )


@router.get("/interview/category/{index}")
def interview_category(index: int, request: Request, db: Session = Depends(get_db)):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)

    category = interview_service.get_category(index)
    if category is None:
        # Past the last category -> go to review.
        return RedirectResponse(url="/interview/review", status_code=303)

    return templates.TemplateResponse(
        request,
        "interview/category.html",
        {
            "organization": org,
            "active": "interview",
            "category": category,
            "index": index,
            "step_number": index + 1,
            "category_count": interview_service.CATEGORY_COUNT,
            "is_last": index == interview_service.CATEGORY_COUNT - 1,
            "flash_messages": [],
        },
    )


@router.get("/interview/review")
def interview_review_get(request: Request, db: Session = Depends(get_db)):
    """If reached via GET (e.g., direct nav), render an empty review that reads
    accumulated answers from sessionStorage client-side and POSTs them back."""
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)
    return templates.TemplateResponse(
        request,
        "interview/collect.html",
        {"organization": org, "active": "interview", "flash_messages": []},
    )


@router.post("/interview/review")
def interview_review_post(
    request: Request,
    answers_json: str = Form("[]"),
    db: Session = Depends(get_db),
):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)

    try:
        all_answers = json.loads(answers_json)
    except json.JSONDecodeError:
        all_answers = []

    proposals = []
    secret_blocked = False
    for entry in all_answers:
        category_key = entry.get("category_key")
        try:
            proposed = interview_service.interpret_answers(category_key, entry)
        except interview_service.SecretBlockedError:
            secret_blocked = True
            continue
        if proposed is None:
            continue

        # Duplicate detection (person + asset) against existing records.
        existing_asset = interview_service.find_existing_asset(db, org.id, proposed.asset_name)
        primary_name = proposed.responsibilities[0].primary_person_name if proposed.responsibilities else ""
        existing_primary = interview_service.find_existing_person(db, org.id, primary_name)

        backup_name = ""
        existing_backup = None
        if proposed.responsibilities and proposed.responsibilities[0].backup_people_names:
            backup_name = proposed.responsibilities[0].backup_people_names[0]
            existing_backup = interview_service.find_existing_person(db, org.id, backup_name)

        resp = proposed.responsibilities[0] if proposed.responsibilities else None
        proposals.append(
            {
                "category_label": next(
                    (c["label"] for c in interview_service.CATEGORIES if c["key"] == category_key),
                    category_key,
                ),
                "asset_name": proposed.asset_name,
                "asset_category": proposed.asset_category,
                "asset_criticality": proposed.asset_criticality,
                "asset_description": proposed.asset_description or "",
                "asset_existing_id": existing_asset.id if existing_asset else "",
                "asset_existing_name": existing_asset.name if existing_asset else "",
                "primary_person_name": primary_name,
                "primary_person_role": (proposed.people[0].get("role_title") if proposed.people else "") or "",
                "primary_existing_id": existing_primary.id if existing_primary else "",
                "responsibility_type": resp.responsibility_type if resp else "manages",
                "backup_status": resp.backup_status if resp else "backup_unknown",
                "backup_person_name": backup_name,
                "backup_existing_id": existing_backup.id if existing_backup else "",
                "documentation_status": proposed.documentation_status,
                "documentation_location": proposed.documentation_location or "",
                "depends_on_personal_account": proposed.depends_on_personal_account,
                "depends_on_single_device": proposed.depends_on_single_device,
            }
        )

    return templates.TemplateResponse(
        request,
        "interview/review.html",
        {
            "organization": org,
            "active": "interview",
            "proposals": proposals,
            "error": secret_check.USER_MESSAGE if secret_blocked else None,
            "flash_messages": [],
        },
    )


@router.post("/interview/save")
async def interview_save(request: Request, db: Session = Depends(get_db)):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)

    form = await request.form()

    # Reconstruct records from the review form. Each accepted row has an index i.
    indices = sorted(
        {
            int(k.split("-")[1])
            for k in form.keys()
            if k.startswith("accept-") and form.get(k) == "on"
        }
    )

    records = []
    for i in indices:
        def g(field, default=""):
            return (form.get(f"{field}-{i}") or default)

        # Person: "existing" choice uses the existing id; "new" creates.
        primary_choice = g("primary_choice", "new")
        backup_choice = g("backup_choice", "new")
        asset_choice = g("asset_choice", "new")

        records.append(
            {
                "asset_name": g("asset_name"),
                "asset_category": g("asset_category", "other"),
                "asset_criticality": g("asset_criticality", "medium"),
                "asset_description": g("asset_description") or None,
                "asset_existing_id": g("asset_existing_id") if asset_choice == "existing" else "",
                "primary_person_name": g("primary_person_name"),
                "primary_person_role": g("primary_person_role") or None,
                "primary_person_existing_id": g("primary_existing_id") if primary_choice == "existing" else "",
                "responsibility_type": g("responsibility_type", "manages"),
                "backup_status": g("backup_status", "backup_unknown"),
                "backup_person_name": g("backup_person_name"),
                "backup_person_existing_id": g("backup_existing_id") if backup_choice == "existing" else "",
                "documentation_status": g("documentation_status", "unknown"),
                "documentation_location": g("documentation_location") or None,
                "depends_on_personal_account": g("depends_on_personal_account") == "on",
                "personal_account_note": g("personal_account_note") or None,
                "depends_on_single_device": g("depends_on_single_device") == "on",
                "single_device_note": g("single_device_note") or None,
            }
        )

    try:
        interview_service.save_confirmed_records(db, org.id, records)
    except interview_service.SaveError:
        # Re-render the review with the blocking message. Rebuild proposals from
        # the submitted records so the user can edit.
        proposals = _records_to_proposals(records)
        return templates.TemplateResponse(
            request,
            "interview/review.html",
            {
                "organization": org,
                "active": "interview",
                "proposals": proposals,
                "error": secret_check.USER_MESSAGE,
                "flash_messages": [],
            },
            status_code=400,
        )

    return RedirectResponse(url="/dashboard", status_code=303)


def _records_to_proposals(records: list[dict]) -> list[dict]:
    """Shape saved-record dicts back into the review template's proposal shape."""
    proposals = []
    for r in records:
        proposals.append(
            {
                "category_label": "",
                "asset_name": r.get("asset_name", ""),
                "asset_category": r.get("asset_category", "other"),
                "asset_criticality": r.get("asset_criticality", "medium"),
                "asset_description": r.get("asset_description") or "",
                "asset_existing_id": r.get("asset_existing_id", ""),
                "asset_existing_name": "",
                "primary_person_name": r.get("primary_person_name", ""),
                "primary_person_role": r.get("primary_person_role") or "",
                "primary_existing_id": r.get("primary_person_existing_id", ""),
                "responsibility_type": r.get("responsibility_type", "manages"),
                "backup_status": r.get("backup_status", "backup_unknown"),
                "backup_person_name": r.get("backup_person_name", ""),
                "backup_existing_id": r.get("backup_person_existing_id", ""),
                "documentation_status": r.get("documentation_status", "unknown"),
                "documentation_location": r.get("documentation_location") or "",
                "depends_on_personal_account": bool(r.get("depends_on_personal_account")),
                "depends_on_single_device": bool(r.get("depends_on_single_device")),
            }
        )
    return proposals
