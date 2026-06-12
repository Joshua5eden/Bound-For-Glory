#!/usr/bin/env python3
"""Pull full online save (roster, champions, pictures) from Streamlit Cloud / Supabase."""
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
    import bfg_cloud_pull as cloud

    invite = (sys.argv[1] if len(sys.argv) > 1 else 'BFG-9309').strip().upper()
    result = cloud.pull_online_save_to_local(invite_code=invite)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get('ok') else 1


if __name__ == '__main__':
    raise SystemExit(main())
