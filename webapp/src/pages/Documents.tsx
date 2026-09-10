import { AlertCircle, ExternalLink, FileText, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { type DriveFile, api } from "../lib/api";

export default function Documents() {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<DriveFile[]>([]);
  const [errorType, setErrorType] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

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
      </div>

      {errorType && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-800 bg-amber-950/30 p-4 text-amber-300">
          <AlertCircle size={18} />
          {errorType === "not_configured" &&
            "Not configured — complete onboarding in Settings first."}
          {errorType === "not_authenticated" &&
            "Not authenticated — run OAuth in Settings first."}
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
          <a
            key={f.id}
            href={f.webViewLink}
            target="_blank"
            rel="noreferrer"
            className="flex items-center justify-between rounded-lg border border-zinc-800 bg-panel p-4 hover:border-zinc-700"
          >
            <div className="flex items-center gap-3">
              <FileText size={18} className="text-amber-400" />
              <div>
                <div className="text-zinc-100">{f.name}</div>
                <div className="text-xs text-zinc-500">{f.modifiedTime}</div>
              </div>
            </div>
            <ExternalLink size={16} className="text-zinc-500" />
          </a>
        ))}
      </div>
    </div>
  );
}
