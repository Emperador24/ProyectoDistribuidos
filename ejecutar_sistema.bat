@echo off
REM Script para ejecutar el sistema distribuido en Windows
REM Universidad Ada Lovelace - Sistema de Préstamo de Libros

setlocal EnableDelayedExpansion

echo ==========================================
echo Sistema Distribuido de Prestamo de Libros
echo Universidad Ada Lovelace
echo ==========================================
echo.

if "%1"=="" goto mostrar_ayuda
if "%1"=="help" goto mostrar_ayuda
if "%1"=="setup" goto setup
if "%1"=="sede1" goto sede1
if "%1"=="sede2" goto sede2
if "%1"=="ps" goto ps
if "%1"=="test" goto test
if "%1"=="clean" goto clean

:mostrar_ayuda
echo Uso: ejecutar_sistema.bat [opcion]
echo.
echo Opciones:
echo   setup       - Configurar BD y generar datos iniciales
echo   sede1       - Iniciar Gestor y Actores Sede 1
echo   sede2       - Iniciar Gestor y Actores Sede 2
echo   ps          - Iniciar Proceso Solicitante
echo   test        - Ejecutar tests del sistema
echo   clean       - Limpiar contenedores Docker
echo   help        - Mostrar esta ayuda
echo.
echo Ejemplo de uso:
echo   ejecutar_sistema.bat setup    REM Primero configurar
echo   ejecutar_sistema.bat sede1    REM En computadora 1
echo   ejecutar_sistema.bat ps       REM En computadora 2
goto fin

:setup
echo [SETUP] Iniciando configuracion del sistema...
echo.

REM Verificar Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker no esta instalado
    goto fin
)

REM Iniciar contenedor MySQL
echo [SETUP] Iniciando contenedor MySQL...
docker-compose up -d

echo [SETUP] Esperando a que MySQL este listo (30 segundos)...
timeout /t 30 /nobreak >nul

REM Generar datos iniciales
echo [SETUP] Generando datos iniciales...
python generar_datos_iniciales.py localhost 3306

if errorlevel 1 (
    echo [ERROR] Fallo la generacion de datos
    goto fin
)

echo.
echo [SETUP] Sistema configurado correctamente
echo.
echo Siguientes pasos:
echo   1. En computadora 1: ejecutar_sistema.bat sede1
echo   2. En computadora 2: ejecutar_sistema.bat ps
goto fin

:sede1
echo [SEDE1] Iniciando Gestor de Carga y Actores...
echo.

set /p MYSQL_HOST="Host de MySQL [localhost]: "
if "%MYSQL_HOST%"=="" set MYSQL_HOST=localhost

echo.
echo [SEDE1] Iniciando componentes...
echo Presiona Ctrl+C para detener
echo.

REM Iniciar Gestor de Carga
echo [SEDE1] Gestor de Carga (puerto 5555/5556)
start "GC-Sede1" python gestor_carga.py 1 5555 5556

timeout /t 2 /nobreak >nul

REM Iniciar Actores
echo [SEDE1] Actor DEVOLUCION
start "Actor-Dev-Sede1" python actor.py DEVOLUCION 1 localhost 5556 %MYSQL_HOST% 3306

timeout /t 1 /nobreak >nul

echo [SEDE1] Actor RENOVACION
start "Actor-Ren-Sede1" python actor.py RENOVACION 1 localhost 5556 %MYSQL_HOST% 3306

echo.
echo [SEDE1] Todos los componentes iniciados
echo.
echo Ventanas abiertas:
echo   - Gestor de Carga Sede 1
echo   - Actor Devolucion Sede 1
echo   - Actor Renovacion Sede 1
goto fin

:sede2
echo [SEDE2] Iniciando Gestor de Carga y Actores...
echo.

set /p MYSQL_HOST="Host de MySQL [localhost]: "
if "%MYSQL_HOST%"=="" set MYSQL_HOST=localhost

echo.
echo [SEDE2] Iniciando componentes...
echo Presiona Ctrl+C para detener
echo.

REM Iniciar Gestor de Carga
echo [SEDE2] Gestor de Carga (puerto 5557/5558)
start "GC-Sede2" python gestor_carga.py 2 5557 5558

timeout /t 2 /nobreak >nul

REM Iniciar Actores
echo [SEDE2] Actor DEVOLUCION
start "Actor-Dev-Sede2" python actor.py DEVOLUCION 2 localhost 5558 %MYSQL_HOST% 3306

timeout /t 1 /nobreak >nul

echo [SEDE2] Actor RENOVACION
start "Actor-Ren-Sede2" python actor.py RENOVACION 2 localhost 5558 %MYSQL_HOST% 3306

echo.
echo [SEDE2] Todos los componentes iniciados
echo.
echo Ventanas abiertas:
echo   - Gestor de Carga Sede 2
echo   - Actor Devolucion Sede 2
echo   - Actor Renovacion Sede 2
goto fin

:ps
echo [PS] Proceso Solicitante
echo.

set /p SEDE="A que sede conectar? [1/2]: "
if "%SEDE%"=="" set SEDE=1

set /p GC_HOST="Host del Gestor de Carga [localhost]: "
if "%GC_HOST%"=="" set GC_HOST=localhost

if "%SEDE%"=="1" (
    set GC_PORT=5555
) else (
    set GC_PORT=5557
)

set /p ARCHIVO="Archivo de peticiones [peticiones.txt]: "
if "%ARCHIVO%"=="" set ARCHIVO=peticiones.txt

if not exist "%ARCHIVO%" (
    echo [ERROR] Archivo no encontrado: %ARCHIVO%
    goto fin
)

echo.
echo [PS] Conectando a Sede %SEDE% en %GC_HOST%:%GC_PORT%
echo [PS] Archivo: %ARCHIVO%
echo.

python proceso_solicitante.py %ARCHIVO% %GC_HOST% %GC_PORT%
goto fin

:test
echo [TEST] Ejecutando tests del sistema...
echo.

set /p MYSQL_HOST="Host de MySQL [localhost]: "
if "%MYSQL_HOST%"=="" set MYSQL_HOST=localhost

python test_sistema.py %MYSQL_HOST% 3306
goto fin

:clean
echo [CLEAN] Limpiando contenedores Docker...
docker-compose down -v
echo [CLEAN] Limpieza completada
goto fin

:fin
endlocal