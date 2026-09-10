import {
  AlertTriangle,
  CheckCircle2,
  FolderSync,
  Play,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";
import { type SyncStatusResult, api } from "../lib/api";

export default function Sync() {
  const [status, setStatus] = useState<SyncStatusResult | null>(null);
  const [localDir, setLocalDir] = useState("");
  const [folderId, setFolderId] = useState("");
  const [intervalSeconds, setIntervalSeconds] = useState(300);
  const [exportFormat, setExportFormat] = useState("docx");
  const [busy, setBusy] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const loadStatus = () =>
    api.syncStatus().then((res) => {
      setStatus(res);
      if (res.success && res.data) {
        setLocalDir(res.data.config.local_dir ?? "");
        setFolderId(res.data.config.folder_id ?? "");
        setIntervalSeconds(res.data.config.interval_seconds);
        setExportFormat(res.data.config.export_format);
      }
    });

  // biome-ignore lint/correctness/useExhaustiveDependencies: run once on mount only.
  useEffect(() => {
    loadStatus();
  }, []);

  const configured = !!status?.data?.config.local_dir;
  const enabled = !!status?.data?.config.enabled;

  const handleConfigure = async () => {
    if (!localDir.trim()) return;
    setBusy(true);
    setActionMessage(null);
    const res = await api.syncConfigure({
      local_dir: localDir.trim(),
      folder_id: folderId.trim() || null,
      interval_seconds: intervalSeconds,
      export_format: exportFormat,
    });
    setActionMessage(
      res.success ? "Sync configured." : `Configure failed: ${res.error}`,
    );
    setBusy(false);
    loadStatus();
  };

  const handleToggle = async () => {
    setBusy(true);
    setActionMessage(null);
    const res = enabled ? await api.syncDisable() : await api.syncEnable();
    setActionMessage(
      res.success
        ? enabled
          ? "Background sync disabled."
          : "Background sync enabled."
        : `Failed: ${res.error}`,
    );
    setBusy(false);
    loadStatus();
  };

  const handleRunOnce = async () => {
    setBusy(true);
    setActionMessage(null);
    const res = await api.syncRunOnce();
    setActionMessage(
      res.success
        ? (res.message ?? "Sync pass complete.")
        : `Run failed: ${res.error}`,
    );
    setBusy(false);
    loadStatus();
  };

  const lastRun = status?.data?.last_run ?? null;
  const lastError = status?.data?.last_error ?? null;

  return (
    <div className="max-w-2xl space-y-6" data-testid="sync-page">
      <section className="rounded-xl border border-zinc-800 bg-panel p-6">
        <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-zinc-100">
          <FolderSync size={18} />
          Local Folder Mirror
        </h2>
        <p className="mb-4 text-sm text-zinc-500">
          Two-way polling sync between a local folder and a Drive folder — like
          OneDrive, but checked periodically rather than instantly. See the
          "Notes" in the tool docs for conflict handling.
        </p>

        <div className="space-y-3 text-sm">
          <div>
            <label
              htmlFor="sync-local-dir"
              className="mb-1 block text-zinc-400"
            >
              Local folder
            </label>
            <input
              id="sync-local-dir"
              data-testid="sync-local-dir"
              value={localDir}
              onChange={(e) => setLocalDir(e.target.value)}
              placeholder="C:\Users\you\GoogleDocsSync"
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 p-2 text-zinc-100 placeholder-zinc-500 focus:border-amber-500 focus:outline-none"
            />
          </div>
          <div>
            <label
              htmlFor="sync-folder-id"
              className="mb-1 block text-zinc-400"
            >
              Drive folder ID (optional — Drive root if blank)
            </label>
            <input
              id="sync-folder-id"
              data-testid="sync-folder-id"
              value={folderId}
              onChange={(e) => setFolderId(e.target.value)}
              placeholder="1AbCdEfGhIjKlMnOpQr..."
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 p-2 text-zinc-100 placeholder-zinc-500 focus:border-amber-500 focus:outline-none"
            />
          </div>
          <div className="flex gap-3">
            <div className="flex-1">
              <label
                htmlFor="sync-interval"
                className="mb-1 block text-zinc-400"
              >
                Poll interval (seconds, min 60)
              </label>
              <input
                id="sync-interval"
                type="number"
                min={60}
                data-testid="sync-interval"
                value={intervalSeconds}
                onChange={(e) => setIntervalSeconds(Number(e.target.value))}
                className="w-full rounded-lg border border-zinc-700 bg-zinc-800 p-2 text-zinc-100 focus:border-amber-500 focus:outline-none"
              />
            </div>
            <div className="flex-1">
              <label htmlFor="sync-format" className="mb-1 block text-zinc-400">
                Local file format
              </label>
              <select
                id="sync-format"
                data-testid="sync-export-format"
                value={exportFormat}
                onChange={(e) => setExportFormat(e.target.value)}
                className="w-full rounded-lg border border-zinc-700 bg-zinc-800 p-2 text-zinc-100"
              >
                {["docx", "odt", "txt", "html"].map((fmt) => (
                  <option key={fmt} value={fmt}>
                    {fmt}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex flex-wrap gap-3 pt-2">
            <button
              type="button"
              data-testid="sync-configure"
              disabled={busy || !localDir.trim()}
              onClick={handleConfigure}
              className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-zinc-950 hover:bg-amber-400 disabled:opacity-40"
            >
              Save configuration
            </button>
            <button
              type="button"
              data-testid="sync-toggle"
              disabled={busy || !configured}
              onClick={handleToggle}
              className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-800 disabled:opacity-40"
            >
              {enabled ? "Disable background sync" : "Enable background sync"}
            </button>
            <button
              type="button"
              data-testid="sync-run-once"
              disabled={busy || !configured}
              onClick={handleRunOnce}
              className="flex items-center gap-2 rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-800 disabled:opacity-40"
            >
              <Play size={14} />
              Run once now
            </button>
          </div>

          {actionMessage && (
            <div data-testid="sync-action-message" className="text-zinc-400">
              {actionMessage}
            </div>
          )}
        </div>
      </section>

      <section
        className="rounded-xl border border-zinc-800 bg-panel p-6"
        data-testid="sync-status-panel"
      >
        <h2 className="mb-4 text-lg font-semibold text-zinc-100">Status</h2>
        <div className="space-y-3 text-sm">
          <div className="flex items-center gap-2">
            {configured ? (
              <CheckCircle2 size={16} className="text-emerald-500" />
            ) : (
              <XCircle size={16} className="text-red-500" />
            )}
            {configured ? "Configured" : "Not configured yet"}
          </div>
          <div className="flex items-center gap-2">
            {enabled ? (
              <CheckCircle2 size={16} className="text-emerald-500" />
            ) : (
              <XCircle size={16} className="text-zinc-500" />
            )}
            {enabled ? "Background polling active" : "Background polling off"}
          </div>
          <div className="text-zinc-500">
            {status?.data?.tracked_count ?? 0} doc(s) tracked.
          </div>

          {lastError && (
            <div className="flex items-start gap-2 rounded-lg border border-red-900 bg-red-950/30 p-3 text-red-300">
              <AlertTriangle size={16} className="mt-0.5 shrink-0" />
              <span data-testid="sync-last-error">{lastError}</span>
            </div>
          )}

          {lastRun && (
            <div
              className="space-y-1 rounded-lg border border-zinc-800 p-3"
              data-testid="sync-last-run"
            >
              <div className="text-zinc-500">Last pass: {lastRun.ran_at}</div>
              <div>
                Pulled:{" "}
                {lastRun.pulled.length ? lastRun.pulled.join(", ") : "none"}
              </div>
              <div>
                Pushed:{" "}
                {lastRun.pushed.length ? lastRun.pushed.join(", ") : "none"}
              </div>
              {lastRun.conflicts.length > 0 && (
                <div className="text-amber-400">
                  Conflicts: {lastRun.conflicts.join(", ")}
                </div>
              )}
              {lastRun.remote_deleted.length > 0 && (
                <div className="text-zinc-500">
                  Moved to _remote_deleted: {lastRun.remote_deleted.join(", ")}
                </div>
              )}
              {lastRun.errors.length > 0 && (
                <div className="text-red-400">
                  Errors:{" "}
                  {lastRun.errors
                    .map((e) => `${e.name}: ${e.error}`)
                    .join("; ")}
                </div>
              )}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
