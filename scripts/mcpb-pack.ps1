# Builds dist/google-docs-mcp-v{version}.mcpb per MCPB_PACKAGING_STANDARDS.md.
# Fresh wipe+recopy pipeline (never packs a stale mcpb/src twin).

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$pkg = 'google_docs_mcp'
$stageRoot = Join-Path $RepoRoot 'mcpb'
$stageSrc = Join-Path $stageRoot 'src'

Write-Host '[1/6] Wiping mcpb/src ...' -ForegroundColor Cyan
if (Test-Path $stageSrc) {
    Remove-Item -Recurse -Force $stageSrc
}
New-Item -ItemType Directory -Force -Path $stageSrc | Out-Null

Write-Host '[2/6] Copying src/<package> -> mcpb/src/<package> (preserving package dir) ...' -ForegroundColor Cyan
Copy-Item -Recurse -Force (Join-Path $RepoRoot "src\$pkg") (Join-Path $stageSrc $pkg)

Write-Host '[3/6] Stripping bytecode/backup pollution from the fresh stage ...' -ForegroundColor Cyan
Get-ChildItem -Path $stageSrc -Recurse -Include '__pycache__' -Directory -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force
Get-ChildItem -Path $stageSrc -Recurse -Include '*.pyc', '*.bak', '*.bak.*' -File -ErrorAction SilentlyContinue |
    Remove-Item -Force

Write-Host '[4/6] Copying manifest.json + assets ...' -ForegroundColor Cyan
Copy-Item -Force (Join-Path $RepoRoot 'manifest.json') $stageRoot
$stageAssets = Join-Path $stageRoot 'assets'
if (Test-Path $stageAssets) { Remove-Item -Recurse -Force $stageAssets }
Copy-Item -Recurse -Force (Join-Path $RepoRoot 'assets') $stageAssets

Write-Host '[5/6] Ensuring .mcpbignore is present at the pack root ...' -ForegroundColor Cyan
Copy-Item -Force (Join-Path $RepoRoot '.mcpbignore') (Join-Path $stageRoot '.mcpbignore')

Write-Host '[6/6] Verifying 3-4-100 prompts ...' -ForegroundColor Cyan
uv run python scripts/verify_3_4_100.py
if ($LASTEXITCODE -ne 0) {
    Write-Host 'ERROR: 3-4-100 verification failed.' -ForegroundColor Red
    exit 1
}

Write-Host 'Verifying package import resolves from mcpb/src only ...' -ForegroundColor Cyan
$env:PYTHONDONTWRITEBYTECODE = '1'
uv run python scripts/verify_mcpb_import.py $stageSrc $pkg
if ($LASTEXITCODE -ne 0) {
    Write-Host 'ERROR: package does not import cleanly from mcpb/src.' -ForegroundColor Red
    exit 1
}

Get-ChildItem -Path $stageRoot -Recurse -Include '__pycache__', '*.pyc', '*.bak', '*.bak.*' -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force

New-Item -ItemType Directory -Force -Path (Join-Path $RepoRoot 'dist') | Out-Null
$version = (Get-Content (Join-Path $RepoRoot 'manifest.json') | ConvertFrom-Json).version
$outFile = Join-Path $RepoRoot "dist\google-docs-mcp-v$version.mcpb"

Write-Host "Packing -> $outFile ..." -ForegroundColor Cyan
bunx @anthropic-ai/mcpb pack $stageRoot $outFile

Write-Host "Done: $outFile" -ForegroundColor Green
