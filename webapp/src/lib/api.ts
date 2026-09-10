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

export type DriveResult = {
  success: boolean;
  error?: string;
  error_type?: string;
  message?: string;
  data?: { items: DriveFile[]; has_more: boolean; next_cursor: string | null };
};

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path);
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
  skillContent: (name: string) => fetch(`/skill/${name}`).then((r) => r.text()),
  llmProviders: () => getJson<{ local: LlmProvider[] }>("/api/llm/providers"),
  llmModels: (provider: string) =>
    getJson<{ models: string[] }>(`/api/llm/models?provider=${provider}`),
  logs: () => getJson<{ items: string[] }>("/api/logs"),
  documents: (query?: string) =>
    getJson<DriveResult>(
      `/api/documents${query ? `?query=${encodeURIComponent(query)}` : ""}`,
    ),
};
