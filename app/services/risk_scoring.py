"""Deterministic, explainable continuity risk scoring engine.

No AI is involved. Given current data, the same input always produces the same
output. Scores are computed on demand and never stored (design §4).

Weights, caps, and thresholds are fixed per design §4.2 and §4.4.
"""

from sqlalchemy.orm import Session

from app.models import (
    Asset,
    AssetDependency,
    AssetDocumentation,
    Responsibility,
)
from app.schemas.risk import AssetRiskResult, ContributingFactor, OrgRiskResult

# --- Weights (design §4.2) ---
CRITICALITY_BASE = {"critical": 45, "high": 30, "medium": 18, "low": 8}
BACKUP_PENALTY = {"no_backup": 15, "backup_unknown": 7, "has_backup": 0}
BACKUP_PENALTY_CAP = 30
DOCUMENTATION_PENALTY = {"no": 15, "unknown": 7, "yes": 0}
PERSONAL_ACCOUNT_PENALTY = 15
SINGLE_DEVICE_PENALTY = 10
MAX_SCORE = 100

# --- Thresholds (design §4.2) ---
# 0-24 Low, 25-49 Medium, 50-74 High, 75-100 Critical
def risk_level_from_score(score: int) -> str:
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


# Backwards-compatible private alias used within this module.
_risk_level_from_score = risk_level_from_score


def org_level_from_scores(scores: list[int]) -> tuple[str, str, dict[str, int]]:
    """Given a list of per-asset scores, return (level, explanation, distribution).

    Uses the same Phase 4 aggregation rules. Used by the What If simulator to
    recompute organization risk from a modified (simulated) set of scores
    without touching the database.
    """
    distribution = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for s in scores:
        distribution[risk_level_from_score(s)] += 1
    level, explanation = _org_risk_level(distribution)
    return level, explanation, distribution


_RESPONSIBILITY_VERB = {
    "manages": "management",
    "understands": "understanding",
    "administers": "administration",
}


def calculate_asset_risk(
    asset: Asset,
    responsibilities: list[Responsibility],
    documentation: AssetDocumentation | None,
    dependency: AssetDependency | None,
) -> AssetRiskResult:
    """Compute the 0-100 risk score for a single asset with an explainable breakdown."""
    factors: list[ContributingFactor] = []

    # Step 1 — criticality base score
    base = CRITICALITY_BASE.get(asset.criticality, 0)
    factors.append(
        ContributingFactor(
            label=f"{asset.criticality.capitalize()} asset",
            points=base,
            detail="Criticality base score",
        )
    )

    # Step 2 — backup penalty per responsibility, capped at 30
    backup_total = 0
    backup_factors: list[ContributingFactor] = []
    for resp in responsibilities:
        penalty = BACKUP_PENALTY.get(resp.backup_status, 0)
        if penalty == 0:
            continue
        backup_total += penalty
        primary_name = resp.primary_person.name if resp.primary_person else "someone"
        verb = _RESPONSIBILITY_VERB.get(resp.responsibility_type, resp.responsibility_type)
        if resp.backup_status == "no_backup":
            label = f"No backup for {primary_name}'s {verb} responsibility"
            detail = f"{primary_name} is the only person for this responsibility"
        else:  # backup_unknown
            label = f"Backup unknown for {primary_name}'s {verb} responsibility"
            detail = f"It is not known whether anyone can cover for {primary_name}"
        backup_factors.append(
            ContributingFactor(label=label, points=penalty, detail=detail)
        )

    # Apply the cap. If capping reduced the total, scale the displayed factors
    # down proportionally is overkill for the MVP — instead we keep the
    # individual factors but note the cap by trimming the reported points so
    # the displayed factor points sum to the capped contribution.
    capped_backup = min(backup_total, BACKUP_PENALTY_CAP)
    if backup_total > BACKUP_PENALTY_CAP and backup_factors:
        # Reduce the reported points so they sum to the cap, keeping the
        # explanation honest about the capped contribution.
        remaining = capped_backup
        n = len(backup_factors)
        for i, bf in enumerate(backup_factors):
            # Distribute the capped total across factors (last one absorbs remainder).
            share = remaining // (n - i)
            bf.points = share
            remaining -= share
    factors.extend(backup_factors)

    # Step 3 — documentation penalty
    doc_status = documentation.status if documentation else "unknown"
    doc_penalty = DOCUMENTATION_PENALTY.get(doc_status, 0)
    if doc_penalty > 0:
        if doc_status == "no":
            label, detail = "No documentation", "No documentation exists for this asset"
        else:  # unknown
            label, detail = "Documentation unknown", "It is not known whether documentation exists"
        factors.append(ContributingFactor(label=label, points=doc_penalty, detail=detail))

    # Step 4 — dependency penalties
    personal_penalty = 0
    single_device_penalty = 0
    if dependency:
        if dependency.depends_on_personal_account:
            personal_penalty = PERSONAL_ACCOUNT_PENALTY
            factors.append(
                ContributingFactor(
                    label="Depends on personal account",
                    points=PERSONAL_ACCOUNT_PENALTY,
                    detail="Relies on a personal (not organization-owned) account",
                )
            )
        if dependency.depends_on_single_device:
            single_device_penalty = SINGLE_DEVICE_PENALTY
            factors.append(
                ContributingFactor(
                    label="Depends on single device",
                    points=SINGLE_DEVICE_PENALTY,
                    detail="Relies on one specific device",
                )
            )

    # Step 5 — final score (capped at 100)
    raw = base + capped_backup + doc_penalty + personal_penalty + single_device_penalty
    score = min(raw, MAX_SCORE)
    risk_level = _risk_level_from_score(score)

    return AssetRiskResult(
        asset_id=asset.id,
        asset_name=asset.name,
        category=asset.category,
        criticality=asset.criticality,
        score=score,
        risk_level=risk_level,
        contributing_factors=factors,
    )


def _org_risk_level(distribution: dict[str, int]) -> tuple[str, str]:
    """Apply org-level aggregation rules (design §4.4). Returns (level, explanation)."""
    critical = distribution["critical"]
    high = distribution["high"]
    medium = distribution["medium"]

    if critical >= 1:
        return (
            "critical",
            f"{critical} critical-risk asset(s) make the organization's continuity risk Critical.",
        )
    if high >= 3:
        return (
            "critical",
            f"{high} high-risk assets accumulate to make the organization's continuity risk Critical.",
        )
    if high >= 1:
        return (
            "high",
            f"{high} high-risk asset(s) make the organization's continuity risk High.",
        )
    if medium >= 1:
        return (
            "medium",
            f"{medium} medium-risk asset(s) make the organization's continuity risk Medium.",
        )
    return ("low", "All assets are low risk. The organization's continuity risk is Low.")


def calculate_org_risk(db: Session, organization_id: int) -> OrgRiskResult:
    """Compute per-asset risks and aggregate to an organization-level result."""
    assets = (
        db.query(Asset)
        .filter(Asset.organization_id == organization_id)
        .all()
    )

    asset_risks: list[AssetRiskResult] = []
    for asset in assets:
        result = calculate_asset_risk(
            asset=asset,
            responsibilities=asset.responsibilities,
            documentation=asset.documentation,
            dependency=asset.dependency,
        )
        asset_risks.append(result)

    # Sort by score descending, then name for stable ordering.
    asset_risks.sort(key=lambda r: (-r.score, r.asset_name.lower()))

    distribution = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for r in asset_risks:
        distribution[r.risk_level] += 1

    level, explanation = _org_risk_level(distribution)
    top_risks = asset_risks[:3]

    return OrgRiskResult(
        risk_level=level,
        explanation=explanation,
        score_distribution=distribution,
        asset_risks=asset_risks,
        top_risks=top_risks,
    )
