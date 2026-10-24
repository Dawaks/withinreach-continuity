# WithinReach Continuity

**Find hidden technology dependencies and single points of failure before they become emergencies.**

WithinReach Continuity is an AI-assisted technology dependency and continuity mapper for small community organizations — churches, nonprofits, student groups, and family businesses.

## Demo Video

[Watch the WithinReach Continuity demo](https://youtu.be/D3Y-yMP7bXE))

---

## The Problem

Small organizations rely on technology — livestreaming, websites, social media, Wi-Fi, shared files, online giving — but the knowledge of how to operate and recover that technology usually lives with one or two people. When that person is unavailable (illness, moving away, stepping down), the organization discovers too late that nobody else can run the livestream, the domain is under someone's personal email, or critical files live on a single laptop. The result is lost services and, sometimes, permanently lost digital assets.

Most coordinators are not IT professionals and would not know what to enter into a blank form. They need a guided tool that surfaces these risks in plain language and tells them what to do next.

## The Solution

WithinReach Continuity helps an organization map its technology dependencies and automatically identifies:

- **Technology dependencies** — who relies on what
- **Single points of failure** — responsibilities with no backup
- **Missing backup coverage** — unknown or absent backups
- **Missing documentation** — knowledge that lives only in someone's head
- **Personal-account dependencies** — services tied to a personal (not organization-owned) account
- **Single-device dependencies** — services that rely on one specific device

It then produces an explainable risk score, a visual dependency map, a "What If?" simulator, and prioritized recommendations.

## Key Features

- **Explainable risk scoring** — a deterministic 0–100 score per asset with a visible breakdown of every contributing factor. No black box, no AI involved in scoring.
- **Dependency map** — an interactive People → Assets → Functions graph that makes concentrations of knowledge and single points of failure visually obvious.
- **What If? simulator** — select a person and instantly see which services would be unaffected, partially affected, or orphaned if they became unavailable.
- **Guided discovery** — a plain-language interview that turns simple answers into proposed records for the user to review and confirm.
- **AI-assisted recommendations** — optional Amazon Bedrock assistance that turns the risk profile into specific, actionable advice.
- **Rule-based fallback** — every AI feature has a fallback that works with no AI configured, so the product is fully usable offline.
- **Credential-safe design** — the application never asks for or stores passwords, keys, tokens, Wi-Fi passwords, or recovery codes, and blocks accidental secret entry.

## Architecture

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python) |
| Templates | Jinja2 server-rendered pages |
| Database | SQLite via SQLAlchemy |
| Visualization | Cytoscape.js (via CDN) |
| AI (optional) | Amazon Bedrock via `boto3` |
| Risk engine | Deterministic, server-side, fully unit-tested |

The code follows a clean `routes → services → data/models` separation. Risk scores are always computed on demand from current data and never stored.

## AI Design

- **AI is optional.** The application runs fully with `AI_ENABLED=false`.
- **Structured fallback works without AI.** The guided interview and recommendations both have rule-based paths.
- **AI never controls risk scoring.** Scoring is deterministic and server-side.
- **The user reviews AI proposals.** AI-suggested interview records are proposals only — nothing is saved until the user confirms.
- **Secret validation runs before any Bedrock transmission.** Free text is checked for likely credentials first; blocked input is never sent to the model. The flow is strictly `user input → secret validation → Bedrock`.
- **The Bedrock model is configurable.** The model ID and region come from environment variables; if the model is unavailable, the app falls back gracefully.

## Security

WithinReach Continuity does **not** require and will **not** store:

- passwords
- API keys
- access codes
- tokens
- recovery codes
- Wi-Fi passwords

Free-text fields are validated server-side to block likely credential values (for example `password is …`), while allowing benign security vocabulary (for example "Password reset procedure is documented in the IT binder."). User-provided content is rendered with Jinja2 autoescaping, and length limits bound every input.

## Running Locally

1. **Clone the repository**
   ```bash
   git clone <your-repository-url>
   cd withinreach-continuity
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate
   ```

3. **Install requirements**
   ```bash
   pip install -r requirements.txt
   ```

4. **(Optional) configure environment**
   ```bash
   cp .env.example .env
   ```
   Defaults work out of the box. AI is disabled by default (`AI_ENABLED=false`).

5. **Start the server**
   ```bash
   uvicorn app.main:app --reload
   ```

6. **Open the app**

   Visit `http://127.0.0.1:8000` in your browser. On first run, the sample Grace Community Church dataset is seeded automatically.

## Demo Dataset

The application ships with a fictional demo organization, **Grace Community Church** (4 people, 8 technology assets, with intentional continuity gaps so the value is immediately visible). It contains no real people or credentials. You can restore it at any time from the dashboard via **Reset to demo data**.

## Testing

The project includes an automated test suite (`pytest`) covering risk scoring, backup relationships, the What If simulator, the dependency-map data, the guided interview, AI fallback behavior, and security controls. Bedrock is mocked in tests — no live AWS access is required.

```bash
pytest
```

## License

Released under the [MIT License](LICENSE).
