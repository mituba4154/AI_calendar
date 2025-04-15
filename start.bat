@echo off

REM Start the Flask application in the background
start python app.py > app.log 2>&1
echo AI Calendar started in the background.