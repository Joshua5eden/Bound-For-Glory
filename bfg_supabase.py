"""Supabase game_saves — keyed by session_id + company + save_type + save_key."""
import json
from datetime import datetime, timezone

PLAYABLE = ['NXT', 'SmackDown', 'WCW']
COMPANY_ALL = 'All'

_client = None


def supabase_configured():
 try:
  import streamlit as st
  url = (st.secrets.get('SUPABASE_URL') or '').strip()
  key = (st.secrets.get('SUPABASE_KEY') or '').strip()
  return bool(url and key)
 except Exception:
  return False


def _get_secrets():
 import streamlit as st
 return st.secrets['SUPABASE_URL'].strip(), st.secrets['SUPABASE_KEY'].strip()


def get_client():
 global _client
 if _client is None:
  from supabase import create_client
  url, key = _get_secrets()
  _client = create_client(url, key)
 return _client


def _now_iso():
 return datetime.now(timezone.utc).isoformat()


def upsert_save(session_id, company, save_type, save_key, payload):
 row = {
  'session_id': session_id,
  'company': company,
  'save_type': save_type,
  'save_key': save_key or '*',
  'payload': payload,
  'updated_at': _now_iso(),
 }
 get_client().table('game_saves').upsert(row, on_conflict='session_id,company,save_type,save_key').execute()


def upsert_saves(rows):
 if not rows:
  return
 now = _now_iso()
 for r in rows:
  r.setdefault('save_key', '*')
  r['updated_at'] = now
 get_client().table('game_saves').upsert(rows, on_conflict='session_id,company,save_type,save_key').execute()


def fetch_session_saves(session_id):
 res = get_client().table('game_saves').select('company,save_type,save_key,payload,updated_at').eq('session_id', session_id).execute()
 return res.data or []


def find_session_by_invite(invite_code):
 code = (invite_code or '').strip().upper()
 if not code:
  return None
 res = (
  get_client()
  .table('game_saves')
  .select('session_id,payload')
  .eq('save_type', 'private_session')
  .eq('save_key', code)
  .limit(1)
  .execute()
 )
 rows = res.data or []
 return rows[0] if rows else None


def save_private_session_meta(session_id, meta):
 upsert_save(session_id, COMPANY_ALL, 'private_session', 'meta', meta)
 inv = (meta.get('invite_code') or '').strip().upper()
 if inv:
  upsert_save(session_id, COMPANY_ALL, 'private_session', inv, meta)


def _filter_company(items, company, field='company'):
 return [x for x in (items or []) if isinstance(x, dict) and x.get(field) == company]


def _filter_company_prefix(dct, company):
 prefix = f'{company}:'
 return {k: v for k, v in (dct or {}).items() if str(k).startswith(prefix)}


def build_save_rows(session_id, payload, week_state=None, pending_trades=None):
 """Split universe payload into game_saves rows so brands do not overwrite each other."""
 rows = []
 meta = {
  'game_name': payload.get('game_name', ''),
  'session_id': session_id,
  'last_updated_by': payload.get('last_updated_by', ''),
  'last_updated_at': payload.get('last_updated_at', ''),
 }
 rows.append({'session_id': session_id, 'company': COMPANY_ALL, 'save_type': 'private_session', 'save_key': 'meta', 'payload': meta})

 ws = week_state or {}
 rows.append({
  'session_id': session_id,
  'company': COMPANY_ALL,
  'save_type': 'player_roles',
  'save_key': 'week_state',
  'payload': {
   'week_progress': ws.get('companies', payload.get('week_progress', {})),
   'player_assignments': ws.get('player_assignments', payload.get('player_assignments', {})),
   'week': ws.get('current_week', payload.get('week', 0)),
   'month': payload.get('month', 1),
   'year': payload.get('year', 1),
  },
 })

 rows.append({
  'session_id': session_id,
  'company': COMPANY_ALL,
  'save_type': 'pending_trades',
  'save_key': 'queue',
  'payload': {'pending_trades': pending_trades if pending_trades is not None else payload.get('pending_trades', [])},
 })

 rows.append({
  'session_id': session_id,
  'company': COMPANY_ALL,
  'save_type': 'free_agency',
  'save_key': 'pool',
  'payload': {
   'free_agency_pool': payload.get('free_agency_pool', []),
   'negotiation_history': payload.get('negotiation_history', []),
   'contract_warnings': payload.get('contract_warnings', []),
   'departed': payload.get('departed', []),
  },
 })

 rows.append({
  'session_id': session_id,
  'company': COMPANY_ALL,
  'save_type': 'trades',
  'save_key': 'history',
  'payload': {'trade_history': payload.get('trade_history', [])},
 })

 rows.append({
  'session_id': session_id,
  'company': COMPANY_ALL,
  'save_type': 'power_rankings',
  'save_key': 'global',
  'payload': {
   'power_rankings': payload.get('power_rankings', []),
   'previous_power_rankings': payload.get('previous_power_rankings', []),
   'power_ranking_history': payload.get('power_ranking_history', []),
   'rankings_include_not_debuted': payload.get('rankings_include_not_debuted', False),
  },
 })

 rows.append({
  'session_id': session_id,
  'company': COMPANY_ALL,
  'save_type': 'universe_global',
  'save_key': 'shared',
  'payload': {
   'character_bible': payload.get('character_bible', {}),
   'staff_character_bible': payload.get('staff_character_bible', {}),
   'company_lore': payload.get('company_lore', {}),
   'company_profiles': payload.get('company_profiles', {}),
   'bank': payload.get('bank', {}),
   'news_feed': payload.get('news_feed', []),
   'nxt_unfiltered_hosts': payload.get('nxt_unfiltered_hosts', {}),
   'nxt_unfiltered_episodes': payload.get('nxt_unfiltered_episodes', []),
   'nxt_unfiltered_draft': payload.get('nxt_unfiltered_draft', {}),
   'last_nxt_unfiltered': payload.get('last_nxt_unfiltered', {}),
   'podcast_hosts_booking_enabled': payload.get('podcast_hosts_booking_enabled', False),
   'money_meter_flash': payload.get('money_meter_flash', {}),
   'finance_opening_applied': payload.get('finance_opening_applied', {}),
   'bidding_wars': payload.get('bidding_wars', []),
   'descriptor_recent': payload.get('descriptor_recent', {}),
   'twitter_manual_gm_response': payload.get('twitter_manual_gm_response', ''),
   'test_event_preview': payload.get('test_event_preview', {}),
   'logistics_reports': payload.get('logistics_reports', []),
   'cameo_library': payload.get('cameo_library', []),
   'film_projects': payload.get('film_projects', []),
   'yearly_attractions': payload.get('yearly_attractions', []),
   'attractions_locked': payload.get('attractions_locked', False),
   'attraction_year': payload.get('attraction_year', 1),
   'debut_history': payload.get('debut_history', []),
   'debut_warnings': payload.get('debut_warnings', []),
   'confirmed_story_debuts': payload.get('confirmed_story_debuts', []),
   'tag_team_overrides': payload.get('tag_team_overrides', {}),
   'wrestler_name_history': payload.get('wrestler_name_history', []),
   'custom_tag_teams': payload.get('custom_tag_teams', {}),
   'roster_show_staff': payload.get('roster_show_staff', {}),
   'breakup_history': payload.get('breakup_history', []),
   'former_tag_teams': payload.get('former_tag_teams', []),
   'exclusive_activity_history': payload.get('exclusive_activity_history', []),
   'exclusive_generated_ideas': payload.get('exclusive_generated_ideas', []),
   'exclusive_violations': payload.get('exclusive_violations', []),
   'company_crisis': payload.get('company_crisis', {}),
   'brand_loyalty_history': payload.get('brand_loyalty_history', []),
   'appearance_history': payload.get('appearance_history', []),
   'last_story_analysis': payload.get('last_story_analysis', {}),
   'last_grade': payload.get('last_grade', {}),
   'story_parse': payload.get('story_parse', {}),
  },
 })

 cal = payload.get('schedule_calendar', [])
 cal_locked = payload.get('calendar_locked', False)
 cal_notes = payload.get('calendar_ai_notes', [])
 sponsor_all = payload.get('sponsor_objectives', [])
 storylines_all = payload.get('storylines', [])
 flags_all = payload.get('storyline_flags', [])
 book_drafts = payload.get('book_show_drafts', {})
 book_archive = payload.get('book_show_archive', {})
 weekly_hist = payload.get('weekly_history', [])
 perf_index = payload.get('weekly_performance_index', {})
 finance_ledger = payload.get('finance_ledger', [])
 show_fin_reports = payload.get('show_finance_reports', [])
 company_fin = payload.get('company_finance', {})
 company_budgets = payload.get('company_budgets', {})
 roster_all = payload.get('roster', [])
 staff_all = payload.get('staff', {})
 champions_all = payload.get('champions', {})
 title_prestige = payload.get('title_prestige', {})
 champion_meta = payload.get('champion_meta', {})
 champion_history = payload.get('champion_history', [])
 title_defense = payload.get('title_defense_history', [])
 tweets = payload.get('twitter_posts', [])
 random_ev = payload.get('random_event_history', [])
 rivalries = payload.get('rivalries', [])
 attractions = payload.get('yearly_attractions', [])
 attr_hist = payload.get('attraction_history', [])
 team_profiles = payload.get('team_profiles', {})
 factions = payload.get('factions', {})

 for co in PLAYABLE:
  rows.append({
   'session_id': session_id,
   'company': co,
   'save_type': 'calendar_events',
   'save_key': 'schedule',
   'payload': {
    'schedule_calendar': _filter_company(cal, co),
    'calendar_locked': cal_locked,
    'calendar_ai_notes': [n for n in cal_notes if co in str(n)],
   },
  })
  rows.append({
   'session_id': session_id,
   'company': co,
   'save_type': 'book_show',
   'save_key': 'drafts',
   'payload': {
    'book_show_drafts': _filter_company_prefix(book_drafts, co),
    'book_show_archive': _filter_company_prefix(book_archive, co),
   },
  })
  rows.append({
   'session_id': session_id,
   'company': co,
   'save_type': 'booking',
   'save_key': 'mode',
   'payload': {
    'booking_mode': payload.get('booking_mode', 'Match Card Mode'),
    'long_story_draft': payload.get('long_story_draft', ''),
    'saved_show': payload.get('saved_show'),
    'ai_booked_show': payload.get('ai_booked_show', False),
    'show_user_edited': payload.get('show_user_edited', False),
   },
  })
  rows.append({
   'session_id': session_id,
   'company': co,
   'save_type': 'storylines',
   'save_key': 'tracker',
   'payload': {
    'storylines': _filter_company(storylines_all, co),
    'storyline_flags': _filter_company(flags_all, co),
   },
  })
  rows.append({
   'session_id': session_id,
   'company': co,
   'save_type': 'sponsor_objectives',
   'save_key': 'objectives',
   'payload': {'sponsor_objectives': _filter_company(sponsor_all, co)},
  })
  rows.append({
   'session_id': session_id,
   'company': co,
   'save_type': 'weekly_performance',
   'save_key': 'history',
   'payload': {
    'weekly_history': _filter_company(weekly_hist, co),
    'weekly_performance_index': {k: v for k, v in (perf_index or {}).items() if str(k).startswith(f'{co}:')},
   },
  })
  rows.append({
   'session_id': session_id,
   'company': co,
   'save_type': 'finance',
   'save_key': 'ledger',
   'payload': {
    'company_finance': {co: company_fin.get(co, {})},
    'company_budgets': {co: company_budgets.get(co, 0)},
    'finance_ledger': _filter_company(finance_ledger, co),
    'show_finance_reports': _filter_company(show_fin_reports, co),
   },
  })
  rows.append({
   'session_id': session_id,
   'company': co,
   'save_type': 'roster',
   'save_key': 'edits',
   'payload': {
    'roster': _filter_company(roster_all, co),
    'staff': _filter_company(staff_all, co),
    'team_profiles': {k: v for k, v in (team_profiles or {}).items() if co in str(k)},
    'factions': _filter_company(factions, co),
   },
  })
  rows.append({
   'session_id': session_id,
   'company': co,
   'save_type': 'champions',
   'save_key': 'titles',
   'payload': {
    'champions': {co: champions_all.get(co, {})},
    'title_prestige': {k: v for k, v in (title_prestige or {}).items() if str(k).startswith(co)},
    'champion_meta': {k: v for k, v in (champion_meta or {}).items() if co in str(k)},
    'champion_history': _filter_company(champion_history, co),
    'title_defense_history': _filter_company(title_defense, co),
   },
  })
  rows.append({
   'session_id': session_id,
   'company': co,
   'save_type': 'tweets',
   'save_key': 'feed',
   'payload': {
    'twitter_posts': _filter_company(tweets, co),
    'twitter_drama': _filter_company(payload.get('twitter_drama', []), co),
    'twitter_recruitment_history': _filter_company(payload.get('twitter_recruitment_history', []), co),
   },
  })
  rows.append({
   'session_id': session_id,
   'company': co,
   'save_type': 'random_events',
   'save_key': 'log',
   'payload': {'random_event_history': _filter_company(random_ev, co)},
  })
  rows.append({
   'session_id': session_id,
   'company': co,
   'save_type': 'rivalries',
   'save_key': 'heat',
   'payload': {'rivalries': _filter_company(rivalries, co)},
  })
  rows.append({
   'session_id': session_id,
   'company': co,
   'save_type': 'attractions',
   'save_key': 'yearly',
   'payload': {'attraction_history': _filter_company(attr_hist, co)},
  })
  rows.append({
   'session_id': session_id,
   'company': co,
   'save_type': 'season_awards',
   'save_key': 'inputs',
   'payload': {
    'weekly_history': _filter_company(weekly_hist, co),
    'storylines': _filter_company(storylines_all, co),
    'sponsor_objectives': _filter_company(sponsor_all, co),
    'company_budgets': {co: company_budgets.get(co, 0)},
   },
  })

 return rows


def sync_session_saves(session_id, payload, week_state=None, pending_trades=None):
 if not supabase_configured() or not session_id or session_id == 'local':
  return False
 try:
  upsert_saves(build_save_rows(session_id, payload, week_state, pending_trades))
  return True
 except Exception as ex:
  raise RuntimeError(f'Supabase save failed: {ex}') from ex


def _merge_dict(target, source):
 for k, v in (source or {}).items():
  if isinstance(v, dict) and isinstance(target.get(k), dict):
   _merge_dict(target[k], v)
  else:
   target[k] = v


def _merge_list_by_company(existing, new_items, company, field='company'):
 kept = [x for x in (existing or []) if not (isinstance(x, dict) and x.get(field) == company)]
 return kept + list(new_items or [])


def merge_rows_to_payload(rows):
 """Reconstruct a universe-shaped dict from game_saves rows."""
 out = {
  'roster': [],
  'staff': [],
  'champions': {},
  'title_prestige': {},
  'champion_meta': {},
  'champion_history': [],
  'title_defense_history': [],
  'storylines': [],
  'storyline_flags': [],
  'sponsor_objectives': [],
  'weekly_history': [],
  'weekly_performance_index': {},
  'finance_ledger': [],
  'show_finance_reports': [],
  'company_finance': {},
  'company_budgets': {},
  'schedule_calendar': [],
  'book_show_drafts': {},
  'book_show_archive': {},
  'twitter_posts': [],
  'twitter_drama': [],
  'twitter_recruitment_history': [],
  'attraction_history': [],
  'random_event_history': [],
  'rivalries': [],
  'attraction_history': [],
  'team_profiles': {},
  'factions': [],
  'pending_trades': [],
  'trade_history': [],
  'free_agency_pool': [],
  'negotiation_history': [],
  'contract_warnings': [],
  'departed': [],
  'power_rankings': [],
  'previous_power_rankings': [],
  'power_ranking_history': [],
 }

 if not rows:
  return None

 for row in rows:
  co = row.get('company', COMPANY_ALL)
  stype = row.get('save_type', '')
  payload = row.get('payload') or {}
  if not isinstance(payload, dict):
   try:
    payload = json.loads(payload)
   except Exception:
    payload = {}

  if stype == 'private_session' and row.get('save_key') == 'meta':
   out['game_name'] = payload.get('game_name', out.get('game_name', ''))
   out['last_updated_by'] = payload.get('last_updated_by', '')
   out['last_updated_at'] = payload.get('last_updated_at', '')
  elif stype == 'player_roles':
   out['week_progress'] = payload.get('week_progress', {})
   out['player_assignments'] = payload.get('player_assignments', {})
   out['week'] = payload.get('week', 0)
   out['month'] = payload.get('month', 1)
   out['year'] = payload.get('year', 1)
  elif stype == 'pending_trades':
   out['pending_trades'] = payload.get('pending_trades', [])
  elif stype == 'free_agency':
   out['free_agency_pool'] = payload.get('free_agency_pool', [])
   out['negotiation_history'] = payload.get('negotiation_history', [])
   out['contract_warnings'] = payload.get('contract_warnings', [])
   out['departed'] = payload.get('departed', [])
  elif stype == 'trades':
   out['trade_history'] = payload.get('trade_history', [])
  elif stype == 'power_rankings':
   out.update({k: payload.get(k, out.get(k)) for k in payload})
  elif stype == 'universe_global':
   _merge_dict(out, payload)
  elif stype == 'calendar_events' and co in PLAYABLE:
   out['schedule_calendar'].extend(payload.get('schedule_calendar', []))
   if payload.get('calendar_locked'):
    out['calendar_locked'] = True
   notes = payload.get('calendar_ai_notes', [])
   if notes:
    out.setdefault('calendar_ai_notes', []).extend(notes)
  elif stype == 'book_show' and co in PLAYABLE:
   out['book_show_drafts'].update(payload.get('book_show_drafts', {}))
   out['book_show_archive'].update(payload.get('book_show_archive', {}))
  elif stype == 'booking' and co in PLAYABLE:
   for k in ('booking_mode', 'long_story_draft', 'saved_show', 'ai_booked_show', 'show_user_edited'):
    if k in payload:
     out[k] = payload[k]
  elif stype == 'storylines' and co in PLAYABLE:
   out['storylines'].extend(payload.get('storylines', []))
   out['storyline_flags'].extend(payload.get('storyline_flags', []))
  elif stype == 'sponsor_objectives' and co in PLAYABLE:
   out['sponsor_objectives'].extend(payload.get('sponsor_objectives', []))
  elif stype == 'weekly_performance' and co in PLAYABLE:
   out['weekly_history'].extend(payload.get('weekly_history', []))
   out['weekly_performance_index'].update(payload.get('weekly_performance_index', {}))
  elif stype == 'finance' and co in PLAYABLE:
   out['company_finance'].update(payload.get('company_finance', {}))
   out['company_budgets'].update(payload.get('company_budgets', {}))
   out['finance_ledger'].extend(payload.get('finance_ledger', []))
   out['show_finance_reports'].extend(payload.get('show_finance_reports', []))
  elif stype == 'roster' and co in PLAYABLE:
   out['roster'].extend(payload.get('roster', []))
   out['staff'].extend(payload.get('staff', []))
   out['team_profiles'].update(payload.get('team_profiles', {}))
   out['factions'].extend(payload.get('factions', []))
  elif stype == 'champions' and co in PLAYABLE:
   out['champions'].update(payload.get('champions', {}))
   out['title_prestige'].update(payload.get('title_prestige', {}))
   out['champion_meta'].update(payload.get('champion_meta', {}))
   out['champion_history'].extend(payload.get('champion_history', []))
   out['title_defense_history'].extend(payload.get('title_defense_history', []))
  elif stype == 'tweets' and co in PLAYABLE:
   out['twitter_posts'].extend(payload.get('twitter_posts', []))
   out['twitter_drama'].extend(payload.get('twitter_drama', []))
   out['twitter_recruitment_history'].extend(payload.get('twitter_recruitment_history', []))
  elif stype == 'random_events' and co in PLAYABLE:
   out['random_event_history'].extend(payload.get('random_event_history', []))
  elif stype == 'rivalries' and co in PLAYABLE:
   out['rivalries'].extend(payload.get('rivalries', []))
  elif stype == 'attractions' and co in PLAYABLE:
   out['attraction_history'].extend(payload.get('attraction_history', []))

 out.setdefault('calendar_locked', False)
 out.setdefault('calendar_ai_notes', [])
 return out


def load_merged_universe(session_id, save_types=None):
 if not supabase_configured() or not session_id or session_id == 'local':
  return None
 try:
  rows = fetch_session_saves(session_id)
  if not rows:
   return None
  if save_types:
   rows = [r for r in rows if r.get('save_type') in save_types]
   if not rows:
    return None
  return merge_rows_to_payload(rows)
 except Exception:
  return None


def load_light_session(session_id):
 return load_merged_universe(session_id, save_types={'player_roles', 'pending_trades'})
