# MongoDB collection catalogue

Executable strict validators and index definitions: `backend/app/schema.py`.
Every document has `_id` (UUID string), `schema_version: 1`, `created_at` (BSON UTC date).
All declared fields are required; unknown fields are rejected. New fields require an explicit
schema version change. Do not use zero/empty text as a substitute for unknown financial data:
keep incomplete form drafts in client state until valid, or version the schema for nullable values.
Money uses integer INR paise, energy integer Wh, capacity integer Wp, shares integer basis points.
Avoid floating-point money and raw meter identifiers in logs. Household connection references
should be tenant-scoped opaque/hash references, not publicly displayed account numbers.

| Collection | Document contents and relationships | Main indexes |
|---|---|---|
| users | Clerk subject, global role, active/disabled | unique auth_subject |
| communities | name, location, DISCOM | DISCOM + location |
| memberships | community → user, scoped role, status | unique community/user; user/status |
| households | community → user, connection reference, consumption, upfront/monthly caps, consent | unique community/connection; user/community |
| projects | community, lifecycle, capacity, estimated cost, eligible reserve balance | community/status |
| assessments | project, readiness/feasibility kind, named input values/units/sources, assumptions, rules version | project/kind/date |
| documents | community, owner, bill/agreement kind, private storage key, MIME, bytes, SHA-256, quarantine status | unique storage key; community/owner/kind |
| agreements | project, immutable document version, participants, signed document hashes, status | unique project/version |
| participations | project → household, agreed/paid/outstanding contribution, ownership and official credit shares, agreement and version | unique project/household |
| optimisation_runs | project, requester, strategy, immutable affordability/benefit input snapshot, model version, solver status, proposed allocations | project/strategy/date |
| exit_cases | project → household, participation snapshot version, obligation category, verified funding gap, alternative strategies and solver links, agreement/approval refs | project/household/status |
| approvals | exit case/project, actor, kind, decision, evidence document | unique exit/actor/kind |
| provider_updates | project → assigned provider, quotation/progress/generation, period and evidence description | project/kind/period |
| settlements | project → household/month, provenance, reliability, expected/recorded credits, expenses, verification state | unique project/household/period |
| financial_events | project → household, immutable payment/expense/refund/reserve event, evidence and timestamp | unique idempotency key; project/household/date |
| benefit_forecasts | project → household/month/model version, estimated credits/expenses and assumptions | unique project/household/period/version |
| explanations | solver run, model/prompt version, explanation text and review status | solver run/date |
| audit_events | community, actor, action, target, request ID | community/date; request ID |

Bounded snapshots and alternative arrays are embedded for consistent reads. Unbounded events,
settlements, documents and histories are separate referenced collections. Enforce request-size
and array-length limits in domain Pydantic DTOs before adding their endpoints; large optimiser
snapshots may need a separate input collection. MongoDB's document size limit is not an API budget.

## Validation split

MongoDB enforces required fields, field types, nonnegative money/energy, share range 0–10000,
role/status/strategy enums, MIME allowlist, file-size maximum and hash format; unique indexes
enforce identity/idempotency and participation/month uniqueness. There are no database foreign keys.

Future domain services must enforce reference existence and same-community relationships,
membership/ownership, canonical UUID/period formats, financial conservation, summed shares,
ledger-derived balances, financing terms, consent, eligibility, document safety and legal state
transitions. Validate a fully-paid exit has no outstanding amount and no assumed funding gap.
Prevent duplicate active exits with a transactional guard when creating an exit. Apply optimistic
version checks and multi-document transactions for accepted changes. Do not allow generic
patching of status, balances, roles, ownership or approved allocations.

This initial catalogue supports the supplied feature scope but is not a complete financial
model: tariff schedules, financing amortisation, time-varying generation and solver objective
definitions still need specified inputs and domain DTOs. Provider updates currently use a
minimal shared envelope; split them into kind-specific validated DTOs in the provider slice.
Retention of append-only audit/financial history is intentional; no TTL indexes delete it.
