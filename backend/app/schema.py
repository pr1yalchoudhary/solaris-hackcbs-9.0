"""Versioned MongoDB validators. Apply explicitly: python -m app.init_db.

Amounts use integer paise, energy integer Wh, and shares integer basis points.
References are UUID strings. Cross-document constraints belong in backend services.
"""
from pymongo import ASCENDING, IndexModel

S = {"bsonType": "string", "minLength": 1}
# Python small ints encode as BSON int; accept both BSON integer widths.
I = {"bsonType": ["int", "long"], "minimum": 0}
D = {"bsonType": "date"}
B = {"bsonType": "bool"}


def enum(*values):
    return {"enum": list(values)}


def array(item):
    return {"bsonType": "array", "items": item}


def obj(fields):
    return {"bsonType": "object", "required": list(fields), "properties": fields, "additionalProperties": False}


def schema(fields):
    return obj({"_id": S, "schema_version": {"enum": [1]}, "created_at": D, **fields})


SCHEMAS = {
    "users": schema({"auth_subject": S, "role": enum("resident", "community_admin", "solar_provider", "platform_admin"), "status": enum("active", "disabled")}),
    "communities": schema({"name": S, "location": S, "discom": S}),
    "memberships": schema({"community_id": S, "user_id": S, "role": enum("resident", "community_admin", "solar_provider"), "status": enum("pending", "active", "withdrawn")}),
    "households": schema({"community_id": S, "user_id": S, "connection_reference": S, "monthly_consumption_wh": I, "max_upfront_paise": I, "max_monthly_paise": I, "consent_recorded": B}),
    "projects": schema({"community_id": S, "name": S, "status": enum("planning", "approved", "installation", "operational", "closed"), "capacity_wp": I, "estimated_cost_paise": I, "reserve_available_paise": I}),
    "assessments": schema({"project_id": S, "kind": enum("readiness", "feasibility"), "input_snapshot": array(obj({"name": S, "value": S, "unit": S, "source": S})), "assumptions": array(S), "result": enum("preliminary", "insufficient_data", "review_required"), "rules_version": S}),
    "documents": schema({"community_id": S, "owner_user_id": S, "kind": enum("electricity_bill", "agreement"), "storage_key": S, "content_type": enum("application/pdf", "image/jpeg", "image/png"), "size_bytes": {**I, "maximum": 10485760}, "sha256": {"bsonType": "string", "pattern": "^[a-f0-9]{64}$"}, "status": enum("quarantined", "verified", "rejected")}),
    "agreements": schema({"project_id": S, "version": I, "document_id": S, "participant_ids": array(S), "consents": array(obj({"user_id": S, "signed_at": D, "document_sha256": S})), "status": enum("draft", "awaiting_consent", "approved", "superseded")}),
    "participations": schema({"project_id": S, "household_id": S, "agreed_contribution_paise": I, "paid_paise": I, "outstanding_paise": I, "ownership_bps": {**I, "maximum": 10000}, "approved_credit_bps": {**I, "maximum": 10000}, "agreement_id": S, "version": I, "status": enum("active", "exit_pending", "exited")}),
    "optimisation_runs": schema({"project_id": S, "requested_by": S, "strategy": enum("equal", "affordability", "benefit", "what_if", "smart_exit"), "input_snapshot": array(obj({"household_id": S, "max_upfront_paise": I, "max_monthly_paise": I, "expected_benefit_paise": I})), "model_version": S, "solver_status": enum("pending", "optimal", "feasible", "infeasible", "unknown", "failed"), "allocations": array(obj({"household_id": S, "contribution_paise": I, "ownership_bps": {**I, "maximum": 10000}})), "assumptions": array(S)}),
    "exit_cases": schema({"project_id": S, "household_id": S, "participation_version": I, "obligation_state": enum("fully_paid", "outstanding"), "outstanding_paise": I, "funding_gap_paise": I, "status": enum("draft", "evaluated", "awaiting_consent", "awaiting_approval", "approved", "executed", "cancelled"), "alternatives": array(obj({"strategy": enum("transfer_new", "transfer_existing", "transfer_multiple", "retention", "community_buyout", "replacement", "voluntary_redistribution", "reserve"), "solver_run_id": S, "financial_impact_paise": {"bsonType": ["int", "long"]}, "ownership_impact": S, "eligibility_evidence": S, "required_approvals": array(S)})), "agreement_ids": array(S), "approval_ids": array(S)}),
    "approvals": schema({"project_id": S, "exit_case_id": S, "actor_user_id": S, "kind": enum("participant_consent", "community", "provider", "external"), "decision": enum("pending", "approved", "rejected"), "evidence_document_id": S}),
    "provider_updates": schema({"project_id": S, "provider_user_id": S, "kind": enum("quotation", "installation", "generation"), "period": S, "amount_paise": I, "generation_wh": I, "description": S}),
    "settlements": schema({"project_id": S, "household_id": S, "period": S, "source_reference": S, "reliable": B, "expected_credit_paise": I, "recorded_credit_paise": I, "expenses_paise": I, "status": enum("unverified", "verified", "disputed")}),
    "financial_events": schema({"project_id": S, "household_id": S, "idempotency_key": S, "kind": enum("contribution", "financing_payment", "expense", "refund", "reserve_deposit", "reserve_use"), "amount_paise": I, "occurred_at": D, "evidence_document_id": S}),
    "benefit_forecasts": schema({"project_id": S, "household_id": S, "period": S, "model_version": S, "expected_credit_paise": I, "expected_expense_paise": I, "assumptions": array(S)}),
    "explanations": schema({"solver_run_id": S, "model": S, "prompt_version": S, "text": S, "status": enum("draft", "reviewed")}),
    "audit_events": schema({"community_id": S, "actor_user_id": S, "action": S, "entity_id": S, "request_id": S}),
}


def index(*fields, unique=False):
    return IndexModel([(field, ASCENDING) for field in fields], unique=unique)


INDEXES = {
    "users": [index("auth_subject", unique=True)],
    "communities": [index("discom", "location")],
    "memberships": [index("community_id", "user_id", unique=True), index("user_id", "status")],
    "households": [index("community_id", "connection_reference", unique=True), index("user_id", "community_id")],
    "projects": [index("community_id", "status")],
    "assessments": [index("project_id", "kind", "created_at")],
    "documents": [index("storage_key", unique=True), index("community_id", "owner_user_id", "kind")],
    "agreements": [index("project_id", "version", unique=True)],
    "participations": [index("project_id", "household_id", unique=True)],
    "optimisation_runs": [index("project_id", "strategy", "created_at")],
    "exit_cases": [index("project_id", "household_id", "status")],
    "approvals": [index("exit_case_id", "actor_user_id", "kind", unique=True)],
    "provider_updates": [index("project_id", "kind", "period")],
    "settlements": [index("project_id", "household_id", "period", unique=True)],
    "financial_events": [index("idempotency_key", unique=True), index("project_id", "household_id", "occurred_at")],
    "benefit_forecasts": [index("project_id", "household_id", "period", "model_version", unique=True)],
    "explanations": [index("solver_run_id", "created_at")],
    "audit_events": [index("community_id", "created_at"), index("request_id")],
}
