"""What If simulation result schemas.

Simulation is purely hypothetical analysis. These models carry the computed
result from the simulator service to the template. Nothing here is persisted.
"""

from pydantic import BaseModel


class SimulationAssetResult(BaseModel):
    """Per-asset outcome of a single-person simulation."""

    asset_id: int
    asset_name: str
    classification: str                 # orphaned | partially_affected | unaffected
    current_score: int
    simulated_score: int
    current_level: str                  # critical | high | medium | low
    simulated_level: str
    lost_responsibilities: list[str]
    uncertain_responsibilities: list[str]
    covered_responsibilities: list[str]
    surviving_backup_names: list[str]
    explanation: str


class SimulationResult(BaseModel):
    """Full result of simulating one person becoming unavailable."""

    person_id: int
    person_name: str
    person_role: str | None
    current_org_level: str
    simulated_org_level: str
    current_org_explanation: str
    simulated_org_explanation: str
    affected_count: int
    affected_assets: list[SimulationAssetResult]
