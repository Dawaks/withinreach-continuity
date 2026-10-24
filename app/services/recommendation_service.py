"""Continuity recommendation service (design §8.3, §8.4).

Builds a secret-free risk profile from the Phase 4 risk engine, then produces
recommendations either via Bedrock (when enabled) or a rule-based fallback that
always works. The risk engine is the source of truth; this service never
recomputes risk.
"""

import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Asset, Organization
from app.schemas.recommendation import Recommendation
from app.services import risk_scoring

logger = logging.getLogger(__name__)

_PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def build_risk_profile(db: Session, organization_id: int) -> dict:
    """Build a secret-free structured risk profile for recommendation generation.

    Excludes passwords, credentials, tokens, personal email addresses, and
    free-text notes. Only includes what's needed for continuity advice.
    """
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    assets = (
        db.query(Asset).filter(Asset.organization_id == organization_id).all()
    )

    asset_entries = []
    for asset in assets:
        risk = risk_scoring.calculate_asset_risk(
            asset, asset.responsibilities, asset.documentation, asset.dependency
        )
        responsible = []
        backup_gaps = []
        for r in asset.responsibilities:
            responsible.append(
                {
                    "person_name": r.primary_person.name,  # name only, never email
                    "responsibility_type": r.responsibility_type,
                    "backup_status": r.backup_status,
                    "backup_people": [
                        rb.backup_person.name for rb in r.backup_people
                    ],
                }
            )
            if r.backup_status in ("no_backup", "backup_unknown"):
                backup_gaps.append(
                    {
                        "person_name": r.primary_person.name,
                        "responsibility_type": r.responsibility_type,
                        "backup_status": r.backup_status,
                    }
                )

        asset_entries.append(
            {
                "asset_name": asset.name,
                "category": asset.category,
                "criticality": asset.criticality,
                "risk_level": risk.risk_level,
                "risk_score": risk.score,
                "contributing_factors": [
                    f"{f.label} ({f.points} pts)" for f in risk.contributing_factors
                ],
                "responsible_people": responsible,
                "backup_gaps": backup_gaps,
                "documentation_status": asset.documentation.status if asset.documentation else "unknown",
                "depends_on_personal_account": bool(
                    asset.dependency and asset.dependency.depends_on_personal_account
                ),
                "depends_on_single_device": bool(
                    asset.dependency and asset.dependency.depends_on_single_device
                ),
            }
        )

    # Sort so the AI sees the worst assets first.
    asset_entries.sort(key=lambda a: -a["risk_score"])

    return {
        "organization": {"name": org.name if org else "", "type": org.org_type if org else ""},
        "assets": asset_entries,
    }


def _rule_based_recommendations(profile: dict) -> list[Recommendation]:
    """Deterministic templates referencing real asset/person names (design §8.4)."""
    recs: list[Recommendation] = []

    # Base verb forms so "who can {verb} {asset}" reads naturally.
    verb_forms = {"manages": "manage", "understands": "understand", "administers": "administer"}

    for asset in profile["assets"]:
        asset_name = asset["asset_name"]
        level = asset["risk_level"]

        for gap in asset["backup_gaps"]:
            person = gap["person_name"]
            verb = verb_forms.get(gap["responsibility_type"], gap["responsibility_type"])
            if gap["backup_status"] == "no_backup":
                recs.append(
                    Recommendation(
                        priority=level,
                        asset_name=asset_name,
                        person_name=person,
                        risk_description=f"{person} is the only person who can {verb} {asset_name}.",
                        recommendation=(
                            f"Identify and train a backup person who can {verb} {asset_name}. "
                            f"Currently {person} has this responsibility with no backup."
                        ),
                        rationale=(
                            f"If {person} is unavailable, {asset_name} would have no one to cover it."
                        ),
                    )
                )
            else:  # backup_unknown
                recs.append(
                    Recommendation(
                        priority=level,
                        asset_name=asset_name,
                        person_name=person,
                        risk_description=f"Backup coverage for {asset_name} is unknown.",
                        recommendation=(
                            f"Confirm whether another person can {verb} {asset_name}. "
                            "Backup coverage is currently unknown."
                        ),
                        rationale="Unknown coverage hides a possible single point of failure.",
                    )
                )

        if asset["documentation_status"] in ("no", "unknown"):
            recs.append(
                Recommendation(
                    priority=level,
                    asset_name=asset_name,
                    person_name=None,
                    risk_description=f"{asset_name} has little or no documentation.",
                    recommendation=(
                        f"Create simple documentation for {asset_name} so the process does "
                        "not depend on one person's memory."
                    ),
                    rationale="Documentation lets a new person take over without the original person.",
                )
            )

        if asset["depends_on_personal_account"]:
            recs.append(
                Recommendation(
                    priority=level,
                    asset_name=asset_name,
                    person_name=None,
                    risk_description=f"{asset_name} depends on a personal account.",
                    recommendation=(
                        f"Move management of {asset_name} from a personal account to an "
                        "organization-owned account where practical."
                    ),
                    rationale="Personal accounts can be lost when an individual leaves.",
                )
            )

        if asset["depends_on_single_device"]:
            recs.append(
                Recommendation(
                    priority=level,
                    asset_name=asset_name,
                    person_name=None,
                    risk_description=f"{asset_name} depends on one specific device.",
                    recommendation=(
                        f"Reduce reliance on one device for {asset_name} by preparing a "
                        "backup device or documented recovery option."
                    ),
                    rationale="A lost or broken device would take the service down.",
                )
            )

    recs.sort(key=lambda r: _PRIORITY_ORDER.get(r.priority, 99))
    return recs


def get_recommendations(db: Session, organization_id: int) -> tuple[str, list[Recommendation]]:
    """Return (mode, recommendations) where mode is 'ai' or 'rule_based'.

    Tries Bedrock when enabled; on any AIError falls back to rule-based.
    """
    profile = build_risk_profile(db, organization_id)

    if settings.AI_ENABLED:
        from app.services import ai_service
        try:
            recs = ai_service.generate_recommendations(profile)
            recs.sort(key=lambda r: _PRIORITY_ORDER.get(r.priority, 99))
            return "ai", recs
        except ai_service.AIError as e:
            logger.warning("AI recommendations failed, using rule-based fallback: %s", e)

    return "rule_based", _rule_based_recommendations(profile)
