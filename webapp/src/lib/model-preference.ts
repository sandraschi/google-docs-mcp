/**
 * Resident-first local LLM model selection.
 *
 * Adapted from the canonical mcp-central-docs/templates/llm-detect/model-preference.ts
 * (logic kept identical; fetch mechanics changed to go through our own backend
 * proxy at GET /api/llm/models instead of hitting Ollama directly from the
 * browser — this repo's Chat page never calls a provider origin directly,
 * per WEBAPP_SOTA_STANDARDS.md §VI.10).
 *
 * The rule: NEVER pick a different model while a preferred one is already
 * loaded in Ollama. Loading a second big model evicts the first and forces a
 * ~30s cold reload for every client using it (see BUGS_DEPOT.md BUG-030,
 * which this repo's original implementation hit exactly — it picked
 * models[0] with no residency check).
 */

export const FLEET_MODEL_PREFERENCE = [
  "qwen3.8:27b",
  "gemma4:12b",
  "qwen2.5-coder:32b-instruct-q4_K_M",
  "deepseek-r1:32b",
  "gemma4:26b",
  "qwen2.5-coder:14b",
  "llama3.1:8b",
  "qwen2.5-coder:7b",
  "mistral:7b",
  "llama3.2:3b",
] as const;

/**
 * Pick the default model: the highest-preference model that is already
 * loaded wins outright (never evicted). If nothing preferred is loaded, fall
 * back to the highest-preference *installed* model. If none of the
 * preference list is installed at all (a non-fleet-standard model set),
 * fall back to the first installed model so the app still has a default.
 */
export function pickPreferredModel(
  installed: string[],
  loaded: string[],
): string {
  const installedOrder = FLEET_MODEL_PREFERENCE.filter((m) =>
    installed.includes(m),
  );
  const loadedSet = new Set(loaded);
  for (const m of installedOrder) {
    if (loadedSet.has(m)) return m;
  }
  if (installedOrder.length > 0) return installedOrder[0];
  return installed[0] ?? "";
}
