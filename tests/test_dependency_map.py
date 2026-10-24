"""Tests for the dependency map graph-data service (design §7)."""

from app.models import Organization
from app.services import risk_scoring
from app.services.dependency_map_service import (
    build_graph_data,
    single_point_of_failure_summary,
)


def _nodes_of_type(graph, node_type):
    return [n for n in graph["nodes"] if n["data"]["type"] == node_type]


def _edges_of_type(graph, edge_type):
    return [e for e in graph["edges"] if e["data"]["edge_type"] == edge_type]


def test_all_people_produce_person_nodes(seeded_db):
    org = seeded_db.query(Organization).first()
    graph = build_graph_data(seeded_db, org.id)
    person_nodes = _nodes_of_type(graph, "person")
    assert len(person_nodes) == 4
    labels = {n["data"]["label"] for n in person_nodes}
    assert labels == {"Dami", "James", "Sarah", "Pastor John"}


def test_all_assets_produce_asset_nodes(seeded_db):
    org = seeded_db.query(Organization).first()
    graph = build_graph_data(seeded_db, org.id)
    asset_nodes = _nodes_of_type(graph, "asset")
    assert len(asset_nodes) == 8


def test_function_nodes_deduplicated(seeded_db):
    org = seeded_db.query(Organization).first()
    graph = build_graph_data(seeded_db, org.id)
    func_nodes = _nodes_of_type(graph, "function")
    # Demo categories used: livestream, website, social_media, network_wifi,
    # payment, data_storage, other. (Audio System is 'livestream' too.)
    cats = sorted(n["data"]["id"] for n in func_nodes)
    # livestream appears once despite 2 assets using it.
    assert cats.count("func-livestream") == 1
    # Distinct categories in demo data:
    expected = {
        "func-livestream", "func-website", "func-social_media",
        "func-network_wifi", "func-payment", "func-data_storage", "func-other",
    }
    assert set(cats) == expected


def test_primary_edges_generated(seeded_db):
    org = seeded_db.query(Organization).first()
    graph = build_graph_data(seeded_db, org.id)
    primary = _edges_of_type(graph, "primary")
    # 10 responsibilities in the demo data -> 10 primary edges.
    assert len(primary) == 10


def test_backup_edges_generated(seeded_db):
    org = seeded_db.query(Organization).first()
    graph = build_graph_data(seeded_db, org.id)
    backup = _edges_of_type(graph, "backup")
    # 5 backup associations in the demo data -> 5 backup edges.
    assert len(backup) == 5
    # Backup edges connect a person to an asset.
    for e in backup:
        assert e["data"]["source"].startswith("person-")
        assert e["data"]["target"].startswith("asset-")


def test_category_edges_generated(seeded_db):
    org = seeded_db.query(Organization).first()
    graph = build_graph_data(seeded_db, org.id)
    cat_edges = _edges_of_type(graph, "category")
    # One asset->function edge per asset.
    assert len(cat_edges) == 8


def test_no_backup_status_carried(seeded_db):
    org = seeded_db.query(Organization).first()
    graph = build_graph_data(seeded_db, org.id)
    primary = _edges_of_type(graph, "primary")
    statuses = {e["data"]["backup_status"] for e in primary}
    assert "no_backup" in statuses
    assert "has_backup" in statuses
    assert "backup_unknown" in statuses


def test_risk_metadata_matches_phase4(seeded_db):
    org = seeded_db.query(Organization).first()
    graph = build_graph_data(seeded_db, org.id)
    # Compare each asset node's risk to the Phase 4 engine directly.
    org_risk = risk_scoring.calculate_org_risk(seeded_db, org.id)
    by_name = {r.asset_name: r for r in org_risk.asset_risks}
    for node in _nodes_of_type(graph, "asset"):
        d = node["data"]
        expected = by_name[d["label"]]
        assert d["risk_score"] == expected.score
        assert d["risk_level"] == expected.risk_level


def test_person_spof_counts_calculated(seeded_db):
    org = seeded_db.query(Organization).first()
    graph = build_graph_data(seeded_db, org.id)
    dami = next(n for n in _nodes_of_type(graph, "person") if n["data"]["label"] == "Dami")
    # Dami is primary on Livestream (critical), Wi-Fi (critical risk), Website (medium),
    # Presentation Laptop (high). Critical/High assets: Livestream(85 crit),
    # Wi-Fi(75 crit), Presentation Laptop(58 high) = 3. Website is medium (30).
    assert dami["data"]["critical_asset_count"] == 3
    # No-backup primary responsibilities for Dami: Livestream, Wi-Fi, Presentation Laptop = 3.
    assert dami["data"]["uncovered_count"] == 3


def test_spof_summary_dami_first(seeded_db):
    org = seeded_db.query(Organization).first()
    summary = single_point_of_failure_summary(seeded_db, org.id)
    assert summary, "Expected at least one dependency concentration"
    # Dami has the most no-backup critical/high responsibilities -> first.
    assert summary[0]["person_name"] == "Dami"
    assert summary[0]["uncovered_count"] == 3
    assert summary[0]["important_asset_count"] == 3


def test_graph_has_expected_totals(seeded_db):
    org = seeded_db.query(Organization).first()
    graph = build_graph_data(seeded_db, org.id)
    assert len(_nodes_of_type(graph, "person")) == 4
    assert len(_nodes_of_type(graph, "asset")) == 8
    assert len(_nodes_of_type(graph, "function")) == 7
    assert len(_edges_of_type(graph, "primary")) == 10
    assert len(_edges_of_type(graph, "backup")) == 5
    assert len(_edges_of_type(graph, "category")) == 8
