@echo off
title VGA HUNTER SNIPER (AUTO-HEALING WATCHDOG)
color 0A

:: Matikan QuickEdit mode agar klik mouse tidak membuat bot freeze/pause
reg add HKCU\Console /v QuickEdit /t REG_DWORD /d 0 /f >nul 2>nul

cd /d "%~dp0"

:loop
cls
echo ======================================================================
echo          VGA HUNTER SNIPER - 24/7 AUTO-HEALING ACTIVE
echo ======================================================================
echo [*] Mode Browser  : 100%% HEADLESS (Auto-Recover on Failure)
echo [*] Cloud Database: Supabase Connected
echo [*] Cloud Web     : https://gcgpu.vercel.app/
echo ======================================================================
python hunter.py

echo.
echo [!] Peringatan: Bot keluar/crash!
echo [*] Membersihkan zombie browser headless...
taskkill /F /IM chrome.exe /T 2>nul
echo [*] Restart otomatis dalam 5 detik...
timeout /t 5 >nul
goto loop
