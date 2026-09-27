import type { ReactNode } from "react";
import type { Status } from "../types";

export const Card = ({ children, className = "" }: { children: ReactNode; className?: string }) => <section className={`rounded-2xl border border-white/5 bg-card p-5 shadow-lg ${className}`}>{children}</section>;
export const Button = ({ children, className = "", ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) => <button className={`inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50 ${className}`} {...props}>{children}</button>;
export const StatusBadge = ({ status }: { status: Status | string }) => { const tone: Record<string, string> = { Approved: "bg-success/15 text-success", Pending: "bg-primary/15 text-accent", Refer: "bg-warning/15 text-warning", Rejected: "bg-danger/15 text-danger", "Pending Approval": "bg-primary/15 text-accent" }; return <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${tone[status] || tone.Pending}`}>{status}</span>; };
export const Input = (props: React.InputHTMLAttributes<HTMLInputElement>) => <input {...props} className={`w-full rounded-xl border border-white/10 bg-surface px-4 py-3 text-sm text-ink outline-none placeholder:text-muted focus:border-primary ${props.className || ""}`} />;
