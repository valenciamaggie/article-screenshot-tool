#!/bin/bash
cd "$(dirname "$0")"
osascript -e 'tell app "Terminal"
    do script "python3 playwright_screenshot.py"
end tell'
