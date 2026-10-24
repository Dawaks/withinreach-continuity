# Hackathon Submission

## Project Name
WithinReach Continuity

## Project Description
WithinReach Continuity is an AI-assisted technology dependency and continuity mapper for small community organizations — churches, nonprofits, student groups, and family businesses. It helps a non-technical coordinator map who manages each piece of technology, then automatically surfaces single points of failure, missing backup coverage, undocumented processes, personal-account dependencies, and single-device dependencies.

The application computes an explainable 0–100 continuity risk score for each technology asset, aggregates it into an organization-level risk level, and presents the results through a risk overview, an interactive dependency map, and a "What If?" simulator that shows what would happen if a specific person became unavailable. A guided discovery interview lets users enter their information in plain language, and recommendations suggest concrete next steps. Amazon Bedrock can optionally assist with interview interpretation and recommendation wording, but every AI feature has a rule-based fallback, and risk scoring is always deterministic. The application never asks for or stores passwords or other credentials.

## GitHub Repository
`[Add public repository URL]`

## Demo Video
`[Optional YouTube or Vimeo URL]`

## Suggested Demo Flow
1. **Dashboard** — show the organization's overall continuity risk (Critical for the demo data) and top risks.
2. **Risk overview** — show per-asset scores grouped by level, each with an explainable factor breakdown.
3. **Dependency Map** — show how one person (Dami) is a concentration of critical, no-backup responsibilities.
4. **What If? Simulator** — run the simulation for Dami and show which services become orphaned.
5. **Guided Discovery** — show a non-technical coordinator adding a dependency and confirming proposed records.
6. **Recommendations** — generate prioritized recommendations (rule-based by default; Bedrock-assisted if configured).

## Technologies Used
- **Python** with **FastAPI** (backend and routing)
- **Jinja2** server-rendered templates with lightweight CSS (Pico CSS + custom styles)
- **SQLite** via **SQLAlchemy** (data layer)
- **Cytoscape.js** (dependency map visualization)
- **Amazon Bedrock** via **boto3** (optional AI assistance)
- **pytest** (automated test suite; Bedrock mocked)
- Deterministic, server-side risk scoring engine (no AI in scoring)
