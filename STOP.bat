@echo off
title STOP VGA HUNTER
cls
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM chrome.exe /T 2>nul
echo [*] Semua proses bot dan chrome berhasil dihentikan.
pause
