"""Dependency map graph-data service (design §7).

Builds Cytoscape-compatible JSON (nodes + edges) and a single-point-of-failure
summary from the current database records. Risk levels/scores come from the
existing Phase 4 engine — never recalculated here or in JavaScript.
"""

from sqlalchemy.orm import Session

from app.models import Asset, Person
from app.services import asset_service, risk_scoring

# Category -> organizational function label (deduplicated via these keys).
FUNCTION_LABELS = {
    "livestream": "Livestream / Audio-Visual",
    "website": "Website / Domain",
    "social_media": "Social Media",
    "network_wifi": "Wi-Fi / Network",
    "data_storage": "Shared Files / Cloud Storage",
    "communication": "Email / Communication",
    "payment": "Payment / Donation",
    "other": "Other",
}


def _person_risk_load(critical_high_count: int, uncovered_count: int) -> str:
    """Overall dependency/risk load for a person, derived from their exposure."""
    if critical_high_count >= 2 and uncovered_count >= 1:
        return "high"
    if critical_high_count >= 1 or uncovered_count >= 1:
        return "medium"
    return "low"


def build_graph_data(db: Session, organization_id: int) -> dict:
    """Return {'nodes': [...], 'edges': [...]} for Cytoscape."""
    people = (
        db.query(Person)
        .filter(Person.organization_id == organization_id)
        .order_by(Person.id)
        .all()
    )
    assets = (
        db.query(Asset)
        .filter(Asset.organization_id == organization_id)
        .order_by(Asset.id)
        .all()
    )

    # Per-asset risk via the Phase 4 engine.
    asset_risk = {
        a.id: risk_scoring.calculate_asset_risk(
            a, a.responsibilities, a.documentation, a.dependency
        )
        for a in assets
    }

    # --- Person exposure stats (critical/high asset count, uncovered count) ---
    person_stats = {
        p.id: {"critical_high": set(), "uncovered": 0} for p in people
    }
    for a in assets:
        level = asset_risk[a.id].risk_level
        for resp in a.responsibilities:
            pid = resp.primary_person_id
            if pid not in person_stats:
                continue
            if level in ("critical", "high"):
                person_stats[pid]["critical_high"].add(a.id)
            if resp.backup_status == "no_backup":
                person_stats[pid]["uncovered"] += 1

    nodes = []
    edges = []

    # --- Person nodes ---
    for p in people:
        ch = len(person_stats[p.id]["critical_high"])
        unc = person_stats[p.id]["uncovered"]
        nodes.append(
            {
                "data": {
                    "id": f"person-{p.id}",
                    "entity_id": p.id,
                    "type": "person",
                    "label": p.name,
                    "role": p.role_title or "",
                    "critical_asset_count": ch,
                    "uncovered_count": unc,
                    "risk_load": _person_risk_load(ch, unc),
                }
            }
        )

    # --- Function (category) nodes, deduplicated to categories actually in use ---
    used_categories = []
    for a in assets:
        if a.category not in used_categories:
            used_categories.append(a.category)
    for cat in used_categories:
        nodes.append(
            {
                "data": {
                    "id": f"func-{cat}",
                    "type": "function",
                    "label": FUNCTION_LABELS.get(cat, asset_service.category_label(cat)),
                }
            }
        )

    # --- Asset nodes + asset->function edges ---
    for a in assets:
        risk = asset_risk[a.id]
        nodes.append(
            {
                "data": {
                    "id": f"asset-{a.id}",
                    "entity_id": a.id,
                    "type": "asset",
                    "label": a.name,
                    "category": a.category,
                    "criticality": a.criticality,
                    "risk_score": risk.score,
                    "risk_level": risk.risk_level,
                }
            }
        )
        edges.append(
            {
                "data": {
                    "id": f"assetfunc-{a.id}",
                    "source": f"asset-{a.id}",
                    "target": f"func-{a.category}",
                    "edge_type": "category",
                }
            }
        )

    # --- Responsibility edges (primary + backup) ---
    for a in assets:
        level = asset_risk[a.id].risk_level
        for resp in a.responsibilities:
            # Primary edge: person -> asset
            edges.append(
                {
                    "data": {
                        "id": f"primary-{resp.id}",
                        "source": f"person-{resp.primary_person_id}",
                        "target": f"asset-{a.id}",
                        "edge_type": "primary",
                        "responsibility_type": resp.responsibility_type,
                        "backup_status": resp.backup_status,
                        "risk_level": level,
                        "label": {"manages": "M", "understands": "U", "administers": "A"}.get(
                            resp.responsibility_type, ""
                        ),
                    }
                }
            )
            # Backup edges: backup person -> asset (dashed)
            for rb in resp.backup_people:
                edges.append(
                    {
                        "data": {
                            "id": f"backup-{rb.id}",
                            "source": f"person-{rb.backup_person_id}",
                            "target": f"asset-{a.id}",
                            "edge_type": "backup",
                            "responsibility_type": resp.responsibility_type,
                            "backup_status": resp.backup_status,
                            "label": "backup",
                        }
                    }
                )

    return {"nodes": nodes, "edges": edges}


def single_point_of_failure_summary(db: Session, organization_id: int) -> list[dict]:
    """Compute, per person, the concentration of important dependencies.

    Returns people who are primary on >=1 Critical/High asset, sorted by the
    number of no-backup critical/high responsibilities then by count, so the
    biggest concentration (e.g., Dami) is first. Fully data-driven.
    """
    people = (
        db.query(Person)
        .filter(Person.organization_id == organization_id)
        .all()
    )
    assets = (
        db.query(Asset)
        .filter(Asset.organization_id == organization_id)
        .all()
    )
    asset_risk = {
        a.id: risk_scoring.calculate_asset_risk(
            a, a.responsibilities, a.documentation, a.dependency
        )
        for a in assets
    }

    summary = []
    for p in people:
        important_assets = []
        uncovered = 0
        for resp in p.primary_responsibilities:
            level = asset_risk[resp.asset_id].risk_level
            if level in ("critical", "high"):
                if resp.asset.name not in [ia["name"] for ia in important_assets]:
                    important_assets.append(
                        {"name": resp.asset.name, "asset_id": resp.asset_id, "level": level}
                    )
                if resp.backup_status == "no_backup":
                    uncovered += 1
        if important_assets:
            summary.append(
                {
                    "person_id": p.id,
                    "person_name": p.name,
                    "role": p.role_title or "",
                    "important_asset_count": len(important_assets),
                    "uncovered_count": uncovered,
                    "assets": important_assets,
                }
            )

    summary.sort(
        key=lambda s: (-s["uncovered_count"], -s["important_asset_count"], s["person_name"].lower())
    )
    return summary
