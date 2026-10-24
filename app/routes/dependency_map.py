"""Dependency map routes (design §11.8).

GET /map                  — the page (Cytoscape loads graph via JS)
GET /api/dependency-map   — graph JSON for Cytoscape
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import dependency_map_service, organization_service
from app.templating import templates

router = APIRouter()


@router.get("/map")
def dependency_map_page(request: Request, db: Session = Depends(get_db)):
    org = organization_service.get_organization(db)
    if org is None:
        return RedirectResponse(url="/setup", status_code=303)

    spof = dependency_map_service.single_point_of_failure_summary(db, org.id)
    return templates.TemplateResponse(
        request,
        "dependency_map.html",
        {
            "organization": org,
            "active": "map",
            "spof": spof,
            "flash_messages": [],
        },
    )


@router.get("/api/dependency-map")
def dependency_map_data(db: Session = Depends(get_db)):
    org = organization_service.get_organization(db)
    if org is None:
        return JSONResponse({"nodes": [], "edges": []})
    return JSONResponse(dependency_map_service.build_graph_data(db, org.id))
