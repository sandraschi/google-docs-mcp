$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$RepoName = "google-docs-mcp"
$Triple = "x86_64-pc-windows-msvc"
$ResourceDir = "$PSScriptRoot\resources"
$DevDir = "$PSScriptRoot\binaries"
$BackendPort = 11972
New-Item -ItemType Directory -Force -Path $ResourceDir, $DevDir | Out-Null

Write-Host "=== ${RepoName} Tauri Release Build ===" -ForegroundColor Cyan

# Naked `bun`/`bunx` inherit whatever PATH the invoking shell happened to have,
# which can predate bun's installer PATH registration in an already-open
# PowerShell window (BUG-045 — exactly this bit a real launch on 2026-09-23).
# Resolve qualified paths once instead.
$bunExe = Join-Path $env:USERPROFILE ".bun\bin\bun.exe"
if (-not (Test-Path $bunExe)) { $bunExe = (Get-Command bun -ErrorAction SilentlyContinue).Source }
if (-not $bunExe) { throw "bun not found — install from https://bun.sh" }
$bunxExe = Join-Path $env:USERPROFILE ".bun\bin\bunx.exe"
if (-not (Test-Path $bunxExe)) { $bunxExe = (Get-Command bunx -ErrorAction SilentlyContinue).Source }
if (-not $bunxExe) { throw "bunx not found — install from https://bun.sh" }

# Step 0: Verify API_BASE matches backend port (catches "Failed to fetch" before Tauri build)
$apiFile = Join-Path $Root "webapp\src\lib\api.ts"
if (Test-Path $apiFile) {
    $apiContent = Get-Content $apiFile -Raw
    if ($apiContent -match "127\.0\.0\.1:(\d+)") {
        $apiPort = [int]$Matches[1]
        if ($apiPort -ne $BackendPort) {
            throw "API_BASE in $apiFile points to port $apiPort but backend serves on $BackendPort. In dev Vite proxies work, in prod/NSIS this gives 'Failed to fetch'."
        }
        Write-Host "  API_BASE port: $apiPort (matches backend) [ok]" -ForegroundColor Green
    } else {
        throw "Could not find a 127.0.0.1:<port> API_BASE in $apiFile — required for the packaged (non-proxied) build."
    }
} else {
    throw "webapp/src/lib/api.ts not found at $apiFile"
}

# Step 1: Biome/TypeScript lint gate + React frontend build
Write-Host "-> [1/4] Building frontend (webapp)..." -ForegroundColor Yellow
$webapp = Join-Path $Root "webapp"
Push-Location $webapp
& $bunExe install --frozen-lockfile

Write-Host "  tsc -b ..." -ForegroundColor Gray
& $bunxExe tsc -b
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "TypeScript compilation failed — fix all errors before building NSIS installer" }

Write-Host "  biome check ..." -ForegroundColor Gray
& $bunxExe biome check .
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "Biome check failed — fix all errors before building NSIS installer" }

& $bunExe run build
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "Frontend build failed" }
Pop-Location

# Step 2: Verify entry point exists, then run PyInstaller
Write-Host "-> [2/4] PyInstaller backend..." -ForegroundColor Yellow
$specFile = "$Root\${RepoName}-backend.spec"
if (-not (Test-Path $specFile)) {
    throw "Backend spec file not found at $specFile"
}
$entryFile = "$Root\run_server.py"
if (-not (Test-Path $entryFile)) {
    throw "run_server.py not found at $entryFile — the spec file references this as the entry point."
}

Push-Location $Root
# Patch fastmcp to not crash on missing metadata (dist-info stripped by PyInstaller's
# frozen filesystem even with the spec's preserve list) — see
# rules/tauri_nsis_building.md "Note on fastmcp metadata".
$fm = "$Root\.venv\Lib\site-packages\fastmcp\__init__.py"
if (Test-Path $fm) {
    $c = Get-Content $fm -Raw
    $old = "try:`n    __version__ = _version(`"fastmcp-slim`")`nexcept PackageNotFoundError:`n    __version__ = _version(`"fastmcp`")"
    $new = "try:`n    __version__ = _version(`"fastmcp-slim`")`nexcept PackageNotFoundError:`n    try:`n        __version__ = _version(`"fastmcp`")`n    except PackageNotFoundError:`n        __version__ = `"0.0.0`""
    if ($c.Contains($old)) {
        $c = $c.Replace($old, $new)
        Set-Content $fm -Value $c -Encoding utf8 -NoNewline
        Write-Host "  Patched fastmcp metadata fallback" -ForegroundColor Yellow
    }
}
$pyiExe = "$Root\.venv\Scripts\pyinstaller.exe"
if (-not (Test-Path $pyiExe)) {
    Write-Host "  Installing pyinstaller in project venv..." -ForegroundColor Yellow
    uv add --dev pyinstaller
}
Remove-Item "$Root\dist\${RepoName}-backend.exe" -Force -ErrorAction SilentlyContinue
& $pyiExe "$specFile" --clean --noconfirm
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "PyInstaller failed with exit code $LASTEXITCODE" }

# Gate: smoke-test the frozen binary (catches import crashes generically)
$frozenExe = "$Root\dist\${RepoName}-backend.exe"
Write-Host "  Smoke-testing frozen binary..." -ForegroundColor Yellow
$testPort = 11999
$oldPort = $env:PORT; $oldHost = $env:HOST
$env:PORT = "$testPort"; $env:HOST = "127.0.0.1"
$testProc = Start-Process -FilePath $frozenExe -NoNewWindow -PassThru -RedirectStandardError "$Root\dist\pyi-crash.log"
Start-Sleep -Seconds 5
$env:PORT = $oldPort; $env:HOST = $oldHost
if ($testProc.HasExited) {
    $crash = Get-Content "$Root\dist\pyi-crash.log" -Raw -ErrorAction SilentlyContinue
    Pop-Location
    throw "Frozen binary crashed on launch (exit $($testProc.ExitCode)):`n$crash"
}
$testProc.Kill(); $testProc.Dispose()
Remove-Item "$Root\dist\pyi-crash.log" -Force -ErrorAction SilentlyContinue
Write-Host "  Frozen binary smoke test PASSED" -ForegroundColor Green
Pop-Location

# Step 3: Embed in Tauri resources (+ dev fallback) with size gate
Write-Host "-> [3/4] Embedding backend..." -ForegroundColor Yellow
$src = "$Root\dist\${RepoName}-backend.exe"
if (-not (Test-Path $src)) { throw "Backend exe not found at $src — PyInstaller step failed" }

$sizeMB = (Get-Item $src).Length / 1MB
if ($sizeMB -lt 5) {
    throw "Backend exe is only $([math]::Round($sizeMB, 1)) MB — PyInstaller likely produced a broken binary. Check $Root\build\${RepoName}-backend\warn-*.txt for hidden import warnings."
}
Copy-Item $src "$ResourceDir\${RepoName}-backend.exe" -Force
Copy-Item $src "$DevDir\${RepoName}-backend-$Triple.exe" -Force
Write-Host "  Backend exe: $([math]::Round($sizeMB, 1)) MB" -ForegroundColor Green

$envExample = "$Root\.env.example"
if (Test-Path $envExample) {
    Copy-Item $envExample "$ResourceDir\.env.example" -Force
    Write-Host "  Bundled .env.example [ok]" -ForegroundColor Green
} else {
    Write-Host "  WARNING: .env.example not found at repo root" -ForegroundColor DarkYellow
}

# Step 4: Single NSIS installer
Write-Host "-> [4/4] Tauri NSIS bundle..." -ForegroundColor Yellow
Push-Location $PSScriptRoot
$env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
& $bunxExe @tauri-apps/cli build --bundles nsis
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "Tauri build failed with exit code $LASTEXITCODE" }
Pop-Location

# Stage to repo dist/
$distDir = Join-Path $Root "dist"
New-Item -ItemType Directory -Force -Path $distDir | Out-Null
$nsisDir = "$PSScriptRoot\target\release\bundle\nsis"
if (Test-Path $nsisDir) { Copy-Item "$nsisDir\*-setup.exe" "$distDir\" -Force }

Write-Host "=== Build complete ===" -ForegroundColor Green
Write-Host "Ship: $nsisDir\*.exe"
