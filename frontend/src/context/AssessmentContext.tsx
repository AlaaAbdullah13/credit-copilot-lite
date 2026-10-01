import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import type { AssessResponse } from "../types";

const CACHE_KEY = "delta-assessments";

function loadCache(): Record<string, AssessResponse> {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY);
    return raw ? (JSON.parse(raw) as Record<string, AssessResponse>) : {};
  } catch {
    return {};
  }
}

function persist(cache: Record<string, AssessResponse>) {
  sessionStorage.setItem(CACHE_KEY, JSON.stringify(cache));
}

interface AssessmentContextValue {
  assessments: Record<string, AssessResponse>;
  list: AssessResponse[];
  get: (id: string) => AssessResponse | undefined;
  upsert: (result: AssessResponse) => void;
  updateStatus: (applicationId: string, status: string) => void;
  clear: () => void;
}

const AssessmentContext = createContext<AssessmentContextValue | null>(null);

export function AssessmentProvider({ children }: { children: ReactNode }) {
  const [assessments, setAssessments] = useState<Record<string, AssessResponse>>(loadCache);

  const upsert = useCallback((result: AssessResponse) => {
    const id = result.application_id;
    if (!id) return;
    setAssessments((prev) => {
      const next = { ...prev, [id]: result };
      persist(next);
      return next;
    });
  }, []);

  const updateStatus = useCallback((applicationId: string, status: string) => {
    setAssessments((prev) => {
      const current = prev[applicationId];
      if (!current) return prev;
      const next = { ...prev, [applicationId]: { ...current, status } };
      persist(next);
      return next;
    });
  }, []);

  const clear = useCallback(() => {
    sessionStorage.removeItem(CACHE_KEY);
    setAssessments({});
  }, []);

  const value = useMemo<AssessmentContextValue>(
    () => ({
      assessments,
      list: Object.values(assessments),
      get: (id) => assessments[id],
      upsert,
      updateStatus,
      clear,
    }),
    [assessments, upsert, updateStatus, clear]
  );

  return <AssessmentContext.Provider value={value}>{children}</AssessmentContext.Provider>;
}

export function useAssessments() {
  const ctx = useContext(AssessmentContext);
  if (!ctx) throw new Error("useAssessments must be used within AssessmentProvider");
  return ctx;
}
