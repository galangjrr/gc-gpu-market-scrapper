Set WshShell = CreateObject("WScript.Shell")
' Menjalankan server.py di background tanpa jendela CMD hitam (0 = Hidden Window)
WshShell.Run "python server.py", 0, False
