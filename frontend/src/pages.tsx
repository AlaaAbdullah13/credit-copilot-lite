import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  Bot,
  Check,
  FileText,
  Plus,
  Search,
  Sparkles,
  X,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import ApplicationTable from "./components/ApplicationTable";
import { Button, Card, EmptyState, Input, Skeleton, Spinner, StatusBadge } from "./components/ui";
import { useAssessments } from "./context/AssessmentContext";
import { useToast } from "./context/ToastContext";
import {
  approveApplication,
  askPolicy,
  assessApplication,
  getErrorMessage,
  ingestDocuments,
  rejectApplication,
} from "./services/api";
import type { AssessResponse, IngestResponse, QueryResponse, Role, RuleResult } from "./types";
import { APPLICATION_PACK_IDS } from "./types";

const Title = ({
  eyebrow,
  children,
  action,
}: {
  eyebrow?: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) => (
  <div className="mb-7 flex items-end justify-between gap-4">
    <div>
      {eyebrow && <p className="mb-1 text-xs font-bold tracking-[0.18em] text-secondary">{eyebrow}</p>}
      <h2 className="text-2xl font-bold text-ink md:text-3xl">{children}</h2>
    </div>
    {action}
  </div>
);

function greetingName(username: string | null | undefined) {
  if (!username) return "there";
  return username.replace(/_/g, " ");
}

export function Dashboard({ username }: { username: string | null }) {
  const { list } = useAssessments();
  const total = list.length;
  const pending = list.filter((a) => a.status === "pending_approval").length;
  const referred = list.filter((a) => (a.decision || "").toLowerCase().includes("refer")).length;
  const approved = list.filter((a) => a.status === "approved" || a.status === "issued").length;

  const kpis = [
    [String(total), "Assessed applications", "text-primary"],
    [String(pending), "Pending approval", "text-accent"],
    [String(referred), "Referred to human", "text-warning"],
    [String(approved), "Approved", "text-success"],
  ] as const;

  const recent = [...list].slice(-4).reverse();
  const insight = useMemo(() => {
    if (!list.length) return null;
    const pendingIds = list.filter((a) => a.status === "pending_approval").map((a) => a.application_id).filter(Boolean);
    if (!pendingIds.length) return "No applications are currently pending officer review.";
    return `${pendingIds.length} assessment${pendingIds.length === 1 ? "" : "s"} awaiting review: ${pendingIds.join(", ")}.`;
  }, [list]);

  return (
    <>
      <Title eyebrow="CREDIT OPERATIONS">Good morning, {greetingName(username)}</Title>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpis.map(([n, l, c]) => (
          <Card key={l}>
            <p className={`text-3xl font-bold ${c}`}>{n}</p>
            <p className="mt-2 text-sm text-muted">{l}</p>
          </Card>
        ))}
      </div>
      <div className="mt-6 grid gap-6 xl:grid-cols-[1.55fr_.75fr]">
        <Card>
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-semibold text-ink">Recent assessments</h3>
            <Link to="/applications" className="text-sm font-medium text-accent transition hover:text-primary">
              View all <ArrowRight className="inline" size={14} />
            </Link>
          </div>
          {recent.length ? (
            <ApplicationTable rows={recent} />
          ) : (
            <EmptyState
              title="No applications yet"
              description="There is no list endpoint on the API. Run an assessment on a seeded pack (APP-001–APP-005) to populate this view with live results."
              action={
                <Link to="/applications">
                  <Button>Go to Applications</Button>
                </Link>
              }
            />
          )}
        </Card>
        <Card className="border-lavender bg-lavender/40">
          <Sparkles className="mb-4 text-primary" size={22} />
          <h3 className="font-semibold text-primary">Copilot insight</h3>
          {insight ? (
            <p className="mt-3 text-sm leading-6 text-ink">{insight}</p>
          ) : (
            <p className="mt-3 text-sm leading-6 text-muted">
              Insights appear after you run live assessments. No fabricated pipeline summary is shown.
            </p>
          )}
        </Card>
      </div>
    </>
  );
}

export function Applications() {
  const navigate = useNavigate();
  const { list, upsert } = useAssessments();
  const { push } = useToast();
  const [term, setTerm] = useState("");
  const [filter, setFilter] = useState("All");
  const [modal, setModal] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  const rows = list.filter((x) => {
    const id = x.application_id || "";
    const matchesTerm = `${id} ${x.decision || ""}`.toLowerCase().includes(term.toLowerCase());
    if (!matchesTerm) return false;
    if (filter === "All") return true;
    if (filter === "Pending") return x.status === "pending_approval";
    if (filter === "Approved") return x.status === "approved" || x.status === "issued";
    if (filter === "Rejected") return x.status === "rejected";
    if (filter === "Referred") return (x.decision || "").toLowerCase().includes("refer");
    return true;
  });

  const runAssess = async (applicationId: string) => {
    setBusyId(applicationId);
    try {
      const result = await assessApplication(applicationId);
      upsert(result);
      push(`Assessment completed for ${applicationId}.`, "success");
      setModal(false);
      navigate(`/applications/${applicationId}`);
    } catch (err) {
      push(getErrorMessage(err), "error");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <>
      <Title
        eyebrow="UNDERWRITING PIPELINE"
        action={
          <Button onClick={() => setModal(true)}>
            <Plus size={17} />
            New Assessment
          </Button>
        }
      >
        Applications
      </Title>
      <Card>
        <div className="mb-5 flex flex-col justify-between gap-4 md:flex-row">
          <div className="flex gap-2 overflow-x-auto">
            {["All", "Pending", "Approved", "Rejected", "Referred"].map((x) => (
              <button
                key={x}
                onClick={() => setFilter(x)}
                className={`whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition ${
                  filter === x ? "bg-primary text-white" : "text-muted hover:bg-lavender hover:text-ink"
                }`}
              >
                {x}
              </button>
            ))}
          </div>
          <div className="relative md:w-72">
            <Search className="absolute left-3 top-3.5 text-muted" size={17} />
            <Input value={term} onChange={(e) => setTerm(e.target.value)} placeholder="Application ID" className="pl-9" />
          </div>
        </div>
        {rows.length ? (
          <ApplicationTable rows={rows} />
        ) : (
          <EmptyState
            title="No applications yet"
            description="The backend has no application list API. Assess a seeded pack (APP-001–APP-005) to create a live record, then manage it here."
            action={
              <Button onClick={() => setModal(true)}>
                <Plus size={17} />
                Start assessment
              </Button>
            }
          />
        )}
      </Card>

      {modal && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-primary/40 p-4 backdrop-blur-sm">
          <Card className="w-full max-w-lg">
            <div className="flex justify-between">
              <h3 className="text-lg font-bold text-ink">Start new assessment</h3>
              <button onClick={() => setModal(false)} className="text-muted hover:text-ink" aria-label="Close">
                <X />
              </button>
            </div>
            <p className="mt-2 text-sm text-muted">
              Call <code className="text-xs">POST /assess</code> with a seeded application pack ID. Arbitrary uploads are not supported by the API.
            </p>
            <p className="mb-2 mt-5 text-xs font-bold text-muted">SEEDED PACKS</p>
            <div className="grid grid-cols-5 gap-2">
              {APPLICATION_PACK_IDS.map((id) => (
                <Button key={id} disabled={busyId !== null} onClick={() => runAssess(id)} className="px-2 py-2 text-xs">
                  {busyId === id ? "…" : id}
                </Button>
              ))}
            </div>
            {busyId && <p className="mt-4 text-sm text-muted">Assessing {busyId}… this may take a moment.</p>}
          </Card>
        </div>
      )}
    </>
  );
}

function extractionValue(app: AssessResponse | undefined, key: string) {
  const field = app?.raw_extraction?.extraction?.[key];
  return field?.value != null ? String(field.value) : "—";
}

export function Detail() {
  const { id = "" } = useParams();
  const { get, upsert } = useAssessments();
  const { push } = useToast();
  const cached = get(id);
  const [app, setApp] = useState<AssessResponse | undefined>(cached);
  const [loading, setLoading] = useState(false);
  const [rule, setRule] = useState<RuleResult | null>(null);
  const [audit, setAudit] = useState(false);

  useEffect(() => {
    setApp(get(id));
  }, [id, get]);

  const runAssess = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const result = await assessApplication(id);
      upsert(result);
      setApp(result);
      push(`Loaded assessment for ${id}.`, "success");
    } catch (err) {
      push(getErrorMessage(err), "error");
    } finally {
      setLoading(false);
    }
  };

  if (!APPLICATION_PACK_IDS.includes(id as (typeof APPLICATION_PACK_IDS)[number]) && !app) {
    return (
      <>
        <Title eyebrow="APPLICATION ASSESSMENT">{id || "Unknown"}</Title>
        <EmptyState title="Application not found" description="Only seeded packs APP-001–APP-005 can be assessed, and only after a successful POST /assess." />
      </>
    );
  }

  if (!app) {
    return (
      <>
        <Title eyebrow="APPLICATION ASSESSMENT">{id}</Title>
        <Card>
          {loading ? (
            <Spinner label="Running assessment…" />
          ) : (
            <EmptyState
              title="No assessment loaded"
              description="This pack has not been assessed in this session. Run POST /assess to load live calculations, rules, and memo text from the backend."
              action={
                <Button onClick={runAssess} disabled={loading}>
                  Run assessment
                </Button>
              }
            />
          )}
        </Card>
      </>
    );
  }

  const calc = app.calculations || {};
  const rules = app.raw_extraction?.rule_results || [];
  const memo = app.raw_extraction?.memo;
  const removed = app.raw_extraction?.removed_fields || [];

  return (
    <>
      <Title eyebrow="APPLICATION ASSESSMENT">
        {app.application_id}{" "}
        <span className="text-muted text-lg font-medium">/ {app.decision || "pending"}</span>
      </Title>
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <StatusBadge status={app.status} />
        {app.decision && <StatusBadge status={app.decision} />}
        <Button className="border border-border bg-white text-primary hover:bg-lavender" onClick={runAssess} disabled={loading}>
          {loading ? "Refreshing…" : "Re-run assessment"}
        </Button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {[
          ["Net Income", extractionValue(app, "net_monthly_income")],
          ["Existing Obligations", extractionValue(app, "existing_monthly_obligations")],
          ["Requested Amount", calc.requested_amount != null ? `${Number(calc.requested_amount).toLocaleString()} EGP` : "—"],
          ["Tenor", calc.tenure_months != null ? `${calc.tenure_months} mo.` : "—"],
          ["Bureau Score", extractionValue(app, "bureau_score")],
        ].map(([l, v]) => (
          <Card className="p-4" key={l}>
            <p className="text-xs text-muted">{l}</p>
            <p className="mt-2 font-semibold text-ink">{v}</p>
          </Card>
        ))}
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1fr_1.1fr]">
        <Card>
          <p className="text-xs font-bold tracking-wider text-secondary">DETERMINISTIC CALCULATION</p>
          <div className="mt-5 grid gap-5 sm:grid-cols-3">
            <div>
              <p className="text-xs text-muted">MONTHLY INSTALLMENT (EMI)</p>
              <b className="mt-1 block text-xl text-ink">
                {calc.emi != null ? `${Number(calc.emi).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} EGP` : "—"}
              </b>
            </div>
            <div>
              <p className="text-xs text-muted">DEBT BURDEN RATIO</p>
              <b className="mt-1 block text-xl text-ink">{calc.dbr != null ? `${Number(calc.dbr).toFixed(2)}%` : "—"}</b>
              {calc.dbr != null && (
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-lavender">
                  <div className="h-full rounded-full bg-warning" style={{ width: `${Math.min(100, Number(calc.dbr) * (100 / 45))}%` }} />
                </div>
              )}
              <small className="text-muted">{String(calc.policy_edition || "")}</small>
            </div>
            <div>
              <p className="text-xs text-muted">MAX ELIGIBLE AMOUNT</p>
              <b className="mt-1 block text-xl text-ink">
                {calc.max_amount != null ? `${Number(calc.max_amount).toLocaleString()} EGP` : "—"}
              </b>
            </div>
          </div>
        </Card>
        <Card>
          <div className="flex justify-between">
            <h3 className="font-semibold text-ink">Fairness & audit trail</h3>
            <button onClick={() => setAudit(!audit)} className="text-sm font-medium text-accent hover:text-primary">
              {audit ? "Hide" : "View"}
            </button>
          </div>
          {audit && (
            <div className="mt-3 rounded-xl border border-border bg-navy p-3 text-sm">
              {removed.length ? (
                <p className="text-success">✓ Protected attributes removed ({removed.join(", ")})</p>
              ) : (
                <p className="text-muted">No removed-field metadata in this response.</p>
              )}
              <p className="mt-2 text-muted">
                Tokens: {app.raw_extraction?.tokens_consumed ?? "—"} · Steps: {(app.raw_extraction?.steps_executed || []).join(" → ") || "—"}
              </p>
            </div>
          )}
          {app.approval_required_from && (
            <p className="mt-4 text-sm text-muted">
              Approval required from: <span className="font-medium text-ink">{app.approval_required_from}</span>
            </p>
          )}
          {app.recommended_amount != null && (
            <p className="mt-2 text-sm text-muted">
              Recommended amount: <span className="font-medium text-ink">{app.recommended_amount.toLocaleString()} EGP</span>
            </p>
          )}
        </Card>
      </div>

      <Card className="mt-6">
        <h3 className="font-semibold text-ink">Rule checks</h3>
        <p className="mt-1 text-sm text-muted">Results returned by the assessment pipeline.</p>
        {rules.length ? (
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {rules.map((c) => (
              <button
                key={c.rule}
                onClick={() => setRule(c)}
                className="flex items-center justify-between rounded-xl border border-border bg-white p-4 text-left transition hover:border-accent/50 hover:bg-lavender/30"
              >
                <span>
                  <b className="block text-sm capitalize text-ink">{c.rule.replace(/_/g, " ")}</b>
                  <small className="capitalize text-muted">{c.status}</small>
                </span>
                {c.status === "pass" ? <Check className="text-success" /> : <AlertTriangle className="text-warning" size={18} />}
              </button>
            ))}
          </div>
        ) : (
          <p className="mt-4 text-sm text-muted">No rule results in this assessment response.</p>
        )}
      </Card>

      <Card className="mt-6">
        <div className="flex items-center gap-2">
          <Bot className="text-primary" />
          <h3 className="font-semibold text-ink">Credit memo</h3>
        </div>
        {memo ? (
          <p className="mt-4 leading-7 text-ink whitespace-pre-wrap">{memo}</p>
        ) : (
          <p className="mt-4 text-sm text-muted">No memo text was returned for this assessment.</p>
        )}
      </Card>

      {rule && (
        <div className="fixed inset-0 z-50 flex justify-end bg-primary/40" onClick={() => setRule(null)}>
          <aside onClick={(e) => e.stopPropagation()} className="h-full w-full max-w-md border-l border-border bg-card p-7 shadow-soft">
            <button className="float-right text-muted hover:text-ink" onClick={() => setRule(null)} aria-label="Close">
              <X />
            </button>
            <p className="text-xs font-bold text-secondary">POLICY CLAUSE CITATION</p>
            <h3 className="mt-3 text-xl font-bold capitalize text-ink">{rule.rule.replace(/_/g, " ")}</h3>
            <div className="mt-6 rounded-xl border border-border bg-lavender/50 p-4">
              <b className="text-primary">{String((rule.citation as { clause_id?: string } | undefined)?.clause_id || "—")}</b>
              <p className="mt-3 text-sm text-muted">Status: {rule.status}</p>
              <pre className="mt-3 overflow-x-auto text-xs text-muted">{JSON.stringify(rule.citation || {}, null, 2)}</pre>
            </div>
          </aside>
        </div>
      )}
    </>
  );
}

export function QA() {
  const [q, setQ] = useState("");
  const [edition, setEdition] = useState("CP-2025");
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const { push } = useToast();

  const run = async (value = q) => {
    if (!value.trim()) return;
    setQ(value);
    setLoading(true);
    setResult(null);
    try {
      const data = await askPolicy(value, edition);
      setResult(data);
    } catch (err) {
      push(getErrorMessage(err), "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Title eyebrow="GROUNDED POLICY SEARCH">Ask Copilot</Title>
      <Card className="max-w-4xl">
        <div className="mb-4 flex flex-wrap gap-2">
          {["CP-2025", "CP-2024"].map((ed) => (
            <button
              key={ed}
              onClick={() => setEdition(ed)}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                edition === ed ? "bg-primary text-white" : "bg-lavender text-primary"
              }`}
            >
              {ed}
            </button>
          ))}
        </div>
        <div className="flex gap-3">
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && run()}
            placeholder="Ask anything about the credit policy..."
          />
          <Button onClick={() => run()} disabled={!q || loading}>
            {loading ? "Searching…" : "Ask"}
          </Button>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {["What is the maximum DBR for 2025?", "What is the policy on crypto-backed loans?"].map((x) => (
            <button
              key={x}
              onClick={() => run(x)}
              className="rounded-full border border-border bg-white px-3 py-2 text-xs text-muted transition hover:border-accent/40 hover:bg-lavender hover:text-primary"
            >
              {x}
            </button>
          ))}
        </div>
      </Card>

      {loading && (
        <Card className="mt-6 max-w-4xl">
          <Spinner label="Querying policy corpus…" />
        </Card>
      )}

      {result && !loading && (result.reason === "no_chunk_above_threshold" || !result.answer ? (
        <Card className="mt-6 max-w-4xl border-warning/40 bg-[#F6EFE3]/40">
          <div className="flex gap-3 text-warning">
            <AlertTriangle />
            <div>
              <b className="text-ink">{result.answer || "I couldn't find enough information in the available documents."}</b>
              <p className="mt-1 text-sm text-muted">Reason: {result.reason}</p>
            </div>
          </div>
        </Card>
      ) : (
        <Card className="mt-6 max-w-4xl">
          <div className="flex gap-2">
            <Sparkles className="text-primary" />
            <h3 className="font-semibold text-ink">Grounded answer</h3>
          </div>
          <p className="mt-4 leading-7 text-ink">{result.answer}</p>
          <div className="mt-5 flex flex-wrap gap-2">
            {result.citations?.length ? (
              result.citations.map((c) => (
                <span
                  key={c.chunk_id}
                  title={[c.source_file, c.clause_id, c.policy_edition].filter(Boolean).join(" · ")}
                  className="rounded-lg bg-lavender px-3 py-2 text-xs font-bold text-primary"
                >
                  {[c.source_file || c.chunk_id, c.clause_id].filter(Boolean).join(" · ")}
                </span>
              ))
            ) : (
              <span className="text-sm text-muted">No citations returned.</span>
            )}
          </div>
        </Card>
      ))}
    </>
  );
}

export function Knowledge() {
  const [report, setReport] = useState<IngestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const { push } = useToast();

  const runIngest = async () => {
    setLoading(true);
    try {
      const data = await ingestDocuments();
      setReport(data);
      push("Ingestion completed.", "success");
    } catch (err) {
      push(getErrorMessage(err), "error");
    } finally {
      setLoading(false);
    }
  };

  const docs = report ? Object.entries(report.documents || {}) : [];

  return (
    <>
      <Title
        eyebrow="TRUSTED POLICY CORPUS"
        action={
          <Button onClick={runIngest} disabled={loading}>
            <Plus size={17} />
            {loading ? "Ingesting…" : "Ingest Documents"}
          </Button>
        }
      >
        Knowledge Base
      </Title>

      {!report && !loading && (
        <EmptyState
          title="No ingestion report yet"
          description="Call POST /ingest to load the trusted policy corpus status from the backend. Document upload is not exposed by the API."
          action={
            <Button onClick={runIngest}>
              <Plus size={17} />
              Ingest Documents
            </Button>
          }
        />
      )}

      {loading && (
        <Card>
          <Spinner label="Running ingestion…" />
          <div className="mt-2 grid gap-3 sm:grid-cols-4">
            <Skeleton className="h-10" />
            <Skeleton className="h-10" />
            <Skeleton className="h-10" />
            <Skeleton className="h-10" />
          </div>
        </Card>
      )}

      {report && !loading && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Card>
              <p className="text-3xl font-bold text-primary">{report.chunks_ingested}</p>
              <p className="mt-2 text-sm text-muted">Chunks ingested</p>
            </Card>
            <Card>
              <p className="text-3xl font-bold text-primary">{report.chunks_inserted}</p>
              <p className="mt-2 text-sm text-muted">Chunks inserted</p>
            </Card>
            <Card>
              <p className="text-3xl font-bold text-accent">{report.chunks_skipped}</p>
              <p className="mt-2 text-sm text-muted">Chunks skipped</p>
            </Card>
            <Card>
              <p className="text-lg font-bold text-ink">{report.backend}</p>
              <p className="mt-2 text-sm text-muted">Vector backend · {report.status}</p>
            </Card>
          </div>

          <Card className="mt-6 overflow-x-auto">
            {docs.length ? (
              <table className="w-full min-w-[600px] text-left text-sm">
                <thead className="border-b border-border text-xs font-semibold uppercase tracking-wider text-muted">
                  <tr>
                    <th className="p-3">Document</th>
                    <th className="p-3">Details</th>
                  </tr>
                </thead>
                <tbody>
                  {docs.map(([name, meta]) => (
                    <tr key={name} className="border-b border-border">
                      <td className="p-3 font-medium text-ink">
                        <span className="inline-flex items-center gap-2">
                          <FileText size={16} className="text-accent" />
                          {name.split("/").pop()}
                        </span>
                      </td>
                      <td className="p-3 text-muted">
                        <code className="text-xs">{JSON.stringify(meta)}</code>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <EmptyState title="No per-document details" description="The ingest response did not include a documents map." />
            )}
            {report.failed?.length > 0 && (
              <div className="mt-4 rounded-xl bg-[#F5E8EA] p-3 text-sm text-danger">
                {report.failed.map((f, i) => (
                  <p key={i}>
                    {f.file}: {f.error}
                  </p>
                ))}
              </div>
            )}
          </Card>
        </>
      )}
    </>
  );
}

export function Approvals({ role }: { role: Role | null }) {
  const { list, updateStatus } = useAssessments();
  const { push } = useToast();
  const pending = list.filter((a) => a.status === "pending_approval");
  const [selectedId, setSelectedId] = useState<string>("");
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!selectedId && pending[0]?.application_id) {
      setSelectedId(pending[0].application_id!);
    }
  }, [pending, selectedId]);

  const app = pending.find((a) => a.application_id === selectedId) || pending[0];

  const submit = async (action: "approve" | "reject") => {
    if (!app?.application_id) return;
    setBusy(true);
    try {
      const result =
        action === "approve"
          ? await approveApplication(app.application_id, comment)
          : await rejectApplication(app.application_id, comment);
      updateStatus(result.application_id, result.status);
      push(`${result.application_id} marked ${result.status}.`, "success");
      setComment("");
    } catch (err) {
      push(getErrorMessage(err), "error");
    } finally {
      setBusy(false);
    }
  };

  if (role !== "credit_officer") {
    return (
      <>
        <Title eyebrow="CREDIT OFFICER QUEUE">Approval Center</Title>
        <Card>
          <p className="text-warning">Credit Officer access is required. Your role is determined by authentication — switch accounts by signing out and signing in again.</p>
        </Card>
      </>
    );
  }

  return (
    <>
      <Title eyebrow="CREDIT OFFICER QUEUE">Approval Center</Title>
      {!pending.length ? (
        <EmptyState
          title="No pending approvals"
          description="Assess an application first (POST /assess). Pending items from this session appear here for approve/reject via the live API."
          action={
            <Link to="/applications">
              <Button>Go to Applications</Button>
            </Link>
          }
        />
      ) : (
        <div className="grid gap-6 xl:grid-cols-[.8fr_1.2fr]">
          <Card>
            <p className="text-xs text-muted">PENDING SIGN-OFF</p>
            <label className="mt-3 block text-xs font-semibold text-muted">Application</label>
            <select
              value={app?.application_id || ""}
              onChange={(e) => setSelectedId(e.target.value)}
              className="mt-1 w-full rounded-lg border border-border bg-white p-2.5 text-sm text-ink"
            >
              {pending.map((p) => (
                <option key={p.application_id!} value={p.application_id!}>
                  {p.application_id}
                </option>
              ))}
            </select>
            {app && (
              <>
                <h3 className="mt-4 text-xl font-bold text-ink">{app.application_id}</h3>
                <div className="mt-3 flex flex-wrap gap-2">
                  <StatusBadge status={app.status} />
                  {app.decision && <StatusBadge status={app.decision} />}
                </div>
                <dl className="mt-5 space-y-3 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-muted">Recommendation</dt>
                    <dd className="capitalize text-accent">{app.decision || "—"}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-muted">Calculated DBR</dt>
                    <dd className="text-ink">{app.calculations?.dbr != null ? `${Number(app.calculations.dbr).toFixed(2)}%` : "—"}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-muted">Recommended amount</dt>
                    <dd className="text-ink">{app.recommended_amount != null ? `${app.recommended_amount.toLocaleString()} EGP` : "—"}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-muted">Authority required</dt>
                    <dd className="text-ink">{app.approval_required_from || "—"}</dd>
                  </div>
                </dl>
              </>
            )}
          </Card>
          <Card>
            <h3 className="font-semibold text-ink">Officer decision</h3>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Add an approval or rejection comment…"
              className="mt-4 h-28 w-full rounded-xl border border-border bg-white p-3 text-sm text-ink outline-none placeholder:text-muted focus:border-accent"
            />
            <div className="mt-4 flex gap-3">
              <Button className="bg-danger hover:bg-[#8F454C]" disabled={busy || !app} onClick={() => submit("reject")}>
                Reject
              </Button>
              <Button disabled={busy || !app} onClick={() => submit("approve")}>
                Approve
              </Button>
            </div>
            <p className="mt-3 text-xs text-muted">Calls POST /approve or POST /reject. Backend authorization and authority limits still apply.</p>
          </Card>
        </div>
      )}
    </>
  );
}

export function Evaluation() {
  return (
    <>
      <Title eyebrow="FR-6 TEST SUITE">System Evaluation</Title>
      <EmptyState
        title="No evaluation API available"
        description="Evaluation is implemented as a CLI tool (python src/cli/evaluate.py), not an HTTP endpoint. Results are not served by the backend, so this page does not invent metrics."
      />
      <Card className="mt-6">
        <h3 className="font-semibold text-ink">How to run evaluation</h3>
        <p className="mt-2 text-sm leading-6 text-muted">
          From the project root, run <code className="rounded bg-lavender px-1.5 py-0.5 text-xs text-primary">python src/cli/evaluate.py</code> and review{" "}
          <code className="rounded bg-lavender px-1.5 py-0.5 text-xs text-primary">docs/EVALUATION.md</code> for the recorded suite.
        </p>
      </Card>
    </>
  );
}
