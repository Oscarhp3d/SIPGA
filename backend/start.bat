@echo off
title SIPGA Backend - Puerto 8000
cd /d "%~dp0"
echo.
echo  Iniciando API SIPGA en http://127.0.0.1:8000
echo  NO cierres esta ventana mientras uses el sistema.
echo  Abre el navegador en: http://127.0.0.1:8000/dashboard.html
echo.
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
pause
