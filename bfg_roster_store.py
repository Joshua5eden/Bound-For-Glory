"""Custom roster persistence — merge default + saved wrestlers by wrestler_id."""
import json
from datetime import datetime, timezone
from pathlib import Path

import bfg_name_change as namechg

PLAYABLE = ['NXT', 'SmackDown', 'WCW']


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def ensure_wrestler_ids(roster):
    namechg.ensure_wrestler_ids(roster)


def baseline_name_keys(baseline):
    return frozenset((w.get('name'), w.get('company')) for w in (baseline or []))


def is_custom_wrestler(w, baseline_keys=None):
    if not w or not isinstance(w, dict):
        return False
    if w.get('is_custom_wrestler'):
        return True
    if baseline_keys is None:
        return False
    return (w.get('name'), w.get('company')) not in baseline_keys


def prepare_new_custom_wrestler(w, created_by=''):
    """Stamp metadata on a newly created roster member before first save."""
    if not w:
        return w
    ts = _now_iso()
    w['is_custom_wrestler'] = True
    w.setdefault('created_at', ts)
    w['updated_at'] = ts
    w.setdefault('created_by', created_by or '')
    w.setdefault('image_path', '')
    w.setdefault('image_url', '')
    w.setdefault('ring_name', w.get('name', ''))
    ensure_wrestler_ids([w])
    return w


def find_roster_index(roster, *, wrestler_id=None, name=None, company=None):
    wid = (wrestler_id or '').strip()
    nm = (name or '').strip()
    co = company
    for i, w in enumerate(roster or []):
        if wid and w.get('wrestler_id') == wid:
            return i
        if nm and w.get('name') == nm and (co is None or w.get('company') == co):
            return i
    return -1


def upsert_roster_member(roster, wrestler):
    """Insert or update a roster entry by wrestler_id (never duplicate custom members)."""
    roster = roster if roster is not None else []
    w = dict(wrestler or {})
    ensure_wrestler_ids([w])
    w['updated_at'] = _now_iso()
    idx = find_roster_index(roster, wrestler_id=w.get('wrestler_id'))
    if idx < 0:
        idx = find_roster_index(roster, name=w.get('name'), company=w.get('company'))
    if idx >= 0:
        merged = dict(roster[idx])
        merged.update(w)
        roster[idx] = merged
        return roster[idx]
    roster.append(w)
    return w


def update_wrestler_image(roster, wrestler_id, image_path, company=None, image_url=''):
    """Attach image path to existing wrestler — never remove roster entry."""
    idx = find_roster_index(roster, wrestler_id=wrestler_id)
    if idx < 0:
        return None
    w = roster[idx]
    w['image_path'] = image_path or w.get('image_path', '')
    if image_url:
        w['image_url'] = image_url
    w['updated_at'] = _now_iso()
    if company:
        w['company'] = company
    return w


def merge_rosters(baseline, saved):
    """
    Merge default + saved rosters.
    - Default wrestlers load from baseline
    - Custom wrestlers (is_custom_wrestler or unknown name) are kept
    - Saved edits patch onto baseline entries by wrestler_id
    - Duplicates removed by wrestler_id
    """
    baseline = [dict(w) for w in (baseline or [])]
    saved = [dict(w) for w in (saved or [])]
    ensure_wrestler_ids(baseline)
    ensure_wrestler_ids(saved)
    bkeys = baseline_name_keys(baseline)

    merged = {}
    order = []

    for w in baseline:
        wid = w.get('wrestler_id')
        if not wid:
            continue
        merged[wid] = w
        order.append(wid)

    for w in saved:
        wid = (w.get('wrestler_id') or '').strip()
        if not wid:
            wid = namechg.make_wrestler_id(w.get('name', ''), w.get('company', 'NXT'))
            w['wrestler_id'] = wid

        custom = is_custom_wrestler(w, bkeys)
        if custom:
            w['is_custom_wrestler'] = True

        if custom or wid not in merged:
            if wid not in order:
                order.append(wid)
            merged[wid] = dict(w)
            continue

        base = dict(merged[wid])
        for k, v in w.items():
            if k == 'wrestler_id':
                continue
            if v is None:
                continue
            if v != '' or k in ('image_path', 'image_url', 'is_custom_wrestler', 'salary', 'overall', 'popularity', 'momentum', 'morale'):
                base[k] = v
        if w.get('is_custom_wrestler'):
            base['is_custom_wrestler'] = True
        merged[wid] = base

    return [merged[wid] for wid in order if wid in merged]


def ensure_custom_roster_index(session_state):
    """Session index: rosters[company][wrestler_id] for custom members."""
    idx = {}
    for w in session_state.get('roster', []) or []:
        if not w.get('is_custom_wrestler'):
            continue
        co = w.get('company', 'NXT')
        wid = w.get('wrestler_id', '')
        if not wid or co not in PLAYABLE:
            continue
        idx.setdefault(co, {})[wid] = w
    session_state['rosters'] = idx
    return idx


def apply_loaded_roster(session_state, baseline, saved_roster=None):
    """Safe roster load — merge baseline with saved/custom entries."""
    saved = saved_roster if saved_roster is not None else session_state.get('roster', [])
    session_state['roster'] = merge_rosters(baseline, saved)
    ensure_custom_roster_index(session_state)
    ensure_wrestler_ids(session_state['roster'])


def custom_members_from_roster(roster):
    """All user-added roster members — always persisted separately."""
    out = []
    for w in roster or []:
        if not isinstance(w, dict):
            continue
        if w.get('is_custom_wrestler'):
            out.append(dict(w))
    return out


def combine_saved_rosters(*roster_lists):
    """Flatten multiple roster snapshots without duplicates."""
    seen = set()
    out = []
    for roster in roster_lists:
        for w in roster or []:
            if not isinstance(w, dict):
                continue
            wid = (w.get('wrestler_id') or '').strip()
            key = wid or f"{w.get('name','')}::{w.get('company','')}"
            if key in seen:
                continue
            seen.add(key)
            out.append(dict(w))
    return out


def write_custom_roster_sidecar(path, roster, *, updated_at=None):
    """Dedicated file for late additions — survives partial universe reloads."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    members = custom_members_from_roster(roster)
    payload = {
        'members': members,
        'updated_at': updated_at or _now_iso(),
    }
    path.write_text(json.dumps(payload, indent=2, default=str), encoding='utf-8')
    return len(members)


def read_custom_roster_sidecar(path):
    path = Path(path)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return []
    members = data.get('members', []) if isinstance(data, dict) else data
    out = []
    for w in members or []:
        if not isinstance(w, dict):
            continue
        row = dict(w)
        row['is_custom_wrestler'] = True
        out.append(row)
    return out


def sidecar_timestamp(path):
    path = Path(path)
    if not path.exists():
        return ''
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return ''
    return data.get('updated_at', '') if isinstance(data, dict) else ''
