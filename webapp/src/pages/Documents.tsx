import {
  AlertCircle,
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  ChevronRight,
  Download,
  ExternalLink,
  FileText,
  Folder,
  LayoutGrid,
  List,
  Loader2,
  Search,
  Star,
  Upload,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
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

const PAGE_LIMIT = 25;
const FAVORITES_KEY = "gdocs-favorites";

function loadFavorites(): Set<string> {
  try {
    const raw = localStorage.getItem(FAVORITES_KEY);
    if (!raw) return new Set();
    const arr = JSON.parse(raw) as string[];
    return new Set(arr);
  } catch {
    return new Set();
  }
}

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
type SortKey = "name" | "modifiedTime";

export default function Documents() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<"browse" | "search">("browse");
  const [items, setItems] = useState<DriveFile[]>([]);
  const [errorType, setErrorType] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  const [importMessage, setImportMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [folderId, setFolderId] = useState<string | null>(null);
  const [folders, setFolders] = useState<DriveFile[]>([]);
  const [breadcrumbs, setBreadcrumbs] = useState<Breadcrumb[]>([]);

  // Sort / filter / view / favorites state (all client-side over loaded items;
  // server still owns search query + cursor pagination).
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [filterText, setFilterText] = useState("");
  const [favoritesOnly, setFavoritesOnly] = useState(false);
  const [view, setView] = useState<"list" | "grid">("list");
  const [perPage, setPerPage] = useState(25);
  const [page, setPage] = useState(1);
  const [favorites, setFavorites] = useState<Set<string>>(loadFavorites);

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

  const toggleFavorite = (id: string) => {
    setFavorites((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      try {
        localStorage.setItem(FAVORITES_KEY, JSON.stringify([...next]));
      } catch {
        // storage full / private mode — favorites just won't persist
      }
      return next;
    });
  };

  const loadBrowse = (fid?: string | null, append = false) => {
    if (append) {
      setLoadingMore(true);
    } else {
      setLoading(true);
      setPage(1);
    }
    setMode("browse");
    api
      .browse(
        fid ?? undefined,
        append ? (nextCursor ?? undefined) : undefined,
        PAGE_LIMIT,
      )
      .then((res) => {
        const data = res.data;
        if (res.success && data) {
          setFolders(data.folders);
          setItems((prev) => (append ? [...prev, ...data.files] : data.files));
          setBreadcrumbs(data.breadcrumbs);
          setFolderId(fid ?? null);
          setHasMore(data.has_more);
          setNextCursor(data.next_cursor);
          setErrorType(null);
        } else {
          if (!append) {
            setFolders([]);
            setItems([]);
            setBreadcrumbs([]);
          }
          setHasMore(false);
          setNextCursor(null);
          setErrorType(res.error_type ?? "api_error");
        }
      })
      .finally(() => {
        setLoading(false);
        setLoadingMore(false);
      });
  };

  const loadSearch = (q?: string, append = false) => {
    if (append) {
      setLoadingMore(true);
    } else {
      setLoading(true);
      setPage(1);
    }
    setMode("search");
    api
      .documents(q, append ? (nextCursor ?? undefined) : undefined, PAGE_LIMIT)
      .then((res) => {
        const data = res.data;
        if (res.success && data) {
          setItems((prev) => (append ? [...prev, ...data.items] : data.items));
          setHasMore(data.has_more);
          setNextCursor(data.next_cursor);
          setErrorType(null);
        } else {
          if (!append) setItems([]);
          setHasMore(false);
          setNextCursor(null);
          setErrorType(res.error_type ?? "api_error");
        }
      })
      .finally(() => {
        setLoading(false);
        setLoadingMore(false);
      });
  };

  // biome-ignore lint/correctness/useExhaustiveDependencies: only run the initial (root folder) load once on mount.
  useEffect(() => {
    loadBrowse(null);
  }, []);

  const visible = useMemo(() => {
    const needle = filterText.trim().toLowerCase();
    let out = items;
    if (favoritesOnly) out = out.filter((f) => favorites.has(f.id));
    if (needle) out = out.filter((f) => f.name.toLowerCase().includes(needle));
    const sorted = [...out].sort((a, b) => {
      if (sortKey === "name") {
        const c = a.name.localeCompare(b.name);
        return sortDir === "asc" ? c : -c;
      }
      const ta = a.modifiedTime ?? "";
      const tb = b.modifiedTime ?? "";
      const c = ta.localeCompare(tb);
      return sortDir === "asc" ? c : -c;
    });
    return sorted;
  }, [items, filterText, favoritesOnly, favorites, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(visible.length / perPage));
  const safePage = Math.min(page, totalPages);
  const paged = visible.slice((safePage - 1) * perPage, safePage * perPage);

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

  const renderActions = (f: DriveFile, compact = false) => (
    <div className="flex items-center gap-1.5">
      <button
        type="button"
        data-testid={`documents-star-${f.id}`}
        title={favorites.has(f.id) ? "Unstar" : "Star"}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          toggleFavorite(f.id);
        }}
        className={`rounded p-1.5 hover:bg-zinc-800 ${
          favorites.has(f.id) ? "text-amber-400" : "text-zinc-500"
        }`}
      >
        <Star size={16} fill={favorites.has(f.id) ? "currentColor" : "none"} />
      </button>
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
      {!compact && (
        <>
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
        </>
      )}
      <a
        href={f.webViewLink}
        target="_blank"
        rel="noreferrer"
        className="rounded p-1.5 text-zinc-500 hover:bg-zinc-800"
      >
        <ExternalLink size={16} />
      </a>
    </div>
  );

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

      {/* Sort / filter / favorites / view toolbar */}
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <input
          data-testid="documents-filter"
          value={filterText}
          onChange={(e) => {
            setFilterText(e.target.value);
            setPage(1);
          }}
          placeholder="Filter loaded docs by name…"
          className="min-w-[200px] flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm text-zinc-100 placeholder-zinc-500 focus:border-amber-500 focus:outline-none"
        />
        <select
          data-testid="documents-sort"
          value={sortKey}
          onChange={(e) => setSortKey(e.target.value as SortKey)}
          className="rounded-lg border border-zinc-700 bg-zinc-800 px-2 py-1.5 text-sm text-zinc-300"
        >
          <option value="name">Sort: name</option>
          <option value="modifiedTime">Sort: modified</option>
        </select>
        <button
          type="button"
          data-testid="documents-sort-dir"
          onClick={() => setSortDir((d) => (d === "asc" ? "desc" : "asc"))}
          title={sortDir === "asc" ? "Ascending" : "Descending"}
          className="rounded-lg border border-zinc-700 px-2.5 py-1.5 text-zinc-300 hover:bg-zinc-800"
        >
          {sortDir === "asc" ? <ArrowUp size={16} /> : <ArrowDown size={16} />}
        </button>
        <button
          type="button"
          data-testid="documents-favorites-only"
          onClick={() => {
            setFavoritesOnly((v) => !v);
            setPage(1);
          }}
          className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 ${
            favoritesOnly
              ? "border-amber-500 text-amber-400"
              : "border-zinc-700 text-zinc-300 hover:bg-zinc-800"
          }`}
        >
          <Star size={14} fill={favoritesOnly ? "currentColor" : "none"} />
          Starred{favoritesOnly ? ` (${favorites.size})` : ""}
        </button>
        <button
          type="button"
          data-testid="documents-view-toggle"
          onClick={() => setView((v) => (v === "list" ? "grid" : "list"))}
          title={view === "list" ? "Switch to cards" : "Switch to list"}
          className="flex items-center gap-1.5 rounded-lg border border-zinc-700 px-3 py-1.5 text-zinc-300 hover:bg-zinc-800"
        >
          {view === "list" ? <LayoutGrid size={16} /> : <List size={16} />}
          {view === "list" ? "Cards" : "List"}
        </button>
        <select
          data-testid="documents-per-page"
          value={perPage}
          onChange={(e) => {
            setPerPage(Number(e.target.value));
            setPage(1);
          }}
          className="rounded-lg border border-zinc-700 bg-zinc-800 px-2 py-1.5 text-sm text-zinc-300"
        >
          {[12, 25, 50].map((n) => (
            <option key={n} value={n}>
              {n}/page
            </option>
          ))}
        </select>
        <span
          data-testid="documents-count"
          className="ml-auto text-xs text-zinc-500"
        >
          {visible.length} of {items.length} loaded
          {favorites.size > 0 && ` · ${favorites.size} starred`}
        </span>
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

      {!loading &&
        !errorType &&
        visible.length === 0 &&
        folders.length === 0 && (
          <div className="rounded-lg border border-zinc-800 bg-panel p-8 text-center text-zinc-500">
            {favoritesOnly
              ? "No starred documents — click the star on any doc to pin it here. Stars are kept in this browser (Drive-side starring needs a backend update)."
              : "No documents found."}
          </div>
        )}

      <div
        className={view === "grid" ? "grid gap-2 sm:grid-cols-2" : "grid gap-2"}
        data-testid="documents-list"
      >
        {paged.map((f) => (
          <div
            key={f.id}
            className="rounded-lg border border-zinc-800 bg-panel p-4 hover:border-zinc-700"
          >
            <div className="flex items-center justify-between gap-2">
              <a
                href={f.webViewLink}
                target="_blank"
                rel="noreferrer"
                className="flex min-w-0 flex-1 items-center gap-3"
              >
                <FileText size={18} className="shrink-0 text-amber-400" />
                <div className="min-w-0">
                  <div className="truncate text-zinc-100">{f.name}</div>
                  <div className="text-xs text-zinc-400">{f.modifiedTime}</div>
                </div>
              </a>
              {renderActions(f, view === "grid")}
            </div>

            {rowAction?.fileId === f.id && rowAction.kind === "restore" && (
              <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-zinc-800 pt-3">
                <span className="text-xs text-zinc-400">
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
                <span className="text-xs text-zinc-400">
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

      {/* Client-side pagination + server-side "load more" */}
      {!loading && !errorType && visible.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <button
            type="button"
            data-testid="documents-prev-page"
            disabled={safePage <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="rounded-lg border border-zinc-700 px-3 py-1.5 text-zinc-300 hover:bg-zinc-800 disabled:opacity-50"
          >
            Prev
          </button>
          <span
            data-testid="documents-page-indicator"
            className="text-xs text-zinc-500"
          >
            Page {safePage} of {totalPages}
          </span>
          <button
            type="button"
            data-testid="documents-next-page"
            disabled={safePage >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            className="rounded-lg border border-zinc-700 px-3 py-1.5 text-zinc-300 hover:bg-zinc-800 disabled:opacity-50"
          >
            Next
          </button>
          {hasMore && (
            <button
              type="button"
              data-testid="documents-load-more"
              disabled={loadingMore}
              onClick={() =>
                mode === "search"
                  ? loadSearch(query || undefined, true)
                  : loadBrowse(folderId, true)
              }
              className="ml-auto rounded-lg border border-amber-700 px-3 py-1.5 text-amber-300 hover:bg-amber-950/30 disabled:opacity-50"
            >
              {loadingMore ? "Loading…" : "Load more from Drive"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
