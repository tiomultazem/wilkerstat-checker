@echo off
cd /d "%~dp0.."
echo Mengunduh MapLibre GL JS ke static\vendor...
mkdir static\vendor 2>nul

powershell -Command "Invoke-WebRequest -Uri 'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js' -OutFile 'static\vendor\maplibre-gl.js'"
powershell -Command "Invoke-WebRequest -Uri 'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css' -OutFile 'static\vendor\maplibre-gl.css'"

echo Selesai.
