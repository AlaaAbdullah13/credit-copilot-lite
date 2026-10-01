import type { ReactNode } from "react";
import { Loader2 } from "lucide-react";

export const Card = ({ children, className = "" }: { children: ReactNode; className?: string }) => (
  <section className={`rounded-2xl border border-border bg-card p-5 shadow-soft ${className}`}>{children}</section>
);

export const Button = ({ children, className = "", ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) => {
  const hasCustomBg = /\bbg-/.test(className);
  const base =
    "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition duration-200 disabled:cursor-not-allowed disabled:opacity-50";
  const primary = hasCustomBg ? "" : "bg-primary text-white hover:bg-[#4F3F5C]";
  return (
    <button className={`${base} ${primary} ${className}`} {...props}>
      {children}
    </button>
  );
};

export const StatusBadge = ({ status }: { status: string }) => {
  const normalized = status.toLowerCase().replace(/_/g, " ");
  const tone =
    normalized.includes("approved") || normalized === "approve"
      ? "bg-[#E8F2EE] text-success"
      : normalized.includes("reject") || normalized.includes("decline")
        ? "bg-[#F5E8EA] text-danger"
        : normalized.includes("refer")
          ? "bg-[#F6EFE3] text-warning"
          : normalized.includes("issued")
            ? "bg-[#E8F2EE] text-success"
            : "bg-lavender text-primary";
  const label = status
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${tone}`}>{label}</span>;
};

export const Input = (props: React.InputHTMLAttributes<HTMLInputElement>) => (
  <input
    {...props}
    className={`w-full rounded-xl border border-border bg-white px-4 py-3 text-sm text-ink outline-none placeholder:text-muted focus:border-accent ${props.className || ""}`}
  />
);

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-12 text-sm text-muted">
      <Loader2 className="animate-spin text-accent" size={20} />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-border bg-white px-6 py-12 text-center">
      <h3 className="text-base font-semibold text-ink">{title}</h3>
      {description ? <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted">{description}</p> : null}
      {action ? <div className="mt-5 flex justify-center">{action}</div> : null}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-xl bg-lavender/70 ${className}`} />;
}
