import { ChevronDown, ChevronRight, Wrench } from "lucide-react";
import { useEffect, useState } from "react";
import { type ToolInfo, api } from "../lib/api";

function ToolCard({ tool }: { tool: ToolInfo }) {
  const [open, setOpen] = useState(false);
  const operationEnum = tool.input_schema.properties?.operation?.enum;

  return (
    <div
      className="rounded-lg border border-zinc-800 bg-panel"
      data-testid={`tool-card-${tool.name}`}
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between p-4 text-left"
      >
        <div className="flex items-center gap-3">
          <Wrench size={16} className="text-amber-400" />
          <div>
            <div className="font-medium text-zinc-100">{tool.name}</div>
            <div className="text-sm text-zinc-500">{tool.description}</div>
          </div>
        </div>
        {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </button>
      {open && (
        <div className="border-t border-zinc-800 p-4 text-sm">
          {operationEnum ? (
            <>
              <div className="mb-2 text-zinc-400">
                Portmanteau — {operationEnum.length} operations:
              </div>
              <div className="flex flex-wrap gap-2">
                {operationEnum.map((op) => (
                  <span
                    key={op}
                    className="rounded bg-zinc-800 px-2 py-1 font-mono text-xs text-zinc-300"
                  >
                    {op}
                  </span>
                ))}
              </div>
            </>
          ) : (
            <div className="text-zinc-500">Solo tool — no operation enum.</div>
          )}
        </div>
      )}
    </div>
  );
}

export default function Tools() {
  const [tools, setTools] = useState<ToolInfo[]>([]);

  useEffect(() => {
    api.tools().then((r) => setTools(r.items));
  }, []);

  return (
    <div className="space-y-3" data-testid="tools-page">
      <h1 className="text-xl font-semibold text-zinc-100">
        Tools ({tools.length})
      </h1>
      {tools.map((t) => (
        <ToolCard key={t.name} tool={t} />
      ))}
    </div>
  );
}
