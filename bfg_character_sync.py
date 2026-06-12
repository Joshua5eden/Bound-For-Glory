"""Global character registry — wrestler/staff/host profiles shared across every session."""
import json
from datetime import datetime, timezone
from pathlib import Path

REGISTRY_PATH = Path('data/character_registry.json')
CHAR_KEYS = ('character_bible', 'staff_character_bible', 'nxt_unfiltered_hosts')


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _empty_registry():
    return {
        'updated_at': '',
        'character_bible': {},
        'staff_character_bible': {},
        'nxt_unfiltered_hosts': {},
    }


def _load_registry():
    if not REGISTRY_PATH.exists():
        return _empty_registry()
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return _empty_registry()
    for key in CHAR_KEYS:
        data.setdefault(key, {})
    return data


def _save_registry(data):
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    data['updated_at'] = _now_iso()
    REGISTRY_PATH.write_text(json.dumps(data, indent=2, default=str), encoding='utf-8')


def _entry_ts(entry):
    return (entry or {}).get('updated_at', '') if isinstance(entry, dict) else ''


def _merge_dict_field(reg_field, incoming, field_updated_at=''):
    """Keep newest profile per name/key."""
    for name, profile in (incoming or {}).items():
        if not name or not isinstance(profile, dict):
            continue
        prev = reg_field.get(name, {})
        new_ts = profile.get('updated_at') or field_updated_at or _now_iso()
        old_ts = _entry_ts(prev)
        if not prev or new_ts >= old_ts:
            merged = dict(profile)
            merged['updated_at'] = new_ts
            reg_field[name] = merged


def merge_registry_from_universe(universe, field_updated_at=''):
    if not isinstance(universe, dict):
        return
    reg = _load_registry()
    ts = field_updated_at or universe.get('characters_updated_at') or universe.get('last_updated_at') or _now_iso()
    for key in CHAR_KEYS:
        _merge_dict_field(reg[key], universe.get(key), ts)
    _save_registry(reg)


def import_all_sessions_into_registry():
    import bfg_sessions as mp

    mp.init_storage()
    for s in mp.list_saved_sessions():
        sid = s['session_id']
        uni = mp.db_load_blob('mp_universe', sid) if sid != 'local' else None
        if not uni and sid != 'local':
            f = mp.session_dir(sid) / 'universe.json'
            if f.exists():
                try:
                    uni = json.loads(f.read_text(encoding='utf-8'))
                except Exception:
                    uni = None
        if sid == 'local':
            f = mp.LOCAL_LEGACY_DIR / 'universe.json'
            if f.exists():
                try:
                    uni = json.loads(f.read_text(encoding='utf-8'))
                except Exception:
                    uni = None
        if uni:
            merge_registry_from_universe(uni)
    return _load_registry()


def apply_registry_to_state(session_state):
    reg = import_all_sessions_into_registry()
    for key in CHAR_KEYS:
        current = dict(session_state.get(key, {}) or {})
        for name, profile in (reg.get(key) or {}).items():
            prev = current.get(name, {})
            if not prev or _entry_ts(profile) >= _entry_ts(prev):
                current[name] = {k: v for k, v in profile.items() if k != 'updated_at'}
        session_state[key] = current
    session_state['characters_updated_at'] = reg.get('updated_at', _now_iso())
    return reg


def update_registry_from_state(character_bible=None, staff_character_bible=None, nxt_unfiltered_hosts=None):
    reg = _load_registry()
    ts = _now_iso()
    payloads = {
        'character_bible': character_bible,
        'staff_character_bible': staff_character_bible,
        'nxt_unfiltered_hosts': nxt_unfiltered_hosts,
    }
    for key, val in payloads.items():
        if val is None:
            continue
        _merge_dict_field(reg[key], val, ts)
    _save_registry(reg)
    return reg


def propagate_characters_to_all_sessions(character_bible=None, staff_character_bible=None, nxt_unfiltered_hosts=None):
    import bfg_sessions as mp

    mp.init_storage()
    reg = update_registry_from_state(character_bible, staff_character_bible, nxt_unfiltered_hosts)
    count = sum(len(reg.get(k) or {}) for k in CHAR_KEYS)

    for s in mp.list_saved_sessions():
        sid = s['session_id']
        uni = mp.db_load_blob('mp_universe', sid) if sid != 'local' else None
        if not uni and sid != 'local':
            f = mp.session_dir(sid) / 'universe.json'
            if f.exists():
                try:
                    uni = json.loads(f.read_text(encoding='utf-8'))
                except Exception:
                    uni = None
        if sid == 'local':
            f = mp.LOCAL_LEGACY_DIR / 'universe.json'
            if f.exists():
                try:
                    uni = json.loads(f.read_text(encoding='utf-8'))
                except Exception:
                    uni = None
        if not uni:
            continue
        for key in CHAR_KEYS:
            merged = dict(uni.get(key, {}) or {})
            for name, profile in (reg.get(key) or {}).items():
                prev = merged.get(name, {})
                if not prev or _entry_ts(profile) >= _entry_ts(prev):
                    merged[name] = {k: v for k, v in profile.items() if k != 'updated_at'}
            uni[key] = merged
        uni['characters_updated_at'] = reg.get('updated_at', _now_iso())
        if sid != 'local':
            mp.db_save_blob('mp_universe', sid, uni)
            f = mp.session_dir(sid) / 'universe.json'
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(uni, indent=2, default=str), encoding='utf-8')
        else:
            f = mp.LOCAL_LEGACY_DIR / 'universe.json'
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(uni, indent=2, default=str), encoding='utf-8')
    return count
