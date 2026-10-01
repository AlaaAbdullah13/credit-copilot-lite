import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { CheckCircle2, Info, X, XCircle } from "lucide-react";

type ToastTone = "success" | "error" | "info";

interface ToastItem {
  id: number;
  message: string;
  tone: ToastTone;
}

interface ToastContextValue {
  push: (message: string, tone?: ToastTone) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const push = useCallback((message: string, tone: ToastTone = "info") => {
    const id = Date.now() + Math.random();
    setItems((prev) => [...prev, { id, message, tone }]);
    window.setTimeout(() => {
      setItems((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  }, []);

  const value = useMemo(() => ({ push }), [push]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed bottom-5 right-5 z-[100] flex w-full max-w-sm flex-col gap-2">
        {items.map((t) => (
          <div
            key={t.id}
            className={`pointer-events-auto flex items-start gap-3 rounded-xl border px-4 py-3 text-sm shadow-soft transition ${
              t.tone === "success"
                ? "border-[#D7E8E1] bg-[#E8F2EE] text-success"
                : t.tone === "error"
                  ? "border-[#EBD6D9] bg-[#F5E8EA] text-danger"
                  : "border-border bg-white text-ink"
            }`}
          >
            {t.tone === "success" ? <CheckCircle2 size={18} className="mt-0.5 shrink-0" /> : null}
            {t.tone === "error" ? <XCircle size={18} className="mt-0.5 shrink-0" /> : null}
            {t.tone === "info" ? <Info size={18} className="mt-0.5 shrink-0 text-accent" /> : null}
            <p className="flex-1 leading-5 text-ink">{t.message}</p>
            <button
              className="text-muted hover:text-ink"
              onClick={() => setItems((prev) => prev.filter((x) => x.id !== t.id))}
              aria-label="Dismiss"
            >
              <X size={16} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
