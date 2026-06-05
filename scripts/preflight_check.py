#!/usr/bin/env python3
"""Pre-deploy sanity check for Bound For Glory (no Streamlit UI run)."""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULES = [
    'app.py',
    'bfg_ui_pages.py',
    'bfg_book_show.py',
    'bfg_autosave.py',
    'bfg_storylines.py',
    'bfg_sponsor_objectives.py',
    'bfg_season_awards.py',
    'bfg_sessions.py',
    'bfg_supabase.py',
    'bfg_crisis.py',
    'bfg_show_quality.py',
    'bfg_twitter_recruit.py',
    'bfg_name_change.py',
]


def main():
    errors = []
    for name in MODULES:
        path = ROOT / name
        if not path.exists():
            errors.append(f'missing: {name}')
            continue
        try:
            ast.parse(path.read_text(encoding='utf-8'))
        except SyntaxError as ex:
            errors.append(f'syntax error in {name}: {ex}')

    req = ROOT / 'requirements.txt'
    if not req.exists():
        errors.append('missing requirements.txt')

    for d in ('data/universe', 'data/sessions', '.streamlit'):
        if not (ROOT / d).exists():
            errors.append(f'missing directory: {d}/')

    if errors:
        print('PREFLIGHT FAILED')
        for e in errors:
            print(' -', e)
        return 1

    print('PREFLIGHT OK — all modules parse; deploy folders present.')
    print('Run locally: python3 -m streamlit run app.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
