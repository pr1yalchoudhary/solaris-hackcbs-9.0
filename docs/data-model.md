# MongoDB development data model

The canonical document models, MongoDB validators and index definitions are in
`backend/app/schema.py`. All 29 collections are initialised explicitly with
`python -m app.init_db` from `backend/`. No business records are seeded.

## Document contract

Every document has a UUID-string `_id`, `schema_version: 1`, and BSON UTC `created_at`.
References use UUID strings. Unknown fields are rejected. Required fields are listed
in the executable schemas; optional fields are declared separately. Nullable numeric
inputs represent missing information; zero is a measured/declared zero, not a default.
Amounts are integer INR paise, energy integer Wh, capacity integer Wp, ownership and
credit fractions integer basis points (0–10000). Integers have explicit safe bounds;
months use YYYY-MM, hashes are SHA-256 hex strings, arrays have at most 1000 entries.
Input/output snapshots carry names, values, units and sources for reproducibility.

| Collection | Purpose and references | Indexes beyond `_id` |
|---|---|---|
| users | Clerk subject, global role and status | unique subject |
| communities | Location, DISCOM, registration reference | DISCOM/location |
| memberships | Community → user, scoped role and status | unique community/user; user/status |
| households | Community → user, opaque connection reference, consumption and affordability caps | unique community/connection; user/community |
| electricity_bills | Household → private document, month, manual/OCR source and verification | household/month; unique document |
| projects | Community, assigned provider, capacity/cost estimates, lifecycle | community/status; provider/status |
| assessments | Project readiness/feasibility, source inputs, output metrics, versioned assumptions | project/kind/date |
| documents | Community/owner, private object key, type, size, checksum, quarantine status | unique object key; community/owner/kind |
| agreements | Project, immutable agreement/document version and affected participants | unique project/version |
| consents | Agreement → user, signed document hash, decision/time; retain decision history | agreement/user/time |
| participations | Project → household and agreement, versioned participation status | unique project/household |
| contributions | Participation/household/project, accepted or proposed commitment and version | unique project/household/version |
| financing_obligations | Household/project, liable party, principal, outstanding balance as-of time, terms and monthly due | project/household/status |
| ownership_records | Household/project share and agreement version, optional exit transaction link | unique project/household/version; partial unique active share per household/project |
| vnm_allocations | Project-wide proposed/approved official credit schedule, approval evidence, version/effective date | unique project/version; partial unique active schedule per project |
| optimisation_runs | Project/requester, strategy, immutable source snapshot, solver result and proposed allocations | project/strategy/date |
| exit_cases | Participation/version, obligation category, verified funding gap/evidence, strategies, impacts, consent/approval links | project/household/status; partial unique open case per participation |
| approvals | Project, target type/ID, actor, decision, evidence and time | unique target/actor/kind |
| exit_transactions | Explicit execution, selected alternative, agreements/approvals, ledger links, before/after ownership | unique idempotency key; unique exit case |
| provider_updates | Assigned provider/project, installation stage, timestamp and evidence | project/stage/time |
| quotations | Provider/project, version, capacity, cost, generation estimate, assumptions, validity | unique project/provider/version |
| generation_records | Provider/project, month, measured energy, provenance and verification | unique project/month/source |
| settlements | Household/project/month, expected and recorded credits, expenses, source and reliability | unique project/household/month |
| financial_events | Append-only contributions/payments/credits/expenses/refunds/reserve/transfer amounts, evidence, reversals | unique idempotency key; project/household/time |
| reserve_funds | Project reserve balance snapshot, agreement eligibility rules, version/as-of date | unique project |
| benefit_forecasts | Household/project/month/version, projected credits/expenses and assumptions | unique project/household/month/model |
| reconciliations | Settlement/forecast, period, expected/recorded difference, reliability outcome | unique settlement/rules version; project/household/month |
| explanations | Solver result → Gemini model/prompt version, reviewed explanation | solver/date |
| audit_events | Community/actor/entity/action/request trace | community/date; request ID |

## Relationships and authority

Communities own projects and households through references; membership gates access.
A participation connects one household to one project. Contributions are commitments,
not payments; `financial_events` is the evidence-backed ledger. Financing obligations
record liability separately from investment ownership. Balances in obligations/reserves
are versioned or timestamped projections and must reconcile to events, not be trusted
as independent sums. A null household on a financial event identifies community-level
reserve/expense activity, not a fictional household.

Ownership and official VNM credit allocation are independent, versioned records. A solver
run or accepted contribution cannot automatically change either. VNM schedules may total
less than 10000 basis points when unallocated shares remain; they can never exceed 10000.
Approved/active schedules require nonempty approval references. Only one schedule can
be active per project, and one ownership record active per household/project.

For SmartExit, fully paid-up cases require zero outstanding contribution and zero assumed
funding gap. Outstanding cases require a positive outstanding amount, but the genuine
community gap can still be zero. Draft/unassessed values may be null. Evaluated and later
cases require a known gap and assessed obligations. Alternatives separately model transfer
to new/existing/multiple participants, eligible retention/buyout, replacement, voluntary
redistribution and eligible reserve funding. Optional solver references do not force a
paid-up transfer to fabricate a solver result. Negative financial impacts are permitted.

Execution records are distinct from proposals. An explicit service transaction must validate
consent to the exact agreement hash/version, eligibility, current participation versions,
each required approval, ownership conservation, affordability and ledger conservation.
No API exists yet for execution; this schema does not implement the workflow itself.
An execution record cannot itself grant regulatory permission or activate VNM allocations.

## Database validation versus service validation

MongoDB enforces field types/shape, required and nullable fields, allowed enums, UUIDs,
integer bounds, month/hash formats, size/MIME limits, local SmartExit obligation/gap rules,
paid-obligation balance and VNM credit sum/approval presence. Unique/partial indexes prevent
duplicate identities, active ownership/schedules/open exits and replayed financial/execution
IDs. There are no foreign keys, database RBAC policies or automatic ownership transfers.

Future backend DTOs/services must validate reference existence and community consistency,
array element uniqueness, valid dates, consent/approval authenticity, period alignment,
ledger balances, tariff/financing calculations, legal eligibility, and all state transitions.
Appending an audit event or declaring an approval ID is not sufficient authorisation.
Use tenant/owner query filters and multi-document transactions with optimistic version checks
for execution. No generic CRUD endpoint should expose these collections.

Financial dashboards derive net benefit and cumulative returns from verified credits and
expenses, compared with the forecast version actually accepted. Avoid duplicating these
aggregates in mutable dashboard documents. Payback requires reliable investment/outflow
history; reconciliation reports insufficient_data when source amounts are null/unreliable.
Electricity OCR and Gemini remain optional integrations with no paid calls in setup.

## Non-destructive initialisation

The initializer is restricted to development `solaris`, preflights every existing managed
collection and index, creates only missing collections/indexes, and verifies exact validator,
strict/error policy and index keys/options after creation. Identical existing schemas are
left untouched. Conflicting definitions cause a failure before creation; explicit migrations
are required rather than `collMod`, dropping, renaming or rebuilding indexes automatically.
Extra collections/indexes are preserved. The script never changes user permissions or writes
application documents. DDL is not atomic: an interruption can leave a safe partial setup;
rerun to finish. Run one initializer at a time. Existing document values are never repaired.
New unique indexes can fail if existing data violates uniqueness; the data remains intact.
