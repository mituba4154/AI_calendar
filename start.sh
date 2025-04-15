#!/bin/bash

# Start the Flask application in the background
python app.py > app.log 2>&1 &
echo "AI Calendar started in the background."