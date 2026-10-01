import { useNavigate } from "react-router-dom";
import { StatusBadge } from "./ui";
import type { AssessResponse } from "../types";

function fmtMoney(n?: number) {
  if (n == null || Number.isNaN(n)) return "—";
  return `${n.toLocaleString(undefined, { maximumFractionDigits: 0 })} EGP`;
}

function fmtPct(n?: number) {
  if (n == null || Number.isNaN(n)) return "—";
  return `${n.toFixed(2)}%`;
}

function decisionLabel(app: AssessResponse) {
  if (app.status && app.status !== "pending_approval") return app.status;
  return app.decision || app.status || "pending_approval";
}

export default function ApplicationTable({ rows }: { rows: AssessResponse[] }) {
  const navigate = useNavigate();

  if (!rows.length) {
    return null;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[700px] text-left text-sm">
        <thead className="border-b border-border text-xs font-semibold uppercase tracking-wider text-muted">
          <tr>
            <th className="p-3 font-semibold">Application</th>
            <th className="p-3 font-semibold">Decision</th>
            <th className="p-3 font-semibold">Requested</th>
            <th className="p-3 font-semibold">DBR</th>
            <th className="p-3 font-semibold">Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((a) => {
            const id = a.application_id || "—";
            return (
              <tr
                key={id}
                onClick={() => id !== "—" && navigate(`/applications/${id}`)}
                className="cursor-pointer border-b border-border transition duration-150 hover:bg-lavender/40"
              >
                <td className="p-3 font-semibold text-accent">{id}</td>
                <td className="p-3 capitalize text-ink">{a.decision || "—"}</td>
                <td className="p-3 text-ink">{fmtMoney(a.calculations?.requested_amount as number | undefined)}</td>
                <td className="p-3 text-ink">{fmtPct(a.calculations?.dbr as number | undefined)}</td>
                <td className="p-3">
                  <StatusBadge status={decisionLabel(a)} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
