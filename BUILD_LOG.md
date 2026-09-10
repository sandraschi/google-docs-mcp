# Build Log

## 2026-09-10 — Initial Tauri/NSIS build

**Result:** Success. Full install → launch → verify → uninstall cycle passed.

### Pipeline

1. `webapp`: `bun install`, `tsc -b`, `biome check`, `bun run build` — clean.
2. PyInstaller: `google-docs-mcp-backend.spec` → `dist/google-docs-mcp-backend.exe` (44 MB,
   well over the 5 MB size gate).
3. Rust/Tauri: `cargo build --release` (native/) — clean, ~2m23s cold, ~1m warm.
4. NSIS: `Google Docs MCP_0.1.0_x64-setup.exe` (47.5 MB) via `makensis`.
5. Smoke test: silent install (`/S`) → launched operator → embedded backend responded
   `{"status":"ok",...}` on `127.0.0.1:11972` → silent uninstall (`/S`) → confirmed removed.

### Failures encountered and fixes (this session)

| # | Symptom | Root cause | Fix |
|---|---------|------------|-----|
| 1 | PyInstaller frozen exe: `PackageNotFoundError: No package metadata was found for fastmcp` | PyInstaller's frozen filesystem strips `.dist-info` even with the spec's preserve list; `fastmcp/__init__.py` calls `importlib.metadata.version()` twice (once for `fastmcp-slim`, falling back to `fastmcp`) with no fallback on the second call | Patched `.venv/Lib/site-packages/fastmcp/__init__.py` to wrap the second `_version("fastmcp")` call in `try/except PackageNotFoundError: __version__ = "0.0.0"`. Same patch step added to `native/build.ps1` so future builds are reproducible without manual intervention. Documented in `rules/tauri_nsis_building.md` already — this confirms the documented gotcha is real and current. |
| 2 | PyInstaller frozen exe: `ModuleNotFoundError: No module named 'unittest'` | The generic fleet PyInstaller spec template excludes `unittest` as a size optimization; this repo's `httplib2` (a transitive dep of `googleapiclient`) imports `pyparsing.testing`, which imports `unittest` at module load time | Removed `unittest` (and `test`/`tests`) from the spec's `excludes` list. Documented inline in `google-docs-mcp-backend.spec` as a repo-specific deviation from the generic template — found by actually running the frozen exe, not by static analysis. |
| 3 | `beforeBuildCommand `bun run build`` failed: `Script not found "build"` | Tauri runs `beforeBuildCommand` from the directory containing `tauri.conf.json` (`native/`), which has no `package.json` — the script lives in `webapp/` | Changed `beforeBuildCommand`/`beforeDevCommand` to the Tauri v2 object form `{"script": "...", "cwd": "../webapp"}`. |
| 4 | `tauri build --bundles nsis` compiled Rust successfully (`exited with code 0`) but produced no `bundle/nsis/*.exe` | `makensis.exe` (NSIS) was installed (`C:\Program Files (x86)\NSIS`) but not on `PATH` — Tauri silently skipped/failed the bundling stage after a successful `cargo build` | Added the NSIS install directory to `PATH` for the build shell. `native/build.ps1`'s existing `$env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"` line does not cover this — flagged as a known gap in that script; a real build machine needs NSIS on `PATH` permanently (winget: `NSIS.NSIS`, or add to `Require-Command` in a future revision). |
| 5 | Real design fix (caught before it shipped, not a build failure): webapp's `fetch("/api/...")` calls are relative paths, which only resolve correctly in dev via the Vite proxy. A packaged/Tauri build serves the webview from a different origin than the backend, so relative paths would 404 ("Failed to fetch") | Added `API_BASE` (`webapp/src/lib/api.ts`) — empty string in dev (`import.meta.env.PROD` false, Vite proxy still used), absolute `http://127.0.0.1:11972` in a production build. Verified the built bundle actually contains the literal string via `grep` on `dist/assets/*.js`. |

### Known gaps for a future pass

- `native/build.ps1`'s NSIS-on-PATH requirement is not yet enforced/auto-installed — add a
  `Require-Command` check (winget `NSIS.NSIS`) before the bundling step.
- Full `pywinauto`-based CUA smoke test (`rules/cua_nsis_smoke_testing.md`) not run — this
  session's manual install/launch/curl/uninstall cycle covers the same functional signal
  (process-level, not window-title/UI-element verification) but is not the automated 9-phase
  script. Add `scripts/cua-smoke.py` in a follow-up if this desktop build sees real usage.
- Installer is unsigned (`mcpb info` / NSIS both report no signature) — acceptable for a
  private/dev build; sign before any public release.
