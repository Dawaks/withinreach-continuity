"""FastAPI application entrypoint for WithinReach Continuity.

Phase 1 — Foundation: creates the app, mounts static files, registers page
routes, and initializes the SQLite database tables on startup.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, SessionLocal, engine

# Import models so they are registered with Base.metadata before create_all.
from app import models  # noqa: F401
from app.demo.seed import seed_demo_data
from app.routes import (
    assets,
    dependency_map,
    interview,
    pages,
    people,
    recommendations,
    responsibilities,
    risk,
    simulation,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all database tables on startup.
    Base.metadata.create_all(bind=engine)

    # Seed demo data if enabled. seed_demo_data is idempotent, so restarting
    # the app will not create duplicate records.
    if settings.SEED_DEMO_DATA:
        db = SessionLocal()
        try:
            seed_demo_data(db)
        finally:
            db.close()

    yield


app = FastAPI(title="WithinReach Continuity", lifespan=lifespan)

# Serve static assets (CSS, JS).
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register page routes.
app.include_router(pages.router)
app.include_router(people.router)
app.include_router(assets.router)
app.include_router(responsibilities.router)
app.include_router(risk.router)
app.include_router(simulation.router)
app.include_router(dependency_map.router)
app.include_router(interview.router)
app.include_router(recommendations.router)
