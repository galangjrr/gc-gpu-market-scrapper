@echo off
title VGA Hunter - Process Status Checker
color 0A
cls
echo ===================================================
echo       VGA HUNTER - PEMERIKSA STATUS BOT PC
echo ===================================================
echo.

powershell -NoProfile -Command ^
    "$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*hunter.py*' };" ^
    "if ($procs) {" ^
    "    Write-Host '[+] STATUS BOT: AKTIF (SEDANG HUNTING DI BACKGROUND)' -ForegroundColor Green;" ^
    "    foreach ($p in $procs) {" ^
    "        $mem = [math]::Round($p.WorkingSetSize / 1MB, 2);" ^
    "        Write-Host ('    - Process ID (PID) : ' + $p.ProcessId);" ^
    "        Write-Host ('    - RAM Terpakai     : ' + $mem + ' MB');" ^
    "        Write-Host ('    - Waktu Mulai      : ' + $p.CreationDate);" ^
    "    }" ^
    "    Write-Host '';" ^
    "    Write-Host '[i] Bot sedang bekerja senyap. Untuk mematikan, jalankan STOP_HUNTER.bat' -ForegroundColor Cyan;" ^
    "} else {" ^
    "    Write-Host '[-] STATUS BOT: TIDAK AKTIF (MATI/OFFLINE)' -ForegroundColor Red;" ^
    "    Write-Host '    Nyalakan bot dengan klik ganda RUN_SILENT.vbs' -ForegroundColor Yellow;" ^
    "}"

echo.
echo ===================================================
pause
