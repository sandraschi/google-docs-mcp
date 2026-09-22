import {
  CheckCircle2,
  ExternalLink,
  KeyRound,
  Loader2,
  LogOut,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";
import { API_BASE } from "../lib/api";
import { useLlmStore } from "../store/llm";

type AuthStatus = {
  configured: boolean;
  authenticated: boolean;
  scopes: string[];
  token_path: string;
  expiry: string | null;
  client_source?: string;
};

export default function Settings() {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [starting, setStarting] = useState(false);
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
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

  const saveClient = async () => {
    setSaving(true);
    setSaveMessage(null);
    try {
      const res = await fetch(`${API_BASE}/api/onboarding/client`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_id: clientId.trim(),
          client_secret: clientSecret.trim(),
        }),
      });
      const body = await res.json();
      if (body.success) {
        setSaveMessage("Saved — you can connect your Google account now.");
        setClientId("");
        setClientSecret("");
        loadStatus();
      } else {
        setSaveMessage(`Error: ${body.error}`);
      }
    } catch (err) {
      setSaveMessage(`Error: ${String(err)}`);
    } finally {
      setSaving(false);
    }
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

            {status.configured ? (
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  data-testid="settings-start-oauth"
                  disabled={starting}
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
            ) : (
              <div className="space-y-3 border-t border-zinc-800 pt-4">
                <p className="text-zinc-400">
                  No Google Cloud OAuth client yet. Paste the Client ID and
                  Secret from your{" "}
                  <a
                    href="https://console.cloud.google.com/apis/credentials"
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-amber-400 hover:underline"
                  >
                    Google Cloud Console <ExternalLink size={12} />
                  </a>{" "}
                  — saved locally to <code>data/oauth_client.json</code>, never
                  sent anywhere but Google. First time doing this?{" "}
                  <a
                    href="#/onboarding"
                    className="text-amber-400 hover:underline"
                  >
                    Full walkthrough →
                  </a>
                </p>
                <input
                  data-testid="settings-client-id"
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                  placeholder="xxxxxxxx.apps.googleusercontent.com"
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-800 p-2 text-sm text-zinc-100 placeholder-zinc-500 focus:border-amber-500 focus:outline-none"
                />
                <input
                  data-testid="settings-client-secret"
                  type="password"
                  value={clientSecret}
                  onChange={(e) => setClientSecret(e.target.value)}
                  placeholder="Client secret"
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-800 p-2 text-sm text-zinc-100 placeholder-zinc-500 focus:border-amber-500 focus:outline-none"
                />
                <button
                  type="button"
                  data-testid="settings-save-client"
                  disabled={saving || !clientId.trim() || !clientSecret.trim()}
                  onClick={saveClient}
                  className="flex items-center gap-2 rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-zinc-950 hover:bg-amber-400 disabled:opacity-50"
                >
                  {saving && <Loader2 size={16} className="animate-spin" />}
                  Save
                </button>
                {saveMessage && (
                  <p
                    data-testid="settings-save-message"
                    className="text-sm text-zinc-400"
                  >
                    {saveMessage}
                  </p>
                )}
              </div>
            )}
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
                  {llm.loadedModels.includes(m) ? " (loaded)" : ""}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>
    </div>
  );
}
