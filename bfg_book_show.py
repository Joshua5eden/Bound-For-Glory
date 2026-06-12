"""Book Show — Long Story Mode + Match Card Mode with autosave and storyline hooks."""
import random
from datetime import datetime

import streamlit as st

import bfg_autosave as autosave
import bfg_storylines as storylines
import bfg_sponsor_objectives as sponsor_obj

SEGMENT_TYPES = [
    'Match', 'Promo', 'Backstage Segment', 'In-Ring Segment', 'Contract Signing',
    'Sponsor Segment', 'Media Appearance', 'Twitter Fallout Segment',
    'Main Event', 'Opening Segment', 'Closing Angle',
]

BOOK_FORMATS = ['Long Story Mode', 'Match Card Mode']


def draft_key(company, week):
    return f"{company}:{int(week)}"


def default_segment(company='', seg_type='Match'):
    return {
        'id': random.randint(10000, 99999),
        'segment_type': seg_type,
        'title': '',
        'wrestlers': [],
        'champion_involved': False,
        'title_involved': 'None',
        'match_type': 'Normal',
        'winner': 'None',
        'finish_type': 'Pinfall',
        'promo_speaker': '',
        'storyline_id': None,
        'sponsor_objective': '',
        'description': '',
        'story_purpose': '',
        'emotional_beat': '',
        'next_week_hook': '',
        'ple_build': False,
        'ple_payoff': False,
        'is_main_event': False,
        'is_opening': False,
        'is_closing': False,
        'notes': '',
    }


def ensure_book_drafts():
    if 'book_show_drafts' not in st.session_state:
        st.session_state.book_show_drafts = {}


def get_draft(company, week):
    ensure_book_drafts()
    dk = draft_key(company, week)
    if dk not in st.session_state.book_show_drafts:
        st.session_state.book_show_drafts[dk] = {
            'company': company,
            'week': int(week),
            'format': st.session_state.get('booking_mode', 'Match Card Mode'),
            'long_story': st.session_state.get('long_story_draft', ''),
            'segments': [],
            'meta': {},
            'opening': '',
            'closing': '',
            'last_saved': '',
        }
    return st.session_state.book_show_drafts[dk]


def ensure_show_memory():
    if 'book_show_archive' not in st.session_state:
        st.session_state.book_show_archive = {}


def archive_key(company, week):
    return draft_key(company, week)


def build_show_record(
    company, week, draft, meta=None, venue=None, book_fmt='', opening='', closing='',
    long_story='', segments=None, matches=None, promos=None, full_story='',
    status='draft', rating=None, grade=None, viewership=None, profit=None, player='',
):
    """Full booking snapshot for Show Library."""
    meta = meta or draft.get('meta', {}) or {}
    return {
        'company': company,
        'week': int(week),
        'status': status,
        'format': book_fmt or draft.get('format', 'Match Card Mode'),
        'show_name': meta.get('show_name', ''),
        'episode': meta.get('episode', 'Weekly Show'),
        'ple': bool(meta.get('ple', False)),
        'featured': meta.get('featured', ''),
        'rival': meta.get('rival', ''),
        'sponsor': meta.get('sponsor', ''),
        'main_event': meta.get('main_event', ''),
        'notes': meta.get('notes', ''),
        'opening': opening or draft.get('opening', ''),
        'closing': closing or draft.get('closing', ''),
        'long_story': long_story or draft.get('long_story', ''),
        'segments': list(segments if segments is not None else draft.get('segments', [])),
        'meta': dict(meta),
        'venue': dict(venue or draft.get('venue', {})),
        'matches': list(matches or []),
        'promos': list(promos or []),
        'full_story': full_story or '',
        'rating': rating,
        'grade': grade,
        'viewership': viewership,
        'profit': profit,
        'saved_by': player,
        'updated_at': datetime.now().isoformat(timespec='seconds'),
        'last_saved': datetime.now().strftime('%H:%M:%S'),
    }


def remember_show(company, week, record, status=None):
    """Upsert one show into the universe Show Library."""
    ensure_show_memory()
    ak = archive_key(company, week)
    rec = dict(record)
    if status:
        rec['status'] = status
    rec['company'] = company
    rec['week'] = int(week)
    rec['updated_at'] = datetime.now().isoformat(timespec='seconds')
    st.session_state.book_show_archive[ak] = rec
    return rec


def migrate_weekly_history_to_archive():
    """Backfill Show Library from completed weekly_history entries."""
    ensure_show_memory()
    arch = st.session_state.book_show_archive
    for hist in st.session_state.get('weekly_history', []):
        co = hist.get('company')
        wk = hist.get('week')
        if co not in ('NXT', 'SmackDown', 'WCW') or wk is None:
            continue
        ak = archive_key(co, wk)
        if ak in arch and (arch[ak].get('long_story') or arch[ak].get('segments')):
            continue
        arch[ak] = {
            'company': co,
            'week': int(wk),
            'status': 'completed',
            'format': hist.get('booking_mode', 'Match Card Mode'),
            'show_name': hist.get('show_name', ''),
            'episode': hist.get('show_type', 'Weekly Show'),
            'ple': bool(hist.get('is_ple', False)),
            'featured': hist.get('featured_star', ''),
            'rival': hist.get('top_rivalry', ''),
            'opening': hist.get('opening', ''),
            'closing': hist.get('closing', ''),
            'long_story': hist.get('long_story', '') or (hist.get('summary', '') or ''),
            'segments': [],
            'meta': {},
            'venue': {
                'venue': hist.get('venue', ''),
                'city': hist.get('city', ''),
                'region': hist.get('region', ''),
                'country': hist.get('country', ''),
                'capacity': hist.get('capacity', 0),
            },
            'matches': list(hist.get('matches', [])),
            'promos': list(hist.get('promos', [])),
            'full_story': hist.get('summary', ''),
            'rating': hist.get('final_rating') or hist.get('episode_rating'),
            'grade': hist.get('grade', ''),
            'viewership': hist.get('viewership', 0),
            'profit': hist.get('profit', 0),
            'saved_by': hist.get('last_updated_by', ''),
            'updated_at': hist.get('last_updated_at', ''),
            'last_saved': '',
        }


def company_show_library(company):
    ensure_show_memory()
    migrate_weekly_history_to_archive()
    rows = [
        r for k, r in st.session_state.book_show_archive.items()
        if r.get('company') == company
    ]
    return sorted(rows, key=lambda x: int(x.get('week', 0)), reverse=True)


def load_show_into_draft(company, week, record):
    """Restore a saved show into the active Book Show editor."""
    dk = draft_key(company, week)
    ensure_book_drafts()
    st.session_state.book_show_drafts[dk] = {
        'company': company,
        'week': int(week),
        'format': record.get('format', 'Match Card Mode'),
        'long_story': record.get('long_story', ''),
        'segments': list(record.get('segments', [])),
        'meta': dict(record.get('meta', {})),
        'opening': record.get('opening', ''),
        'closing': record.get('closing', ''),
        'venue': dict(record.get('venue', {})),
        'last_saved': record.get('last_saved', ''),
    }
    m = st.session_state.book_show_drafts[dk]['meta']
    if record.get('show_name'):
        m['show_name'] = record['show_name']
    for k in ('episode', 'ple', 'featured', 'rival', 'sponsor', 'main_event', 'notes'):
        if record.get(k) not in (None, ''):
            m[k] = record[k]
    st.session_state.book_show_drafts[dk]['meta'] = m
    st.session_state.long_story_draft = st.session_state.book_show_drafts[dk]['long_story']
    st.session_state.booking_mode = st.session_state.book_show_drafts[dk]['format']
    st.session_state['_book_load_week'] = int(week)
    return st.session_state.book_show_drafts[dk]


def remember_completed_show(company, week, draft, meta, venue, book_fmt, opening, closing,
                            long_story, segments, matches, promos, full_story, hist):
    """Archive a show after it airs (run show)."""
    rec = build_show_record(
        company, week, draft, meta, venue, book_fmt, opening, closing, long_story, segments,
        matches, promos, full_story, status='completed',
        rating=hist.get('final_rating') or hist.get('episode_rating'),
        grade=hist.get('grade'),
        viewership=hist.get('viewership'),
        profit=hist.get('profit'),
        player=st.session_state.get('player_name', ''),
    )
    remember_show(company, week, rec, status='completed')
    return rec


def sync_draft_fields(draft, meta, venue, book_fmt, opening, closing, long_story, segments):
    draft['meta'] = dict(meta or {})
    draft['format'] = book_fmt
    draft['opening'] = opening
    draft['closing'] = closing
    draft['long_story'] = long_story
    draft['segments'] = list(segments or [])
    if venue:
        draft['venue'] = dict(venue)


def save_draft(company, week, persist=False, save_fn=None, touch_fn=None, full_record=None):
    dk = draft_key(company, week)
    draft = st.session_state.book_show_drafts[dk]
    draft['last_saved'] = datetime.now().strftime('%H:%M:%S')
    st.session_state.long_story_draft = draft.get('long_story', '')
    st.session_state.booking_mode = draft.get('format', 'Match Card Mode')
    if full_record:
        remember_show(company, week, full_record, status=full_record.get('status', 'draft'))
    else:
        remember_show(company, week, build_show_record(
            company, week, draft,
            meta=draft.get('meta', {}),
            venue=draft.get('venue', {}),
            book_fmt=draft.get('format', ''),
            opening=draft.get('opening', ''),
            closing=draft.get('closing', ''),
            long_story=draft.get('long_story', ''),
            segments=draft.get('segments', []),
            status='draft',
            player=st.session_state.get('player_name', ''),
        ), status='draft')
    if touch_fn:
        touch_fn(company)
    if persist and save_fn:
        autosave.autosave_universe(save_fn, company)
    return dk


def segments_to_matches_promos(segments):
    matches, promos = [], []
    for i, s in enumerate(segments or []):
        parts = [x for x in (s.get('wrestlers') or []) if x and x != 'None']
        story = ' '.join(filter(None, [
            s.get('story_purpose', ''), s.get('emotional_beat', ''),
            s.get('description', ''), s.get('next_week_hook', ''),
        ])).strip()
        stype = s.get('segment_type', 'Match')
        label = s.get('title') or stype or f'Segment {i + 1}'
        if s.get('is_main_event') or stype == 'Main Event':
            label += ' — MAIN EVENT'
        if stype in ('Match', 'Main Event'):
            matches.append({
                'label': label,
                'participants': parts + ['None', 'None'],
                'winner': s.get('winner', 'None'),
                'title': s.get('title_involved', 'None'),
                'stip': s.get('match_type', 'Normal'),
                'rivalry': '',
                'story': story,
                'segment_meta': s,
            })
        else:
            promos.append({
                'label': label,
                'participants': parts,
                'purpose': s.get('story_purpose', '') or stype,
                'story': story,
                'segment_meta': s,
            })
    return matches, promos


def match_card_to_long_summary(segments, opening='', closing=''):
    lines = []
    if opening:
        lines.append(f"OPENING: {opening}")
    for s in segments or []:
        stype = s.get('segment_type', 'Segment')
        title = s.get('title', '')
        wrestlers = ', '.join(x for x in (s.get('wrestlers') or []) if x and x != 'None')
        lines.append(f"\n{stype.upper()}{': ' + title if title else ''}")
        if wrestlers:
            lines.append(f"Talent: {wrestlers}")
        if s.get('story_purpose'):
            lines.append(f"Purpose: {s['story_purpose']}")
        if s.get('emotional_beat'):
            lines.append(f"Emotional beat: {s['emotional_beat']}")
        if s.get('description'):
            lines.append(s['description'])
        if s.get('next_week_hook'):
            lines.append(f"Next week: {s['next_week_hook']}")
        if s.get('winner') and s.get('winner') != 'None':
            lines.append(f"Winner: {s['winner']}")
    if closing:
        lines.append(f"\nCLOSING: {closing}")
    return '\n'.join(lines)


def apply_storylines_from_booking(company, week, rating, feedback, featured, rival, ple,
                                  segments=None, main_storyline_id=None, beat='', ple_build=False,
                                  ple_pay=False, end_story=False):
    storylines.migrate_flags_to_storylines()
    updates = storylines.update_storyline_from_show(company, rating, feedback, featured, rival, ple=ple)
    if main_storyline_id:
        sl = storylines.get_storyline(main_storyline_id)
        if sl and sl.get('company') == company:
            if beat:
                storylines.add_storyline_beat(sl, beat, week)
            if ple_build:
                sl['ple_target'] = True
            if ple_pay:
                sl['status'] = 'Ready For PLE'
                sl['ple_payoff'] = True
            if end_story:
                sl['status'] = 'Completed'
    for s in segments or []:
        sid = s.get('storyline_id')
        if not sid:
            continue
        sl = storylines.get_storyline(sid)
        if not sl or sl.get('company') != company:
            continue
        hook = s.get('next_week_hook') or s.get('story_purpose', '')
        if hook:
            storylines.add_storyline_beat(sl, hook, week)
            sl['next_beat'] = hook[:200]
        if s.get('ple_build'):
            sl['ple_target'] = True
        if s.get('ple_payoff'):
            sl['ple_payoff'] = True
            sl['status'] = 'Ready For PLE'
        if s.get('sponsor_objective'):
            sl['sponsor_tie'] = s['sponsor_objective']
        if float(rating or 7) >= 7.5:
            sl['heat'] = min(100, int(sl.get('heat', 50)) + 3)
        elif float(rating or 7) < 5:
            sl['heat'] = max(0, int(sl.get('heat', 50)) - 2)
    return updates


def render_storyline_picker(company, key_prefix='book', featured=''):
    storylines.migrate_flags_to_storylines()
    co_st = storylines.company_storylines(company)
    opts = ['— New storyline —', '— None —'] + [
        f"{s.get('id')}: {s.get('name', 'Story')}" for s in co_st[:24]
    ]
    pick = st.selectbox('Main storyline', opts, key=f'{key_prefix}_st_pick')
    beat = st.text_input('Story beat / hook for this week', key=f'{key_prefix}_st_beat')
    c1, c2, c3 = st.columns(3)
    ple_build = c1.checkbox('PLE build', key=f'{key_prefix}_ple_b')
    ple_pay = c2.checkbox('PLE payoff', key=f'{key_prefix}_ple_p')
    end_st = c3.checkbox('End storyline', key=f'{key_prefix}_st_end')
    sid = None
    if pick and not pick.startswith('—'):
        try:
            sid = int(pick.split(':')[0])
        except ValueError:
            sid = None
    if pick.startswith('— New') and st.button('Create storyline', key=f'{key_prefix}_st_new'):
        ns = storylines.default_storyline(company, f'{featured or company} arc')
        if featured and featured != 'None':
            ns['wrestlers'] = [featured]
        st.session_state.storylines.insert(0, ns)
        st.rerun()
    return sid, beat, ple_build, ple_pay, end_st


def render_run_results(h, company, gr, fin_report=None, storyline_updates=None):
    if not gr:
        return
    fb = gr.get('feedback', {}) or {}
    bd = gr.get('breakdown', {}) or {}
    with h.bfg_card('Show Results — Story-First Grade'):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric('Final AI Rating', f"{gr.get('rating', '—')}/10")
        c2.metric('Letter Grade', gr.get('grade', '—'))
        vp = gr.get('viewership_preview') or {}
        if vp:
            c3.metric('Projected viewership', f"{int(vp.get('viewership', 0)):,}")
        if fin_report:
            c4.metric('Profit / Loss', h.money(fin_report.get('profit_loss', 0)))
    if bd:
        with st.expander('Rating breakdown', expanded=True):
            st.caption(
                'Story Continuity 25% · Emotion 20% · Character 15% · Rivalry 15% · '
                'Champion 10% · Promo/Match 10% · Business 5%'
            )
            cols = st.columns(3)
            for i, (k, v) in enumerate(bd.items()):
                cols[i % 3].metric(k, f"{v}/10")
    if fin_report:
        with st.expander('Money & bank', expanded=False):
            st.write(
                f"**Old bank:** {h.money(fin_report.get('budget_before', 0))} → "
                f"**New:** {h.money(fin_report.get('budget_after', 0))}"
            )
            st.write(
                f"**Revenue:** {h.money(fin_report.get('total_revenue', 0))} · "
                f"**Expenses:** {h.money(fin_report.get('total_expenses', 0))}"
            )
    if storyline_updates:
        with st.expander('Storyline Tracker updates', expanded=False):
            for s in storyline_updates[:10]:
                st.write(f"• **{s.get('name', 'Story')}** — {s.get('status', 'Active')} · heat {s.get('heat', 0)}")
    if fb.get('next_week'):
        with st.expander('Next week suggestions', expanded=False):
            st.write(fb['next_week'])
    h.render_grade_report(gr)
    if fb.get('ai_narrative'):
        with st.expander('Full AI creative report', expanded=False):
            st.markdown(fb['ai_narrative'])


def render_show_memory_panel(h, company, mp_edit, current_week, money_fn=None):
    """Browse and reload every saved Book Show for this brand."""
    money_fn = money_fn or (lambda x: f'${int(x):,}')
    library = company_show_library(company)
    with h.bfg_card('Show Library — remembered shows'):
        st.caption(
            'Every saved draft and completed show is stored here. '
            'Switch weeks to reload a past booking into the editor.'
        )
        if not library:
            st.info('No saved shows yet. Save a draft or run a show to build your library.')
            return current_week
        opts = [
            f"Week {r['week']} — {r.get('show_name') or 'Untitled'} "
            f"({r.get('status', 'draft').title()})"
            + (f" · {r.get('rating')}/10" if r.get('rating') else '')
            for r in library
        ]
        pick = st.selectbox('Select a remembered show', range(len(opts)), format_func=lambda i: opts[i], key=f'book_mem_pick_{company}')
        rec = library[pick]
        wk = int(rec['week'])
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric('Week', wk)
        c2.metric('Status', rec.get('status', 'draft').title())
        c3.metric('Format', (rec.get('format') or '—')[:14])
        if rec.get('rating'):
            c4.metric('Rating', f"{rec['rating']}/10")
        if rec.get('viewership'):
            c5.metric('Viewership', f"{int(rec['viewership']):,}")
        st.caption(
            f"Saved **{rec.get('updated_at', '—')}** by {rec.get('saved_by') or '—'} · "
            f"{len(rec.get('segments', []))} segments · "
            f"{len(rec.get('matches', []))} matches · {len(rec.get('promos', []))} promos"
        )
        ba, bb, bc = st.columns(3)
        if ba.button('Load into editor', key=f'book_mem_load_{company}_{wk}', disabled=not mp_edit):
            load_show_into_draft(company, wk, rec)
            st.success(f'Loaded Week {wk} into the editor.')
            st.rerun()
        if bb.button('Load into current booking week', key=f'book_mem_copy_{company}_{wk}', disabled=not mp_edit):
            load_show_into_draft(company, current_week, rec)
            st.success(f'Copied Week {wk} content to booking Week {current_week}.')
            st.rerun()
        if bc.button('Refresh library', key=f'book_mem_refresh_{company}'):
            migrate_weekly_history_to_archive()
            st.rerun()
        with st.expander('View full saved show', expanded=False):
            if rec.get('show_name'):
                st.write(f"**{rec['show_name']}** · {rec.get('episode', '')} · {rec.get('venue', {}).get('venue', '')}, {rec.get('venue', {}).get('city', '')}")
            if rec.get('featured'):
                st.write(f"Featured: **{rec['featured']}** · Rivalry: {rec.get('rival', '—')}")
            if rec.get('profit') is not None and rec.get('status') == 'completed':
                st.write(f"Profit/Loss: **{money_fn(rec.get('profit', 0))}**")
            if rec.get('long_story'):
                st.text_area('Long story', rec['long_story'], height=280, disabled=True, key=f'book_mem_ls_{company}_{wk}')
            for seg in rec.get('segments', [])[:20]:
                st.write(
                    f"• **{seg.get('segment_type', 'Segment')}** — {seg.get('title', '')} · "
                    f"{', '.join(x for x in seg.get('wrestlers', []) if x and x != 'None')}"
                )
            for m in rec.get('matches', [])[:12]:
                st.write(f"• **{m.get('label', 'Match')}** → {m.get('winner', 'TBD')}")
        return wk
    return current_week


def render_match_card_builder(h, company, draft, mp_edit, co_st):
    segs = draft.setdefault('segments', [])
    st_opts = ['— None —'] + [f"{s.get('id')}: {s.get('name', '')}" for s in co_st[:20]]
    spo_opts = [''] + [lbl for lbl, _ in sponsor_obj.active_objective_options(company)]

    with st.expander('Add segment', expanded=len(segs) == 0):
        stype = st.selectbox('Segment type', SEGMENT_TYPES, key='book_add_stype')
        if st.button('＋ Add segment', key='book_add_seg', disabled=not mp_edit):
            segs.append(default_segment(company, stype))
            st.rerun()

    for idx, s in enumerate(list(segs)):
        with st.expander(
            f"{idx + 1}. {s.get('segment_type', 'Segment')} — {s.get('title', '') or 'Untitled'}",
            expanded=idx < 2,
        ):
            s['segment_type'] = st.selectbox(
                'Type', SEGMENT_TYPES,
                index=SEGMENT_TYPES.index(s['segment_type']) if s['segment_type'] in SEGMENT_TYPES else 0,
                key=f'bseg_t_{s["id"]}',
            )
            s['title'] = st.text_input('Segment title', s.get('title', ''), key=f'bseg_title_{s["id"]}')
            w1 = h.clean_name_selector(
                'Talent 1', f'bseg_w1_{s["id"]}', company_filter=True, type_filter=True,
                default_company=company, default_entity='All', extra_options=['None'], current='None',
            )
            w2 = h.clean_name_selector(
                'Talent 2', f'bseg_w2_{s["id"]}', company_filter=True, type_filter=True,
                default_company=company, default_entity='All', extra_options=['None'], current='None',
            )
            s['wrestlers'] = [x for x in [w1, w2] if x and x != 'None']
            s['champion_involved'] = st.checkbox('Champion involved', s.get('champion_involved', False), key=f'bseg_ch_{s["id"]}')
            s['title_involved'] = st.selectbox('Title', ['None'] + h.COMPANIES[company]['titles'], key=f'bseg_ti_{s["id"]}')
            if s['segment_type'] in ('Match', 'Main Event'):
                s['match_type'] = st.selectbox(
                    'Match type',
                    ['Normal', 'No DQ', 'Cage', 'Ladder', 'Title Match', 'Tag Team', 'Squash Match'],
                    key=f'bseg_mt_{s["id"]}',
                )
                s['winner'] = h.clean_name_selector(
                    'Winner', f'bseg_win_{s["id"]}',
                    options=['None', 'TBD'] + s['wrestlers'], current='None', show_search=True,
                )
                s['finish_type'] = st.selectbox('Finish', ['Pinfall', 'Submission', 'DQ', 'Count-out', 'NC'], key=f'bseg_fin_{s["id"]}')
            else:
                s['promo_speaker'] = h.clean_name_selector(
                    'Promo speaker', f'bseg_sp_{s["id"]}', company_filter=True,
                    default_company=company, extra_options=['None'], current='None',
                )
            st_pick = st.selectbox('Storyline attached', st_opts, key=f'bseg_st_{s["id"]}')
            if st_pick and not st_pick.startswith('—'):
                try:
                    s['storyline_id'] = int(st_pick.split(':')[0])
                except ValueError:
                    s['storyline_id'] = None
            else:
                s['storyline_id'] = None
            cur_spo = s.get('sponsor_objective', '')
            if cur_spo and cur_spo not in spo_opts:
                spo_opts = spo_opts + [cur_spo]
            s['sponsor_objective'] = st.selectbox(
                'Sponsor objective (assigned)', spo_opts, key=f'bseg_spo_{s["id"]}',
                help='Link segment to an open sponsor-assigned objective — not a random sponsor pick.',
            )
            s['story_purpose'] = st.text_input('Story purpose', s.get('story_purpose', ''), key=f'bseg_purp_{s["id"]}')
            s['emotional_beat'] = st.text_input('Emotional beat', s.get('emotional_beat', ''), key=f'bseg_emo_{s["id"]}')
            s['description'] = st.text_area('Segment description', s.get('description', ''), height=80, key=f'bseg_desc_{s["id"]}')
            s['next_week_hook'] = st.text_input('Next week hook', s.get('next_week_hook', ''), key=f'bseg_nx_{s["id"]}')
            m1, m2, m3 = st.columns(3)
            s['ple_build'] = m1.checkbox('PLE build', s.get('ple_build', False), key=f'bseg_pb_{s["id"]}')
            s['ple_payoff'] = m2.checkbox('PLE payoff', s.get('ple_payoff', False), key=f'bseg_pp_{s["id"]}')
            s['is_main_event'] = m3.checkbox('Main event', s.get('is_main_event', False), key=f'bseg_me_{s["id"]}')
            s['is_opening'] = st.checkbox('Opening', s.get('is_opening', False), key=f'bseg_op_{s["id"]}')
            s['is_closing'] = st.checkbox('Closing', s.get('is_closing', False), key=f'bseg_cl_{s["id"]}')
            s['notes'] = st.text_input('Notes', s.get('notes', ''), key=f'bseg_no_{s["id"]}')
            ba, bb, bc = st.columns(3)
            if ba.button('Duplicate', key=f'bseg_dup_{s["id"]}', disabled=not mp_edit):
                dup = dict(s)
                dup['id'] = random.randint(10000, 99999)
                segs.insert(idx + 1, dup)
                st.rerun()
            if bb.button('Move up', key=f'bseg_up_{s["id"]}', disabled=idx == 0 or not mp_edit):
                segs[idx], segs[idx - 1] = segs[idx - 1], segs[idx]
                st.rerun()
            if bc.button('Delete', key=f'bseg_del_{s["id"]}', disabled=not mp_edit):
                segs.pop(idx)
                st.rerun()


def render_book_show_page(h):
    h.migrate_schedule_calendar()
    company = h.render_page_shell(
        'Book Show',
        subtitle='Long Story or Match Card — story-first grading, autosave, Storyline Tracker & Weekly Performance.',
        use_brand_tabs=True,
        tabs_label='Brand',
        show_meter=True,
    )
    mp_edit = h.can_edit_company(company)
    st.caption('**Editable**' if mp_edit else '**View Only** — rival brands can preview but not edit.')
    if h.company_show_locked(company) and not h.is_admin():
        st.warning(f'{company} show is locked this week. Admin can unlock in Commissioner Control Center.')

    migrate_weekly_history_to_archive()
    nw = h.next_bookable_week()
    load_wk = st.session_state.pop('_book_load_week', None)
    if load_wk is not None:
        nw = int(load_wk)
    draft = get_draft(company, nw)
    wp_co = st.session_state.week_progress.get(company, {})
    st.caption(
        f"**{company}** · Universe week **{st.session_state.week}** · Booking week **{nw}** · "
        f"Status: {wp_co.get('status', 'Not Started')}" + (' · Locked' if wp_co.get('locked') else '')
    )

    cal_locked = st.session_state.get('calendar_locked', False)
    sched = h.get_scheduled_show(company, nw)
    if cal_locked and not sched:
        st.error(f'Calendar locked but no Week {nw} entry for {company}.')
    if sched:
        loc = h.format_schedule_location(sched)
        st.markdown(
            f"<div class='event-box'><b>Week {nw} — {sched.get('show_name', '')}</b> · {loc} · "
            f"{sched.get('venue', '')}</div>",
            unsafe_allow_html=True,
        )

    default_name = {'NXT': f'NXT Week {nw}', 'SmackDown': f'SmackDown Week {nw}', 'WCW': f'WCW Week {nw}'}.get(company)
    sched_name = sched.get('show_name', default_name) if sched else default_name
    episode_opts = [
        'Weekly Show', 'Go-home before PLE', 'Fallout after PLE', 'PLE', 'TV Special',
        'Tournament', 'International Tour', 'Stadium Show', 'Homecoming Show',
    ]
    sched_type = sched.get('show_type', 'Weekly Show') if sched else 'Weekly Show'
    episode_val = h.schedule_to_episode_type(sched_type) if sched else 'Weekly Show'
    ple_locked = h.schedule_show_is_ple(sched_type) if sched else False

    meta = draft.setdefault('meta', {})
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        show_name = st.text_input('Show name', meta.get('show_name', sched_name), key='book_show_name')
    with m2:
        ep_idx = episode_opts.index(episode_val) if episode_val in episode_opts else 0
        episode = st.selectbox('Show type', episode_opts, index=ep_idx, key='book_episode')
    with m3:
        ple = st.checkbox('PLE target', value=ple_locked or episode == 'PLE', key='book_ple')
    with m4:
        featured = h.clean_name_selector(
            'Featured star', 'book_feat', company_filter=True, type_filter=True,
            default_company=company, default_entity='All',
        )
    meta.update({'show_name': show_name, 'episode': episode, 'ple': ple, 'featured': featured})
    rival = st.text_input('Top rivalry', sched.get('planned_rivalry', '') if sched else '', key='book_rival')
    meta['rival'] = rival
    spo_opts = [''] + [lbl for lbl, _ in sponsor_obj.active_objective_options(company)]
    cur_meta_spo = meta.get('sponsor', '')
    if cur_meta_spo and cur_meta_spo not in spo_opts:
        spo_opts = spo_opts + [cur_meta_spo]
    meta['sponsor'] = st.selectbox(
        'Sponsor objective attached', spo_opts, key='book_sponsor',
        help='Attach show to a sponsor-assigned objective from Sponsor Objectives page.',
    )
    meta['main_event'] = st.text_input('Main event (label)', meta.get('main_event', ''), key='book_main_ev')
    meta['notes'] = st.text_area('Notes', meta.get('notes', ''), height=60, key='book_notes')

    if sched and sched.get('venue_data'):
        venue = dict(sched['venue_data'])
    elif cal_locked:
        st.error('Venue missing on calendar.')
        venue = {
            'country': 'United States', 'region': 'NY', 'city': 'New York City', 'venue': 'Arena',
            'capacity': 15000, 'rental_cost': 400000, 'security_cost': 100000,
            'travel_multiplier': 1.1, 'prestige': 5,
        }
    else:
        venue = h.venue_selector('book')

    render_show_memory_panel(h, company, mp_edit, nw, money_fn=h.money)

    with st.expander('Book a different week', expanded=False):
        week_opts = sorted({int(r.get('week', 0)) for r in company_show_library(company)} | {int(nw), int(st.session_state.week), int(nw) + 1})
        week_opts = [w for w in week_opts if w >= 0] or [int(nw)]
        bw = st.selectbox('Editing week', week_opts, index=week_opts.index(int(nw)) if int(nw) in week_opts else 0, key=f'book_edit_week_{company}')
        if bw != nw and st.button('Switch to this week', key=f'book_switch_week_{company}', disabled=not mp_edit):
            draft = get_draft(company, bw)
            nw = int(bw)
            st.rerun()
        st.caption(f"Currently editing **Week {nw}** · Next bookable: **{h.next_bookable_week()}**")

    autosave.render_autosave_indicator('book_as')
    if draft.get('last_saved'):
        st.caption(f"Draft auto-saved **{draft['last_saved']}** · {len(company_show_library(company))} shows in library")

    fmt_idx = 0 if draft.get('format', 'Match Card Mode') == 'Long Story Mode' else 1
    book_fmt = st.radio('Book Show Format', BOOK_FORMATS, horizontal=True, index=fmt_idx, key='book_format_radio')
    draft['format'] = book_fmt
    st.session_state.booking_mode = book_fmt

    opening = draft.get('opening', '')
    closing = draft.get('closing', '')
    long_story = draft.get('long_story', st.session_state.get('long_story_draft', ''))
    matches, promos = [], []

    if book_fmt == 'Long Story Mode':
        st.markdown('#### Full Show Story / Long-Term Story')
        st.caption(
            'Paste your full episode, PLE, rivalry build, promos, matches, backstage segments, '
            'Twitter fallout, sponsor moments, and story details. AI grades story-first and updates trackers.'
        )
        long_story = st.text_area(
            'Full show story',
            value=long_story,
            height=640,
            key='book_long_story_area',
            disabled=not mp_edit,
        )
        draft['long_story'] = long_story
        st.session_state.long_story_draft = long_story
        o1, o2 = st.columns(2)
        with o1:
            draft['opening'] = st.text_area('Opening segment (optional)', draft.get('opening', ''), height=70, key='book_opening')
        with o2:
            draft['closing'] = st.text_area('Closing angle (optional)', draft.get('closing', ''), height=70, key='book_closing')
        opening, closing = draft['opening'], draft['closing']
        if st.button('AI Extract Match Card From Long Story', key='book_extract_mc', disabled=not mp_edit):
            sp = h.parse_long_story(long_story, company)
            st.session_state.story_parse = sp
            for m in sp.get('matches', []):
                seg = default_segment(company, 'Match')
                seg['title'] = m.get('line', '')[:80]
                seg['wrestlers'] = m.get('participants', [])
                seg['winner'] = m.get('winner', 'TBD')
                seg['description'] = m.get('line', '')
                draft['segments'].append(seg)
            for p in sp.get('promos', []):
                seg = default_segment(company, 'Promo')
                seg['description'] = p.get('line', '')
                draft['segments'].append(seg)
            st.success('Segments extracted — switch to Match Card Mode to edit.')
            st.rerun()
    else:
        st.markdown('#### Match Card Mode')
        st.caption('Unlimited segments with story boxes — each can attach to Storyline Tracker.')
        draft['opening'] = st.text_area('Opening segment', draft.get('opening', opening), height=60, key='book_open_card')
        draft['closing'] = st.text_area('Closing angle', draft.get('closing', closing), height=60, key='book_close_card')
        opening, closing = draft['opening'], draft['closing']
        co_st = storylines.company_storylines(company)
        render_match_card_builder(h, company, draft, mp_edit, co_st)
        cnv1, cnv2 = st.columns(2)
        with cnv1:
            if st.button('Convert Match Card to Long Story Summary', key='book_to_long', disabled=not mp_edit):
                draft['long_story'] = match_card_to_long_summary(draft['segments'], opening, closing)
                st.session_state.long_story_draft = draft['long_story']
                st.success('Summary saved to Long Story draft (switch format to view).')
                st.rerun()

    sid, beat, ple_build, ple_pay, end_st = render_storyline_picker(company, 'book', featured)

    if st.session_state.get('ai_booked_show'):
        st.info('AI-booked show — official rating disabled until you mark user-edited.')
        st.session_state.show_user_edited = st.checkbox(
            'Mark as user-edited and allow grading',
            value=st.session_state.get('show_user_edited', False),
            key='book_user_edited',
        )

    if book_fmt == 'Long Story Mode':
        sp = h.parse_long_story(long_story, company) if long_story.strip() else {'matches': [], 'promos': []}
        for m in sp.get('matches', []):
            matches.append({
                **m,
                'label': m.get('label', 'Match'),
                'participants': m.get('participants', []),
                'story': m.get('line', ''),
            })
        for p in sp.get('promos', []):
            promos.append({
                'label': 'Promo',
                'participants': p.get('participants', []),
                'purpose': 'Detected',
                'story': p.get('line', ''),
            })
    else:
        matches, promos = segments_to_matches_promos(draft.get('segments', []))

    full = h.build_show_story(long_story if book_fmt == 'Long Story Mode' else '', opening, promos, matches, closing)

    with h.bfg_card('Card preview'):
        st.write(f"**{show_name}** · {company} · {venue.get('venue', '')}, {venue.get('city', '')}")
        for p in promos[:14]:
            st.write(f"• **{p.get('label', 'Promo')}** — {', '.join(p.get('participants', []) or [])}")
        for m in matches[:14]:
            st.write(
                f"• **{m.get('label', 'Match')}** — "
                f"{' vs '.join([x for x in m.get('participants', []) if x != 'None'])} → {m.get('winner', 'TBD')}"
            )

    ctx_pack = h.booking_context_pack(company, venue, featured, rival, sched, nw)
    ctx_pack['ple'] = ple
    can_run = (
        (not cal_locked or bool(sched)) and mp_edit
        and not (h.company_show_locked(company) and not h.is_admin())
    )

    st.markdown('#### Actions')
    b1, b2, b3, b4, b5, b6, b7, b8 = st.columns(8)
    if b1.button('Save draft', key='book_save_draft', disabled=not mp_edit):
        sync_draft_fields(draft, meta, venue, book_fmt, opening, closing, long_story, draft.get('segments', []))
        rec = build_show_record(
            company, nw, draft, meta, venue, book_fmt, opening, closing, long_story,
            draft.get('segments', []), matches, promos, full,
            status='draft', player=st.session_state.get('player_name', ''),
        )
        save_draft(company, nw, persist=True, save_fn=h.save_universe, touch_fn=h.touch_universe_meta, full_record=rec)
        try:
            h.mark_company_draft_saved(company)
        except AttributeError:
            pass
        st.success('Draft saved to Show Library.')
        st.rerun()
    if b2.button('Run AI show grade', key='book_grade', disabled=not mp_edit):
        if not h.official_rating_enabled():
            st.session_state.last_grade = {
                'rating': 0, 'grade': '—', 'notes': [], 'feedback': {}, 'breakdown': {},
                'official': False,
                'disabled_reason': 'AI-booked — mark user-edited to grade.',
                'company': company,
            }
        else:
            gr = h.build_grade_result(
                full, featured, rival, venue, ple, company, matches, promos, sched, book_fmt, use_ai=True,
            )
            gr['company'] = company
            vp = h.calculate_show_viewership(
                company, gr['rating'], gr['feedback'], gr['breakdown'],
                venue, featured, rival, ple, sched, matches, promos,
            )
            gr['viewership'] = vp['viewership']
            gr['viewership_preview'] = vp
            st.session_state.last_grade = gr
        save_draft(company, nw)
        st.rerun()
    if b3.button('Update Storyline Tracker', key='book_st_upd', disabled=not mp_edit):
        gr = h.build_grade_result(
            full, featured, rival, venue, ple, company, matches, promos, sched, book_fmt, use_ai=False,
        )
        upd = apply_storylines_from_booking(
            company, nw, gr['rating'], gr['feedback'], featured, rival, ple,
            draft.get('segments', []), sid, beat, ple_build, ple_pay, end_st,
        )
        st.session_state.last_storyline_updates = upd
        h.touch_universe_meta(company)
        h.save_universe()
        st.success(f'Storyline Tracker updated ({len(upd)} storylines).')
        st.rerun()
    if b4.button('Generate WP preview', key='book_wp_prev', disabled=not mp_edit):
        gr = st.session_state.get('last_grade') or h.build_grade_result(
            full, featured, rival, venue, ple, company, matches, promos, sched, book_fmt, use_ai=False,
        )
        vp = h.calculate_show_viewership(
            company, gr['rating'], gr['feedback'], gr.get('breakdown', {}),
            venue, featured, rival, ple, sched, matches, promos,
        )
        st.session_state.wp_grade_preview = {
            'company': company, 'week': nw, 'rating': gr['rating'], 'viewership': vp.get('viewership', 0),
            'note': 'Run show to lock official Weekly Performance record.',
        }
        st.info(f"Preview: {gr['rating']}/10 · ~{vp.get('viewership', 0):,} viewers. Run show to finalize.")
    if b5.button('Clear long story', key='book_clear_ls', disabled=not mp_edit):
        st.session_state['_book_clear_confirm'] = True
    if st.session_state.get('_book_clear_confirm'):
        if st.checkbox('Confirm clear long story draft', key='book_clear_confirm'):
            draft['long_story'] = ''
            st.session_state.long_story_draft = ''
            st.session_state['_book_clear_confirm'] = False
            st.rerun()
    if b6.button('Run show as this week', key='book_run', disabled=not can_run):
        sync_draft_fields(draft, meta, venue, book_fmt, opening, closing, long_story, draft.get('segments', []))
        h.run_book_show_week(
            company, nw, show_name, episode, venue, ple, featured, rival, sched,
            full, matches, promos, book_fmt, opening, closing, long_story,
            sid, beat, ple_build, ple_pay, end_st, draft.get('segments', []),
            draft, meta,
        )
        save_draft(company, nw, persist=True, save_fn=h.save_universe, touch_fn=h.touch_universe_meta)
        st.rerun()
    if b7.button('AI suggest', key='book_ai_sug', disabled=not mp_edit):
        st.session_state.last_suggest = h.ai_suggest_improvements(full, company, ctx_pack)
        st.rerun()
    if b8.button('AI book show', key='book_ai_book', disabled=not mp_edit):
        written = h.ai_book_show(company, ctx_pack, long_format=(book_fmt == 'Long Story Mode'))
        draft['long_story'] = written
        st.session_state.long_story_draft = written
        st.session_state.ai_booked_show = True
        st.session_state.show_user_edited = False
        st.rerun()

    fin = st.session_state.get('last_show_finance_report')
    if fin and fin.get('company') == company:
        render_run_results(
            h, company, st.session_state.get('last_grade'),
            fin_report=fin,
            storyline_updates=st.session_state.get('last_storyline_updates'),
        )
    elif st.session_state.get('last_grade') and st.session_state.last_grade.get('company') == company:
        render_run_results(
            h, company, st.session_state.last_grade,
            storyline_updates=st.session_state.get('last_storyline_updates'),
        )

    if st.session_state.get('last_dirt_sheet') and st.session_state.last_dirt_sheet.get('company') == company:
        h.render_viewership_dirt_sheet(st.session_state.last_dirt_sheet)
    if st.session_state.get('last_suggest'):
        with st.expander('AI suggestions', expanded=False):
            st.markdown(st.session_state.last_suggest)

    if mp_edit:
        sync_draft_fields(draft, meta, venue, book_fmt, opening, closing, long_story, draft.get('segments', []))
        save_draft(company, nw)
