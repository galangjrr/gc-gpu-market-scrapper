@echo off
title VGA HUNTER SNIPER - CLOUD & LOCAL MONITOR
color 0A
cls
echo ======================================================================
echo          VGA HUNTER SNIPER - LIVE TERMINAL MONITOR
echo ======================================================================
echo [*] Mode Browser  : 100%% HEADLESS (Browser Gaib / Tidak Akan Muncul)
echo [*] Cloud Database: Supabase Connected (bgsmqeglwfjmkxbvbeay)
echo [*] Cloud Web     : https://gcgpu.vercel.app/
echo [*] Lokasi Kerja  : %~dp0
echo ======================================================================
echo [i] Tips: Anda bisa memicu 'Scan Sekarang' atau 'Pause' langsung dari HP!
echo.

cd /d "%~dp0"
python hunter.py
pause
