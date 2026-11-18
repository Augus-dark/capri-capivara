@echo off
cd /d "%~dp0"
title Criar Capri.exe
if not exist "capri_app.py" (
  echo Nao achei o capri_app.py nesta pasta. Coloque este arquivo ao lado dele.
  pause
  exit /b
)
echo Instalando o PyInstaller...
python -m pip install --upgrade pyinstaller
echo.
echo Criando o Capri.exe (pode demorar alguns minutos)...
if exist "capri.ico" (
  python -m PyInstaller --noconfirm --onefile --noconsole --name Capri --icon capri.ico --collect-all customtkinter --collect-all speech_recognition capri_app.py
) else (
  python -m PyInstaller --noconfirm --onefile --noconsole --name Capri --collect-all customtkinter --collect-all speech_recognition capri_app.py
)
echo.
if exist "dist\Capri.exe" (
  echo PRONTO! O arquivo esta em: %~dp0dist\Capri.exe
  explorer "%~dp0dist"
) else (
  echo Deu erro. Leia a mensagem acima.
)
pause
