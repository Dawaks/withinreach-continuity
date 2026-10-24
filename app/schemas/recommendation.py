"""Continuity recommendation schemas (design §8.3)."""

from pydantic import BaseModel


class Recommendation(BaseModel):
    """A single continuity recommendation."""

    priority: str                       # critical | high | medium | low
    asset_name: str
    person_name: str | None = None
    risk_description: str               # the risk being addressed
    recommendation: str                 # the recommended action
    rationale: str                      # short reason why it matters
