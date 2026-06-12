#!/usr/bin/env python3
"""One-time setup for NXT Unfiltered podcast audio."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)


def run(cmd):
    subprocess.run(cmd, check=True)


def main():
    print('Installing Python packages...')
    run([sys.executable, '-m', 'pip', 'install', '-q', '-r', 'requirements.txt'])

    if not shutil.which('ffmpeg'):
        print('Installing ffmpeg (Homebrew)...')
        run(['brew', 'install', 'ffmpeg'])
    print(f"ffmpeg: {shutil.which('ffmpeg')}")

    out = subprocess.run(
        [sys.executable, '-m', 'pip', 'show', 'edge-tts', 'pydub', 'openai'],
        check=True, capture_output=True, text=True,
    ).stdout
    for line in out.splitlines():
        if line.startswith(('Name', 'Version')):
            print(line)

    env = ROOT / '.env'
    if not env.is_file():
        shutil.copy(ROOT / '.env.example', env)
        print('Created .env — edit it and set OPENAI_API_KEY for best voice quality.')
    else:
        print('.env already exists.')

    print('Done. Run: python3 -m streamlit run app.py')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
