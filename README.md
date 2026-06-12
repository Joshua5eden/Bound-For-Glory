# Bound For Glory

**Joshua Eden** — wrestling GM simulator. Run **NXT**, **SmackDown**, and **WCW** in one shared universe.

Streamlit app for deep single-player / hot-seat GM mode, plus a standalone **Brand Wars GM** React mod for 3-player online seasons.

## Features

- Book weekly shows (match card + long story mode), grades, finances, and storylines
- Brand-themed UI (NXT / SmackDown / WCW)
- Champions, rivalries, Twitter, appearances, sponsors, trades, multiplayer sessions
- **Brand Wars GM** — 3 GMs, one season, online room codes (Supabase)
- Optional AI (OpenAI / Claude) and built-in mode with Edge TTS for NXT Unfiltered podcast audio

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

The standalone **brand-wars-gm** React mod uses the same `game_saves` table for online room codes — see `brand-wars-gm/README.md`.

### Podcast audio (NXT Unfiltered)

```bash
python3 setup_podcast_audio.py
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
| `bfg_*.py` | Book show, UI pages, storylines, sessions, crisis, cloud sync, etc. |
| `brand-wars-gm/` | Standalone 3-player React GM mod (Vite + Tailwind) |
| `scripts/` | Preflight check, Supabase SQL, cloud pull utilities |
| `.streamlit/config.toml` | Theme and server defaults |

## Brand Wars GM (online with friends)

```bash
cd brand-wars-gm
npm install
cp .env.example .env   # add Supabase keys for remote multiplayer
npm run dev
```

Deploy `brand-wars-gm/` to Vercel for a public link — see `brand-wars-gm/README.md`.

## License

MIT — Joshua Eden
