import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { BookOpen, CheckCircle2, ClipboardList, LayoutDashboard, LogOut, MessageSquare, ShieldCheck } from "lucide-react";
import type { Role } from "../types";
import { setRole } from "../services/api";
const nav = [["/", "Dashboard", LayoutDashboard], ["/applications", "Applications", ClipboardList], ["/qa", "Ask Copilot", MessageSquare], ["/knowledge-base", "Knowledge Base", BookOpen], ["/approvals", "Approvals", CheckCircle2], ["/evaluation", "Evaluation", ShieldCheck]] as const;
export default function Layout({ children, role, onRole }: { children: React.ReactNode; role: Role; onRole: (role: Role) => void }) {
 const navigate = useNavigate(); const changeRole = (v: Role) => { onRole(v); setRole(v); };
 return <div className="min-h-screen bg-navy text-ink lg:flex"><aside className="flex shrink-0 flex-col border-b border-white/5 bg-surface p-5 lg:sticky lg:top-0 lg:h-screen lg:w-72 lg:border-b-0 lg:border-r">
  <div className="flex items-center gap-3"><img src="/logo.png" alt="DELTA Credit Copilot Logo" className="h-10 w-auto"/><div><h1 className="font-bold tracking-[.18em]">DELTA</h1><p className="text-xs text-muted">Credit Copilot</p></div></div><p className="mt-5 text-xs italic leading-5 text-muted">“Smarter credit decisions. Human approved.”</p>
  <nav className="mt-8 grid grid-cols-2 gap-2 lg:grid-cols-1">{nav.map(([to, label, Icon]) => <NavLink end={to === "/"} key={to} to={to} className={({isActive}) => `flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition ${isActive ? "bg-primary/15 text-accent" : "text-muted hover:bg-white/5 hover:text-ink"}`}><Icon size={18}/>{label}{label === "Approvals" && role === "credit_officer" && <span className="ml-auto rounded-full bg-secondary/15 px-2 py-0.5 text-[10px] text-secondary">Officer</span>}</NavLink>)}</nav>
  <div className="mt-auto hidden border-t border-white/5 pt-5 lg:block"><label className="mb-2 block text-xs font-semibold text-muted">DEMO ROLE</label><select value={role} onChange={e => changeRole(e.target.value as Role)} className="w-full rounded-lg border border-white/10 bg-card p-2.5 text-sm"><option value="loan_officer">Loan Officer</option><option value="credit_officer">Credit Officer</option></select><div className="mt-5 flex items-center gap-3"><div className="grid h-9 w-9 place-items-center rounded-full bg-primary font-bold">A</div><div className="text-sm"><b>Alaa</b><button onClick={() => navigate("/login")} className="ml-2 text-xs text-muted hover:text-ink"><LogOut size={14}/></button></div></div></div>
 </aside><main className="min-w-0 flex-1 p-5 md:p-8">{children}</main></div>;
}
