"""Polished page renderers — uses helpers registered by app.py (never imports app)."""
from types import SimpleNamespace

import streamlit as st

import bfg_autosave as autosave
import bfg_storylines as sl
import bfg_sponsor_objectives as spo
import bfg_season_awards as sa

PLAYABLE = ['NXT', 'SmackDown', 'WCW']

# Populated from app.py via register_helpers() — never import app.py from here.
H = None


def register_helpers(**kwargs):
    """Bind callables/constants from the running app module (no import of app)."""
    global H
    H = SimpleNamespace(**kwargs)


def _h():
    if H is None:
        raise RuntimeError(
            'UI helpers not registered. Restart the app — app.py must call register_ui_page_helpers() before pages render.'
        )
    return H


def render_game_intro():
    h = _h()
    h.render_storage_status_banner('page')
    autosave.render_autosave_indicator('intro_as')
    st.markdown('<div class="game-title">BOUND FOR GLORY</div>', unsafe_allow_html=True)
    st.markdown('<div class="game-title-sm">GM MODE</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="game-subtitle">Multiplayer wrestling GM — book shows, stories, sponsors, and brands.</div>',
        unsafe_allow_html=True,
    )
    with h.bfg_card('How To Play'):
        st.markdown(
            """
**Bound For Glory GM Mode** is a multiplayer wrestling GM game where players control **NXT**, **SmackDown**, or **WCW**.

Each player books shows, writes stories, manages contracts, completes sponsor objectives, handles money, builds stars, reacts to random events, and competes to have the best brand.

**Winning is not just money.** The best brand wins with:
- Strong stories and continuity
- Sponsor objective execution
- PLE payoffs and fan investment
- Viewership, attendance, and popularity growth
- Profit from *great* booking

Money matters — but it should follow great stories and completed objectives.
            """
        )
    c1, c2, c3, c4 = st.columns(4)
    if c1.button('Create Private Game', type='primary', use_container_width=True, key='gate_create'):
        st.session_state.gate_screen = 'login'
        st.session_state.gate_login_tab = 0
        st.rerun()
    if c2.button('Join Private Game', type='primary', use_container_width=True, key='gate_join'):
        st.session_state.gate_screen = 'login'
        st.session_state.gate_login_tab = 1
        st.rerun()
    if c3.button('Continue Saved Game', use_container_width=True, key='gate_continue'):
        st.session_state.gate_screen = 'continue'
        st.rerun()
    if c4.button('View Tutorial', use_container_width=True, key='gate_tutorial'):
        st.session_state.gate_screen = 'tutorial'
        st.rerun()
    if st.button('Solo test mode (quick)', key='gate_solo'):
        st.session_state.gate_screen = 'login'
        st.rerun()
    st.markdown('---')
    with h.bfg_card('I have my invite code + brand code'):
        st.caption('Use the **invite code** (BFG-xxxx) plus your **8-letter brand code** (NXT, WCW, SmackDown, or Admin).')
        j_inv = st.text_input('Invite code', key='gate_join_inv', placeholder='BFG-6051')
        j_name = st.text_input('Your name', key='gate_join_name', value='Joshua')
        j_acc = st.text_input('Brand code', key='gate_join_acc', placeholder='NXT / WCW / Admin — 8 characters')
        if j_inv.strip() and hasattr(h, 'lookup_invite_session'):
            hit = h.lookup_invite_session(j_inv.strip())
            if hit:
                pics = hit.get('picture_stats') or {}
                st.success(
                    f"Found **{hit.get('game_name', 'game')}** on this computer · Week {hit.get('week', 0)} · "
                    f"pictures NXT {pics.get('NXT', 0)} · WCW {pics.get('WCW', 0)} · SmackDown {pics.get('SmackDown', 0)}"
                )
                st.code(
                    f"Invite: {hit.get('invite_code', '')}\n"
                    f"Admin: {hit.get('admin_code', '')}\n"
                    f"NXT: {hit.get('nxt_code', '')}\n"
                    f"SmackDown: {hit.get('smackdown_code', '')}\n"
                    f"WCW: {hit.get('wcw_code', '')}",
                    language=None,
                )
            else:
                st.warning('Invite not on **this computer**. Use the same Streamlit URL where you created the game, or Continue Saved Game to clone a local copy.')
        if st.button('Join my session', type='primary', key='gate_join_codes_btn'):
            if hasattr(h, 'request_join_with_codes'):
                if not j_inv.strip() or not j_acc.strip() or not j_name.strip():
                    st.error('Enter invite code, your name, and brand code.')
                else:
                    h.request_join_with_codes(j_inv.strip(), j_acc.strip(), j_name.strip())
    st.markdown('---')
    if hasattr(h, 'request_quick_login'):
        cqe1, cqe2 = st.columns(2)
        with cqe1:
            if st.button(
                '▶ ENTER BFG-9309 (Admin)',
                type='primary',
                use_container_width=True,
                key='gate_quick_enter',
            ):
                h.request_quick_login('BFG-9309', 'Joshua')
        with cqe2:
            if hasattr(h, 'request_join_with_codes') and st.button(
                '▶ BFG-9309 + 3K5FC2PY',
                use_container_width=True,
                key='gate_join_9309_code',
            ):
                h.request_join_with_codes('BFG-9309', '3K5FC2PY', 'Joshua')
        st.caption('**BFG-9309** easywork · your code **3K5FC2PY** = Admin · or one-click enter with no codes.')
    saves = h.list_saved_sessions() if hasattr(h, 'list_saved_sessions') else []
    if saves:
        st.caption('Saved games here: ' + ', '.join(f"{s.get('game_name')} ({s.get('invite_code','local')})" for s in saves[:4]))


def _continue_session(s, as_admin=True):
    h = _h()
    if hasattr(h, 'request_continue_session'):
        h.request_continue_session(s['session_id'], 'Joshua')
        return
    import bfg_sessions as mp
    meta = mp.load_session_meta(s['session_id']) or {} if s['session_id'] != 'local' else {}
    st.session_state.session_id = s['session_id']
    st.session_state.logged_in = True
    st.session_state.game_name = s.get('game_name', 'Continued Game')
    st.session_state.invite_code = s.get('invite_code') or meta.get('invite_code', '')
    st.session_state._universe_loaded = False
    st.session_state.gate_screen = ''
    st.rerun()


def render_continue_saved():
    h = _h()
    import bfg_sessions as mp

    st.markdown('### Continue Saved Game')
    st.caption('Pick a universe on **this computer**. Use **Clone → new session** if old invite codes stopped working.')
    sessions = mp.list_saved_sessions()
    if not sessions:
        st.info('No saved universes found on this server. Create or join a private game, or use solo test mode.')
    else:
        for s in sessions[:12]:
            sid = s['session_id']
            with h.bfg_card(s.get('game_name', 'Universe')):
                st.markdown(
                    f"**{s.get('game_name', 'Universe')}** — Week {s.get('week', 0)} · updated {s.get('updated', '—')}"
                )
                pics = s.get('picture_stats') or {}
                pic_line = f" · pictures NXT {pics.get('NXT', 0)} WCW {pics.get('WCW', 0)} SD {pics.get('SmackDown', 0)}"
                if s.get('invite_code'):
                    st.caption(f"Invite `{s['invite_code']}` · session `{sid[:12]}…`{pic_line}")
                else:
                    st.caption(f"Session `{sid[:12]}…`{pic_line}")
                if s.get('admin_code'):
                    st.code(
                        f"Invite: {s.get('invite_code', '')}\n"
                        f"Admin: {s.get('admin_code', '')}\n"
                        f"NXT: {s.get('nxt_code', '')}\n"
                        f"SmackDown: {s.get('smackdown_code', '')}\n"
                        f"WCW: {s.get('wcw_code', '')}",
                        language=None,
                    )
                if pics.get('total', 0) == 0 or pics.get('WCW', 0) == 0 or pics.get('SmackDown', 0) == 0:
                    st.warning(
                        'Pictures for this save on **this computer**: '
                        f"NXT {pics.get('NXT', 0)} · SmackDown {pics.get('SmackDown', 0)} · WCW {pics.get('WCW', 0)}. "
                        'Full portraits may still be on **Streamlit Cloud** — open that app, or use Save Center → Pull from Supabase.'
                    )
                c1, c2, c3, c4, c5 = st.columns(5)
                if c1.button('Admin', key=f'cont_admin_{sid[:12]}', type='primary', use_container_width=True):
                    _continue_session(s, as_admin=True)
                if c2.button('NXT GM', key=f'cont_nxt_{sid[:12]}', use_container_width=True):
                    if s.get('nxt_code') and hasattr(h, 'request_join_with_codes'):
                        h.request_join_with_codes(s['invite_code'], s['nxt_code'], 'Joshua')
                if c3.button('SmackDown GM', key=f'cont_sd_{sid[:12]}', use_container_width=True):
                    if s.get('smackdown_code') and hasattr(h, 'request_join_with_codes'):
                        h.request_join_with_codes(s['invite_code'], s['smackdown_code'], 'Joshua')
                if c4.button('WCW GM', key=f'cont_wcw_{sid[:12]}', use_container_width=True):
                    if s.get('wcw_code') and hasattr(h, 'request_join_with_codes'):
                        h.request_join_with_codes(s['invite_code'], s['wcw_code'], 'Joshua')
                if c5.button('Clone', key=f'cont_clone_{sid[:12]}', use_container_width=True):
                    st.session_state._clone_source_id = sid
                    st.session_state._clone_source_name = s.get('game_name', 'Universe')
                    st.rerun()
        if st.session_state.get('_clone_source_id'):
            src = st.session_state._clone_source_id
            src_name = st.session_state.get('_clone_source_name', 'Universe')
            st.markdown('---')
            st.markdown(f'#### Clone **{src_name}** → new session')
            st.caption('Keeps roster, pictures, champions, calendar, and finances. Gives you **new login codes**.')
            new_name = st.text_input('New game name', value=f'{src_name} v2', key='cont_clone_gname')
            creator = st.text_input('Your name (Admin)', value='Joshua', key='cont_clone_admin')
            c1, c2 = st.columns(2)
            if c1.button('Create cloned session', type='primary', key='cont_clone_confirm'):
                if not new_name.strip() or not creator.strip():
                    st.error('Enter a game name and your name.')
                else:
                    try:
                        meta = mp.clone_private_session(src, new_name.strip(), creator.strip())
                        st.session_state.pop('_clone_source_id', None)
                        st.session_state.pop('_clone_source_name', None)
                        st.session_state.mp_created_codes = meta
                        st.session_state.gate_screen = 'login'
                        st.success('Cloned successfully. Save your **new codes** on the next screen.')
                        st.rerun()
                    except Exception as ex:
                        st.error(f'Clone failed: {ex}')
            if c2.button('Cancel clone', key='cont_clone_cancel'):
                st.session_state.pop('_clone_source_id', None)
                st.session_state.pop('_clone_source_name', None)
                st.rerun()
    if st.button('← Back', key='cont_back'):
        st.session_state.pop('_clone_source_id', None)
        st.session_state.gate_screen = 'intro'
        st.rerun()


def render_tutorial_page():
    h = _h()
    h.render_page_shell('Tutorial / How To Play', subtitle='Everything you need for a smooth friend-group session.', show_meter=False)
    sections = [
        ('1. Create or join', 'Host creates a **private game** and shares invite + role codes. Friends join with invite code + NXT / SmackDown / WCW / Admin code.'),
        ('2. Log in', 'Pick your role: **NXT GM**, **SmackDown GM**, **WCW GM**, or **Admin**. You can only edit your brand; rivals are view-only.'),
        ('3. Book a show', 'Use **Schedule Calendar** then **Book Show**. Structured card or Long Story Mode. AI grades when you run the show.'),
        ('4. AI grading', 'Ratings use story quality, logistics, champions, sponsors, and continuity. AI-booked shows need “user-edited” to count as official manual ratings.'),
        ('5. Storyline Tracker', 'Tracks feuds, heat, continuity, PLE targets. Book Show links storylines; AI updates after each show.'),
        ('6. Sponsor Objectives', 'Quarterly activations — complete requirements for payouts; miss them for penalties.'),
        ('7. Money', '**Finance** is the detailed ledger. **Live Money Meter** on major pages. **Weekly Performance** shows result money only.'),
        ('8. Contracts & Free Agency', '**Contracts** for renewals; free agents and bidding under crisis rules.'),
        ('9. Twitter', 'Posts, fan heat, and **Recruit / Tamper** for cross-brand recruitment.'),
        ('10. Weekly Performance', 'Fan view rating graphs, Dirt Sheet grading table, and full show reports per brand.'),
        ('11. Season Awards', 'End-of-year weighted score (story 30%, continuity 20%, sponsors 15%, PLE 15%, growth, profit 3%).'),
        ('12. Saves', 'Auto-save on edits. **Save Center** for backup. Each private session is isolated — NXT never overwrites SmackDown.'),
    ]
    for title, body in sections:
        with h.bfg_card(title):
            st.markdown(body)
    if st.button('← Back to intro', key='tut_back'):
        st.session_state.gate_screen = 'intro'
        st.rerun()


def render_storyline_tracker_page():
    h = _h()
    sl.migrate_flags_to_storylines()
    comp = h.render_page_shell(
        'Storyline Tracker',
        subtitle='Story memory for AI continuity — heat, unresolved beats, PLE targets.',
        use_brand_tabs=True,
        show_meter=True,
    )
    can = h.can_edit_company(comp)
    autosave.render_autosave_indicator()
    stories = sl.company_storylines(comp)
    if can and st.button('＋ New storyline', key='st_new'):
        s = sl.default_storyline(comp, f'{comp} Story {len(stories) + 1}')
        st.session_state.storylines.insert(0, s)
        h.touch_universe_meta(comp)
        h.save_universe()
        st.rerun()
    if not stories:
        st.info('No storylines yet. Create one or book a show with a featured star.')
    for s in stories[:24]:
        with h.bfg_card(f"{s.get('name', 'Story')} · {s.get('status', 'Active')}"):
            c1, c2, c3 = st.columns(3)
            c1.metric('Heat', s.get('heat', 0))
            c2.metric('Quality', s.get('quality_score', 0))
            c3.metric('Continuity', s.get('continuity_score', 0))
            st.caption(
                f"Type: {s.get('story_type')} · Wrestlers: {', '.join(s.get('wrestlers') or []) or '—'} · "
                f"Last week: {s.get('last_updated_week', '—')}"
            )
            if s.get('ai_warning'):
                st.warning(s['ai_warning'])
            if s.get('last_week_summary'):
                st.write('**Last week:**', s['last_week_summary'])
            if s.get('unresolved'):
                st.write('**Unresolved:**', '; '.join(s['unresolved'][:5]))
            if s.get('next_beat'):
                st.write('**Next beat:**', s['next_beat'])
            if can:
                with st.expander('Edit storyline', expanded=False):
                    s['name'] = st.text_input('Name', s.get('name', ''), key=f"stn_{s['id']}")
                    s['status'] = st.selectbox('Status', sl.STATUSES, index=sl.STATUSES.index(s.get('status', 'Active')) if s.get('status') in sl.STATUSES else 0, key=f"sts_{s['id']}")
                    s['story_type'] = st.selectbox('Type', sl.STORY_TYPES, key=f"stt_{s['id']}")
                    s['notes'] = st.text_area('Notes', s.get('notes', ''), key=f"stno_{s['id']}")
                    s['next_beat'] = st.text_input('Next suggested beat', s.get('next_beat', ''), key=f"stnb_{s['id']}")
                    if st.button('Save storyline', key=f"stsave_{s['id']}"):
                        h.touch_universe_meta(comp)
                        h.save_universe()
                        st.toast('Storyline saved.')
                        st.rerun()


def render_sponsor_objectives_page():
    h = _h()
    spo.ensure_sponsor_objectives(h.COMPANIES)
    comp = h.render_page_shell(
        'Sponsor Objectives',
        subtitle='Quarterly sponsor requirements, progress, payouts, and penalties.',
        use_brand_tabs=True,
        show_meter=True,
    )
    objs = spo.company_objectives(comp)
    _badge_cls = {'Completed': 'green', 'Paid': 'green', 'Met': 'green', 'Submitted': 'blue',
                  'In Progress': 'gold', 'Active': 'gold', 'Partial': 'silver',
                  'Failed': 'red', 'Not Started': 'gray'}
    for o in objs:
        pct = min(100, int(100 * int(o.get('progress', 0)) / max(1, int(o.get('target', 3)))))
        stt = o.get('status', 'Active')
        with h.bfg_card():
            st.markdown(
                f"**🤝 {o.get('sponsor', o.get('title', 'Sponsor'))} — {o.get('title', 'Objective')}** "
                f"<span class='bfg-badge {_badge_cls.get(stt, 'gray')}'>{stt}</span>",
                unsafe_allow_html=True,
            )
            st.progress(pct / 100.0)
            st.write(o.get('requirement', ''))
            st.markdown(
                f"<span class='bfg-badge silver'>Progress {o.get('progress', 0)}/{o.get('target', 3)}</span>"
                f"<span class='bfg-badge green'>Payout {h.money(o.get('payout', 0))}</span>"
                f"<span class='bfg-badge red'>Penalty {h.money(o.get('penalty', 0))}</span>",
                unsafe_allow_html=True,
            )
            if h.can_edit_company(comp) and o.get('status') == 'Active' and st.button('Mark progress +1', key=f"spo_{o['id']}"):
                o['progress'] = min(int(o.get('target', 3)), int(o.get('progress', 0)) + 1)
                if o['progress'] >= int(o.get('target', 3)):
                    o['status'] = 'Completed'
                    o['week_completed'] = st.session_state.week
                h.touch_universe_meta(comp)
                h.save_universe()
                st.rerun()


def render_season_awards_page():
    h = _h()
    h.render_page_shell('Season Awards', subtitle='End-of-year winners — weighted score, not richest brand only.', show_meter=False)
    result = sa.compute_season_awards(st.session_state)
    st.markdown(result['explanation'])
    cols = st.columns(3)
    for i, c in enumerate(PLAYABLE):
        m = result['metrics'][c]
        with cols[i]:
            st.markdown(f"### {c}")
            st.metric('Season score', m['composite'])
            st.caption(
                f"Story {m['story_quality']} · Cont. {m['continuity']} · Sponsors {m['sponsor_pct']}% · PLE {m['ple_avg']}"
            )
    st.success(f"**Season champion: {result['winner']}**")
    with st.expander('All awards', expanded=True):
        for name, val in result['awards'].items():
            st.write(f"**{name}:** {val}")


def render_multiplayer_dashboard():
    h = _h()
    h.sync_session_from_storage(light=True)
    h.render_page_shell(
        'Multiplayer Dashboard',
        subtitle='Week progress for all three brands — banks, ratings, unfinished tasks.',
        show_meter=False,
        show_badge=True,
    )
    h.render_money_meter_multi()
    gn = st.session_state.get('game_name', '')
    if gn:
        st.caption(f'**{gn}** · Session `{h.get_session_id()[:10]}…`')
    st.caption(f'**Shared universe week:** {st.session_state.week} · Next bookable: **Week {h.next_bookable_week()}**')
    ready = h.all_companies_week_completed()
    st.metric('Ready to advance week', 'Yes' if ready else 'No — waiting on GMs')
    cols = st.columns(3)
    for i, comp in enumerate(PLAYABLE):
        wp = st.session_state.week_progress.get(comp, {})
        hist = next((h for h in reversed(st.session_state.weekly_history) if h.get('company') == comp), None)
        fin = st.session_state.company_finance.get(comp, {})
        pending = []
        if wp.get('status') not in ('Completed', 'Locked'):
            pending.append('Finish weekly show')
        with cols[i]:
            st.markdown(f'### {comp}')
            st.write(f"**GM:** {h.get_assigned_gm_display(comp)}")
            st.write(f"**Status:** {wp.get('status', 'Not Started')}")
            st.metric('Bank', h.money(fin.get('current_budget', 0)))
            if hist:
                st.write(f"**Last rating:** {hist.get('episode_rating', '—')}/10")
                st.write(f"**Viewership:** {int(hist.get('viewership', 0)):,}")
                st.write(f"**P/L:** {h.money(hist.get('profit', 0))}")
            spo_done = sum(1 for o in st.session_state.get('sponsor_objectives', []) if o.get('company') == comp and o.get('status') == 'Completed')
            st.caption(f"Sponsor objectives done: {spo_done}")
            if pending:
                st.warning(' · '.join(pending))


def render_commissioner_control_center():
    h = _h()
    if not h.is_admin():
        st.error('Commissioner Control Center is Admin / Commissioner only.')
        return
    h.render_page_shell(
        'Commissioner Control Center',
        subtitle='Admin overrides — week advance, unlocks, backups, session health.',
        show_meter=False,
    )
    st.write(f"**Week {st.session_state.week}** · Calendar locked: **{st.session_state.get('calendar_locked', False)}**")
    for comp in PLAYABLE:
        wp = st.session_state.week_progress.get(comp, {})
        st.write(f"**{comp}:** {wp.get('status', 'Not Started')} · locked={wp.get('locked', False)}")
    incomplete = [c for c in PLAYABLE if st.session_state.week_progress.get(c, {}).get('status') != 'Completed']
    if incomplete:
        st.warning('Incomplete shows: ' + ', '.join(incomplete))
    pending_tr = [t for t in st.session_state.pending_trades if t.get('status') == 'Proposed']
    st.write(f"**Pending trades:** {len(pending_tr)}")
    c1, c2, c3 = st.columns(3)
    if c1.button('Advance week (all brands done)', key='cc_advance'):
        if h.try_advance_shared_week_after_show():
            st.success('Week advanced.')
            st.rerun()
        else:
            st.error('Not all brands completed.')
    if c2.button('Force advance week', key='cc_force'):
        if h.force_advance_shared_week():
            st.success('Forced advance.')
            st.rerun()
    un = st.selectbox('Unlock company show', PLAYABLE, key='cc_unlock_co')
    if c3.button('Unlock company show', key='cc_unlock'):
        h.admin_unlock_company_week(un)
        st.rerun()
    if st.button('Unlock schedule (reset lock only)', key='cc_unlock_cal'):
        st.session_state.calendar_locked = False
        h.save_universe()
        st.rerun()
    if st.button('Save universe backup', key='cc_save'):
        h.save_universe()
        st.success('Saved.')
    if st.button('Logout all (reset session login)', key='cc_logout'):
        st.session_state.logged_in = False
        st.rerun()
