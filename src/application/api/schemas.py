"""HTTP request and response schemas for the public API."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    # Demo usernames are account identifiers; ``credit_officer`` is a role,
    # not a valid login name.  Keep Swagger aligned with the seeded account.
    username: str | None = Field(default=None, examples=["credit1"])
    password: str | None = Field(default=None, examples=["credit_demo_2026"])


class LoginResponse(BaseModel):
    token: str
    role: str
    username: str


class QueryRequest(BaseModel):
    question: str | None = Field(
        default=None,
        examples=["What is the maximum debt burden ratio in the 2025 credit policy?"],
    )
    policy_edition: str | None = Field(default=None, examples=["CP-2025"])


class PolicyCitation(BaseModel):
    chunk_id: str
    source_file: str | None = None
    clause_id: str | None = None
    page: int | None = None
    policy_edition: str | None = None


class QueryResponse(BaseModel):
    answer: str
    citations: list[PolicyCitation]
    reason: str


class AssessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application_id: str = Field(examples=["APP-001"])


class AssessResponse(BaseModel):
    application_id: str | None = None
    calculations: dict[str, Any] = Field(default_factory=dict)
    decision: str | None = None
    status: str
    recommended_amount: float | None = None
    approval_required_from: str | None = None
    citations: list[dict[str, Any]] = Field(default_factory=list)
    raw_extraction: dict[str, Any] | None = None
    run_id: str
    request_id: str


class DecisionRequest(BaseModel):
    application_id: str | None = Field(default=None, examples=["APP-001"])
    amount: float | None = Field(default=None, examples=[200000])
    comment: str | None = Field(default=None, examples=["Income and bureau verified."])


class IssueRequest(BaseModel):
    application_id: str | None = Field(default=None, examples=["APP-001"])


class ApplicationStatusResponse(BaseModel):
    application_id: str
    status: str


class IngestResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str
    successful: list[str]
    failed: list[dict[str, str]]
    chunks_ingested: int
    chunks_inserted: int
    chunks_skipped: int
    documents: dict[str, dict[str, Any]]
    backend: str


class ErrorResponse(BaseModel):
    error: str
    detail: str
