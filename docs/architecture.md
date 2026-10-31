# Architecture and implementation priorities

## Runtime boundaries

Browser (React/Vite/TypeScript/Tailwind) → HTTPS FastAPI → MongoDB Atlas.
Clerk issues short-lived identity tokens; FastAPI verifies them and loads stored roles.
Private S3 holds bills and agreements; FastAPI authorises scoped signed URLs.
OR-Tools CP-SAT runs server-side with integer paise/Wh/basis points and bounded solve time.
Gemini receives only a redacted solver-result snapshot and explains computed values.
It never determines ownership, recalculates financial results, or approves a transfer.
No SQL database, SQL migrations or client-side database access is involved.

## MVP implementation order

1. **Foundation (this change):** local frontend/API, config, health/readiness, token and role
   enforcement, collection validators/indexes, explicit Atlas bootstrap, local solver smoke check.
2. **First end-to-end slice:** Clerk sign-in and separate resident/admin/provider dashboards;
   community registration and membership; household inputs and optional document metadata.
   Validate consumption, affordability and consent; enforce tenant and owner filtering everywhere.
3. **Readiness and feasibility:** preliminary location/DISCOM checks based on sourced,
   versioned rules. Show unknowns and missing information. Estimate capacity, generation,
   costs and payback from user/provider inputs with units, assumptions and provenance.
   No invented approvals, guaranteed savings, or hardcoded financial estimates.
4. **Investment planning:** implement equal, affordability-aware and benefit-aware arrangements
   with explicit objectives and constraints; compare the same input snapshot. Add What-If
   copies without mutating accepted plans. Show infeasible/unknown solver outcomes honestly.
5. **Participation and SmartExit:** consent, immutable agreement versions, financial events,
   accepted contributions, ownership and approved VNM allocations. Implement exit alternatives
   and approval-gated execution. Solver output is always a proposal.
6. **Operational proof:** provider quotations/progress/generation, financial benefit dashboards,
   projected versus actual performance. Reconcile DISCOM credits only where reliable inputs
   and compatible periods exist; otherwise report insufficient data.

Defer bill OCR, automated external integrations, complex finance products and Gemini until
the manual-input path works. Start with one community/project and monthly settlement periods,
but preserve tenant isolation. A working domain demo will span steps 2–5; this foundation
alone must not be presented as that demo.

## SmartExit rules

- Snapshot the accepted participation, ledger, agreement version and obligation evidence.
  Classify fully paid-up versus outstanding obligations. Outstanding debt is not automatically
  a community funding gap: determine due amounts, liable party, timing, committed incoming
  funds and eligible reserve separately using disclosed inputs.
- Fully paid-up: evaluate ownership transfer/sale to a willing new resident, existing resident,
  or several participants. Retention or community buyout requires documented eligibility.
  Do not assume a shortfall, forced discount or mandatory redistribution.
- Outstanding obligations: first establish whether a genuine community funding gap exists.
  Compare replacement, voluntary redistribution and eligible reserves as applicable. CP-SAT
  enforces each consenting household's upfront/monthly caps, reserve limits and conservation
  of required funding and ownership. Financing liability and ownership must be separate variables.
- Present alternatives with calculated financial impacts, ownership implications, eligibility
  evidence, assumptions, solver status and required approvals. Never treat missing data as zero.
- Gemini may explain the recorded results only; no financial calculation originates from it.
- Acceptance creates an awaiting-consent proposal. No automatic ownership or official credit
  allocation changes. Execution must check signed agreements, consent from every affected
  party and applicable approvals against current versions. External approval evidence records
  a real decision; it does not claim regulatory permission or replace official DISCOM processes.
- Use a transaction for accepted ledger/participation/agreement/audit changes with optimistic
  version checks and an idempotency key. Execute only an explicit authorised action after all
  preconditions. Keep official VNM allocation unchanged until the required external approval
  evidence exists. Execution endpoints are intentionally absent from this foundation.

## Backend access policy

Residents access their own household/financial documents and community-visible plans.
Community administrators manage only their community and consent/approval workflows.
Assigned solar providers access quotations, installation, generation and settlement tasks;
they cannot read unrelated household finances or change ownership unilaterally.
Platform administrators perform operational provisioning; membership is still required for
the supplied community route. Authorise every future operation using membership scope,
resource ownership and allowed action, then query by both resource ID and community ID.
The browser cannot grant roles. Never expose a generic database or arbitrary-filter API.

## Storage and privacy

Use a private S3 bucket; generate random tenant-scoped keys and short-lived signed URLs
only after backend authorisation. Enforce upload size/type/checksum, quarantine and malware
checks, then record verified metadata. Verify actual object metadata before marking complete.
Download authorisation is separate from upload authorisation. Define retention/deletion with
the community; audit access without logging raw bills, tokens or connection strings.
No external account, bucket or paid service has been provisioned.

## Sources

- [PyMongo Async connection](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/connect/mongoclient/)
- [MongoDB indexes](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/indexes/)
- [Clerk manual JWT verification](https://clerk.com/docs/guides/sessions/manual-jwt-verification)
- [OR-Tools CP-SAT](https://developers.google.com/optimization/cp/cp_solver/)
- [S3 signed URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html)
- [Gemini Python SDK](https://googleapis.github.io/python-genai/)
