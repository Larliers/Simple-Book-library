@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
  start "" /D "%~dp0" ".venv\Scripts\pythonw.exe" "src\main.py"
  exit /b 0
)
if exist "main.exe" (
  start "" /D "%~dp0" "main.exe"
  exit /b 0
)
echo No runnable app found. Install the project dependencies first.
pause
exit /b 1
