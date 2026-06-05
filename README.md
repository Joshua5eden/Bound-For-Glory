# Bound For Glory

Wrestling GM simulator — run **NXT**, **SmackDown**, and **WCW** in one shared universe (Streamlit).

## Features

- Book weekly shows (match card + long story mode), grades, finances, and storylines
- Brand-themed UI (NXT / SmackDown / WCW)
- Champions, rivalries, Twitter, appearances, sponsors, trades, multiplayer sessions
- Optional AI (OpenAI) and built-in mode with Edge TTS for NXT Unfiltered podcast audio

## Requirements

- Python 3.10+
- See `requirements.txt`

## Run locally

```bash
git clone git@github.com:Joshua5eden/Bound-For-Glory.git
cd Bound-For-Glory
pip3 install -r requirements.txt
cp .env.example .env   # optional — see below
python3 scripts/preflight_check.py
python3 -m streamlit run app.py
```

Open **http://localhost:8501**

### Environment (optional)

Copy `.env.example` to `.env`:

- **`BFG_BUILTIN_AI_ONLY=true`** (default) — no OpenAI billing; built-in scripts + Edge TTS
- Set **`OPENAI_API_KEY`** and `BFG_BUILTIN_AI_ONLY=false` if you want ChatGPT scripts/voices

### Multiplayer / Supabase (optional)

1. In Supabase SQL Editor, run `scripts/supabase_game_saves.sql`.
2. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`:

```toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_KEY = "your-service-role-key"
```

Saves use `game_saves` keyed by `session_id + company + save_type + save_key` so NXT, SmackDown, and WCW never overwrite each other.

Without Supabase secrets, the app runs in **local testing mode** (JSON/SQLite on this server).

### Podcast audio (NXT Unfiltered)

```bash
chmod +x setup_podcast_audio.sh
./setup_podcast_audio.sh
```

## Before deploy

```bash
python3 scripts/preflight_check.py
```

Deploy as a Streamlit app; use host secrets for `OPENAI_API_KEY` and `DATABASE_URL` if needed.

## Project layout

| Path | Role |
|------|------|
| `app.py` | Main Streamlit application |
| `bfg_*.py` | Book show, UI pages, storylines, sessions, crisis, etc. |
| `scripts/preflight_check.py` | Syntax / deploy folder check |
| `.streamlit/config.toml` | Theme and server defaults |

## License

Add your license here if you publish the repo publicly.
