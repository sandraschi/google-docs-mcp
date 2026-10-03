import {
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Circle,
  ExternalLink,
  KeyRound,
  Loader2,
} from "lucide-react";
import { useEffect, useState } from "react";
import { API_BASE } from "../lib/api";

type AuthStatus = {
  configured: boolean;
  authenticated: boolean;
  client_source: string;
  expiry: string | null;
};

const STEPS = [
  "What this is",
  "Cost & accounts",
  "Cloud Console setup",
  "Connect",
  "Done",
] as const;

function StepDots({ current }: { current: number }) {
  return (
    <div className="flex items-center gap-2" data-testid="onboarding-steps">
      {STEPS.map((s, i) => (
        <div key={s} className="flex items-center gap-2">
          {i < current ? (
            <CheckCircle2 size={18} className="text-emerald-500" />
          ) : i === current ? (
            <div className="h-[18px] w-[18px] rounded-full border-2 border-amber-500" />
          ) : (
            <Circle size={18} className="text-zinc-500" />
          )}
          <span
            className={
              i === current ? "text-sm text-zinc-100" : "text-sm text-zinc-400"
            }
          >
            {s}
          </span>
          {i < STEPS.length - 1 && <div className="h-px w-6 bg-zinc-800" />}
        </div>
      ))}
    </div>
  );
}

export default function Onboarding() {
  const [step, setStep] = useState(0);
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);

  const loadStatus = () =>
    fetch(`${API_BASE}/api/auth/status`)
      .then((r) => r.json())
      .then(setStatus);

  // biome-ignore lint/correctness/useExhaustiveDependencies: run once on mount only.
  useEffect(() => {
    loadStatus();
  }, []);

  useEffect(() => {
    if (status?.authenticated && step < 4) setStep(4);
  }, [status, step]);

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
        setSaveMessage("Saved. You can connect your Google account now.");
        setStatus(body.data);
        setStep(3);
      } else {
        setSaveMessage(`Error: ${body.error}`);
      }
    } catch (err) {
      setSaveMessage(`Error: ${String(err)}`);
    } finally {
      setSaving(false);
    }
  };

  const connect = async () => {
    setConnecting(true);
    try {
      await fetch(`${API_BASE}/api/auth/start`, { method: "POST" });
    } finally {
      setConnecting(false);
      loadStatus();
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6" data-testid="onboarding-page">
      <h1 className="text-2xl font-bold text-zinc-100">Onboarding</h1>
      <div className="overflow-x-auto pb-2">
        <StepDots current={step} />
      </div>

      <div className="rounded-xl border border-zinc-800 bg-panel p-6">
        {step === 0 && (
          <div className="space-y-3" data-testid="onboarding-step-0">
            <h2 className="text-lg font-semibold text-zinc-100">
              What this is for
            </h2>
            <p className="text-zinc-400">
              This lets Claude read and edit your Google Docs, and manage those
              files in Google Drive — directly, using your own Google account.
              Every write happens because you asked for it; there's no
              autonomous scheduling or background posting.
            </p>
            <p className="text-zinc-400">
              Nothing about your document content or account passes through any
              server run by the maker of this app — every call goes straight
              from this machine to Google.
            </p>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-3" data-testid="onboarding-step-1">
            <h2 className="text-lg font-semibold text-zinc-100">
              Cost and accounts
            </h2>
            <table className="w-full text-sm">
              <tbody className="divide-y divide-zinc-800">
                <tr>
                  <td className="py-2 text-zinc-500">Account needed?</td>
                  <td className="py-2 text-zinc-200">
                    Yes — any Google account
                  </td>
                </tr>
                <tr>
                  <td className="py-2 text-zinc-500">Free tier?</td>
                  <td className="py-2 text-zinc-200">
                    Yes, generous for personal use
                  </td>
                </tr>
                <tr>
                  <td className="py-2 text-zinc-500">Credit card required?</td>
                  <td className="py-2 text-zinc-200">No</td>
                </tr>
                <tr>
                  <td className="py-2 text-zinc-500">Ongoing cost?</td>
                  <td className="py-2 text-zinc-200">
                    Free at personal-use volumes
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-3" data-testid="onboarding-step-2">
            <h2 className="text-lg font-semibold text-zinc-100">
              Google Cloud Console setup
            </h2>
            <ol className="list-decimal space-y-2 pl-5 text-sm text-zinc-400">
              <li>
                Open{" "}
                <a
                  href="https://console.cloud.google.com/"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-amber-400 hover:underline"
                >
                  Google Cloud Console <ExternalLink size={12} />
                </a>{" "}
                and create (or pick) a project.
              </li>
              <li>
                APIs &amp; Services → Library — enable{" "}
                <strong>Google Docs API</strong> and{" "}
                <strong>Google Drive API</strong>.
              </li>
              <li>
                Google Auth Platform → Branding — fill app name + support email
                (one-time registration; "Get Started" if prompted).
              </li>
              <li>
                Google Auth Platform → Audience — User type{" "}
                <strong>External</strong> (stay in Testing). Project owners
                already have access — only add <em>other</em> Gmails under{" "}
                <strong>Test users</strong>; adding yourself errors out and is
                safe to skip.
              </li>
              <li>
                Google Auth Platform → Clients → Create Client — Application
                type <strong>Desktop app</strong> (leave the AI-agent checkbox
                off for personal use).
              </li>
              <li>
                Copy the generated Client ID and Client Secret immediately — the
                secret is shown only once. Paste them on the Connect step next.
              </li>
            </ol>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-3" data-testid="onboarding-step-3">
            <h2 className="flex items-center gap-2 text-lg font-semibold text-zinc-100">
              <KeyRound size={18} />
              Connect
            </h2>
            {status?.configured ? (
              <div className="space-y-3">
                <p className="text-sm text-zinc-400">
                  Client is configured (
                  {status.client_source === "env"
                    ? "via environment"
                    : "via this wizard"}
                  ). Click below to sign in — your browser will open Google's
                  consent screen.
                </p>
                <button
                  type="button"
                  data-testid="onboarding-connect-button"
                  disabled={connecting}
                  onClick={connect}
                  className="flex items-center gap-2 rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-zinc-950 hover:bg-amber-400 disabled:opacity-50"
                >
                  {connecting && <Loader2 size={16} className="animate-spin" />}
                  Connect Google Account
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-sm text-zinc-400">
                  Paste the Client ID and Client Secret from step 3. These are
                  saved locally to <code>data/oauth_client.json</code> (never
                  committed, never sent anywhere but Google).
                </p>
                <input
                  data-testid="onboarding-client-id"
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                  placeholder="xxxxxxxx.apps.googleusercontent.com"
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-800 p-2 text-sm text-zinc-100"
                />
                <input
                  data-testid="onboarding-client-secret"
                  type="password"
                  value={clientSecret}
                  onChange={(e) => setClientSecret(e.target.value)}
                  placeholder="Client secret"
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-800 p-2 text-sm text-zinc-100"
                />
                <button
                  type="button"
                  data-testid="onboarding-save-client"
                  disabled={saving || !clientId || !clientSecret}
                  onClick={saveClient}
                  className="flex items-center gap-2 rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-zinc-950 hover:bg-amber-400 disabled:opacity-50"
                >
                  {saving && <Loader2 size={16} className="animate-spin" />}
                  Save
                </button>
                {saveMessage && (
                  <p className="text-sm text-zinc-400">{saveMessage}</p>
                )}
              </div>
            )}
          </div>
        )}

        {step === 4 && (
          <div className="space-y-3" data-testid="onboarding-step-4">
            <h2 className="flex items-center gap-2 text-lg font-semibold text-emerald-400">
              <CheckCircle2 size={20} />
              {status?.authenticated ? "You're connected" : "Almost there"}
            </h2>
            {status?.authenticated ? (
              <p className="text-sm text-zinc-400">
                Sanity check passed — try asking Claude: "Create a test Google
                Doc."
              </p>
            ) : (
              <p className="text-sm text-zinc-400">
                Client is saved but you haven't completed the browser sign-in
                yet — go back to Connect and click the button.
              </p>
            )}
          </div>
        )}
      </div>

      <div className="flex justify-between">
        <button
          type="button"
          data-testid="onboarding-back"
          disabled={step === 0}
          onClick={() => setStep((s) => Math.max(0, s - 1))}
          className="flex items-center gap-1 rounded-lg border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 hover:bg-zinc-800 disabled:opacity-30"
        >
          <ChevronLeft size={16} />
          Back
        </button>
        <button
          type="button"
          data-testid="onboarding-next"
          disabled={step === STEPS.length - 1}
          onClick={() => setStep((s) => Math.min(STEPS.length - 1, s + 1))}
          className="flex items-center gap-1 rounded-lg border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 hover:bg-zinc-800 disabled:opacity-30"
        >
          Next
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}
