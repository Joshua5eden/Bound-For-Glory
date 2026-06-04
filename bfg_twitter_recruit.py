"""Twitter recruitment, tampering, and cross-brand morale/loyalty system."""
import random
import re
import streamlit as st

PLAYABLE = ['NXT', 'SmackDown', 'WCW']

RECRUIT_TWEET_TYPES = [
    'Friendly Recruitment',
    'Dream Match Tease',
    'Brand Shot',
    'Sponsor Opportunity Tease',
    'Sports Opportunity Tease',
    'Culture Opportunity Tease',
    'Loyalty Test',
    'Contract Rumor',
    'Public Tampering',
    'Subtle Tease',
]

TAMPERING_BY_TYPE = {
    'Friendly Recruitment': 'low',
    'Dream Match Tease': 'low',
    'Subtle Tease': 'low',
    'Brand Shot': 'medium',
    'Sponsor Opportunity Tease': 'medium',
    'Sports Opportunity Tease': 'medium',
    'Culture Opportunity Tease': 'medium',
    'Loyalty Test': 'medium',
    'Contract Rumor': 'medium',
    'Dream Match Tease': 'low',
    'Public Tampering': 'high',
}

BRAND_RECRUIT_STYLE = {
    'NXT': {
        'tags': 'Apple, Google, HBO, Netflix, Rockstar, NXT Spotlight Studio, NXT Unfiltered',
        'line': 'NXT doesn\'t just book matches. We build legacies. If they can\'t see your story, we will.',
        'types': ['Sponsor Opportunity Tease', 'Friendly Recruitment', 'Dream Match Tease'],
    },
    'SmackDown': {
        'tags': 'Sony, Paramount, PRIME, New Balance, Hasbro, Grammys, Culture Pulse',
        'line': 'You\'re too big to be hidden backstage. SmackDown turns stars into culture.',
        'types': ['Culture Opportunity Tease', 'Brand Shot', 'Sponsor Opportunity Tease'],
    },
    'WCW': {
        'tags': 'ESPN, CBS, NBA, NFL, EA Sports, Microsoft, Pepsi, Gatorade, Sports Desk',
        'line': 'If you want to be treated like an athlete and not a prop, WCW has the spotlight.',
        'types': ['Sports Opportunity Tease', 'Public Tampering', 'Loyalty Test'],
    },
}

TARGET_RESPONSES = [
    'defends_brand', 'rejects_recruiter', 'accepts_tease', 'stays_silent', 'likes_only',
    'quote_attitude', 'starts_rumor', 'demands_booking', 'loyalty_up', 'loyalty_down', 'requests_gm_meeting',
]

BRAND_DEFENSE_LINES = {
    'NXT': [
        'Keep our roster\'s name out your mouth. If you want war, say that.',
        'NXT built this brand — tampering tweets don\'t scare us.',
    ],
    'SmackDown': [
        'Culture Pulse sees everything. Back off our stars.',
        'You want smoke? SmackDown has the receipts.',
    ],
    'WCW': [
        'Sports Desk flagged this tampering. WCW answers on the ring, not Twitter.',
        'Our athletes aren\'t for sale on social media.',
    ],
}

TARGET_RESPONSE_LINES = {
    'defends_brand': [
        'Funny how everybody sees it except the people writing my checks.',
        'I bleed this brand until they give me a reason not to.',
        'My contract says {comp}. Your tweet says desperate.',
    ],
    'rejects_recruiter': [
        'Hard pass. I know where I belong.',
        'Nice try. Not today.',
    ],
    'accepts_tease': [
        '…interesting. DM me.',
        'You might be right. We\'ll see.',
    ],
    'stays_silent': [
        '(no public reply — but the like button tells a story)',
    ],
    'likes_only': [
        '(liked the tweet — no comment)',
    ],
    'quote_attitude': [
        'Bold of you to tweet that where my GM can see it.',
        'Clock\'s ticking alright — just not the way you think.',
    ],
    'starts_rumor': [
        'Maybe it\'s time people ask why I\'m still here.',
    ],
    'demands_booking': [
        'Book me right or watch this get louder.',
    ],
    'loyalty_up': [
        'Even broke, this is my brand. I\'m not running when things get hard.',
    ],
    'requests_gm_meeting': [
        'GM office. Tomorrow. Non-negotiable.',
    ],
}


def ensure_recruitment_state():
    if 'twitter_recruitment_history' not in st.session_state:
        st.session_state.twitter_recruitment_history = []
    if 'twitter_manual_gm_response' not in st.session_state:
        st.session_state.twitter_manual_gm_response = False
    for w in st.session_state.get('roster', []):
        w.setdefault('recruitment_interest', {})
        w.setdefault('fa_rumor_heat', 0)
        w.setdefault('tampering_flags', 0)


def morale_tier(morale):
    m = int(morale or 50)
    if m >= 80:
        return 'very_loyal', 'Very loyal (80–100)'
    if m >= 60:
        return 'stable', 'Stable (60–79)'
    if m >= 40:
        return 'frustrated', 'Frustrated (40–59)'
    if m >= 20:
        return 'unhappy', 'Unhappy (20–39)'
    return 'critical', 'Very unhappy (0–19)'


def recruitment_vulnerability_score(target, target_comp, recruiter_comp, crisis_is_fn, get_budget_fn):
    """0–100 how recruitable the target is right now."""
    if not target or target.get('company') != target_comp:
        return 0, []
    score = 0
    reasons = []
    morale = int(target.get('morale', 50))
    loyalty = int(target.get('brand_loyalty', 50))
    tier, _ = morale_tier(morale)
    tier_bonus = {'critical': 28, 'unhappy': 20, 'frustrated': 12, 'stable': 4, 'very_loyal': -15}
    score += tier_bonus.get(tier, 0)
    if tier in ('critical', 'unhappy', 'frustrated'):
        reasons.append(f'Morale {morale} ({tier.replace("_", " ")})')
    if loyalty < 40:
        score += 15
        reasons.append(f'Low brand loyalty ({loyalty})')
    elif loyalty >= 75:
        score -= 12
    wk = int(st.session_state.get('week', 0))
    lb = target.get('last_booked_week')
    if lb is not None and wk - int(lb) >= 4:
        score += 10
        reasons.append('Not booked recently')
    if int(target.get('booking_satisfaction', 60)) < 45:
        score += 8
        reasons.append('Poor booking satisfaction')
    if int(target.get('contract_weeks_remaining', 99)) <= 12:
        score += 12
        reasons.append('Expiring contract')
    if target.get('rejected_pay_cut'):
        score += 10
        reasons.append('Rejected pay cut')
    if target.get('requested_release'):
        score += 14
        reasons.append('Requested release')
    if target.get('renewal_status') in ('Rejected', 'Wants More Money', 'Refused Renewal', 'Testing Free Agency'):
        score += 10
        reasons.append(target.get('renewal_status'))
    if int(target.get('momentum', 50)) < 42:
        score += 6
        reasons.append('Low momentum')
    if crisis_is_fn(target_comp):
        score += 14
        reasons.append(f'{target_comp} in Financial Crisis')
    try:
        from bfg_crisis import brand_fit_score
        fit_new = brand_fit_score(target, recruiter_comp)
        fit_cur = brand_fit_score(target, target_comp)
        if fit_new > fit_cur + 8:
            score += 8
            reasons.append(f'Better brand fit at {recruiter_comp}')
    except ImportError:
        pass
    score = max(0, min(100, score))
    return score, reasons


def estimate_tampering(tweet_type, text):
    base = TAMPERING_BY_TYPE.get(tweet_type, 'medium')
    t = (text or '').lower()
    if re.search(r'\$\d|million|pay you|contract offer|sign with|we\'ll pay', t):
        return 'high', 'Direct money/contract language detected'
    if 'come to' in t and ('champion' in t or 'world title' in t):
        return 'high', 'Public contract/title promise'
    if base == 'high':
        return 'high', 'Tweet type is high tampering risk'
    if base == 'low':
        return 'low', 'Subtle tease — low commissioner risk'
    return 'medium', 'Direct recruitment — warning possible'


def suggest_recruit_tweet(recruiter_name, recruiter_comp, target_name, target_comp, tweet_type):
    style = BRAND_RECRUIT_STYLE.get(recruiter_comp, {})
    templates = {
        'Friendly Recruitment': f"@{target_name.split()[0]} — you'd be appreciated over here. {recruiter_comp} sees stars different.",
        'Dream Match Tease': f"Imagine {recruiter_name} and {target_name} main-eventing on the same brand. Just saying.",
        'Brand Shot': f"Looks like they forgot what they had over there. {recruiter_comp} knows how to make stars.",
        'Sponsor Opportunity Tease': f"{target_name} — {style.get('tags', 'big partners')} live on {recruiter_comp}. You know where to find us.",
        'Sports Opportunity Tease': f"You want that ESPN spotlight? {recruiter_comp} is where athletes become legends.",
        'Culture Opportunity Tease': f"Grammys, Sony, PRIME, red carpets — {recruiter_comp} is calling.",
        'Loyalty Test': f"They keep disrespecting you, {target_name}. How long you staying quiet?",
        'Contract Rumor': f"Clock's ticking on that {target_comp} contract, {target_name}.",
        'Public Tampering': f"Come to {recruiter_comp} and we'll make you a world champion.",
        'Subtle Tease': f"Some people look better in {recruiter_comp[:3]} colors.",
    }
    line = templates.get(tweet_type, style.get('line', f'{recruiter_comp} is watching.'))
    if len(line) > 280:
        line = line[:277] + '…'
    return line


def pick_target_response(target, recruiter_comp, target_comp, tweet_type, vuln_score, loyalty, tampering, manual=None):
    if manual and manual in TARGET_RESPONSES:
        return manual
    morale = int(target.get('morale', 50))
    tier, _ = morale_tier(morale)
    weights = {k: 8 for k in TARGET_RESPONSES}
    if tier == 'very_loyal' or loyalty >= 78:
        weights['defends_brand'] += 35
        weights['loyalty_up'] += 20
        weights['rejects_recruiter'] += 25
        weights['accepts_tease'] -= 10
    elif tier == 'critical' or loyalty < 35:
        weights['loyalty_down'] += 25
        weights['accepts_tease'] += 20
        weights['starts_rumor'] += 15
        weights['demands_booking'] += 18
        weights['requests_gm_meeting'] += 12
    elif tier in ('unhappy', 'frustrated'):
        weights['quote_attitude'] += 18
        weights['likes_only'] += 14
        weights['loyalty_down'] += 12
    if vuln_score >= 55:
        weights['accepts_tease'] += 15
        weights['likes_only'] += 10
    if vuln_score < 25:
        weights['rejects_recruiter'] += 20
    if tampering == 'high':
        weights['defends_brand'] += 10
        weights['quote_attitude'] += 8
    if tweet_type in ('Loyalty Test', 'Brand Shot'):
        weights['quote_attitude'] += 10
    if tweet_type == 'Friendly Recruitment':
        weights['stays_silent'] += 12
        weights['likes_only'] += 10
    keys = list(weights.keys())
    vals = [max(1, weights[k]) for k in keys]
    return random.choices(keys, weights=vals, k=1)[0]


def response_text(outcome, target, target_comp, recruiter_comp):
    pool = TARGET_RESPONSE_LINES.get(outcome, TARGET_RESPONSE_LINES['stays_silent'])
    line = random.choice(pool)
    return line.replace('{comp}', target_comp)


def brand_counter_response(target_comp, tampering):
    lines = BRAND_DEFENSE_LINES.get(target_comp, ['Ownership has been notified.'])
    role = random.choice(['GM', 'Owner'])
    name = st.session_state.company_profiles.get(target_comp, {}).get('gm') or st.session_state.company_profiles.get(target_comp, {}).get('owner') or f'{target_comp} Office'
    text = random.choice(lines)
    if tampering == 'high':
        text += ' Commissioner may review this tampering.'
    return {'role': role, 'name': name, 'text': text[:280]}


def compute_recruitment_effects(target, recruiter, recruiter_comp, target_comp, tweet_type, vuln_score, loyalty, tampering, response_outcome, brand_fit_delta=0):
    morale = int(target.get('morale', 50))
    tier, _ = morale_tier(morale)
    eff = {
        'target_morale': 0, 'target_loyalty': 0, 'target_buzz': 0, 'target_controversy': 0,
        'recruiter_pop': 0, 'recruiter_momentum': 0, 'fa_interest': 0, 'bidding_risk': 0,
        'sponsor_conf_target': 0, 'sponsor_conf_recruiter': 0, 'prestige_target': 0,
        'rivalry_heat': 5, 'locker_room': 0,
    }
    base = max(0, (vuln_score - 20) // 10)
    if tier == 'very_loyal':
        base = max(0, base - 3)
    if response_outcome in ('defends_brand', 'loyalty_up', 'rejects_recruiter'):
        eff['target_loyalty'] += random.randint(2, 6)
        eff['target_morale'] += random.randint(0, 3)
    elif response_outcome in ('loyalty_down', 'accepts_tease', 'starts_rumor'):
        eff['target_loyalty'] -= random.randint(3, 8)
        eff['target_morale'] -= random.randint(2, 6)
        eff['fa_interest'] += random.randint(4, 12) + base
    elif response_outcome in ('demands_booking', 'requests_gm_meeting', 'quote_attitude'):
        eff['target_morale'] -= random.randint(3, 5)
        eff['target_loyalty'] -= random.randint(1, 4)
        eff['fa_interest'] += random.randint(2, 6)
    elif response_outcome == 'likes_only':
        eff['target_morale'] -= random.randint(1, 3)
        eff['fa_interest'] += random.randint(3, 7)
    else:
        eff['target_morale'] -= random.randint(0, 2)
    if tampering == 'high':
        eff['target_controversy'] += random.randint(4, 10)
        eff['sponsor_conf_target'] -= random.randint(3, 8)
        eff['sponsor_conf_recruiter'] -= random.randint(2, 6)
        eff['prestige_target'] -= 2
    elif tampering == 'medium':
        eff['sponsor_conf_target'] -= random.randint(0, 3)
    eff['target_buzz'] += random.randint(5, 14) + base // 2
    eff['recruiter_pop'] += random.randint(0, 3)
    eff['recruiter_momentum'] += random.randint(1, 4)
    if vuln_score >= 60:
        eff['bidding_risk'] += random.randint(8, 20)
    try:
        from bfg_crisis import is_financial_crisis
        if is_financial_crisis(target_comp):
            eff['bidding_risk'] += random.randint(5, 15)
    except ImportError:
        pass
    if brand_fit_delta > 0:
        eff['fa_interest'] += min(10, brand_fit_delta // 5)
    interest = target.setdefault('recruitment_interest', {})
    interest[recruiter_comp] = min(100, int(interest.get(recruiter_comp, 0)) + eff['fa_interest'])
    return eff


def build_ai_explanation(target, recruiter_comp, target_comp, vuln_score, reasons, response_outcome, effects, tampering):
    parts = []
    if vuln_score >= 50:
        parts.append(f"Recruitment pressure landed because {target.get('name')} is vulnerable ({vuln_score}/100).")
    else:
        parts.append(f"Limited effect — target not very recruitable ({vuln_score}/100).")
    if reasons:
        parts.append('Factors: ' + '; '.join(reasons[:4]) + '.')
    parts.append(f"Target reaction: {response_outcome.replace('_', ' ')}.")
    if effects.get('fa_interest', 0) > 5:
        parts.append(f"Free agency / bidding interest toward {recruiter_comp} +{effects['fa_interest']}.")
    if effects.get('bidding_risk', 0) >= 12:
        parts.append('AI flags wrestler as bidding-war vulnerable if crisis continues.')
    if tampering == 'high':
        parts.append('High tampering risk — sponsor and commissioner fallout possible.')
    elif tampering == 'medium':
        parts.append('Medium tampering — rival GM may respond.')
    return ' '.join(parts)


def process_recruitment_tweet(recruiter, target, recruiter_comp, target_comp, tweet_type, tweet_text,
                              find_fn, is_champ_fn, crisis_adjust_loyalty_fn, manual_target_response=None,
                              manual_brand_action=None, post_tweet_fn=None):
    """
    Full recruitment flow. Returns dict with posts, effects, record.
    post_tweet_fn(comp, kind, name, handle, role, typ, text, mention, extra) -> post
    """
    ensure_recruitment_state()
    if recruiter_comp == target_comp:
        return {'ok': False, 'error': 'Cannot recruit within the same brand.'}
    if not target or target.get('company') != target_comp:
        return {'ok': False, 'error': 'Invalid target wrestler.'}
    if not recruiter:
        return {'ok': False, 'error': 'Invalid recruiter.'}
    try:
        from bfg_crisis import is_financial_crisis, brand_fit_score
        crisis_fn = is_financial_crisis
        fit_new = brand_fit_score(target, recruiter_comp)
        fit_cur = brand_fit_score(target, target_comp)
        brand_fit_delta = fit_new - fit_cur
    except ImportError:
        crisis_fn = lambda c: False
        brand_fit_delta = 0
    vuln_score, reasons = recruitment_vulnerability_score(target, target_comp, recruiter_comp, crisis_fn, None)
    loyalty = int(target.get('brand_loyalty', 50))
    tampering, tamper_note = estimate_tampering(tweet_type, tweet_text)
    if vuln_score < 15 and loyalty >= 70:
        return {'ok': False, 'error': f'{target["name"]} is too loyal and stable right now (vulnerability {vuln_score}/100).'}
    response_outcome = pick_target_response(target, recruiter_comp, target_comp, tweet_type, vuln_score, loyalty, tampering, manual_target_response)
    effects = compute_recruitment_effects(target, recruiter, recruiter_comp, target_comp, tweet_type, vuln_score, loyalty, tampering, response_outcome, brand_fit_delta)
    explanation = build_ai_explanation(target, recruiter_comp, target_comp, vuln_score, reasons, response_outcome, effects, tampering)
    target_morale = int(target.get('morale', 50))
    target['morale'] = max(0, min(100, target_morale + effects['target_morale']))
    if crisis_adjust_loyalty_fn and effects['target_loyalty']:
        crisis_adjust_loyalty_fn(target, effects['target_loyalty'], f'Twitter recruitment from {recruiter_comp}')
    target['twitter_buzz'] = min(100, int(target.get('twitter_buzz', 0)) + effects['target_buzz'])
    target['controversy_risk'] = min(100, int(target.get('controversy_risk', 20)) + effects['target_controversy'])
    target['fa_rumor_heat'] = min(100, int(target.get('fa_rumor_heat', 0)) + effects['fa_interest'])
    if recruiter:
        recruiter['popularity'] = min(100, int(recruiter.get('popularity', 50)) + effects['recruiter_pop'])
        recruiter['momentum'] = min(100, int(recruiter.get('momentum', 50)) + effects['recruiter_momentum'])
    prof_t = st.session_state.company_profiles.setdefault(target_comp, {})
    prof_r = st.session_state.company_profiles.setdefault(recruiter_comp, {})
    prof_t['sponsor_confidence'] = max(1, min(100, int(prof_t.get('sponsor_confidence', 85)) + effects['sponsor_conf_target']))
    prof_r['sponsor_confidence'] = max(1, min(100, int(prof_r.get('sponsor_confidence', 85)) + effects['sponsor_conf_recruiter']))
    posts = []
    mention = target['name']
    if post_tweet_fn:
        handle = recruiter.get('handle') or ('@' + recruiter['name'].lower().replace(' ', '_'))
        main = post_tweet_fn(
            recruiter_comp, 'wrestler', recruiter['name'], handle,
            'Wrestler', 'Recruitment / Tampering', tweet_text, mention,
            {'topic': 'Other Company Comment', 'tone': 'petty', 'ai_generated': True, 'interaction': 'recruitment',
             'recruitment_target': target['name'], 'recruitment_type': tweet_type, 'tampering': tampering},
        )
        posts.append(main)
        resp_txt = response_text(response_outcome, target, target_comp, recruiter_comp)
        if response_outcome not in ('stays_silent', 'likes_only') and resp_txt and not resp_txt.startswith('('):
            th = target.get('handle') or ('@' + target['name'].lower().replace(' ', '_'))
            rpost = post_tweet_fn(
                target_comp, 'wrestler', target['name'], th,
                'Wrestler', 'Recruitment Response', resp_txt, recruiter['name'],
                {'topic': 'Contract', 'tone': 'bitter', 'reply_to_id': main.get('id'), 'ai_generated': True},
            )
            posts.append(rpost)
        elif response_outcome == 'likes_only' and main:
            main['recruitment_liked'] = True
        if manual_brand_action != 'ignore' and random.random() < (0.75 if tampering in ('high', 'medium') else 0.35):
            bc = brand_counter_response(target_comp, tampering)
            if post_tweet_fn:
                sp = next((s for s in st.session_state.staff.get(target_comp, []) if bc['role'] in s.get('role', '')), None)
                if sp:
                    bpost = post_tweet_fn(target_comp, 'staff', sp['name'], sp['handle'], sp['role'], 'Tampering Response', bc['text'], recruiter_comp,
                                          {'topic': 'Other Company Comment', 'tone': 'corporate', 'ai_generated': True})
                    posts.append(bpost)
    flag = f'Twitter recruitment: {recruiter["name"]} → {target["name"]}'
    st.session_state.setdefault('storyline_flags', []).insert(0, {
        'week': st.session_state.get('week', 0),
        'flag': flag,
        'target': target['name'],
        'company': target_comp,
        'recruiter': recruiter['name'],
        'recruiter_company': recruiter_comp,
        'tweet_type': tweet_type,
        'response': response_outcome,
        'tampering': tampering,
        'notes': (tweet_text or '')[:120],
        'follow_up': 'Monitor morale, loyalty, and bidding war risk.',
        'unresolved': True,
    })
    st.session_state.setdefault('twitter_drama', []).insert(0, {
        'week': st.session_state.get('week', 0),
        'wrestler': target['name'],
        'company': target_comp,
        'topic': 'Recruitment / Tampering',
        'text': tweet_text[:200],
        'unresolved': True,
    })
    if effects['bidding_risk'] >= 15 and crisis_fn(target_comp):
        st.session_state.news_feed.insert(0, f"**BIDDING RUMOR:** {target['name']} ({target_comp}) may listen to {recruiter_comp} after Twitter tampering.")
    record = {
        'week': st.session_state.get('week', 0),
        'recruiter': recruiter['name'], 'recruiter_company': recruiter_comp,
        'target': target['name'], 'target_company': target_comp,
        'tweet_type': tweet_type, 'text': tweet_text, 'tampering': tampering,
        'vulnerability': vuln_score, 'response': response_outcome, 'effects': effects,
        'explanation': explanation, 'reasons': reasons,
    }
    st.session_state.twitter_recruitment_history.insert(0, record)
    return {
        'ok': True, 'record': record, 'posts': posts, 'effects': effects,
        'response_outcome': response_outcome, 'response_text': response_text(response_outcome, target, target_comp, recruiter_comp),
        'tampering': tampering, 'tamper_note': tamper_note, 'vulnerability': vuln_score,
        'reasons': reasons, 'explanation': explanation, 'brand_fit_delta': brand_fit_delta,
    }
