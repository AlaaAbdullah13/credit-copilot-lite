from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import inspect

from src.application.approval import ApprovalEngine
from src.domain.exceptions import AuthorityLimitExceeded
from src.infrastructure.db.migration import run_migration
from src.infrastructure.db.models import Application, AuditLog, User
from src.infrastructure.db.sql import create_session_factory


@pytest.fixture
def db_session(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'phase4.db'}"
    run_migration(db_url)
    session_factory = create_session_factory(db_url)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def test_phase4_migration_creates_all_tables(db_session):
    tables = sorted(inspect(db_session.bind).get_table_names())
    assert {
        "users",
        "applications",
        "assessment_runs",
        "rules_outputs",
        "credit_memos",
        "approval_records",
        "audit_logs",
    }.issubset(tables)


def test_approval_flow_and_audit_event(db_session):
    user = User(username="credit.officer", role="credit_officer", authority_limit=250000.0)
    loan_user = User(username="loan.officer", role="loan_officer", authority_limit=0.0)
    db_session.add_all([user, loan_user])
    db_session.commit()

    app = Application(
        owner_id=user.id,
        requested_amount=180000.0,
        annual_rate=12.5,
        tenure_months=48,
        monthly_income=22000.0,
        other_monthly_installments=0.0,
        date_of_birth=date(1995, 4, 12),
        application_date=date(2025, 3, 3),
        policy_edition="2025",
        status="pending",
    )
    db_session.add(app)
    db_session.commit()

    approval = ApprovalEngine(db_session).approve(
        app.id,
        user.id,
        justification="Within policy and within authority limit.",
        amount=180000.0,
    )

    app_record = db_session.get(Application, app.id)
    assert approval.decision == "approved"
    assert app_record.status == "approved"
    assert app_record.decision_reason == "Within policy and within authority limit."
    assert db_session.query(AuditLog).filter_by(application_id=app.id, action="approval:approved").count() == 1

    with pytest.raises(ValueError):
        ApprovalEngine(db_session).reject(app.id, loan_user.id, justification="Loan officer cannot reject.")

    rejected_app = Application(
        owner_id=user.id,
        requested_amount=190000.0,
        annual_rate=12.5,
        tenure_months=36,
        monthly_income=23000.0,
        other_monthly_installments=0.0,
        date_of_birth=date(1992, 5, 2),
        application_date=date(2025, 4, 1),
        policy_edition="2025",
        status="pending",
    )
    db_session.add(rejected_app)
    db_session.commit()

    reject = ApprovalEngine(db_session).reject(
        rejected_app.id,
        user.id,
        justification="Re-evaluated after document review.",
        amount=190000.0,
    )
    assert reject.decision == "rejected"
    assert db_session.get(Application, rejected_app.id).status == "rejected"

    with pytest.raises(ValueError):
        ApprovalEngine(db_session).approve(rejected_app.id, user.id, justification="Application no longer pending.")


def test_credit_officer_exceeds_authority_limit_and_admin_override(db_session):
    credit = User(username="credit.override", role="credit_officer", authority_limit=100000.0)
    admin = User(username="admin.override", role="admin", authority_limit=500000.0)
    db_session.add_all([credit, admin])
    db_session.commit()

    app = Application(
        owner_id=credit.id,
        requested_amount=250000.0,
        annual_rate=12.5,
        tenure_months=36,
        monthly_income=25000.0,
        other_monthly_installments=0.0,
        date_of_birth=date(1991, 1, 14),
        application_date=date(2025, 2, 10),
        policy_edition="2025",
        status="pending",
    )
    db_session.add(app)
    db_session.commit()

    with pytest.raises(AuthorityLimitExceeded):
        ApprovalEngine(db_session).approve(app.id, credit.id, justification="Too large.", amount=250000.0)

    approved = ApprovalEngine(db_session).approve(
        app.id,
        admin.id,
        justification="Admin override approved.",
        amount=250000.0,
    )
    assert approved.decision == "approved"
    assert db_session.get(Application, app.id).status == "approved"
