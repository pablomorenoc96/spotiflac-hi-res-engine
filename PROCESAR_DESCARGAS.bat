@echo off
chcp 65001 > nul
title Procesador y Auditor de Descargas Musicales (Hi-Res / Lossless)
color 0B

echo ===============================================================================
echo        AUDITORIA Y SUSTITUCION AUTOMATICA DE MUSICA (HI-RES / LOSSLESS)
echo ===============================================================================
echo.
echo Selecciona el modo de ejecucion:
echo   [1] Procesar y sustituir archivos descargados ahora mismo (1 sola pasada)
echo   [2] Modo Vigilante en Tiempo Real (supervisa mientras SpotiFLAC descarga en cola)
echo.
set /p MODO="Selecciona opcion (1 o 2, por defecto 1): "

if "%MODO%"=="2" (
    cls
    echo [MODO VIGILANTE] Supervisando descargas en tiempo real...
    python "D:\MUSICA\procesar_descargas.py" --watch
) else (
    python "D:\MUSICA\procesar_descargas.py"
)

echo.
pause
