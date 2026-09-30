"""Persistent workflow records.  Schema creation is owned exclusively by Alembic."""

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

from src.infrastructure.db.sql import Base


def _id() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=_id)
    username = Column(String, unique=True, nullable=False)
    role = Column(String, nullable=False)
    authority_limit = Column(Float, nullable=False, default=250000.0)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class Application(Base):
    __tablename__ = "applications"
    id = Column(String, primary_key=True, default=_id)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    requested_amount = Column(Float, nullable=False)
    tenure_months = Column(Integer, nullable=False)
    monthly_income = Column(Float, nullable=False)
    other_monthly_installments = Column(Float, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    application_date = Column(Date, nullable=False)
    policy_edition = Column(String, nullable=False)
    recommended_amount = Column(Float)
    recommendation = Column(String)
    status = Column(String, nullable=False, default="pending_approval")
    decision_reason = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class AssessmentRun(Base):
    __tablename__ = "assessment_runs"
    id = Column(String, primary_key=True, default=_id)
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    request_id = Column(String, nullable=False)
    policy_edition = Column(String, nullable=False)
    steps_executed = Column(JSON, nullable=False, default=list)
    chunk_ids = Column(JSON, nullable=False, default=list)
    removed_fields = Column(JSON, nullable=False, default=list)
    tokens_consumed = Column(Integer, nullable=False, default=0)
    token_usage = Column(JSON, nullable=False, default=dict)
    status = Column(String, nullable=False, default="pending_approval")
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class ApprovalRecord(Base):
    __tablename__ = "approval_records"
    id = Column(String, primary_key=True, default=_id)
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    approver_id = Column(String, ForeignKey("users.id"), nullable=False)
    decision = Column(String, nullable=False)
    comment = Column(Text)
    amount = Column(Float)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
