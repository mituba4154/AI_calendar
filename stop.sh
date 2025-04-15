#!/bin/bash

# Stop the Flask application
PID=$(pgrep -f "python app.py")

if [ -z "$PID" ]; then
  echo "AI Calendar is not running."
else
  kill $PID
  echo "AI Calendar stopped."
fi