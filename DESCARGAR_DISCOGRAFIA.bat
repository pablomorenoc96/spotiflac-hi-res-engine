@echo off
title SPOTIFLAC HI-RES ENGINE - DESCARGADOR DE DISCOGRAFÍAS COMPLETAS
chcp 65001 >nul
cd /d "D:\MUSICA"

echo ===============================================================================
echo      SPOTIFLAC HI-RES ENGINE - DESCARGADOR DE DISCOGRAFÍAS COMPLETAS
echo ===============================================================================
echo  * Descarga toda la discografía de estudio de un artista en 1 solo comando.
echo  * Prioridad 1: ⭐ Hi-Res 24-bit / Prioridad 2: 💿 FLAC 16-bit Lossless.
echo  * Auditoría Acústica ffmpeg (0 Errores) + Carátulas 1000x1000 HD.
echo  * Omite automáticamente los álbumes que ya tengas completos en tu disco.
echo ===============================================================================
echo.

python descargar_discografia.py %*

echo.
pause
