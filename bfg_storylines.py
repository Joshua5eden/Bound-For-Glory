"""Storyline Tracker — persistent story memory for AI continuity."""
import random
import streamlit as st

PLAYABLE = ['NXT', 'SmackDown', 'WCW']
STATUSES = [
    'Active', 'Heating Up', 'Cooling Off', 'Ignored', 'Needs Follow-Up',
    'Ready For PLE', 'Completed', 'Dropped',
]
STORY_TYPES = ['Feud', 'Title', 'Faction', 'Betrayal', 'Redemption', 'Celebrity', 'Sports', 'Contract', 'Free Agency']


def default_storyline(company='', name='New Storyline'):
    return {
        'id': random.randint(10000, 99999),
        'name': name,
        'company': company,
        'wrestlers': [],
        'champion_involved': False,
        'title': '',
        'story_type': 'Feud',
        'heat': 50,
        'quality_score': 55,
        'continuity_score': 55,
        'emotional_theme': '',
        'last_updated_week': int(st.session_state.get('week', 0)),
        'last_segment': '',
        'last_week_summary': '',
        'unresolved': [],
        'next_beat': '',
        'ple_target': False,
        'ple_payoff': False,
        'sponsor_tie': '',
        'media_tie': '',
        'twitter_drama': '',
        'morale_impact': 0,
        'popularity_impact': 0,
        'momentum_impact': 0,
        'ai_warning': '',
        'status': 'Active',
        'notes': '',
        'beats': [],
    }


def ensure_storyline_state():
    if 'storylines' not in st.session_state:
        st.session_state.storylines = []
    if 'storyline_flags' not in st.session_state:
        st.session_state.storyline_flags = []


def company_storylines(company):
    ensure_storyline_state()
    return [s for s in st.session_state.storylines if s.get('company') == company]


def get_storyline(sid):
    for s in st.session_state.get('storylines', []):
        if int(s.get('id')) == int(sid):
            return s
    return None


def add_storyline_beat(story, beat_text, week=None):
    if not story:
        return
    wk = int(week if week is not None else st.session_state.get('week', 0))
    story['beats'].insert(0, {'week': wk, 'text': (beat_text or '')[:500]})
    story['beats'] = story['beats'][:40]
    story['last_updated_week'] = wk
    story['last_segment'] = (beat_text or '')[:200]


def update_storyline_from_show(company, rating, feedback, featured, rival, ple=False):
    """AI-style update after a show completes."""
    ensure_storyline_state()
    fb = feedback or {}
    active = [s for s in st.session_state.storylines if s.get('company') == company and s.get('status') not in ('Completed', 'Dropped')]
    if not active:
        if featured and featured not in ('None', ''):
            s = default_storyline(company, f'{featured} arc')
            s['wrestlers'] = [featured]
            s['heat'] = 45
            s['last_week_summary'] = f'Week {st.session_state.week}: {featured} featured on show ({rating}/10).'
            st.session_state.storylines.insert(0, s)
        return []
    updates = []
    story_drop = bool(fb.get('dropped'))
    for s in active:
        names = set(s.get('wrestlers') or [])
        hit = featured in names or any(n in str(rival or '') for n in names) or not names
        if not hit and story_drop:
            s['status'] = 'Ignored'
            s['continuity_score'] = max(0, int(s.get('continuity_score', 50)) - 12)
            s['ai_warning'] = f"Story ignored this week — '{s.get('name')}' needs follow-up."
            updates.append(s)
            continue
        if hit:
            s['heat'] = min(100, int(s.get('heat', 50)) + random.randint(2, 8))
            s['quality_score'] = min(100, int(s.get('quality_score', 50)) + int((float(rating or 7) - 6) * 3))
            s['continuity_score'] = min(100, int(s.get('continuity_score', 50)) + (6 if not story_drop else -8))
            if float(rating or 7) >= 8:
                s['status'] = 'Heating Up' if s['status'] == 'Active' else s['status']
            if ple:
                s['ple_target'] = True
                if float(rating or 7) >= 8.5:
                    s['status'] = 'Ready For PLE'
            s['last_week_summary'] = (fb.get('summary') or f'Show rated {rating}/10')[:220]
            if fb.get('dropped'):
                s.setdefault('unresolved', []).append(f"Week {st.session_state.week}: thread dropped on TV")
            if fb.get('next_week'):
                s['next_beat'] = fb.get('next_week', '')[:200]
            add_storyline_beat(s, s['last_week_summary'])
        updates.append(s)
    return updates


def migrate_flags_to_storylines():
    """One-time style merge from legacy storyline_flags."""
    ensure_storyline_state()
    existing = {(s.get('company'), s.get('name')) for s in st.session_state.storylines}
    for f in st.session_state.get('storyline_flags', []):
        comp = f.get('company', '')
        flag = f.get('flag', 'Story')
        target = f.get('target', '')
        key = (comp, flag)
        if key in existing or not comp:
            continue
        s = default_storyline(comp, flag[:80])
        if target:
            s['wrestlers'] = [target]
        s['notes'] = f.get('notes', '')[:200]
        s['status'] = 'Needs Follow-Up' if f.get('unresolved') else 'Active'
        st.session_state.storylines.append(s)
        existing.add(key)
