import { ExternalLink, LayoutGrid, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { type FleetApp, api } from "../lib/api";

export default function Apps() {
  const [items, setItems] = useState<FleetApp[]>([]);
  const [available, setAvailable] = useState(true);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api
      .apps()
      .then((r) => {
        setAvailable(r.available);
        setItems(r.items);
      })
      .finally(() => setLoading(false));
  };

  // biome-ignore lint/correctness/useExhaustiveDependencies: run once on mount only.
  useEffect(() => {
    load();
  }, []);

  return (
    <div className="space-y-4" data-testid="apps-page">
      <div className="flex items-center justify-between">
        <h1 className="flex items-center gap-2 text-xl font-semibold text-zinc-100">
          <LayoutGrid size={20} />
          Apps Hub
        </h1>
        <button
          type="button"
          data-testid="apps-refresh"
          onClick={load}
          className="flex items-center gap-2 rounded-lg border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 hover:bg-zinc-800"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {!available && (
        <div className="rounded-lg border border-zinc-800 bg-panel p-6 text-zinc-500">
          Fleet discovery isn't available on this machine — this feature reads
          the shared port registry from a sibling <code>mcp-central-docs</code>{" "}
          checkout, which only exists on Sandra's own fleet workspace. Not an
          error; just not applicable here.
        </div>
      )}

      {available && !loading && items.length === 0 && (
        <div className="rounded-lg border border-zinc-800 bg-panel p-8 text-center text-zinc-500">
          No other fleet webapps are currently running.
        </div>
      )}

      <div
        className="grid grid-cols-2 gap-3 md:grid-cols-3"
        data-testid="apps-list"
      >
        {items.map((a) => (
          <a
            key={a.port}
            href={a.url}
            target="_blank"
            rel="noreferrer"
            data-testid={`apps-card-${a.name}`}
            className="flex flex-col gap-1 rounded-lg border border-zinc-800 bg-panel p-4 hover:border-amber-500/50"
          >
            <div className="flex items-center justify-between">
              <span className="font-medium text-zinc-100">{a.name}</span>
              <ExternalLink size={14} className="text-zinc-500" />
            </div>
            <span className="text-xs text-zinc-500">:{a.port}</span>
          </a>
        ))}
      </div>
    </div>
  );
}
