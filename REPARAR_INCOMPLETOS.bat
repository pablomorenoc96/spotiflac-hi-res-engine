@echo off
title SPOTIFLAC HI-RES ENGINE - REPARADOR DE ALBUMES INCOMPLETOS
color 0E
cd /d "D:\MUSICA"

echo ===============================================================================
echo    SPOTIFLAC HI-RES ENGINE - REPARACION DE ALBUMES INCOMPLETOS
echo ===============================================================================
echo  Detecta albumes con solo portada (cover.jpg) o pistas faltantes en secuencia
echo  y descarga automaticamente las pistas que faltan a maxima calidad FLAC.
echo ===============================================================================
echo.

if not "%~1"=="" goto con_args

echo Selecciona el modo de reparacion:
echo   [1] Reparar lote de 10 albumes
echo   [2] Reparar lote de 50 albumes
echo   [3] Reparar TODOS los albumes incompletos
echo   [4] Reparar un artista especifico
echo   [5] Solo auditar y actualizar informe
echo   [6] Salir
echo.
set /p opt="Opcion [1-6]: "

if "%opt%"=="1" goto op1
if "%opt%"=="2" goto op2
if "%opt%"=="3" goto op3
if "%opt%"=="4" goto op4
if "%opt%"=="5" goto op5
if "%opt%"=="6" goto fin
goto fin

:op1
echo.
python "D:\MUSICA\actualizar_biblioteca.py" --reparar-incompletos --limite 10
goto fin

:op2
echo.
python "D:\MUSICA\actualizar_biblioteca.py" --reparar-incompletos --limite 50
goto fin

:op3
echo.
python "D:\MUSICA\actualizar_biblioteca.py" --reparar-incompletos
goto fin

:op4
echo.
set /p art="Nombre exacto del artista: "
python "D:\MUSICA\actualizar_biblioteca.py" --reparar-incompletos --artista "%art%"
goto fin

:op5
echo.
python "D:\MUSICA\actualizar_biblioteca.py" --auditar
goto fin

:con_args
python "D:\MUSICA\actualizar_biblioteca.py" --reparar-incompletos %*
goto fin

:fin
echo.
echo Presiona cualquier tecla para cerrar...
pause >nul
