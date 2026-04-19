#!/usr/bin/env bash
DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$DIR/venv"

# Create venv if it doesn't exist
if [ ! -f "$VENV/bin/python3.14" ]; then
  echo "🔧 Setting up virtual environment..."
  /opt/homebrew/bin/python3.14 -m venv "$VENV"
  "$VENV/bin/pip" install flask yt-dlp
fi

echo ""
echo "🚀 Starting MediaSnap at http://localhost:8080"
echo "   Press Ctrl+C to stop."
echo ""
"$VENV/bin/python3.14" "$DIR/app.py"
