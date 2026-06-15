# Run this on WINDOWS (in PowerShell) to save clipboard to a shared folder.
# Setup:
#   1. VirtualBox → Settings → Shared Folders → Add folder "clipboard"
#      Host path: C:\Users\YOURNAME\clipboard  (create this folder)
#      Auto-mount + Permanent
#   2. Copy this script to that folder
#   3. Double-click or run: powershell -File windows-save-clipboard.ps1
#   4. Keep it running — it watches Windows clipboard and saves to paste.txt

$outFile = Join-Path $PSScriptRoot "paste.txt"
$last = ""

Write-Host "Watching Windows clipboard → $outFile"
Write-Host "Copy text in Windows, then press Ctrl+Shift+F12 in Ubuntu"
Write-Host "Press Ctrl+C to stop"
Write-Host ""

while ($true) {
    if (Get-Command Get-Clipboard -ErrorAction SilentlyContinue) {
        $current = Get-Clipboard -Raw -ErrorAction SilentlyContinue
        if ($null -ne $current -and $current -ne $last) {
            $last = $current
            [System.IO.File]::WriteAllText($outFile, $current)
            Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Saved $($current.Length) chars"
        }
    }
    Start-Sleep -Milliseconds 500
}