@echo off
title Stop VGA Hunter Background Process
echo [*] Menghentikan semua proses background VGA Hunter...
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM pythonw.exe /T 2>nul
echo [+] Berhasil dihentikan!
pause
