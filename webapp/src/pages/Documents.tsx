import {
  AlertCircle,
  ArrowUpDown,
  ChevronRight,
  Download,
  ExternalLink,
  FileText,
  Folder,
  Loader2,
  Search,
  Upload,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { API_BASE, type Breadcrumb, type DriveFile, api } from "../lib/api";

const EXPORT_FORMATS = ["pdf", "docx", "odt", "txt", "html"] as const;
const CONVERT_FORMATS = [
  "doc",
  "fodt",
  "rtf",
  "odt",
  "txt",
  "pdf",
  "html",
] as const;

function triggerDownload(url: string) {
  const a = document.createElement("a");
  a.href = url;
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

function ErrorBanner({ errorType }: { errorType: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-amber-800 bg-amber-950/30 p-4 text-amber-300">
      <AlertCircle size={18} />
      {errorType === "not_configured" && (
        <span>
          Not configured —{" "}
          <a href="#/onboarding" className="underline hover:text-amber-200">
            complete onboarding
          </a>{" "}
          first.
        </span>
      )}
      {errorType === "not_authenticated" && (
        <span>
          Not authenticated —{" "}
          <a href="#/onboarding" className="underline hover:text-amber-200">
            connect your account
          </a>{" "}
          first.
        </span>
      )}
      {errorType === "dependency_unavailable" && (
        <span>libreoffice-mcp is not reachable — start it and retry.</span>
      )}
      {![
        "not_configured",
        "not_authenticated",
        "dependency_unavailable",
      ].includes(errorType) && `Error: ${errorType}`}
    </div>
  );
}

type RowAction = { fileId: string; kind: "restore" | "convert" } | null;

export default function Documents() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<"browse" | "search">("browse");
  const [items, setItems] = useState<DriveFile[]>([]);
  const [errorType, setErrorType] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [importMessage, setImportMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [folderId, setFolderId] = useState<string | null>(null);
  const [folders, setFolders] = useState<DriveFile[]>([]);
  const [breadcrumbs, setBreadcrumbs] = useState<Breadcrumb[]>([]);

  const [backupOpen, setBackupOpen] = useState(false);
  const [backupOutputDir, setBackupOutputDir] = useState("");
  const [backupFormat, setBackupFormat] = useState<string>("pdf");
  const [backupRecursive, setBackupRecursive] = useState(false);
  const [backupBusy, setBackupBusy] = useState(false);
  const [backupMessage, setBackupMessage] = useState<string | null>(null);

  const [rowAction, setRowAction] = useState<RowAction>(null);
  const [restorePath, setRestorePath] = useState("");
  const [convertFormat, setConvertFormat] = useState<string>("pdf");
  const [convertPath, setConvertPath] = useState("");
  const [rowBusy, setRowBusy] = useState(false);
  const [rowMessage, setRowMessage] = useState<string | null>(null);

  const loadBrowse = (fid?: string | null) => {
    setLoading(true);
    setMode("browse");
    api
      .browse(fid ?? undefined)
      .then((res) => {
        if (res.success && res.data) {
          setFolders(res.data.folders);
          setItems(res.data.files);
          setBreadcrumbs(res.data.breadcrumbs);
          setFolderId(fid ?? null);
          setErrorType(null);
        } else {
          setFolders([]);
          setItems([]);
          setBreadcrumbs([]);
          setErrorType(res.error_type ?? "api_error");
        }
      })
      .finally(() => setLoading(false));
  };

  const loadSearch = (q?: string) => {
    setLoading(true);
    setMode("search");
    api
      .documents(q)
      .then((res) => {
        if (res.success && res.data) {
          setItems(res.data.items);
          setErrorType(null);
        } else {
          setItems([]);
          setErrorType(res.error_type ?? "api_error");
        }
      })
      .finally(() => setLoading(false));
  };

  // biome-ignore lint/correctness/useExhaustiveDependencies: only run the initial (root folder) load once on mount.
  useEffect(() => {
    loadBrowse(null);
  }, []);

  const handleImport = async (file: File) => {
    setImporting(true);
    setImportMessage(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${API_BASE}/api/documents/import`, {
        method: "POST",
        body: form,
      });
      const body = await res.json();
      if (body.success) {
        setImportMessage(
          `Imported "${file.name}" as "${body.data.file.name}".`,
        );
        mode === "search"
          ? loadSearch(query || undefined)
          : loadBrowse(folderId);
      } else {
        setImportMessage(`Import failed: ${body.error}`);
      }
    } catch (err) {
      setImportMessage(`Import failed: ${String(err)}`);
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const runBackup = async () => {
    if (!backupOutputDir.trim()) return;
    setBackupBusy(true);
    setBackupMessage(null);
    const res = await api.backupFolder({
      folder_id: folderId,
      output_dir: backupOutputDir.trim(),
      export_format: backupFormat,
      recursive: backupRecursive,
    });
    if (res.success && res.data) {
      const errCount = res.data.errors.length;
      setBackupMessage(
        `Backed up ${res.data.files.length} doc(s) to ${res.data.output_dir}${errCount ? ` (${errCount} error(s)).` : "."}`,
      );
    } else {
      setBackupMessage(`Backup failed: ${res.error ?? res.error_type}`);
    }
    setBackupBusy(false);
  };

  const openRowAction = (fileId: string, kind: "restore" | "convert") => {
    setRowAction((cur) =>
      cur?.fileId === fileId && cur.kind === kind ? null : { fileId, kind },
    );
    setRowMessage(null);
    setRestorePath("");
    setConvertPath("");
  };

  const runRestore = async (fileId: string) => {
    if (!restorePath.trim()) return;
    setRowBusy(true);
    setRowMessage(null);
    const res = await api.restoreFile(fileId, restorePath.trim());
    setRowMessage(
      res.success
        ? (res.message ?? "Restored.")
        : `Restore failed: ${res.error ?? res.error_type}`,
    );
    setRowBusy(false);
  };

  const runConvert = async (fileId: string) => {
    if (!convertPath.trim()) return;
    setRowBusy(true);
    setRowMessage(null);
    const res = await api.convertAdvanced(
      fileId,
      convertFormat,
      convertPath.trim(),
    );
    setRowMessage(
      res.success
        ? (res.message ?? "Converted.")
        : `Convert failed: ${res.error ?? res.error_type}`,
    );
    setRowBusy(false);
  };

  return (
    <div className="space-y-4" data-testid="documents-page">
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 text-zinc-500" size={16} />
          <input
            data-testid="documents-search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) =>
              e.key === "Enter" && loadSearch(query || undefined)
            }
            placeholder="Search your Google Docs…"
            className="w-full rounded-lg border border-zinc-700 bg-zinc-800 py-2 pl-9 pr-3 text-sm text-zinc-100 placeholder-zinc-500 focus:border-amber-500 focus:outline-none"
          />
        </div>
        <button
          type="button"
          data-testid="documents-search-button"
          onClick={() => loadSearch(query || undefined)}
          className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-zinc-950 hover:bg-amber-400"
        >
          Search
        </button>
        {mode === "search" && (
          <button
            type="button"
            data-testid="documents-back-to-browse"
            onClick={() => {
              setQuery("");
              loadBrowse(folderId);
            }}
            className="rounded-lg border border-zinc-700 px-3 py-2 text-sm text-zinc-300 hover:bg-zinc-800"
          >
            Browse
          </button>
        )}
        <input
          ref={fileInputRef}
          type="file"
          accept=".docx,.odt,.txt,.md,.html,.htm,.rtf"
          className="hidden"
          data-testid="documents-import-input"
          onChange={(e) =>
            e.target.files?.[0] && handleImport(e.target.files[0])
          }
        />
        <button
          type="button"
          data-testid="documents-import-button"
          disabled={importing}
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center gap-2 rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-800 disabled:opacity-50"
        >
          {importing ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Upload size={16} />
          )}
          Import
        </button>
        {mode === "browse" && (
          <button
            type="button"
            data-testid="documents-backup-toggle"
            onClick={() => {
              setBackupOpen((o) => !o);
              setBackupMessage(null);
            }}
            className="flex items-center gap-2 rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-800"
          >
            <ArrowUpDown size={16} />
            Backup folder
          </button>
        )}
      </div>

      {mode === "browse" && (
        <div
          className="flex items-center gap-1 text-sm text-zinc-400"
          data-testid="documents-breadcrumbs"
        >
          <button
            type="button"
            onClick={() => loadBrowse(null)}
            className="rounded px-2 py-1 hover:bg-zinc-800 hover:text-zinc-100"
          >
            My Drive
          </button>
          {breadcrumbs.map((b) => (
            <span key={b.id} className="flex items-center gap-1">
              <ChevronRight size={14} />
              <button
                type="button"
                onClick={() => loadBrowse(b.id)}
                className="rounded px-2 py-1 hover:bg-zinc-800 hover:text-zinc-100"
              >
                {b.name}
              </button>
            </span>
          ))}
        </div>
      )}

      {backupOpen && mode === "browse" && (
        <div
          data-testid="documents-backup-panel"
          className="space-y-3 rounded-lg border border-zinc-700 bg-panel p-4"
        >
          <div className="text-sm text-zinc-300">
            Backup every doc in{" "}
            {breadcrumbs.length
              ? breadcrumbs[breadcrumbs.length - 1].name
              : "My Drive"}{" "}
            to a local folder.
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <input
              data-testid="documents-backup-output-dir"
              value={backupOutputDir}
              onChange={(e) => setBackupOutputDir(e.target.value)}
              placeholder="C:\Users\you\GoogleDocsBackup"
              className="min-w-[280px] flex-1 rounded border border-zinc-700 bg-zinc-800 p-2 text-sm text-zinc-100 placeholder-zinc-500 focus:border-amber-500 focus:outline-none"
            />
            <select
              value={backupFormat}
              onChange={(e) => setBackupFormat(e.target.value)}
              className="rounded border border-zinc-700 bg-zinc-800 p-2 text-sm text-zinc-300"
            >
              {EXPORT_FORMATS.map((fmt) => (
                <option key={fmt} value={fmt}>
                  {fmt}
                </option>
              ))}
            </select>
            <label className="flex items-center gap-2 text-sm text-zinc-400">
              <input
                type="checkbox"
                checked={backupRecursive}
                onChange={(e) => setBackupRecursive(e.target.checked)}
              />
              Include subfolders
            </label>
            <button
              type="button"
              data-testid="documents-backup-run"
              disabled={backupBusy || !backupOutputDir.trim()}
              onClick={runBackup}
              className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-zinc-950 hover:bg-amber-400 disabled:opacity-50"
            >
              {backupBusy ? "Backing up…" : "Run backup"}
            </button>
          </div>
          {backupMessage && (
            <div
              data-testid="documents-backup-message"
              className="text-sm text-zinc-300"
            >
              {backupMessage}
            </div>
          )}
        </div>
      )}

      {importMessage && (
        <div
          data-testid="documents-import-status"
          className="rounded-lg border border-zinc-700 bg-panel p-3 text-sm text-zinc-300"
        >
          {importMessage}
        </div>
      )}

      {errorType && <ErrorBanner errorType={errorType} />}

      {loading && <div className="text-zinc-500">Loading…</div>}

      {!loading && !errorType && mode === "browse" && folders.length > 0 && (
        <div className="grid gap-2" data-testid="documents-folders">
          {folders.map((f) => (
            <button
              type="button"
              key={f.id}
              onClick={() => loadBrowse(f.id)}
              className="flex items-center gap-3 rounded-lg border border-zinc-800 bg-panel p-3 text-left hover:border-zinc-700"
            >
              <Folder size={18} className="text-amber-400" />
              <span className="text-zinc-100">{f.name}</span>
            </button>
          ))}
        </div>
      )}

      {!loading && !errorType && items.length === 0 && folders.length === 0 && (
        <div className="rounded-lg border border-zinc-800 bg-panel p-8 text-center text-zinc-500">
          No documents found.
        </div>
      )}

      <div className="grid gap-2" data-testid="documents-list">
        {items.map((f) => (
          <div
            key={f.id}
            className="rounded-lg border border-zinc-800 bg-panel p-4 hover:border-zinc-700"
          >
            <div className="flex items-center justify-between">
              <a
                href={f.webViewLink}
                target="_blank"
                rel="noreferrer"
                className="flex flex-1 items-center gap-3"
              >
                <FileText size={18} className="text-amber-400" />
                <div>
                  <div className="text-zinc-100">{f.name}</div>
                  <div className="text-xs text-zinc-500">{f.modifiedTime}</div>
                </div>
              </a>
              <div className="flex items-center gap-2">
                <select
                  aria-label={`Export format for ${f.name}`}
                  data-testid={`documents-export-format-${f.id}`}
                  defaultValue="pdf"
                  id={`export-format-${f.id}`}
                  className="rounded border border-zinc-700 bg-zinc-800 p-1.5 text-xs text-zinc-300"
                >
                  {EXPORT_FORMATS.map((fmt) => (
                    <option key={fmt} value={fmt}>
                      {fmt}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  data-testid={`documents-export-${f.id}`}
                  title="Export"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    const select = document.getElementById(
                      `export-format-${f.id}`,
                    ) as HTMLSelectElement;
                    triggerDownload(
                      `${API_BASE}/api/documents/${f.id}/export?format=${select.value}`,
                    );
                  }}
                  className="rounded p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-amber-400"
                >
                  <Download size={16} />
                </button>
                <button
                  type="button"
                  data-testid={`documents-restore-toggle-${f.id}`}
                  title="Restore from local file"
                  onClick={() => openRowAction(f.id, "restore")}
                  className="rounded px-2 py-1.5 text-xs text-zinc-400 hover:bg-zinc-800 hover:text-amber-400"
                >
                  Restore…
                </button>
                <button
                  type="button"
                  data-testid={`documents-convert-toggle-${f.id}`}
                  title="Convert via LibreOffice"
                  onClick={() => openRowAction(f.id, "convert")}
                  className="rounded px-2 py-1.5 text-xs text-zinc-400 hover:bg-zinc-800 hover:text-amber-400"
                >
                  Convert…
                </button>
                <a
                  href={f.webViewLink}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded p-1.5 text-zinc-500 hover:bg-zinc-800"
                >
                  <ExternalLink size={16} />
                </a>
              </div>
            </div>

            {rowAction?.fileId === f.id && rowAction.kind === "restore" && (
              <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-zinc-800 pt-3">
                <span className="text-xs text-zinc-500">
                  Overwrite this Google Doc's content from a local file:
                </span>
                <input
                  data-testid={`documents-restore-path-${f.id}`}
                  value={restorePath}
                  onChange={(e) => setRestorePath(e.target.value)}
                  placeholder="C:\path\to\file.docx"
                  className="min-w-[240px] flex-1 rounded border border-zinc-700 bg-zinc-800 p-2 text-sm text-zinc-100 placeholder-zinc-500 focus:border-amber-500 focus:outline-none"
                />
                <button
                  type="button"
                  data-testid={`documents-restore-run-${f.id}`}
                  disabled={rowBusy || !restorePath.trim()}
                  onClick={() => runRestore(f.id)}
                  className="rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-medium text-zinc-950 hover:bg-amber-400 disabled:opacity-50"
                >
                  {rowBusy ? "Restoring…" : "Restore"}
                </button>
              </div>
            )}

            {rowAction?.fileId === f.id && rowAction.kind === "convert" && (
              <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-zinc-800 pt-3">
                <span className="text-xs text-zinc-500">
                  Convert via libreoffice-mcp to:
                </span>
                <select
                  value={convertFormat}
                  onChange={(e) => setConvertFormat(e.target.value)}
                  className="rounded border border-zinc-700 bg-zinc-800 p-1.5 text-xs text-zinc-300"
                >
                  {CONVERT_FORMATS.map((fmt) => (
                    <option key={fmt} value={fmt}>
                      {fmt}
                    </option>
                  ))}
                </select>
                <input
                  data-testid={`documents-convert-path-${f.id}`}
                  value={convertPath}
                  onChange={(e) => setConvertPath(e.target.value)}
                  placeholder="C:\path\to\output"
                  className="min-w-[240px] flex-1 rounded border border-zinc-700 bg-zinc-800 p-2 text-sm text-zinc-100 placeholder-zinc-500 focus:border-amber-500 focus:outline-none"
                />
                <button
                  type="button"
                  data-testid={`documents-convert-run-${f.id}`}
                  disabled={rowBusy || !convertPath.trim()}
                  onClick={() => runConvert(f.id)}
                  className="rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-medium text-zinc-950 hover:bg-amber-400 disabled:opacity-50"
                >
                  {rowBusy ? "Converting…" : "Convert"}
                </button>
              </div>
            )}

            {rowAction?.fileId === f.id && rowMessage && (
              <div
                data-testid={`documents-row-message-${f.id}`}
                className="mt-2 text-xs text-zinc-400"
              >
                {rowMessage}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
