import {
  AlertCircle,
  Download,
  ExternalLink,
  FileText,
  Loader2,
  Search,
  Upload,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { API_BASE, type DriveFile, api } from "../lib/api";

const EXPORT_FORMATS = ["pdf", "docx", "odt", "txt", "html"] as const;

function triggerDownload(url: string) {
  const a = document.createElement("a");
  a.href = url;
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

export default function Documents() {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<DriveFile[]>([]);
  const [errorType, setErrorType] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [importMessage, setImportMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const load = (q?: string) => {
    setLoading(true);
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

  // biome-ignore lint/correctness/useExhaustiveDependencies: `load` is a fresh function each render; only run the initial (unfiltered) load once on mount.
  useEffect(() => {
    load();
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
        load(query || undefined);
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

  return (
    <div className="space-y-4" data-testid="documents-page">
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 text-zinc-500" size={16} />
          <input
            data-testid="documents-search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && load(query || undefined)}
            placeholder="Search your Google Docs…"
            className="w-full rounded-lg border border-zinc-700 bg-zinc-800 py-2 pl-9 pr-3 text-sm text-zinc-100 placeholder-zinc-500 focus:border-amber-500 focus:outline-none"
          />
        </div>
        <button
          type="button"
          data-testid="documents-search-button"
          onClick={() => load(query || undefined)}
          className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-zinc-950 hover:bg-amber-400"
        >
          Search
        </button>
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
      </div>

      {importMessage && (
        <div
          data-testid="documents-import-status"
          className="rounded-lg border border-zinc-700 bg-panel p-3 text-sm text-zinc-300"
        >
          {importMessage}
        </div>
      )}

      {errorType && (
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
          {!["not_configured", "not_authenticated"].includes(errorType) &&
            `Error: ${errorType}`}
        </div>
      )}

      {loading && <div className="text-zinc-500">Loading…</div>}

      {!loading && !errorType && items.length === 0 && (
        <div className="rounded-lg border border-zinc-800 bg-panel p-8 text-center text-zinc-500">
          No documents found.
        </div>
      )}

      <div className="grid gap-2" data-testid="documents-list">
        {items.map((f) => (
          <div
            key={f.id}
            className="flex items-center justify-between rounded-lg border border-zinc-800 bg-panel p-4 hover:border-zinc-700"
          >
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
        ))}
      </div>
    </div>
  );
}
