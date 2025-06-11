@echo off
echo Ejecutando flujo Gaming via URI...

REM Usar protocolo URI de PAD
start "" "ms-powerautomate://run?flowname=envio_masivo"

echo Comando enviado a Power Automate Desktop
timeout /t 5 /nobreak >nul