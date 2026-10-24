"""Risk scoring result schemas.

These are plain Pydantic models used to carry computed risk results from the
scoring service to the routes/templates. Risk scores are never stored — they
are computed on demand (design §3.5, §4).
"""

from pydantic import BaseModel


class ContributingFactor(BaseModel):
    """A single explainable contributor to an asset's risk score."""

    label: str      # e.g., "Critical asset"
    points: int     # e.g., 45
    detail: str     # e.g., "Criticality base score"


class AssetRiskResult(BaseModel):
    """Per-asset risk result with an explainable breakdown."""

    asset_id: int
    asset_name: str
    category: str
    criticality: str
    score: int                                  # 0-100
    risk_level: str                             # critical | high | medium | low
    contributing_factors: list[ContributingFactor]


class OrgRiskResult(BaseModel):
    """Organization-level risk result."""

    risk_level: str                             # critical | high | medium | low
    explanation: str
    score_distribution: dict[str, int]          # {critical: n, high: n, medium: n, low: n}
    asset_risks: list[AssetRiskResult]          # all assets, sorted by score desc
    top_risks: list[AssetRiskResult]            # highest-scoring assets (up to 3)
