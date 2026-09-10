export default function Help() {
  return (
    <div
      className="prose prose-invert max-w-3xl space-y-6"
      data-testid="help-page"
    >
      <h1 className="text-2xl font-bold text-zinc-100">Help</h1>

      <section>
        <h2 className="text-lg font-semibold text-zinc-100">Architecture</h2>
        <p className="text-zinc-400">
          FastMCP server (stdio, for Claude Desktop) plus this Starlette webapp
          backend (port 11972) which mounts the same MCP tool surface at{" "}
          <code>/mcp</code>. No local database — Google Docs/Drive are the
          source of truth; the only local state is a cached OAuth token. Full
          detail: <code>docs/ARCHITECTURE.md</code> in the repo.
        </p>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-zinc-100">Ports</h2>
        <table className="w-full text-sm text-zinc-300">
          <tbody>
            <tr>
              <td className="pr-4 text-zinc-500">Backend</td>
              <td>11972</td>
            </tr>
            <tr>
              <td className="pr-4 text-zinc-500">Frontend (dev)</td>
              <td>11973</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-zinc-100">
          Environment variables
        </h2>
        <p className="text-zinc-400">
          <code>GOOGLE_DOCS_MCP_CLIENT_ID</code>,{" "}
          <code>GOOGLE_DOCS_MCP_CLIENT_SECRET</code> — OAuth client from Google
          Cloud Console. See Settings to check current status, or{" "}
          <code>docs/ONBOARDING.md</code> in the repo for the full walkthrough.
        </p>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-zinc-100">Troubleshooting</h2>
        <ul className="list-disc pl-5 text-zinc-400">
          <li>
            All tool calls fail with "not configured" — set the OAuth env vars,
            restart.
          </li>
          <li>
            All tool calls fail with "not authenticated" — click Connect Google
            Account in Settings.
          </li>
          <li>
            Chat is disabled — start Ollama or LM Studio locally, then reload
            Settings.
          </li>
        </ul>
        <p className="text-zinc-500">
          Full list: <code>docs/TROUBLESHOOTING.md</code> in the repo.
        </p>
      </section>
    </div>
  );
}
