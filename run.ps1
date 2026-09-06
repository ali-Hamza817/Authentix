# Authentix — one-step setup & launch (Windows PowerShell)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
}

$py = ".\.venv\Scripts\python.exe"
Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
& $py -m pip install --upgrade pip -q
& $py -m pip install -r requirements.txt -q

# Build the React UI when Node is available (server.py falls back to web/ otherwise)
$npm = Get-Command npm -ErrorAction SilentlyContinue
if ($npm -and -not (Test-Path "frontend\dist")) {
    Write-Host "Building the React frontend..." -ForegroundColor Cyan
    & npm --prefix frontend install --no-audit --no-fund
    & npm --prefix frontend run build
}

if ($args.Count -gt 0) {
    & $py -m authentix @args
} else {
    Write-Host "`nAuthentix running at http://127.0.0.1:8000  (Ctrl+C to stop)`n" -ForegroundColor Green
    & $py server.py
}
