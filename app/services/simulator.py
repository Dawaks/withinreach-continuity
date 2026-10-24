"""What If simulator — single-person impact analysis (design §5).

Given one unavailable person, evaluate every asset where that person is a
primary responsible person, classify each affected asset, and compute a
simulated risk score. The simulation is purely hypothetical: it never writes
to the database and never changes the normal risk-scoring engine.
"""

from sqlalchemy.orm import Session

from app.models import Asset, Person
from app.schemas.simulation import SimulationAssetResult, SimulationResult
from app.services import risk_scoring
from app.services.responsibility_service import (
    backup_status_label,
    responsibility_type_label,
)

PARTIAL_PENALTY = 25
MAX_SCORE = 100


def _responsibility_label(resp) -> str:
    """e.g., 'Manages (Dami)'."""
    return f"{responsibility_type_label(resp.responsibility_type)} ({resp.primary_person.name})"


def _surviving_backups(resp, unavailable_id: int) -> list[str]:
    """Names of this responsibility's backup people who are NOT the unavailable person."""
    return [
        rb.backup_person.name
        for rb in resp.backup_people
        if rb.backup_person_id != unavailable_id
    ]


def _classify_asset(asset: Asset, unavailable_id: int):
    """Classify a single asset for the simulation.

    Returns a dict with classification, the responsibility buckets, surviving
    backup names, and an explanation — or None if the person is not a primary
    on this asset (asset not affected at all).
    """
    person_responsibilities = [
        r for r in asset.responsibilities if r.primary_person_id == unavailable_id
    ]
    if not person_responsibilities:
        return None  # person not connected as a primary -> asset not affected

    other_responsibilities = [
        r for r in asset.responsibilities if r.primary_person_id != unavailable_id
    ]

    lost: list[str] = []
    uncertain: list[str] = []
    covered: list[str] = []
    surviving_backup_names: list[str] = []

    for resp in person_responsibilities:
        label = _responsibility_label(resp)
        if resp.backup_status == "has_backup":
            survivors = _surviving_backups(resp, unavailable_id)
            if survivors:
                covered.append(f"{label} → backup: {', '.join(survivors)}")
                surviving_backup_names.extend(survivors)
            else:
                # has_backup but the only backup is the unavailable person
                lost.append(label)
        elif resp.backup_status == "backup_unknown":
            uncertain.append(label)
        else:  # no_backup
            lost.append(label)

    # Classification
    if not lost and not uncertain:
        classification = "unaffected"
    else:
        # Some coverage lost or uncertain. Orphaned only if nothing survives:
        # no covered responsibility of the person's, and no other primary person.
        if not covered and not other_responsibilities:
            classification = "orphaned"
        else:
            classification = "partially_affected"

    return {
        "classification": classification,
        "lost": lost,
        "uncertain": uncertain,
        "covered": covered,
        "surviving_backup_names": sorted(set(surviving_backup_names)),
        "has_other_primary": bool(other_responsibilities),
    }


def _build_explanation(person_name: str, info: dict) -> str:
    """Plain-language explanation referencing the actual backup relationships."""
    classification = info["classification"]
    if classification == "unaffected":
        names = ", ".join(info["surviving_backup_names"])
        return (
            f"{person_name} is unavailable, but {names} "
            f"{'is' if len(info['surviving_backup_names']) == 1 else 'are'} "
            f"recorded as backup, so this stays covered."
        )
    if classification == "orphaned":
        return (
            f"{person_name} is the only person recorded for this asset and no "
            f"surviving backup is assigned. Nobody else could step in."
        )
    # partially_affected
    parts = []
    if info["lost"]:
        parts.append(f"{len(info['lost'])} responsibility(ies) would be lost")
    if info["uncertain"]:
        parts.append(f"{len(info['uncertain'])} with unknown backup coverage")
    coverage_note = ""
    if info["covered"]:
        coverage_note = " Some responsibilities remain covered by a backup."
    elif info["has_other_primary"]:
        coverage_note = " Another person still has a role on this asset."
    return (
        f"{person_name} is unavailable: " + "; ".join(parts) + "." + coverage_note
    )


def _simulated_score(classification: str, current_score: int) -> int:
    if classification == "orphaned":
        return 100
    if classification == "partially_affected":
        return min(current_score + PARTIAL_PENALTY, MAX_SCORE)
    return current_score  # unaffected


def simulate_person_unavailable(
    db: Session, organization_id: int, person_id: int
) -> SimulationResult | None:
    """Simulate one person becoming unavailable. Returns None if person missing.

    Does not modify the database.
    """
    person = (
        db.query(Person)
        .filter(Person.organization_id == organization_id, Person.id == person_id)
        .first()
    )
    if person is None:
        return None

    assets = (
        db.query(Asset).filter(Asset.organization_id == organization_id).all()
    )

    # Current per-asset scores (Phase 4 engine, unchanged).
    current_results = {
        a.id: risk_scoring.calculate_asset_risk(
            a, a.responsibilities, a.documentation, a.dependency
        )
        for a in assets
    }

    affected: list[SimulationAssetResult] = []
    simulated_scores: list[int] = []

    for asset in assets:
        current = current_results[asset.id]
        info = _classify_asset(asset, person_id)
        if info is None:
            # Not affected — score unchanged, not listed.
            simulated_scores.append(current.score)
            continue

        sim_score = _simulated_score(info["classification"], current.score)
        simulated_scores.append(sim_score)

        affected.append(
            SimulationAssetResult(
                asset_id=asset.id,
                asset_name=asset.name,
                classification=info["classification"],
                current_score=current.score,
                simulated_score=sim_score,
                current_level=current.risk_level,
                simulated_level=risk_scoring.risk_level_from_score(sim_score),
                lost_responsibilities=info["lost"],
                uncertain_responsibilities=info["uncertain"],
                covered_responsibilities=info["covered"],
                surviving_backup_names=info["surviving_backup_names"],
                explanation=_build_explanation(person.name, info),
            )
        )

    # Current org risk (from current scores).
    current_level, current_expl, _ = risk_scoring.org_level_from_scores(
        [r.score for r in current_results.values()]
    )
    # Simulated org risk (from modified scores).
    sim_level, sim_expl, _ = risk_scoring.org_level_from_scores(simulated_scores)

    # Order affected assets: orphaned, partially_affected, unaffected; then score desc.
    order = {"orphaned": 0, "partially_affected": 1, "unaffected": 2}
    affected.sort(key=lambda a: (order[a.classification], -a.simulated_score, a.asset_name.lower()))

    return SimulationResult(
        person_id=person.id,
        person_name=person.name,
        person_role=person.role_title,
        current_org_level=current_level,
        simulated_org_level=sim_level,
        current_org_explanation=current_expl,
        simulated_org_explanation=sim_expl,
        affected_count=len(affected),
        affected_assets=affected,
    )
