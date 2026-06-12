# Bound For Glory GM Mod

**Joshua Eden** — 3-player wrestling GM game: **WCW vs SmackDown vs NXT**, one 48-week season, one champion brand. Standalone React app (Vite + Tailwind + Recharts).

## Run it

```bash
cd brand-wars-gm
npm install
npm run dev
```

Open the URL Vite prints (usually http://localhost:5173).

## AI features (optional)

Script grading, podcast grading, **Unfiltered episode generation**, and "AI Takes" on the social tab call the Claude API. Podcast playback uses **smooth neural voices** (Microsoft Edge TTS — same as the main Bound For Glory app). Optional OpenAI key for HD voice fallback.

```bash
cp .env.example .env
# put your Anthropic API key in .env
```

Without a key, everything else works — use **Quick Segments** instead of the long-form script mode.

## How it plays

- **Modes**: Hot-seat (pass the device) or **Online** (shared cloud save with room codes).
- Each week, all three GMs book their show (matches, segments, venue), then **GO LIVE**, then advance the week together.
- Week 4 of every month is PLE week. Blow off hot feuds at PLEs for big payoffs.
- Winning isn't just money — the champion brand is decided by **5 pillars**: Story, Sponsor Execution, PLE & Fan Investment, Audience Growth, and Profit.
- Sponsors issue monthly objectives, random incidents hit after PLE weeks (DUIs, injuries, walkouts, Montreal screwjobs…), and there's trading, free agency, training camps, briefcases, a podcast, and a social media timeline.

## Saves

Hot-seat mode persists to `localStorage`. Online mode syncs the shared season through Supabase when configured.

### Play with friends far away

You need **two** things: cloud saves (Supabase) and a **public URL** (localhost only works on your computer).

#### 1. Supabase (syncs the season)

1. [supabase.com](https://supabase.com) → new project
2. SQL Editor → run `scripts/supabase_game_saves.sql`
3. Project Settings → API → copy **URL** and **anon public** key
4. Add to `brand-wars-gm/.env`:

```env
VITE_SUPABASE_URL=https://xxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
```

#### 2. Deploy to Vercel (free public link)

1. Push this repo to GitHub (`Joshua5eden/Bound-For-Glory`)
2. [vercel.com/new](https://vercel.com/new) → import the repo
3. Set **Root Directory** to `brand-wars-gm`
4. Environment variables (same as `.env`):
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`
5. Deploy → you get a URL like `https://bound-for-glory-gm.vercel.app`

Send friends **that URL**. You create a room; they **Join Room** with your **BWG-####** code.

Restart `npm run dev` locally after editing `.env` so cloud saves show as enabled.

The "reset" link in the top bar burns the season down (online reset keeps brand claims).
