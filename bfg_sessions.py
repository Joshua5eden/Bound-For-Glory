"""Private multiplayer sessions — per-group universe storage (JSON + optional SQLite)."""
import json
import os
import random
import sqlite3
import string
import uuid
from datetime import datetime, timezone
from pathlib import Path

SESSIONS_ROOT = Path('data/sessions')
REGISTRY_PATH = SESSIONS_ROOT / 'registry.json'
SQLITE_PATH = Path('data/bfg_multiplayer.db')
LOCAL_LEGACY_DIR = Path('data/universe')

ROLE_MAP = {
 'admin': ('Admin', 'All'),
 'nxt': ('NXT GM', 'NXT'),
 'smackdown': ('SmackDown GM', 'SmackDown'),
 'wcw': ('WCW GM', 'WCW'),
}


def _now_iso():
 return datetime.now(timezone.utc).isoformat()


def database_url_configured():
 try:
  import bfg_supabase as sb
  if sb.supabase_configured():
   return True
 except Exception:
  pass
 try:
  import streamlit as st
  url = st.secrets.get('DATABASE_URL', '') or st.secrets.get('SUPABASE_URL', '')
  return bool(url)
 except Exception:
  return bool(os.getenv('DATABASE_URL', '') or os.getenv('SUPABASE_URL', ''))


def shared_storage_available():
 """True when SQLite or remote DB can persist sessions for multiple browsers."""
 return SQLITE_PATH.parent.exists() or database_url_configured()


def init_storage():
 SESSIONS_ROOT.mkdir(parents=True, exist_ok=True)
 SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
 if not REGISTRY_PATH.exists():
  REGISTRY_PATH.write_text('{}', encoding='utf-8')
 conn = sqlite3.connect(SQLITE_PATH)
 conn.execute(
  """CREATE TABLE IF NOT EXISTS mp_sessions (
   session_id TEXT PRIMARY KEY,
   game_name TEXT,
   invite_code TEXT UNIQUE,
   admin_code TEXT,
   nxt_code TEXT,
   smackdown_code TEXT,
   wcw_code TEXT,
   created_at TEXT,
   created_by TEXT
  )"""
 )
 conn.execute(
  """CREATE TABLE IF NOT EXISTS mp_universe (
   session_id TEXT PRIMARY KEY,
   payload TEXT,
   updated_at TEXT
  )"""
 )
 conn.execute(
  """CREATE TABLE IF NOT EXISTS mp_week_state (
   session_id TEXT PRIMARY KEY,
   payload TEXT,
   updated_at TEXT
  )"""
 )
 conn.execute(
  """CREATE TABLE IF NOT EXISTS mp_pending_trades (
   session_id TEXT PRIMARY KEY,
   payload TEXT,
   updated_at TEXT
  )"""
 )
 conn.commit()
 conn.close()


def _load_registry():
 if not REGISTRY_PATH.exists():
  return {}
 try:
  return json.loads(REGISTRY_PATH.read_text(encoding='utf-8'))
 except Exception:
  return {}


def _save_registry(reg):
 REGISTRY_PATH.write_text(json.dumps(reg, indent=2), encoding='utf-8')


def invite_exists(invite_code):
 reg = _load_registry()
 return invite_code.upper() in {k.upper() for k in reg}


def generate_invite_code():
 for _ in range(200):
  code = f'BFG-{random.randint(1000, 9999)}'
  if not invite_exists(code):
   return code
 return f'BFG-{random.randint(10000, 99999)}'


def reserve_invite_code(preferred=None):
 """Use a specific invite code when available, else generate a new one."""
 code = normalize_invite_code(preferred) if preferred else ''
 if code and not invite_exists(code):
  return code
 return generate_invite_code()


def generate_access_code():
 return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


def generate_session_id():
 return uuid.uuid4().hex[:16]


def session_dir(session_id):
 return SESSIONS_ROOT / session_id


def session_meta_path(session_id):
 return session_dir(session_id) / 'meta.json'


def normalize_invite_code(invite_code):
 """Accept BFG-6051, bfg-6051, 6051, extra spaces."""
 raw = (invite_code or '').strip().upper().replace(' ', '')
 if not raw:
  return ''
 if raw.startswith('BFG-'):
  return raw
 if raw.startswith('BFG'):
  rest = raw[3:].lstrip('-')
  return f'BFG-{rest}' if rest else raw
 if raw.isdigit():
  return f'BFG-{raw}'
 return raw


def resolve_invite(invite_code):
 reg = _load_registry()
 key = normalize_invite_code(invite_code)
 if not key:
  return None
 if key in reg:
  return reg[key]
 for k, v in reg.items():
  if (k or '').strip().upper() == key:
   return v
 return None


def register_invite(invite_code, session_id):
 reg = _load_registry()
 reg[invite_code.strip().upper()] = session_id
 _save_registry(reg)


def unregister_session(session_id):
 reg = _load_registry()
 reg = {k: v for k, v in reg.items() if v != session_id}
 _save_registry(reg)


def save_session_meta(session_id, meta):
 d = session_dir(session_id)
 d.mkdir(parents=True, exist_ok=True)
 session_meta_path(session_id).write_text(json.dumps(meta, indent=2), encoding='utf-8')
 conn = sqlite3.connect(SQLITE_PATH)
 conn.execute(
  """INSERT OR REPLACE INTO mp_sessions
   (session_id, game_name, invite_code, admin_code, nxt_code, smackdown_code, wcw_code, created_at, created_by)
   VALUES (?,?,?,?,?,?,?,?,?)""",
  (
   session_id,
   meta.get('game_name', ''),
   meta.get('invite_code', ''),
   meta.get('admin_code', ''),
   meta.get('nxt_code', ''),
   meta.get('smackdown_code', ''),
   meta.get('wcw_code', ''),
   meta.get('created_at', ''),
   meta.get('created_by', ''),
  ),
 )
 conn.commit()
 conn.close()
 try:
  import bfg_supabase as sb
  if sb.supabase_configured():
   sb.save_private_session_meta(session_id, meta)
 except Exception:
  pass


def load_session_meta(session_id):
 p = session_meta_path(session_id)
 if p.exists():
  return json.loads(p.read_text(encoding='utf-8'))
 conn = sqlite3.connect(SQLITE_PATH)
 row = conn.execute(
  'SELECT game_name, invite_code, admin_code, nxt_code, smackdown_code, wcw_code, created_at, created_by FROM mp_sessions WHERE session_id=?',
  (session_id,),
 ).fetchone()
 conn.close()
 if not row:
  return None
 return {
  'session_id': session_id,
  'game_name': row[0],
  'invite_code': row[1],
  'admin_code': row[2],
  'nxt_code': row[3],
  'smackdown_code': row[4],
  'wcw_code': row[5],
  'created_at': row[6],
  'created_by': row[7],
 }


def match_access_code(meta, access_code):
 code = (access_code or '').strip().upper()
 if not code or not meta:
  return None
 extra = meta.get('extra_access') or {}
 if code in extra:
  slot = extra[code]
  if slot in ROLE_MAP:
   role, company = ROLE_MAP[slot]
   return {'role': role, 'company': company, 'slot': slot}
 pairs = [
  ('admin_code', 'admin'),
  ('nxt_code', 'nxt'),
  ('smackdown_code', 'smackdown'),
  ('wcw_code', 'wcw'),
 ]
 for field, slot in pairs:
  if code == (meta.get(field) or '').strip().upper():
   role, company = ROLE_MAP[slot]
   return {'role': role, 'company': company, 'slot': slot}
 return None


def restore_access_code(invite_code, access_code, role_slot='admin', keep_previous=True):
 """Re-activate a remembered brand code on an existing invite session."""
 init_storage()
 sid = resolve_invite(normalize_invite_code(invite_code) or invite_code)
 if not sid:
  raise ValueError(f'Invite {invite_code} not found on this server.')
 meta = load_session_meta(sid) or {'session_id': sid}
 code = (access_code or '').strip().upper()
 if not code or len(code) < 6:
  raise ValueError('Access code must be at least 6 characters.')
 slot = (role_slot or 'admin').lower()
 if slot not in ROLE_MAP:
  raise ValueError(f'Unknown role slot: {role_slot}')
 field = f'{slot}_code' if slot != 'admin' else 'admin_code'
 history = meta.setdefault('code_history', {})
 if keep_previous and meta.get(field) and meta[field] != code:
  history[field] = meta[field]
  extra = meta.setdefault('extra_access', {})
  extra[(meta[field] or '').strip().upper()] = slot
 meta[field] = code
 extra = meta.setdefault('extra_access', {})
 extra[code] = slot
 save_session_meta(sid, meta)
 return meta


def create_private_session(game_name, creator_name, invite_code=None):
 init_storage()
 session_id = generate_session_id()
 invite_code = reserve_invite_code(invite_code)
 admin_code = generate_access_code()
 nxt_code = generate_access_code()
 smackdown_code = generate_access_code()
 wcw_code = generate_access_code()
 meta = {
  'session_id': session_id,
  'game_name': (game_name or 'Private Universe').strip(),
  'invite_code': invite_code,
  'admin_code': admin_code,
  'nxt_code': nxt_code,
  'smackdown_code': smackdown_code,
  'wcw_code': wcw_code,
  'created_at': _now_iso(),
  'created_by': (creator_name or 'Commissioner').strip(),
 }
 save_session_meta(session_id, meta)
 register_invite(invite_code, session_id)
 session_dir(session_id).mkdir(parents=True, exist_ok=True)
 return meta


def join_private_session(invite_code, player_name, access_code):
 init_storage()
 invite_norm = normalize_invite_code(invite_code)
 session_id = resolve_invite(invite_norm or invite_code)
 if not session_id:
  try:
   import bfg_supabase as sb
   if sb.supabase_configured():
    hit = sb.find_session_by_invite(invite_code)
    if hit:
     session_id = hit.get('session_id')
     meta = hit.get('payload') or {}
     if isinstance(meta, str):
      meta = json.loads(meta)
     if meta and session_id:
      role_info = match_access_code(meta, access_code)
      if not role_info:
       return None, 'Invalid access code for this game. Use Admin, NXT, SmackDown, or WCW GM code.'
      return {
       'session_id': session_id,
       'game_name': meta.get('game_name', ''),
       'invite_code': meta.get('invite_code', ''),
       'player_name': (player_name or '').strip(),
       'role': role_info['role'],
       'assigned_company': role_info['company'],
       'meta': meta,
      }, None
  except Exception:
   pass
  return None, 'Invite code not found. Check the code or create a new private game.'
 meta = load_session_meta(session_id)
 if not meta:
  return None, 'Session data missing on server — ask the host to re-save the universe.'
 role_info = match_access_code(meta, access_code)
 if not role_info:
  return None, 'Invalid access code for this game. Use Admin, NXT, SmackDown, or WCW GM code.'
 return {
  'session_id': session_id,
  'game_name': meta.get('game_name', ''),
  'invite_code': meta.get('invite_code', ''),
  'player_name': (player_name or '').strip(),
  'role': role_info['role'],
  'assigned_company': role_info['company'],
  'meta': meta,
 }, None


def session_picture_stats(session_id):
 """Count portraits linked in a session roster."""
 init_storage()
 uni = db_load_blob('mp_universe', session_id) if session_id != 'local' else None
 if not uni:
  f = (LOCAL_LEGACY_DIR if session_id == 'local' else session_dir(session_id)) / 'universe.json'
  if f.exists():
   try:
    uni = json.loads(f.read_text(encoding='utf-8'))
   except Exception:
    uni = None
 if not isinstance(uni, dict):
  return {'total': 0, 'NXT': 0, 'SmackDown': 0, 'WCW': 0}
 stats = {'total': 0, 'NXT': 0, 'SmackDown': 0, 'WCW': 0}
 for w in uni.get('roster', []) or []:
  if not isinstance(w, dict):
   continue
  if not (w.get('image_path') or w.get('image_url')):
   continue
  stats['total'] += 1
  co = w.get('company', '')
  if co in stats:
   stats[co] += 1
 return stats


def lookup_invite_session(invite_code):
 """Resolve invite to session meta + picture stats on this server."""
 init_storage()
 sid = resolve_invite(normalize_invite_code(invite_code) or invite_code)
 if not sid:
  return None
 meta = load_session_meta(sid) or {'session_id': sid}
 meta['session_id'] = sid
 meta['picture_stats'] = session_picture_stats(sid)
 saves = [s for s in list_saved_sessions() if s['session_id'] == sid]
 if saves:
  meta['week'] = saves[0].get('week', 0)
  meta['has_universe'] = saves[0].get('has_universe', False)
 return meta


def list_saved_sessions():
 """All universes on this server — for Continue / Clone screens."""
 init_storage()
 out = []
 seen = set()

 def _add(session_id, game_name, week, updated, invite_code='', has_universe=False):
  if session_id in seen:
   return
  seen.add(session_id)
  out.append({
   'session_id': session_id,
   'game_name': game_name or 'Universe',
   'week': week,
   'updated': updated,
   'invite_code': invite_code,
   'has_universe': has_universe,
  })

 local_uni = LOCAL_LEGACY_DIR / 'universe.json'
 if local_uni.exists():
  try:
   data = json.loads(local_uni.read_text(encoding='utf-8'))
   _add('local', data.get('game_name', 'Solo test universe'), data.get('week', 0), data.get('last_updated_at', ''), has_universe=True)
  except Exception:
   pass

 if SESSIONS_ROOT.exists():
  for p in sorted(SESSIONS_ROOT.iterdir(), key=lambda x: x.stat().st_mtime if x.is_dir() else 0, reverse=True):
   if not p.is_dir():
    continue
   sid = p.name
   uni = p / 'universe.json'
   meta = load_session_meta(sid) or {}
   if not uni.exists() and not meta:
    continue
   data = {}
   if uni.exists():
    try:
     data = json.loads(uni.read_text(encoding='utf-8'))
    except Exception:
     data = {}
   pics = session_picture_stats(sid)
   _add(
    sid,
    data.get('game_name') or meta.get('game_name') or sid[:8],
    data.get('week', 0),
    data.get('last_updated_at') or meta.get('created_at', ''),
    meta.get('invite_code', ''),
    has_universe=uni.exists() or bool(db_load_blob('mp_universe', sid)),
   )
   if out and out[-1]['session_id'] == sid:
    out[-1].update({
     'admin_code': meta.get('admin_code', ''),
     'nxt_code': meta.get('nxt_code', ''),
     'smackdown_code': meta.get('smackdown_code', ''),
     'wcw_code': meta.get('wcw_code', ''),
     'picture_stats': pics,
    })
 return sorted(out, key=lambda s: s.get('updated', ''), reverse=True)


def clone_private_session(source_session_id, new_game_name, creator_name, invite_code=None):
 """New invite codes + session id, but copy roster, pictures meta, saves, and progress."""
 init_storage()
 source_session_id = (source_session_id or '').strip() or 'local'
 src_dir = LOCAL_LEGACY_DIR if source_session_id == 'local' else session_dir(source_session_id)
 if source_session_id != 'local' and not src_dir.exists():
  raise FileNotFoundError('Source session folder not found.')

 meta = create_private_session((new_game_name or 'Cloned Universe').strip(), (creator_name or 'Admin').strip(), invite_code=invite_code)
 new_id = meta['session_id']
 dst_dir = session_dir(new_id)
 dst_dir.mkdir(parents=True, exist_ok=True)

 import shutil
 for fname in ('universe.json', 'custom_roster.json', 'week_state.json', 'pending_trades.json'):
  src = src_dir / fname
  if src.exists():
   shutil.copy2(src, dst_dir / fname)

 uni_path = dst_dir / 'universe.json'
 universe = None
 if uni_path.exists():
  try:
   universe = json.loads(uni_path.read_text(encoding='utf-8'))
  except Exception:
   universe = None
 if universe is None:
  universe = db_load_blob('mp_universe', source_session_id) if source_session_id != 'local' else None
 if universe is None and (src_dir / 'universe.json').exists():
  try:
   universe = json.loads((src_dir / 'universe.json').read_text(encoding='utf-8'))
  except Exception:
   universe = None
 if universe is None:
  raise FileNotFoundError('No universe save found to clone.')

 universe = json.loads(json.dumps(universe, default=str))
 universe['session_id'] = new_id
 universe['game_name'] = meta['game_name']
 universe['last_updated_by'] = meta['created_by']
 universe['last_updated_at'] = _now_iso()
 uni_path.write_text(json.dumps(universe, indent=2, default=str), encoding='utf-8')
 db_save_blob('mp_universe', new_id, universe)

 for table, fname in (('mp_week_state', 'week_state.json'), ('mp_pending_trades', 'pending_trades.json')):
  blob = None
  fpath = dst_dir / fname
  if fpath.exists():
   try:
    blob = json.loads(fpath.read_text(encoding='utf-8'))
   except Exception:
    blob = None
  if blob is None and source_session_id != 'local':
   blob = db_load_blob(table, source_session_id)
  if blob is not None:
   db_save_blob(table, new_id, blob)
   fpath.write_text(json.dumps(blob, indent=2, default=str), encoding='utf-8')

 meta['cloned_from'] = source_session_id
 save_session_meta(new_id, meta)
 return meta


def delete_session(session_id):
 if not session_id:
  return
 unregister_session(session_id)
 import shutil
 d = session_dir(session_id)
 if d.exists():
  shutil.rmtree(d, ignore_errors=True)
 conn = sqlite3.connect(SQLITE_PATH)
 for table in ('mp_sessions', 'mp_universe', 'mp_week_state', 'mp_pending_trades'):
  conn.execute(f'DELETE FROM {table} WHERE session_id=?', (session_id,))
 conn.commit()
 conn.close()


def db_save_blob(table, session_id, payload_dict):
 conn = sqlite3.connect(SQLITE_PATH)
 conn.execute(
  f'INSERT OR REPLACE INTO {table} (session_id, payload, updated_at) VALUES (?,?,?)',
  (session_id, json.dumps(payload_dict, default=str), _now_iso()),
 )
 conn.commit()
 conn.close()


def db_load_blob(table, session_id):
 conn = sqlite3.connect(SQLITE_PATH)
 row = conn.execute(f'SELECT payload FROM {table} WHERE session_id=?', (session_id,)).fetchone()
 conn.close()
 if not row:
  return None
 return json.loads(row[0])
