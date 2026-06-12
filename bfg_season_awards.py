"""Season Awards — end-of-year scoring (not money-only winner)."""
import streamlit as st

PLAYABLE = ['NXT', 'SmackDown', 'WCW']

AWARD_NAMES = [
    'Best Brand', 'Best Overall GM', 'Best Storyline', 'Best Rivalry', 'Best PLE',
    'Best Weekly Show', 'Best Champion', "Best Women's Champion", 'Best Tag Team',
    'Best Match', 'Best Promo', 'Biggest Draw', 'Most Improved Wrestler', 'Breakout Star',
    'Biggest Flop', 'Best Sponsor Activation', 'Best Media Appearance', 'Best Twitter Moment',
    'Best Free Agent Signing', 'Best Contract Move', 'Best Comeback', 'Best Heel',
    'Best Babyface', 'Most Profitable Brand', 'Best Continuity', 'Best Story Payoff',
    'Best Brand Identity Execution',
]

WEIGHTS = {
    'story_quality': 0.30,
    'continuity': 0.20,
    'sponsor': 0.15,
    'ple': 0.15,
    'viewership': 0.07,
    'attendance': 0.05,
    'pop_morale': 0.05,
    'profit': 0.03,
}


def _avg(vals):
    vals = [float(v) for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else 0.0


def brand_season_metrics(company, session_state):
    hist = [h for h in session_state.get('weekly_history', []) if h.get('company') == company]
    storylines = [s for s in session_state.get('storylines', []) if s.get('company') == company]
    objs = [o for o in session_state.get('sponsor_objectives', []) if o.get('company') == company]
    bank = float((session_state.get('company_budgets') or {}).get(company, 0) or 0)

    story_q = _avg([s.get('quality_score', 50) for s in storylines]) or 50
    cont = _avg([s.get('continuity_score', 50) for s in storylines]) or 50
    sponsor_done = sum(1 for o in objs if o.get('status') in ('Met', 'Partial', 'Paid', 'Completed'))
    sponsor_total = max(1, len(objs))
    sponsor_pct = 100.0 * sponsor_done / sponsor_total
    ratings = [float(h.get('rating', 7) or 7) for h in hist]
    ple_shows = [h for h in hist if h.get('ple') or h.get('is_ple')]
    ple_avg = _avg([h.get('rating', 7) for h in ple_shows]) or _avg(ratings) or 7
    view = _avg([h.get('viewership', 0) for h in hist[-12:]]) or 0
    att = _avg([h.get('attendance', 0) for h in hist[-12:]]) or 0
    profit_growth = min(100, max(0, bank / 1_000_000)) if bank > 0 else 30

    pop_morale = 50.0
    roster = [w for w in session_state.get('roster', []) if w.get('company') == company]
    if roster:
        pop_morale = _avg([w.get('popularity', 50) for w in roster[:30]])

    composite = (
        story_q * WEIGHTS['story_quality']
        + cont * WEIGHTS['continuity']
        + sponsor_pct * WEIGHTS['sponsor']
        + ple_avg * 10 * WEIGHTS['ple']
        + min(100, view / 50000) * WEIGHTS['viewership']
        + min(100, att / 500) * WEIGHTS['attendance']
        + pop_morale * WEIGHTS['pop_morale']
        + profit_growth * WEIGHTS['profit']
    )

    best_story = max(storylines, key=lambda s: s.get('quality_score', 0), default=None)
    best_show = max(hist, key=lambda h: float(h.get('rating', 0) or 0), default=None)

    return {
        'company': company,
        'composite': round(composite, 2),
        'story_quality': round(story_q, 1),
        'continuity': round(cont, 1),
        'sponsor_pct': round(sponsor_pct, 1),
        'ple_avg': round(ple_avg, 2),
        'viewership': int(view),
        'attendance': int(att),
        'profit_signal': round(profit_growth, 1),
        'best_storyline': (best_story or {}).get('name', '—'),
        'best_show_week': (best_show or {}).get('week', '—'),
        'best_show_rating': (best_show or {}).get('rating', '—'),
    }


def compute_season_awards(session_state):
    metrics = {c: brand_season_metrics(c, session_state) for c in PLAYABLE}
    winner = max(PLAYABLE, key=lambda c: metrics[c]['composite'])
    awards = {}
    awards['Best Brand'] = winner
    awards['Best Overall GM'] = winner
    awards['Best Storyline'] = metrics[winner]['best_storyline']
    awards['Best Weekly Show'] = f"{metrics[winner]['company']} Week {metrics[winner]['best_show_week']} ({metrics[winner]['best_show_rating']})"
    awards['Most Profitable Brand'] = max(PLAYABLE, key=lambda c: (session_state.get('company_budgets') or {}).get(c, 0))
    awards['Best Continuity'] = max(PLAYABLE, key=lambda c: metrics[c]['continuity'])
    for name in AWARD_NAMES:
        awards.setdefault(name, metrics[winner].get('best_storyline', '—') if 'Story' in name else winner)
    explanation = (
        f"**{winner}** wins the season with composite **{metrics[winner]['composite']}**. "
        f"Story quality ({metrics[winner]['story_quality']}), continuity ({metrics[winner]['continuity']}), "
        f"and sponsor completion ({metrics[winner]['sponsor_pct']}%) outweighed raw bank balance — "
        f"money is only {int(WEIGHTS['profit']*100)}% of the formula."
    )
    return {'metrics': metrics, 'winner': winner, 'awards': awards, 'explanation': explanation}
