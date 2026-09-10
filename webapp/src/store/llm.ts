import { create } from "zustand";
import { type LlmProvider, api } from "../lib/api";
import { pickPreferredModel } from "../lib/model-preference";

interface LlmState {
  providers: LlmProvider[];
  status: Record<string, "probing" | "detected" | "not_found">;
  selectedProvider: string;
  selectedModel: string;
  models: string[];
  loadedModels: string[];
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
  loadedModels: [],

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
    set({ selectedProvider: name, models: [], loadedModels: [] });
    try {
      const { models, loaded } = await api.llmModels(name);
      const saved = localStorage.getItem(LS_MODEL);
      // Resident-first: never override a model already loaded in Ollama with
      // a different one just because it's saved/preferred — that evicts it
      // and forces a ~30s cold reload (BUGS_DEPOT.md BUG-030).
      const model =
        saved &&
        models.includes(saved) &&
        (loaded.length === 0 || loaded.includes(saved))
          ? saved
          : pickPreferredModel(models, loaded);
      set({ models, loadedModels: loaded, selectedModel: model });
      if (model) localStorage.setItem(LS_MODEL, model);
    } catch {
      set({ models: [], loadedModels: [] });
    }
  },

  selectModel: (name: string) => {
    localStorage.setItem(LS_MODEL, name);
    set({ selectedModel: name });
  },
}));
