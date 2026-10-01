import { NavLink, useNavigate } from "react-router-dom";
import { BookOpen, CheckCircle2, ClipboardList, LayoutDashboard, LogOut, MessageSquare, ShieldCheck } from "lucide-react";
import { useAuth } from "../context/AuthContext";

const nav = [
  ["/", "Dashboard", LayoutDashboard],
  ["/applications", "Applications", ClipboardList],
  ["/qa", "Ask Copilot", MessageSquare],
  ["/knowledge-base", "Knowledge Base", BookOpen],
  ["/approvals", "Approvals", CheckCircle2],
  ["/evaluation", "Evaluation", ShieldCheck],
] as const;

function roleLabel(role: string | null) {
  if (role === "credit_officer") return "Credit Officer";
  if (role === "loan_officer") return "Loan Officer";
  return role || "—";
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const { role, username, logout } = useAuth();

  const items = nav.filter(([path]) => {
    if (path === "/approvals") return role === "credit_officer";
    return true;
  });

  return (
    <div className="min-h-screen bg-navy text-ink lg:flex">
      <aside className="flex shrink-0 flex-col border-b border-white/10 bg-primary p-5 text-white lg:sticky lg:top-0 lg:h-screen lg:w-72 lg:border-b-0 lg:border-r lg:border-white/10">
        <div className="flex items-center gap-3">
          <img src="/logo.png" alt="DELTA Credit Copilot Logo" className="h-12 w-auto" />
          <div>
            <h1 className="text-lg font-bold tracking-[0.16em] text-white">DELTA</h1>
            <p className="text-xs font-medium text-[#D4CBD9]">Credit Copilot</p>
          </div>
        </div>
        <p className="mt-5 text-xs italic leading-5 text-[#C9BECF]">“Smarter credit decisions. Human approved.”</p>

        <nav className="mt-8 grid grid-cols-2 gap-2 lg:grid-cols-1">
          {items.map(([to, label, Icon]) => (
            <NavLink
              end={to === "/"}
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition duration-200 ${
                  isActive ? "bg-[#E9E1EC]/20 text-white" : "text-[#C9BECF] hover:bg-white/10 hover:text-white"
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto hidden border-t border-white/10 pt-5 lg:block">
          <p className="mb-1 text-xs font-semibold tracking-wide text-[#C9BECF]">SIGNED IN</p>
          <div className="mt-3 flex items-center gap-3">
            <div className="grid h-9 w-9 place-items-center rounded-full bg-lavender font-bold text-primary">
              {(username || "?").slice(0, 1).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-white">{username}</p>
              <p className="text-xs text-[#C9BECF]">{roleLabel(role)}</p>
            </div>
            <button
              onClick={() => {
                logout();
                navigate("/login");
              }}
              className="rounded-lg p-2 text-[#C9BECF] transition hover:bg-white/10 hover:text-white"
              aria-label="Log out"
              title="Log out"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>
      <main className="min-w-0 flex-1 p-5 md:p-8">{children}</main>
    </div>
  );
}
