@echo off
title VGA Hunter Control Center
color 0A
cls

:menu
cls
echo =========================================================
echo               VGA HUNTER CONTROL CENTER
echo          Tokopedia + FB Marketplace + Toco.id
echo =========================================================
echo.
echo  [1] Start Control Server + Auto Sniper (Web Dashboard Live)
echo  [2] Jalankan Sekali Scan Manual (Live Discord Alert)
echo  [3] Cek Estimasi Harga Pasar & Potensi Margin Cuan
echo  [4] Reset Database Cache (Kirim Ulang Semua Listing)
echo  [5] Keluar
echo.
echo =========================================================
set /p opt="Pilih menu [1-5]: "

if "%opt%"=="1" goto run_server
if "%opt%"=="2" goto run_once
if "%opt%"=="3" goto run_market
if "%opt%"=="4" goto reset_db
if "%opt%"=="5" exit
goto menu

:run_server
cls
echo [*] Menjalankan Server & Dashboard Live di http://localhost:5000...
python server.py
pause
goto menu

:run_once
cls
echo [*] Menjalankan 1 Putaran Scan...
python hunter.py --once
pause
goto menu

:run_market
cls
echo [*] Menghitung Estimasi Harga Pasar Real-time...
python market_analyzer.py
pause
goto menu

:reset_db
cls
echo [*] Mereset Cache Database seen_deals.db...
python hunter.py --reset-db --once
pause
goto menu
