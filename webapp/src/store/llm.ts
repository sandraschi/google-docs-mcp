import { create } from "zustand";
import { type LlmProvider, api } from "../lib/api";

interface LlmState {
  providers: LlmProvider[];
  status: Record<string, "probing" | "detected" | "not_found">;
  selectedProvider: string;
  selectedModel: string;
  models: string[];
  probe: () => Promise<void>;
  selectProvider: (name: string) => Promise<void>;
  selectModel: (name: string) => void;
}

const LS_PROVIDER = "google-docs-mcp-llm-provider";
const LS_MODEL = "google-docs-mcp-llm-model";

export const useLlmStore = create<LlmState>((set, get) => ({
  providers: [],
  status: {},
  selectedProvider: localStorage.getItem(LS_PROVIDER) ?? "",
  selectedModel: localStorage.getItem(LS_MODEL) ?? "",
  models: [],

  probe: async () => {
    set({
      status: { Ollama: "probing", "LM Studio": "probing", vLLM: "probing" },
    });
    try {
      const { local } = await api.llmProviders();
      const status: LlmState["status"] = {};
      for (const p of local)
        status[p.name] = p.detected ? "detected" : "not_found";
      set({ providers: local, status });

      const saved = get().selectedProvider;
      const detected = local.find((p) => p.detected);
      const target =
        local.find((p) => p.name === saved && p.detected) ?? detected;
      if (target) {
        await get().selectProvider(target.name);
      }
    } catch {
      set({
        status: {
          Ollama: "not_found",
          "LM Studio": "not_found",
          vLLM: "not_found",
        },
      });
    }
  },

  selectProvider: async (name: string) => {
    localStorage.setItem(LS_PROVIDER, name);
    set({ selectedProvider: name, models: [] });
    try {
      const { models } = await api.llmModels(name);
      const saved = localStorage.getItem(LS_MODEL);
      const model = saved && models.includes(saved) ? saved : (models[0] ?? "");
      set({ models, selectedModel: model });
      if (model) localStorage.setItem(LS_MODEL, model);
    } catch {
      set({ models: [] });
    }
  },

  selectModel: (name: string) => {
    localStorage.setItem(LS_MODEL, name);
    set({ selectedModel: name });
  },
}));
