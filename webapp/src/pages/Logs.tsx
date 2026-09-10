import { RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../lib/api";

export default function Logs() {
  const [lines, setLines] = useState<string[]>([]);

  const load = () => api.logs().then((r) => setLines(r.items));

  // biome-ignore lint/correctness/useExhaustiveDependencies: `load` is a fresh function each render; interval should still only be set up once on mount.
  useEffect(() => {
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="space-y-3" data-testid="logs-page">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-zinc-100">Logs</h1>
        <button
          type="button"
          data-testid="logs-refresh"
          onClick={load}
          className="flex items-center gap-2 rounded-lg border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 hover:bg-zinc-800"
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>
      <pre
        data-testid="logs-content"
        className="max-h-[70vh] overflow-y-auto rounded-lg border border-zinc-800 bg-black p-4 font-mono text-xs text-zinc-300"
      >
        {lines.length ? lines.join("\n") : "No log lines yet."}
      </pre>
    </div>
  );
}
