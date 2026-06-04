"""Auto-save status and debounced save helpers for Bound For Glory."""
from datetime import datetime
import streamlit as st


def ensure_autosave_state():
    if 'autosave_status' not in st.session_state:
        st.session_state.autosave_status = 'idle'
    if 'autosave_last_at' not in st.session_state:
        st.session_state.autosave_last_at = ''
    if 'autosave_last_error' not in st.session_state:
        st.session_state.autosave_last_error = ''


def set_autosave_status(status, error=''):
    ensure_autosave_state()
    st.session_state.autosave_status = status
    if status == 'saved':
        st.session_state.autosave_last_at = datetime.now().strftime('%H:%M:%S')
        st.session_state.autosave_last_error = ''
    elif status == 'failed':
        st.session_state.autosave_last_error = error or 'Unknown error'
    elif status == 'saving':
        st.session_state.autosave_last_error = ''


def render_autosave_indicator(key='autosave_ind'):
    ensure_autosave_state()
    status = st.session_state.autosave_status
    at = st.session_state.autosave_last_at
    if status == 'saving':
        st.caption('💾 Saving…')
    elif status == 'saved' and at:
        st.caption(f'✅ Auto-saved at {at}')
    elif status == 'failed':
        st.error(f'Save failed — {st.session_state.autosave_last_error or "retry"}')
    elif at:
        st.caption(f'Last saved {at}')


def autosave_universe(save_fn, company=None):
    """Wrap universe save with visible status."""
    set_autosave_status('saving')
    try:
        save_fn()
        set_autosave_status('saved')
        if company:
            st.session_state.setdefault('company_last_saved', {})[company] = datetime.now().isoformat()
    except Exception as e:
        set_autosave_status('failed', str(e)[:120])
        raise
