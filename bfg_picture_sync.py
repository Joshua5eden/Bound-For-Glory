"""Global picture registry — one upload visible in every private session on this server."""
import base64
import json
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import bfg_name_change as namechg

REGISTRY_PATH = Path('data/picture_registry.json')
WRESTLER_EXTS = ('.png', '.jpg', '.jpeg', '.webp')
_MAX_B64_BYTES = 1_500_000
_COMPANY_SUFFIXES = ('nxt', 'smackdown', 'wcw')


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _load_registry():
    if not REGISTRY_PATH.exists():
        return {'updated_at': '', 'wrestlers': {}, 'belts': {}, 'logos': {}, 'owners': {}, 'banners': {}}
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return {'updated_at': '', 'wrestlers': {}, 'logos': {}, 'owners': {}, 'banners': {}, 'belts': {}}
    for key in ('wrestlers', 'belts', 'logos', 'owners', 'banners'):
        data.setdefault(key, {})
    return data


def _save_registry(data):
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    data['updated_at'] = _now_iso()
    REGISTRY_PATH.write_text(json.dumps(data, indent=2, default=str), encoding='utf-8')


def _encode_image_file(path):
    p = Path(path or '')
    if not p.is_file():
        return ''
    try:
        raw = p.read_bytes()
    except OSError:
        return ''
    if not raw or len(raw) > _MAX_B64_BYTES:
        return ''
    return base64.b64encode(raw).decode('ascii')


def _wrestler_id_core(wid):
    core = (wid or '').strip().lower()
    if core.startswith('w-'):
        core = core[2:]
    for co in _COMPANY_SUFFIXES:
        suffix = f'-{co}'
        if core.endswith(suffix):
            return core[: -len(suffix)]
    return core


def match_wrestler_for_stem(roster, stem):
    """Match an image filename (no extension) to a roster wrestler."""
    if not roster:
        return None
    namechg.ensure_wrestler_ids(roster)
    key = (stem or '').strip().lower().replace(' ', '_')
    if not key:
        return None
    by_id = {}
    by_slug = {}
    by_core = {}
    for w in roster:
        if not isinstance(w, dict):
            continue
        wid = (w.get('wrestler_id') or '').strip()
        if wid:
            by_id[wid.lower()] = w
            by_core[_wrestler_id_core(wid)] = w
        slug = namechg._slug(w.get('name', ''))
        if slug:
            by_slug[slug] = w
    if key in by_id:
        return by_id[key]
    if key in by_slug:
        return by_slug[key]
    if key in by_core:
        return by_core[key]
    key_dash = key.replace('_', '-')
    for w in roster:
        wid = (w.get('wrestler_id') or '').lower()
        if key_dash in wid or key in wid.replace('-', '_'):
            return w
    return None


def save_wrestler_image_bytes(wrestler, raw_bytes, ext='.png', roster=None):
    """Write image file, register globally, and patch roster row."""
    if not wrestler or not raw_bytes:
        return False, 'Missing wrestler or image data.'
    if roster is not None:
        namechg.ensure_wrestler_ids(roster)
    wid = (wrestler.get('wrestler_id') or '').strip()
    if not wid:
        wid = namechg.make_wrestler_id(wrestler.get('name', ''), wrestler.get('company', 'NXT'))
        wrestler['wrestler_id'] = wid
    ext = ext if ext.startswith('.') else f'.{ext}'
    if ext.lower() not in WRESTLER_EXTS:
        ext = '.png'
    folder = Path('assets/wrestlers')
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'{wid}{ext}'
    path.write_bytes(raw_bytes)
    wrestler['image_path'] = str(path)
    register_wrestler_image(wrestler, str(path))
    return True, str(path)


def _expand_uploaded_files(uploaded_files):
    """Flatten zip archives into individual image uploads."""
    expanded = []
    for f in uploaded_files or []:
        fname = (getattr(f, 'name', '') or '').lower()
        raw = f.getvalue() if hasattr(f, 'getvalue') else f.read()
        if fname.endswith('.zip'):
            try:
                with zipfile.ZipFile(BytesIO(raw)) as zf:
                    for info in zf.infolist():
                        if info.is_dir():
                            continue
                        inner = Path(info.filename).name
                        if Path(inner).suffix.lower() not in WRESTLER_EXTS:
                            continue

                        class _ZipEntry:
                            def __init__(self, name, data):
                                self.name = name
                                self._data = data

                            def getvalue(self):
                                return self._data

                        expanded.append(_ZipEntry(inner, zf.read(info)))
            except Exception:
                class _BadZip:
                    name = fname

                    def getvalue(self):
                        return b''

                expanded.append(_BadZip())
        else:
            expanded.append(f)
    return expanded


def bulk_import_wrestler_images(uploaded_files, roster):
    """Import many portraits at once — filenames matched to wrestler_id or name slug."""
    matched = []
    unmatched = []
    errors = []
    uploaded_files = _expand_uploaded_files(uploaded_files)
    if not uploaded_files:
        return {'matched': matched, 'unmatched': unmatched, 'errors': errors, 'count': 0}
    namechg.ensure_wrestler_ids(roster)
    for f in uploaded_files:
        fname = getattr(f, 'name', '') or 'image.png'
        stem = Path(fname).stem
        ext = Path(fname).suffix.lower() or '.png'
        if ext not in WRESTLER_EXTS:
            unmatched.append(fname)
            continue
        w = match_wrestler_for_stem(roster, stem)
        if not w:
            unmatched.append(fname)
            continue
        try:
            raw = f.getvalue() if hasattr(f, 'getvalue') else f.read()
            ok, msg = save_wrestler_image_bytes(w, raw, ext, roster=roster)
            if ok:
                matched.append((w.get('name', stem), msg))
            else:
                errors.append(f'{fname}: {msg}')
        except Exception as ex:
            errors.append(f'{fname}: {ex}')
    return {'matched': matched, 'unmatched': unmatched, 'errors': errors, 'count': len(matched)}


def repair_all_pictures(roster):
    """Rescan disk, restore backups, link every portrait to roster rows."""
    namechg.ensure_wrestler_ids(roster)
    restored = restore_registry_images_to_disk()
    scan_assets_into_registry(roster)
    apply_registry_to_roster(roster)
    reg = _load_registry()
    return {
        'restored_files': restored,
        'registry_count': len(reg.get('wrestlers', {})),
        'linked_count': sum(1 for w in roster if isinstance(w, dict) and w.get('image_path')),
    }


def register_wrestler_image(wrestler, image_path, image_url=''):
    """Record a wrestler portrait for all sessions."""
    if not wrestler or not isinstance(wrestler, dict):
        return
    wid = (wrestler.get('wrestler_id') or '').strip()
    if not wid:
        wid = namechg.make_wrestler_id(wrestler.get('name', ''), wrestler.get('company', 'NXT'))
        wrestler['wrestler_id'] = wid
    reg = _load_registry()
    b64 = _encode_image_file(image_path)
    reg['wrestlers'][wid] = {
        'wrestler_id': wid,
        'name': wrestler.get('name', ''),
        'company': wrestler.get('company', ''),
        'image_path': image_path or '',
        'image_url': image_url or '',
        'image_data_b64': b64 or reg.get('wrestlers', {}).get(wid, {}).get('image_data_b64', ''),
        'updated_at': _now_iso(),
    }
    _save_registry(reg)


def restore_registry_images_to_disk():
    """Rebuild missing asset files from embedded registry backups."""
    reg = _load_registry()
    restored = 0
    for wid, entry in (reg.get('wrestlers') or {}).items():
        path = entry.get('image_path', '')
        b64 = entry.get('image_data_b64', '')
        if not b64:
            continue
        target = Path(path) if path else Path('assets/wrestlers') / f'{wid}.png'
        if target.is_file():
            continue
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(base64.b64decode(b64))
            entry['image_path'] = str(target)
            restored += 1
        except Exception:
            continue
    if restored:
        _save_registry(reg)
    return restored


def remove_wrestler_from_registry(wrestler_id):
    reg = _load_registry()
    reg['wrestlers'].pop((wrestler_id or '').strip(), None)
    _save_registry(reg)


def clear_wrestler_image(wrestler):
    """Remove portrait from disk, registry, and roster row."""
    if not wrestler:
        return False
    wid = (wrestler.get('wrestler_id') or '').strip()
    removed = False
    for path in {wrestler.get('image_path', '')}:
        p = Path(path or '')
        if p.is_file():
            try:
                p.unlink()
                removed = True
            except OSError:
                pass
    folder = Path('assets/wrestlers')
    stems = {wid, namechg._slug(wrestler.get('name', '')), _wrestler_id_core(wid)}
    for stem in {s for s in stems if s}:
        for ext in WRESTLER_EXTS:
            p = folder / f'{stem}{ext}'
            if p.is_file():
                try:
                    p.unlink()
                    removed = True
                except OSError:
                    pass
    if wid:
        remove_wrestler_from_registry(wid)
    wrestler.pop('image_path', None)
    wrestler.pop('image_url', None)
    return removed


def scan_assets_into_registry(roster=None):
    """Rebuild registry entries from files already on disk."""
    reg = _load_registry()
    wrest_dir = Path('assets/wrestlers')
    if wrest_dir.is_dir():
        for p in wrest_dir.iterdir():
            if not p.is_file() or p.suffix.lower() not in WRESTLER_EXTS:
                continue
            stem = p.stem
            w = match_wrestler_for_stem(roster, stem) if roster else None
            wid = (w.get('wrestler_id') if w else stem) or stem
            existing = reg['wrestlers'].get(wid, {})
            reg['wrestlers'][wid] = {
                'wrestler_id': wid,
                'name': (w.get('name') if w else existing.get('name', stem)),
                'company': (w.get('company') if w else existing.get('company', '')),
                'image_path': str(p),
                'image_url': existing.get('image_url', ''),
                'image_data_b64': existing.get('image_data_b64', '') or _encode_image_file(p),
                'updated_at': _now_iso(),
            }
            if w and not w.get('image_path'):
                w['image_path'] = str(p)
    for kind, folder in (
        ('belts', 'assets/belts'),
        ('logos', 'assets/logos'),
        ('owners', 'assets/owners'),
        ('banners', 'assets/banners'),
    ):
        d = Path(folder)
        if not d.is_dir():
            continue
        for p in d.iterdir():
            if p.is_file() and p.suffix.lower() in WRESTLER_EXTS:
                reg[kind][p.stem] = {'path': str(p), 'updated_at': _now_iso()}
    _save_registry(reg)
    return reg


def image_bytes_for_wrestler(wrestler):
    """Return raw image bytes from disk or registry backup."""
    if not wrestler:
        return None
    path = wrestler.get('image_path', '')
    if path and Path(path).is_file():
        try:
            return Path(path).read_bytes()
        except OSError:
            pass
    wid = (wrestler.get('wrestler_id') or '').strip()
    if not wid:
        return None
    entry = (_load_registry().get('wrestlers') or {}).get(wid, {})
    b64 = entry.get('image_data_b64', '')
    if b64:
        try:
            return base64.b64decode(b64)
        except Exception:
            return None
    reg_path = entry.get('image_path', '')
    if reg_path and Path(reg_path).is_file():
        try:
            return Path(reg_path).read_bytes()
        except OSError:
            return None
    return None


def apply_registry_to_roster(roster):
    """Patch roster rows with shared picture paths."""
    if not roster:
        return roster
    namechg.ensure_wrestler_ids(roster)
    restore_registry_images_to_disk()
    reg = _load_registry()
    by_id = reg.get('wrestlers', {})
    by_core = {_wrestler_id_core(k): v for k, v in by_id.items()}
    for w in roster:
        if not isinstance(w, dict):
            continue
        wid = (w.get('wrestler_id') or '').strip()
        entry = by_id.get(wid) if wid else None
        if not entry and wid:
            entry = by_core.get(_wrestler_id_core(wid))
        if not entry:
            matched = match_wrestler_for_stem(roster, namechg._slug(w.get('name', '')))
            if matched:
                entry = by_id.get((matched.get('wrestler_id') or ''), {})
        if not entry:
            continue
        path = entry.get('image_path', '')
        if path and Path(path).exists():
            w['image_path'] = path
        if entry.get('image_url'):
            w['image_url'] = entry['image_url']
    return roster


def registry_to_image_meta():
    meta = {}
    for wid, entry in (_load_registry().get('wrestlers') or {}).items():
        if not wid:
            continue
        meta[wid] = {
            'company': entry.get('company', ''),
            'updated_at': entry.get('updated_at', ''),
        }
    return meta


def merge_registry_from_universe(universe):
    """Pull picture rows from a universe save into the global registry."""
    if not isinstance(universe, dict):
        return
    reg = _load_registry()
    for w in universe.get('roster', []) or []:
        if not isinstance(w, dict):
            continue
        wid = (w.get('wrestler_id') or '').strip()
        path = w.get('image_path', '')
        url = w.get('image_url', '')
        if not wid or (not path and not url):
            continue
        prev = reg['wrestlers'].get(wid, {})
        if path and not Path(path).exists():
            path = prev.get('image_path', '') if Path(prev.get('image_path', '')).exists() else ''
        reg['wrestlers'][wid] = {
            'wrestler_id': wid,
            'name': w.get('name', prev.get('name', '')),
            'company': w.get('company', prev.get('company', '')),
            'image_path': path or prev.get('image_path', ''),
            'image_url': url or prev.get('image_url', ''),
            'image_data_b64': prev.get('image_data_b64', '') or _encode_image_file(path),
            'updated_at': _now_iso(),
        }
    for wid, meta in (universe.get('wrestler_image_meta') or {}).items():
        if wid in reg['wrestlers']:
            reg['wrestlers'][wid]['company'] = meta.get('company', reg['wrestlers'][wid].get('company', ''))
    _save_registry(reg)


def import_all_sessions_into_registry():
    """Merge picture data from every saved universe on this server."""
    import bfg_sessions as mp

    mp.init_storage()
    sample_roster = []
    for s in mp.list_saved_sessions():
        sid = s['session_id']
        uni = mp.db_load_blob('mp_universe', sid) if sid != 'local' else None
        if uni and uni.get('roster'):
            sample_roster = uni['roster']
            break
    scan_assets_into_registry(sample_roster or None)
    for s in mp.list_saved_sessions():
        sid = s['session_id']
        uni = None
        if sid != 'local':
            uni = mp.db_load_blob('mp_universe', sid)
            if not uni:
                f = mp.session_dir(sid) / 'universe.json'
                if f.exists():
                    try:
                        uni = json.loads(f.read_text(encoding='utf-8'))
                    except Exception:
                        uni = None
        else:
            f = mp.LOCAL_LEGACY_DIR / 'universe.json'
            if f.exists():
                try:
                    uni = json.loads(f.read_text(encoding='utf-8'))
                except Exception:
                    uni = None
        if uni:
            merge_registry_from_universe(uni)
    return _load_registry()


def _write_wrestler_bytes(wrestler, raw_bytes, ext='.png', roster=None):
    if not wrestler or not raw_bytes:
        return False, 'missing data'
    return save_wrestler_image_bytes(wrestler, raw_bytes, ext, roster=roster)


def import_pictures_from_supabase(invite_code=None, session_id=None, roster=None):
    """Pull portrait backups from Supabase cloud into local assets + registry."""
    import bfg_supabase as sb

    if not sb.supabase_configured():
        return {'ok': False, 'error': 'Supabase not configured', 'imported': 0}
    sid = (session_id or '').strip()
    if not sid and invite_code:
        hit = sb.find_session_by_invite(invite_code)
        sid = (hit or {}).get('session_id', '')
    if not sid:
        return {'ok': False, 'error': 'Session not found in cloud', 'imported': 0}
    try:
        rows = sb.fetch_session_saves(sid)
    except Exception as ex:
        return {'ok': False, 'error': str(ex), 'imported': 0}
    if not rows:
        return {'ok': False, 'error': 'No cloud saves for this session', 'imported': 0}

    merged = sb.merge_rows_to_payload(rows) or {}
    cloud_roster = list(merged.get('roster') or [])
    img_paths = {}
    for row in rows:
        if row.get('save_type') != 'wrestler_image':
            continue
        payload = row.get('payload') or {}
        wid = payload.get('wrestler_id') or row.get('save_key', '')
        if wid:
            img_paths[wid] = payload

    by_id = {w.get('wrestler_id'): w for w in cloud_roster if w.get('wrestler_id')}
    if roster:
        namechg.ensure_wrestler_ids(roster)
        local_by_id = {w.get('wrestler_id'): w for w in roster if w.get('wrestler_id')}
    else:
        local_by_id = by_id

    imported = 0
    errors = []
    for wid, info in img_paths.items():
        w = local_by_id.get(wid) or by_id.get(wid)
        if not w:
            continue
        b64 = info.get('image_data_b64', '')
        if b64:
            try:
                raw = base64.b64decode(b64)
                ext = Path(info.get('image_path', '') or f'{wid}.png').suffix.lower() or '.png'
                ok, msg = _write_wrestler_bytes(w, raw, ext, roster=roster)
                if ok:
                    imported += 1
                else:
                    errors.append(f'{wid}: {msg}')
            except Exception as ex:
                errors.append(f'{wid}: {ex}')
            continue
        url = (info.get('image_url') or '').strip()
        if url:
            try:
                import urllib.request
                with urllib.request.urlopen(url, timeout=20) as resp:
                    raw = resp.read()
                ext = Path(url.split('?')[0]).suffix.lower() or '.png'
                ok, msg = _write_wrestler_bytes(w, raw, ext, roster=roster)
                if ok:
                    imported += 1
                else:
                    errors.append(f'{wid}: {msg}')
            except Exception as ex:
                errors.append(f'{wid} url: {ex}')

    for w in cloud_roster:
        wid = w.get('wrestler_id')
        if not wid or wid in img_paths:
            continue
        path = w.get('image_path', '')
        url = (w.get('image_url') or '').strip()
        local = local_by_id.get(wid) or w
        if url and not local.get('image_path'):
            try:
                import urllib.request
                with urllib.request.urlopen(url, timeout=20) as resp:
                    raw = resp.read()
                ext = Path(url.split('?')[0]).suffix.lower() or '.png'
                ok, _ = _write_wrestler_bytes(local, raw, ext, roster=roster)
                if ok:
                    imported += 1
            except Exception as ex:
                errors.append(f'{wid} roster url: {ex}')
        elif path and local and not local.get('image_path'):
            local['image_path'] = path

    if roster:
        apply_registry_to_roster(roster)
        repair_all_pictures(roster)
    return {
        'ok': True,
        'session_id': sid,
        'cloud_refs': len(img_paths),
        'imported': imported,
        'errors': errors[:12],
    }


def recover_pictures_from_streamlit(invite_codes=None, roster=None):
    """Try every known invite code; return best cloud picture import result."""
    codes = list(invite_codes or ('BFG-9309', 'BFG-6051', 'BFG-6956'))
    best = {'ok': False, 'error': 'No cloud session found', 'imported': 0}
    for code in codes:
        result = import_pictures_from_supabase(invite_code=code, roster=roster)
        if not result.get('ok'):
            if best.get('error') == 'No cloud session found':
                best = result
            continue
        if result.get('imported', 0) >= best.get('imported', 0):
            best = {**result, 'invite_code': code}
    if best.get('ok') and roster is not None:
        propagate_pictures_to_all_sessions(roster)
    return best


def propagate_pictures_to_all_sessions(roster=None, image_meta=None):
    """Write global picture registry into every session save."""
    import bfg_sessions as mp

    mp.init_storage()
    reg = import_all_sessions_into_registry()
    restore_registry_images_to_disk()
    reg = _load_registry()
    if roster:
        for w in roster:
            if w.get('wrestler_id') and (w.get('image_path') or w.get('image_url')):
                register_wrestler_image(w, w.get('image_path', ''), w.get('image_url', ''))

    meta = dict(image_meta or registry_to_image_meta())

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

        roster_rows = apply_registry_to_roster(list(uni.get('roster', [])))
        for w in roster_rows:
            wid = w.get('wrestler_id')
            if wid and wid in reg.get('wrestlers', {}):
                ent = reg['wrestlers'][wid]
                if ent.get('image_path'):
                    w['image_path'] = ent['image_path']
                if ent.get('image_url'):
                    w['image_url'] = ent['image_url']

        uni['roster'] = roster_rows
        merged_meta = dict(uni.get('wrestler_image_meta', {}) or {})
        merged_meta.update(registry_to_image_meta())
        merged_meta.update(meta)
        uni['wrestler_image_meta'] = merged_meta
        uni['pictures_updated_at'] = reg.get('updated_at', _now_iso())

        if sid != 'local':
            mp.db_save_blob('mp_universe', sid, uni)
            f = mp.session_dir(sid) / 'universe.json'
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(uni, indent=2, default=str), encoding='utf-8')
        else:
            f = mp.LOCAL_LEGACY_DIR / 'universe.json'
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(uni, indent=2, default=str), encoding='utf-8')

    return len(reg.get('wrestlers', {}))
