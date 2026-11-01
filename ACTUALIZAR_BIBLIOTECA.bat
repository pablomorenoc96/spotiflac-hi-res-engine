@echo off
title SPOTIFLAC HI-RES ENGINE - ACTUALIZADOR DE BIBLIOTECA (1 CLIC)
color 0B

echo ===============================================================================
echo     SPOTIFLAC HI-RES ENGINE - MONITOR Y ACTUALIZADOR DE BIBLIOTECA (1 CLIC)
echo ===============================================================================
echo  * Escanea todos los artistas de D:\MUSICA
echo  * Comprueba si hay nuevos lanzamientos en la nube (Deezer / MusicBrainz)
echo  * Descarga e integra automaticamente en FLAC Hi-Res/Lossless con ffmpeg
echo  * SIN SERVICIOS NI PROCESOS EN SEGUNDO PLANO (Cero consumo al cerrar)
echo ===============================================================================
echo.

python "D:\MUSICA\actualizar_biblioteca.py" %*

echo.
echo ===============================================================================
echo Proceso finalizado. Ningun proceso permanece en segundo plano.
echo ===============================================================================
pause
