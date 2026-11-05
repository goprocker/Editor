# Edit Kit installer for Windows (PowerShell). Copies the skills into %USERPROFILE%\.claude\skills.
# Skills with the same name are backed up first to %USERPROFILE%\.claude\skills-backup\<date>, nothing is lost.
$ErrorActionPreference = "Stop"
$src = Join-Path $PSScriptRoot "skills"
$dst = Join-Path $env:USERPROFILE ".claude\skills"
$bk = Join-Path $env:USERPROFILE (".claude\skills-backup\" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Get-ChildItem $src -Directory | ForEach-Object {
  $target = Join-Path $dst $_.Name
  if (Test-Path $target) { New-Item -ItemType Directory -Force -Path $bk | Out-Null; Move-Item $target (Join-Path $bk $_.Name) }
  Copy-Item $_.FullName $target -Recurse
  Write-Host "installed /$($_.Name)"
}
if (Test-Path $bk) { Write-Host "(your previous versions were saved in $bk)" }
$brands = Join-Path $env:USERPROFILE ".claude\motion-kit\brands"
New-Item -ItemType Directory -Force -Path $brands | Out-Null
if (-not (Test-Path (Join-Path $brands "README.md"))) { Copy-Item (Join-Path $PSScriptRoot "brands\README.md") $brands }
if (-not (Test-Path (Join-Path $brands "_template"))) { Copy-Item (Join-Path $PSScriptRoot "brands\_template") $brands -Recurse }
Write-Host ""
Write-Host "Done. Close and reopen Claude Code, then type:  /edit"
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { Write-Host "Missing: Node.js 22+  ->  download from nodejs.org" }
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { Write-Host "Missing: FFmpeg  ->  open PowerShell and run:  winget install ffmpeg" }
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { Write-Host "Missing: Python 3  ->  python.org (tick 'Add python.exe to PATH'), then:  python -m pip install pillow numpy" }
