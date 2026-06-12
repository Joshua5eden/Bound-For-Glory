"""Legendary GM Mode — dirt sheet media, calendar approval, owner goals, GM trust,
locker room chemistry, wrestler development, trade block, FA interest, markets,
weekly media questions, and brand power rankings. Adds only — removes nothing."""
import random
from datetime import datetime

import streamlit as st

PLAYABLE = ['NXT', 'SmackDown', 'WCW']

_H = {}


def register_helpers(**kw):
    _H.update(kw)


def _h(name, default=None):
    return _H.get(name, default)


# ====================================================
# DIRT SHEET ACCOUNTS
# ====================================================
DIRT_ACCOUNTS = [
    {'name': 'Dave Meltz', 'handle': '@DaveMeltz', 'style': 'ratings and star analysis'},
    {'name': 'The Wrestling Observer Room', 'handle': '@ObserverRoom', 'style': 'insider analysis'},
    {'name': 'Ringside Radar', 'handle': '@RingsideRadar', 'style': 'show reviews'},
    {'name': 'Pro Graps Insider', 'handle': '@ProGrapsInsider', 'style': 'backstage scoops'},
    {'name': 'The Locker Room Leak', 'handle': '@LockerRoomLeak', 'style': 'morale rumors'},
    {'name': 'Kayfabe Report', 'handle': '@KayfabeReport', 'style': 'story continuity'},
    {'name': 'Fight Desk Daily', 'handle': '@FightDeskDaily', 'style': 'sponsor and business'},
    {'name': 'The Dirt Sheet Doctor', 'handle': '@DirtSheetDoc', 'style': 'hot takes'},
    {'name': 'Main Event Metrics', 'handle': '@MainEventMetrics', 'style': 'numbers and calendar'},
    {'name': 'Heat Check Wrestling', 'handle': '@HeatCheckWres', 'style': 'fan pulse'},
]


def ensure_gm_state():
    ss = st.session_state
    ss.setdefault('gm_trust_adj', {c: 0 for c in PLAYABLE})
    ss.setdefault('locker_chem_adj', {c: 0 for c in PLAYABLE})
    ss.setdefault('dirt_sheet_adj', {c: 0 for c in PLAYABLE})
    ss.setdefault('gm_owner_goal_status', {})
    ss.setdefault('media_question_log', [])
    ss.setdefault('trade_block', [])
    ss.setdefault('calendar_approval_results', {})
    ss.setdefault('dirt_sheet_names', {a['name']: a['name'] for a in DIRT_ACCOUNTS})
    ss.setdefault('dev_focus', {})
    for key in ('gm_trust_adj', 'locker_chem_adj', 'dirt_sheet_adj'):
        for c in PLAYABLE:
            ss[key].setdefault(c, 0)


def _account(i=None):
    a = DIRT_ACCOUNTS[i % len(DIRT_ACCOUNTS)] if i is not None else random.choice(DIRT_ACCOUNTS)
    name = st.session_state.get('dirt_sheet_names', {}).get(a['name'], a['name'])
    return {**a, 'name': name}


def _roster(comp):
    fn = _h('roster')
    return fn(comp) if fn else [w for w in st.session_state.get('roster', []) if w.get('company') == comp]


def _last_show(comp):
    return next((h for h in reversed(st.session_state.get('weekly_history', [])) if h.get('company') == comp), None)


def _avg(vals):
    vals = [v for v in vals if isinstance(v, (int, float))]
    return sum(vals) / len(vals) if vals else 0


# ====================================================
# LOCKER ROOM CHEMISTRY
# ====================================================
def locker_chemistry(comp):
    ensure_gm_state()
    r = _roster(comp)
    if not r:
        return 50, ['No roster data']
    morale = _avg([w.get('morale', 50) for w in r])
    booking = _avg([w.get('booking_satisfaction', 60) for w in r])
    loyalty = _avg([w.get('brand_loyalty', 50) for w in r])
    injured = sum(1 for w in r if w.get('injury'))
    low_morale = sum(1 for w in r if w.get('morale', 50) < 35)
    releases = sum(1 for d in st.session_state.get('departed', []) if isinstance(d, dict) and d.get('company') == comp)
    drama = sum(1 for d in st.session_state.get('twitter_drama', []) if d.get('company') == comp and d.get('unresolved'))
    score = morale * 0.40 + booking * 0.30 + loyalty * 0.30
    score -= low_morale * 2 + injured * 1.5 + min(10, releases) * 1.2 + min(12, drama) * 1.5
    score += st.session_state.locker_chem_adj.get(comp, 0)
    score = max(0, min(100, round(score)))
    notes = [
        f'Average morale {morale:.0f}',
        f'Booking satisfaction {booking:.0f}',
        f'Brand loyalty {loyalty:.0f}',
    ]
    if low_morale: notes.append(f'{low_morale} wrestler(s) under 35 morale')
    if injured: notes.append(f'{injured} injured')
    if drama: notes.append(f'{drama} unresolved Twitter drama flag(s)')
    return score, notes


# ====================================================
# DIRT SHEET APPROVAL (critic score)
# ====================================================
def dirt_sheet_approval(comp):
    ensure_gm_state()
    shows = [h for h in st.session_state.get('weekly_history', []) if h.get('company') == comp]
    score = 55.0
    if shows:
        recent = shows[-6:]
        avg_rating = _avg([float(h.get('episode_rating') or h.get('final_rating') or 7) for h in recent])
        score += (avg_rating - 7.0) * 9
        ples = [h for h in recent if h.get('is_ple')]
        if ples:
            score += (_avg([float(h.get('episode_rating') or 7) for h in ples]) - 7.5) * 4
    stories = [s for s in st.session_state.get('storylines', []) if s.get('company') == comp]
    active = [s for s in stories if str(s.get('status', '')).lower() in ('active', 'building', 'hot')]
    dropped = [s for s in stories if str(s.get('status', '')).lower() in ('dropped', 'abandoned')]
    score += min(10, len(active) * 2.5) - len(dropped) * 4
    objs = [o for o in st.session_state.get('sponsor_objectives', []) if o.get('company') == comp]
    done = [o for o in objs if str(o.get('status', '')).lower() in ('completed', 'complete', 'done')]
    failed = [o for o in objs if str(o.get('status', '')).lower() == 'failed']
    score += len(done) * 2 - len(failed) * 3
    chem, _n = locker_chemistry(comp)
    score += (chem - 60) * 0.15
    score += st.session_state.dirt_sheet_adj.get(comp, 0)
    score = max(0, min(100, round(score)))
    if score >= 85: head = 'Smart booking, strong continuity, and a hot main event saved the week.'
    elif score >= 70: head = 'Solid week — stories connect and champions matter.'
    elif score >= 55: head = 'Watchable, but the booking needs a clearer direction.'
    elif score >= 40: head = 'Cold stretch — dropped threads and random matches are hurting the product.'
    else: head = 'Sheets are roasting this brand — fix continuity before fans tune out.'
    return score, head


# ====================================================
# GM TRUST / OWNER CONFIDENCE
# ====================================================
def gm_trust(comp):
    ensure_gm_state()
    ds, _hd = dirt_sheet_approval(comp)
    chem, _n = locker_chemistry(comp)
    fin = st.session_state.get('company_finance', {}).get(comp, {})
    budget = int(fin.get('current_budget', st.session_state.get('company_budgets', {}).get(comp, 0)) or 0)
    score = 50 + (ds - 60) * 0.45 + (chem - 60) * 0.30
    if budget > 120_000_000: score += 8
    elif budget < 30_000_000: score -= 10
    elif budget < 60_000_000: score -= 4
    goals = evaluate_owner_goals(comp)
    score += sum(4 for g in goals if g['result'] == 'Completed')
    score -= sum(3 for g in goals if g['result'] == 'Failed')
    score += st.session_state.gm_trust_adj.get(comp, 0)
    score = max(0, min(100, round(score)))
    factors = [f'Dirt sheet approval {ds}', f'Locker room chemistry {chem}', f'Budget {budget:,}']
    return score, factors


def trust_tier(score):
    if score >= 85: return 'Untouchable', 'Owner gives you full creative control.'
    if score >= 70: return 'Trusted', 'Owner is happy — keep building.'
    if score >= 50: return 'Stable', 'Owner is watching but patient.'
    if score >= 35: return 'On Notice', 'Owner warnings — budget limits possible.'
    return 'Hot Seat', 'Commissioner review possible — fix sponsor goals and morale now.'


# ====================================================
# OWNER GOALS
# ====================================================
OWNER_GOAL_TEMPLATES = {
    'NXT': [
        {'id': 'nxt_story', 'goal': 'Produce the best storyline of the year', 'metric': 'Run a storyline to PLE payoff with high continuity'},
        {'id': 'nxt_media', 'goal': 'Complete 5 premium media sponsor objectives', 'metric': '5 completed sponsor objectives'},
        {'id': 'nxt_breakout', 'goal': 'Build one breakout star', 'metric': 'A wrestler gains 15+ popularity'},
        {'id': 'nxt_ple', 'goal': 'Have one 9/10 PLE', 'metric': 'Any PLE rated 9.0 or higher'},
        {'id': 'nxt_continuity', 'goal': 'Keep continuity strong all season', 'metric': 'Dirt sheet approval above 80'},
    ],
    'SmackDown': [
        {'id': 'sd_culture', 'goal': 'Win Culture Pulse 6 times', 'metric': '6 Culture Pulse wins'},
        {'id': 'sd_viral', 'goal': 'Create 3 viral celebrity moments', 'metric': '3 viral/mega posts'},
        {'id': 'sd_sponsor', 'goal': 'Complete Sony / PRIME / Paramount objectives', 'metric': 'Complete brand sponsor objectives'},
        {'id': 'sd_view', 'goal': 'Increase viewership by 15%', 'metric': 'Latest viewership 15% over first show'},
        {'id': 'sd_conf', 'goal': 'Keep sponsor confidence above 75', 'metric': 'Sponsor objective completion strong'},
    ],
    'WCW': [
        {'id': 'wcw_rev', 'goal': 'Lead the league in revenue', 'metric': 'Highest total show profit'},
        {'id': 'wcw_sponsor', 'goal': 'Complete EA Sports / Microsoft / Pepsi / Gatorade objectives', 'metric': 'Complete brand sponsor objectives'},
        {'id': 'wcw_stadium', 'goal': 'Sell out one stadium show', 'metric': 'Sellout at a 40k+ venue'},
        {'id': 'wcw_prestige', 'goal': 'Build championship prestige', 'metric': 'Title prestige rising'},
        {'id': 'wcw_finance', 'goal': 'Keep finances strong', 'metric': 'Budget above $60M'},
    ],
}


def evaluate_owner_goals(comp):
    ensure_gm_state()
    out = []
    shows = [h for h in st.session_state.get('weekly_history', []) if h.get('company') == comp]
    objs = [o for o in st.session_state.get('sponsor_objectives', []) if o.get('company') == comp]
    done_objs = [o for o in objs if str(o.get('status', '')).lower() in ('completed', 'complete', 'done')]
    posts = [p for p in st.session_state.get('twitter_posts', []) if p.get('company') == comp]
    fin = st.session_state.get('company_finance', {}).get(comp, {})
    budget = int(fin.get('current_budget', st.session_state.get('company_budgets', {}).get(comp, 0)) or 0)
    ds, _ = dirt_sheet_approval(comp)
    manual = st.session_state.gm_owner_goal_status

    for tpl in OWNER_GOAL_TEMPLATES.get(comp, []):
        gid = tpl['id']
        result, progress = 'In Progress', ''
        if gid in ('nxt_media', 'sd_sponsor', 'wcw_sponsor'):
            need = 5 if gid == 'nxt_media' else 3
            progress = f'{len(done_objs)}/{need} sponsor objectives complete'
            if len(done_objs) >= need: result = 'Completed'
        elif gid == 'nxt_ple':
            ples = [h for h in shows if h.get('is_ple')]
            best = max([float(h.get('episode_rating') or 0) for h in ples], default=0)
            progress = f'Best PLE rating {best:.1f}/10'
            if best >= 9.0: result = 'Completed'
        elif gid in ('nxt_continuity',):
            progress = f'Dirt sheet approval {ds}/100'
            if ds >= 80: result = 'Completed'
            elif ds < 40 and len(shows) >= 6: result = 'Failed'
        elif gid == 'sd_viral':
            viral = sum(1 for p in posts if p.get('viral') or p.get('mega'))
            progress = f'{viral}/3 viral moments'
            if viral >= 3: result = 'Completed'
        elif gid == 'sd_view':
            if len(shows) >= 2:
                first = int(shows[0].get('viewership', 0) or 1)
                latest = int(shows[-1].get('viewership', 0) or 0)
                pct = (latest - first) / first * 100 if first else 0
                progress = f'Viewership {pct:+.0f}% vs first show'
                if pct >= 15: result = 'Completed'
            else:
                progress = 'Need 2+ completed shows'
        elif gid == 'wcw_rev':
            totals = {}
            for h in st.session_state.get('weekly_history', []):
                totals[h.get('company')] = totals.get(h.get('company'), 0) + int(h.get('profit', 0) or 0)
            mine = totals.get(comp, 0)
            progress = f'Total profit {mine:,}'
            if totals and mine == max(totals.values()) and mine > 0: result = 'Completed'
        elif gid == 'wcw_stadium':
            hit = any(int(h.get('capacity', 0) or 0) >= 40000 and 'Sellout' in str((h.get('logistics') or {}).get('sellout_status', '')) for h in shows)
            progress = 'Stadium sellout achieved' if hit else 'No stadium sellout yet'
            if hit: result = 'Completed'
        elif gid == 'wcw_finance':
            progress = f'Budget {budget:,}'
            if budget >= 60_000_000: result = 'Completed'
            elif budget < 20_000_000: result = 'Failed'
        elif gid == 'nxt_breakout':
            gain = 0
            for w in _roster(comp):
                gain = max(gain, int(w.get('popularity', 50)) - 70)
            progress = 'Watch rising stars gain popularity through stories'
        else:
            progress = tpl['metric']
        if manual.get(f'{comp}:{gid}') in ('Completed', 'Failed', 'In Progress'):
            result = manual[f'{comp}:{gid}']
        out.append({**tpl, 'result': result, 'progress': progress})
    return out


# ====================================================
# WRESTLER DEVELOPMENT
# ====================================================
def development_label(w):
    pop = int(w.get('popularity', 50)); mom = int(w.get('momentum', 50))
    morale = int(w.get('morale', 50)); ovr = int(w.get('overall', 70))
    booked = w.get('last_booked_week')
    wins = int(w.get('wins', 0)); losses = int(w.get('losses', 0))
    buzz = int(w.get('twitter_buzz', 0) or 0)
    week = int(st.session_state.get('week', 0))
    labels = []
    if pop >= 88 and ovr >= 88: labels.append('Main Event Ready')
    if mom >= 75 and pop < 85: labels.append('Breakout Star')
    if 60 <= mom < 75 and pop < 80: labels.append('Rising Prospect')
    if wins >= 3 and str(w.get('streak', '')).startswith('W'): labels.append('Hot Hand')
    if mom <= 30: labels.append('Cooling Off')
    if buzz >= 60 and morale < 50: labels.append('Overexposed')
    if booked is None and week >= 3: labels.append('Underused')
    if int(w.get('locker_room_reputation', 50)) >= 80: labels.append('Locker Room Leader')
    if int(w.get('sponsor_trust', 50)) >= 80: labels.append('Sponsor Magnet')
    if pop >= 80 and mom >= 65 and int(w.get('title_wins', 0)) == 0: labels.append('Future Champion')
    return labels or ['Steady']


# ====================================================
# TRADE BLOCK + FREE AGENCY INTEREST
# ====================================================
def trade_block_rows():
    ensure_gm_state()
    rows = []
    manual_ids = {t.get('wrestler_id') for t in st.session_state.trade_block}
    for w in st.session_state.get('roster', []):
        wid = w.get('wrestler_id')
        reasons = []
        if wid in manual_ids:
            entry = next(t for t in st.session_state.trade_block if t.get('wrestler_id') == wid)
            reasons.append(entry.get('reason') or 'GM listed')
        if w.get('requested_release'): reasons.append('Requested release')
        if int(w.get('morale', 50)) < 30: reasons.append('Very low morale')
        if int(w.get('booking_satisfaction', 60)) < 30: reasons.append('Unhappy with booking')
        if not reasons:
            continue
        value = round(int(w.get('popularity', 50)) * 0.5 + int(w.get('overall', 70)) * 0.4 + int(w.get('momentum', 50)) * 0.1)
        interested = [c for c in PLAYABLE if c != w.get('company')]
        rec = 'Trade now — value will drop' if int(w.get('morale', 50)) < 25 else ('Hold for a better package' if value >= 75 else 'Listen to offers')
        rows.append({
            'wrestler': w.get('name'), 'wrestler_id': wid, 'brand': w.get('company'),
            'salary': int(w.get('salary', 0)), 'years': int(w.get('contract_length_years', 1)),
            'morale': int(w.get('morale', 50)), 'loyalty': int(w.get('brand_loyalty', 50)),
            'popularity': int(w.get('popularity', 50)), 'trade_value': value,
            'reason': ' · '.join(reasons), 'interested': interested, 'recommendation': rec,
        })
    return sorted(rows, key=lambda x: -x['trade_value'])


BRAND_PITCH = {
    'NXT': 'cinematic stories and media deals',
    'SmackDown': 'mainstream celebrity exposure',
    'WCW': 'sports legitimacy',
}


def fa_interest_rows():
    out = []
    for w in st.session_state.get('free_agency_pool', []) or []:
        if not isinstance(w, dict):
            continue
        pop = int(w.get('popularity', 50))
        fits = {}
        for c in PLAYABLE:
            fit = 50 + random.Random(f"{w.get('name')}{c}").randint(-15, 15)
            if c == w.get('previous_company'): fit += int(w.get('brand_loyalty', 50)) // 5 - 8
            fits[c] = max(5, min(99, fit))
        fav = max(fits, key=fits.get)
        out.append({
            'wrestler': w.get('name'), 'preferred': fav,
            'money_demand': int(w.get('salary_demand', w.get('salary', 500000)) or 500000),
            'creative_demand': w.get('contract_demand', 'Standard deal'),
            'title_demand': 'Yes' if pop >= 82 else 'No',
            'media_interest': 'High' if int(w.get('sponsor_trust', 50)) >= 70 else 'Medium',
            'loyalty_concern': 'Yes' if int(w.get('brand_loyalty', 50)) < 35 else 'No',
            'fits': fits,
            'prediction': f'{fav} is favored because the wrestler wants {BRAND_PITCH[fav]}.',
        })
    return sorted(out, key=lambda x: -x['money_demand'])


# ====================================================
# FAN INTEREST / MARKET SIZE
# ====================================================
MARKETS = {
    'New York': {'size': 'Elite', 'demand': 'High', 'sponsor': 'High', 'risk': 'Expensive', 'sellout': 'Hard but huge payoff'},
    'Los Angeles': {'size': 'Elite', 'demand': 'High', 'sponsor': 'High', 'risk': 'Expensive', 'sellout': 'Hard but huge payoff'},
    'Chicago': {'size': 'Elite', 'demand': 'Very High', 'sponsor': 'High', 'risk': 'Hot crowd, high expectations', 'sellout': 'Likely with a hot story'},
    'Dallas': {'size': 'Large', 'demand': 'High', 'sponsor': 'High', 'risk': 'Stadium-size temptation', 'sellout': 'Good'},
    'Toronto': {'size': 'Large', 'demand': 'High', 'sponsor': 'Medium', 'risk': 'Border travel cost', 'sellout': 'Good'},
    'London': {'size': 'Elite', 'demand': 'Very High', 'sponsor': 'High', 'risk': 'International travel', 'sellout': 'Strong for PLEs'},
    'Tokyo': {'size': 'Large', 'demand': 'High', 'sponsor': 'Medium', 'risk': 'Long travel + jet lag', 'sellout': 'Strong for dream matches'},
    'Atlanta': {'size': 'Large', 'demand': 'High', 'sponsor': 'Medium', 'risk': 'WCW heritage market', 'sellout': 'Good'},
    'Orlando': {'size': 'Medium', 'demand': 'High', 'sponsor': 'Medium', 'risk': 'Low', 'sellout': 'Easier sellout'},
    'Las Vegas': {'size': 'Large', 'demand': 'Medium', 'sponsor': 'High', 'risk': 'Tourist crowd', 'sellout': 'Good for specials'},
}


def market_profile(city):
    c = (city or '').strip()
    if c in MARKETS:
        return {**MARKETS[c], 'city': c}
    return {'city': c or 'Unknown', 'size': 'Medium', 'demand': 'Medium', 'sponsor': 'Medium',
            'risk': 'Lower revenue ceiling', 'sellout': 'Easier sellout'}


# ====================================================
# BRAND POWER RANKINGS
# ====================================================
def brand_power_rankings():
    rows = []
    for c in PLAYABLE:
        ds, _ = dirt_sheet_approval(c)
        chem, _n = locker_chemistry(c)
        shows = [h for h in st.session_state.get('weekly_history', []) if h.get('company') == c]
        avg_rating = _avg([float(h.get('episode_rating') or h.get('final_rating') or 0) for h in shows[-6:]]) if shows else 0
        view = _avg([int(h.get('viewership', 0) or 0) for h in shows[-4:]]) if shows else 0
        objs = [o for o in st.session_state.get('sponsor_objectives', []) if o.get('company') == c]
        done = sum(1 for o in objs if str(o.get('status', '')).lower() in ('completed', 'complete', 'done'))
        score = ds * 0.35 + chem * 0.20 + avg_rating * 10 * 0.25 + min(20, done * 4) + min(10, view / 300000)
        rows.append({'brand': c, 'score': round(score, 1), 'dirt_sheet': ds, 'chemistry': chem,
                     'avg_rating': round(avg_rating, 1), 'sponsor_wins': done, 'viewership': int(view)})
    rows.sort(key=lambda x: -x['score'])
    return rows


# ====================================================
# DIRT SHEET TWEET GENERATION
# ====================================================
def _dirt_texts(comp):
    ss = st.session_state
    week = ss.get('week', 0)
    last = _last_show(comp)
    ds, _hd = dirt_sheet_approval(comp)
    chem, _n = locker_chemistry(comp)
    texts = []
    if last:
        rt = float(last.get('episode_rating') or last.get('final_rating') or 7)
        vn = last.get('venue', 'the arena'); sn = last.get('show_name', f'{comp} TV')
        if rt >= 8.5:
            texts.append(f"{sn} delivered. {rt}/10 with real story logic — {comp} is booking like it matters.")
            texts.append(f"Hearing nothing but praise for {comp} after {sn}. {vn} crowd was molten. {rt}/10 territory.")
        elif rt >= 7:
            texts.append(f"{comp}'s {sn} was solid — {rt}/10. Strong pacing, though the midcard needs direction.")
        else:
            texts.append(f"{comp} has the money, but {sn} felt cold. Big venue, weak emotional hook. {rt}/10.")
            texts.append(f"Rough one for {comp}. {sn} drifted — champions need a reason to be on TV.")
        prof = int(last.get('profit', 0) or 0)
        if prof > 800000:
            texts.append(f"Business note: {comp} cleared a strong number on {sn}. Sponsors noticed.")
        elif prof < -300000:
            texts.append(f"{comp} lost money on {sn}. The sheets say venue size didn't match story heat.")
    if chem < 45:
        texts.append(f"{comp} locker room morale may become a story if booking doesn't change soon.")
        texts.append(f"Stars in {comp} are watching the free agent market closely. Morale is a real concern backstage.")
    elif chem >= 75:
        texts.append(f"Backstage word: {comp}'s locker room chemistry is the best in the league right now.")
    if ds >= 80:
        texts.append(f"{comp} continuity is unmatched right now. Week {week} booking respected every running story.")
    elif ds <= 40:
        texts.append(f"{comp} keeps dropping threads. Fans invested in stories deserve payoffs, not resets.")
    fa = ss.get('free_agency_pool', [])
    if fa:
        big = max(fa, key=lambda w: int(w.get('popularity', 0) or 0), default=None)
        if big and int(big.get('popularity', 0)) >= 75:
            texts.append(f"Rumor mill: every brand wants {big.get('name')}. Bidding war incoming.")
    blocked = trade_block_rows()
    mine = [t for t in blocked if t['brand'] == comp]
    if mine:
        texts.append(f"Hearing {mine[0]['wrestler']} is quietly on the trade block in {comp}. Reason: {mine[0]['reason']}.")
    objs = [o for o in ss.get('sponsor_objectives', []) if o.get('company') == comp]
    done = [o for o in objs if str(o.get('status', '')).lower() in ('completed', 'complete', 'done')]
    if done:
        texts.append(f"Sponsors got what they wanted from {comp} this cycle. Full payout likely on recent activations.")
    appr = ss.get('calendar_approval_results', {}).get(comp)
    if appr:
        texts.append(f"{comp}'s yearly calendar grades a {appr.get('grade','B')} — {appr.get('status','Approved')}. {appr.get('headline','Smart spacing.')}")
    random.shuffle(texts)
    return texts


def post_dirt_sheet_tweets(comp, n=3):
    """Create dirt sheet posts in the shared Twitter feed."""
    make_post = _h('make_twitter_post')
    texts = _dirt_texts(comp)
    posted = 0
    for i, text in enumerate(texts[:n]):
        acct = _account(random.randrange(len(DIRT_ACCOUNTS)))
        if make_post:
            post = make_post(comp, 'media', acct['name'], acct['handle'], 'Wrestling Media',
                             'Dirt Sheet Report', f"{text}"[:280], '',
                             {'topic': 'Wrestling Story', 'tone': 'insider', 'label': 'Dirt Sheet'})
            st.session_state.twitter_posts.insert(0, post)
            posted += 1
    return posted


# ====================================================
# CALENDAR APPROVAL
# ====================================================
def calendar_approval(entries, comp=None):
    ensure_gm_state()
    entries = [e for e in (entries or []) if not comp or e.get('company') == comp]
    if not entries:
        return {'grade': '—', 'status': 'Needs Fixes', 'headline': 'No calendar entries to review.',
                'conflicts': [], 'warnings': ['Add shows in Plan Schedule first.'], 'notes': [],
                'scores': {}, 'dirt_sheet': 'Main Event Metrics: No schedule filed. Nothing to grade.'}
    conflicts, warnings, notes = [], [], []
    by_date = {}
    for e in entries:
        d = str(e.get('date') or '')
        co = e.get('company', '')
        wk = int(e.get('week', 0) or 0)
        if d:
            key = (co, d)
            if key in by_date:
                conflicts.append(f"{co} has two shows on {d} (Week {wk} + Week {by_date[key]}) — same exact date is blocked.")
            else:
                by_date[key] = wk
    venue_dates = {}
    for e in entries:
        d = str(e.get('date') or '')
        v = e.get('venue', '')
        if d and v:
            key = (v, d)
            if key in venue_dates and venue_dates[key] != e.get('company'):
                conflicts.append(f"{v} is double-booked on {d} by {venue_dates[key]} and {e.get('company')}.")
            venue_dates[key] = e.get('company')
    cross = {}
    for e in entries:
        d = str(e.get('date') or '')
        if d:
            cross.setdefault(d, []).append(e.get('company'))
    for d, cos in cross.items():
        if len(set(cos)) > 1:
            warnings.append(f"Two brands run on {d} ({', '.join(sorted(set(cos)))}) — needs Admin override if intentional.")

    ples = sorted([int(e.get('week', 0)) for e in entries if 'PLE' in str(e.get('show_type', ''))])
    ple_score = 80
    for a, b in zip(ples, ples[1:]):
        gap = b - a
        if gap < 3:
            warnings.append(f'PLEs at Week {a} and Week {b} are only {gap} week(s) apart — builds will feel rushed.')
            ple_score -= 12
        elif gap > 10:
            notes.append(f'Long gap between PLEs (Week {a} → {b}) — fill with a TV special to hold momentum.')
            ple_score -= 4
    intl_run, travel_score = 0, 85
    for e in sorted(entries, key=lambda x: int(x.get('week', 0))):
        if e.get('country') and e.get('country') != 'United States':
            intl_run += 1
            if intl_run >= 2:
                warnings.append(f"Back-to-back international weeks around Week {e.get('week')} — travel costs stack.")
                travel_score -= 10
        else:
            intl_run = 0
    exp = [e for e in entries if int(e.get('projected_profit_loss', 0) or 0) < -500000]
    biz_score = 85 - len(exp) * 10
    for e in exp:
        warnings.append(f"Week {e.get('week')} ({e.get('venue','venue')}) projects a heavy loss — downsize or build the story harder.")
    cities = [e.get('city', '') for e in entries if e.get('city')]
    repeats = {c: cities.count(c) for c in set(cities) if cities.count(c) >= 4}
    for c, n in repeats.items():
        notes.append(f'{c} appears {n} times — fans may want more variety.')
    venue_score = 80
    for e in entries:
        cap = int(e.get('capacity', 0) or 0)
        pct = int(e.get('projected_sellout_pct', 0) or 0)
        if cap >= 40000 and pct and pct < 55:
            warnings.append(f"Week {e.get('week')}: {e.get('venue','Stadium')} may be too big for projected demand ({pct}% sellout).")
            venue_score -= 8
    sponsor_score = min(95, 60 + len([e for e in entries if 'PLE' in str(e.get('show_type', ''))]) * 5)

    total = ple_score * 0.25 + travel_score * 0.2 + biz_score * 0.25 + venue_score * 0.2 + sponsor_score * 0.1
    total -= len(conflicts) * 15
    total = max(0, min(100, total))
    if conflicts: status = 'Blocked Conflict'
    elif total >= 80 and not warnings: status = 'Approved'
    elif total >= 60: status = 'Approved With Warnings'
    else: status = 'Needs Fixes'
    grade = ('A+' if total >= 93 else 'A' if total >= 88 else 'A-' if total >= 83 else 'B+' if total >= 78
             else 'B' if total >= 72 else 'B-' if total >= 66 else 'C+' if total >= 60 else 'C' if total >= 50 else 'D')
    if status == 'Approved':
        headline = 'The schedule is strong — good spacing, no same-day conflicts, smart venues.'
        ds_react = f"{_account(0)['name']}: This is a smart calendar. Strong pacing, big market placement, and no obvious scheduling disaster."
    elif status == 'Approved With Warnings':
        headline = 'Solid plan with a few risks worth fixing before locking.'
        ds_react = f"{_account(8)['name']}: {comp or 'This'} schedule has smart spacing overall — a couple of risky weeks, but approved."
    elif status == 'Blocked Conflict':
        headline = 'Same-date conflicts must be fixed before this calendar can be approved.'
        ds_react = f"{_account(2)['name']}: Someone double-booked a date. Sheets are laughing — fix it before the fans do."
    else:
        headline = 'Too many risks — rework venues, spacing, or budgets.'
        ds_react = f"{_account(6)['name']}: This calendar needs another pass. Costs and spacing don't add up yet."
    return {
        'grade': grade, 'status': status, 'headline': headline,
        'conflicts': conflicts, 'warnings': warnings, 'notes': notes,
        'scores': {'PLE spacing': round(ple_score), 'Travel': round(travel_score),
                   'Business risk': round(biz_score), 'Venue logic': round(venue_score),
                   'Sponsor opportunity': round(sponsor_score), 'Overall': round(total)},
        'dirt_sheet': ds_react,
        'reviewed_at': datetime.now().isoformat(timespec='seconds'),
    }


# ====================================================
# WEEKLY MEDIA QUESTIONS
# ====================================================
RESPONSE_STYLES = ['Confident', 'Humble', 'Defensive', 'Honest', 'Blame Creative',
                   'Protect Wrestler', 'Call Out Rival Brand', 'Promise Better Show']

RESPONSE_EFFECTS = {
    'Confident': {'fan': 2, 'owner': 2, 'morale': 1, 'note': 'Fans respect the swagger.'},
    'Humble': {'fan': 2, 'owner': 1, 'morale': 2, 'note': 'Locker room appreciates honesty.'},
    'Defensive': {'fan': -2, 'owner': -1, 'morale': 0, 'note': 'Sheets smell blood when GMs get defensive.'},
    'Honest': {'fan': 3, 'owner': 1, 'morale': 1, 'note': 'Honesty buys patience.'},
    'Blame Creative': {'fan': -1, 'owner': -3, 'morale': -3, 'note': 'Throwing creative under the bus hurts trust.'},
    'Protect Wrestler': {'fan': 1, 'owner': 0, 'morale': 4, 'note': 'The locker room notices who protects them.'},
    'Call Out Rival Brand': {'fan': 3, 'owner': -1, 'morale': 1, 'note': 'Fans love brand war heat; owners get nervous.'},
    'Promise Better Show': {'fan': 1, 'owner': 1, 'morale': 0, 'note': 'Now you have to deliver.'},
}


def media_questions_for(comp):
    last = _last_show(comp)
    week = st.session_state.get('week', 0)
    qs = []
    if last:
        rt = float(last.get('episode_rating') or last.get('final_rating') or 7)
        champs = st.session_state.get('champions', {}).get(comp, {})
        main_champ = next(iter(champs.values()), '')
        feat = last.get('featured_star', '')
        if main_champ and main_champ not in str(last.get('matches', '')) + str(feat):
            qs.append(f'Why did you leave your champion {main_champ} off the show?')
        if rt < 6.5:
            qs.append(f"{last.get('show_name','The show')} rated {rt}/10 — what went wrong this week?")
        if int(last.get('profit', 0) or 0) > 500000 and rt < 7:
            qs.append(f'{comp} made money, but did the story actually connect?')
    objs = [o for o in st.session_state.get('sponsor_objectives', []) if o.get('company') == comp]
    failed = [o for o in objs if str(o.get('status', '')).lower() == 'failed']
    if failed:
        qs.append(f'Are you worried about {comp} missing another sponsor objective?')
    chem, _n = locker_chemistry(comp)
    if chem < 45:
        qs.append('Locker room sources describe morale as fragile. How do you respond?')
    if comp == 'NXT':
        qs.append('Is NXT becoming too media-focused and not wrestling-focused?')
    elif comp == 'SmackDown':
        qs.append('Does SmackDown lean too hard on celebrity moments instead of wrestling?')
    else:
        qs.append('WCW promises sports legitimacy — does this week prove it?')
    qs.append(f'What is the plan for Week {week + 1}?')
    answered = {m.get('question') for m in st.session_state.get('media_question_log', [])
                if m.get('company') == comp and m.get('week') == week}
    return [q for q in qs if q not in answered][:4]


def apply_media_response(comp, question, style):
    ensure_gm_state()
    eff = RESPONSE_EFFECTS.get(style, RESPONSE_EFFECTS['Honest'])
    st.session_state.gm_trust_adj[comp] = max(-25, min(25, st.session_state.gm_trust_adj.get(comp, 0) + eff['owner']))
    st.session_state.locker_chem_adj[comp] = max(-25, min(25, st.session_state.locker_chem_adj.get(comp, 0) + eff['morale']))
    st.session_state.dirt_sheet_adj[comp] = max(-25, min(25, st.session_state.dirt_sheet_adj.get(comp, 0) + eff['fan']))
    st.session_state.media_question_log.insert(0, {
        'week': st.session_state.get('week', 0), 'company': comp,
        'question': question, 'style': style, 'outcome': eff['note'],
        'at': datetime.now().isoformat(timespec='seconds'),
    })
    return eff['note']


# ====================================================
# UI — WEEKLY PULSE (Weekly Performance embed)
# ====================================================
def render_weekly_pulse(comp):
    if comp not in PLAYABLE:
        return
    ensure_gm_state()
    card = _h('bfg_card')
    ds, head = dirt_sheet_approval(comp)
    trust, _f = gm_trust(comp)
    chem, _n = locker_chemistry(comp)
    with st.container(border=True):
        st.markdown(f"##### 📰 GM Pulse — {comp}")
        c1, c2, c3 = st.columns(3)
        c1.metric('Dirt Sheet Approval', f'{ds}/100')
        c2.metric('Owner Confidence', f'{trust}/100')
        c3.metric('Locker Chemistry', f'{chem}/100')
        st.caption(f'**Headline:** “{head}”')
        qs = media_questions_for(comp)
        if qs:
            with st.expander(f'🎙 Weekly media questions ({len(qs)})', expanded=False):
                q = st.selectbox('Question', qs, key=f'mq_q_{comp}')
                style = st.selectbox('Response style', RESPONSE_STYLES, key=f'mq_s_{comp}')
                if st.button('Answer the press', key=f'mq_go_{comp}'):
                    note = apply_media_response(comp, q, style)
                    save = _h('save_universe')
                    if save:
                        try: save()
                        except Exception: pass
                    st.success(f'Answered ({style}). {note}')
                    st.rerun()


# ====================================================
# UI — DIRT SHEET TAB (Twitter embed)
# ====================================================
ACCOUNT_BADGES = {
    'Dave Meltz': ('ANALYTICAL', '#7fb0ff'),
    'The Wrestling Observer Room': ('INSIDER', '#7fb0ff'),
    'Ringside Radar': ('REVIEW', '#cf8aff'),
    'Pro Graps Insider': ('SCOOP', '#ff8a5c'),
    'The Locker Room Leak': ('RUMOR', '#ff5c5c'),
    'Kayfabe Report': ('STORY', '#cf8aff'),
    'Fight Desk Daily': ('BUSINESS', '#3dd68c'),
    'The Dirt Sheet Doctor': ('HOT TAKE', '#f1c440'),
    'Main Event Metrics': ('NUMBERS', '#d4d4dc'),
    'Heat Check Wrestling': ('HEAT CHECK', '#f1c440'),
}


def _html_escape(s):
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def render_dirt_card(p):
    raw = p.get('wrestler', '')
    orig = next((a['name'] for a in DIRT_ACCOUNTS
                 if st.session_state.get('dirt_sheet_names', {}).get(a['name'], a['name']) == raw or a['name'] == raw), raw)
    badge, color = ACCOUNT_BADGES.get(orig, ('REPORT', '#9aa0a6'))
    st.markdown(
        f"<div class='ds-card' style='--ds-accent:{color}'>"
        f"<span class='ds-acct'>{_html_escape(raw)}</span><span class='ds-handle'>{_html_escape(p.get('handle',''))}</span> "
        f"<span class='bfg-badge gray' style='color:{color};border-color:{color}66;background:{color}1a'>{badge}</span>"
        f"<div class='ds-meta'>{_html_escape(p.get('company',''))} · Week {p.get('week','—')} · {_html_escape(p.get('post_type','Dirt Sheet Report'))}</div>"
        f"<div class='ds-text'>{_html_escape(p.get('text',''))}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_dirt_sheet_tab(comp):
    ensure_gm_state()
    st.caption('Fictional wrestling media — rumors, ratings talk, calendar reviews, and backstage notes. Rename any account below.')
    ds, head = dirt_sheet_approval(comp)
    c1, c2 = st.columns([1, 2.2])
    c1.metric(f'{comp} Dirt Sheet Approval', f'{ds}/100')
    c2.markdown(f"**This week's sheet headline:**\n\n“{head}”")
    g1, g2, g3 = st.columns(3)
    if g1.button('📰 Generate 3 dirt sheet posts', key='dsh_gen3', type='primary'):
        n = post_dirt_sheet_tweets(comp, 3)
        st.toast(f'{n} dirt sheet post(s) hit the timeline.')
        st.rerun()
    if g2.button('🔥 Full media cycle (6 posts)', key='dsh_gen6'):
        n = post_dirt_sheet_tweets(comp, 6)
        st.toast(f'{n} dirt sheet post(s) hit the timeline.')
        st.rerun()
    if g3.button('🏆 League-wide reactions', key='dsh_genall'):
        total = sum(post_dirt_sheet_tweets(c, 2) for c in PLAYABLE)
        st.toast(f'{total} posts across all brands.')
        st.rerun()
    feed = [p for p in st.session_state.get('twitter_posts', []) if p.get('role') == 'Wrestling Media'][:14]
    if feed:
        st.markdown('###### Latest from the sheets')
        for p in feed:
            render_dirt_card(p)
    else:
        st.info('No dirt sheet posts yet — generate some above.')
    with st.expander('Rename dirt sheet accounts', expanded=False):
        names = st.session_state.dirt_sheet_names
        for a in DIRT_ACCOUNTS:
            names[a['name']] = st.text_input(a['handle'], value=names.get(a['name'], a['name']), key=f"dsn_{a['handle']}")


# ====================================================
# UI — CALENDAR APPROVAL PANEL (Calendar embed)
# ====================================================
def render_calendar_approval_panel():
    ensure_gm_state()
    st.markdown('##### ✅ AI Calendar Approval')
    st.caption('PLEs and weekly shows CAN share a week on different days. Only exact same-date conflicts block approval.')
    target = st.radio('Review scope', ['All'] + PLAYABLE, horizontal=True, key='cal_appr_scope')
    if st.button('Run Calendar Approval', key='cal_appr_run', type='primary'):
        comp = None if target == 'All' else target
        result = calendar_approval(st.session_state.get('schedule_calendar', []), comp)
        st.session_state.calendar_approval_results[target] = result
        save = _h('save_universe')
        if save:
            try: save()
            except Exception: pass
        st.rerun()
    result = st.session_state.calendar_approval_results.get(target)
    if not result:
        st.info('Run approval to grade the schedule, surface conflicts, and get a dirt sheet reaction.')
        return
    status_icon = {'Approved': '🟢', 'Approved With Warnings': '🟡', 'Needs Fixes': '🟠', 'Blocked Conflict': '🔴'}.get(result['status'], '⚪')
    c1, c2, c3 = st.columns([1, 1.4, 2.6])
    c1.metric('Calendar Grade', result['grade'])
    c2.metric('Status', f"{status_icon} {result['status']}")
    with c3:
        st.markdown(f"**AI Notes:** “{result['headline']}”")
        st.caption(f"Reviewed {result.get('reviewed_at','')}")
    sc = result.get('scores', {})
    if sc:
        cols = st.columns(len(sc))
        for col, (k, v) in zip(cols, sc.items()):
            col.metric(k, f'{v}')
    if result['conflicts']:
        st.error('**Blocked conflicts:**\n\n' + '\n'.join(f'- {c}' for c in result['conflicts']))
    if result['warnings']:
        with st.expander(f"⚠️ Warnings ({len(result['warnings'])})", expanded=result['status'] != 'Approved'):
            for w in result['warnings']:
                st.write('• ' + w)
    if result['notes']:
        with st.expander(f"💡 Recommendations ({len(result['notes'])})", expanded=False):
            for n in result['notes']:
                st.write('• ' + n)
    st.markdown(f"📰 **Dirt Sheet Reaction:** “{result['dirt_sheet']}”")


# ====================================================
# UI — GM HUB PAGE (5 Pillars)
# ====================================================
def render_gm_hub():
    ensure_gm_state()
    shell = _h('render_page_shell')
    if shell:
        comp = shell('GM Hub', subtitle='The 5 Pillars — Owner Goals · GM Trust · Locker Chemistry · Development · Dirt Sheet Approval.', use_brand_tabs=True, tabs_label='Brand', show_meter=True)
    else:
        st.title('GM Hub')
        comp = st.radio('Brand', PLAYABLE, horizontal=True, key='gmhub_brand')
    money = _h('money', lambda v: f'${v:,.0f}')

    # ----- 5 PILLARS BANNER -----
    ds, head = dirt_sheet_approval(comp)
    trust, factors = gm_trust(comp)
    chem, chem_notes = locker_chemistry(comp)
    goals = evaluate_owner_goals(comp)
    done_goals = sum(1 for g in goals if g['result'] == 'Completed')
    devs = [w for w in _roster(comp) if 'Breakout Star' in development_label(w) or 'Rising Prospect' in development_label(w)]
    tier, tier_note = trust_tier(trust)

    st.markdown('#### 🏛 The 5 Pillars')
    p1, p2, p3, p4, p5 = st.columns(5)
    p1.metric('1 · Owner Goals', f'{done_goals}/{len(goals)}', help='Seasonal goals completed')
    p2.metric('2 · GM Trust', f'{trust}/100', help=tier_note)
    p3.metric('3 · Chemistry', f'{chem}/100')
    p4.metric('4 · Development', f'{len(devs)} rising', help='Breakout stars + rising prospects')
    p5.metric('5 · Dirt Sheet', f'{ds}/100')
    st.caption(f'**Owner status: {tier}** — {tier_note} · Sheet headline: “{head}”')

    tabs = st.tabs(['Owner Goals', 'GM Trust', 'Chemistry', 'Development', 'Trade Block',
                    'FA Interest', 'Markets', 'Media Room', 'Brand Rankings'])

    # ----- OWNER GOALS -----
    with tabs[0]:
        st.caption(f'{comp} seasonal goals — rewards on completion, owner pressure on failure.')
        for g in goals:
            icon = {'Completed': '✅', 'Failed': '❌'}.get(g['result'], '🔄')
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"**{icon} {g['goal']}**")
                c1.caption(f"{g['metric']} · _{g['progress']}_")
                pick = c2.selectbox('Status', ['Auto', 'Completed', 'In Progress', 'Failed'],
                                    key=f"og_{comp}_{g['id']}",
                                    index=0)
                if pick != 'Auto':
                    st.session_state.gm_owner_goal_status[f"{comp}:{g['id']}"] = pick
                else:
                    st.session_state.gm_owner_goal_status.pop(f"{comp}:{g['id']}", None)
        st.caption('Rewards: owner confidence ↑ · bonus budget · sponsor confidence · morale · prestige. '
                   'Failures: confidence ↓ · pressure · budget restrictions · dirt sheet criticism.')

    # ----- GM TRUST -----
    with tabs[1]:
        st.metric(f'{comp} GM Trust / Owner Confidence', f'{trust}/100', tier)
        st.progress(trust / 100)
        st.markdown('**What the owner is weighing:**')
        for f in factors:
            st.write('• ' + f)
        st.markdown('**Goes up when:** strong stories · continuity · sponsor wins · profitable booking · great PLEs · stars built · approved calendar.')
        st.markdown('**Goes down when:** dropped stories · failed sponsors · money collapses · morale drops · stars leave · messy schedule.')
        if trust < 35:
            st.error('🔥 HOT SEAT — owner warnings active. Expect budget limits and forced objectives until trust recovers.')

    # ----- CHEMISTRY -----
    with tabs[2]:
        st.metric(f'{comp} Locker Room Chemistry', f'{chem}/100')
        st.progress(chem / 100)
        for n in chem_notes:
            st.write('• ' + n)
        if chem >= 75:
            st.success('High chemistry: better promos and matches, morale boost, lower walkout risk, higher loyalty.')
        elif chem < 45:
            st.warning('Low chemistry: bad tweets, contract issues, walkout and free agency risk, sponsor concern.')
        unhappy = sorted(_roster(comp), key=lambda w: w.get('morale', 50))[:5]
        if unhappy:
            st.markdown('**Watch list (lowest morale):**')
            for w in unhappy:
                st.write(f"• **{w.get('name')}** — morale {w.get('morale',50)} · booking {w.get('booking_satisfaction',60)} · loyalty {w.get('brand_loyalty',50)}")

    # ----- DEVELOPMENT -----
    with tabs[3]:
        st.caption('Madden/2K-style development — wrestling version. Labels update live from stories, matches, buzz, and booking.')
        flt = st.selectbox('Filter label', ['All', 'Breakout Star', 'Rising Prospect', 'Main Event Ready', 'Hot Hand',
                                            'Cooling Off', 'Overexposed', 'Underused', 'Locker Room Leader',
                                            'Sponsor Magnet', 'Future Champion'], key=f'dev_flt_{comp}')
        rows = []
        for w in sorted(_roster(comp), key=lambda x: -int(x.get('momentum', 50))):
            labels = development_label(w)
            if flt != 'All' and flt not in labels:
                continue
            rows.append((w, labels))
        st.caption(f'{len(rows)} wrestler(s)')
        for w, labels in rows[:30]:
            with st.container(border=True):
                c1, c2 = st.columns([2.4, 1.6])
                c1.markdown(f"**{w.get('name')}** — {' · '.join(labels)}")
                c1.caption(f"OVR {w.get('overall',70)} · Pop {w.get('popularity',50)} · Mom {w.get('momentum',50)} · Morale {w.get('morale',50)} · Stamina {w.get('stamina',85)} · Loyalty {w.get('brand_loyalty',50)}")
                focus = c2.selectbox('Dev focus', ['None', 'Mic skill', 'Ring skill', 'Charisma', 'Media value', 'Sponsor value', 'Story value'],
                                     key=f"devf_{w.get('wrestler_id', w.get('name'))}",
                                     index=0)
                if focus != 'None':
                    st.session_state.dev_focus[w.get('wrestler_id', w.get('name'))] = focus

    # ----- TRADE BLOCK -----
    with tabs[4]:
        st.caption('Wrestlers on the block — listed by GMs or flagged by morale, release requests, and booking unhappiness.')
        add_pool = [w.get('name') for w in _roster(comp)]
        ac1, ac2, ac3 = st.columns([2, 2, 1])
        pick = ac1.selectbox('List a wrestler', [''] + add_pool, key=f'tb_add_{comp}')
        reason = ac2.text_input('Reason on block', key=f'tb_reason_{comp}', placeholder='e.g. salary dump, fresh start')
        if ac3.button('Add to block', key=f'tb_go_{comp}') and pick:
            w = next((x for x in _roster(comp) if x.get('name') == pick), None)
            if w and not any(t.get('wrestler_id') == w.get('wrestler_id') for t in st.session_state.trade_block):
                st.session_state.trade_block.append({'wrestler_id': w.get('wrestler_id'), 'name': pick,
                                                     'company': comp, 'reason': reason or 'GM listed',
                                                     'added_week': st.session_state.get('week', 0)})
                save = _h('save_universe')
                if save:
                    try: save()
                    except Exception: pass
                st.rerun()
        rows = trade_block_rows()
        if not rows:
            st.info('Trade block is empty — list someone above, or it auto-fills when wrestlers get unhappy.')
        for t in rows:
            with st.container(border=True):
                c1, c2, c3 = st.columns([2.2, 1.6, 1.2])
                c1.markdown(f"**{t['wrestler']}** ({t['brand']}) — value **{t['trade_value']}**")
                c1.caption(f"Reason: {t['reason']}")
                c2.caption(f"{money(t['salary'])}/yr · {t['years']}y · morale {t['morale']} · loyalty {t['loyalty']} · pop {t['popularity']}")
                c2.caption(f"Interested: {', '.join(t['interested'])}")
                c3.markdown(f"_AI: {t['recommendation']}_")
                if t['wrestler_id'] in {x.get('wrestler_id') for x in st.session_state.trade_block}:
                    if c3.button('Remove', key=f"tb_rm_{t['wrestler_id']}"):
                        st.session_state.trade_block = [x for x in st.session_state.trade_block if x.get('wrestler_id') != t['wrestler_id']]
                        st.rerun()
        st.caption('Make actual trades in **Trade Center** — this board is the scouting layer.')

    # ----- FA INTEREST -----
    with tabs[5]:
        st.caption('Free Agency Interest Board — who wants whom, and why. Sign in **Free Agency**.')
        rows = fa_interest_rows()
        if not rows:
            st.info('No free agents right now — the board fills when contracts expire or stars hit the market.')
        for r in rows[:20]:
            with st.container(border=True):
                c1, c2 = st.columns([2.4, 1.6])
                c1.markdown(f"**{r['wrestler']}** — prefers **{r['preferred']}**")
                c1.caption(f"Demand {money(r['money_demand'])} · {r['creative_demand']} · Title demand: {r['title_demand']} · Media: {r['media_interest']} · Loyalty concern: {r['loyalty_concern']}")
                fits = ' · '.join(f"{c} {v}" for c, v in sorted(r['fits'].items(), key=lambda x: -x[1]))
                c2.caption(f'Brand fit: {fits}')
                c2.markdown(f"_AI: {r['prediction']}_")

    # ----- MARKETS -----
    with tabs[6]:
        st.caption('Fan interest and market size — scout cities before booking the calendar.')
        cities = sorted(set(list(MARKETS.keys()) + [e.get('city') for e in st.session_state.get('schedule_calendar', []) if e.get('city')]))
        city = st.selectbox('City', cities, key='mkt_city')
        m = market_profile(city)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric('Market Size', m['size'])
        c2.metric('Wrestling Demand', m['demand'])
        c3.metric('Sponsor Value', m['sponsor'])
        c4.metric('Sellout Outlook', m['sellout'][:18])
        st.caption(f"**Risk:** {m['risk']}")
        st.markdown('###### Elite markets at a glance')
        for name, mm in MARKETS.items():
            st.write(f"• **{name}** — {mm['size']} market · demand {mm['demand']} · sponsor {mm['sponsor']} · {mm['risk']}")

    # ----- MEDIA ROOM -----
    with tabs[7]:
        st.caption('Weekly media questions — your answers move morale, fans, owner confidence, and the sheets.')
        qs = media_questions_for(comp)
        if qs:
            q = st.selectbox("This week's question", qs, key=f'mr_q_{comp}')
            style = st.selectbox('Response style', RESPONSE_STYLES, key=f'mr_s_{comp}')
            eff = RESPONSE_EFFECTS[style]
            st.caption(f"Effect preview: fans {eff['fan']:+d} · owner {eff['owner']:+d} · morale {eff['morale']:+d} — {eff['note']}")
            if st.button('Give the answer', key=f'mr_go_{comp}', type='primary'):
                note = apply_media_response(comp, q, style)
                save = _h('save_universe')
                if save:
                    try: save()
                    except Exception: pass
                st.success(f'Press conference done ({style}). {note}')
                st.rerun()
        else:
            st.info('No open questions this week — run a show and the press will line up.')
        log = [m for m in st.session_state.get('media_question_log', []) if m.get('company') == comp][:10]
        if log:
            st.markdown('###### Press history')
            for m in log:
                st.write(f"• W{m['week']} — “{m['question']}” → **{m['style']}** ({m['outcome']})")

    # ----- BRAND RANKINGS -----
    with tabs[8]:
        st.caption('Brand Power Rankings — story quality, continuity, sponsors, chemistry, and performance. Not just money.')
        rows = brand_power_rankings()
        for i, r in enumerate(rows, 1):
            medal = {1: '🥇', 2: '🥈', 3: '🥉'}.get(i, f'{i}.')
            with st.container(border=True):
                c1, c2 = st.columns([1.8, 2.2])
                c1.markdown(f"### {medal} {r['brand']} — {r['score']}")
                c2.caption(f"Dirt sheet {r['dirt_sheet']} · chemistry {r['chemistry']} · avg rating {r['avg_rating']}/10 · sponsor wins {r['sponsor_wins']} · viewership {r['viewership']:,}")
        if st.button('📰 Dirt sheet reacts to the rankings', key='bpr_dirt'):
            top = rows[0]['brand']
            acct = _account(3)
            make_post = _h('make_twitter_post')
            if make_post:
                text = f"{top} is number one this week because their story continuity is unmatched."
                post = make_post(top, 'media', acct['name'], acct['handle'], 'Wrestling Media',
                                 'Dirt Sheet Report', text, '', {'topic': 'Wrestling Story', 'tone': 'insider', 'label': 'Dirt Sheet'})
                st.session_state.twitter_posts.insert(0, post)
                st.toast('Rankings reaction posted to the timeline.')
