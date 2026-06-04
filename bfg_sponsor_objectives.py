"""Sponsor Objectives — quarterly brand requirements and payouts."""
import random
import streamlit as st

PLAYABLE = ['NXT', 'SmackDown', 'WCW']


def default_objective(company, sponsor='', quarter=None):
    q = quarter or st.session_state.get('quarter', 1)
    return {
        'id': random.randint(10000, 99999),
        'company': company,
        'sponsor': sponsor,
        'quarter': q,
        'title': f'{sponsor or "Brand"} activation',
        'requirement': 'Book sponsor-tagged segment on weekly TV.',
        'progress': 0,
        'target': 3,
        'payout': 250000,
        'penalty': 75000,
        'status': 'Active',
        'notes': '',
        'week_completed': None,
    }


def ensure_sponsor_objectives(companies_dict):
    if 'sponsor_objectives' not in st.session_state:
        st.session_state.sponsor_objectives = []
    if st.session_state.sponsor_objectives:
        return
    for comp in PLAYABLE:
        sponsors = (companies_dict.get(comp) or {}).get('sponsors', []) or ['Partner']
        for i, sp in enumerate(sponsors[:2]):
            o = default_objective(comp, sp)
            o['title'] = f'{sp} — Q{st.session_state.get("quarter", 1)} objective {i + 1}'
            o['requirement'] = f'Execute {sp} activation on TV or media ({o["target"]} times).'
            o['payout'] = 200000 + i * 100000
            st.session_state.sponsor_objectives.append(o)


def company_objectives(company):
    return [o for o in st.session_state.get('sponsor_objectives', []) if o.get('company') == company]


def check_show_sponsor_progress(company, sponsor_tags, rating):
    """Bump progress when show includes sponsor activations."""
    tags = [t.lower() for t in (sponsor_tags or []) if t]
    if not tags:
        return []
    done = []
    for o in company_objectives(company):
        if o.get('status') != 'Active':
            continue
        sp = (o.get('sponsor') or '').lower()
        if sp and any(sp in t or t in sp for t in tags):
            o['progress'] = min(int(o.get('target', 3)), int(o.get('progress', 0)) + 1)
            if float(rating or 7) >= 7:
                o['progress'] = min(int(o.get('target', 3)), o['progress'] + 0)  # no double bump
            if o['progress'] >= int(o.get('target', 3)):
                o['status'] = 'Completed'
                o['week_completed'] = st.session_state.get('week')
            done.append(o)
    return done
