Set WshShell = CreateObject("WScript.Shell")
' Menjalankan hunter.py murni (Scraper -> Supabase Cloud -> Discord) 100% gaib tanpa buka localhost atau browser
WshShell.Run "python hunter.py", 0, False
