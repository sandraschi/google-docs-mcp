import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  FileText,
  FolderOpen,
  KeyRound,
  MessageSquareText,
  RefreshCw,
  Wrench,
} from "lucide-react";
import { useEffect, useState } from "react";
import { API_BASE, type DashboardData, api } from "../lib/api";

type RecentFile = {
  id: string;
  name: string;
  mimeType: string;
  modifiedTime: string;
  webViewLink?: string;
};

function Kpi({
  label,
  value,
  sub,
  icon: Icon,
  href,
}: {
  label: string;
  value: string;
  sub?: string;
  icon: typeof Wrench;
  href?: string;
}) {
  const inner = (
    <div
      className="rounded-xl border border-zinc-800 bg-panel p-4"
      data-testid={`kpi-${label.toLowerCase().replace(/\s+/g, "-")}`}
    >
      <div className="flex items-center gap-2 text-zinc-400 text-sm">
        <Icon size={16} />
        {label}
      </div>
      <div className="mt-2 text-2xl font-semibold text-zinc-100">{value}</div>
      {sub && <div className="mt-1 text-xs text-zinc-500">{sub}</div>}
    </div>
  );
  return href ? (
    <a href={href} className="block hover:border-zinc-600">
      {inner}
    </a>
  ) : (
    inner
  );
}

function kindLabel(mime: string): string {
  if (mime === "application/vnd.google-apps.document") return "Doc";
  if (mime === "application/vnd.google-apps.spreadsheet") return "Sheet";
  if (mime === "application/vnd.google-apps.presentation") return "Slides";
  if (mime === "application/vnd.google-apps.folder") return "Folder";
  if (mime.startsWith("application/pdf")) return "PDF";
  return mime.split("/").pop() ?? "file";
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [recents, setRecents] = useState<RecentFile[]>([]);
  const [recentsBlocked, setRecentsBlocked] = useState(false);
  const [syncState, setSyncState] = useState<string>("—");
  const [error, setError] = useState(false);

  useEffect(() => {
    api
      .dashboard()
      .then(setData)
      .catch(() => setError(true));
    fetch(`${API_BASE}/api/recent`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        if (d.needs_auth) setRecentsBlocked(true);
        else if (Array.isArray(d.items)) setRecents(d.items);
      })
      .catch(() => {});
    fetch(`${API_BASE}/api/sync/status`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        const tracked = d?.data?.tracked_count ?? d?.tracked_count;
        if (typeof tracked === "number") setSyncState(`${tracked} tracked`);
      })
      .catch(() => {});
  }, []);

  const needsOnboarding = data && (!data.configured || !data.authenticated);

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      <div className="rounded-2xl border border-zinc-800 bg-gradient-to-br from-panel to-surface p-8">
        <h1 className="text-2xl font-bold text-zinc-100">google-docs-mcp</h1>
        <p className="mt-2 max-w-2xl text-zinc-400">
          Real Google Docs editing and Google Drive file management, driven by
          natural-language prompts to Claude — no third-party proxy, your own
          OAuth credentials. Search, read, create, share, and sync docs to a
          local folder; every action below exists as an MCP tool too.
        </p>
        <div className="mt-4 flex flex-wrap gap-2" data-testid="hero-actions">
          <a
            href="#/documents"
            className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-zinc-950 hover:bg-amber-400"
          >
            Browse Drive
          </a>
          <a
            href="#/chat"
            className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-200 hover:bg-zinc-800"
          >
            Ask about docs
          </a>
          <a
            href="#/sync"
            className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-200 hover:bg-zinc-800"
          >
            Sync status
          </a>
          <a
            href="#/tools"
            className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-200 hover:bg-zinc-800"
          >
            Browse tools
          </a>
        </div>
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
        <div
          className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6"
          data-testid="kpi-grid"
        >
          <Kpi label="Version" value={data.version} icon={Wrench} />
          <Kpi
            label="Tools"
            value={String(data.tool_count)}
            sub="MCP + REST"
            icon={FileText}
            href="#/tools"
          />
          <Kpi
            label="Connection"
            value={
              data.authenticated ? "Live" : data.configured ? "Idle" : "Setup"
            }
            sub={data.authenticated ? "grant valid" : "see onboarding"}
            icon={data.authenticated ? CheckCircle2 : KeyRound}
            href="#/onboarding"
          />
          <Kpi
            label="Recent docs"
            value={recentsBlocked ? "—" : String(recents.length)}
            sub={recentsBlocked ? "sign in first" : "last modified"}
            icon={Clock3}
            href="#/documents"
          />
          <Kpi label="Sync" value={syncState} icon={RefreshCw} href="#/sync" />
          <Kpi
            label="Chat"
            value="Ready"
            sub="ask about docs"
            icon={MessageSquareText}
            href="#/chat"
          />
        </div>
      )}

      <div
        className="rounded-xl border border-zinc-800 bg-panel p-4"
        data-testid="recent-docs"
      >
        <div className="mb-3 flex items-center gap-2 text-zinc-200">
          <FolderOpen size={16} />
          <h2 className="font-semibold">Recently modified</h2>
        </div>
        {recentsBlocked ? (
          <p className="text-sm text-zinc-400">
            Sign in first —{" "}
            <a href="#/onboarding" className="text-amber-400 hover:underline">
              complete onboarding
            </a>
            , then your latest Drive files appear here.
          </p>
        ) : recents.length === 0 ? (
          <p className="text-sm text-zinc-500">
            Nothing yet — create a doc or wait for Drive changes.
          </p>
        ) : (
          <ul className="divide-y divide-zinc-800">
            {recents.map((f) => (
              <li key={f.id} className="flex items-center gap-3 py-2">
                <span className="rounded bg-zinc-800 px-2 py-0.5 text-xs text-zinc-300">
                  {kindLabel(f.mimeType)}
                </span>
                {f.webViewLink ? (
                  <a
                    href={f.webViewLink}
                    target="_blank"
                    rel="noreferrer"
                    className="truncate text-sm text-zinc-100 hover:underline"
                    title={f.name}
                  >
                    {f.name}
                  </a>
                ) : (
                  <span
                    className="truncate text-sm text-zinc-100"
                    title={f.name}
                  >
                    {f.name}
                  </span>
                )}
                <span className="ml-auto shrink-0 text-xs text-zinc-500">
                  {new Date(f.modifiedTime).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
