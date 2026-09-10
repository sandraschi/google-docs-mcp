import { CheckCircle2, KeyRound, LogOut, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { API_BASE } from "../lib/api";
import { useLlmStore } from "../store/llm";

type AuthStatus = {
  configured: boolean;
  authenticated: boolean;
  scopes: string[];
  token_path: string;
  expiry: string | null;
};

export default function Settings() {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [starting, setStarting] = useState(false);
  const llm = useLlmStore();

  const loadStatus = () =>
    fetch(`${API_BASE}/api/auth/status`)
      .then((r) => r.json())
      .then(setStatus);

  // biome-ignore lint/correctness/useExhaustiveDependencies: run once on mount only; llm is a fresh store-selector object every render, including it would re-probe in a loop.
  useEffect(() => {
    loadStatus();
    llm.probe();
  }, []);

  const startOAuth = async () => {
    setStarting(true);
    try {
      await fetch(`${API_BASE}/api/auth/start`, { method: "POST" });
    } finally {
      setStarting(false);
      loadStatus();
    }
  };

  const revoke = async () => {
    await fetch(`${API_BASE}/api/auth/revoke`, { method: "POST" });
    loadStatus();
  };

  return (
    <div className="max-w-2xl space-y-6" data-testid="settings-page">
      <section className="rounded-xl border border-zinc-800 bg-panel p-6">
        <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-zinc-100">
          <KeyRound size={18} />
          Google Account Connection
        </h2>
        {status && (
          <div className="space-y-3 text-sm">
            <div className="flex items-center gap-2">
              {status.configured ? (
                <CheckCircle2 size={16} className="text-emerald-500" />
              ) : (
                <XCircle size={16} className="text-red-500" />
              )}
              OAuth client {status.configured ? "configured" : "not configured"}
            </div>
            <div className="flex items-center gap-2">
              {status.authenticated ? (
                <CheckCircle2 size={16} className="text-emerald-500" />
              ) : (
                <XCircle size={16} className="text-red-500" />
              )}
              {status.authenticated ? "Authenticated" : "Not authenticated"}
            </div>
            {status.expiry && (
              <div className="text-zinc-500">
                Token expires: {status.expiry}
              </div>
            )}
            <div className="text-zinc-500">Token file: {status.token_path}</div>

            {!status.configured && (
              <p className="text-amber-400">
                Set GOOGLE_DOCS_MCP_CLIENT_ID / GOOGLE_DOCS_MCP_CLIENT_SECRET —
                see docs/ONBOARDING.md.
              </p>
            )}

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                data-testid="settings-start-oauth"
                disabled={!status.configured || starting}
                onClick={startOAuth}
                className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-zinc-950 hover:bg-amber-400 disabled:opacity-40"
              >
                {starting ? "Opening browser…" : "Connect Google Account"}
              </button>
              <button
                type="button"
                data-testid="settings-revoke"
                onClick={revoke}
                className="flex items-center gap-2 rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-800"
              >
                <LogOut size={14} />
                Revoke
              </button>
            </div>
          </div>
        )}
      </section>

      <section className="rounded-xl border border-zinc-800 bg-panel p-6">
        <h2 className="mb-4 text-lg font-semibold text-zinc-100">
          Local Intelligence (Chat)
        </h2>
        <div className="space-y-3 text-sm">
          {llm.providers.map((p) => (
            <div key={p.name} className="flex items-center justify-between">
              <span>
                {p.name} (:{p.port})
              </span>
              <span
                className={
                  llm.status[p.name] === "detected"
                    ? "text-emerald-500"
                    : "text-zinc-500"
                }
              >
                {llm.status[p.name] ?? "probing…"}
              </span>
            </div>
          ))}

          <div className="pt-2">
            <label htmlFor="llm-provider" className="mb-1 block text-zinc-400">
              Provider
            </label>
            <select
              id="llm-provider"
              data-testid="llm-provider-select"
              value={llm.selectedProvider}
              onChange={(e) => llm.selectProvider(e.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 p-2 text-zinc-100"
            >
              <option value="">No local LLM detected</option>
              {llm.providers
                .filter((p) => p.detected)
                .map((p) => (
                  <option key={p.name} value={p.name}>
                    {p.name}
                  </option>
                ))}
            </select>
          </div>

          <div>
            <label htmlFor="llm-model" className="mb-1 block text-zinc-400">
              Model
            </label>
            <select
              id="llm-model"
              data-testid="llm-model-select"
              value={llm.selectedModel}
              onChange={(e) => llm.selectModel(e.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 p-2 text-zinc-100"
              disabled={!llm.models.length}
            >
              {llm.models.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>
    </div>
  );
}
