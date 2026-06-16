# Stop background Auto-Typer on Windows
$procs = Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'pythonw.exe'" |
    Where-Object { $_.CommandLine -like "*auto_typer.py*" }

if (-not $procs) {
    Write-Host "  Auto-Typer is not running."
    exit 0
}

foreach ($proc in $procs) {
    Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    Write-Host "  Stopped PID $($proc.ProcessId)"
}

Write-Host "  Auto-Typer stopped."