@echo off
REM Serve the flashcards web app from Windows (not WSL) so a phone on the same
REM Wi-Fi can reach it directly at http://<this-PC-Wi-Fi-IP>:8000 with no
REM port-proxy. Double-click this file in Explorer, or run it from a terminal.
REM First run: Windows Defender Firewall will ask to allow Python -> click Allow
REM (tick "Private networks"). Stop the server with Ctrl-C.
echo Flashcards server starting...
echo On your phone (same Wi-Fi) open:  http://192.168.178.21:8000
echo Press Ctrl-C to stop.
echo.
py -3 -m http.server 8000 --directory "%~dp0."
pause
