Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

pythonCmd = "python"
Set shell = CreateObject("WScript.Shell")

On Error Resume Next
shell.Run "pythonw --version", 0, True
If Err.Number <> 0 Then
    Err.Clear
    shell.Run "py -3 --version", 0, True
    If Err.Number = 0 Then
        pythonCmd = "py -3"
    End If
Else
    pythonCmd = "pythonw"
End If
On Error GoTo 0

autoTyper = scriptDir & "\auto_typer.py"
shell.Run pythonCmd & " """ & autoTyper & """", 0, False