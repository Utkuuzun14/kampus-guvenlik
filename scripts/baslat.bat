@echo off
REM ============================================================
REM IoT Kampus Guvenlik Sistemi - Tek tikla baslatma (Windows)
REM Broker + Backend + Sahte Uretec + React panelini ayri
REM pencerelerde baslatir.
REM ============================================================

echo Kampus Guvenlik Sistemi baslatiliyor...

REM 1) Mosquitto broker (ayri pencere)
start "MQTT Broker" /d "C:\Program Files\mosquitto" cmd /k "mosquitto -c mosquitto.conf -v"

REM Broker'in ayaga kalkmasi icin kisa bekleme
timeout /t 3 /nobreak >nul

REM 2) Backend (ayri pencere)
start "Backend API" cmd /k "cd /d %~dp0..\backend && venv\Scripts\activate && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

REM Backend'in baglanmasi icin kisa bekleme
timeout /t 3 /nobreak >nul

REM 3) Sahte veri uretec (ayri pencere)
start "Sahte Veri" cmd /k "cd /d %~dp0..\backend && venv\Scripts\activate && python ..\scripts\sahte_veri.py"

REM 4) React panel (ayri pencere)
start "React Panel" cmd /k "cd /d %~dp0..\frontend && npm run dev"

echo.
echo Dort pencere acildi: Broker, Backend, Sahte Veri, React Panel.
echo Panel icin tarayicida: http://localhost:5173 (veya 5174)
echo.
pause
