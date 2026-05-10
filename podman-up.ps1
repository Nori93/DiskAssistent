#!/usr/bin/env pwsh
# Build images and start DiskAssistent containers using plain podman.
# Worker-service runs NATIVELY on Windows (full disk access).
# Only webapi + frontend run in containers.

param(
    [switch]$Build   = $false,
    [switch]$Down    = $false,
    [switch]$NoStart = $false
)

$ProjectName = "diskassistent"
$Network     = "diskassistent_net"

# ── Down ─────────────────────────────────────────────────────────────────────
if ($Down) {
    Write-Host "Stopping and removing containers..." -ForegroundColor Cyan
    podman rm -f "${ProjectName}_webapi" "${ProjectName}_frontend" 2>$null
    Write-Host "Done." -ForegroundColor Green
    exit 0
}

# ── Build ─────────────────────────────────────────────────────────────────────
if ($Build) {
    Write-Host "Building webapi..." -ForegroundColor Cyan
    podman build -f "$PSScriptRoot\Containerfile.webapi"  -t diskassistent_webapi  "$PSScriptRoot"
    if ($LASTEXITCODE -ne 0) { Write-Error "WebAPI build failed"; exit 1 }

    Write-Host "Building frontend..." -ForegroundColor Cyan
    podman build -f "$PSScriptRoot\Containerfile.frontend" -t diskassistent_frontend "$PSScriptRoot"
    if ($LASTEXITCODE -ne 0) { Write-Error "Frontend build failed"; exit 1 }

    Write-Host "All images built." -ForegroundColor Green
    if ($NoStart) { exit 0 }
}

# ── Network & Volumes ─────────────────────────────────────────────────────────
podman network exists $Network 2>$null
if ($LASTEXITCODE -ne 0) {
    podman network create $Network | Out-Null
    Write-Host "Created network $Network" -ForegroundColor DarkGray
}

foreach ($vol in @("diskassistent_shared-db", "diskassistent_shared-logs", "diskassistent_shared-thumbs")) {
    podman volume exists $vol 2>$null
    if ($LASTEXITCODE -ne 0) {
        podman volume create $vol | Out-Null
        Write-Host "Created volume $vol" -ForegroundColor DarkGray
    }
}

$SettingsFile = Join-Path $PSScriptRoot "settings.container.json"

# ── Remove old containers if they exist ───────────────────────────────────────
podman rm -f "${ProjectName}_webapi" "${ProjectName}_frontend" 2>$null

# ── Start webapi ──────────────────────────────────────────────────────────────
# Worker runs natively on the host; containers reach it via host.containers.internal
Write-Host "Starting webapi..." -ForegroundColor Cyan
podman run -d `
    --name "${ProjectName}_webapi" `
    --network $Network `
    -p 8001:8001 `
    -e WEBAPI_HOST=0.0.0.0 `
    -e WEBAPI_PORT=8001 `
    -e WORKER_URL=http://host.containers.internal:8002 `
    -e "HOST_AGENT_SECRET=$env:HOST_AGENT_SECRET" `
    -v diskassistent_shared-db:/app/database `
    -v diskassistent_shared-logs:/app/logs `
    -v diskassistent_shared-thumbs:/app/frontend/static/img/thumbnails `
    -v "${SettingsFile}:/app/settings.json:ro" `
    diskassistent_webapi
if ($LASTEXITCODE -ne 0) { Write-Error "WebAPI failed to start"; exit 1 }

# ── Start frontend ────────────────────────────────────────────────────────────
Write-Host "Starting frontend..." -ForegroundColor Cyan
podman run -d `
    --name "${ProjectName}_frontend" `
    --network $Network `
    -p 4200:80 `
    diskassistent_frontend
if ($LASTEXITCODE -ne 0) { Write-Error "Frontend failed to start"; exit 1 }

Write-Host ""
Write-Host "Containers running:" -ForegroundColor Green
Write-Host "  Frontend → http://localhost:4200" -ForegroundColor White
Write-Host "  WebAPI   → http://localhost:8001/docs" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "Make sure Worker Service is running natively on port 8002." -ForegroundColor Yellow


# ── Network & Volumes ─────────────────────────────────────────────────────────
podman network exists $Network 2>$null
if ($LASTEXITCODE -ne 0) {
    podman network create $Network | Out-Null
    Write-Host "Created network $Network" -ForegroundColor DarkGray
}

foreach ($vol in @("diskassistent_shared-db", "diskassistent_shared-logs", "diskassistent_shared-thumbs")) {
    podman volume exists $vol 2>$null
    if ($LASTEXITCODE -ne 0) {
        podman volume create $vol | Out-Null
        Write-Host "Created volume $vol" -ForegroundColor DarkGray
    }
}

$SettingsFile = Join-Path $PSScriptRoot "settings.container.json"

# ── Remove old containers if they exist ───────────────────────────────────────
podman rm -f "${ProjectName}_webapi" "${ProjectName}_frontend" 2>$null

# ── Start webapi ──────────────────────────────────────────────────────────────
# Worker runs natively on the host; containers reach it via host.containers.internal
Write-Host "Starting webapi..." -ForegroundColor Cyan
podman run -d `
    --name "${ProjectName}_webapi" `
    --network $Network `
    -p 8001:8001 `
    -e WEBAPI_HOST=0.0.0.0 `
    -e WEBAPI_PORT=8001 `
    -e WORKER_URL=http://host.containers.internal:8002 `
    -e "HOST_AGENT_SECRET=$env:HOST_AGENT_SECRET" `
    -v diskassistent_shared-db:/app/database `
    -v diskassistent_shared-logs:/app/logs `
    -v diskassistent_shared-thumbs:/app/frontend/static/img/thumbnails `
    -v "${SettingsFile}:/app/settings.json:ro" `
    diskassistent_webapi
if ($LASTEXITCODE -ne 0) { Write-Error "WebAPI failed to start"; exit 1 }

# ── Start frontend ────────────────────────────────────────────────────────────
Write-Host "Starting frontend..." -ForegroundColor Cyan
podman run -d `
    --name "${ProjectName}_frontend" `
    --network $Network `
    -p 4200:80 `
    diskassistent_frontend
if ($LASTEXITCODE -ne 0) { Write-Error "Frontend failed to start"; exit 1 }

Write-Host ""
Write-Host "Containers running:" -ForegroundColor Green
Write-Host "  Frontend → http://localhost:4200" -ForegroundColor White
Write-Host "  WebAPI   → http://localhost:8001/docs" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "Make sure Worker Service is running natively on port 8002." -ForegroundColor Yellow
