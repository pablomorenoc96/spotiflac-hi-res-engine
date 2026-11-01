@echo off
title SPOTIFLAC HI-RES ENGINE - DESCARGADOR INTERACTIVO (HI-RES 24-BIT / LOSSLESS)
chcp 65001 >nul
cd /d "D:\MUSICA"
python descargar_musica.py %*
echo.
pause
