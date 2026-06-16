# Auto-Typer — one-shot install + start (Windows)
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\auto-install.ps1
#   powershell -ExecutionPolicy Bypass -File .\auto-install.ps1 --bg
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$AppArgs
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "  $Message"
}

Write-Host ""
Write-Host "  ============================================"
Write-Host "    AUTO-TYPER - Auto Install and Start"
Write-Host "  ============================================"

Write-Step "[1/4] Checking Python ..."
$python = $null
foreach ($cmd in @("python", "python3", "py")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        $python = $cmd
        break
    }
}

if (-not $python) {
    Write-Host ""
    Write-Host "  ERROR: Python not found."
    Write-Host "  Install Python 3.10+ from https://www.python.org/downloads/"
    Write-Host "  Check 'Add Python to PATH' during install, then run this again."
    Write-Host ""
    Write-Host "  Or try: winget install Python.Python.3.12"
    exit 1
}

Write-Host "  Found: $python"
& $python --version

Write-Step "[2/4] Installing requirements ..."
& $python -m pip install --upgrade pip --quiet
& $python -m pip install -r requirements.txt

Write-Step "[3/4] Checking config ..."
if (-not (Test-Path "config.txt")) {
    $configText = @(
        "# Auto-Typer config"
        "hotkey=ctrl+shift+f12"
        "reset_hotkey=ctrl+shift+f11"
        "speed=40"
        "human_delay=false"
        "indent_mode=literal"
    ) -join "`n"
    Set-Content -Path "config.txt" -Value $configText -Encoding UTF8
    Write-Host "  Created config.txt"
} else {
    Write-Host "  config.txt OK"
}

Write-Step "[4/4] Starting Auto-Typer ..."
Write-Host ""
Write-Host "  Hotkeys:"
Write-Host "    Ctrl+Shift+F12  = start / stop-after-line / resume"
Write-Host "    Ctrl+Shift+F11  = reset to beginning"
Write-Host ""
Write-Host "  Copy text, click a field, press Ctrl+Shift+F12"
Write-Host "  Keep this window open. Ctrl+C here to quit."
Write-Host ""

$mode = $AppArgs | Select-Object -First 1

if ($mode -eq "--bg") {
    $vbs = Join-Path $ScriptDir "launch-silent-windows.vbs"
    if (-not (Test-Path $vbs)) {
        Write-Host "  ERROR: launch-silent-windows.vbs not found."
        exit 1
    }
    Start-Process -FilePath "wscript.exe" -ArgumentList "`"$vbs`"" -WindowStyle Hidden
    Start-Sleep -Seconds 1
    Write-Host "  Running in background. Stop with: .\stop-windows.ps1"
    exit 0
}

& $python auto_typer.py @AppArgs
exit $LASTEXITCODE