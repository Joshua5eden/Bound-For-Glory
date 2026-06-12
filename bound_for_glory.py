#!/usr/bin/env python3
"""Run Bound For Glory locally: install deps, preflight check, launch Streamlit.

Usage:
    python3 bound_for_glory.py            # full setup + launch
    python3 bound_for_glory.py --check    # preflight check only (use before deploy)

Open: http://localhost:8501

Optional multiplayer database: set DATABASE_URL in .streamlit/secrets.toml
(never commit real keys).

Podcast audio (NXT Unfiltered): python3 setup_podcast_audio.py
OpenAI voices (optional): copy .env.example to .env and set OPENAI_API_KEY.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)


def run(cmd):
    subprocess.run(cmd, check=True)


def main():
    check_only = '--check' in sys.argv[1:]

    if not check_only:
        print('Installing Python packages...')
        run([sys.executable, '-m', 'pip', 'install', '-q', '-r', 'requirements.txt'])

    print('Running preflight check...')
    run([sys.executable, 'scripts/preflight_check.py'])

    if check_only:
        print('Preflight check passed — ready to deploy.')
        return 0

    print('Starting Streamlit — open http://localhost:8501')
    run([sys.executable, '-m', 'streamlit', 'run', 'app.py'])
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as e:
        raise SystemExit(e.returncode)
    except KeyboardInterrupt:
        raise SystemExit(130)
