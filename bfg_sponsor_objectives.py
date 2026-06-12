"""Sponsor Objectives — sponsors assign objectives; players complete ad/script submissions."""
import json
import random
import re
import streamlit as st

PLAYABLE = ['NXT', 'SmackDown', 'WCW']

STATUSES = [
    'Not Started', 'In Progress', 'Submitted', 'Met', 'Partial', 'Failed', 'Paid',
]

OBJECTIVE_TYPES = [
    'Commercial Objective',
    'Product Placement Objective',
    'Social Media Campaign Objective',
    'Documentary Segment Objective',
    'Trailer Objective',
    'Toy/Merch Campaign Objective',
    'Trading Card Campaign Objective',
    'Sneaker/Apparel Campaign Objective',
    'Beverage Activation Objective',
    'Gaming Crossover Objective',
    'Streaming Special Objective',
    'Red Carpet Sponsor Objective',
    'Halftime Sponsor Objective',
    'Sports Analytics Objective',
    'Anime Trailer Objective',
    'Travel/Arrival Segment Objective',
    'Backstage Sponsor Segment Objective',
    'Ad Script Objective',
]

BRAND_HUB = {
    'NXT': 'NXT Spotlight Studio',
    'SmackDown': 'SmackDown Culture Pulse',
    'WCW': 'WCW Sports Desk',
}

PAYOUT_BANDS = {
    'NXT': (500_000, 6_000_000),
    'SmackDown': (2_000_000, 7_000_000),
    'WCW': (750_000, 3_000_000),
}

TERMINAL_STATUSES = {'Met', 'Partial', 'Failed', 'Paid', 'Completed'}

GRADE_WEIGHTS = {
    'sponsor_fit': 0.25,
    'wrestler_fit': 0.20,
    'script_quality': 0.20,
    'story_connection': 0.15,
    'entertainment': 0.10,
    'brand_safety': 0.10,
}

SPONSOR_TYPE_HINTS = {
    'netflix': 'Streaming Special Objective',
    'hbo': 'Streaming Special Objective',
    'paramount': 'Streaming Special Objective',
    'amazon': 'Streaming Special Objective',
    'marvel': 'Trailer Objective',
    'dc': 'Trailer Objective',
    'hollywood': 'Commercial Objective',
    'rockstar': 'Gaming Crossover Objective',
    'ea sports': 'Gaming Crossover Objective',
    'mattel': 'Toy/Merch Campaign Objective',
    'lego': 'Toy/Merch Campaign Objective',
    'barbie': 'Toy/Merch Campaign Objective',
    'funko': 'Toy/Merch Campaign Objective',
    'topps': 'Trading Card Campaign Objective',
    'panini': 'Trading Card Campaign Objective',
    'nike': 'Sneaker/Apparel Campaign Objective',
    'adidas': 'Sneaker/Apparel Campaign Objective',
    'under armour': 'Sneaker/Apparel Campaign Objective',
    'new balance': 'Sneaker/Apparel Campaign Objective',
    'coca-cola': 'Beverage Activation Objective',
    'monster': 'Beverage Activation Objective',
    'pepsi': 'Beverage Activation Objective',
    'gatorade': 'Beverage Activation Objective',
    'bud light': 'Beverage Activation Objective',
    'sony': 'Social Media Campaign Objective',
    'prime': 'Social Media Campaign Objective',
    'draftkings': 'Sports Analytics Objective',
    'espn': 'Halftime Sponsor Objective',
    'cbs': 'Halftime Sponsor Objective',
    'nbc': 'Red Carpet Sponsor Objective',
    'snl': 'Commercial Objective',
    'good morning america': 'Travel/Arrival Segment Objective',
    'olympics': 'Red Carpet Sponsor Objective',
    'apple': 'Commercial Objective',
    'microsoft': 'Documentary Segment Objective',
    'mercedes': 'Travel/Arrival Segment Objective',
    'tesla': 'Travel/Arrival Segment Objective',
    'samsung': 'Product Placement Objective',
    'marriott': 'Travel/Arrival Segment Objective',
    'chase': 'Documentary Segment Objective',
    'progressive': 'Commercial Objective',
}

SPONSOR_WRESTLER_PROFILE = {
    'netflix': ('cinematic prestige star', 'prestige drama, documentary storytelling, cinematic character work'),
    'hbo': ('cinematic prestige star', 'prestige drama, documentary storytelling, cinematic character work'),
    'marvel': ('charismatic hero or antihero', 'blockbuster presence, larger-than-life star power'),
    'rockstar': ('hot momentum star', 'cinematic gaming energy, main-character aura, rising heat'),
    'apple': ('premium crossover star', 'premium polish, tech-lifestyle crossover, high popularity'),
    'sony': ('music-culture crossover star', 'mainstream music-video energy, viral culture, social buzz'),
    'prime': ('influencer-energy star', 'viral culture, influencer marketing, social media buzz'),
    'gatorade': ('athletic champion', 'sports performance, athlete credibility, champion legitimacy'),
    'nike': ('athletic champion', 'sports performance, peak athlete credibility'),
    'adidas': ('athletic champion', 'sports performance, peak athlete credibility'),
    'pepsi': ('mainstream babyface', 'mass-market appeal, family-friendly energy'),
    'ea sports': ('competitive gamer-athlete', 'sports gamer crossover, competitive credibility'),
    'topps': ('collectible star', 'card-market heat, nostalgia and star power'),
    'funko': ('merch-friendly star', 'toy-shelf appeal, recognizable gimmick'),
    'draftkings': ('analytics-friendly star', 'stats-friendly credibility, big-fight moments'),
    'espn': ('sports desk anchor star', 'sports legitimacy, ESPN crossover credibility'),
}

CUSTOM_BLUEPRINTS = {
    ('NXT', 'Rockstar Games'): {
        'objective_type': 'Trailer Objective',
        'title': 'Rise to Glory trailer',
        'description': 'Create a 60-second NXT: Rise to Glory trailer ad featuring a top star as the main character or final boss.',
        'requirements': [
            'Must feature a hot wrestler with momentum',
            'Must feel cinematic and gaming-focused',
            'Must connect to NXT Spotlight Studio',
        ],
        'required_wrestler_type': 'hot momentum star',
        'min_grade': 8.5,
        'risk_level': 'Medium',
    },
    ('NXT', 'Marvel'): {
        'objective_type': 'Trailer Objective',
        'title': 'Marvel crossover trailer',
        'description': 'Create a blockbuster Marvel-style trailer spot with an NXT star as the hero.',
        'requirements': ['Must feel cinematic', 'Must connect to NXT Spotlight Studio', 'Minimum spectacle and star power'],
        'required_wrestler_type': 'charismatic hero or antihero',
        'min_grade': 8.0,
        'risk_level': 'Medium',
    },
    ('SmackDown', 'Sony'): {
        'objective_type': 'Social Media Campaign Objective',
        'title': 'Music-video sponsor segment',
        'description': 'Create a music-video-style sponsor segment with a SmackDown star and music/culture crossover.',
        'requirements': [
            'Must feel mainstream',
            'Must fit SmackDown Culture Pulse',
            'Must generate viral/social buzz',
        ],
        'required_wrestler_type': 'music-culture crossover star',
        'min_grade': 8.0,
        'risk_level': 'Medium',
    },
    ('SmackDown', 'PRIME'): {
        'objective_type': 'Social Media Campaign Objective',
        'title': 'PRIME viral activation',
        'description': 'Create a viral PRIME hydration campaign with influencer-energy presentation.',
        'requirements': ['Must feel viral', 'Must fit SmackDown Culture Pulse', 'Social-first hook required'],
        'required_wrestler_type': 'influencer-energy star',
        'min_grade': 7.5,
        'risk_level': 'Low',
    },
    ('WCW', 'Gatorade'): {
        'objective_type': 'Commercial Objective',
        'title': 'Performance training commercial',
        'description': 'Create a performance training commercial featuring a WCW champion or athletic top star.',
        'requirements': [
            'Must feel sports-legitimate',
            'Must fit WCW Sports Desk',
            'Must improve athlete credibility',
        ],
        'required_wrestler_type': 'athletic champion',
        'min_grade': 7.5,
        'risk_level': 'Low',
    },
    ('WCW', 'EA Sports'): {
        'objective_type': 'Gaming Crossover Objective',
        'title': 'EA Sports crossover spot',
        'description': 'Create a competitive sports-game crossover ad with a WCW star as the featured athlete.',
        'requirements': ['Must feel competitive', 'Must fit WCW Sports Desk', 'Athlete credibility required'],
        'required_wrestler_type': 'competitive gamer-athlete',
        'min_grade': 7.5,
        'risk_level': 'Medium',
    },
    ('NXT', 'Netflix'): {
        'objective_type': 'Streaming Special Objective',
        'title': 'Netflix docu-series teaser',
        'description': 'Create a prestige Netflix docu-series teaser starring an NXT breakout.',
        'requirements': ['Premium tone', 'Connect to NXT Spotlight Studio', 'Documentary storytelling'],
        'required_wrestler_type': 'cinematic prestige star',
        'min_grade': 8.0,
        'risk_level': 'Low',
    },
    ('NXT', 'Apple'): {
        'objective_type': 'Commercial Objective',
        'title': 'Apple Vision Pro premium spot',
        'description': 'Create a premium Apple Vision Pro ad featuring one of NXT\'s hottest wrestlers.',
        'requirements': [
            'Must feel premium and cinematic',
            'Must feature a wrestler with high popularity or momentum',
            'Must connect to NXT Spotlight Studio',
        ],
        'required_wrestler_type': 'premium crossover star',
        'min_grade': 8.0,
        'risk_level': 'Medium',
    },
}


SIGNATURE_HERO = {
    'NXT': 'Rockstar Games',
    'SmackDown': 'Sony',
    'WCW': 'Gatorade',
}


def _inject_signature_objectives(company):
    """One hero signature brief per brand per quarter (Rockstar / Sony / Gatorade)."""
    week = int(st.session_state.get('week', 0))
    q = st.session_state.get('quarter', 1)
    sp = SIGNATURE_HERO.get(company)
    if not sp:
        return
    bp = CUSTOM_BLUEPRINTS.get((company, sp))
    if not bp:
        return
    if any(
        o.get('company') == company and o.get('sponsor') == sp and o.get('quarter') == q
        for o in st.session_state.sponsor_objectives
    ):
        return
    o = default_objective(company, sp, quarter=q, blueprint=bp)
    o['week_assigned'] = week
    st.session_state.sponsor_objectives.insert(0, o)


def _new_id():
    return random.randint(10000, 99999)


def _sponsor_key(sponsor):
    return (sponsor or '').lower().strip()


def _objective_type_for_sponsor(sponsor, company):
    key = _sponsor_key(sponsor)
    for hint, otype in SPONSOR_TYPE_HINTS.items():
        if hint in key:
            return otype
    defaults = {
        'NXT': 'Commercial Objective',
        'SmackDown': 'Social Media Campaign Objective',
        'WCW': 'Commercial Objective',
    }
    return defaults.get(company, 'Ad Script Objective')


def _wrestler_profile_for_sponsor(sponsor):
    key = _sponsor_key(sponsor)
    for hint, profile in SPONSOR_WRESTLER_PROFILE.items():
        if hint in key:
            return profile
    return ('versatile TV star', 'strong popularity, momentum, and brand-safe presentation')


def _payout_ranges(company, risk='Medium', min_grade=7.5):
    pmin, pmax = PAYOUT_BANDS.get(company, (500_000, 3_000_000))
    risk_mult = {'Low': 0.9, 'Medium': 1.0, 'High': 1.15}.get(risk, 1.0)
    grade_mult = 0.85 + (float(min_grade) - 6.5) * 0.08
    pmax = int(pmax * risk_mult * grade_mult)
    pmin = int(pmin * risk_mult)
    ppmin = max(50_000, int(pmin * 0.2))
    ppmax = max(ppmin + 50_000, int(pmax * 0.35))
    fail_pen = max(75_000, int(pmin * 0.15))
    return pmin, pmax, ppmin, ppmax, fail_pen


def default_objective(company, sponsor='', quarter=None, blueprint=None):
    q = quarter or st.session_state.get('quarter', 1)
    week = int(st.session_state.get('week', 0))
    bp = blueprint or {}
    obj_type = bp.get('objective_type') or _objective_type_for_sponsor(sponsor, company)
    wrestler_type, reason_seed = _wrestler_profile_for_sponsor(sponsor)
    min_grade = float(bp.get('min_grade', 7.5))
    risk = bp.get('risk_level', 'Medium')
    pmin, pmax, ppmin, ppmax, fail_pen = _payout_ranges(company, risk, min_grade)
    hub = BRAND_HUB.get(company, '')
    title = bp.get('title') or f'{sponsor} {obj_type.replace(" Objective", "")}'
    desc = bp.get('description') or (
        f'{sponsor} assigned a {obj_type.lower()} for {company}. '
        f'Deliver the required spot and connect it to {hub}.'
    )
    reqs = bp.get('requirements') or [
        f'Must fit {sponsor} brand identity',
        f'Must connect to {hub}',
        f'Minimum sponsor review grade: {min_grade}/10',
    ]
    return {
        'id': _new_id(),
        'company': company,
        'sponsor': sponsor,
        'brand': company,
        'objective_type': obj_type,
        'title': title,
        'description': desc,
        'requirements': list(reqs),
        'required_wrestler_type': bp.get('required_wrestler_type', wrestler_type),
        'recommended_wrestlers': [],
        'recommended_reason': reason_seed,
        'brand_hub': hub,
        'deadline_week': week + random.randint(3, 6),
        'min_grade': min_grade,
        'payout_min': pmin,
        'payout_max': pmax,
        'partial_payout_min': ppmin,
        'partial_payout_max': ppmax,
        'failure_penalty': fail_pen,
        'sponsor_confidence_delta': {'full': 6, 'strong': 4, 'partial': 0, 'small_partial': -2, 'fail': -8},
        'risk_level': risk,
        'status': 'Not Started',
        'quarter': q,
        'week_assigned': week,
        'week_completed': None,
        'submission': {
            'wrestler1': '',
            'wrestler2': '',
            'script': '',
            'storyline_id': '',
            'show': '',
            'week': week,
            'notes': '',
        },
        'grade_result': None,
        'payout_paid': 0,
        'notes': '',
        # legacy compat
        'progress': 0,
        'target': 1,
        'payout': pmax,
        'penalty': fail_pen,
        'requirement': desc,
    }


def _is_legacy_objective(o):
    return not o.get('objective_type')


def _normalize_status(o):
    stt = o.get('status', 'Not Started')
    if stt == 'Active':
        o['status'] = 'Not Started' if not (o.get('submission') or {}).get('script') else 'In Progress'
    elif stt == 'Completed':
        o['status'] = 'Paid' if int(o.get('payout_paid', 0) or 0) > 0 else 'Met'


def migrate_sponsor_objectives(companies_dict):
    objs = st.session_state.get('sponsor_objectives', [])
    if not objs:
        return
    kept = []
    for o in objs:
        if _is_legacy_objective(o):
            if o.get('status') in ('Completed', 'Paid'):
                o['status'] = 'Paid'
                o['objective_type'] = o.get('objective_type') or 'Ad Script Objective'
                o['title'] = o.get('title') or f"{o.get('sponsor', 'Sponsor')} legacy objective"
                kept.append(o)
            continue
        _normalize_status(o)
        kept.append(o)
    st.session_state.sponsor_objectives = kept


def _blueprint_for(company, sponsor):
    return CUSTOM_BLUEPRINTS.get((company, sponsor))


def _assign_objectives_for_company(companies_dict, company, count=2):
    sponsors = (companies_dict.get(company) or {}).get('sponsors', []) or ['Partner']
    week = int(st.session_state.get('week', 0))
    q = st.session_state.get('quarter', 1)
    active = [
        o for o in st.session_state.sponsor_objectives
        if o.get('company') == company and o.get('status') not in TERMINAL_STATUSES
    ]
    need = max(0, count - len(active))
    if need <= 0:
        return
    pool = list(sponsors)
    random.shuffle(pool)
    used_sponsors = {o.get('sponsor') for o in active}
    for sp in pool:
        if need <= 0:
            break
        if sp in used_sponsors:
            continue
        bp = _blueprint_for(company, sp)
        o = default_objective(company, sp, quarter=q, blueprint=bp)
        o['recommended_wrestlers'] = []
        st.session_state.sponsor_objectives.append(o)
        used_sponsors.add(sp)
        need -= 1
    idx = 0
    while need > 0 and pool:
        sp = pool[idx % len(pool)]
        bp = _blueprint_for(company, sp)
        o = default_objective(company, sp, quarter=q, blueprint=bp)
        o['title'] = f"{sp} — alternate Q{q} brief"
        st.session_state.sponsor_objectives.append(o)
        need -= 1
        idx += 1


def ensure_sponsor_objectives(companies_dict):
    if 'sponsor_objectives' not in st.session_state:
        st.session_state.sponsor_objectives = []
    migrate_sponsor_objectives(companies_dict)
    for comp in PLAYABLE:
        _inject_signature_objectives(comp)
        _assign_objectives_for_company(companies_dict, comp, count=2)
        for o in company_objectives(comp):
            if o.get('status') not in TERMINAL_STATUSES:
                o['recommended_wrestlers'] = recommend_wrestler_names(
                    comp, o, st.session_state.get('roster', []), champions=st.session_state.get('champions', {}),
                )[:5]


def company_objectives(company):
    return [o for o in st.session_state.get('sponsor_objectives', []) if o.get('company') == company]


def objective_by_id(oid):
    for o in st.session_state.get('sponsor_objectives', []):
        if int(o.get('id', -1)) == int(oid):
            return o
    return None


def active_objective_options(company):
    opts = []
    for o in company_objectives(company):
        if o.get('status') in TERMINAL_STATUSES:
            continue
        label = f"{o['id']}: {o.get('sponsor', '')} — {o.get('objective_type', '')}"
        opts.append((label, o['id']))
    return opts


def _story_heat_for_wrestler(name, company, storylines):
    heat = 0
    for s in storylines or []:
        if s.get('company') != company:
            continue
        if name in (s.get('wrestlers') or []):
            heat = max(heat, int(s.get('heat', 0) or 0))
    return heat


def _is_champion(name, company, champions):
    for title, holder in (champions or {}).get(company, {}).items():
        if holder == name:
            return True
    return False


def _sponsor_fit_score(w, sponsor, objective_type):
    pop = int(w.get('popularity', 50) or 50)
    mom = int(w.get('momentum', 50) or 50)
    trust = int(w.get('sponsor_trust', 60) or 60)
    buzz = int(w.get('twitter_buzz', 40) or 40)
    cont = int(w.get('controversy_risk', 20) or 20)
    sk = _sponsor_key(sponsor)
    score = pop * 0.28 + mom * 0.22 + trust * 0.18 + buzz * 0.12
    if 'gatorade' in sk or 'nike' in sk or 'adidas' in sk or 'under armour' in sk:
        score += 8 if pop >= 75 else 0
        score += 6 if mom >= 70 else 0
    if 'sony' in sk or 'prime' in sk:
        score += buzz * 0.15
    if 'rockstar' in sk or 'ea sports' in sk or 'Gaming' in objective_type:
        score += mom * 0.12
    if 'netflix' in sk or 'hbo' in sk or 'Documentary' in objective_type:
        score += trust * 0.1
    if cont >= 70 and 'family' not in sk:
        score -= 8
    return score


def recommend_wrestler_names(company, objective, roster, champions=None, storylines=None, limit=5):
    sponsor = objective.get('sponsor', '')
    obj_type = objective.get('objective_type', '')
    rows = []
    for w in roster or []:
        if w.get('company') != company or w.get('status') not in (None, 'Active'):
            continue
        name = w.get('name', '')
        if not name:
            continue
        heat = _story_heat_for_wrestler(name, company, storylines or st.session_state.get('storylines', []))
        champ_bonus = 12 if _is_champion(name, company, champions or {}) else 0
        fit = _sponsor_fit_score(w, sponsor, obj_type)
        morale = int(w.get('morale', 50) or 50)
        media = int(w.get('fan_support', 50) or 50)
        total = fit + heat * 0.18 + champ_bonus + morale * 0.05 + media * 0.08
        rows.append((total, name))
    rows.sort(key=lambda x: -x[0])
    return [n for _, n in rows[:limit]]


def build_recommendation_reason(objective, names):
    sponsor = objective.get('sponsor', 'Sponsor')
    base = objective.get('recommended_reason') or _wrestler_profile_for_sponsor(sponsor)[1]
    if not names:
        return base
    return f"{base}. Top fits for {sponsor}: {', '.join(names[:3])}."


def _clamp_grade(v):
    return round(max(1.0, min(10.0, float(v))), 1)


def _keyword_score(text, keywords):
    t = (text or '').lower()
    if not t:
        return 35.0
    hits = sum(1 for k in keywords if k.lower() in t)
    base = 45 + hits * 8
    if len(t) > 120:
        base += 8
    if len(t) > 400:
        base += 8
    if len(t) > 900:
        base += 5
    return min(98.0, base)


def _grade_component_sponsor_fit(objective, submission):
    script = submission.get('script', '')
    sponsor = objective.get('sponsor', '')
    hub = objective.get('brand_hub', '')
    reqs = ' '.join(objective.get('requirements') or [])
    kws = [sponsor, hub, objective.get('objective_type', '').split()[0]]
    kws += re.findall(r'[A-Za-z]{4,}', reqs)[:6]
    return _keyword_score(script, [k for k in kws if k])


def _grade_component_wrestler_fit(objective, submission, find_fn=None):
    w1 = submission.get('wrestler1', '')
    if not w1:
        return 25.0
    rec = objective.get('recommended_wrestlers') or []
    if w1 in rec[:3]:
        base = 92
    elif w1 in rec:
        base = 84
    else:
        base = 62
    w = find_fn(w1) if find_fn else None
    if w:
        base += min(8, (int(w.get('popularity', 50)) - 50) * 0.12)
        base += min(6, (int(w.get('momentum', 50)) - 50) * 0.1)
    w2 = submission.get('wrestler2', '')
    if w2:
        base += 3
    return min(98.0, base)


def _grade_component_script_quality(submission):
    script = (submission.get('script') or '').strip()
    if not script:
        return 20.0
    words = len(script.split())
    score = 50
    if words >= 40:
        score += 12
    if words >= 90:
        score += 12
    if words >= 180:
        score += 8
    if any(x in script.lower() for x in ('scene', 'voiceover', 'cut to', 'camera', 'tagline', 'sponsor', 'brand')):
        score += 10
    if submission.get('notes'):
        score += 3
    return min(96.0, score)


def _grade_component_story_connection(objective, submission, storylines=None):
    sid = submission.get('storyline_id')
    if not sid:
        return 48.0
    for s in storylines or st.session_state.get('storylines', []):
        if str(s.get('id')) == str(sid):
            w1 = submission.get('wrestler1', '')
            if w1 and w1 in (s.get('wrestlers') or []):
                return 88.0
            return 72.0
    return 55.0


def _grade_component_entertainment(submission, wrestler=None):
    script = submission.get('script', '')
    score = _grade_component_script_quality(submission) * 0.55
    if wrestler:
        score += min(15, int(wrestler.get('momentum', 50)) * 0.12)
    return min(95.0, score)


def _grade_component_brand_safety(submission, wrestler=None):
    if not wrestler:
        return 70.0
    risk = int(wrestler.get('controversy_risk', 25) or 25)
    trust = int(wrestler.get('sponsor_trust', 60) or 60)
    script = (submission.get('script') or '').lower()
    penalty = 0
    for bad in ('scandal', 'lawsuit', 'arrest', 'bleed', 'blood', 'controversy'):
        if bad in script:
            penalty += 8
    return max(35.0, min(95.0, 55 + trust * 0.35 - risk * 0.25 - penalty))


def grade_submission(objective, submission, find_fn=None, ai_fn=None):
    w = find_fn(submission.get('wrestler1', '')) if find_fn and submission.get('wrestler1') else None
    components = {
        'sponsor_fit': _grade_component_sponsor_fit(objective, submission),
        'wrestler_fit': _grade_component_wrestler_fit(objective, submission, find_fn),
        'script_quality': _grade_component_script_quality(submission),
        'story_connection': _grade_component_story_connection(objective, submission),
        'entertainment': _grade_component_entertainment(submission, w),
        'brand_safety': _grade_component_brand_safety(submission, w),
    }
    overall = sum(components[k] * GRADE_WEIGHTS[k] for k in GRADE_WEIGHTS) / 10.0
    overall = _clamp_grade(overall)

    explanation = {
        'completed_objective': overall >= float(objective.get('min_grade', 7)),
        'wrestler_fit_ok': components['wrestler_fit'] >= 70,
        'script_good': components['script_quality'] >= 65,
        'brand_identity': components['sponsor_fit'] >= 65,
        'storyline_helped': components['story_connection'] >= 70,
    }

    ai_note = ''
    if ai_fn and (submission.get('script') or '').strip():
        prompt = (
            f"Grade this wrestling sponsor ad submission 1-10. Sponsor: {objective.get('sponsor')}. "
            f"Type: {objective.get('objective_type')}. Wrestler: {submission.get('wrestler1')}. "
            f"Requirements: {'; '.join(objective.get('requirements') or [])}. "
            f"Script excerpt: {(submission.get('script') or '')[:1200]}. "
            "Reply JSON only: {\"grade\":7.5,\"summary\":\"one sentence\"}"
        )
        raw = ai_fn(prompt, max_output=400, temperature=0.35)
        if raw:
            try:
                m = re.search(r'\{.*\}', raw, re.DOTALL)
                if m:
                    data = json.loads(m.group())
                    ai_grade = float(data.get('grade', overall))
                    overall = _clamp_grade(overall * 0.65 + ai_grade * 0.35)
                    ai_note = str(data.get('summary', ''))[:240]
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

    payout_amt, outcome, payout_tier = calculate_payout(overall, objective)
    summary = _build_grade_summary(objective, submission, overall, components, payout_tier, payout_amt, explanation)
    if ai_note:
        summary += f' AI: {ai_note}'

    return {
        'overall': overall,
        'components': {k: round(v / 10.0, 2) for k, v in components.items()},
        'explanation': explanation,
        'payout': payout_amt,
        'outcome': outcome,
        'payout_tier': payout_tier,
        'summary': summary,
    }


def _build_grade_summary(objective, submission, grade, components, payout_tier, payout_amt, explanation):
    sponsor = objective.get('sponsor', 'Sponsor')
    w = submission.get('wrestler1', '—')
    lines = [
        f"**{sponsor} review: {grade}/10** ({payout_tier.replace('_', ' ')})",
        f"Objective completed: **{'Yes' if explanation['completed_objective'] else 'Partially / No'}** · Wrestler **{w}**",
        f"Sponsor fit {components['sponsor_fit']:.1f} · Wrestler fit {components['wrestler_fit']:.1f} · "
        f"Script {components['script_quality']:.1f} · Story {components['story_connection']:.1f}",
    ]
    if payout_amt > 0:
        lines.append(f"Sponsor pays **${payout_amt:,}**.")
    else:
        lines.append('No payout — sponsor confidence may drop.')
    return ' '.join(lines)


def calculate_payout(grade, objective):
    g = float(grade or 0)
    min_g = float(objective.get('min_grade', 7))
    pmin = int(objective.get('payout_min', 200000))
    pmax = int(objective.get('payout_max', 1000000))
    ppmin = int(objective.get('partial_payout_min', 50000))
    ppmax = int(objective.get('partial_payout_max', 400000))

    if g >= 10:
        return int(pmax * 1.12), 'Met', 'full_bonus'
    if g >= 9:
        return pmax, 'Met', 'full'
    if g >= 8:
        return int(pmax * 0.88 + pmin * 0.12), 'Met', 'strong'
    if g >= 7:
        if min_g >= 8:
            return int((ppmin + ppmax) / 2), 'Partial', 'partial_below_req'
        return int((pmin + pmax) / 2), 'Met', 'normal'
    if g >= 6:
        return int((ppmin + ppmax) / 2), 'Partial', 'partial'
    if g >= 5:
        return ppmin, 'Partial', 'small_partial'
    return 0, 'Failed', 'none'


def save_submission_draft(objective, submission):
    objective['submission'] = dict(submission)
    if objective.get('status') == 'Not Started':
        objective['status'] = 'In Progress'


def apply_objective_completion(objective, grade_result, helpers=None):
    """Finance, confidence, wrestler stats, Twitter, storyline, weekly performance."""
    helpers = helpers or {}
    company = objective.get('company')
    outcome = grade_result.get('outcome', 'Failed')
    payout = int(grade_result.get('payout', 0) or 0)
    tier = grade_result.get('payout_tier', 'none')
    week = int(st.session_state.get('week', 0))
    objective['grade_result'] = grade_result
    objective['week_completed'] = week
    objective['status'] = outcome
    objective['payout_paid'] = payout

    add_txn = helpers.get('add_transaction')
    find_fn = helpers.get('find')
    make_tweet = helpers.get('make_twitter_post')
    touch = helpers.get('touch_universe_meta')
    apply_deltas = helpers.get('apply_wrestler_deltas')
    add_beat = helpers.get('add_storyline_beat')

    prof = st.session_state.company_profiles.setdefault(company, {})
    deltas = objective.get('sponsor_confidence_delta') or {}
    conf = int(prof.get('sponsor_confidence', 85))
    if tier in ('full_bonus', 'full', 'strong'):
        conf += int(deltas.get('full', 6))
    elif tier in ('normal',):
        conf += int(deltas.get('strong', 4))
    elif tier in ('partial', 'partial_below_req'):
        conf += int(deltas.get('partial', 0))
    elif tier == 'small_partial':
        conf += int(deltas.get('small_partial', -2))
    else:
        conf += int(deltas.get('fail', -8))
    prof['sponsor_confidence'] = max(1, min(100, conf))

    sub = objective.get('submission') or {}
    wname = sub.get('wrestler1')
    if find_fn and apply_deltas and wname:
        w = find_fn(wname)
        if w:
            g = float(grade_result.get('overall', 5))
            if g >= 8:
                apply_deltas(w, pop=(3, 7), mom=(2, 6), sponsor=(2, 5), buzz=(2, 6))
            elif g >= 6:
                apply_deltas(w, pop=(1, 4), mom=(1, 3), buzz=(1, 3))
            elif g < 5:
                apply_deltas(w, sponsor=(-4, -1), morale=(-3, 0))

    if payout and add_txn:
        add_txn(
            company,
            'Sponsor Objective',
            f"{objective.get('sponsor')} — {objective.get('title')} ({grade_result.get('overall')}/10)",
            payout,
            week,
            source='sponsor_objective',
        )
        objective['status'] = 'Paid'

    penalty = int(objective.get('failure_penalty', 0) or 0)
    if outcome == 'Failed' and penalty and add_txn:
        add_txn(
            company,
            'Sponsor Penalty',
            f"{objective.get('sponsor')} objective failed — confidence hit",
            -penalty,
            week,
            source='sponsor_objective',
        )

    sid = sub.get('storyline_id')
    if sid and add_beat:
        import bfg_storylines as sl
        story = sl.get_storyline(sid)
        if story:
            beat = (
                f"Sponsor spot ({objective.get('sponsor')}): {objective.get('objective_type')} — "
                f"{grade_result.get('overall')}/10. {grade_result.get('summary', '')[:180]}"
            )
            add_beat(story, beat, week)
            story['sponsor_tie'] = objective.get('sponsor', '')

    if make_tweet and wname and float(grade_result.get('overall', 0)) >= 7:
        sponsor = objective.get('sponsor', '')
        txt = (
            f"Just wrapped the {sponsor} spot. {wname} delivered. "
            f"Fans are already clipping it. #{sponsor.replace(' ', '')} #{company}"
        )
        make_tweet(company, 'wrestler', wname, '@' + wname.replace(' ', ''), 'Wrestler',
                   'Sponsor Activation', txt, '', {'topic': 'Sponsor', 'effects': {'buzz': (4, 9), 'pop': (2, 5)}})

    perf = {
        'type': 'sponsor_objective',
        'company': company,
        'week': week,
        'objective_id': objective.get('id'),
        'sponsor': objective.get('sponsor'),
        'title': objective.get('title'),
        'grade': grade_result.get('overall'),
        'payout': payout,
        'outcome': outcome,
        'wrestler': wname,
    }
    st.session_state.setdefault('weekly_performance_index', {})
    st.session_state.weekly_performance_index[f"{company}:spo:{week}:{objective.get('id')}"] = perf
    st.session_state.setdefault('news_feed', [])
    st.session_state.news_feed.insert(
        0,
        f"Week {week}: {company} completed {objective.get('sponsor')} objective — "
        f"{grade_result.get('overall')}/10 · {outcome} · ${payout:,}",
    )
    st.session_state.news_feed = st.session_state.news_feed[:80]

    if touch:
        touch(company)
    return objective


def submit_objective_for_review(objective_id, submission, helpers=None):
    obj = objective_by_id(objective_id)
    if not obj:
        return None, 'Objective not found.'
    if obj.get('status') in TERMINAL_STATUSES:
        return obj, 'This objective is already closed.'
    script = (submission.get('script') or '').strip()
    if not script:
        return obj, 'Add a script or commercial copy before submitting.'
    if not submission.get('wrestler1'):
        return obj, 'Select a featured wrestler.'
    obj['submission'] = dict(submission)
    obj['status'] = 'Submitted'
    grade_result = grade_submission(
        obj,
        obj['submission'],
        find_fn=helpers.get('find') if helpers else None,
        ai_fn=helpers.get('ai') if helpers else None,
    )
    apply_objective_completion(obj, grade_result, helpers=helpers)
    return obj, grade_result.get('summary', 'Submitted.')


def generate_script_with_ai(objective, submission, ai_fn, find_fn=None):
    if not ai_fn:
        return ''
    w = find_fn(submission.get('wrestler1', '')) if find_fn else None
    w2 = submission.get('wrestler2', '')
    wrestler_line = submission.get('wrestler1', 'Top star')
    if w:
        wrestler_line = (
            f"{w.get('name')} (pop {w.get('popularity')}, momentum {w.get('momentum')}, "
            f"gimmick: {w.get('gimmick_name') or w.get('nickname') or 'star'})"
        )
    prompt = (
        f"Write a sponsor {objective.get('objective_type')} script for wrestling brand {objective.get('company')}.\n"
        f"Sponsor: {objective.get('sponsor')}\n"
        f"Brief: {objective.get('description')}\n"
        f"Requirements: {'; '.join(objective.get('requirements') or [])}\n"
        f"Brand hub: {objective.get('brand_hub')}\n"
        f"Featured wrestler: {wrestler_line}\n"
        f"Second wrestler: {w2 or 'none'}\n"
        f"Notes: {submission.get('notes', '')}\n"
        f"Tone: premium, broadcast-ready, 150-250 words with scene directions."
    )
    return ai_fn(prompt, max_output=1800, temperature=0.65) or ''


def check_show_sponsor_progress(company, sponsor_tags, rating):
    """Legacy/show-time bump for product-placement style objectives linked on segments."""
    tags = [str(t).lower() for t in (sponsor_tags or []) if t]
    if not tags:
        return []
    done = []
    for o in company_objectives(company):
        if o.get('status') in TERMINAL_STATUSES:
            continue
        sp = _sponsor_key(o.get('sponsor'))
        if not sp:
            continue
        if not any(sp in t or t in sp for t in tags):
            continue
        if o.get('objective_type') in (
            'Product Placement Objective',
            'Backstage Sponsor Segment Objective',
            'Travel/Arrival Segment Objective',
        ):
            sub = o.setdefault('submission', {})
            if not sub.get('show'):
                sub['show'] = 'TV Show'
            if float(rating or 7) >= 7 and o.get('status') == 'In Progress':
                o['progress'] = min(1, int(o.get('progress', 0)) + 1)
                done.append(o)
    return done


def sponsor_objectives_done_count(company):
    return sum(
        1 for o in st.session_state.get('sponsor_objectives', [])
        if o.get('company') == company and o.get('status') in ('Met', 'Partial', 'Paid', 'Completed')
    )
