"""Wrestler name / ring name change — permanent wrestler_id, full universe rename."""
import re
import json
from datetime import datetime, timezone
from pathlib import Path

PLAYABLE = ['NXT', 'SmackDown', 'WCW']

_NAME_KEYS = frozenset({
 'name', 'wrestler', 'champion', 'holder', 'winner', 'loser', 'target', 'mention',
 'mentions', 'team_name', 'partner', 'member', 'member_name', 'featured', 'rival',
 'caller', 'callee', 'photo', 'star', 'talent', 'subject', 'poster', 'parent_author',
 'wrestler_obj', 'tag_team', 'faction', 'from', 'to', 'signed', 'released',
})

_SKIP_TEXT_KEYS = frozenset({'id', 'session_id', 'save_key', 'save_type', 'handle'})


def _slug(n):
 return re.sub(r'[^a-z0-9_]', '', (n or '').lower().replace(' ', '_').replace("'", '').replace('\u2019', ''))


def make_wrestler_id(name, company):
 base = f"W-{_slug(name)}-{_slug(company)}"
 return base[:96] if base else f"W-unknown-{_slug(company)}"


def ensure_wrestler_ids(roster):
 """Assign wrestler_id to every roster entry (stable after first assign)."""
 seen = set()
 for w in roster or []:
  if not isinstance(w, dict):
   continue
  wid = (w.get('wrestler_id') or '').strip()
  if not wid:
   wid = make_wrestler_id(w.get('name', ''), w.get('company', 'NXT'))
   base, n = wid, 2
   while wid in seen:
    wid = f'{base}-{n}'
    n += 1
   w['wrestler_id'] = wid
  seen.add(w['wrestler_id'])
  w.setdefault('ring_name', w.get('name', ''))
  w.setdefault('real_name', '')
  w.setdefault('nickname', '')
  w.setdefault('gimmick_name', '')


def find_by_wrestler_id(roster, wid):
 wid = (wid or '').strip()
 if not wid:
  return None
 return next((w for w in (roster or []) if w.get('wrestler_id') == wid), None)


def find_by_name(roster, name):
 name = (name or '').strip()
 if not name:
  return None
 return next((w for w in (roster or []) if w.get('name') == name), None)


def _replace_exact(val, old, new):
 if isinstance(val, str) and val == old:
  return new
 return val


def _replace_in_text(val, old, new):
 if not isinstance(val, str) or not old or old == new:
  return val
 if val == old:
  return new
 return val.replace(old, new)


def _walk_rename(obj, old, new, *, text_keys=False):
 """Recursively replace exact name matches in known fields and list items."""
 if obj is None:
  return obj
 if isinstance(obj, str):
  return _replace_in_text(obj, old, new) if text_keys else _replace_exact(obj, old, new)
 if isinstance(obj, list):
  out = []
  for item in obj:
   if isinstance(item, str) and item == old:
    out.append(new)
   else:
    out.append(_walk_rename(item, old, new, text_keys=text_keys))
  return out
 if isinstance(obj, dict):
  new_obj = {}
  for k, v in obj.items():
   nk = new if (isinstance(k, str) and k == old) else k
   if isinstance(v, str):
    if k in _SKIP_TEXT_KEYS:
     new_obj[nk] = v
    elif k in _NAME_KEYS or (not text_keys and v == old):
     new_obj[nk] = _replace_exact(v, old, new)
    elif text_keys and k in ('text', 'notes', 'summary', 'feedback', 'description', 'detail', 'line', 'message', 'label', 'reason', 'ai_warning', 'last_segment', 'last_week_summary', 'long_story_draft', 'dirt_sheet', 'review', 'event', 'effect', 'title', 'show_name', 'segment', 'promo', 'beat_text'):
     new_obj[nk] = _replace_in_text(v, old, new)
    else:
     new_obj[nk] = _replace_exact(v, old, new)
   else:
    new_obj[nk] = _walk_rename(v, old, new, text_keys=text_keys)
  return new_obj
 return obj


def _rename_dict_key(dct, old, new):
 if not isinstance(dct, dict) or old not in dct:
  return
 dct[new] = dct.pop(old)


def _rename_champions(champions, old, new):
 if not isinstance(champions, dict):
  return
 for comp, titles in champions.items():
  if not isinstance(titles, dict):
   continue
  for title, holder in list(titles.items()):
   if holder == old:
    titles[title] = new


def _rename_tag_team_globals(old, new, tag_team_members, wcw_divisions, sd_divisions):
 if old in tag_team_members:
  tag_team_members[new] = tag_team_members.pop(old)
 if old in wcw_divisions:
  wcw_divisions[new] = wcw_divisions.pop(old)
 if hasattr(sd_divisions, '__contains__') and old in sd_divisions:
  sd_divisions[new] = sd_divisions.pop(old)


def _rename_custom_tag_teams(custom, old, new):
 if not isinstance(custom, dict):
  return
 if old in custom:
  custom[new] = custom.pop(old)
 for team, members in custom.items():
  if team == old:
   continue
  if not isinstance(members, list):
   continue
  for m in members:
   if isinstance(m, dict) and m.get('name') == old:
    m['name'] = new


def _rename_tag_member_defs(tag_team_members, old, new):
 for team, members in list(tag_team_members.items()):
  if not isinstance(members, list):
   continue
  for m in members:
   if isinstance(m, dict) and m.get('name') == old:
    m['name'] = new


def _rename_team_profiles(profiles, old, new):
 if not isinstance(profiles, dict):
  return
 if old in profiles:
  profiles[new] = profiles.pop(old)


def _rename_character_bible(bible, old, new):
 if not isinstance(bible, dict) or old not in bible:
  return
 bible[new] = bible.pop(old)


def _rename_wrestler_image(old_name, new_name):
 folder = Path('assets/wrestlers')
 for ext in ('.png', '.jpg', '.jpeg', '.webp'):
  src = folder / f'{_slug(old_name)}{ext}'
  if src.is_file():
   dst = folder / f'{_slug(new_name)}{ext}'
   if not dst.exists():
    try:
     src.rename(dst)
    except OSError:
     pass
   return


def _rename_affiliations(roster, old, new):
 for w in roster or []:
  if not isinstance(w, dict):
   continue
  if w.get('tag_team_affiliation') == old:
   w['tag_team_affiliation'] = new


def _rename_factions(factions, old, new):
 if not isinstance(factions, dict):
  return
 for comp in PLAYABLE:
  lst = factions.get(comp)
  if not isinstance(lst, list):
   continue
  factions[comp] = [new if x == old else x for x in lst]


def rename_wrestler_everywhere(ss, old_name, new_name, *, tag_team_members=None, wcw_divisions=None, sd_divisions=None):
 """Update old_name → new_name across session state. Returns count of touched areas."""
 old_name = (old_name or '').strip()
 new_name = (new_name or '').strip()
 if not old_name or not new_name or old_name == new_name:
  return 0
 touched = 0
 roster = ss.get('roster', [])
 w = find_by_name(roster, old_name)
 if w:
  w['name'] = new_name
  touched += 1
 _rename_champions(ss.get('champions'), old_name, new_name)
 _rename_character_bible(ss.get('character_bible'), old_name, new_name)
 _rename_team_profiles(ss.get('team_profiles'), old_name, new_name)
 _rename_custom_tag_teams(ss.get('custom_tag_teams'), old_name, new_name)
 if tag_team_members is not None:
  _rename_tag_team_globals(old_name, new_name, tag_team_members, wcw_divisions or {}, sd_divisions or {})
  _rename_tag_member_defs(tag_team_members, old_name, new_name)
 _rename_affiliations(roster, old_name, new_name)
 _rename_factions(ss.get('factions'), old_name, new_name)
 if isinstance(wcw_divisions, dict) and old_name in wcw_divisions:
  wcw_divisions[new_name] = wcw_divisions.pop(old_name)
 keys_to_walk = [
  'champion_meta', 'champion_history', 'title_defense_history', 'twitter_posts', 'twitter_drama',
  'twitter_recruitment_history', 'weekly_history', 'book_show_drafts', 'book_show_archive',
  'saved_show', 'storylines', 'storyline_flags', 'sponsor_objectives', 'rivalries',
  'free_agency_pool', 'negotiation_history', 'contract_warnings', 'departed',
  'finance_ledger', 'show_finance_reports', 'power_rankings', 'previous_power_rankings',
  'power_ranking_history', 'random_event_history', 'appearance_history', 'trade_history',
  'pending_trades', 'debut_history', 'bidding_wars', 'film_projects', 'cameo_library',
  'attraction_history', 'exclusive_activity_history', 'brand_loyalty_history', 'breakup_history',
  'former_tag_teams', 'last_story_analysis', 'last_grade', 'story_parse', 'test_event_preview',
  'schedule_calendar', 'nxt_unfiltered_episodes', 'last_nxt_unfiltered', 'weekly_performance_index',
 ]
 for key in keys_to_walk:
  if key not in ss:
   continue
  before = json.dumps(ss[key], default=str) if ss[key] is not None else ''
  ss[key] = _walk_rename(ss[key], old_name, new_name, text_keys=True)
  after = json.dumps(ss[key], default=str) if ss[key] is not None else ''
  if before != after:
   touched += 1
 for key in ('news_feed', 'calendar_ai_notes', 'debut_warnings', 'contract_warnings'):
  if key not in ss or not isinstance(ss[key], list):
   continue
  ss[key] = [_replace_in_text(x, old_name, new_name) if isinstance(x, str) else _walk_rename(x, old_name, new_name, text_keys=True) for x in ss[key]]
  touched += 1
 if ss.get('long_story_draft'):
  ss['long_story_draft'] = _replace_in_text(ss['long_story_draft'], old_name, new_name)
  touched += 1
 _rename_wrestler_image(old_name, new_name)
 return touched


def apply_wrestler_name_change(
 ss,
 wrestler_id,
 new_display_name,
 *,
 real_name='',
 nickname='',
 gimmick_name='',
 reason='',
 minor_typo=False,
 changed_by='',
 tag_team_members=None,
 wcw_divisions=None,
 sd_divisions=None,
 post_reactions_fn=None,
):
 """
 Apply a name change for one wrestler. Keeps wrestler_id; updates universe-wide references.
 post_reactions_fn(old, new, w, reason) optional — Twitter/Dirt Sheet/Storyline hooks.
 """
 new_display_name = (new_display_name or '').strip()
 if not new_display_name:
  return False, 'Enter a new display name.'
 w = find_by_wrestler_id(ss.get('roster', []), wrestler_id)
 if not w:
  return False, 'Wrestler not found (invalid wrestler_id).'
 old_name = w.get('name', '').strip()
 if old_name == new_display_name and not any([real_name, nickname, gimmick_name]):
  return False, 'New name matches current display name.'
 other = find_by_name(ss.get('roster', []), new_display_name)
 if other and other.get('wrestler_id') != wrestler_id:
  return False, f'"{new_display_name}" is already on the roster — no duplicate wrestlers.'
 hist = ss.setdefault('wrestler_name_history', [])
 entry = {
  'wrestler_id': wrestler_id,
  'company': w.get('company', ''),
  'previous_name': old_name,
  'current_display_name': new_display_name,
  'previous_names': list({h.get('previous_name') for h in hist if h.get('wrestler_id') == wrestler_id and h.get('previous_name')} | {old_name}),
  'name_changed_week': int(ss.get('week', 0)),
  'name_change_reason': (reason or '').strip(),
  'changed_by': (changed_by or '').strip() or ss.get('player_name', 'GM'),
  'timestamp': datetime.now(timezone.utc).isoformat(),
  'minor_typo_fix': bool(minor_typo),
  'ring_name': new_display_name,
  'real_name': (real_name or w.get('real_name', '')).strip(),
  'nickname': (nickname or w.get('nickname', '')).strip(),
  'gimmick_name': (gimmick_name or w.get('gimmick_name', '')).strip(),
 }
 if old_name != new_display_name:
  rename_wrestler_everywhere(ss, old_name, new_display_name, tag_team_members=tag_team_members, wcw_divisions=wcw_divisions, sd_divisions=sd_divisions)
 w['name'] = new_display_name
 w['ring_name'] = new_display_name
 if real_name:
  w['real_name'] = real_name.strip()
 if nickname:
  w['nickname'] = nickname.strip()
 if gimmick_name:
  w['gimmick_name'] = gimmick_name.strip()
 hist.insert(0, entry)
 if not minor_typo and old_name != new_display_name and callable(post_reactions_fn):
  post_reactions_fn(old_name, new_display_name, w, reason)
 elif not minor_typo and old_name != new_display_name:
  comp = w.get('company', 'NXT')
  ss.setdefault('news_feed', []).insert(0, f"NAME CHANGE: {old_name} is now **{new_display_name}** on {comp}. {(reason or '')[:120]}")
 return True, f'Updated **{old_name}** → **{new_display_name}** everywhere (wrestler_id `{wrestler_id}` unchanged).'


def name_history_for(wrestler_id, history=None):
 wid = (wrestler_id or '').strip()
 rows = [h for h in (history or []) if h.get('wrestler_id') == wid]
 return sorted(rows, key=lambda x: x.get('timestamp', ''), reverse=True)
