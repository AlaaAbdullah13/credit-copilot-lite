export type Role = "loan_officer" | "credit_officer";

export type ApplicationStatus = "pending_approval" | "approved" | "rejected" | "issued";

export interface LoginResponse {
  token: string;
  role: string;
  username: string;
}

export interface AuthSession {
  token: string;
  role: Role;
  username: string;
}

export interface PolicyCitation {
  chunk_id: string;
  source_file?: string | null;
  clause_id?: string | null;
  page?: number | null;
  policy_edition?: string | null;
}

export interface QueryResponse {
  answer: string;
  citations: PolicyCitation[];
  reason: string;
}

export interface RuleResult {
  rule: string;
  status: string;
  citation?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface AssessResponse {
  application_id: string | null;
  calculations: {
    requested_amount?: number;
    annual_rate?: number;
    emi?: number;
    dbr?: number;
    max_amount?: number;
    tenure_months?: number;
    policy_edition?: string;
    [key: string]: unknown;
  };
  decision: string | null;
  status: string;
  recommended_amount: number | null;
  approval_required_from: string | null;
  citations: Record<string, unknown>[];
  raw_extraction: {
    extraction?: Record<string, { value?: unknown; source_section?: string; quote?: string }>;
    rule_results?: RuleResult[];
    memo?: string;
    tokens_consumed?: number;
    token_usage?: Record<string, unknown>;
    steps_executed?: string[];
    removed_fields?: string[];
    injection_detected?: boolean;
    error?: string;
    [key: string]: unknown;
  } | null;
  run_id: string;
  request_id: string;
}

export interface ApplicationStatusResponse {
  application_id: string;
  status: string;
}

export interface IngestResponse {
  status: string;
  successful: string[];
  failed: { file?: string; error?: string }[];
  chunks_ingested: number;
  chunks_inserted: number;
  chunks_skipped: number;
  documents: Record<string, Record<string, unknown>>;
  backend: string;
}

export interface ApiError {
  status: number;
  message: string;
  error?: string;
  detail?: unknown;
}

/** Seeded pack IDs accepted by POST /assess (backend-validated). */
export const APPLICATION_PACK_IDS = ["APP-001", "APP-002", "APP-003", "APP-004", "APP-005"] as const;
