"""MongoDB v1 schemas: integer paise/Wh/Wp/basis points, UUID references, UTC dates.

JSON Schema enforces shape. Service transactions enforce references, consent,
state transitions, ownership conservation and financial reconciliation.
"""
from pymongo import ASCENDING, IndexModel

S = {"bsonType": "string", "minLength": 1, "maxLength": 4096}
ID = {"bsonType": "string", "pattern": r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"}
I = {"bsonType": ["int", "long"], "minimum": 0, "maximum": 9007199254740991}
SIGNED = {"bsonType": ["int", "long"], "minimum": -9007199254740991, "maximum": 9007199254740991}
POS = {**I, "minimum": 1}
SHARE = {**I, "maximum": 10000}
D = {"bsonType": "date"}
B = {"bsonType": "bool"}
MONTH = {"bsonType": "string", "pattern": r"^\d{4}-(0[1-9]|1[0-2])$"}
HASH = {"bsonType": "string", "pattern": "^[a-f0-9]{64}$"}
TEXT = {"bsonType": "string", "minLength": 1, "maxLength": 20000}


def enum(*values):
    return {"enum": list(values)}


def nullable(value):
    return {"anyOf": [value, {"bsonType": "null"}]}


def array(item, minimum=0):
    return {"bsonType": "array", "items": item, "minItems": minimum, "maxItems": 1000}


def obj(fields, optional=None):
    return {"bsonType": "object", "required": list(fields), "properties": {**fields, **(optional or {})}, "additionalProperties": False}


def schema(fields, optional=None):
    return obj({"_id": ID, "schema_version": {"enum": [1]}, "created_at": D, **fields}, optional)


INPUT = obj({"name": S, "value": S, "unit": S, "source": S})
ALLOCATION = obj({"household_id": ID, "contribution_paise": I, "monthly_financing_paise": I, "ownership_bps": SHARE, "estimated_credit_bps": SHARE})

SCHEMAS = {
    "users": schema({"auth_subject": S, "role": enum("resident", "community_admin", "solar_provider", "platform_admin"), "status": enum("active", "disabled")}),
    "communities": schema({"name": S, "location": S, "discom": S}, {"registration_reference": S}),
    "memberships": schema({"community_id": ID, "user_id": ID, "role": enum("resident", "community_admin", "solar_provider"), "status": enum("pending", "active", "withdrawn")}),
    "households": schema({"community_id": ID, "user_id": ID, "connection_reference": S, "monthly_consumption_wh": nullable(I), "max_upfront_paise": nullable(I), "max_monthly_paise": nullable(I), "consent_recorded": B}),
    "electricity_bills": schema({"household_id": ID, "document_id": ID, "period": MONTH, "consumption_wh": nullable(I), "bill_amount_paise": nullable(I), "source": enum("manual", "ocr"), "verification_status": enum("pending", "verified", "rejected")}, {"verified_by": ID, "verified_at": D}),
    "projects": schema({"community_id": ID, "name": S, "status": enum("planning", "approved", "installation", "operational", "closed"), "capacity_wp": nullable(I), "estimated_cost_paise": nullable(I)}, {"provider_user_id": ID, "commissioned_at": D}),
    "assessments": schema({"project_id": ID, "kind": enum("readiness", "feasibility"), "input_snapshot": array(INPUT), "output_snapshot": array(INPUT), "assumptions": array(S), "result": enum("preliminary", "insufficient_data", "review_required"), "rules_version": S}),
    "documents": schema({"community_id": ID, "owner_user_id": ID, "kind": enum("electricity_bill", "agreement", "payment_evidence", "approval_evidence", "provider_evidence", "settlement_evidence"), "storage_key": S, "content_type": enum("application/pdf", "image/jpeg", "image/png"), "size_bytes": {**POS, "maximum": 10485760}, "sha256": HASH, "status": enum("quarantined", "verified", "rejected")}),
    "agreements": schema({"project_id": ID, "version": POS, "document_id": ID, "participant_ids": array(ID, 1), "status": enum("draft", "awaiting_consent", "approved", "superseded")}, {"exit_case_id": ID, "supersedes_id": ID}),
    "consents": schema({"agreement_id": ID, "user_id": ID, "document_sha256": HASH, "decision": enum("accepted", "declined", "withdrawn"), "decided_at": D}),
    "participations": schema({"project_id": ID, "household_id": ID, "agreement_id": ID, "version": POS, "status": enum("pending", "active", "exit_pending", "exited")}),
    "contributions": schema({"project_id": ID, "household_id": ID, "participation_id": ID, "agreement_id": ID, "committed_paise": I, "version": POS, "status": enum("proposed", "accepted", "superseded")}),
    "financing_obligations": schema({"project_id": ID, "household_id": ID, "agreement_id": ID, "principal_paise": I, "outstanding_paise": I, "monthly_due_paise": I, "liable_party": enum("household", "community"), "terms_reference": S, "as_of": D, "status": enum("active", "paid", "disputed", "transferred")}),
    "ownership_records": schema({"project_id": ID, "household_id": ID, "agreement_id": ID, "version": POS, "ownership_bps": SHARE, "status": enum("proposed", "active", "superseded")}, {"effective_at": D, "exit_transaction_id": ID}),
    "vnm_allocations": schema({"project_id": ID, "version": POS, "status": enum("proposed", "awaiting_approval", "approved", "active", "superseded"), "allocations": array(obj({"household_id": ID, "credit_bps": SHARE}), 1), "approval_ids": array(ID), "source_reference": S}, {"effective_at": D, "supersedes_id": ID}),
    "optimisation_runs": schema({"project_id": ID, "requested_by": ID, "strategy": enum("equal", "affordability", "benefit", "what_if", "smart_exit"), "input_snapshot": array(INPUT), "model_version": S, "solver_status": enum("pending", "optimal", "feasible", "infeasible", "unknown", "failed"), "allocations": array(ALLOCATION), "objective_value": nullable(SIGNED), "assumptions": array(S)}, {"baseline_run_id": ID, "exit_case_id": ID}),
    "exit_cases": schema({"project_id": ID, "household_id": ID, "participation_id": ID, "participation_version": POS, "obligation_state": enum("unassessed", "fully_paid", "outstanding"), "outstanding_paise": nullable(I), "funding_gap_paise": nullable(I), "funding_evidence": array(INPUT), "status": enum("draft", "evaluated", "awaiting_consent", "awaiting_approval", "approved", "executed", "cancelled"), "alternatives": array(obj({"alternative_id": ID, "strategy": enum("transfer_new", "transfer_existing", "transfer_multiple", "retention", "community_buyout", "replacement", "voluntary_redistribution", "reserve"), "solver_run_id": nullable(ID), "eligible": B, "eligibility_evidence": array(INPUT), "financial_impacts": array(obj({"household_id": ID, "net_paise": SIGNED})), "proposed_allocations": array(ALLOCATION), "required_approvals": array(S)})), "agreement_ids": array(ID), "approval_ids": array(ID)}, {"selected_alternative_id": ID}),
    "approvals": schema({"project_id": ID, "target_type": enum("exit_case", "vnm_allocation", "agreement", "project"), "target_id": ID, "actor_user_id": ID, "kind": enum("participant_consent", "community", "provider", "external"), "decision": enum("pending", "approved", "rejected"), "evidence_document_id": nullable(ID), "decided_at": nullable(D)}),
    "exit_transactions": schema({"project_id": ID, "exit_case_id": ID, "alternative_id": ID, "idempotency_key": S, "executed_by": ID, "executed_at": D, "agreement_ids": array(ID, 1), "approval_ids": array(ID, 1), "financial_event_ids": array(ID), "ownership_changes": array(obj({"household_id": ID, "before_bps": SHARE, "after_bps": SHARE}), 1), "participation_version": POS}, {"approved_vnm_allocation_id": ID}),
    "provider_updates": schema({"project_id": ID, "provider_user_id": ID, "stage": enum("survey", "procurement", "installation", "commissioning", "maintenance"), "description": TEXT, "document_ids": array(ID), "occurred_at": D}),
    "quotations": schema({"project_id": ID, "provider_user_id": ID, "version": POS, "capacity_wp": POS, "installation_cost_paise": I, "estimated_annual_generation_wh": nullable(I), "assumptions": array(S), "valid_until": D, "status": enum("submitted", "accepted", "rejected", "expired")}),
    "generation_records": schema({"project_id": ID, "provider_user_id": ID, "period": MONTH, "generation_wh": I, "source_reference": S, "verified": B}),
    "settlements": schema({"project_id": ID, "household_id": ID, "period": MONTH, "source_reference": S, "reliable": B, "expected_credit_paise": nullable(I), "recorded_credit_paise": nullable(I), "expenses_paise": nullable(I), "status": enum("unverified", "verified", "disputed")}, {"document_id": ID, "vnm_allocation_id": ID}),
    "financial_events": schema({"project_id": ID, "household_id": nullable(ID), "idempotency_key": S, "kind": enum("contribution", "financing_payment", "expense", "refund", "credit", "reserve_deposit", "reserve_use", "share_sale", "share_purchase"), "amount_paise": I, "occurred_at": D, "source_reference": S, "evidence_document_id": nullable(ID)}, {"obligation_id": ID, "exit_transaction_id": ID, "reverses_event_id": ID}),
    "reserve_funds": schema({"project_id": ID, "available_paise": I, "as_of": D, "eligibility_rules_reference": S, "agreement_id": ID, "version": POS}),
    "benefit_forecasts": schema({"project_id": ID, "household_id": ID, "period": MONTH, "model_version": S, "expected_credit_paise": nullable(I), "expected_expense_paise": nullable(I), "assumptions": array(S)}, {"optimisation_run_id": ID}),
    "reconciliations": schema({"project_id": ID, "household_id": ID, "period": MONTH, "settlement_id": ID, "forecast_id": nullable(ID), "expected_credit_paise": nullable(I), "recorded_credit_paise": nullable(I), "difference_paise": nullable(SIGNED), "status": enum("insufficient_data", "matched", "mismatch", "reviewed"), "rules_version": S, "source_references": array(S)}),
    "explanations": schema({"solver_run_id": ID, "model": S, "prompt_version": S, "text": TEXT, "status": enum("draft", "reviewed")}),
    "audit_events": schema({"community_id": ID, "actor_user_id": ID, "action": S, "entity_id": ID, "request_id": S}),
}

# Enforce local SmartExit invariants even for writes outside the API.
EXIT_VALIDATOR = {"$and": [
    {"$jsonSchema": SCHEMAS["exit_cases"]},
    {"$or": [{"obligation_state": {"$ne": "fully_paid"}}, {"outstanding_paise": 0, "funding_gap_paise": 0}]},
    {"$or": [{"obligation_state": {"$ne": "outstanding"}}, {"outstanding_paise": {"$gt": 0}}]},
    {"$or": [{"status": "draft"}, {"obligation_state": {"$ne": "unassessed"}, "funding_gap_paise": {"$type": ["int", "long"]}}]},
]}
VALIDATORS = {name: {"$jsonSchema": value} for name, value in SCHEMAS.items()}
VALIDATORS["exit_cases"] = EXIT_VALIDATOR
VALIDATORS["financing_obligations"] = {"$and": [{"$jsonSchema": SCHEMAS["financing_obligations"]}, {"$or": [{"status": {"$ne": "paid"}}, {"outstanding_paise": 0}]}]}
VALIDATORS["vnm_allocations"] = {"$and": [
    {"$jsonSchema": SCHEMAS["vnm_allocations"]},
    {"$expr": {"$lte": [{"$sum": "$allocations.credit_bps"}, 10000]}},
    {"$or": [{"status": {"$nin": ["approved", "active"]}}, {"approval_ids.0": {"$exists": True}}]},
]}


def index(*fields, unique=False, partial=None):
    options = {"unique": unique}
    if partial is not None:
        options["partialFilterExpression"] = partial
    return IndexModel([(field, ASCENDING) for field in fields], **options)


INDEXES = {
    "users": [index("auth_subject", unique=True)],
    "communities": [index("discom", "location")],
    "memberships": [index("community_id", "user_id", unique=True), index("user_id", "status")],
    "households": [index("community_id", "connection_reference", unique=True), index("user_id", "community_id")],
    "electricity_bills": [index("household_id", "period"), index("document_id", unique=True)],
    "projects": [index("community_id", "status"), index("provider_user_id", "status")],
    "assessments": [index("project_id", "kind", "created_at")],
    "documents": [index("storage_key", unique=True), index("community_id", "owner_user_id", "kind")],
    "agreements": [index("project_id", "version", unique=True)],
    "consents": [index("agreement_id", "user_id", "decided_at")],
    "participations": [index("project_id", "household_id", unique=True)],
    "contributions": [index("project_id", "household_id", "version", unique=True)],
    "financing_obligations": [index("project_id", "household_id", "status")],
    "ownership_records": [index("project_id", "household_id", "version", unique=True), index("project_id", "household_id", "status", unique=True, partial={"status": "active"})],
    "vnm_allocations": [index("project_id", "version", unique=True), index("project_id", "status", unique=True, partial={"status": "active"})],
    "optimisation_runs": [index("project_id", "strategy", "created_at")],
    "exit_cases": [index("project_id", "household_id", "status"), index("participation_id", unique=True, partial={"status": {"$in": ["draft", "evaluated", "awaiting_consent", "awaiting_approval", "approved"]}})],
    "approvals": [index("target_type", "target_id", "actor_user_id", "kind", unique=True)],
    "exit_transactions": [index("idempotency_key", unique=True), index("exit_case_id", unique=True)],
    "provider_updates": [index("project_id", "stage", "occurred_at")],
    "quotations": [index("project_id", "provider_user_id", "version", unique=True)],
    "generation_records": [index("project_id", "period", "source_reference", unique=True)],
    "settlements": [index("project_id", "household_id", "period", unique=True)],
    "financial_events": [index("idempotency_key", unique=True), index("project_id", "household_id", "occurred_at")],
    "reserve_funds": [index("project_id", unique=True)],
    "benefit_forecasts": [index("project_id", "household_id", "period", "model_version", unique=True)],
    "reconciliations": [index("settlement_id", "rules_version", unique=True), index("project_id", "household_id", "period")],
    "explanations": [index("solver_run_id", "created_at")],
    "audit_events": [index("community_id", "created_at"), index("request_id")],
}
