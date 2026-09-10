// In dev, Vite proxies /api and /skill to the backend (vite.config.ts) so a
// bare relative path works. In a production/Tauri build there is no dev
// proxy — the webview serves static files from a different origin than the
// backend — so requests must target the backend's absolute origin directly.
// See native/tauri.conf.json's CSP `connect-src` for the matching allowlist.
export const API_BASE: string = import.meta.env.PROD
  ? "http://127.0.0.1:11972"
  : "";

export type AuthStatus = {
  configured: boolean;
  authenticated: boolean;
};

export type DashboardData = {
  version: string;
  configured: boolean;
  authenticated: boolean;
  tool_count: number;
  scopes: string[];
};

export type ToolInfo = {
  name: string;
  description: string;
  input_schema: {
    properties?: Record<
      string,
      { description?: string; enum?: string[]; type?: string }
    >;
    required?: string[];
  };
};

export type SkillInfo = { name: string; uri: string };

export type LlmProvider = {
  name: string;
  port: number;
  base: string;
  detected: boolean;
};

export type DriveFile = {
  id: string;
  name: string;
  mimeType: string;
  modifiedTime?: string;
  webViewLink?: string;
};

export type FleetApp = { name: string; port: number; url: string };

export type DriveResult = {
  success: boolean;
  error?: string;
  error_type?: string;
  message?: string;
  data?: { items: DriveFile[]; has_more: boolean; next_cursor: string | null };
};

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () =>
    getJson<{ status: string; configured: boolean; authenticated: boolean }>(
      "/api/health",
    ),
  dashboard: () => getJson<DashboardData>("/api/dashboard"),
  tools: () => getJson<{ items: ToolInfo[] }>("/api/tools"),
  skills: () => getJson<{ items: SkillInfo[] }>("/api/skills"),
  skillContent: (name: string) =>
    fetch(`${API_BASE}/skill/${name}`).then((r) => r.text()),
  llmProviders: () => getJson<{ local: LlmProvider[] }>("/api/llm/providers"),
  llmModels: (provider: string) =>
    getJson<{ models: string[]; loaded: string[] }>(
      `/api/llm/models?provider=${provider}`,
    ),
  logs: () => getJson<{ items: string[] }>("/api/logs"),
  documents: (query?: string) =>
    getJson<DriveResult>(
      `/api/documents${query ? `?query=${encodeURIComponent(query)}` : ""}`,
    ),
  apps: () => getJson<{ available: boolean; items: FleetApp[] }>("/api/apps"),
};
