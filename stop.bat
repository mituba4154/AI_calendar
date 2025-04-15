@echo off

REM Stop the Flask application
for /f "tokens=1" %%p in ('tasklist /fi "imagename eq python.exe" /fo csv /nh') do (
  if not "%%p"=="INFO:" (
    taskkill /PID %%p /F
  )
)
echo AI Calendar stopped.