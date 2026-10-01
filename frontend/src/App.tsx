import { useState } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import Layout from "./components/Layout";
import { Approvals, Applications, Dashboard, Detail, Evaluation, Knowledge, QA } from "./pages";
import { Button, Input } from "./components/ui";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { AssessmentProvider } from "./context/AssessmentContext";
import { ToastProvider, useToast } from "./context/ToastContext";
import { getErrorMessage } from "./services/api";

function Login() {
  const nav = useNavigate();
  const { login, isAuthenticated } = useAuth();
  const { push } = useToast();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  if (isAuthenticated) return <Navigate to="/" replace />;

  const submit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setLoading(true);
    try {
      await login(username.trim(), password);
      push("Signed in successfully.", "success");
      nav("/");
    } catch (err) {
      push(getErrorMessage(err), "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="grid min-h-screen place-items-center bg-navy p-5">
      <section className="z-10 w-full max-w-md rounded-2xl border border-border bg-card p-8 shadow-soft">
        <div className="text-center">
          <img src="/logo.png" alt="DELTA Credit Copilot Logo" className="mx-auto h-16 w-auto" />
          <h1 className="mt-4 text-2xl font-bold tracking-[0.16em] text-primary">DELTA</h1>
          <p className="text-sm font-medium text-muted">Credit Copilot</p>
          <p className="mt-4 text-sm italic text-muted">Smarter credit decisions. Human approved.</p>
        </div>
        <form className="mt-7 space-y-4" onSubmit={submit}>
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-muted">Username</label>
            <Input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" autoComplete="username" />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-muted">Password</label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              autoComplete="current-password"
            />
          </div>
          <Button className="w-full" type="submit" disabled={loading || !username || !password}>
            {loading ? "Signing in…" : "Login to workspace"}
          </Button>
        </form>
        <p className="mt-5 text-center text-xs leading-5 text-muted">
          Role is assigned by the backend after authentication. Use your seeded demo account credentials.
        </p>
      </section>
    </main>
  );
}

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function Workspace() {
  const { role, username } = useAuth();
  return (
    <AssessmentProvider>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard username={username} />} />
          <Route path="/applications" element={<Applications />} />
          <Route path="/applications/:id" element={<Detail />} />
          <Route path="/qa" element={<QA />} />
          <Route path="/knowledge-base" element={<Knowledge />} />
          <Route path="/approvals" element={<Approvals role={role} />} />
          <Route path="/evaluation" element={<Evaluation />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </AssessmentProvider>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/*"
            element={
              <RequireAuth>
                <Workspace />
              </RequireAuth>
            }
          />
        </Routes>
      </ToastProvider>
    </AuthProvider>
  );
}
