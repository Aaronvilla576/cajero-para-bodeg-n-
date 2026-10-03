@echo off
echo Instalando dependencias del Sistema de Ventas de Bodegon...
py -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo No se encontro el comando "py". Probando con "python"...
    python -m pip install -r requirements.txt
)
echo.
echo Listo. Ahora puedes ejecutar iniciar.bat
pause
