@echo off
chcp 65001 >nul
title SpotiFLAC Hi-Res Engine - Audiophile Curator

echo ===============================================================================
echo                SPOTIFLAC HI-RES ENGINE - AUDIOPHILE DESKTOP GUI
echo ===============================================================================
echo  Iniciando interfaz visual de alta fidelidad...
echo  Prioridad: ⭐ Hi-Res 24-bit / 💿 FLAC 16-bit Lossless
echo  Regla estricta: Cero procesos residentes en segundo plano
echo ===============================================================================
echo.

python "%~dp0app.py"

exit /b
