import { useState } from "react";
import { API_BASE } from "../lib/api";

type Source = {
  id: string;
  name: string;
  mimeType: string;
  modifiedTime?: string;
};

type StitchResult = {
  document_id: string;
  url: string;
  title: string;
  used: { id: string; name: string }[];
  skipped: { id: string; name: string; reason: string }[];
};

export default function Stitcher() {
  const [mode, setMode] = useState<"recent" | "search" | "ids">("recent");
  const [count, setCount] = useState(10);
  const [query, setQuery] = useState("");
  const [ids, setIds] = useState("");
  const [title, setTitle] = useState("");
  const [sources, setSources] = useState<Source[] | null>(null);
  const [result, setResult] = useState<StitchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const body = () => ({
    mode,
    count,
    query: query || null,
    ids: ids
      .split(/[\s,]+/)
      .map((s) => s.trim())
      .filter(Boolean),
    title: title || null,
    skip_duplicates: true,
  });

  const preview = async () => {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const r = await fetch(`${API_BASE}/api/stitch/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body()),
      }).then((r) => r.json());
      if (!r.success) throw new Error(r.error ?? "Preview failed");
      setSources(r.data.sources);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Preview failed");
      setSources(null);
    } finally {
      setBusy(false);
    }
  };

  const stitch = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`${API_BASE}/api/stitch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body()),
      }).then((r) => r.json());
      if (!r.success) throw new Error(r.error ?? "Stitch failed");
      setResult(r.data);
      setSources(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Stitch failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-3xl space-y-6" data-testid="stitcher-page">
      <div>
        <h1 className="text-2xl font-bold text-zinc-100">Stitcher</h1>
        <p className="mt-1 text-sm text-zinc-400">
          Combine small chat-export docs into one compendium Google Doc — titled
          sections, source links, duplicates removed. Preview first (free), then
          stitch.
        </p>
      </div>

      <div className="flex gap-2" data-testid="stitcher-modes">
        {(["recent", "search", "ids"] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => {
              setMode(m);
              setSources(null);
              setResult(null);
            }}
            className={`rounded-lg px-4 py-1.5 text-sm font-medium ${
              mode === m
                ? "bg-amber-500 text-zinc-950"
                : "border border-zinc-700 text-zinc-300 hover:bg-zinc-800"
            }`}
          >
            {m === "recent"
              ? "Recent"
              : m === "search"
                ? "Search"
                : "Hand-picked"}
          </button>
        ))}
      </div>

      <div className="space-y-3 rounded-xl border border-zinc-800 bg-panel p-4">
        {mode === "recent" && (
          <label className="flex items-center gap-2 text-sm text-zinc-300">
            How many recent docs
            <input
              type="number"
              min={1}
              max={50}
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              className="w-20 rounded-lg border border-zinc-700 bg-zinc-800 p-1.5 text-sm text-zinc-100"
              data-testid="stitcher-count"
            />
          </label>
        )}
        {mode === "search" && (
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search Drive text, e.g. reversing-mcp"
            className="w-full rounded-lg border border-zinc-700 bg-zinc-800 p-2 text-sm text-zinc-100"
            data-testid="stitcher-query"
          />
        )}
        {mode === "ids" && (
          <textarea
            value={ids}
            onChange={(e) => setIds(e.target.value)}
            placeholder="Document ids, comma or newline separated"
            rows={3}
            className="w-full rounded-lg border border-zinc-700 bg-zinc-800 p-2 font-mono text-sm text-zinc-100"
            data-testid="stitcher-ids"
          />
        )}
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Compendium title (optional — dated by default)"
          className="w-full rounded-lg border border-zinc-700 bg-zinc-800 p-2 text-sm text-zinc-100"
          data-testid="stitcher-title"
        />
        <div className="flex gap-2">
          <button
            type="button"
            onClick={preview}
            disabled={busy}
            className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-200 hover:bg-zinc-800 disabled:opacity-40"
            data-testid="stitcher-preview"
          >
            {busy ? "Working…" : "Preview sources"}
          </button>
          <button
            type="button"
            onClick={stitch}
            disabled={busy}
            className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-zinc-950 hover:bg-amber-400 disabled:opacity-40"
            data-testid="stitcher-stitch"
          >
            {busy ? "Stitching…" : "Stitch into new doc"}
          </button>
        </div>
      </div>

      {error && (
        <p className="text-sm text-red-400" data-testid="stitcher-error">
          {error}
        </p>
      )}

      {sources && (
        <div
          className="rounded-xl border border-zinc-800 bg-panel p-4"
          data-testid="stitcher-sources"
        >
          <h2 className="mb-2 font-semibold text-zinc-100">
            {sources.length} source(s) — looks right? Hit stitch.
          </h2>
          <ul className="space-y-1">
            {sources.map((s) => (
              <li
                key={s.id}
                className="truncate text-sm text-zinc-300"
                title={s.id}
              >
                {s.name}
                <span className="text-zinc-500">
                  {" "}
                  · {s.modifiedTime?.slice(0, 10)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {result && (
        <div
          className="rounded-xl border border-emerald-800 bg-emerald-950/20 p-4"
          data-testid="stitcher-result"
        >
          <h2 className="font-semibold text-emerald-300">
            Stitched {result.used.length} doc(s) into “{result.title}”
          </h2>
          <a
            href={result.url}
            target="_blank"
            rel="noreferrer"
            className="text-sm text-emerald-400 hover:underline"
          >
            Open the compendium →
          </a>
          {result.skipped.length > 0 && (
            <p className="mt-1 text-sm text-zinc-400">
              Skipped {result.skipped.length}:{" "}
              {result.skipped.map((s) => `${s.name} (${s.reason})`).join(", ")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
