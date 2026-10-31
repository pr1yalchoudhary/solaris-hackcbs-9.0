# Development database initialisation · 31 October 2026

Target: `solaris`, using the existing ignored backend environment file.
Preflight found no existing collections or documents.

The initializer created **29 collections**, with strict/error validators and **70 total
indexes** (29 built-in `_id` indexes plus 41 application indexes). Every validator and
required index key/unique/partial option was compared with the executable definitions.
All collections contained **zero documents** after setup.

Created collections:

```text
users
communities
memberships
households
electricity_bills
projects
assessments
documents
agreements
consents
participations
contributions
financing_obligations
ownership_records
vnm_allocations
optimisation_runs
exit_cases
approvals
exit_transactions
provider_updates
quotations
generation_records
settlements
financial_events
reserve_funds
benefit_forecasts
reconciliations
explanations
audit_events
```

A second initialization created no collections. Metadata and indexes before/after
the repeat run were identical, and document count remained zero.

Backend tests: **7 passed** (the original 3 plus 4 database setup/safety tests).
The existing Starlette/httpx TestClient deprecation warning remains non-blocking.
Tests include non-destructive repeat initialization, validator-conflict refusal,
unique-index conflict refusal, schema/index coverage, authentication and local solver checks.

Issue encountered: the first attempt stopped before making database changes because
PyMongo Async metadata cursor methods needed awaiting. This was corrected along with
the test doubles, then the tests and real initialization succeeded. No permission
changes were needed. No records were inserted, deleted, overwritten or seeded.
No commits, pushes, deployments or paid API requests were made.

This validates DDL and metadata, not end-to-end financial workflows. Cross-document
references, approvals, affordability and ownership conservation still need transactional
backend services. The initializer does not implement SmartExit execution endpoints.
