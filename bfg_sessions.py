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


def generate_access_code():
 return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


def generate_session_id():
 return uuid.uuid4().hex[:16]


def session_dir(session_id):
 return SESSIONS_ROOT / session_id


def session_meta_path(session_id):
 return session_dir(session_id) / 'meta.json'


def resolve_invite(invite_code):
 reg = _load_registry()
 return reg.get((invite_code or '').strip().upper())


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


def create_private_session(game_name, creator_name):
 init_storage()
 session_id = generate_session_id()
 invite_code = generate_invite_code()
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
 session_id = resolve_invite(invite_code)
 if not session_id:
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
