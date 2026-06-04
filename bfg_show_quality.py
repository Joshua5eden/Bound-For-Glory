"""Dynamic show quality economics, sellout bonuses, champion usage, sponsor ads, and descriptor generation."""
import random
import streamlit as st

PLAYABLE = ['NXT', 'SmackDown', 'WCW']
CHAMP_PLACEHOLDERS = ('Vacant', 'Place Holder', 'TBD - Tournament', 'TBD - Title Match', 'None', '')

SELLOUT_TICKET_MULT = {
    'Sellout': 1.20, 'Near Sellout': 1.12, 'Strong Crowd': 1.05, 'Good Crowd': 1.0,
    'Soft Crowd': 0.95, 'Weak Attendance': 0.85,
}
SELLOUT_MERCH_MULT = {
    'Sellout': 1.15, 'Near Sellout': 1.08, 'Strong Crowd': 1.05, 'Good Crowd': 1.0,
    'Soft Crowd': 0.95, 'Weak Attendance': 1.0,
}
SELLOUT_SPONSOR_CONF = {
    'Sellout': 10, 'Near Sellout': 5, 'Strong Crowd': 0, 'Good Crowd': 0,
    'Soft Crowd': 0, 'Weak Attendance': -10,
}

SPONSOR_AD_TYPES = [
    '15-second ad read', '30-second commercial', 'sponsored backstage segment',
    'branded entrance package', 'sponsored replay', 'sponsored match graphic',
    'social media ad', 'YouTube trailer ad', 'red carpet ad', 'halftime ad',
    'arena video board ad', 'sponsor challenge', 'product placement', 'merch ad',
    'trading card ad', 'toy launch ad', 'streaming special ad',
]

BRAND_AD_STYLES = {
    'NXT': [
        'Apple Vision Pro immersive promo', 'Google/YouTube trailer premiere',
        'HBO Max Road To Bound For Glory ad', 'Netflix documentary teaser',
        'Rockstar / NXT: Rise to Glory game trailer', 'Crunchyroll anime opening ad',
        'Red Bull stunt feature', 'Delta global arrival ad', 'Mattel / DC merch commercial',
    ],
    'SmackDown': [
        'PRIME viral challenge', 'Sony Music artist crossover commercial',
        'Paramount Plus countdown special ad', 'New Balance sneaker drop ad',
        'Hasbro action figure commercial', 'Bandai Namco fighting game trailer',
        'Grammys red carpet sponsor spot', 'music video release promo',
    ],
    'WCW': [
        'EA Sports ratings reveal', 'Microsoft sports analytics replay',
        'Pepsi halftime sponsor spot', 'Gatorade performance feature',
        'Funko figure drop commercial', 'Topps/Panini trading card launch',
        'ESPN/CBS big-fight promo', 'NBA/NFL stadium board ad',
    ],
}

# Descriptor banks — mixed dynamically; not one billion hardcoded lines.
DESCRIPTOR_BANKS = {
    'wrestling': [
        'blood-feud', 'grudge-match', 'money-drawing', 'crowd-hooking', 'heat-heavy', 'promo-driven',
        'bell-to-bell', 'spot-heavy', 'psychology-rich', 'old-school', 'new-school', 'strong-style',
        'sports-entertainment-heavy', 'workrate-focused', 'angle-driven', 'character-first', 'belt-centered',
        'faction-fueled', 'betrayal-loaded', 'revenge-driven', 'redemption-heavy', 'underdog-coded',
        'monster-push', 'star-making', 'title-elevating', 'division-carrying', 'locker-room-shaking',
        'fanbase-splitting', 'dirt-sheet-friendly', 'go-home-ready', 'fallout-worthy', 'swerve-heavy',
        'finish-heavy', 'clean-finish', 'dirty-finish', 'protected-loss', 'statement-win', 'momentum-reset',
        'momentum-spike', 'heat-magnet', 'babyface-making', 'heel-solidifying', 'crowd-turning',
        'chant-starting', 'arena-rocking', 'merch-line-moving', 'ratings-bumping', 'gate-driving',
        'sponsor-safe', 'sponsor-dangerous', 'continuity-saving', 'continuity-breaking', 'payoff-worthy',
        'slow-burn-approved', 'flashpoint moment', 'rivalry escalator', 'championship stabilizer',
        'main-event audition', 'PLE-sealing segment', 'brand-saving promo', 'money promo', 'hot-match payoff',
        'storyline insurance', 'world-title gravity', 'Ultimate-X energy', 'Anarchy-level chaos',
        'arena-wide brawl', 'stadium-scale fight',
    ],
    'outside': [
        'box-office', 'prestige-TV', 'award-season', 'streaming-era', 'algorithm-friendly', 'viral-ready',
        'headline-driven', 'brand-safe', 'brand-risky', 'investor-friendly', 'advertiser-friendly',
        'premium-content', 'must-stream', 'must-watch', 'appointment-TV', 'watercooler', 'social-first',
        'broadcast-polished', 'marketable', 'commercially sharp', 'culturally loud', 'media-savvy',
        'sponsor-ready', 'sports-legitimate', 'analytics-friendly', 'tech-powered', 'music-video-coded',
        'red-carpet-polished', 'fashion-forward', 'collector-ready', 'toy-aisle-ready', 'game-trailer-ready',
        'documentary-worthy', 'stadium-friendly', 'arena-tested', 'franchise-building', 'global-facing',
        'youth-market', 'mainstream-friendly', 'niche-burning', 'fan-service-heavy', 'internet-proof',
        'controversy-proof', 'risk-loaded', 'high-upside', 'high-risk', 'low-risk', 'premium-feeling',
        'luxury-coded', 'street-level', 'grassroots', 'cult-favorite', 'mass-market', 'cross-platform',
        'multi-screen', 'eventized', 'commercially explosive', 'attention-economy', 'culture-driving',
        'sponsor-magnetic', 'brand-expanding', 'market-moving', 'audience-growing', 'reputation-building',
    ],
    'sellout': [
        'sold-out spectacle', 'standing-room-only energy', 'packed-house pressure', 'capacity-shaking crowd',
        'wall-to-wall attendance', 'arena-bursting turnout', 'box-office sellout', 'crowd-packed heater',
        'no-seat-left atmosphere', 'sellout statement', 'ticket-demand explosion', 'arena-maxed moment',
        'full-house frenzy',
    ],
    'near_sellout': [
        'near-sellout surge', 'almost-packed arena', 'heavy crowd demand', 'strong gate energy',
        'hot-ticket night', 'almost-capacity crowd', 'big-market pull', 'ticket-sales heater',
        'premium crowd turnout', 'packed-feeling building',
    ],
    'strong_crowd': [
        'healthy crowd', 'strong live gate', 'loud building', 'solid arena energy', 'engaged crowd',
        'business-positive crowd', 'good ticket movement', 'crowd held up strong', 'fanbase showed out',
    ],
    'weak_attendance': [
        'soft gate', 'empty-seat concern', 'attendance drag', 'weak crowd optics', 'low-demand night',
        'ticket-sales warning', 'half-full feeling', 'bad market response', 'crowd energy problem',
        'venue mismatch', 'cold market night',
    ],
    'stadium': [
        'stadium-sized spectacle', 'big-game atmosphere', 'mega-event scale', 'open-air pressure',
        'massive venue gamble', 'stadium gamble', 'supercard energy', 'sports-entertainment spectacle',
        'city-wide event', 'festival-sized crowd', 'major-market play', 'mega-gate opportunity',
        'large-scale presentation',
    ],
    'main_event': [
        'championship-caliber main event', 'title-scene-defining main event', 'main-event-worthy closer',
        'money-match closer', 'PLE-level main event', 'world-title atmosphere', 'champion-driven finale',
        'headline-worthy closer', 'storyline-closing main event', 'crowd-erupting finale',
        'rivalry-defining main event', 'prestige-heavy closer', 'high-pressure championship moment',
        'box-office main event', 'brand-carrying main event', 'main-event masterpiece',
        'champion showcase', 'title prestige showcase', 'final-segment heater', 'go-home closing angle',
        'ratings-closing segment', 'statement main event', 'legacy-building closer',
        'sponsor-friendly finale', 'fan-investment closer',
    ],
    'champion_pos': [
        'champion spotlight', 'title-holder presence', 'gold-centered segment', 'championship aura',
        'prestige-building appearance', 'title-scene momentum', 'champion credibility boost',
        'champion-backed story', 'gold-driven episode', 'championship gravity', 'title prestige moment',
        'champion’s statement', 'belt-focused presentation', 'champion-led rating boost',
        'champion carried the brand', 'title picture clarity', 'championship showcase',
        'gold standard segment', 'champion-made moment',
    ],
    'champion_neg': [
        'champion ignored', 'title felt cold', 'championship scene neglected', 'belt lost importance',
        'champion underused', 'title picture blurred', 'gold felt secondary', 'champion presence missing',
        'prestige dropped', 'main title cooled off', 'champion booking concern', 'title momentum stalled',
    ],
    'sponsor_good': [
        'premium sponsor placement', 'clean commercial integration', 'brand-perfect ad read',
        'money-making sponsor spot', 'seamless product placement', 'viral sponsor clip',
        'high-converting sponsor moment', 'sponsor-friendly segment', 'ad slot delivered',
        'commercial break win', 'sponsor objective enhanced', 'brand-safe activation',
        'mainstream-ready ad', 'broadcast-polished ad', 'social-ready ad spot',
    ],
    'sponsor_bad': [
        'forced sponsor plug', 'awkward product placement', 'dead-air commercial moment',
        'sponsor mismatch', 'fan-rejected ad', 'brand-risk ad', 'tone-deaf sponsor spot',
        'commercial momentum killer', 'overproduced ad break', 'sponsor confidence concern',
        'bad product fit', 'ad felt fake', 'crowd rejected the plug',
    ],
    'money_gain': [
        'money-making night', 'revenue-positive gate', 'sponsor-backed windfall', 'merch-heavy episode',
        'ticket surge', 'broadcast cash-in', 'commercially explosive show', 'profit-positive presentation',
    ],
    'money_loss': [
        'cost-heavy night', 'gate underperformed', 'sponsor pullback risk', 'merch-soft episode',
        'attendance drag on revenue', 'expensive production gamble', 'red-ink warning',
    ],
    'NXT': [
        'Spotlight Studio-approved', 'Unfiltered-worthy', 'Hollywood-machine', 'HBO-prestige',
        'Netflix-doc-ready', 'Apple-premium', 'Google-trending', 'Rockstar-coded', 'Rise-to-Glory-ready',
        'Crunchyroll-stylized', 'Red-Bull-fueled', 'Oscar-night', 'SNL-sketchable', 'cinematic-main-event',
        'prestige-drama', 'world-building', 'streaming-special-worthy', 'media-machine-ready',
        'global-star-making',
    ],
    'SmackDown': [
        'Culture-Pulse-approved', 'Sony-soundtracked', 'Paramount-ready', 'PRIME-viral',
        'New-Balance-clean', 'Hasbro-shelf-ready', 'Bandai-fighting-game-coded', 'Grammy-night',
        'music-video-ready', 'red-carpet-chaos', 'celebrity-heavy', 'internet-loud', 'viral-challenge',
        'pop-culture-crossover', 'mainstream-chaos', 'clip-farm-ready',
    ],
    'WCW': [
        'Sports-Desk-approved', 'EA-Sports-rated', 'Microsoft-powered', 'Pepsi-halftime',
        'Gatorade-performance', 'Funko-ready', 'Topps-card-worthy', 'Panini-premium', 'ESPN-coded',
        'CBS-broadcast', 'SportsCenter-ready', 'NFL-scale', 'NBA-arena', 'halftime-worthy',
        'stadium-gamble', 'big-fight-presentation', 'championship-sports', 'analytics-driven',
        'broadcast-quality', 'playoff-energy', 'game-day atmosphere', 'broadcast-table-approved',
    ],
}


def _recent_key():
    return 'descriptor_recent'


def ensure_descriptor_state():
    if _recent_key() not in st.session_state:
        st.session_state[_recent_key()] = []


def pick_descriptor(bank, brand=None, avoid_recent=True, k=1):
    ensure_descriptor_state()
    pool = list(DESCRIPTOR_BANKS.get(bank, []))
    if brand and brand in DESCRIPTOR_BANKS:
        pool = pool + list(DESCRIPTOR_BANKS[brand])
    if not pool:
        return 'solid episode' if k == 1 else ['solid episode']
    recent = set(st.session_state[_recent_key()][-40:])
    candidates = [p for p in pool if p not in recent] or pool
    picks = random.sample(candidates, min(k, len(candidates)))
    for p in picks:
        st.session_state[_recent_key()].insert(0, p)
    st.session_state[_recent_key()] = st.session_state[_recent_key()][:80]
    return picks[0] if k == 1 else picks


def sellout_from_pct(pct):
    if pct >= 97:
        return 'Sellout', pct
    if pct >= 90:
        return 'Near Sellout', pct
    if pct >= 80:
        return 'Strong Crowd', pct
    if pct >= 65:
        return 'Good Crowd', pct
    if pct >= 50:
        return 'Soft Crowd', pct
    return 'Weak Attendance', pct


def sellout_money_multipliers(status):
    return {
        'ticket': SELLOUT_TICKET_MULT.get(status, 1.0),
        'merch': SELLOUT_MERCH_MULT.get(status, 1.0),
        'sponsor_conf_delta': SELLOUT_SPONSOR_CONF.get(status, 0),
    }


def get_attendance_descriptor(capacity_pct, sellout_status, venue_type='Arena'):
    if venue_type == 'Stadium' or capacity_pct >= 85:
        base = pick_descriptor('stadium')
    elif sellout_status == 'Sellout':
        base = pick_descriptor('sellout')
    elif sellout_status == 'Near Sellout':
        base = pick_descriptor('near_sellout')
    elif sellout_status in ('Strong Crowd', 'Good Crowd'):
        base = pick_descriptor('strong_crowd')
    else:
        base = pick_descriptor('weak_attendance')
    return base


def get_money_descriptor(profit_loss):
    if int(profit_loss or 0) >= 500_000:
        return pick_descriptor('money_gain')
    if int(profit_loss or 0) > 0:
        return pick_descriptor('money_gain')
    if int(profit_loss or 0) < -200_000:
        return pick_descriptor('money_loss')
    return pick_descriptor('outside')


def get_sponsor_descriptor(result, brand):
    bank = 'sponsor_good' if result in ('success', 'premium', 'clean') else 'sponsor_bad'
    return pick_descriptor(bank, brand=brand)


def get_champion_descriptor(usage_summary):
    if usage_summary.get('ignored'):
        return pick_descriptor('champion_neg')
    if usage_summary.get('main_event'):
        return pick_descriptor('main_event')
    if usage_summary.get('wrestled') or usage_summary.get('promo'):
        return pick_descriptor('champion_pos')
    if usage_summary.get('appeared'):
        return pick_descriptor('champion_pos')
    return pick_descriptor('champion_neg')


def get_main_event_descriptor(champ_in_main, rivalry_heat, ple, rating):
    if champ_in_main or rivalry_heat >= 70 or ple:
        return pick_descriptor('main_event')
    if float(rating or 7) >= 8:
        return pick_descriptor('main_event')
    return pick_descriptor('wrestling')


def get_show_descriptor(brand, rating, continuity, sellout_status, sponsor_result, champion_usage, profit_loss=0):
    parts = []
    if brand in PLAYABLE:
        parts.append(pick_descriptor(brand, brand=brand))
    if continuity >= 8:
        parts.append('continuity-rich')
    elif continuity < 5:
        parts.append('continuity-breaking')
    parts.append(get_attendance_descriptor(0, sellout_status))
    parts.append(get_champion_descriptor(champion_usage))
    if sponsor_result:
        parts.append(get_sponsor_descriptor(sponsor_result, brand))
    parts.append(get_money_descriptor(profit_loss))
    parts.append(pick_descriptor('wrestling'))
    if float(rating or 7) >= 8.5:
        parts.append(pick_descriptor('outside'))
    seen = set()
    uniq = []
    for p in parts:
        if p and p not in seen:
            seen.add(p)
            uniq.append(p)
    return ', '.join(uniq[:6])


def company_champion_names(company, is_champ_fn):
    names = []
    for holder in (st.session_state.get('champions', {}).get(company, {}) or {}).values():
        if holder and holder not in CHAMP_PLACEHOLDERS and is_champ_fn(holder):
            names.append(holder)
    return list(dict.fromkeys(names))


def analyze_champion_usage(company, matches, promos, featured, is_champ_fn, rivalry_heat_fn, breakdown=None, feedback=None):
    breakdown = breakdown or {}
    feedback = feedback or {}
    champs = company_champion_names(company, is_champ_fn)
    booked = set()
    wrestled = set()
    promo_set = set()
    main_event = set()
    for m in matches or []:
        parts = [p for p in m.get('participants', []) if p not in ('None', 'TBD', 'NC', '')]
        booked.update(parts)
        if m.get('winner') in parts:
            wrestled.add(m.get('winner'))
        for p in parts:
            wrestled.add(p)
    if matches:
        last = matches[-1]
        main_parts = [p for p in last.get('participants', []) if p not in ('None', 'TBD', 'NC', '')]
        for c in champs:
            if c in main_parts:
                main_event.add(c)
    for p in promos or []:
        for n in p.get('participants', []) or []:
            if n != 'None':
                booked.add(n)
                promo_set.add(n)
    appeared = [c for c in champs if c in booked]
    wrestled_ch = [c for c in champs if c in wrestled]
    promo_ch = [c for c in champs if c in promo_set]
    ignored = []
    for c in champs:
        if c not in booked:
            heat = rivalry_heat_fn(c)
            if heat >= 50 or float(breakdown.get('Champion', breakdown.get('champion', 5)) if isinstance(breakdown, dict) else 5) < 6:
                ignored.append(c)
    story_ok = float(_bd(breakdown, 'Champion', 5)) >= 6 or float(_bd(breakdown, 'Story', 5)) >= 6
    valid_usage = bool(appeared) and (story_ok or featured in champs or main_event or promo_ch)
    mult = {
        'ticket': 1.0, 'merch': 1.0, 'media': 1.0, 'sponsor': 1.0, 'viewership': 1.0,
        'prestige': 0, 'title_prestige': 0, 'sponsor_conf': 0, 'fan_investment': 0,
    }
    notes = []
    if appeared and valid_usage:
        mult['sponsor'] *= 1.03
        mult['merch'] *= 1.03
        notes.append('Champion appeared → +3% sponsor/media & merch')
    if wrestled_ch and valid_usage:
        mult['viewership'] *= 1.05
        mult['ticket'] *= 1.03
        notes.append('Champion wrestled → +5% viewership / attendance boost')
    if promo_ch and valid_usage:
        mult['prestige'] += 4
        notes.append('Champion promo → +4% story/brand prestige')
    if main_event and valid_usage:
        mult['sponsor'] *= 1.08
        mult['merch'] *= 1.08
        mult['viewership'] *= 1.10
        mult['title_prestige'] += 5
        notes.append('Champion in main event → +10% main-event / +8% sponsor & merch')
    if ignored:
        mult['title_prestige'] -= 5
        mult['prestige'] -= 3
        if any(rivalry_heat_fn(c) >= 55 for c in ignored):
            mult['prestige'] -= 5
            notes.append('Champion ignored with active rivalry → title & story hit')
        else:
            notes.append('Champion underused → title prestige dip')
        mult['fan_investment'] -= 3
    used_well = len(appeared) >= 2 and valid_usage and not ignored
    if used_well:
        mult['prestige'] += 5
        mult['sponsor_conf'] += 5
        notes.append('Multiple champions used well → +5% brand prestige & sponsor confidence')
    if appeared and not valid_usage:
        notes.append('Champion appearance lacked story context — limited bonus')
        mult['merch'] = min(mult['merch'], 1.01)
        mult['sponsor'] = min(mult['sponsor'], 1.01)
    return {
        'champions': champs, 'appeared': appeared, 'wrestled': wrestled_ch, 'promo': promo_ch,
        'main_event': list(main_event), 'ignored': ignored, 'valid_usage': valid_usage,
        'multipliers': mult, 'notes': notes,
        'summary': {
            'appeared': bool(appeared), 'wrestled': bool(wrestled_ch), 'promo': bool(promo_ch),
            'main_event': bool(main_event), 'ignored': bool(ignored),
        },
    }


def _bd(breakdown, needle, default=5.5):
    if not breakdown:
        return default
    for k, v in breakdown.items():
        if needle.lower() in str(k).lower():
            return float(v)
    return default


def score_sponsor_ad(company, ad_type, rating, star_pop, sellout_status, controversy, brand_fit):
    score = 50 + float(rating or 7) * 4 + int(star_pop or 0) * 0.2
    if sellout_status in ('Sellout', 'Near Sellout'):
        score += 12
    if brand_fit:
        score += 15
    if controversy > 60:
        score -= 20
    if ad_type in ('product placement', 'merch ad', 'toy launch ad') and company == 'SmackDown':
        score += 8
    if 'halftime' in ad_type and company == 'WCW':
        score += 10
    if 'streaming' in ad_type and company == 'NXT':
        score += 10
    if score >= 78:
        return 'premium', score
    if score >= 62:
        return 'success', score
    if score >= 48:
        return 'clean', score
    return 'weak', score


def run_sponsor_ads(company, booked_names, rating, sellout_status, find_fn, is_champ_fn, sponsors=None):
    sponsors = sponsors or []
    if not sponsors:
        sponsors = ['Partner']
    n_ads = 1 if float(rating or 7) < 7 else min(2, 1 + (1 if sellout_status in ('Sellout', 'Near Sellout') else 0))
    ads = []
    styles = BRAND_AD_STYLES.get(company, [])
    for _ in range(n_ads):
        ad_type = random.choice(SPONSOR_AD_TYPES)
        style = random.choice(styles) if styles else ad_type
        star = None
        pop = 50
        for nm in booked_names or []:
            w = find_fn(nm) if find_fn else None
            if w and (is_champ_fn(nm) if is_champ_fn else False):
                star = nm
                pop = int(w.get('popularity', 70))
                break
        if not star and booked_names:
            nm = random.choice(list(booked_names))
            w = find_fn(nm) if find_fn else None
            star = nm
            pop = int(w.get('popularity', 60)) if w else 60
        brand_fit = random.random() < 0.72
        result, sc = score_sponsor_ad(company, ad_type, rating, pop, sellout_status, 30, brand_fit)
        rev = int(40000 + sc * 3500)
        if result == 'premium':
            rev = int(rev * 1.35)
        elif result == 'weak':
            rev = int(rev * 0.55)
        ads.append({
            'type': ad_type, 'style': style, 'star': star, 'result': result, 'score': sc,
            'revenue': rev, 'descriptor': get_sponsor_descriptor(result, company),
        })
    return ads


def apply_show_quality_to_log(log, company, venue, matches, promos, rating, feedback, breakdown,
                              featured='', rival='', ple=False, find_fn=None, is_champ_fn=None, rivalry_heat_fn=None, sponsors=None):
    """Apply sellout, champion, sponsor economics and build descriptor package into log."""
    find_fn = find_fn or (lambda n: None)
    is_champ_fn = is_champ_fn or (lambda n: False)
    rivalry_heat_fn = rivalry_heat_fn or (lambda n: 0)
    cap = max(1, int((venue or {}).get('capacity', log.get('capacity', 15000))))
    att = int(log.get('attendance', 0))
    pct = 100 * att / cap
    sellout_status, _ = sellout_from_pct(pct)
    sm = sellout_money_multipliers(sellout_status)
    log['capacity'] = cap
    log['capacity_filled_pct'] = round(pct, 1)
    log['sellout_status'] = sellout_status
    ticket = int(log.get('ticket_revenue', 0))
    merch = int(log.get('merchandise_revenue', 0))
    sponsor = int(log.get('sponsor_revenue', 0))
    media = int(log.get('media_revenue', 0))
    log['ticket_revenue'] = int(ticket * sm['ticket'])
    log['merchandise_revenue'] = int(merch * sm['merch'])
    champ = analyze_champion_usage(company, matches, promos, featured, is_champ_fn, rivalry_heat_fn, breakdown, feedback)
    cm = champ['multipliers']
    log['ticket_revenue'] = int(log['ticket_revenue'] * cm['ticket'])
    log['merchandise_revenue'] = int(log['merchandise_revenue'] * cm['merch'])
    log['media_revenue'] = int(media * cm['media'] * cm['sponsor'])
    log['sponsor_revenue'] = int(sponsor * cm['sponsor'])
    booked = set()
    for m in matches or []:
        for p in m.get('participants', []) or []:
            if p not in ('None', 'TBD', 'NC'):
                booked.add(p)
    for p in promos or []:
        for n in p.get('participants', []) or []:
            if n != 'None':
                booked.add(n)
    ads = run_sponsor_ads(company, booked, rating, sellout_status, find_fn, is_champ_fn, sponsors=sponsors)
    ad_rev = sum(a['revenue'] for a in ads)
    log['sponsor_revenue'] = int(log['sponsor_revenue'] + ad_rev)
    log['sponsor_ads'] = ads
    rh = rivalry_heat_fn(rival) if rival and str(rival).lower() not in ('none', '') else 0
    main_desc = get_main_event_descriptor(bool(champ['main_event']), rh, ple, rating)
    att_desc = get_attendance_descriptor(pct, sellout_status, (venue or {}).get('type', 'Arena'))
    champ_desc = get_champion_descriptor(champ['summary'])
    continuity = _bd(breakdown, 'Story', 5.5)
    sponsor_result = ads[0]['result'] if ads else 'clean'
    show_line = get_show_descriptor(company, rating, continuity, sellout_status, sponsor_result, champ['summary'], log.get('profit_loss', 0))
    quality_notes = [
        f"Sellout: {sellout_status} ({pct:.0f}% capacity) — ticket ×{sm['ticket']:.2f}, merch ×{sm['merch']:.2f}",
    ] + champ['notes']
    for a in ads:
        quality_notes.append(f"Sponsor ad ({a['type']}): {a['descriptor']} (+{a['revenue']:,})")
    prof = st.session_state.company_profiles.setdefault(company, {})
    prof['sponsor_confidence'] = max(1, min(100, int(prof.get('sponsor_confidence', 85)) + sm['sponsor_conf_delta'] + cm['sponsor_conf'] + (5 if sponsor_result == 'premium' else 0)))
    if cm['prestige']:
        prof['prestige'] = max(1, min(100, int(prof.get('prestige', 85)) + int(cm['prestige'])))
    pkg = {
        'sellout_status': sellout_status, 'capacity_pct': round(pct, 1),
        'show_descriptor': show_line, 'attendance_descriptor': att_desc,
        'champion_descriptor': champ_desc, 'main_event_descriptor': main_desc,
        'money_descriptor': get_money_descriptor(log.get('profit_loss', 0)),
        'sponsor_ads': ads, 'champion_usage': champ, 'quality_notes': quality_notes,
        'viewership_mult': cm['viewership'], 'sellout_mult': sm,
    }
    log['show_quality'] = pkg
    log['ai_notes'] = list(log.get('ai_notes', [])) + quality_notes[:4]
    exp = log.get('weekly_expenses', 0)
    inc = (
        log['ticket_revenue'] + log['merchandise_revenue'] + log['media_revenue'] +
        log['sponsor_revenue'] + int(log.get('movie_revenue', 0)) + int(log.get('market_bonus', 0)) +
        int(log.get('ple_bonus', 0)) + int(log.get('stadium_bonus', 0)) + int(log.get('viral_twitter_bonus', 0))
    )
    log['weekly_income'] = inc
    log['profit_loss'] = inc - exp
    return log, pkg


def enrich_viewership_modifiers(vd, pkg, rating, breakdown):
    """Add show-quality factors to viewership calculation notes and multiplier."""
    if not pkg:
        return vd
    mult = vd.get('multiplier', 1.0)
    notes = list(vd.get('modifiers', []))
    vm = float(pkg.get('viewership_mult', 1.0))
    if vm != 1.0:
        mult *= vm
        notes.append(f"Champion usage → viewership ×{vm:.2f}")
    ss = pkg.get('sellout_status', '')
    if ss == 'Sellout':
        mult += 0.04
        notes.append(f'{ss} → +4% viewership')
    elif ss == 'Near Sellout':
        mult += 0.02
        notes.append(f'{ss} → +2% viewership')
    elif ss == 'Weak Attendance':
        mult -= 0.03
        notes.append('Weak gate → -3% viewership')
    continuity = _bd(breakdown, 'Story', 5.5)
    if continuity >= 8:
        mult += 0.02
        notes.append('Story continuity strong → +2%')
    vd['multiplier'] = round(mult, 3)
    vd['modifiers'] = notes
    vd['show_descriptor'] = pkg.get('show_descriptor', '')
    return vd
