# Set your Auto-Typer keyboard shortcut
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host ""
Write-Host "  Auto-Typer - Set Hotkey Shortcut"
Write-Host "  ================================="
Write-Host ""
Write-Host "  Enter your shortcut using + between keys."
Write-Host "  Examples:"
Write-Host "    ctrl+shift+f12   (default)"
Write-Host "    ctrl+alt+t"
Write-Host "    ctrl+shift+v"
Write-Host "    ctrl+shift+pause"
Write-Host ""

$current = "ctrl+shift+f12"
if (Test-Path "config.txt") {
    $line = Get-Content "config.txt" | Where-Object { $_ -match "^hotkey=" } | Select-Object -First 1
    if ($line) { $current = ($line -split "=", 2)[1].Trim() }
}

Write-Host "  Current hotkey: $current"
Write-Host ""
$hotkey = Read-Host "  New hotkey (Enter to keep current)"

if ([string]::IsNullOrWhiteSpace($hotkey)) {
    $hotkey = $current
}

$speed = "15"
if (Test-Path "config.txt") {
    $line = Get-Content "config.txt" | Where-Object { $_ -match "^speed=" } | Select-Object -First 1
    if ($line) { $speed = ($line -split "=", 2)[1].Trim() }
}

$configText = @(
    "# Auto-Typer config - edit hotkey and speed here"
    "# Examples: ctrl+shift+f12, ctrl+alt+t, ctrl+shift+v"
    "hotkey=$hotkey"
    "speed=$speed"
) -join "`n"
Set-Content -Path "config.txt" -Value $configText -Encoding UTF8

Write-Host ""
Write-Host "  Saved hotkey: $hotkey"
Write-Host "  Restart Auto-Typer for changes to take effect."
Write-Host ""