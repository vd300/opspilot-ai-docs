from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from langgraph.types import interrupt

from app.graph.state import InvestigationState

APPROVAL_TTL_MINUTES = 30
APPROVAL_ACTION = "simulated_checkout_service_rollback"
PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
EXPIRED = "expired"


class ApprovalStateError(ValueError):
    pass


def create_pending_approval(state: InvestigationState) -> InvestigationState:
    if not state.get("requires_approval"):
        return {}

    approval_id = state.get("approval_id") or str(uuid4())
    expires_at = state.get("approval_expires_at") or (
        datetime.now(timezone.utc) + timedelta(minutes=APPROVAL_TTL_MINUTES)
    ).isoformat()
    final_response = dict(state.get("final_response") or {})
    final_response.update(
        {
            "status": "approval_required",
            "requires_approval": True,
            "approval_id": approval_id,
            "approval_status": PENDING,
            "approval_requested_action": APPROVAL_ACTION,
            "approval_expires_at": expires_at,
        }
    )
    return {
        "approval_id": approval_id,
        "approval_status": PENDING,
        "approval_requested_action": APPROVAL_ACTION,
        "approval_expires_at": expires_at,
        "final_response": final_response,
    }


def approval_interrupt_payload(state: InvestigationState) -> dict[str, Any]:
    return {
        "investigation_id": state.get("investigation_id"),
        "approval_id": state.get("approval_id"),
        "requested_action": state.get("approval_requested_action"),
        "expires_at": state.get("approval_expires_at"),
        "message": "Human approval is required before simulating rollback.",
    }


def wait_for_human_approval(state: InvestigationState) -> InvestigationState:
    if state.get("approval_status") != PENDING:
        return {}
    decision = interrupt(approval_interrupt_payload(state))
    return apply_approval_decision(state, decision)


def apply_approval_decision(
    state: InvestigationState,
    decision: dict[str, Any],
    *,
    now: datetime | None = None,
) -> InvestigationState:
    normalized = _normalize_decision(decision)
    decided_at = (now or datetime.now(timezone.utc)).isoformat()
    if is_approval_expired(state, now=now):
        return _decision_state(
            state,
            approval_status=EXPIRED,
            approval_decision=normalized["decision"],
            decided_by=normalized["decided_by"],
            decided_at=decided_at,
            result={
                "action": state.get("approval_requested_action"),
                "executed": False,
                "mode": "simulated",
                "reason": "Approval request expired before a valid decision was applied.",
            },
        )

    if normalized["decision"] == "approve":
        return _decision_state(
            state,
            approval_status=APPROVED,
            approval_decision="approve",
            decided_by=normalized["decided_by"],
            decided_at=decided_at,
            result=simulate_rollback(state, normalized),
        )

    return _decision_state(
        state,
        approval_status=REJECTED,
        approval_decision="reject",
        decided_by=normalized["decided_by"],
        decided_at=decided_at,
        result={
            "action": state.get("approval_requested_action"),
            "executed": False,
            "mode": "simulated",
            "reason": normalized.get("comment") or "Human rejected the rollback request.",
        },
    )


def finalize_approval_response(state: InvestigationState) -> InvestigationState:
    if state.get("approval_status") not in {APPROVED, REJECTED, EXPIRED}:
        return {}

    final_response = dict(state.get("final_response") or {})
    status = {
        APPROVED: "rollback_simulated",
        REJECTED: "approval_rejected",
        EXPIRED: "approval_expired",
    }[state["approval_status"]]
    final_response.update(
        {
            "status": status,
            "requires_approval": False,
            "approval_status": state.get("approval_status"),
            "approval_decision": state.get("approval_decision"),
            "approval_decided_by": state.get("approval_decided_by"),
            "approval_decided_at": state.get("approval_decided_at"),
            "approval_result": state.get("approval_result"),
        }
    )
    if state.get("approval_status") == APPROVED:
        final_response["message"] = (
            f"{final_response.get('message')} Approval was granted and rollback was simulated only."
        )
    elif state.get("approval_status") == REJECTED:
        final_response["message"] = (
            f"{final_response.get('message')} Approval was rejected; no rollback was simulated."
        )
    else:
        final_response["message"] = (
            f"{final_response.get('message')} Approval expired; no rollback was simulated."
        )
    return {
        "active_agent": "incident_coordinator",
        "requires_approval": False,
        "final_response": final_response,
    }


def is_approval_expired(
    state: InvestigationState | dict[str, Any],
    *,
    now: datetime | None = None,
) -> bool:
    expires_at = state.get("approval_expires_at")
    if not expires_at:
        return False
    expiry = datetime.fromisoformat(str(expires_at))
    current = now or datetime.now(timezone.utc)
    return current >= expiry


def simulate_rollback(
    state: InvestigationState | dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    return {
        "action": state.get("approval_requested_action") or APPROVAL_ACTION,
        "executed": True,
        "mode": "simulated",
        "service_name": state.get("service_name"),
        "environment": state.get("environment"),
        "approved_by": decision["decided_by"],
        "summary": "Simulated rollback for checkout-service; no production system was changed.",
    }


def _normalize_decision(decision: dict[str, Any]) -> dict[str, Any]:
    raw_decision = str(decision.get("decision") or "").strip().lower()
    if raw_decision not in {"approve", "reject"}:
        raise ApprovalStateError("Approval decision must be approve or reject.")
    decided_by = str(decision.get("decided_by") or "").strip()
    if not decided_by:
        raise ApprovalStateError("Approval decision requires decided_by.")
    comment = decision.get("comment")
    return {
        "decision": raw_decision,
        "decided_by": decided_by,
        "comment": str(comment).strip() if comment else None,
    }


def _decision_state(
    state: InvestigationState,
    *,
    approval_status: str,
    approval_decision: str,
    decided_by: str,
    decided_at: str,
    result: dict[str, Any],
) -> InvestigationState:
    return {
        "approval_status": approval_status,
        "approval_decision": approval_decision,
        "approval_decided_by": decided_by,
        "approval_decided_at": decided_at,
        "approval_result": result,
    }
