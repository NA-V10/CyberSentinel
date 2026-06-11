Set shell = CreateObject("WScript.Shell")
shell.Run "cmd /k """ & Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\")) & "start-backend.bat""", 1, False
