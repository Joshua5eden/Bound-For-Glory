"""Pull full universe + pictures from Streamlit Cloud (Supabase) into local saves."""
import json
from pathlib import Path


def pull_online_save_to_local(invite_code='BFG-9309', local_session_id=None):
    """Download cloud game_saves for an invite and write into this Mac's session folder."""
    import bfg_supabase as sb
    import bfg_sessions as mp
    import bfg_picture_sync as pic_sync

    invite = (invite_code or '').strip().upper()
    if not sb.supabase_configured():
        return {
            'ok': False,
            'error': 'Supabase not configured — add SUPABASE_URL and SUPABASE_KEY to .streamlit/secrets.toml',
            'imported_pictures': 0,
        }

    hit = sb.find_session_by_invite(invite)
    if not hit:
        return {'ok': False, 'error': f'Invite {invite} not found in cloud database', 'imported_pictures': 0}

    cloud_sid = (hit.get('session_id') or '').strip()
    cloud = sb.load_merged_universe(cloud_sid)
    if not cloud:
        return {'ok': False, 'error': 'Cloud session exists but has no save rows', 'imported_pictures': 0}

    mp.init_storage()
    local_sid = (local_session_id or '').strip() or mp.resolve_invite(invite)
    if not local_sid:
        for s in mp.list_saved_sessions():
            if (s.get('invite_code') or '').upper() == invite:
                local_sid = s['session_id']
                break
    if not local_sid:
        return {'ok': False, 'error': f'No local session for {invite} — create or clone one first', 'imported_pictures': 0}

    local = mp.db_load_blob('mp_universe', local_sid) or {}
    meta = mp.load_session_meta(local_sid) or {}
    payload = json.loads(json.dumps(cloud, default=str))
    payload['session_id'] = local_sid
    payload['game_name'] = local.get('game_name') or meta.get('game_name') or payload.get('game_name', 'Universe')
    payload['invite_code'] = invite

    roster = list(payload.get('roster') or [])
    pic_result = pic_sync.recover_pictures_from_streamlit(invite_codes=[invite], roster=roster)
    payload['roster'] = roster
    payload['pictures_updated_at'] = pic_result.get('session_id', cloud_sid)
    payload['last_updated_at'] = cloud.get('last_updated_at') or payload.get('last_updated_at', '')

    mp.db_save_blob('mp_universe', local_sid, payload)
    out_dir = mp.session_dir(local_sid)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'universe.json').write_text(json.dumps(payload, indent=2, default=str), encoding='utf-8')

    pics = pic_sync.registry_to_image_meta()
    roster_pics = sum(1 for w in roster if isinstance(w, dict) and (w.get('image_path') or w.get('image_url')))
    by_brand = {'NXT': 0, 'SmackDown': 0, 'WCW': 0}
    for w in roster:
        if not isinstance(w, dict) or not (w.get('image_path') or w.get('image_url')):
            continue
        co = w.get('company', '')
        if co in by_brand:
            by_brand[co] += 1

    return {
        'ok': True,
        'invite_code': invite,
        'cloud_session_id': cloud_sid,
        'local_session_id': local_sid,
        'roster_count': len(roster),
        'roster_with_pictures': roster_pics,
        'pictures_by_brand': by_brand,
        'imported_pictures': pic_result.get('imported', 0),
        'cloud_picture_refs': pic_result.get('cloud_refs', 0),
        'picture_errors': (pic_result.get('errors') or [])[:8],
        'registry_count': len(pics),
    }
