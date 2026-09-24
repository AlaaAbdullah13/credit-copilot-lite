from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from src.infrastructure.db.sql import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False)
    role = Column(String, nullable=False, default="loan_officer")
    authority_limit = Column(Float, nullable=False, default=250000.0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    applications = relationship("Application", back_populates="owner")
    approvals = relationship("ApprovalRecord", back_populates="approver")


class Application(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String, ForeignKey("users.id"), nullable=True)
    requested_amount = Column(Float, nullable=False)
    annual_rate = Column(Float, nullable=False, default=12.5)
    tenure_months = Column(Integer, nullable=False)
    monthly_income = Column(Float, nullable=False)
    other_monthly_installments = Column(Float, nullable=False, default=0.0)
    date_of_birth = Column(Date, nullable=False)
    application_date = Column(Date, nullable=False)
    policy_edition = Column(String, nullable=False, default="2025")
    policy_snapshot = Column(JSON, nullable=True)
    status = Column(String, nullable=False, default="pending")
    decision_reason = Column(Text, nullable=True)
    decision_timestamp = Column(DateTime, nullable=True)
    fairness_stripped_fields = Column(JSON, nullable=True, default=list)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    owner = relationship("User", back_populates="applications")
    assessment_runs = relationship("AssessmentRun", back_populates="application")
    rules_outputs = relationship("RulesOutput", back_populates="application")
    memos = relationship("CreditMemoRecord", back_populates="application")
    approvals = relationship("ApprovalRecord", back_populates="application")
    audit_logs = relationship("AuditLog", back_populates="application")


class AssessmentRun(Base):
    __tablename__ = "assessment_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    request_id = Column(String, nullable=True)
    policy_edition = Column(String, nullable=False)
    steps_executed = Column(JSON, nullable=False, default=list)
    chunk_ids = Column(JSON, nullable=False, default=list)
    tokens_consumed = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False, default="completed")
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    application = relationship("Application", back_populates="assessment_runs")


class RulesOutput(Base):
    __tablename__ = "rules_outputs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    rule_name = Column(String, nullable=False)
    result = Column(String, nullable=False)
    details = Column(JSON, nullable=True, default=dict)
    citation = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    application = relationship("Application", back_populates="rules_outputs")


class CreditMemoRecord(Base):
    __tablename__ = "credit_memos"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    assessment_run_id = Column(String, ForeignKey("assessment_runs.id"), nullable=True)
    status = Column(String, nullable=False, default="pending")
    memo_text = Column(Text, nullable=True)
    decision_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    application = relationship("Application", back_populates="memos")


class ApprovalRecord(Base):
    __tablename__ = "approval_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    approver_id = Column(String, ForeignKey("users.id"), nullable=False)
    decision = Column(String, nullable=False)
    comment = Column(Text, nullable=True)
    amount = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    application = relationship("Application", back_populates="approvals")
    approver = relationship("User", back_populates="approvals")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String, ForeignKey("applications.id"), nullable=True)
    actor_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    step_name = Column(String, nullable=True)
    previous_status = Column(String, nullable=True)
    new_status = Column(String, nullable=True)
    details = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    application = relationship("Application", back_populates="audit_logs")


__all__ = [
    "Application",
    "ApprovalRecord",
    "AssessmentRun",
    "AuditLog",
    "CreditMemoRecord",
    "RulesOutput",
    "User",
]
