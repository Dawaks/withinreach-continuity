# Demo Script — WithinReach Continuity

A concise walkthrough for a short hackathon video (roughly 3–4 minutes).
Start from a clean demo reset so the numbers match.

---

## Opening (the problem)
"Small organizations — churches, nonprofits, student groups — run on technology, but the knowledge of how to operate it usually lives with one or two people. When that person is unavailable, nobody can run the livestream, or the website domain is stuck under someone's personal email. WithinReach Continuity finds those hidden dependencies before they become emergencies."

## Dashboard (overall risk)
"Here's Grace Community Church, our sample organization. Four people, eight technology assets. The dashboard immediately shows the overall continuity risk is **Critical**, with the top risks: the Sunday Livestream, the Wi-Fi Network, and the Donation Platform."

## Dependency Map (concentration around Dami)
"The dependency map shows people connected to the technology they manage. Notice **Dami** — larger and highlighted in red — because several critical systems depend on her with no backup. Red edges are no-backup responsibilities; dashed edges are backups. The single point of failure is obvious at a glance."

## What If? (run the Dami simulation)
"Let's ask: what happens if Dami is unavailable? Select Dami, run the simulation. The Wi-Fi Network and Presentation Laptop become **Orphaned** — nobody else can manage them. The Sunday Livestream is **Partially Affected**. Only the Church Website stays **Covered**, because Sarah is recorded as a backup. The organization's risk stays Critical, and now we can see exactly why."

## Guided Discovery (non-technical entry)
"How does a non-technical coordinator add this information? The guided interview asks plain-language questions — 'Who normally handles this? Could someone else fill in? Is there documentation?' — and proposes structured records. The user reviews and confirms before anything is saved. And it never asks for passwords or access codes."

## Recommendations (fallback + optional AI)
"Finally, recommendations. WithinReach generates prioritized, specific actions — for example, 'Train a backup person who can manage the Sunday Livestream; currently only Dami can.' This works with no AI at all using rule-based templates. With Amazon Bedrock enabled, the same risk profile produces more natural, context-aware wording — but AI never changes the risk scores, and credentials are never sent to the model."

## Closing (the value)
"WithinReach Continuity helps small organizations identify their operational technology dependencies — single points of failure, missing backups, undocumented processes — before an absence turns into an emergency. Within reach: solving what's close to you."
