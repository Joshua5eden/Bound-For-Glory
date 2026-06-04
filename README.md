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
git clone https://github.com/YOUR_USERNAME/bound-for-glory.git
cd bound-for-glory
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

### Multiplayer (optional)

Create `.streamlit/secrets.toml` (never commit it):

```toml
DATABASE_URL = "postgresql://..."
```

Without a database, solo play and local JSON saves still work.

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
