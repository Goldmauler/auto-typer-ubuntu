# Install Auto-Typer for Windows
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host ""
Write-Host "  Auto-Typer - Windows Install"
Write-Host "  ============================"
Write-Host ""

$python = $null
foreach ($cmd in @("python", "python3", "py")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        $python = $cmd
        break
    }
}

if (-not $python) {
    Write-Host "  ERROR: Python not found."
    Write-Host "  Install Python 3.10+ from https://www.python.org/downloads/"
    Write-Host "  Check 'Add Python to PATH' during install."
    exit 1
}

Write-Host "  Using: $python"
& $python --version
Write-Host ""

Write-Host "  Installing pynput ..."
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt

if (-not (Test-Path "config.txt")) {
    $configText = @(
        "# Auto-Typer config - edit hotkey and speed here"
        "# Examples: ctrl+shift+f12, ctrl+alt+t, ctrl+shift+v"
        "hotkey=ctrl+shift+f12"
        "speed=8"
        "human_delay=true"
    ) -join "`n"
    Set-Content -Path "config.txt" -Value $configText -Encoding UTF8
    Write-Host "  Created config.txt (default hotkey: Ctrl+Shift+F12)"
}

Write-Host ""
Write-Host "  Install complete!"
Write-Host ""
Write-Host "  Next steps:"
Write-Host "    1. Run:  .\set-hotkey.ps1     (optional - change shortcut)"
Write-Host "    2. Run:  .\start-windows.bat  (start listening)"
Write-Host "    3. Copy text, click a field, press your hotkey"
Write-Host "    4. Press hotkey again to interrupt/stop typing"
Write-Host ""