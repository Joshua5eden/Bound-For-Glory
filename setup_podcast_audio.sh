#!/bin/bash
# One-time setup for NXT Unfiltered podcast audio
set -e
cd "$(dirname "$0")"
echo "Installing Python packages..."
python3 -m pip install -q -r requirements.txt
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "Installing ffmpeg (Homebrew)..."
  brew install ffmpeg
fi
echo "ffmpeg: $(command -v ffmpeg)"
python3 -m pip show edge-tts pydub openai | grep -E '^Name|^Version'
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env — edit it and set OPENAI_API_KEY for best voice quality."
else
  echo ".env already exists."
fi
echo "Done. Run: python3 -m streamlit run app.py"
