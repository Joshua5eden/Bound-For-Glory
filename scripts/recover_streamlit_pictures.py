#!/usr/bin/env python3
"""Pull wrestler portraits from Streamlit Cloud / Supabase into this Mac."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)


def _load_env():
    env = ROOT / '.env'
    if not env.is_file():
        return
    for line in env.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and v and not os.environ.get(k):
            os.environ[k] = v


def main():
    _load_env()
    import bfg_supabase as sb
    import bfg_picture_sync as pic_sync
    import bfg_sessions as mp

    if not sb.supabase_configured():
        print('BLOCKED: Supabase not configured on this Mac.')
        print('Add to .streamlit/secrets.toml OR .env:')
        print('  SUPABASE_URL = "https://xxxx.supabase.co"')
        print('  SUPABASE_KEY = "your-key"')
        print('Copy both from Streamlit Cloud → Manage app → Secrets.')
        return 1

    mp.init_storage()
    roster = []
    for s in mp.list_saved_sessions():
        if s.get('invite_code') == 'BFG-9309' and s.get('has_universe'):
            uni = mp.db_load_blob('mp_universe', s['session_id'])
            if uni and uni.get('roster'):
                roster = list(uni['roster'])
                break
    if not roster:
        for s in mp.list_saved_sessions():
            uni = mp.db_load_blob('mp_universe', s['session_id'])
            if uni and uni.get('roster'):
                roster = list(uni['roster'])
                break

    result = pic_sync.recover_pictures_from_streamlit(roster=roster)
    print(json.dumps({k: v for k, v in result.items() if k != 'errors'}, indent=2))
    if result.get('errors'):
        print('errors:', result['errors'][:8])
    if result.get('ok') and result.get('imported', 0) > 0:
        print(f"OK — imported {result['imported']} portraits for {result.get('invite_code', '?')}")
        return 0
    if result.get('ok'):
        print('Connected to cloud but no downloadable portrait backups found.')
        print('Open your Streamlit Cloud app — pictures may only exist on that server disk.')
        return 2
    print('FAILED:', result.get('error', 'unknown'))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
