import { Download, Eraser, Send } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { API_BASE, api } from "../lib/api";
import { useLlmStore } from "../store/llm";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  ts?: string;
};

function newId(): string {
  return typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random()}`;
}

const HISTORY_KEY = "google-docs-mcp-chat-history";
const PERSONALITY_KEY = "google-docs-mcp-chat-personality";
const MAX_MESSAGES = 100;

const PERSONALITIES: Record<string, string> = {
  assistant:
    "You are a helpful assistant for Google Docs and Drive tasks. Be concise.",
  editor:
    "You are a meticulous copy editor. Suggest precise text edits, quote exact phrases to change.",
  planner:
    "You help plan document structure — outlines, headings, and sections — before writing prose.",
  custom: "",
};

const EXAMPLE_PROMPTS = [
  "How do I find where a heading starts in a document?",
  "What's the difference between trash and delete_permanently?",
  "How do I share a doc with someone as a commenter?",
  "Explain the batch_update escape hatch.",
  "What OAuth scopes does this server request?",
  "How does pagination work for list_files?",
];

function loadHistory(): ChatMessage[] {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) ?? "[]");
  } catch {
    return [];
  }
}

export default function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>(loadHistory);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [personality, setPersonality] = useState(
    localStorage.getItem(PERSONALITY_KEY) ?? "assistant",
  );
  const [customPrompt, setCustomPrompt] = useState("");
  const [skillContent, setSkillContent] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const llm = useLlmStore();

  // biome-ignore lint/correctness/useExhaustiveDependencies: run once on mount only; llm is a fresh store-selector object every render, including it would re-probe in a loop.
  useEffect(() => {
    llm.probe();
    api
      .skills()
      .then((r) => r.items[0] && api.skillContent(r.items[0].name))
      .then((c) => c && setSkillContent(c));
  }, []);

  useEffect(() => {
    localStorage.setItem(
      HISTORY_KEY,
      JSON.stringify(messages.slice(-MAX_MESSAGES)),
    );
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  useEffect(() => {
    localStorage.setItem(PERSONALITY_KEY, personality);
  }, [personality]);

  const systemPrompt = () => {
    const role =
      personality === "custom" ? customPrompt : PERSONALITIES[personality];
    return skillContent ? `${skillContent}\n\n---\n\n## Role\n${role}` : role;
  };

  const send = async (text: string) => {
    if (!text.trim() || !llm.selectedProvider) return;
    const userMsg: ChatMessage = {
      id: newId(),
      role: "user",
      content: text,
      ts: new Date().toISOString(),
    };
    const next = [...messages, userMsg];
    setMessages(next);
    setInput("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/llm/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: llm.selectedProvider,
          model: llm.selectedModel,
          messages: [
            { role: "system", content: systemPrompt() },
            ...next.map(({ role, content }) => ({ role, content })),
          ],
        }),
      });
      const data = await res.json();
      setMessages((m) => [
        ...m,
        {
          id: newId(),
          role: "assistant",
          content: data.content ?? data.error ?? "(no response)",
          ts: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        {
          id: newId(),
          role: "assistant",
          content: `Error: ${String(err)}`,
          ts: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const clear = () => setMessages([]);

  const exportChat = () => {
    const text = messages
      .map((m) => `[${m.ts ?? ""}] ${m.role}: ${m.content}`)
      .join("\n");
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `google-docs-mcp-chat-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col" data-testid="chat-page">
      <div
        className="mb-3 flex items-center gap-3 rounded-lg border border-zinc-800 bg-panel p-3 text-sm"
        data-testid="chat-controls"
      >
        <select
          data-testid="personality-select"
          value={personality}
          onChange={(e) => setPersonality(e.target.value)}
          className="rounded border border-zinc-700 bg-zinc-800 p-1.5 text-zinc-100"
        >
          <option value="assistant">Assistant</option>
          <option value="editor">Editor</option>
          <option value="planner">Planner</option>
          <option value="custom">Custom</option>
        </select>
        {personality === "custom" && (
          <input
            value={customPrompt}
            onChange={(e) => setCustomPrompt(e.target.value)}
            placeholder="Custom system prompt…"
            className="flex-1 rounded border border-zinc-700 bg-zinc-800 p-1.5 text-zinc-100"
          />
        )}
        <span className="ml-auto text-zinc-500">
          {llm.selectedProvider
            ? `${llm.selectedProvider}${llm.selectedModel ? ` / ${llm.selectedModel}` : ""}`
            : "No local LLM detected"}
        </span>
        <button
          type="button"
          data-testid="chat-export"
          disabled={!messages.length}
          onClick={exportChat}
          className="rounded p-1.5 text-zinc-400 hover:bg-zinc-800 disabled:opacity-30"
        >
          <Download size={16} />
        </button>
        <button
          type="button"
          data-testid="chat-clear"
          disabled={!messages.length}
          onClick={clear}
          className="rounded p-1.5 text-zinc-400 hover:bg-zinc-800 disabled:opacity-30"
        >
          <Eraser size={16} />
        </button>
      </div>

      <div
        ref={scrollRef}
        data-testid="chat-messages"
        className="flex-1 space-y-3 overflow-y-auto rounded-lg border border-zinc-800 bg-panel p-4"
      >
        {messages.length === 0 && (
          <div data-testid="example-prompts" className="flex flex-wrap gap-2">
            {EXAMPLE_PROMPTS.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setInput(p)}
                className="rounded-full border border-zinc-700 px-3 py-1.5 text-xs text-zinc-300 hover:bg-zinc-800"
              >
                {p}
              </button>
            ))}
          </div>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            className={`max-w-2xl rounded-lg px-4 py-2 text-sm ${m.role === "user" ? "ml-auto bg-amber-500/10 text-amber-100" : "bg-zinc-800 text-zinc-100"}`}
          >
            {m.content}
          </div>
        ))}
        {loading && <div className="text-zinc-500">Thinking…</div>}
      </div>

      <div className="mt-3 flex gap-2">
        <input
          data-testid="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send(input)}
          placeholder={
            llm.selectedProvider
              ? "Ask about google-docs-mcp…"
              : "Start Ollama or LM Studio to chat"
          }
          disabled={!llm.selectedProvider}
          className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 p-3 text-zinc-100 disabled:opacity-50"
        />
        <button
          type="button"
          data-testid="chat-send"
          disabled={!llm.selectedProvider || loading}
          onClick={() => send(input)}
          className="rounded-lg bg-amber-500 px-4 text-zinc-950 hover:bg-amber-400 disabled:opacity-40"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}
