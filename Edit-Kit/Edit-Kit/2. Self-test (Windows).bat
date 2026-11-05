@echo off
REM Double-click to check that Edit Kit works on this PC (renders a 3 s test video)
cd /d "%~dp0"
python selftest.py
if errorlevel 9009 py selftest.py
pause
