import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  KeyRound,
  Wrench,
} from "lucide-react";
import { useEffect, useState } from "react";
import { type DashboardData, api } from "../lib/api";

function Kpi({
  label,
  value,
  icon: Icon,
}: { label: string; value: string; icon: typeof Wrench }) {
  return (
    <div
      className="rounded-xl border border-zinc-800 bg-panel p-4"
      data-testid={`kpi-${label.toLowerCase().replace(/\s+/g, "-")}`}
    >
      <div className="flex items-center gap-2 text-zinc-400 text-sm">
        <Icon size={16} />
        {label}
      </div>
      <div className="mt-2 text-2xl font-semibold text-zinc-100">{value}</div>
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api
      .dashboard()
      .then(setData)
      .catch(() => setError(true));
  }, []);

  const needsOnboarding = data && (!data.configured || !data.authenticated);

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      <div className="rounded-2xl border border-zinc-800 bg-gradient-to-br from-panel to-surface p-8">
        <h1 className="text-2xl font-bold text-zinc-100">google-docs-mcp</h1>
        <p className="mt-2 max-w-2xl text-zinc-400">
          Real Google Docs editing and Google Drive file management, driven by
          natural-language prompts to Claude — no third-party proxy, your own
          OAuth credentials.
        </p>
      </div>

      {needsOnboarding && (
        <a
          href="#/onboarding"
          data-testid="onboarding-cue"
          className="flex items-center justify-center gap-2 rounded-xl border-2 border-red-600 bg-red-600/10 px-4 py-3 font-semibold text-red-400 hover:bg-red-600/20"
        >
          <AlertTriangle size={18} />
          Complete onboarding — connect your Google account
        </a>
      )}

      {error && (
        <div className="rounded-xl border border-red-800 bg-red-950/40 p-4 text-red-300">
          Could not reach the backend at /api/dashboard — is the server running?
        </div>
      )}

      {data && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Kpi label="Version" value={data.version} icon={Wrench} />
          <Kpi label="Tools" value={String(data.tool_count)} icon={FileText} />
          <Kpi
            label="Configured"
            value={data.configured ? "Yes" : "No"}
            icon={KeyRound}
          />
          <Kpi
            label="Authenticated"
            value={data.authenticated ? "Yes" : "No"}
            icon={data.authenticated ? CheckCircle2 : AlertTriangle}
          />
        </div>
      )}
    </div>
  );
}
