import axios, { AxiosError } from "axios";
import type {
  ApplicationStatusResponse,
  AssessResponse,
  AuthSession,
  IngestResponse,
  LoginResponse,
  QueryResponse,
} from "../types";

const STORAGE_KEY = "delta-auth";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
});

export function loadSession(): AuthSession | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AuthSession;
    if (!parsed?.token || !parsed?.role || !parsed?.username) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function saveSession(session: AuthSession | null) {
  if (!session) {
    localStorage.removeItem(STORAGE_KEY);
    delete api.defaults.headers.common.Authorization;
    return;
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  api.defaults.headers.common.Authorization = `Bearer ${session.token}`;
}

const existing = loadSession();
if (existing) {
  api.defaults.headers.common.Authorization = `Bearer ${existing.token}`;
}

export function getErrorMessage(err: unknown): string {
  if (!axios.isAxiosError(err)) {
    if (err instanceof Error) return err.message;
    return "Something went wrong. Please try again.";
  }
  const ax = err as AxiosError<{ detail?: unknown; error?: string }>;
  if (!ax.response) {
    return "Unable to reach the server. Check that the API is running.";
  }
  const status = ax.response.status;
  const data = ax.response.data;
  const detail =
    typeof data?.detail === "string"
      ? data.detail
      : Array.isArray(data?.detail)
        ? data.detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join("; ")
        : data?.error
          ? `${data.error}${typeof data.detail === "string" ? `: ${data.detail}` : ""}`
          : null;

  if (status === 401) {
    if (detail?.toLowerCase().includes("username") || detail?.toLowerCase().includes("password")) {
      return detail;
    }
    return "Your session has expired. Please sign in again.";
  }
  if (status === 403) return detail || "You don't have permission to perform this action.";
  if (status === 404) return detail || "The requested resource could not be found.";
  if (status === 400) return detail || "Invalid request. Please check your input.";
  if (status === 409) return detail || "This action conflicts with the current application state.";
  if (status === 422) return detail || "The request could not be validated.";
  if (status === 503) return detail || "A required service is temporarily unavailable.";
  if (status >= 500) return "Something went wrong. Please try again.";
  return detail || "Something went wrong. Please try again.";
}

export async function login(username: string, password: string): Promise<AuthSession> {
  const { data } = await api.post<LoginResponse>("/login", { username, password });
  const session: AuthSession = {
    token: data.token,
    role: data.role as AuthSession["role"],
    username: data.username,
  };
  saveSession(session);
  return session;
}

export function logout() {
  saveSession(null);
}

export async function askPolicy(question: string, policyEdition = "CP-2025"): Promise<QueryResponse> {
  const { data } = await api.post<QueryResponse>("/query", {
    question,
    policy_edition: policyEdition,
  });
  return data;
}

export async function assessApplication(applicationId: string): Promise<AssessResponse> {
  const { data } = await api.post<AssessResponse>("/assess", { application_id: applicationId });
  return data;
}

export async function approveApplication(applicationId: string, comment?: string): Promise<ApplicationStatusResponse> {
  const { data } = await api.post<ApplicationStatusResponse>("/approve", {
    application_id: applicationId,
    comment: comment || null,
  });
  return data;
}

export async function rejectApplication(applicationId: string, comment?: string): Promise<ApplicationStatusResponse> {
  const { data } = await api.post<ApplicationStatusResponse>("/reject", {
    application_id: applicationId,
    comment: comment || null,
  });
  return data;
}

export async function issueApplication(applicationId: string): Promise<ApplicationStatusResponse> {
  const { data } = await api.post<ApplicationStatusResponse>("/issue", {
    application_id: applicationId,
  });
  return data;
}

export async function ingestDocuments(): Promise<IngestResponse> {
  const { data } = await api.post<IngestResponse>("/ingest");
  return data;
}
