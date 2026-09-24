from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from src.domain.exceptions import AuthorityLimitExceeded
from src.infrastructure.db.models import (
    Application,
    ApprovalRecord,
    AuditLog,
    CreditMemoRecord,
    User,
)


class ApprovalEngine:
    def __init__(self, session: Session):
        self.session = session

    def _log_event(
        self,
        application: Application,
        actor: User | None,
        *,
        action: str,
        step_name: str | None,
        previous_status: str | None,
        new_status: str | None,
        details: dict[str, Any] | None = None,
    ) -> None:
        log_entry = AuditLog(
            application_id=application.id,
            actor_id=actor.id if actor else None,
            action=action,
            step_name=step_name,
            previous_status=previous_status,
            new_status=new_status,
            details=details or {},
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(log_entry)

    def _ensure_pending(self, application: Application) -> None:
        if application.status != "pending":
            raise ValueError(f"Application {application.id} is not pending and cannot be changed.")

    def _ensure_approver(self, actor: User | None) -> None:
        if actor is None:
            raise PermissionError("Unknown approver.")
        if actor.role not in {"credit_officer", "admin"}:
            raise PermissionError("Only Credit Officers or Admins can approve or reject applications.")

    def record_decision(
        self,
        application_id: str,
        actor_id: str,
        *,
        decision: str,
        justification: str,
        amount: float | None = None,
    ) -> ApprovalRecord:
        decision = decision.lower()
        if decision not in {"approved", "rejected"}:
            raise ValueError("Decision must be 'approved' or 'rejected'.")

        application = self.session.get(Application, application_id)
        if application is None:
            raise ValueError(f"Application {application_id} does not exist.")
        actor = self.session.get(User, actor_id)
        self._ensure_pending(application)
        self._ensure_approver(actor)

        start_amount = float(amount if amount is not None else application.requested_amount)
        if decision == "approved" and start_amount > float(actor.authority_limit or 0.0) and actor.role != "admin":
            raise AuthorityLimitExceeded(
                f"Requested amount {start_amount} exceeds the assigned authority limit of {float(actor.authority_limit or 0.0)}."
            )

        previous_status = application.status
        application.status = decision
        application.decision_reason = justification
        application.decision_timestamp = datetime.now(timezone.utc)

        approval_record = ApprovalRecord(
            application_id=application.id,
            approver_id=actor.id,
            decision=decision,
            comment=justification,
            amount=start_amount,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(approval_record)

        memo = (
            self.session.query(CreditMemoRecord)
            .filter_by(application_id=application.id)
            .order_by(CreditMemoRecord.created_at.desc())
            .first()
        )
        if memo is not None:
            memo.status = decision
            memo.decision_reason = justification
            memo.updated_at = datetime.now(timezone.utc)

        self._log_event(
            application,
            actor,
            action=f"approval:{decision}",
            step_name="decision",
            previous_status=previous_status,
            new_status=decision,
            details={
                "justification": justification,
                "requested_amount": start_amount,
                "actor_role": actor.role,
            },
        )

        self.session.commit()
        return approval_record

    def approve(self, application_id: str, actor_id: str, *, justification: str, amount: float | None = None) -> ApprovalRecord:
        return self.record_decision(
            application_id,
            actor_id,
            decision="approved",
            justification=justification,
            amount=amount,
        )

    def reject(self, application_id: str, actor_id: str, *, justification: str, amount: float | None = None) -> ApprovalRecord:
        return self.record_decision(
            application_id,
            actor_id,
            decision="rejected",
            justification=justification,
            amount=amount,
        )

    def issue(self, application_id: str, actor_id: str, *, justification: str, amount: float | None = None) -> ApprovalRecord:
        application = self.session.get(Application, application_id)
        if application is None:
            raise ValueError(f"Application {application_id} does not exist.")
        if application.status != "approved":
            raise ValueError("Only approved applications can be issued.")

        actor = self.session.get(User, actor_id)
        self._ensure_approver(actor)

        application.status = "issued"
        application.decision_reason = justification
        application.decision_timestamp = datetime.now(timezone.utc)

        approval_record = ApprovalRecord(
            application_id=application.id,
            approver_id=actor.id,
            decision="issued",
            comment=justification,
            amount=float(amount if amount is not None else application.requested_amount),
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(approval_record)

        memo = (
            self.session.query(CreditMemoRecord)
            .filter_by(application_id=application.id)
            .order_by(CreditMemoRecord.created_at.desc())
            .first()
        )
        if memo is not None:
            memo.status = "approved"
            memo.decision_reason = justification
            memo.updated_at = datetime.now(timezone.utc)

        self._log_event(
            application,
            actor,
            action="issue",
            step_name="decision",
            previous_status="approved",
            new_status="issued",
            details={"justification": justification},
        )
        self.session.commit()
        return approval_record

    def log_fairness_stripping(self, application_id: str, actor_id: str | None, stripped_fields: list[str]) -> AuditLog:
        application = self.session.get(Application, application_id)
        if application is None:
            raise ValueError(f"Application {application_id} does not exist.")

        application.fairness_stripped_fields = stripped_fields
        log_entry = AuditLog(
            application_id=application.id,
            actor_id=actor_id,
            action="fairness_strip",
            step_name="step_2",
            previous_status=application.status,
            new_status=application.status,
            details={"stripped_fields": stripped_fields},
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(log_entry)
        self.session.commit()
        return log_entry


__all__ = ["ApprovalEngine"]
