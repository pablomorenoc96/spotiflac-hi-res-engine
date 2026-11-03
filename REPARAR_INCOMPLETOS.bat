@echo off
chcp 65001 >nul
title SpotiFLAC Hi-Res Engine - Reparador de Álbumes Incompletos

echo ===============================================================================
echo    SPOTIFLAC HI-RES ENGINE - REPARACIÓN DE ÁLBUMES INCOMPLETOS
echo ===============================================================================
echo  Detecta álbumes con solo carátula (cover.jpg) o 0 pistas de audio
echo  y descarga automáticamente todas sus pistas faltantes a:
echo    * Prioridad 1: ⭐ Hi-Res 24-bit / 48-192 kHz
echo    * Prioridad 2: 💿 Lossless FLAC 16-bit (CD Quality)
echo    * Auditoría acústica estricta con ffmpeg (0 errores)
echo ===============================================================================
echo.

if not "%~1"=="" (
    python "%~dp0actualizar_biblioteca.py" --reparar-incompletos %*
    goto fin
)

echo Selecciona el modo de reparación:
echo   [1] Reparar lote pequeño (Primeros 10 álbumes incompletos)
echo   [2] Reparar lote mediano (Primeros 50 álbumes incompletos)
echo   [3] Reparar TODOS los álbumes incompletos de la biblioteca
echo   [4] Reparar álbumes de un artista específico
echo   [5] Solo auditar y actualizar informe (_ALBUMES_INCOMPLETOS_DETECTADOS.txt)
echo   [6] Salir
echo.
set /p opt="Opción [1-6]: "

if "%opt%"=="1" (
    echo.
    python "%~dp0actualizar_biblioteca.py" --reparar-incompletos --limite 10
    goto fin
)
if "%opt%"=="2" (
    echo.
    python "%~dp0actualizar_biblioteca.py" --reparar-incompletos --limite 50
    goto fin
)
if "%opt%"=="3" (
    echo.
    python "%~dp0actualizar_biblioteca.py" --reparar-incompletos
    goto fin
)
if "%opt%"=="4" (
    echo.
    set /p art="Nombre exacto del artista: "
    python "%~dp0actualizar_biblioteca.py" --reparar-incompletos --artista "%art%"
    goto fin
)
if "%opt%"=="5" (
    echo.
    python "%~dp0actualizar_biblioteca.py" --auditar
    goto fin
)

:fin
echo.
echo Presiona cualquier tecla para cerrar...
pause >nul
