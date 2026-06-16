# Start Auto-Typer on Windows (foreground)
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$python = $null
foreach ($cmd in @("python", "python3", "py")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        $python = $cmd
        break
    }
}

if (-not $python) {
    Write-Host "  ERROR: Python not found. Run install-windows.ps1 first."
    exit 1
}

$mode = $args[0]

if ($mode -eq "--test") {
    & $python auto_typer.py --test
    exit $LASTEXITCODE
}

if ($mode -eq "--bg") {
    $vbs = Join-Path $ScriptDir "launch-silent-windows.vbs"
    if (-not (Test-Path $vbs)) {
        Write-Host "  ERROR: launch-silent-windows.vbs not found."
        exit 1
    }
    Start-Process -FilePath "wscript.exe" -ArgumentList "`"$vbs`"" -WindowStyle Hidden
    Start-Sleep -Seconds 1
    Write-Host "  Auto-Typer started in background."
    Write-Host "  Stop with: .\stop-windows.ps1"
    exit 0
}

& $python auto_typer.py @args