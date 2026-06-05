import os, re, json, random, asyncio, subprocess, shutil, hashlib
from pathlib import Path
from datetime import date, datetime
from contextlib import contextmanager
import streamlit as st

st.set_page_config(page_title='BOUND FOR GLORY GM MODE', page_icon='🏆', layout='wide')

PROJECT_ROOT=Path(__file__).resolve().parent

def load_project_env():
 """Load OPENAI_API_KEY (and other vars) from project .env before secrets lookup."""
 env=PROJECT_ROOT/'.env'
 if not env.is_file(): return
 for line in env.read_text(encoding='utf-8').splitlines():
  line=line.strip()
  if not line or line.startswith('#') or '=' not in line: continue
  k,v=line.split('=',1)
  k,v=k.strip(),v.strip().strip('"').strip("'")
  if k and v and not os.environ.get(k): os.environ[k]=v

load_project_env()

import bfg_sessions as mp
try:
 import bfg_supabase as sb
except ModuleNotFoundError:
 class _SupabaseStub:
  @staticmethod
  def supabase_configured(): return False
  @staticmethod
  def load_merged_universe(*_a,**_k): return None
  @staticmethod
  def load_light_session(*_a,**_k): return None
  @staticmethod
  def sync_session_saves(*_a,**_k): return False
 sb=_SupabaseStub()
import bfg_crisis as crisis
import bfg_show_quality as showq
import bfg_twitter_recruit as twrecruit
import bfg_storylines as storylines
import bfg_sponsor_objectives as sponsor_obj
import bfg_autosave as autosave
import bfg_ui_pages as ui_pages

def find_ffmpeg():
 for cand in [shutil.which('ffmpeg'),'/usr/local/bin/ffmpeg','/opt/homebrew/bin/ffmpeg','/usr/bin/ffmpeg']:
  if cand and Path(cand).exists(): return cand
 return None

NXT_UNFILTERED_AUDIO_DIR=PROJECT_ROOT/'data'/'audio'/'nxt_unfiltered'
OPENAI_TTS_VOICE_MAP={'neutral':'nova','warm':'shimmer','deep':'onyx','bright':'nova','energetic':'echo','smooth':'fable','broadcast':'onyx','fan-debate':'echo'}
EDGE_TTS_VOICE_MAP={'neutral':'en-US-JennyNeural','warm':'en-US-AriaNeural','deep':'en-US-GuyNeural','bright':'en-US-AnaNeural','energetic':'en-US-BrandonNeural','smooth':'en-US-RogerNeural','broadcast':'en-US-BrianNeural','fan-debate':'en-US-ChristopherNeural'}
HOST_EDGE_VOICE={'Maya Cruz':'en-US-AriaNeural','Tasha Monroe':'en-US-JennyNeural','Serena Vale':'en-US-SaraNeural','Marcus King':'en-US-GuyNeural','Dante Brooks':'en-US-RogerNeural','Rico Blaze':'en-US-BrianNeural'}

PLAYABLE=['NXT','SmackDown','WCW']

BRAND_UI={
 'NXT':{'glow':'#b026ff','accent':'#d4af37','accent2':'#c0c0c0','silver':'#c0c0c0','bg1':'#020202','bg2':'#08000f','hdr':'#b026ff','border':'#9b7fd6','card1':'#171717','card2':'#07000d','sidebar_bg':'#0a0612','sidebar_card':'#16101f','text':'#f5f0ff','muted':'#d4c8f0','btn_bg':'#14001f','tagline':'NXT Spotlight Studio · Hollywood · Netflix · Oscars'},
 'SmackDown':{'glow':'#1e4fd6','accent':'#e10600','accent2':'#c8d4e8','silver':'#c8d4e8','bg1':'#020814','bg2':'#0a1630','hdr':'#1e4fd6','border':'#5a8fd9','card1':'#0f1a33','card2':'#060d1c','sidebar_bg':'#060d1c','sidebar_card':'#0f1a33','text':'#f4f8ff','muted':'#c8d8f5','btn_bg':'#0a1630','tagline':'Grammys · Music TV · Celebrity Culture'},
 'WCW':{'glow':'#8b0000','accent':'#d4af37','accent2':'#708090','steel':'#708090','silver':'#a8a8b0','bg1':'#050505','bg2':'#1a0505','hdr':'#8b0000','border':'#8a8a8a','card1':'#1a1010','card2':'#0a0606','sidebar_bg':'#0a0606','sidebar_card':'#1a0c0c','text':'#f8f2ee','muted':'#e8d4c8','btn_bg':'#1a0808','tagline':'ESPN · NBA/NFL · Sports Desk'},
}

GLOBAL_UI_CSS="""
* { box-sizing: border-box; }
.bfg-card, .metric-card, .story-card, .tweet-card, .champion-card, .roster-card,
.top-card, .gm-card, .event-box {
 overflow-wrap: anywhere; word-break: break-word; white-space: normal;
 line-height: 1.35; padding: 1rem; margin-bottom: 1rem; max-width: 100%;
}
.stMarkdown, .stText, p, span, div, label {
 overflow-wrap: anywhere; word-break: break-word;
}
pre, code {
 white-space: pre-wrap !important; overflow-x: auto; max-width: 100%;
}
[data-testid="stVerticalBlock"] { gap: 1rem; }
[data-testid="stHorizontalBlock"] { gap: 1rem; }
[data-testid="stVerticalBlockBorderWrapper"] {
 overflow: visible !important; overflow-wrap: anywhere; word-break: break-word;
}
.page-top-bar { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; margin: 0 0 18px; }
.brand-badge {
 display: flex; align-items: center; gap: 14px; padding: 12px 18px; border-radius: 16px;
 background: linear-gradient(135deg, rgba(255,255,255,.06), rgba(0,0,0,.45));
 border: 1px solid var(--bb-border, #555); box-shadow: 0 0 22px var(--bb-glow, #b026ff)44;
 max-width: 100%;
}
.brand-badge-dot { width: 12px; height: 12px; border-radius: 50%; background: var(--bb-accent, #d4af37); box-shadow: 0 0 10px var(--bb-glow); flex-shrink: 0; }
.brand-badge-name { font-size: 1.15rem; font-weight: 900; letter-spacing: .08em; color: #fff; }
.brand-badge-sub { font-size: .82rem; color: var(--bb-muted, #ccc); line-height: 1.35; max-width: 520px; }
.brand-badge-week { font-size: .78rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; color: var(--bb-accent); white-space: nowrap; }
.page-subtitle { font-size: 15px; color: var(--bb-muted, #d4c8f0); margin: -8px 0 16px; line-height: 1.45; opacity: .95; }
.kpi-card, .bfg-kpi {
 background: linear-gradient(145deg, var(--bb-card1, #141414), var(--bb-card2, #0a0012));
 border: 1px solid var(--bb-border, #333); border-radius: 14px;
 padding: 14px 16px; min-height: 88px; margin-bottom: 8px;
 box-shadow: 0 0 12px var(--bb-glow, #b026ff)22;
}
.kpi-label { font-size: 11px; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; color: var(--bb-muted, #aaa); }
.kpi-value { font-size: 26px; font-weight: 900; color: var(--bb-text, #fff); line-height: 1.1; margin-top: 6px; }
.kpi-sub { font-size: 12px; color: var(--bb-muted, #b8b0d0); margin-top: 4px; }
.bfg-content-card { border-radius: 18px; padding: 4px 0; }
div[data-testid="stMetric"] {
 background: linear-gradient(145deg, var(--bb-card1, #141414), var(--bb-card2, #0a0010)) !important;
 border: 1px solid var(--bb-border, #2a2a35) !important; border-radius: 14px !important;
 padding: 10px 12px !important;
}
div[data-testid="stMetric"] label { color: var(--bb-muted, #b8b0d0) !important; font-size: 12px !important; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: var(--bb-text, #fff) !important; font-weight: 900 !important; }
[data-testid="stTabs"] button { font-weight: 700 !important; border-radius: 10px 10px 0 0 !important; }
[data-testid="stExpander"] summary { font-weight: 700 !important; color: var(--bb-text, #eee) !important; }
.scroll-box { max-height: 720px; overflow-y: auto; overflow-x: hidden; padding-right: 4px; }
.game-title-sm { margin-top: 4px !important; }
div[data-testid="stSelectbox"], div[data-baseweb="select"] { overflow: visible !important; }
.tw-stat-row [data-testid="stMetric"] { background: linear-gradient(145deg,var(--bb-card1,#141414),var(--bb-card2,#0a0012)); border: 1px solid var(--bb-border,#333); border-radius: 12px; padding: 8px 10px; }
.tw-preset-bar { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0 12px; }
.tw-feed-scroll { max-height: 72vh; overflow-y: auto; padding-right: 6px; }
.tw-compose-panel { position: sticky; top: 0; }
.tweet-card-compact { border-left: 3px solid #b026ff; padding-left: 12px; margin-bottom: 10px; }
.tweet-handle { color: #9aa0a6; font-size: 0.9rem; }
.tweet-body { font-size: 1.05rem; line-height: 1.45; margin: 8px 0; }
.tweet-eng { color: #888; font-size: 0.82rem; }
.cal-yscroll, .cal-readable-list {
 width: 100%; overflow-x: auto; overflow-y: auto; max-height: 78vh;
 border: 1px solid var(--bb-border, #333); border-radius: 12px; background: var(--bb-card2, #0c0c10);
 margin: 8px 0 16px; padding: 4px 0;
}
.cal-yscroll .cal-schedule-table,
.cal-yscroll .cal-schedule-table td,
.cal-yscroll .cal-schedule-table th,
.cal-readable-card, .cal-readable-card * {
 overflow-wrap: normal !important; word-break: normal !important;
 white-space: normal !important; overflow: visible !important; text-overflow: clip !important;
}
.cal-schedule-table {
 width: max-content; min-width: 100%; border-collapse: collapse; font-size: 14px; table-layout: auto;
}
.cal-schedule-table thead th {
 position: sticky; top: 0; z-index: 2;
 background: linear-gradient(180deg, var(--bb-card1, #1a1a24), var(--bb-card2, #121218));
 color: var(--bb-text, #e8e0ff); font-size: 12px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase;
 padding: 12px 14px; border-bottom: 2px solid var(--bb-border, #444); white-space: nowrap;
}
.cal-schedule-table tbody td {
 padding: 14px 14px; border-bottom: 1px solid var(--bb-border, #2a2a35); color: var(--bb-text, #f5f2ff);
 line-height: 1.5; vertical-align: top; min-width: 72px;
}
.cal-schedule-table tbody tr:hover { background: color-mix(in srgb, var(--bb-glow, #b026ff) 12%, transparent); }
.cal-schedule-table .col-location { color: #b8dcff; min-width: 180px; }
.cal-schedule-table .col-venue { font-weight: 700; min-width: 200px; }
.cal-schedule-table .col-show { min-width: 140px; }
.cal-schedule-table .col-type { min-width: 110px; }
.cal-readable-card {
 margin: 0 10px 10px; padding: 14px 16px; border-radius: 10px;
 background: linear-gradient(145deg, var(--bb-card1, #14141c), var(--bb-card2, #0e0e14));
 border: 1px solid var(--bb-border, #3a3a48);
 font-size: 14px; line-height: 1.55; color: var(--bb-text, #f2f0fa);
}
.cal-readable-card .cal-r-head {
 font-size: 15px; font-weight: 800; margin-bottom: 10px; color: #fff;
 border-bottom: 1px solid #333; padding-bottom: 8px;
}
.cal-readable-card .cal-r-line { margin: 6px 0; }
.cal-readable-card .cal-r-label {
 display: inline-block; min-width: 118px; font-weight: 800; color: #a8a0c8;
 font-size: 11px; letter-spacing: .08em; text-transform: uppercase;
}
.cal-readable-card .cal-r-val { color: #f8f6ff; }
.cal-readable-card .cal-r-loc { color: #9ec8ff; font-weight: 600; }
.cal-readable-card .cal-r-venue { color: #ffe8a8; font-weight: 700; }
.cal-pl-pos { color: #3dd68c; font-weight: 800; }
.cal-pl-neg { color: #ff6b6b; font-weight: 800; }
.cal-status-pill {
 display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 800;
 background: #252530; color: #eee;
}
"""

@contextmanager
def bfg_card(title=None):
 try:
  box=st.container(border=True)
 except TypeError:
  box=st.container()
 with box:
  if title:
   st.subheader(title)
  yield

def html_escape(s):
 return (s or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def render_long_markdown(text,title='Details',expanded=False,key=None):
 if not text:
  return
 body=str(text).strip()
 if len(body) < 280 and '\n' not in body:
  st.markdown(body)
  return
 with st.expander(title,expanded=expanded):
  st.markdown(body)

def render_ai_analysis(text,title='AI Analysis'):
 if not text:
  return
 body=str(text).strip()
 if body.startswith('{') or body.startswith('['):
  with st.expander(title,expanded=False):
   st.warning('Raw data hidden — open Developer Debug if needed.')
  return
 sections=re.split(r'\n(?=#{1,3}\s|\*\*[A-Za-z][^*]+\*\*:?)',body)
 if len(sections)<=1:
  render_long_markdown(body,title,expanded=len(body)>400)
  return
 with st.expander(title,expanded=True):
  for sec in sections[:14]:
   sec=sec.strip()
   if sec:
    st.markdown(sec)

def get_brand_tokens(comp):
 return dict(BRAND_UI.get(comp, BRAND_UI['NXT']))

def set_active_brand(comp):
 """Sync active brand from page tabs / login. Do not touch sidebar_brand — sidebar runs first each run."""
 if comp in PLAYABLE:
  st.session_state.active_brand=comp

def inject_brand_theme(comp=None):
 """Single theme injection for app background, cards, and metrics."""
 comp=comp or st.session_state.get('active_brand','NXT')
 if comp not in PLAYABLE:
  comp='NXT'
 st.markdown(brand_css(comp),unsafe_allow_html=True)

def display_title(name):
 """UI label helper — original universe; no third-party logos in display text."""
 return (name or '').replace('Undisputed WWE Championship','Undisputed Championship').replace('WWE ','').strip()

def brand_css(comp):
 t=get_brand_tokens(comp)
 gr,gg,gb=int(t['glow'][1:3],16),int(t['glow'][3:5],16),int(t['glow'][5:7],16)
 card_grad=f"linear-gradient(145deg,{t['card1']},{t['card2']})"
 return f"""<style>
.stApp{{
 --bb-glow:{t['glow']};--bb-accent:{t['accent']};--bb-accent2:{t.get('accent2',t['silver'])};
 --bb-silver:{t['silver']};--bb-bg1:{t['bg1']};--bb-bg2:{t['bg2']};--bb-hdr:{t['hdr']};
 --bb-border:{t['border']};--bb-card1:{t['card1']};--bb-card2:{t['card2']};
 --bb-muted:{t['muted']};--bb-text:{t['text']};--bb-btn-bg:{t['btn_bg']};
 background:radial-gradient(circle at top left,rgba({gr},{gg},{gb},.28),transparent 38%),linear-gradient(135deg,{t['bg1']},{t['bg2']} 52%,#050508)!important;
 color:{t['text']}!important;
}}
section.main .block-container{{background:transparent}}
.stApp [data-testid="stAppViewContainer"]{{background:transparent}}
.stApp [data-testid="stHeader"]{{background:rgba(0,0,0,.35);border-bottom:1px solid {t['border']}55}}
.stApp [data-testid="stToolbar"]{{background:transparent}}
.block-container{{padding-top:1rem;max-width:100%}}
.game-title{{font-size:58px;font-weight:950;text-align:center;color:#eee;text-shadow:0 0 20px {t['glow']};letter-spacing:4px;line-height:1.05}}
.game-title-sm{{font-size:34px;font-weight:900;text-align:center;color:{t['accent']};letter-spacing:6px;margin-top:4px}}
.game-subtitle{{text-align:center;color:{t['muted']};margin-bottom:20px;font-size:15px}}
.top-card,.gm-card,.event-box,.tweet-card,.kpi-card,.bfg-kpi{{background:{card_grad};border:1px solid {t['border']};border-radius:18px;padding:15px;margin-bottom:12px;box-shadow:0 0 16px {t['glow']}33;overflow-wrap:anywhere}}
.top-card{{text-align:center;min-height:95px}}
.card-title{{color:{t['silver']};font-size:12px;text-transform:uppercase;letter-spacing:.1em}}
.card-number{{font-size:23px;font-weight:900;color:{t['accent']}}}
.section-header{{font-size:30px;font-weight:900;color:#eee;border-left:5px solid {t['hdr']};padding-left:12px;margin:18px 0 12px}}
.overall-badge,.rank-badge,.align-badge{{display:inline-block;padding:4px 9px;border-radius:999px;background:{t['glow']};color:white;font-size:12px;font-weight:800;margin:3px}}
.rank-badge{{background:{t['silver']};color:#080808}}
.align-badge{{background:#333}}
.small-text{{font-size:13px;color:{t['muted']}}}
.page-subtitle{{color:{t['muted']}}}
.scroll-box{{max-height:760px;overflow-y:auto;overflow-x:visible}}
section.main .block-container{{overflow:visible!important;padding-bottom:3rem;max-width:100%}}
section.main .block-container>div{{overflow:visible!important}}
[data-testid="stVerticalBlock"]{{overflow:visible!important}}
[data-testid="stSelectbox"]{{overflow:visible!important}}
div[data-testid="stSelectbox"]>div{{overflow:visible!important}}
div[data-baseweb="popover"]{{max-height:600px!important;overflow-y:auto!important;z-index:999999!important}}
ul[role="listbox"]{{max-height:520px!important;overflow-y:auto!important}}
div[role="listbox"]{{max-height:520px!important;overflow-y:auto!important}}
[data-baseweb="select"]{{z-index:999999!important}}
.clean-selector-wrap{{margin:4px 0 10px}}
div.stButton>button{{width:100%;border-radius:12px;border:1px solid {t['glow']};background:{t['btn_bg']};color:{t['text']};font-weight:800}}
div.stButton>button[kind="primary"],div.stButton>button[data-testid="baseButton-primary"]{{background:linear-gradient(135deg,{t['glow']},{t['accent']})!important;border-color:{t['accent']}!important;color:#fff!important;box-shadow:0 0 18px {t['glow']}66!important}}
.brand-tabs-wrap div.stButton>button{{min-height:44px}}
.brand-tabs-wrap div.stButton>button[kind="primary"]{{box-shadow:0 0 22px {t['glow']}88!important;border:2px solid {t['accent']}!important}}
div[data-testid="stRadio"]>div{{gap:8px;transition:all .2s ease-in-out}}
.brand-tabs-wrap{{transition:all .2s ease-in-out;padding:8px 0 16px;border-bottom:1px solid {t['border']}44;margin-bottom:8px}}
div[data-testid="stRadio"] > label:has(input:checked) {{
 box-shadow:0 0 20px {t['glow']}aa!important;border:2px solid {t['accent']}!important;
 background:linear-gradient(135deg,{t['glow']}44,{t['card2']})!important;transform:scale(1.02);
}}
.roster-card{{background:{card_grad};border:1px solid {t['border']};border-radius:16px;padding:16px;margin-bottom:14px}}
.tag-team-card{{border-left:4px solid {t['accent']};background:linear-gradient(145deg,{t['card1']},{t['card2']})}}
.champion-card{{border:2px solid {t['accent']};background:linear-gradient(160deg,rgba(255,255,255,.06),rgba(0,0,0,.5));padding:22px 20px 16px;margin-bottom:22px;border-radius:20px;box-shadow:0 0 32px {t['glow']}66,0 8px 24px rgba(0,0,0,.55);overflow-wrap:anywhere;position:relative}}
.champion-card::before{{content:'';position:absolute;inset:0;border-radius:20px;pointer-events:none;box-shadow:inset 0 0 48px {t['glow']}22}}
.champion-card .champ-title{{font-size:26px;font-weight:950;margin-bottom:14px;color:{t['accent']};text-shadow:0 0 14px {t['glow']}}}
.champ-name-large{{font-size:28px;font-weight:950;color:#fff;margin:4px 0 8px}}
.champ-ovr-badge{{display:inline-block;padding:6px 14px;border-radius:999px;background:linear-gradient(135deg,{t['glow']},{t['accent']});color:#fff;font-size:15px;font-weight:900;margin:4px 6px 4px 0}}
.champ-prestige-badge{{display:inline-block;padding:5px 12px;border-radius:999px;border:1px solid {t['accent']};color:{t['accent']};font-size:13px;font-weight:800;margin:4px 6px 4px 0;background:rgba(0,0,0,.35)}}
.champ-meta-line{{font-size:14px;color:{t['muted']};margin:5px 0;line-height:1.45}}
.champ-reign-line{{font-size:13px;color:{t['muted']};margin-top:10px;padding-top:10px;border-top:1px solid {t['border']}55}}
.img-slot{{border:2px dashed {t['border']};border-radius:12px;display:flex;align-items:center;justify-content:center;color:{t['muted']};background:#151520;font-size:12px;font-weight:700;padding:8px;min-height:90px}}
.helper-note{{font-size:14px;color:{t['text']};background:rgba(255,255,255,.06);border:1px solid {t['border']};border-radius:12px;padding:10px 12px;margin:8px 0;line-height:1.45}}
div[data-testid="stCaptionContainer"] p{{font-size:14px!important;color:{t['muted']}!important;line-height:1.4!important}}
div[data-testid="stMetric"]{{border-color:{t['border']}66!important}}
.money-meter-wrap{{--mm-glow:{t['glow']};--mm-accent:{t['accent']};--mm-border:{t['border']};border-radius:18px;padding:14px 18px;margin:8px 0 14px;border:2px solid var(--mm-border);background:linear-gradient(145deg,#121218,#06060c);box-shadow:0 0 18px var(--mm-glow)}}
.money-meter-company{{font-size:12px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:var(--mm-accent)}}
.money-meter-bank{{font-size:34px;font-weight:950;line-height:1.1;color:#fff;text-shadow:0 0 12px var(--mm-glow)}}
.money-meter-bank.compact{{font-size:28px}}
.money-meter-change{{font-size:15px;font-weight:800;margin:6px 0}}
.money-meter-stat{{font-size:13px;color:{t['muted']};margin:3px 0}}
.money-meter-flash{{border-radius:12px;padding:10px 14px;margin:8px 0;font-weight:800;border:1px solid var(--mm-border)}}
.money-meter-flash.gain{{background:rgba(46,204,113,.12);color:#2ecc71;border-color:#2ecc71}}
.money-meter-flash.loss{{background:rgba(231,76,60,.12);color:#e74c3c;border-color:#e74c3c}}
.money-ticker-item{{font-size:12px;padding:5px 0;border-bottom:1px solid #2a2a35;line-height:1.35}}
.brand-hub-banner{{border-radius:18px;padding:18px 20px;margin:0 0 16px;border:1px solid {t['border']};background:{card_grad};box-shadow:0 0 24px {t['glow']}44}}
.brand-hub-banner h3{{margin:0 0 8px;color:{t['accent']};font-size:1.35rem}}
{GLOBAL_UI_CSS}
</style>"""

def sidebar_theme(comp):
 t=get_brand_tokens(comp)
 g,m,a,b=t['glow'],t['accent'],t['text'],t['border']
 return f"""<style>
section[data-testid="stSidebar"]{{
 min-width:22.5rem!important;max-width:22.5rem!important;width:22.5rem!important;
 background:linear-gradient(180deg,{t['sidebar_bg']} 0%,#050508 100%)!important;
 border-right:1px solid {b}55!important;
}}
section[data-testid="stSidebar"] > div {{
 padding:1.1rem 1rem 2rem!important;
 background:transparent!important;
}}
section[data-testid="stSidebar"] * {{
 font-size:15px;
}}
section[data-testid="stSidebar"] .sb-header {{
 text-align:center;padding:14px 12px 16px;margin-bottom:14px;
 background:linear-gradient(145deg,{t['sidebar_card']},{t['sidebar_bg']});
 border:1px solid {b};border-radius:16px;
 box-shadow:0 0 20px {g}44;
}}
section[data-testid="stSidebar"] .sb-title {{
 font-size:1.35rem;font-weight:900;letter-spacing:.14em;color:{a};
 line-height:1.15;text-shadow:0 0 12px {g}88;
}}
section[data-testid="stSidebar"] .sb-title-sm {{
 font-size:1.05rem;font-weight:800;letter-spacing:.28em;color:{m};
 margin-top:4px;
}}
section[data-testid="stSidebar"] .sb-sub {{
 font-size:.92rem;color:{m};margin-top:10px;line-height:1.4;opacity:.95;
}}
section[data-testid="stSidebar"] .sb-section {{
 font-size:.78rem;font-weight:800;letter-spacing:.2em;color:{m};
 margin:18px 0 10px;padding-left:4px;
 border-left:3px solid {g};
 padding-left:10px;
}}
section[data-testid="stSidebar"] .sb-company-label {{
 font-size:.82rem;font-weight:700;color:{a};margin:12px 0 8px;letter-spacing:.06em;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] > label {{
 font-size:1rem!important;font-weight:700!important;color:{a}!important;
 padding:10px 12px!important;margin:6px 0!important;
 background:{t['sidebar_card']}!important;border:1px solid {b}66!important;
 border-radius:12px!important;transition:all .2s ease!important;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] > label:hover {{
 border-color:{g}!important;box-shadow:0 0 14px {g}55!important;
 transform:translateY(-1px);
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] > label[data-checked="true"],
section[data-testid="stSidebar"] div[data-testid="stRadio"] > label:has(input:checked) {{
 background:linear-gradient(135deg,{g}33,{t['sidebar_card']})!important;
 border-color:{g}!important;box-shadow:0 0 16px {g}66!important;color:#fff!important;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] > div {{
 gap:10px!important;
}}
section[data-testid="stSidebar"] div.stButton > button {{
 width:100%!important;min-height:46px!important;
 font-size:.98rem!important;font-weight:700!important;
 color:{a}!important;background:{t['sidebar_card']}!important;
 border:1px solid {b}88!important;border-radius:12px!important;
 padding:10px 14px!important;margin:0 0 10px!important;
 transition:all .2s ease!important;letter-spacing:.02em;
}}
section[data-testid="stSidebar"] div.stButton > button:hover {{
 border-color:{g}!important;color:#fff!important;
 box-shadow:0 4px 18px {g}55!important;transform:translateY(-1px);
 background:linear-gradient(135deg,{g}22,{t['sidebar_card']})!important;
}}
section[data-testid="stSidebar"] div.stButton > button[kind="primary"],
section[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-primary"] {{
 background:linear-gradient(135deg,{g},{g}cc)!important;
 border-color:{m}!important;color:#fff!important;
 box-shadow:0 0 20px {g}77!important;font-weight:800!important;
}}
section[data-testid="stSidebar"] div[data-testid="stMarkdown"] p,
section[data-testid="stSidebar"] label p {{
 color:{a}!important;
}}
section[data-testid="stSidebar"] hr {{
 border-color:{b}44;margin:14px 0;
}}
</style>"""

# ---------------- DATA FROM UNIVERSE DRAFT PDF ----------------
COMPANIES={
'NXT':{'titles':['NXT Crown Jewels Title','I.C Title','World Tag Team Champions',"Women's Title","Women's N.A Title"],'sponsors':['Netflix','FOX','FS1/FS2','Comcast','NBC Sports','Mattel','Barbie','DC','Marvel','Hollywood','Olympics','SNL','Good Morning America','Coca-Cola','Monster','Nike','Under Armour','Slim Jim','DraftKings','Bud Light','Lego'],'platforms':['Netflix','FOX','FS1/FS2','Comcast','NBC Sports'],'owner':'Eric Bischoff','gm':'Eric Bischoff','budget_key':'nxt_budget'},
'SmackDown':{'titles':['Undisputed WWE Championship','N.A Championship','World Tag Team Champions',"Women's World Championship","Women's U.S. Championship"],'sponsors':['USA Network','TNT','Paramount Plus','PRIME','New Balance','Snickers','Progressive','Chase','Samsung','Marriott','Sony'],'platforms':['USA Network','TNT','Paramount Plus'],'owner':'Ric Flair','gm':'Ava','budget_key':'sd_budget'},
'WCW':{'titles':['World Heavyweight Championship','United States Title','World Tag Team Champions','WCW Television Title','Cruiserweight Title'],'sponsors':['CBS','ESPN2','ESPN Deportes','Amazon Prime','ESPN+','Adidas','Pepsi','Gatorade','EA Sports',"McDonald's",'Microsoft','Mercedes','Tesla','Funko','Topps','Panini'],'platforms':['CBS','ESPN2','ESPN Deportes','Amazon Prime','ESPN+'],'owner':'Stephanie McMahon / Shane McMahon','gm':'Nick Aldis','budget_key':'wcw_budget'}}
COMPANY_PROFILES={
 'NXT':{'commentary':'Mauro Ranallo, Pat McAfee, Jerry Lawler, R-Truth','ring_announcer':'Samantha Irvin','theme_song':'NXT Immortal Theme','prestige':88,'notes':'','logo_path':'','banner_path':'','owner_pic':''},
 'SmackDown':{'commentary':'Eric Collins, Ernie Johnson, Dick Vitale','ring_announcer':'Mike Walczewski','theme_song':'SmackDown Theme','prestige':85,'notes':'','logo_path':'','banner_path':'','owner_pic':''},
 'WCW':{'commentary':'Michael Cole, Corey Graves, Jim Ross','ring_announcer':'Michael Buffer','theme_song':'WCW Legacy Theme','prestige':90,'notes':'','logo_path':'','banner_path':'','owner_pic':''},
}
WCW_FACTIONS=['The Kliq','Face of Fear','New Era','Team Jordan','Bloodline','British Strong Style','Judgment Day','Latino World Order','Hart Foundation','WCW Originals','Kings of Wrestling']
SD_DIVISIONS={}
for _n in ['Undertaker','Boogeyman','Booker T','Hollywood Hulk Hogan','Kurt Angle','Logan Paul','Randy Orton','Stone Cold Steve Austin 01','Tony D',"La'Quarius Jones"]: SD_DIVISIONS[_n]='Undisputed WWE Championship'
for _n in ['Andre Chase','Batista 08','DDP',"Je'Von Evans",'Macho Man','Sheamus','The Hurricane','Trick Williams','Yokozuna','Kane']: SD_DIVISIONS[_n]='N.A Championship'
for _n in ['Cedric & Ashante','Fraxiom','Noam Dar & Oro Mensah','Steiner Brothers','Street Profits','The Family','La Parka & Mr. Iguana','Hank & Tank','Noam Dar & Rey Fenix']: SD_DIVISIONS[_n]='World Tag Team'
for _n in ['Alexa Bliss','Becky Lynch','Giulia','Liv Morgan','Natalya','Piper Niven','Bayley','Maxxine Dupri','Jacy Jayne','Ava Moreno']: SD_DIVISIONS[_n]="Women's World Championship"
for _n in ['Raquel','Kelani Jordan','Lyra Valkyria','Lola Vice','Tatum Paxley','Wendy Choo','Chelsea Green','Eve Torres','Lash Legend','Tegan Nox','Diana Vegas','Jazmyn Nyx']: SD_DIVISIONS[_n]="Women's U.S. Championship"
for _n in ['KSI','Bad Bunny','Glorilla']: SD_DIVISIONS[_n]='Guest Star'
WCW_DIVISIONS={}
for _n in ['The Rock','Cody Rhodes','Shawn Michaels','Bray Wyatt','Triple H','Drew McIntyre','Bronson Reed','Finn Balor','Jey Uso','Omos','Bret Hart','Jordan Burroughs','Mark Henry','Goldberg']: WCW_DIVISIONS[_n]='World Heavyweight Championship'
for _n in ['Carmelo Hayes','Carlito','Solo Sikoa','Brian Pillman','Rob Van Dam','Bam Bam Bigelow','Mick Foley','Shawn Spears','Faarooq','El Ordinario','Sid Justice','Giovanni Vinci']: WCW_DIVISIONS[_n]='United States Title'
for _n in ['New Day','LWO','Wyatt 6','Hart Foundation','The Outsiders','War Raiders','Dudley Boyz','WCW Originals','Briggs and Jensen','Billy Gunn and Road Dogg','Haku and Tama','Psycho Clown and Pagano','No Quarter Catch Crew']: WCW_DIVISIONS[_n]='World Tag Team'
for _n in ['Eddie Guerrero','Rey Mysterio','Dragon Lee','Tyler Bate','Pete Dunne','X-Pac','JD McDonagh','Dominik Mysterio','Penta','El Hijo de Vikingo','Hector Flores','Octagon Jr']: WCW_DIVISIONS[_n]='Cruiserweight Title'
for _n in ['Matt Cardona','Ethan Page','Lexis King','Andre Walker','Apollo Crews','Ken Shamrock',"D'Lo Brown",'Andrade','Karrion Kross','Ilja Dragunov']: WCW_DIVISIONS[_n]='WCW Television Title'
US_STATES=['Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut','Delaware','Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa','Kansas','Kentucky','Louisiana','Maine','Maryland','Massachusetts','Michigan','Minnesota','Mississippi','Missouri','Montana','Nebraska','Nevada','New Hampshire','New Jersey','New Mexico','New York','North Carolina','North Dakota','Ohio','Oklahoma','Oregon','Pennsylvania','Rhode Island','South Carolina','South Dakota','Tennessee','Texas','Utah','Vermont','Virginia','Washington','West Virginia','Wisconsin','Wyoming','Washington D.C.']
MATCH_TYPE_CATEGORIES={'Regular':['Normal','Tag Team','Triple Threat','Fatal 4-Way','Six-Man Tag','Eight-Man Tag','Mixed Tag'],'Hardcore':['No DQ','Street Fight','Falls Count Anywhere','Tables Match','TLC Match','Last Man Standing','First Blood','I Quit Match'],'Cage / Special':['Steel Cage','Hell in a Cell','WarGames','Elimination Chamber','Anarchy in the Arena','Ultimate X'],'Story / Stakes':['Title Match','Number One Contender','Open Challenge','Loser Leaves Brand','Career vs Career','Mask vs Hair','Contract Signing Segment','Main Event Grudge Match','Squash Match'],'Tournament':['Tournament Match','King of the Ring','Queen of the Hill','World Cup Match','Beat the Clock','Gauntlet Match'],'Cinematic':['Backstage Brawl','Parking Lot Brawl','Cinematic Match']}
ALL_MATCH_TYPES=[m for cats in MATCH_TYPE_CATEGORIES.values() for m in cats]
MATCH_EFFECTS={
 'Normal':{'rating':0,'fan':0,'injury':1,'stamina':2,'cost':0,'viral':0},
 'Anarchy in the Arena':{'rating':1.2,'fan':1.5,'injury':3,'stamina':4,'cost':1.4,'viral':1.3},
 'Ultimate X':{'rating':.9,'fan':1.4,'injury':2.5,'stamina':3.5,'cost':1.1,'viral':1.8},
 'Steel Cage':{'rating':.6,'fan':.8,'injury':2,'stamina':3,'cost':.8,'viral':.5},
 'Hell in a Cell':{'rating':.8,'fan':1.0,'injury':2.5,'stamina':3.5,'cost':1.0,'viral':.7},
 'Tables Match':{'rating':.5,'fan':.7,'injury':2,'stamina':2.5,'cost':.6,'viral':.6},
 'Title Match':{'rating':.7,'fan':1.1,'injury':1.5,'stamina':2,'cost':.3,'viral':.8},
 'Squash Match':{'rating':-.2,'fan':-.1,'injury':.5,'stamina':1,'cost':-.3,'viral':.2},
}
DEFAULT_MATCH_EFFECT={'rating':0,'fan':0,'injury':1,'stamina':2,'cost':0,'viral':0}
PPVS=[('May','NXT Bound For Glory','NXT'),('June','Heatwave','SmackDown'),('July','American Bash','WCW'),('August','NXT Redemption','NXT'),('September','No Mercy','SmackDown'),('October','Halloween Havoc','WCW'),('November','Worlds Collide & War Games','NXT + All Brands'),('December','Bad Blood','SmackDown'),('January','World War 3','WCW'),('February','NXT Sacrifice','NXT'),('March','WrestleMania','SmackDown + All Brands'),('April','Starrcade','WCW')]

HOMETOWNS={
 'CM Punk':'Chicago, Illinois','Roman Reigns':'Pensacola, Florida','Seth Rollins':'Davenport, Iowa','Chad Gable':'Minneapolis, Minnesota','Rhea Ripley':'Adelaide, Australia',
 'Shinsuke Nakamura':'Kyoto, Japan','Gunther':'Vienna, Austria','John Cena':'West Newbury, Massachusetts','Kevin Owens':'Marieville, Quebec','Sami Zayn':'Montreal, Quebec',
 'Jacob Fatu':'Samoan Dynasty','Christian Rose':'Hollywood, California','Brock Lesnar':'Webster, South Dakota','Jeff Hardy':'Cameron, North Carolina','Matt Hardy':'Cameron, North Carolina',
 'Undertaker':'Death Valley','Logan Paul':'Cleveland, Ohio','Randy Orton':'St. Louis, Missouri','Batista 08':'Washington, D.C.','Becky Lynch':'Dublin, Ireland','Liv Morgan':'Elmwood Park, New Jersey',
 'Stone Cold Steve Austin 01':'Victoria, Texas','Booker T':'Houston, Texas','Hollywood Hulk Hogan':'Augusta, Georgia','Kurt Angle':'Pittsburgh, Pennsylvania','Kane':'Corona, California',
 'Alexa Bliss':'North Hollywood, California','Giulia':'Tokyo, Japan','Bayley':'San Jose, California','Raquel':'La Barca, Mexico','Natalya':'Calgary, Alberta',
 'Montez Ford':'Chicago, Illinois','Angelo Dawkins':'Cincinnati, Ohio','Scott Steiner':'Detroit, Michigan','Rick Steiner':'Detroit, Michigan',
 'The Rock':'Miami, Florida','Triple H':'Greenwich, Connecticut','Shawn Michaels':'San Antonio, Texas','Eddie Guerrero':'El Paso, Texas','Rey Mysterio':'San Diego, California',
 'Goldberg':'Atlanta, Georgia','Kevin Nash':'Detroit, Michigan','Scott Hall':'Miami, Florida','Cody Rhodes':'Atlanta, Georgia','Bret Hart':'Calgary, Alberta',
 'Drew McIntyre':'Ayr, Scotland','Finn Balor':'Bray, Ireland','Jey Uso':'San Francisco, California','Bianca Belair':'Knoxville, Tennessee',
 'LA Knight':'New Jersey','Damian Priest':'New York City','Abyss':'Atlanta, Georgia','Trish Stratus':'Toronto, Canada',
 'Jade Cargill':'Vidalia, Georgia','Dragon Lee':'Mexico City, Mexico','Tyler Bate':'Derby, England','Pete Dunne':'Liverpool, England',
 'Charlotte Flair':'Charlotte, North Carolina','Iyo Sky':'Tokyo, Japan','Asuka':'Osaka, Japan','Gunther':'Vienna, Austria',
 'Raven':'Atlanta, Georgia','Lani Rose':'Los Angeles, California','Jacob Fatu':'Samoan Dynasty','AJ Styles':'Gainesville, Georgia',
 'Miro':'Kavala, Greece','Oba Femi':'Nigeria','Ricky Saints':'Unknown','Austin Theory':'McDonough, Georgia','Santos Escobar':'Mexico City, Mexico',
 'The Miz':'Parma, Ohio','Malakai Black':'Auckland, New Zealand','Trick Williams': 'Columbia, South Carolina',"Je'Von Evans":'Unknown',
 'Fraxiom':'England','Apollo Crews':'Stone Mountain, Georgia','Andre Walker':'Unknown','Ethan Page':'St. John, New Brunswick',
 'Matt Cardona':'Massapequa, New York','Lexis King':'Unknown','Penta':'Mexico City, Mexico','El Hijo de Vikingo':'Mexico',
 'Solo Sikoa':'Sacramento, California','Carmelo Hayes':'Chicago, Illinois','Carlito':'New York City','Bronson Reed':'Brisbane, Australia',
 'Mark Henry':'Silsbee, Texas','Jordan Burroughs':'Sandy, Utah','Brian Pillman':'Cincinnati, Ohio','Rob Van Dam':'Battle Creek, Michigan',
 'Mick Foley':'Long Island, New York','Bam Bam Bigelow':'Asbury Park, New Jersey','Omos':'Lagos, Nigeria','Bray Wyatt':'Scottsdale, Arizona',
 'Nick Aldis':'Norfolk, England','Andrade':'Monterrey, Mexico','Karrion Kross':'Sacramento, California',"D'Lo Brown":'Decatur, Georgia',
 'Ken Shamrock':'Macon, Georgia','X-Pac':'San Diego, California','Boogeyman':'Unknown',"La'Quarius Jones":'Unknown','Tony D':'Unknown',
 'Macho Man':'Columbus, Ohio','Sheamus':'Dublin, Ireland','The Hurricane':'Omaha, Nebraska','Yokozuna':'San Francisco, California',
 'Hollywood Hulk Hogan':'Augusta, Georgia','DDP':'New Jersey','Andre Chase':'Unknown','Tiffany Stratton':'Zephyrhills, Florida',
 'Stephanie Vaquer':'Santiago, Chile','Brie Bella':'Phoenix, Arizona','Nia Jax':'Honolulu, Hawaii','Candice LeRae':'Ponoma, California',
 'Kairi Sane':'Osaka, Japan','Lita':'Atlanta, Georgia','Sol Ruca':'Phoenix, Arizona','Mariah May':'Unknown','Roxanne Perez':'Newark, New Jersey',
 'Nikki Bella':'Phoenix, Arizona','Naomi':'Orlando, Florida','Thea Hail':'Unknown','Nikkita Lyons':'Unknown','Kelly Kelly':'Kent, Ohio',
 'Jordynne Grace':'Unknown','Alba Fyre':'Unknown','Fallon Henley':'Unknown','Glorilla':'Memphis, Tennessee','Bad Bunny':'Puerto Rico',
 'KSI':'London, England','Chelsea Green':'Las Vegas, Nevada','Lola Vice':'Unknown','Lyra Valkyria':'Unknown','Kelani Jordan':'Unknown',
}
TAG_TEAM_MEMBERS={
 'The Hardys':[{'name':'Jeff Hardy','overall':93,'alignment':'F','from':'Cameron, North Carolina','status':'Active'},{'name':'Matt Hardy','overall':90,'alignment':'F','from':'Cameron, North Carolina','status':'Active'}],
 'Street Profits':[{'name':'Montez Ford','overall':80,'alignment':'F','from':'Chicago, Illinois','status':'Active'},{'name':'Angelo Dawkins','overall':78,'alignment':'F','from':'Cincinnati, Ohio','status':'Active'}],
 'Steiner Brothers':[{'name':'Scott Steiner','overall':88,'alignment':'H','from':'Detroit, Michigan','status':'Active'},{'name':'Rick Steiner','overall':85,'alignment':'H','from':'Detroit, Michigan','status':'Active'}],
 'The Outsiders':[{'name':'Kevin Nash','overall':90,'alignment':'H','from':'Detroit, Michigan','status':'Active'},{'name':'Scott Hall','overall':89,'alignment':'H','from':'Miami, Florida','status':'Active'}],
 'Cedric & Ashante':[{'name':'Cedric Alexander','overall':79,'alignment':'F','from':'Pineville, Louisiana','status':'Active'},{'name':'Ashante Adonis','overall':76,'alignment':'F','from':'Ottawa, Canada','status':'Active'}],
 'Noam Dar & Oro Mensah':[{'name':'Noam Dar','overall':80,'alignment':'N','from':'Tel Aviv, Israel','status':'Active'},{'name':'Oro Mensah','overall':78,'alignment':'N','from':'London, England','status':'Active'}],
 'Noam Dar & Rey Fenix':[{'name':'Noam Dar','overall':80,'alignment':'N','from':'Tel Aviv, Israel','status':'Active'},{'name':'Rey Fenix','overall':82,'alignment':'F','from':'Mexico City, Mexico','status':'Active'}],
 'La Parka & Mr. Iguana':[{'name':'La Parka','overall':84,'alignment':'N','from':'Monterrey, Mexico','status':'Active'},{'name':'Mr. Iguana','overall':80,'alignment':'N','from':'Mexico','status':'Active'}],
 'Hank & Tank':[{'name':'Hank','overall':83,'alignment':'N','from':'USA','status':'Active'},{'name':'Tank','overall':82,'alignment':'N','from':'USA','status':'Active'}],
 'The Family':[{'name':'Talla Tonga','overall':78,'alignment':'H','from':'Tonga','status':'Active'},{'name':'Hikuleo','overall':79,'alignment':'H','from':'Tonga','status':'Active'}],
 'Fraxiom':[{'name':'Axiom','overall':83,'alignment':'F','from':'England','status':'Active'},{'name':'Frazer','overall':83,'alignment':'F','from':'England','status':'Active'}],
 'Domlishes':[{'name':'Dominik Mysterio','overall':92,'alignment':'H','from':'San Diego, California','status':'Active'},{'name':'Rhea Ripley','overall':92,'alignment':'H','from':'Adelaide, Australia','status':'Active'}],
 'American Made':[{'name':'Curtis Thompson','overall':90,'alignment':'F','from':'USA','status':'Active'},{'name':'Hank Walker','overall':90,'alignment':'F','from':'USA','status':'Active'}],
 'Pretty Deadly':[{'name':'Elton Prince','overall':88,'alignment':'H','from':'England','status':'Active'},{'name':'Kit Wilson','overall':88,'alignment':'H','from':'England','status':'Active'}],
 'New Day':[{'name':'Kofi Kingston','overall':88,'alignment':'F','from':'Ghana','status':'Active'},{'name':'Xavier Woods','overall':86,'alignment':'F','from':'Decatur, Georgia','status':'Active'}],
 'Dudley Boyz':[{'name':'Bubba Ray Dudley','overall':88,'alignment':'H','from':'Boston, Massachusetts','status':'Active'},{'name':'D-Von Dudley','overall':86,'alignment':'H','from':'Boston, Massachusetts','status':'Active'}],
 'War Raiders':[{'name':'Erik','overall':85,'alignment':'F','from':'Moscow, Idaho','status':'Active'},{'name':'Ivar','overall':84,'alignment':'F','from':'Sweden','status':'Active'}],
 'DIY':[{'name':'Johnny Gargano','overall':91,'alignment':'F','from':'Lakewood, Ohio','status':'Active'},{'name':'Tommaso Ciampa','overall':90,'alignment':'H','from':'Boston, Massachusetts','status':'Active'}],
 'MCMG':[{'name':'Alex Shelley','overall':89,'alignment':'F','from':'Detroit, Michigan','status':'Active'},{'name':'Chris Sabin','overall':88,'alignment':'F','from':'Detroit, Michigan','status':'Active'}],
 'Alpha Academy':[{'name':'Chad Gable','overall':92,'alignment':'F','from':'Minneapolis, Minnesota','status':'Active'},{'name':'Otis','overall':86,'alignment':'F','from':'Denver, Colorado','status':'Active'}],
 'Hart Foundation':[{'name':'Bret Hart','overall':92,'alignment':'F','from':'Calgary, Alberta','status':'Active'},{'name':'Owen Hart','overall':90,'alignment':'F','from':'Calgary, Alberta','status':'Active'}],
 'LWO':[{'name':'Rey Mysterio','overall':90,'alignment':'F','from':'San Diego, California','status':'Active'},{'name':'Dragon Lee','overall':84,'alignment':'F','from':'Mexico','status':'Active'}],
 'Wyatt 6':[{'name':'Bray Wyatt','overall':93,'alignment':'N','from':'Georgia','status':'Active'},{'name':'Eragon Rowan','overall':88,'alignment':'N','from':'USA','status':'Active'}],
 'WCW Originals':[{'name':'Sting','overall':90,'alignment':'F','from':'Venice Beach, California','status':'Active'},{'name':'Lex Luger','overall':86,'alignment':'F','from':'Atlanta, Georgia','status':'Active'}],
 'Briggs and Jensen':[{'name':'Charlie Briggs','overall':78,'alignment':'H','from':'USA','status':'Active'},{'name':'Ivar Jensen','overall':78,'alignment':'H','from':'Denmark','status':'Active'}],
 'Billy Gunn and Road Dogg':[{'name':'Billy Gunn','overall':84,'alignment':'H','from':'Phoenix, Arizona','status':'Active'},{'name':'Road Dogg','overall':83,'alignment':'H','from':'Marietta, Georgia','status':'Active'}],
 'Haku and Tama':[{'name':'Haku','overall':84,'alignment':'F','from':'Tonga','status':'Active'},{'name':'Tama Tonga','overall':84,'alignment':'H','from':'Tonga','status':'Active'}],
 'Psycho Clown and Pagano':[{'name':'Psycho Clown','overall':84,'alignment':'H','from':'Mexico City, Mexico','status':'Active'},{'name':'Pagano','overall':84,'alignment':'H','from':'Mexico','status':'Active'}],
 'No Quarter Catch Crew':[{'name':'Charlie Dempsey','overall':83,'alignment':'H','from':'England','status':'Active'},{'name':'Damon Kemp','overall':83,'alignment':'H','from':'USA','status':'Active'}],
}
COMPANY_FACTIONS={'NXT':['DIY','Pretty Deadly','Alpha Academy'],'SmackDown':['The Family','Fraxiom'],'WCW':WCW_FACTIONS}
WOMEN_DIVISION_KW=('Women',"Women's")
STARTING_BUDGET=150000000
DEFAULT_SINGLES_DIV={'NXT':'I.C Title','SmackDown':'N.A Championship','WCW':'United States Title'}
COMPANY_LOGISTICS_RULES={
 'NXT':{'hotel_sponsor':None,'hotel_coverage':0,'transport_sponsor':None,'transport_coverage':0,'hotel_note':'NXT pays full hotel costs','transport_note':'NXT pays full transportation','merch_partners':['Mattel','Barbie','DC','Marvel','Netflix','Hollywood']},
 'SmackDown':{'hotel_sponsor':'Marriott','hotel_coverage':1.0,'transport_sponsor':None,'transport_coverage':0,'hotel_note':'Marriott covered hotel costs','transport_note':'SmackDown pays transportation','merch_partners':['PRIME','New Balance','Sony','USA Network']},
 'WCW':{'hotel_sponsor':None,'hotel_coverage':0,'transport_sponsor':'Tesla/Mercedes','transport_coverage':1.0,'hotel_note':'WCW pays hotel unless sponsor covers event','transport_note':'Tesla/Mercedes covered transportation','merch_partners':['ESPN','CBS','Adidas','Pepsi','EA Sports']},
}
LOGISTICS_BASE={'hotel':420000,'transport':300000,'production':450000,'medical':100000,'catering':120000,'insurance':80000,'advertising_weekly':75000,'advertising_ple':150000,'sponsor_activation_weekly':40000,'sponsor_activation_ple':100000,'media_production':50000}
TICKET_PRICES={'Weekly Show':65,'TV Special':85,'Go-Home Show':90,'Go-home before PLE':90,'Fallout Show':75,'PLE':120,'Stadium Show':140,'International Tour':100,'Tournament':90,'Crossover Event':110,'Homecoming Show':80}
VIEWERSHIP_MIN=500_000
VIEWERSHIP_MAX=5_000_000
FILMING_TEMPLATES={
 'Netflix series cameo':{'partner':'Netflix','type':'show','length':'1 week','revenue':1500000,'popularity':5,'stamina':-5,'miss_risk':0.15,'tension':0.1},
 'Marvel/DC cameo':{'partner':'Marvel/DC','type':'cameo','length':'2 weeks','revenue':3000000,'popularity':8,'stamina':-8,'miss_risk':0.25,'tension':0.2},
 'Hollywood movie role':{'partner':'Hollywood','type':'movie','length':'1 month','revenue':5000000,'popularity':10,'stamina':-12,'miss_risk':0.35,'tension':0.35},
 'SNL appearance':{'partner':'SNL','type':'show','length':'1 week','revenue':750000,'popularity':4,'stamina':-3,'miss_risk':0.1,'tension':0.15},
 'Good Morning America':{'partner':'Good Morning America','type':'press','length':'1 week','revenue':500000,'popularity':3,'stamina':-2,'miss_risk':0.05,'tension':0.05},
 'Olympics appearance':{'partner':'Olympics','type':'appearance','length':'1 week','revenue':900000,'popularity':6,'stamina':-4,'miss_risk':0.08,'tension':0.1},
 'ESPN sports crossover':{'partner':'ESPN','type':'appearance','length':'1 week','revenue':850000,'popularity':5,'stamina':-3,'miss_risk':0.1,'tension':0.08},
 'Grammys red carpet':{'partner':'Grammys','type':'red carpet','length':'1 week','revenue':650000,'popularity':5,'stamina':-3,'miss_risk':0.08,'tension':0.12},
}

def W(n,c,d,o=80,a='N',s=500000):
 loc=HOMETOWNS.get(n,'') or 'Unknown'
 sy=2026
 return {'name':n,'company':c,'division':d,'overall':int(o),'alignment':a,'salary':int(s),'status':'Active','popularity':min(100,int(o)),'momentum':55,'morale':70,'stamina':85,'controversy_risk':20,'fan_support':min(100,int(o)),'locker_room_reputation':55,'sponsor_trust':60,'debut_status':'Debuted','debut_week':None,'debut_show':'','debut_company':c,'debut_segment':'','debut_type':'','debut_rating':0,'last_booked_week':None,'weeks_since_debut':0,'weeks_not_used_after_debut':0,'from_location':loc,'hometown':loc,'contract_length_years':3,'contract_start_year':sy,'contract_start_week':0,'contract_expiration_year':sy+3,'contract_expiration_week':0,'contract_weeks_remaining':156,'contract_weeks_left':156,'contract_years_remaining':3,'contract_status':'Active','renewal_status':'Not Started','salary_demand':int(s*1.1),'contract_demand':'Standard deal','contract_morale_impact':0,'free_agency_eligible':False,'previous_company':'','fa_reason':'','negotiation_offer_salary':0,'negotiation_offer_years':0,'negotiation_signing_bonus':0,'renewal_chance':70,'wins':0,'losses':0,'draws':0,'singles_wins':0,'singles_losses':0,'tag_wins':0,'tag_losses':0,'title_wins':0,'title_losses':0,'streak':'','last_result':'None','power_score':0,'rank':None,'last_rank':None,'rank_reason':'Initial ranking','image_path':'','rivalry_heat':0,'twitter_buzz':0,'injury':False,'ple_boost':0,'fan_investment':50,'last_show_boost':0,'story_grade_boost':0,'tag_team_affiliation':'','political_outspoken':random.random()<.12}

ROSTER=[]
for x in [('CM Punk',94,'N',3000000),('Shinsuke Nakamura',94,'F',2000000),('Seth Rollins',95,'N',5000000),('Gunther',94,'H',2000000),('Roman Reigns',96,'N',5000000),('AJ Styles',94,'F',2000000),('John Cena',94,'F',5000000),('Raven',97,'N',3000000),('Kevin Owens',93,'N',2000000),('Sami Zayn',92,'F',2000000),('Jacob Fatu',92,'N',950000),('Christian Rose',96,'N',7000000),('Brock Lesnar',95,'H',3000000)]: ROSTER.append(W(x[0],'NXT','NXT Crown Jewels Title',x[1],x[2],x[3]))
for x in [('The Miz',88,'H'),('Austin Theory',90,'N'),('Santos Escobar',87,'H'),('Abyss',93,'H'),('Damian Priest',90,'H'),('Chad Gable',92,'F'),('LA Knight',92,'N'),('Ricky Saints',89,'F'),('Oba Femi',92,'N'),('Miro',92,'N'),('Jeff Hardy',93,'F'),('Malakai Black',91,'H')]: ROSTER.append(W(x[0],'NXT','I.C Title',x[1],x[2],800000))
for x in [('The Hardys',93,'F'),('Domlishes',92,'H'),('American Made',90,'F'),('DIY',91,'F'),('Pretty Deadly',88,'H'),('MCMG',89,'F'),('Alpha Academy',86,'F')]: ROSTER.append(W(x[0],'NXT','World Tag Team',x[1],x[2],900000))
for x in [('Lani Rose',90,'N',3500000),('Iyo Sky',88,'F',900000),('Asuka',92,'N',800000),('Tiffany Stratton',88,'H',2000000),('Trish Stratus',89,'F',800000),('Charlotte Flair',90,'N',1000000),('Bianca Belair',90,'H',3000000),('Rhea Ripley',92,'F',1000000),('Stephanie Vaquer',87,'F',800000),('Brie Bella',88,'F',600000),('Nia Jax',89,'H',650000),('Candice LeRae',85,'F',300000),('Kairi Sane',87,'F',850000),('Lita',88,'N',800000),('Jade Cargill',86,'H',2000000),('Sol Ruca',84,'F',750000),('Mariah May',91,'N',450000),('Roxanne Perez',89,'H',900000),('Nikki Bella',88,'H',750000),('Naomi',85,'F',850000),('Thea Hail',82,'F',200000),('Nikkita Lyons',83,'N',400000),('Kelly Kelly',86,'F',400000),('Jordynne Grace',90,'F',800000),('Alba Fyre',86,'H',400000),('Fallon Henley',85,'F',200000)]: ROSTER.append(W(x[0],'NXT','Women',x[1],x[2],x[3]))
for x in [('Undertaker',97,'F',10000000),('Boogeyman',89,'H',4000000),('Booker T',90,'F',5500000),('Hollywood Hulk Hogan',93,'N',7000000),('Kurt Angle',89,'H',5000000),('Logan Paul',90,'H',5000000),('Randy Orton',92,'N',7000000),('Stone Cold Steve Austin 01',97,'N',10000000),('Tony D',84,'H',1000000),("La'Quarius Jones",95,'F',3000000),('Andre Chase',80,'F',400000),('Batista 08',91,'F',6500000),('DDP',91,'H',5500000),("Je'Von Evans",83,'F',1000000),('Macho Man',89,'H',3000000),('Sheamus',88,'F',2700000),('The Hurricane',80,'N',500000),('Trick Williams',84,'F',1000000),('Yokozuna',87,'H',2500000),('Kane',87,'N',4000000),('Cedric & Ashante',77,'F',300000),('Fraxiom',83,'F',700000),('Steiner Brothers',85,'H',1000000),('Street Profits',79,'F',800000),('Alexa Bliss',89,'F',3500000),('Becky Lynch',94,'F',7500000),('Giulia',90,'F',3000000),('Liv Morgan',92,'H',5500000),('Natalya',85,'H',1500000),('Bayley',90,'N',3500000),('Raquel',88,'N',2500000),('Kelani Jordan',86,'F',2000000),('Lyra Valkyria',86,'F',2700000),('Lola Vice',84,'F',1500000),('Chelsea Green',87,'H',3500000),('KSI',85,'N',900000),('Bad Bunny',82,'F',1000000),('Glorilla',85,'F',600000)]: ROSTER.append(W(x[0],'SmackDown','Roster',x[1],x[2],x[3]))
for x in [('The Rock',96,'F',5000000),('Cody Rhodes',94,'F',5000000),('Shawn Michaels',94,'H',1500000),('Bray Wyatt',93,'N',900000),('Triple H',95,'H',5000000),('Drew McIntyre',91,'F',1500000),('Bronson Reed',87,'H',700000),('Finn Balor',90,'H',800000),('Jey Uso',88,'F',600000),('Omos',86,'H',700000),('Bret Hart',92,'F',1000000),('Jordan Burroughs',88,'F',2000000),('Mark Henry',88,'H',750000),('Goldberg',93,'F',1000000),('Carmelo Hayes',86,'N',700000),('Carlito',84,'H',500000),('Solo Sikoa',88,'H',800000),('Brian Pillman',85,'H',550000),('Rob Van Dam',88,'F',750000),('Bam Bam Bigelow',84,'F',450000),('Mick Foley',88,'F',800000),('Eddie Guerrero',90,'H',1500000),('Rey Mysterio',90,'F',2500000),('Dragon Lee',84,'F',500000),('Tyler Bate',85,'F',400000),('Pete Dunne',86,'F',500000),('X-Pac',84,'H',500000),('Penta',88,'H',700000),('El Hijo de Vikingo',88,'H',700000),('Matt Cardona',85,'F',400000),('Ethan Page',84,'H',500000),('Lexis King',82,'H',400000),('Andre Walker',87,'H',800000),('Apollo Crews',84,'F',300000),('Ken Shamrock',86,'F',650000),("D'Lo Brown",82,'F',500000),('Andrade',86,'F',700000), ('Karrion Kross',85,'H',600000)]: ROSTER.append(W(x[0],'WCW','Roster',x[1],x[2],x[3]))
_ROSTER_NOT_DEBUTED={'Dragon Lee','Tyler Bate','Pete Dunne','Lexis King','Trick Williams',"Je'Von Evans",'Fraxiom','Apollo Crews','Andre Walker','Ethan Page','Matt Cardona'}
for w in ROSTER:
 if w['name'] in _ROSTER_NOT_DEBUTED: w['debut_status']='Not Debuted'; w['debut_week']=None

CHAMPIONS={'NXT':{'NXT Crown Jewels Title':'Place Holder','I.C Title':'Place Holder','World Tag Team Champions':'Place Holder',"Women's Title":'Place Holder',"Women's N.A Title":'Place Holder'},'SmackDown':{'Undisputed WWE Championship':'Undertaker','N.A Championship':'TBD - Tournament','World Tag Team Champions':'TBD - Tournament',"Women's World Championship":'TBD - Tournament',"Women's U.S. Championship":'TBD - Title Match'},'WCW':{'World Heavyweight Championship':'Triple H','United States Title':'Solo Sikoa','World Tag Team Champions':'The Outsiders','WCW Television Title':'Shawn Michaels','Cruiserweight Title':'Eddie Guerrero'}}
CHARACTER_BIBLE={'Christian Rose':{'archetype':'Hollywood franchise final boss with ruthless Triple H power and Rock-level star aura.','promo':'Dangerous, arrogant, corporate, cinematic, personal, manipulative.','should_do':['control','legacy','Hollywood','power','main event','franchise','manipulate'],'should_not':['beg','act humble','look weak'],'notes':'Your universe version.'},'Lani Rose':{'archetype':'Fearless top woman with fire and fight.','promo':'Fiery, defiant, emotional, sharp.','should_do':['fight','challenge','prove','champion'],'should_not':['sound timid'],'notes':''},'Raven':{'archetype':'Dark psychological villain.','promo':'Cryptic, poetic, dark.','should_do':['mind games','pain','darkness','fear'],'should_not':['act goofy'],'notes':''},'CM Punk':{'archetype':'Loose cannon truth teller.','promo':'Sharp, real, confrontational.','should_do':['truth','pipebomb','call out','hypocrisy'],'should_not':['sound corporate'],'notes':''}}
ATTRACTIONS=[{'name':'Massage / Spa Day','cost':350000,'morale_gain':10,'stamina_gain':6,'popularity_gain':1,'momentum_gain':2,'sponsor_impact':0,'risk_impact':-2,'description':'Recovery after travel, injuries, or locker room tension.'},{'name':'Holiday Time With Family / Vacation','cost':500000,'morale_gain':15,'stamina_gain':10,'popularity_gain':0,'momentum_gain':1,'sponsor_impact':1,'risk_impact':-3,'description':'Family time and burnout recovery.'},{'name':'Media Tour','cost':650000,'morale_gain':0,'stamina_gain':-3,'popularity_gain':6,'momentum_gain':2,'sponsor_impact':3,'risk_impact':1,'description':'Popularity and sponsor boost.'},{'name':'Social Media Campaign','cost':250000,'morale_gain':1,'stamina_gain':0,'popularity_gain':5,'momentum_gain':4,'sponsor_impact':1,'risk_impact':2,'description':'Online buzz and viral chance.'},{'name':'Celebrity Crossover','cost':1500000,'morale_gain':1,'stamina_gain':-2,'popularity_gain':10,'momentum_gain':8,'sponsor_impact':5,'risk_impact':2,'description':'Huge media boost.'},{'name':'Community / Charity Appearance','cost':300000,'morale_gain':5,'stamina_gain':0,'popularity_gain':3,'momentum_gain':1,'sponsor_impact':4,'risk_impact':-1,'description':'Public image and sponsor confidence.'}]
VENUES=[{'country':'United States','region':'New York','city':'New York City','venue':'Madison Square Garden','capacity':19812,'type':'Arena','rental_cost':900000,'security_cost':250000,'travel_multiplier':1.25,'ticket_multiplier':1.6,'market_bonus':600000,'prestige':10},{'country':'United States','region':'New York','city':'Brooklyn','venue':'Barclays Center','capacity':17732,'type':'Arena','rental_cost':700000,'security_cost':210000,'travel_multiplier':1.18,'ticket_multiplier':1.45,'market_bonus':450000,'prestige':9},{'country':'United States','region':'New Jersey','city':'East Rutherford','venue':'MetLife Stadium','capacity':82500,'type':'Stadium','rental_cost':3000000,'security_cost':900000,'travel_multiplier':1.35,'ticket_multiplier':1.85,'market_bonus':800000,'prestige':10},{'country':'United States','region':'California','city':'Los Angeles','venue':'Crypto.com Arena','capacity':20000,'type':'Arena','rental_cost':850000,'security_cost':240000,'travel_multiplier':1.30,'ticket_multiplier':1.55,'market_bonus':550000,'prestige':9},{'country':'United States','region':'California','city':'Inglewood','venue':'SoFi Stadium','capacity':70240,'type':'Stadium','rental_cost':3500000,'security_cost':950000,'travel_multiplier':1.45,'ticket_multiplier':1.95,'market_bonus':900000,'prestige':10},{'country':'United States','region':'Illinois','city':'Chicago','venue':'United Center','capacity':20917,'type':'Arena','rental_cost':750000,'security_cost':230000,'travel_multiplier':1.22,'ticket_multiplier':1.45,'market_bonus':500000,'prestige':9},{'country':'United States','region':'Texas','city':'Arlington','venue':'AT&T Stadium','capacity':80000,'type':'Stadium','rental_cost':3200000,'security_cost':900000,'travel_multiplier':1.40,'ticket_multiplier':1.80,'market_bonus':700000,'prestige':10},{'country':'United Kingdom','region':'England','city':'London','venue':'Wembley Stadium','capacity':90000,'type':'Stadium','rental_cost':3800000,'security_cost':1100000,'travel_multiplier':1.75,'ticket_multiplier':2.00,'market_bonus':1000000,'prestige':10},{'country':'United Kingdom','region':'England','city':'London','venue':'O2 Arena','capacity':20000,'type':'Arena','rental_cost':900000,'security_cost':260000,'travel_multiplier':1.55,'ticket_multiplier':1.60,'market_bonus':650000,'prestige':9},{'country':'Canada','region':'Ontario','city':'Toronto','venue':'Scotiabank Arena','capacity':19800,'type':'Arena','rental_cost':750000,'security_cost':230000,'travel_multiplier':1.35,'ticket_multiplier':1.45,'market_bonus':450000,'prestige':9},{'country':'Japan','region':'Tokyo','city':'Tokyo','venue':'Tokyo Dome','capacity':55000,'type':'Stadium','rental_cost':2500000,'security_cost':650000,'travel_multiplier':1.90,'ticket_multiplier':1.80,'market_bonus':850000,'prestige':10},{'country':'Mexico','region':'Mexico City','city':'Mexico City','venue':'Arena México','capacity':16500,'type':'Arena','rental_cost':500000,'security_cost':170000,'travel_multiplier':1.45,'ticket_multiplier':1.30,'market_bonus':420000,'prestige':9},{'country':'Saudi Arabia','region':'Riyadh','city':'Riyadh','venue':'Kingdom Arena','capacity':30000,'type':'Arena','rental_cost':2000000,'security_cost':600000,'travel_multiplier':2.00,'ticket_multiplier':2.10,'market_bonus':1200000,'prestige':9}]
COUNTRIES=['United States','Canada','United Kingdom','Japan','Mexico','Saudi Arabia','Australia','Germany','France','Italy','Spain','Ireland','Brazil','India','South Korea','China','United Arab Emirates','Qatar','South Africa']
def clamp_stat(v,lo=0,hi=100):
 return max(lo,min(hi,int(v)))

def _rng(r):
 if r is None or r==0: return 0
 if isinstance(r,tuple): return random.randint(int(r[0]),int(r[1]))
 return int(r)

DEBUT_STATUSES=['Not Debuted','Debuted','Returning Soon','On Hiatus','Free Agent']
DEBUT_TYPES=['Match Debut','Promo Debut','Surprise Debut','Return','Backstage Debut','Twitter Debut','Media Debut']
DEFAULT_NOT_DEBUTED={'Dragon Lee','Tyler Bate','Pete Dunne','Lexis King','Trick Williams',"Je'Von Evans",'Fraxiom','Apollo Crews','Andre Walker','Ethan Page','Matt Cardona','Lexis King'}

def is_not_debuted(w):
 return w and w.get('debut_status','Debuted')=='Not Debuted'

def is_debuted_active(w):
 return w and w.get('debut_status') in ('Debuted','Returning Soon')

def ensure_wrestler_stats():
 for w in st.session_state.roster:
  w.setdefault('controversy_risk',20); w.setdefault('fan_support',w.get('fan_investment',50)); w.setdefault('locker_room_reputation',55)
  w.setdefault('sponsor_trust',60); w.setdefault('political_outspoken',False)
  if w.get('fan_investment') and w.get('fan_support',50)==50: w['fan_support']=min(100,int(w.get('fan_investment',50)))
  crisis.seed_wrestler_loyalty(w)

def ensure_wrestler_debut_fields():
 ensure_wrestler_stats()
 if 'debut_history' not in st.session_state: st.session_state.debut_history=[]
 if 'debut_warnings' not in st.session_state: st.session_state.debut_warnings=[]
 for w in st.session_state.roster:
  if 'debut_status' not in w:
   w['debut_status']='Not Debuted' if w['name'] in DEFAULT_NOT_DEBUTED else 'Debuted'
  w.setdefault('debut_week',w.get('debut_week') or (st.session_state.week if w['debut_status']=='Debuted' else None))
  w.setdefault('debut_show',''); w.setdefault('debut_company',w.get('company','')); w.setdefault('debut_segment',''); w.setdefault('debut_type','')
  w.setdefault('debut_rating',0); w.setdefault('last_booked_week',w.get('last_booked_week'))
  w.setdefault('weeks_since_debut',0); w.setdefault('weeks_not_used_after_debut',0)
  w.setdefault('contract_weeks_left',52); w.setdefault('renewal_chance',70)
  if w['debut_status']=='Debuted' and w.get('debut_week') and st.session_state.week>=w['debut_week']:
   w['weeks_since_debut']=max(0,st.session_state.week-int(w['debut_week']))

def mark_wrestler_debuted(w,company,show_name='',debut_type='Match Debut',segment='',story_snippet='',week=None):
 if not w or is_tag_team_entry(w): return False
 was_not=is_not_debuted(w)
 dw=int(week if week is not None else st.session_state.week)
 w['debut_status']='Debuted' if w.get('debut_status')!='Returning Soon' else 'Debuted'
 w['debut_week']=dw; w['debut_show']=show_name or w.get('debut_show',''); w['debut_company']=company
 w['debut_segment']=segment or debut_type; w['debut_type']=debut_type
 w['last_booked_week']=int(week if week is not None else st.session_state.week); w['weeks_not_used_after_debut']=0
 if was_not:
  rating=grade_debut_quality(w,story_snippet,debut_type,segment)
  w['debut_rating']=rating
  st.session_state.debut_history.insert(0,{'week':dw,'name':w['name'],'company':company,'show':show_name,'type':debut_type,'segment':segment,'rating':rating})
  st.session_state.news_feed.insert(0,f"TV DEBUT: {w['name']} ({debut_type}) on {show_name or company} — rated {rating}/10")
 return was_not

def mark_wrestler_booked(w,week=None,company='',show_name='',context='match'):
 if not w or is_tag_team_entry(w): return
 week=int(week if week is not None else st.session_state.week)
 comp=company or w.get('company','')
 dtype={'match':'Match Debut','promo':'Promo Debut','story':'Surprise Debut','backstage':'Backstage Debut','twitter':'Twitter Debut','media':'Media Debut'}.get(context,'Match Debut')
 if is_not_debuted(w): mark_wrestler_debuted(w,comp,show_name,dtype,segment=context,week=week)
 else:
  w['last_booked_week']=week; w['weeks_not_used_after_debut']=0
  if w.get('debut_status')=='Returning Soon': w['debut_status']='Debuted'
  if w.get('company') in PLAYABLE:
   crisis.adjust_brand_loyalty(w,random.randint(2,4),f'Booked on {show_name or comp}')
   w['booking_satisfaction']=min(100,int(w.get('booking_satisfaction',60))+random.randint(1,3))

def grade_debut_quality(w,story_snippet,debut_type,segment):
 score=6.0; sn=(story_snippet or '').lower()
 if 'main event' in sn or 'champion' in sn or w['overall']>=90: score+=1.5
 if any(x in sn for x in ['attack','betray','surprise','return','cryptic','crowd','roar','champion']): score+=1.2
 if debut_type in ('Match Debut','Surprise Debut'): score+=.8
 if 'random' in sn and 'backstage' in sn and len(sn)<80: score-=1.5
 if not sn: score=6.5
 score=max(1,min(10,round(score,1)))
 if score>=8:
  apply_wrestler_deltas(w,pop=(5,8),mom=(6,10),morale=(4,7),fan_support=(4,8),rivalry=(5,10))
 elif score>=6:
  apply_wrestler_deltas(w,pop=(2,5),mom=(3,6),morale=(2,4))
 else:
  apply_wrestler_deltas(w,mom=(1,2),fan_support=(-2,0))
  st.session_state.setdefault('storyline_flags',[]).insert(0,{'week':st.session_state.week,'flag':'Weak debut intro','target':w['name'],'company':w['company'],'notes':f"{w['name']} debut rated {score}/10 — follow up needed."})
 return score

def debut_unused_penalty(w):
 if not w or is_not_debuted(w) or not is_debuted_active(w): return None
 if w.get('debut_status') in ('On Hiatus','Free Agent'): return None
 weeks=int(w.get('weeks_not_used_after_debut',0))
 if weeks<2: return None
 pop=w.get('popularity',50); mult=1.4 if pop>=85 else (1.1 if pop>=75 else 0.85)
 pen={'weeks':weeks,'warnings':[]}
 if weeks==2:
  pen.update({'morale':-int(2*mult),'momentum':-1}); pen['warnings'].append(f"{w['name']} debuted but has not been booked for 2 weeks.")
 elif weeks==3:
  pen.update({'morale':-int(5*mult),'momentum':-3}); pen['warnings'].append(f"{w['name']} debuted in Week {w.get('debut_week')} but has not been followed up ({weeks} weeks).")
 elif weeks>=4:
  pen.update({'morale':-int(8*mult),'momentum':-5}); pen['warnings'].append(f"{w['name']} is frustrated after {weeks} weeks without TV time.")
  if int(w.get('contract_weeks_remaining',w.get('contract_weeks_left',52)))<=8: pen['warnings'].append(f"{w['name']} contract has {w.get('contract_weeks_remaining',0)} weeks left — renewal harder if unused.")
 return pen

def apply_debut_unused_penalties(company=None):
 ensure_wrestler_debut_fields()
 warnings=[]
 for w in st.session_state.roster:
  if company and w['company']!=company: continue
  pen=debut_unused_penalty(w)
  if not pen: continue
  apply_wrestler_deltas(w,morale=pen.get('morale',0),momentum=pen.get('momentum',0))
  for msg in pen.get('warnings',[]):
   warnings.append(msg)
   st.session_state.debut_warnings.insert(0,{'week':st.session_state.week,'company':w['company'],'wrestler':w['name'],'message':msg})
  if pen.get('weeks',0)>=3 and random.random()<.35:
   txt=random.choice([f"I didn't come here to sit in catering. — {w['name']}",f"Debut was the easy part. Getting opportunity around here? That's the fight. — {w['name']}",f"Funny how the spotlight disappears after the first pop. — {w['name']}"])
   make_twitter_post(w['company'],'wrestler',w['name'],'@'+slug(w['name']).replace('_',''),'Wrestler','Creative Complaint Tweet',txt,'',{'ai_generated':True,'topic':'Creative Complaint','tone':'bitter','effects':{'controversy':(4,8),'morale':(-2,0),'buzz':(3,6)}})
  if pen.get('weeks',0)>=4 and int(w.get('contract_weeks_remaining',52))<=6:
   w['renewal_chance']=max(10,w.get('renewal_chance',70)-15)
 return warnings

def advance_debut_week_tracking(company,booked_names):
 ensure_wrestler_debut_fields()
 booked=set(booked_names or [])
 for w in st.session_state.roster:
  if w['company']!=company: continue
  if is_not_debuted(w): continue
  if w['name'] in booked:
   mark_wrestler_booked(w,st.session_state.week,company)
  elif is_debuted_active(w):
   w['weeks_not_used_after_debut']=int(w.get('weeks_not_used_after_debut',0))+1

def detect_story_debuts(text,company):
 ensure_wrestler_debut_fields()
 found=[]
 for w in roster(company):
  if not is_singles_entry(w) or not is_not_debuted(w): continue
  if w['name'].lower() in (text or '').lower(): found.append(w['name'])
 return found

def collect_booked_from_show(matches,promos):
 names=set()
 for m in matches or []:
  for n in m.get('participants',[]):
   if n and n not in ('None','TBD','NC','A','B','Unknown'): names.add(n)
  win=m.get('winner')
  if win and win not in ('None','TBD','NC',''): names.add(win)
 for p in promos or []:
  for n in p.get('participants',[]):
   if n and n not in ('None','Unknown'): names.add(n)
 return names

def process_show_booking_debuts(matches,promos,story,company,show_name,run_week):
 ensure_wrestler_debut_fields()
 booked=collect_booked_from_show(matches,promos)
 for n in booked:
  w=find(n)
  if not w: continue
  ctx='promo' if any(n in (pp.get('participants') or []) for pp in (promos or [])) and not any(n in (mm.get('participants') or []) for mm in (matches or [])) else 'match'
  mark_wrestler_booked(w,run_week,company,show_name,ctx)
 for nm in st.session_state.get('confirmed_story_debuts',[]):
  w=find(nm)
  if w and w['company']==company: mark_wrestler_debuted(w,company,show_name,'Surprise Debut',segment='Long Story',story_snippet=story or '',week=run_week)
 return booked

def set_wrestler_debut_status(w,status,debut_week=None):
 if not w or is_tag_team_entry(w): return
 ensure_wrestler_debut_fields()
 w['debut_status']=status if status in DEBUT_STATUSES else w['debut_status']
 if status=='Not Debuted':
  w['debut_week']=None; w['weeks_not_used_after_debut']=0; w['last_booked_week']=None
 elif status in ('Debuted','Returning Soon'):
  if debut_week is not None: w['debut_week']=int(debut_week)
  elif not w.get('debut_week'): w['debut_week']=st.session_state.week
 elif status=='On Hiatus':
  w['weeks_not_used_after_debut']=0

def get_debut_followup_warnings(company=None):
 ensure_wrestler_debut_fields()
 out=[]
 for w in st.session_state.roster:
  if company and w['company']!=company: continue
  pen=debut_unused_penalty(w)
  if pen: out.append(f"**{w['name']}** — debuted Week {w.get('debut_week','?')}, not booked {pen['weeks']} weeks. Morale/momentum at risk.")
 return out[:12]

WEEKS_PER_YEAR=52
CONTRACT_STATUSES=['Active','Expiring Soon','Negotiating','Refused Renewal','Released','Free Agent','Signed Elsewhere']
RENEWAL_STATUSES=['Not Started','Offer Made','Negotiating','Accepted','Rejected','Wants More Money','Wants Better Booking','Wants Creative Control','Testing Free Agency']
CONTRACT_PRESETS={
 'CM Punk':{'salary':8500000,'contract_length_years':3},
 'Christian Rose':{'salary':12000000,'contract_length_years':5},
 'Roman Reigns':{'salary':12000000,'contract_length_years':4},
 'Seth Rollins':{'salary':9500000,'contract_length_years':4},
 'Becky Lynch':{'salary':9000000,'contract_length_years':4},
 'Rhea Ripley':{'salary':5500000,'contract_length_years':4},
 'Jade Cargill':{'salary':6000000,'contract_length_years':4},
 'Logan Paul':{'salary':8000000,'contract_length_years':3},
 'Triple H':{'salary':10000000,'contract_length_years':5},
 'The Rock':{'salary':15000000,'contract_length_years':3},
}

def game_contract_year():
 return 2025+max(0,int(st.session_state.get('year',1))-1)

def calendar_year_locked():
 return bool(st.session_state.get('calendar_locked',False))

def sync_wrestler_from(w):
 if not w: return
 loc=(w.get('from_location') or w.get('hometown') or HOMETOWNS.get(w['name'],'') or '').strip()
 if not loc: loc='Unknown'
 w['from_location']=loc; w['hometown']=loc

def apply_from_locations():
 for w in st.session_state.roster:
  sync_wrestler_from(w)
 for members in TAG_TEAM_MEMBERS.values():
  for m in members:
   if not m.get('from'): m['from']=HOMETOWNS.get(m['name'],'Unknown')

def default_contract_years_for(w):
 if w['overall']>=94: return 5
 if w['overall']>=88: return 3
 if w['overall']>=82: return 2
 return 1

def seed_default_contract(w,start_year=None,start_week=None):
 ensure_wrestler_debut_fields()
 sy=int(start_year if start_year is not None else game_contract_year())
 sw=int(start_week if start_week is not None else st.session_state.week)
 preset=CONTRACT_PRESETS.get(w['name'],{})
 yrs=int(preset.get('contract_length_years',default_contract_years_for(w)))
 if preset.get('salary'): w['salary']=int(preset['salary'])
 w['contract_length_years']=yrs
 w['contract_start_year']=sy; w['contract_start_week']=sw
 w['contract_expiration_year']=sy+yrs
 w['contract_expiration_week']=sw
 w['contract_status']='Active'; w['renewal_status']='Not Started'
 w['salary_demand']=int(w['salary']*1.12)
 w['contract_demand']='Standard multi-year deal'
 w['contract_morale_impact']=0
 w['free_agency_eligible']=False
 w['previous_company']=''
 w['fa_reason']=''
 w['negotiation_offer_salary']=0
 w['negotiation_offer_years']=0
 w['negotiation_signing_bonus']=0
 recompute_contract_counters(w)

def recompute_contract_counters(w):
 if not w or is_tag_team_entry(w): return
 cy=game_contract_year(); cw=int(st.session_state.week)
 exp_y=int(w.get('contract_expiration_year',cy))
 exp_w=int(w.get('contract_expiration_week',0))
 start_y=int(w.get('contract_start_year',cy))
 yrs_given=int(w.get('contract_length_years',2))
 w['contract_length_years']=yrs_given
 weeks_left=max(0,(exp_y-cy)*WEEKS_PER_YEAR+(exp_w-cw))
 w['contract_weeks_remaining']=weeks_left
 w['contract_weeks_left']=weeks_left
 w['contract_years_remaining']=round(weeks_left/WEEKS_PER_YEAR,2)
 if w.get('contract_status') in ('Free Agent','Released','Signed Elsewhere'): return
 if weeks_left<=0 and w.get('contract_status')=='Active':
  w['contract_status']='Expiring Soon'
 elif weeks_left<=8:
  w['contract_status']='Expiring Soon' if w.get('contract_status')=='Active' else w.get('contract_status')
 elif w.get('contract_status')=='Expiring Soon' and weeks_left>8:
  w['contract_status']='Active'
 w['free_agency_eligible']=weeks_left<=0 or w.get('contract_status') in ('Free Agent','Released')
 w['salary_demand']=max(int(w.get('salary_demand',w['salary'])),int(w['salary']*1.08))

def ensure_contract_fields():
 ensure_wrestler_debut_fields()
 apply_from_locations()
 if 'free_agency_pool' not in st.session_state: st.session_state.free_agency_pool=[]
 if 'negotiation_history' not in st.session_state: st.session_state.negotiation_history=[]
 if 'contract_warnings' not in st.session_state: st.session_state.contract_warnings=[]
 for w in st.session_state.roster:
  if is_tag_team_entry(w): continue
  sync_wrestler_from(w)
  if 'contract_start_year' not in w:
   seed_default_contract(w)
  else:
   for k,v in [('contract_length_years',2),('contract_start_year',game_contract_year()),('contract_start_week',0),('contract_expiration_year',game_contract_year()+2),('contract_expiration_week',0),('contract_status','Active'),('renewal_status','Not Started'),('salary_demand',w['salary']),('contract_demand','Standard deal'),('contract_morale_impact',0),('free_agency_eligible',False),('previous_company',''),('fa_reason',''),('negotiation_offer_salary',0),('negotiation_offer_years',0),('negotiation_signing_bonus',0)]:
    w.setdefault(k,v)
  recompute_contract_counters(w)

def contract_display_line(w):
 recompute_contract_counters(w)
 wk=int(w.get('contract_weeks_remaining',0))
 if w.get('contract_status')=='Free Agent': return 'Contract: Expired · Status: Free Agent'
 if wk<=0: return 'Contract: Expired'
 if wk<=8: return f'Contract: {wk} weeks left ⚠️'
 return f"Contract: {w.get('contract_length_years',0)} yr · Expires {w.get('contract_expiration_year','—')} · {w.get('contract_years_remaining',0):.1f} yr left"

def is_champion_name(n):
 return any(n==c for t in st.session_state.champions.values() for c in t.values() if c and c not in ('Vacant','Place Holder','TBD - Tournament','TBD - Title Match'))

def compute_renewal_chance(w,offer_salary=None,offer_years=None,bonus=0,creative=False,media=False,title_push=False):
 if not w: return 0
 recompute_contract_counters(w)
 offer_salary=int(offer_salary if offer_salary is not None else w.get('negotiation_offer_salary',w['salary']))
 demand=int(w.get('salary_demand',w['salary']))
 base=42
 base+=min(28,(w.get('morale',50)-50)*.45)
 base+=min(18,(w.get('popularity',50)-50)*.28)
 base+=min(12,(w.get('momentum',50)-50)*.2)
 if offer_salary>=demand: base+=18
 elif offer_salary>=w['salary']: base+=8
 else: base-=14
 if offer_years and offer_years>=3: base+=4
 if bonus>0: base+=min(10,bonus/500000)
 if creative: base+=5
 if media: base+=4
 if title_push: base+=6
 if is_champion_name(w['name']): base-=6; base+=8 if offer_salary>=demand*1.15 else 0
 if int(w.get('weeks_not_used_after_debut',0))>=3 and w.get('debut_status')=='Debuted': base-=18
 wr=w.get('wins',0); lr=w.get('losses',0)
 if wr>lr: base+=4
 elif lr>wr+3: base-=5
 prof=st.session_state.company_profiles.get(w['company'],{})
 base+=min(8,int(prof.get('prestige',80))*.08)
 if w.get('renewal_status')=='Wants More Money' and offer_salary<demand*1.1: base-=12
 if w.get('renewal_status')=='Wants Better Booking': base+=6 if title_push else -8
 if w.get('renewal_status')=='Testing Free Agency': base-=10
 w['renewal_chance']=max(5,min(95,int(base)))
 return w['renewal_chance']

def log_negotiation(w,company,action,detail):
 st.session_state.negotiation_history.insert(0,{'week':st.session_state.week,'name':w['name'],'company':company,'action':action,'detail':detail,'salary':w.get('salary'),'renewal_status':w.get('renewal_status')})

def contract_twitter_blast(w,kind,company='',other_co=''):
 texts={
  'wrestler_complaint':[f"Funny how loyalty only matters when the contract is almost up. — {w['name']}",f"The business side of this place? Let's just say the numbers don't lie. — {w['name']}"],
  'owner':[f"We value every talent on this roster. Business will be handled professionally. — {COMPANIES.get(company,{}).get('owner','Ownership')}"],
  'rival':[f"If they don't appreciate you over there, there's always room on our side. — {w['name']}"],
  'company':[f"BREAKING: {other_co or company} has signed {w['name']} to a multi-year contract."],
  'commentator':[f"That is a major loss for {company} if they let {w['name']} walk."],
 }
 if kind=='wrestler_complaint': make_twitter_post(company,'wrestler',w['name'],'@'+slug(w['name']).replace('_',''),'Wrestler','Contract Tweet',random.choice(texts['wrestler_complaint']),'',{'ai_generated':True,'topic':'Contract','tone':'bitter','effects':{'controversy':(3,7),'buzz':(2,5)}})
 elif kind=='company' and other_co: make_twitter_post(other_co,'company',other_co+' Official','@'+slug(other_co),'Company Account','Contract News',texts['company'][0],'',{'ai_generated':True,'topic':'Contract','effects':{'buzz':(5,10)}})
 elif kind=='commentator':
  staf=next((s for s in st.session_state.staff.get(company,[]) if 'Commentator' in s.get('role','')),None)
  if staf: make_twitter_post(company,'staff',staf['name'],staf['handle'],'Commentator','Contract Reaction',texts['commentator'][0],w['name'],{'ai_generated':True,'topic':'Contract'})

def move_to_free_agency(w,reason='Contract expired'):
 if not w or is_tag_team_entry(w): return
 ensure_contract_fields()
 prev=w['company']
 w['previous_company']=prev; w['fa_reason']=reason
 w['contract_status']='Free Agent'; w['renewal_status']='Testing Free Agency'
 w['free_agency_eligible']=True
 w['contract_weeks_remaining']=0; w['contract_weeks_left']=0
 w['company']='Free Agency'
 w['debut_status']=w.get('debut_status','Debuted')
 entry={'name':w['name'],'from_location':w.get('from_location','Unknown'),'overall':w['overall'],'popularity':w['popularity'],'morale':w['morale'],'salary_demand':w.get('salary_demand',w['salary']),'contract_demand':w.get('contract_demand','Multi-year deal'),'previous_company':prev,'reason':reason,'interested':random.sample(PLAYABLE,min(2,len(PLAYABLE))),'signing_chance':min(90,40+w['popularity']//2)}
 pool=[x for x in st.session_state.free_agency_pool if x.get('name')!=w['name']]
 pool.insert(0,entry); st.session_state.free_agency_pool=pool
 st.session_state.news_feed.insert(0,f"{prev} forgot to renew {w['name']}. {w['name']} is now a free agent. ({reason})")
 if w['popularity']>=85 or is_champion_name(w['name']):
  prof=st.session_state.company_profiles.get(prev,{})
  prof['prestige']=max(1,int(prof.get('prestige',80))-3)
  st.session_state.setdefault('storyline_flags',[]).insert(0,{'week':st.session_state.week,'flag':'Major star lost to free agency','target':w['name'],'company':prev,'notes':reason})
 contract_twitter_blast(w,'wrestler_complaint',prev)
 contract_twitter_blast(w,'commentator',prev)
 sync_company_payroll_stats()

def advance_contracts_weekly(company):
 if not calendar_year_locked(): return []
 ensure_contract_fields()
 for w in payroll_wrestlers(company):
  recompute_contract_counters(w)
  wk=int(w.get('contract_weeks_remaining',0))
  if wk>0:
   w['contract_weeks_remaining']=wk-1; w['contract_weeks_left']=wk-1
   recompute_contract_counters(w)
  else:
   if w.get('contract_status') not in ('Free Agent','Released','Negotiating'):
    move_to_free_agency(w,f'{company} contract expired — now Free Agent')
 get_contract_warnings(company)

def get_contract_warnings(company=None):
 ensure_contract_fields()
 warns=[]
 for w in st.session_state.roster:
  if is_tag_team_entry(w): continue
  if company and w.get('company')!=company and w.get('company')!='Free Agency': continue
  if w.get('company')=='Free Agency': continue
  recompute_contract_counters(w)
  wk=int(w.get('contract_weeks_remaining',0))
  nm=w['name']; co=w.get('company','')
  if w.get('contract_status')=='Free Agent': continue
  if wk==0: warns.append(f"**{nm}** ({co}) — contract expired. Free agency risk.")
  elif wk==1: warns.append(f"**{nm}** — contract expires **this week**. Renew or lose them.")
  elif wk==2: warns.append(f"**{nm}** has **2 weeks** left on contract.")
  elif wk==4: warns.append(f"**{nm}** has **4 weeks** left. Renew or risk free agency.")
  elif wk==8: warns.append(f"**{nm}** has **8 weeks** left on contract.")
  if wk<=8 and is_champion_name(nm): warns.append(f"⚠️ **CHAMPION** {nm} contract expiring soon ({wk} weeks).")
  if w.get('renewal_status') in ('Rejected','Testing Free Agency','Refused Renewal'): warns.append(f"**{nm}** — {w.get('renewal_status')}. May test free agency.")
 for msg in warns[:16]:
  st.session_state.contract_warnings.insert(0,{'week':st.session_state.week,'company':company or '','message':msg})
 return warns

def apply_contract_offer(w,company,salary,years,bonus=0,creative=False,media=False,title_push=False):
 ensure_contract_fields()
 w['negotiation_offer_salary']=int(salary); w['negotiation_offer_years']=int(years)
 w['negotiation_signing_bonus']=int(bonus)
 w['contract_status']='Negotiating'; w['renewal_status']='Offer Made'
 chance=compute_renewal_chance(w,salary,years,bonus,creative,media,title_push)
 if random.randint(1,100)<=chance:
  w['salary']=int(salary); w['contract_length_years']=int(years)
  sy=game_contract_year(); sw=st.session_state.week
  w['contract_start_year']=sy; w['contract_start_week']=sw
  w['contract_expiration_year']=sy+int(years); w['contract_expiration_week']=sw
  w['contract_status']='Active'; w['renewal_status']='Accepted'
  recompute_contract_counters(w)
  if bonus>0:
   add_transaction(company,'Signing Bonus',f"{w['name']} renewal bonus",-int(bonus))
   finance_flash(company,-int(bonus),f"signing bonus: {w['name']}")
  log_negotiation(w,company,'Renewal Accepted',f"{years}yr @ {money(salary)}")
  st.session_state.news_feed.insert(0,f"{w['name']} re-signed with {company} ({years} years, {money(salary)}).")
  crisis.adjust_brand_loyalty(w,random.randint(4,8)+(3 if creative else 0)+(2 if title_push else 0),'Contract renewed — promises kept')
  sync_company_payroll_stats()
  return True
 if int(salary)<int(w.get('salary',salary)):
  w['rejected_pay_cut']=True
  crisis.adjust_brand_loyalty(w,-10,'Rejected pay cut / low renewal offer')
 if salary<w.get('salary_demand',w['salary']):
  w['renewal_status']='Wants More Money'
 elif not title_push and w.get('weeks_not_used_after_debut',0)>=2:
  w['renewal_status']='Wants Better Booking'
 else:
  w['renewal_status']='Rejected'
 w['contract_status']='Refused Renewal'
 log_negotiation(w,company,'Renewal Rejected',f"Offer {money(salary)} — chance was {chance}%")
 contract_twitter_blast(w,'wrestler_complaint',company)
 return False

def sign_free_agent_to_company(w,company,years,salary,bonus=0):
 ensure_contract_fields()
 if get_company_budget(company)<int(salary)+int(bonus):
  return False,'Budget too low for salary + bonus.'
 w['company']=company; w['contract_status']='Active'; w['renewal_status']='Accepted'
 w['salary']=int(salary); seed_default_contract(w)
 w['contract_length_years']=int(years)
 sy=game_contract_year()
 w['contract_expiration_year']=sy+int(years)
 recompute_contract_counters(w)
 st.session_state.free_agency_pool=[x for x in st.session_state.free_agency_pool if x.get('name')!=w['name']]
 if bonus>0:
  add_transaction(company,'Free Agent Signing Bonus',f"{w['name']} signing",-int(bonus))
  finance_flash(company,-int(bonus),f"FA signing bonus")
 add_transaction(company,'Free Agent Signing',f"{w['name']} — {years}yr",0)
 st.session_state.news_feed.insert(0,f"{company} signed {w['name']} ({years} years, {money(salary)}).")
 contract_twitter_blast(w,'company',company,company)
 for oc in PLAYABLE:
  if oc!=company and random.random()<.4: contract_twitter_blast(w,'rival',oc)
 log_negotiation(w,company,'Signed from Free Agency',f"{years}yr @ {money(salary)}")
 sync_company_payroll_stats()
 return True,'Signed'

def release_wrestler_contract(w,company,fee=500000):
 ensure_contract_fields()
 if fee>0 and get_company_budget(company)>=fee:
  add_transaction(company,'Release Fee',f"Released {w['name']}",-int(fee))
  finance_flash(company,-int(fee),f"release: {w['name']}")
 w['contract_status']='Released'; w['renewal_status']='Rejected'
 move_to_free_agency(w,f'Released by {company}')
 return True

def apply_wrestler_deltas(w,pop=0,morale=0,momentum=0,stamina=0,controversy=0,fan_support=0,locker=0,sponsor=0,buzz=0,rivalry=0):
 if not w: return {}
 ch={}
 if pop: d=_rng(pop); w['popularity']=clamp_stat(w['popularity']+d); ch['popularity']=d
 if morale: d=_rng(morale); w['morale']=clamp_stat(w['morale']+d); ch['morale']=d
 if momentum: d=_rng(momentum); w['momentum']=clamp_stat(w['momentum']+d); ch['momentum']=d
 if stamina: d=_rng(stamina); w['stamina']=clamp_stat(w['stamina']+d); ch['stamina']=d
 if controversy: d=_rng(controversy); w['controversy_risk']=clamp_stat(w['controversy_risk']+d); ch['controversy_risk']=d
 if fan_support: d=_rng(fan_support); w['fan_support']=clamp_stat(w['fan_support']+d); w['fan_investment']=w['fan_support']; ch['fan_support']=d
 if locker: d=_rng(locker); w['locker_room_reputation']=clamp_stat(w['locker_room_reputation']+d); ch['locker_room_reputation']=d
 if sponsor: d=_rng(sponsor); w['sponsor_trust']=clamp_stat(w['sponsor_trust']+d); ch['sponsor_trust']=d
 if buzz: d=_rng(buzz); w['twitter_buzz']=clamp_stat(w['twitter_buzz']+d); ch['twitter_buzz']=d
 if rivalry: d=_rng(rivalry); w['rivalry_heat']=clamp_stat(w.get('rivalry_heat',0)+d); ch['rivalry_heat']=d
 return ch

def _ev_tpl(name,etype,desc,pop=0,morale=0,mom=0,sta=0,money=0,cont=0,sponsor=0,buzz=0,fan_support=0,locker=0,rivalry=0,story='',ai='',w=1):
 return {'name':name,'event_type':etype,'description':desc,'pop':pop,'morale':morale,'momentum':mom,'stamina':sta,'money':money,'controversy':cont,'sponsor':sponsor,'buzz':buzz,'fan_support':fan_support,'locker':locker,'rivalry':rivalry,'storyline':story,'ai_followup':ai,'weight':w}

RANDOM_EVENT_CATALOG=[
 _ev_tpl('Tourism Board Bonus','Business','City tourism board offers co-promotion.',pop=(3,7),morale=(2,5),money=(400000,1200000),buzz=(2,6),story='Local market boost for next show.',ai='Use hometown stars and city-specific hype.',w=2),
 _ev_tpl('Local Government Event Grant','Business','Mayor/governor grants event subsidy.',money=(500000,1500000),pop=(2,5),story='Positive PR week.',w=2),
 _ev_tpl('International Media Tour','Media','International press tour builds global buzz.',pop=(4,9),morale=(-2,2),sta=(-6,-2),money=(600000,2000000),buzz=(5,10),story='Media momentum before international show.',w=2),
 _ev_tpl('Stadium Sponsor Activation','Business','Stadium sponsor activates premium branding.',money=(500000,1800000),pop=(3,6),sponsor=(3,7),w=2),
 _ev_tpl('Sold-Out Arena Bonus','Business','Tickets sell out early.',pop=(5,10),morale=(3,6),money=(800000,2500000),fan_support=(4,8),w=2),
 _ev_tpl('Celebrity Attends Show','Story','Celebrity guest in front row goes viral.',pop=(3,8),buzz=(4,9),money=(300000,900000),w=2),
 _ev_tpl('Emotional Victory Boosts Fan Support','Story','Underdog win becomes emotional moment.',pop=(4,10),morale=(5,10),mom=(4,8),fan_support=(5,10),w=2),
 _ev_tpl('Underdog Becomes Fan Favorite','Story','Crowd rallies behind underdog.',pop=(5,12),fan_support=(6,12),mom=(3,7),w=2),
 _ev_tpl('Storyline Becomes Unexpectedly Hot','Story','Angle catches fire online.',pop=(4,9),buzz=(6,12),rivalry=(5,10),w=2),
 _ev_tpl('Olympics Appearance Creates National Pride','Media','Olympic crossover boosts babyface.',pop=(3,9),morale=(2,6),sponsor=(2,6),w=2),
 _ev_tpl('Good Morning America Interview Boosts Babyface','Media','Wholesome TV hit lifts star.',pop=(3,8),morale=(2,5),sponsor=(2,5),w=2),
 _ev_tpl('NBA Halftime Appearance Goes Viral','Media','Sports crossover trends.',pop=(4,10),buzz=(5,10),money=(400000,1200000),w=2),
 _ev_tpl('Grammys Appearance Creates Heat','Media','Music culture crossover.',pop=(3,8),buzz=(4,8),cont=(0,5),w=2),
 _ev_tpl('Fan Petition Demands Better Booking','Story','Fans campaign for better usage.',pop=(2,6),morale=(-2,3),story='Book meaningful segment next week.',ai='Reward fan movement with a strong segment.',w=2),
 _ev_tpl('Missed Flight','Travel','Talent misses connection.',pop=(-4,-1),morale=(-6,-2),sta=(-8,-3),money=(-200000,-80000),cont=(2,6),w=2),
 _ev_tpl('Travel Delay','Travel','Travel chaos affects roster.',morale=(-5,-1),sta=(-6,-2),money=(-150000,-50000),w=2),
 _ev_tpl('Visa Issue','Travel','Visa paperwork delays arrival.',morale=(-4,-1),sta=(-5,-2),money=(-200000,-100000),w=2),
 _ev_tpl('Championship Belt Lost During Travel','Travel','Belt lost in transit.',pop=(-6,-2),cont=(5,10),buzz=(4,9),story='Title storyline chaos.',w=2),
 _ev_tpl('Championship Belt Stolen During Travel','Travel','Belt stolen — angle potential.',pop=(-4,2),cont=(6,12),buzz=(6,12),story='Investigation angle.',w=2),
 _ev_tpl('Minor Injury','Injury','Talent banged up.',pop=(-3,-1),morale=(-4,-1),sta=(-10,-4),mom=(-3,-1),w=2),
 _ev_tpl('Major Injury','Injury','Serious injury.',pop=(-8,-3),morale=(-10,-4),sta=(-20,-8),mom=(-6,-2),money=(-400000,-150000),w=2),
 _ev_tpl('Locker Room Tension Between Talent','Locker Room','2-6 wrestlers arguing backstage.',morale=(-6,-2),locker=(-8,-3),cont=(3,8),buzz=(2,6),story='Faction or rivalry escalation.',w=3),
 _ev_tpl('Superstar Complains About Creative On Twitter','Locker Room','Public creative complaint.',pop=(-6,-2),morale=(-4,0),cont=(6,12),buzz=(5,12),sponsor=(-6,-2),story='GM must respond.',ai='Address on next show or Twitter.',w=2),
 _ev_tpl('Superstar Refuses To Lose','Locker Room','Talent refuses finish.',pop=(-5,-1),morale=(-8,-3),locker=(-10,-4),cont=(5,10),story='Behind-the-scenes power struggle.',w=2),
 _ev_tpl('Superstar Walks Out Before Match','Locker Room','Walkout before match.',pop=(-8,-3),morale=(-10,-5),cont=(8,15),buzz=(6,12),money=(-300000,-100000),w=2),
 _ev_tpl('Tag Team Partner Feels Disrespected','Locker Room','Tag tension rises.',morale=(-5,-1),locker=(-6,-2),rivalry=(4,8),story='Tag team breakup tease.',w=2),
 _ev_tpl('DUI Arrest','Scandal','Legal scandal hits star.',pop=(-20,-8),morale=(-12,-5),cont=(10,18),sponsor=(-10,-15),money=(-2500000,-800000),w=1),
 _ev_tpl('Public Assault','Scandal','Public fight scandal.',pop=(-15,-5),cont=(8,15),sponsor=(-8,-12),money=(-2000000,-600000),w=1),
 _ev_tpl('Sponsor Complains About Character Direction','Sponsor','Sponsor unhappy with character.',pop=(-6,-2),sponsor=(-10,-15),morale=(-4,-1),story='Adjust character or risk deal.',w=2),
 _ev_tpl('Interview Goes Wrong','Media','Media interview backfires.',pop=(-8,-3),cont=(4,10),buzz=(3,8),sponsor=(-4,-8),w=2),
 _ev_tpl('Fans Reject Storyline','Story','Crowd rejects angle.',pop=(-12,-4),morale=(-5,-1),fan_support=(-8,-3),story='Pivot storyline next week.',w=2),
 _ev_tpl('Crowd Rejects Storyline','Story','Live crowd turns on angle.',pop=(-10,-4),fan_support=(-6,-2),story='Change direction or double down.',w=2),
 _ev_tpl('Fans Turn On Overpushed Star','Story','Backlash to overpush.',pop=(-10,-3),morale=(-6,-2),fan_support=(-8,-4),w=2),
 _ev_tpl('Wrestler Feels Disrespected After Being Left Off Card','Story','Talent left off card angry.',morale=(-8,-3),pop=(-4,2),cont=(3,8),story='Book them or explain storyline absence.',ai='Use Twitter complaint in grading continuity.',w=2),
 _ev_tpl('Creative Walkout','Locker Room','Creative staff walkout rumor.',morale=(-6,-2),locker=(-5,-2),money=(-500000,-180000),w=1),
 _ev_tpl('Contract Renewal Dispute','Business','Contract talks stall.',morale=(-5,-2),pop=(-3,3),cont=(3,7),story='Contract segment next week.',w=2),
 _ev_tpl('Network Interference','Business','Network wants changes.',pop=(-2,4),money=(-500000,-200000),story='Adjust main event for network.',w=1),
 _ev_tpl('Montreal Screwjob','Story','Controversial finish talk.',pop=(-2,6),cont=(5,12),buzz=(6,12),rivalry=(5,10),w=1),
 _ev_tpl('Unexpected Turn','Story','Surprise angle opportunity.',pop=(2,7),mom=(3,7),rivalry=(4,8),w=2),
 _ev_tpl('Wellness Policy Violation','Scandal','Wellness violation.',pop=(-8,-3),morale=(-6,-2),cont=(5,10),sponsor=(-5,-10),w=1),
 _ev_tpl('Contract Renewal Dispute','Business','Contract talks stall with {target}.',morale=(-6,-2),pop=(-3,3),cont=(3,7),story='Renew or risk free agency.',w=2),
 _ev_tpl('Superstar Wants Bigger Deal','Business','{target} demands a bigger contract.',morale=(-4,0),pop=(2,6),story='Salary demand increased.',w=2),
 _ev_tpl('Champion Threatens Free Agency','Business','Champion {target} threatens to walk.',pop=(3,8),cont=(5,10),buzz=(4,9),story='Urgent renewal needed.',w=2),
 _ev_tpl('Tag Team Wants Package Deal','Business','Tag team wants joint contract package.',morale=(-3,2),locker=(-4,2),story='Package deal negotiation.',w=2),
 _ev_tpl('Wrestler Refuses Renewal Due To Bad Booking','Story','{target} refuses renewal — bad booking.',morale=(-8,-3),pop=(-2,4),fan_support=(-4,-1),story='Book them better or lose them.',w=2),
 _ev_tpl('Wrestler Wants Creative Control','Business','{target} wants creative control clause.',cont=(4,8),morale=(-2,3),story='Creative control demand.',w=2),
 _ev_tpl('Wrestler Wants Media Opportunities','Media','{target} wants media/TV clauses.',pop=(2,6),sponsor=(2,5),story='Media opportunities in renewal.',w=2),
 _ev_tpl('Company Forgot To Renew Contract','Business','Front office forgot to renew {target}.',pop=(-4,-1),morale=(-6,-2),cont=(3,7),buzz=(3,8),story='Business mistake — renew immediately.',w=2),
 _ev_tpl('Free Agent Meeting Leaks','Media','Secret meeting with {target} leaks online.',buzz=(6,12),cont=(4,9),story='Free agency rumors heat up.',w=2),
 _ev_tpl('Rival Company Interested In Star','Business','Rival brand circling {target}.',morale=(-3,4),buzz=(5,10),story='Competing offer likely.',w=2),
 _ev_tpl('Sponsor Wants Star Re-Signed','Sponsor','Sponsor pressures renewal for {target}.',sponsor=(3,7),pop=(2,5),story='Sponsor wants star kept.',w=2),
 _ev_tpl('Fan Campaign Demands Renewal','Story','Fans campaign to re-sign {target}.',pop=(3,8),fan_support=(4,8),morale=(2,5),story='Fan pressure to renew.',w=2),
 _ev_tpl('Wrestler Signs Elsewhere','Business','{target} signs with another company (rumor).',pop=(-6,-2),morale=(-8,-3),buzz=(8,14),story='May leave soon if not countered.',w=1),
 _ev_tpl('Contract Tampering Rumor','Scandal','Tampering rumor around {target}.',cont=(6,12),buzz=(5,10),story='Legal/PR headache.',w=1),
 _ev_tpl('Agent Demands Higher Salary','Business','Agent pushes higher number for {target}.',morale=(-2,2),pop=(1,4),story='Agent driving price up.',w=2),
 _ev_tpl('Wrestler Demands PLE Main Event Clause','Business','{target} wants PLE main event clause.',morale=(-2,4),pop=(2,6),story='Main event clause in talks.',w=2),
]
EVENTS=[t['name'] for t in RANDOM_EVENT_CATALOG]+['Superstar Refuses To Perform In Country Due To Political Beliefs','Superstar Criticizes Host Country Online','Fans Split Over Political Statement','Network Requests Public Apology']

def political_refusal_event(target,company,venue,variant=None):
 w=find(target)
 if not variant: variant=random.choice(['fan_support','fan_reject','mixed','company_punish'])
 desc='In-game controversy: talent refuses to perform due to stated political beliefs (fiction only — business/story impact).'
 base={'event':'Superstar Refuses To Perform In Country Due To Political Beliefs','event_type':'Political/Travel','target':target,'company':company,'description':desc,'status':'unresolved','storyline':'Owner/GM must respond publicly.','ai_followup':'Book statement segment, Twitter debate, and card adjustment.'}
 if variant=='fan_support':
  base.update({'pop':(5,5),'morale':(4,4),'sponsor':(-2,-2),'controversy':(10,10),'fan_support':(6,6),'buzz':(8,8),'money':(-200000,-50000),'effect':'Fans support wrestler; sponsors nervous.'})
 elif variant=='fan_reject':
  base.update({'pop':(-8,-8),'morale':(-3,-3),'sponsor':(-6,-6),'controversy':(15,15),'fan_support':(-6,-6),'buzz':(10,10),'money':(-400000,-150000),'effect':'Fans reject decision; controversy spikes.'})
 elif variant=='mixed':
  base.update({'pop':0,'morale':(-1,2),'controversy':(12,12),'buzz':(10,10),'locker':(-3,5),'effect':'Split reaction; Twitter debate explodes.'})
 else:
  base.update({'pop':(-4,-6),'morale':(-10,-10),'locker':(8,8),'controversy':(10,10),'effect':'Company punishes talent — suspension angle possible.'})
 base['money']=base.get('money',(-300000,-100000))
 if isinstance(base['money'],tuple): base['money']=random.randint(base['money'][0],base['money'][1])
 return base

def build_random_event(company,target=None,venue=None):
 ensure_wrestler_stats()
 tgt=target or random.choice(opts(company))
 w=find(tgt)
 intl=venue and venue.get('country') not in ('United States',None,'')
 if intl and w and (w.get('political_outspoken') or w.get('morale',70)<45 or random.random()<.08):
  return political_refusal_event(tgt,company,venue)
 pool=[t for t in RANDOM_EVENT_CATALOG]
 weights=[t['weight'] for t in pool]
 tpl=random.choices(pool,weights=weights,k=1)[0]
 money=tpl['money']
 if isinstance(money,tuple): money=random.randint(money[0],money[1])
 desc=tpl['description'].replace('{target}',tgt)
 rec={'id':len(st.session_state.random_event_history)+1,'week':st.session_state.week,'month':st.session_state.month,'event':tpl['name'],'event_type':tpl['event_type'],'target':tgt,'company':company,'description':desc,'money':money,'effect':tpl['storyline'],'status':'unresolved','notes':'','bring_back':True,'storyline':tpl['storyline'],'ai_followup':tpl['ai_followup'],'tpl':tpl}
 return rec

def apply_random_event_record(ev):
 w=find(ev.get('target',''))
 tpl=ev.get('tpl') or {}
 ch=apply_wrestler_deltas(w,pop=ev.get('pop',tpl.get('pop',0)),morale=ev.get('morale',tpl.get('morale',0)),momentum=ev.get('momentum',tpl.get('momentum',0)),stamina=ev.get('stamina',tpl.get('stamina',0)),controversy=ev.get('controversy',tpl.get('controversy',0)),fan_support=ev.get('fan_support',tpl.get('fan_support',0)),locker=ev.get('locker',tpl.get('locker',0)),sponsor=ev.get('sponsor',tpl.get('sponsor',0)),buzz=ev.get('buzz',tpl.get('buzz',0)),rivalry=ev.get('rivalry',tpl.get('rivalry',0)))
 ev['stat_changes']=ch
 st.session_state.setdefault('storyline_flags',[]).insert(0,{'week':st.session_state.week,'flag':ev.get('event'),'target':ev.get('target'),'company':ev.get('company'),'notes':ev.get('storyline',''),'unresolved':ev.get('status')=='unresolved'})
 st.session_state.news_feed.insert(0,f"Random event: {ev.get('event')} — {ev.get('target')} — {ev.get('effect',ev.get('description',''))}")
 return ev

def money(x):
 try: return '${:,.0f}'.format(float(0 if x is None else x))
 except (TypeError, ValueError): return '—'
def fmt_display(v, default='—'):
 if v is None: return default
 if isinstance(v,str) and v.strip().lower() in ('','none','null'): return default
 return v
def appearance_risk_label(rec):
 if not isinstance(rec,dict): return '—'
 eff=rec.get('effects') if isinstance(rec.get('effects'),dict) else {}
 for v in (rec.get('controversy_risk'),rec.get('risk_level'),rec.get('risk'),eff.get('risk')):
  if v not in (None,'','null'): return fmt_display(v)
 return 'Low'
def normalize_appearance_record(rec):
 if not isinstance(rec,dict): return {}
 r=dict(rec)
 person=r.get('person') or r.get('wrestler')
 r['person']=fmt_display(person,'—')
 r['appearance']=fmt_display(r.get('appearance') or r.get('activity') or r.get('project_type'),'Appearance')
 r['company']=fmt_display(r.get('company'),'—')
 try: r['week']=int(r.get('week') or st.session_state.get('week',1))
 except (TypeError, ValueError): r['week']=1
 rev=r.get('revenue')
 try: r['revenue']=int(rev) if rev not in (None,'') else 0
 except (TypeError, ValueError): r['revenue']=0
 if not r.get('controversy_risk') and not r.get('risk_level'):
  eff=r.get('effects') if isinstance(r.get('effects'),dict) else {}
  risk=eff.get('risk') if isinstance(eff,dict) else None
  r['controversy_risk']=fmt_display(risk,'Low')
  r['risk_level']=r['controversy_risk']
 else:
  r['controversy_risk']=fmt_display(r.get('controversy_risk') or r.get('risk_level'),'Low')
  r['risk_level']=r['controversy_risk']
 return r
def migrate_appearance_records():
 for key in ('appearance_history','exclusive_activity_history'):
  if key in st.session_state:
   st.session_state[key]=[normalize_appearance_record(a) for a in st.session_state.get(key,[])]
 if st.session_state.get('last_cameo'):
  st.session_state.last_cameo=normalize_cameo_record(st.session_state.last_cameo)
 if st.session_state.get('cameo_library'):
  st.session_state.cameo_library=[normalize_cameo_record(c) for c in st.session_state.cameo_library]
def normalize_cameo_record(rec):
 if not isinstance(rec,dict): return {}
 r=dict(rec)
 r['person']=fmt_display(r.get('person'),'—')
 r['partner']=fmt_display(r.get('partner'),'—')
 r['project_type']=fmt_display(r.get('project_type'),'—')
 r['tone']=fmt_display(r.get('tone'),'—')
 r['title']=fmt_display(r.get('title'),f"{r['person']} — {r['partner']} {r['project_type']}")
 r['label']=fmt_display(r.get('label'),'Saved')
 r['script']=r.get('script') or ''
 r['risk_level']=fmt_display(r.get('risk_level'),'Low')
 r['continuity_warning']=fmt_display(r.get('continuity_warning'),'')
 try: r['week']=int(r.get('week') or st.session_state.get('week',1))
 except (TypeError, ValueError): r['week']=1
 eff=r.get('effects') if isinstance(r.get('effects'),dict) else {}
 for flat,key,default in (
  ('revenue','revenue',0),('popularity_effect','popularity',0),('morale_effect','morale',0),
  ('stamina_effect','stamina',0),('sponsor_effect','sponsor_confidence',0),('merchandise_boost','merchandise_boost',0),
 ):
  if r.get(flat) is None and isinstance(eff,dict): r[flat]=eff.get(key,default)
  elif r.get(flat) is None: r[flat]=default
 return r
def slug(n): return re.sub(r'[^a-z0-9_]','',n.lower().replace(' ','_').replace("'",'').replace("\u2019",''))

def image_file_ok(path):
 """Skip empty/corrupt files so st.image never raises PIL.UnidentifiedImageError."""
 try:
  p=Path(path)
  if not p.is_file() or p.stat().st_size<32: return False
  from PIL import Image
  with Image.open(p) as im:
   im.load()
  return True
 except Exception:
  return False

def purge_invalid_asset_files():
 """Delete broken uploads so previews never crash the page."""
 for root in ('assets/wrestlers','assets/owners','assets/gm','assets/staff','assets/podcast_hosts','assets/logos','assets/banners','assets/belts'):
  d=Path(root)
  if not d.is_dir(): continue
  for p in d.iterdir():
   if p.is_file() and p.suffix.lower() in ('.png','.jpg','.jpeg','.webp') and not image_file_ok(p):
    try: p.unlink()
    except OSError: pass

def safe_st_image(path,w=80,fallback_label='IMG',fallback_h=None):
 if path:
  try:
   from PIL import Image
   with Image.open(path) as im:
    im.load()
    st.image(im,width=w)
   return
  except Exception:
   try: Path(path).unlink(missing_ok=True)
   except OSError: pass
 show_img_slot(fallback_label,w,fallback_h or (w-10 if w>50 else 70))

def img_path(n):
 for e in ['.png','.jpg','.jpeg','.webp']:
  p=Path('assets/wrestlers')/f'{slug(n)}{e}'
  if p.exists() and image_file_ok(p): return str(p)
 return ''
def show_img(n,w=80):
 p=img_path(n)
 if p: safe_st_image(p,w,'IMG')
 else: st.markdown(f"<div style='width:{w}px;height:{w}px;border:1px dashed #b026ff;border-radius:14px;display:flex;align-items:center;justify-content:center;color:#c9b6e8;background:#151520'>IMG</div>",unsafe_allow_html=True)
def rec(w): return f"{w.get('wins',0)}-{w.get('losses',0)}-{w.get('draws',0)}"
def align(a): return {'F':'Face','H':'Heel','N':'Neutral'}.get(a,a)
def roster(company=None): return [w for w in st.session_state.roster if not company or w['company']==company]
def find(name): return next((w for w in st.session_state.roster if w['name']==name),None)
def opts(company=None): return [w['name'] for w in sorted(roster(company),key=lambda x:x['name'].lower())]

def opts_singles(company):
 return sorted([w['name'] for w in roster(company) if is_singles_entry(w)],key=str.lower)

def opts_individuals(company):
 return sorted(set(opts_singles(company)+opts_women(company)),key=str.lower)

def opts_twitter_wrestlers(company='NXT'):
 """Individual wrestlers only for Twitter (includes tag team members, excludes team unit names)."""
 comps=PLAYABLE if company=='All' else [company]
 names=[]
 for c in comps:
  for w in roster(c):
   if not is_tag_team_entry(w): names.append(w['name'])
 return sorted(set(names),key=str.lower)

def tag_team_for_wrestler(name,company):
 for w in roster(company):
  if not is_tag_team_entry(w): continue
  if any(m['name']==name for m in team_members_for(w,company)): return w['name']
 return ''

def twitter_wrestler_extra(name,comp,**extra):
 tname=tag_team_for_wrestler(name,comp)
 if tname:
  tw=find(tname)
  extra.setdefault('team_name',tname)
  if tw: extra.setdefault('members',[m['name'] for m in team_members_for(tw,comp)])
 return extra

def opts_women(company):
 return sorted([w['name'] for w in roster(company) if is_women_entry(w)],key=str.lower)

def opts_tags(company):
 return sorted([w['name'] for w in roster(company) if is_tag_team_entry(w) and is_team_active(company,w['name'])],key=str.lower)

def opts_factions(company):
 return sorted(COMPANY_FACTIONS.get(company,[]),key=str.lower)

def opts_champions(company):
 ch=set()
 for t,v in st.session_state.champions.get(company,{}).items():
  if v and not is_vacant_champion(v): ch.add(v)
 return sorted(ch,key=str.lower)

def opts_company_accounts(company):
 return sorted([s['name'] for s in st.session_state.staff.get(company,[]) if s.get('role')=='Company Account'],key=str.lower)

def opts_staff_people(company):
 return sorted([f"{s['name']} — {s['role']}" for s in st.session_state.staff.get(company,[]) if s.get('role')!='Company Account'],key=str.lower)

def roster_pool(company,pool_type='All'):
 if pool_type=='Singles Wrestlers': return opts_singles(company)
 if pool_type=="Women's Roster": return opts_women(company)
 if pool_type=='Tag Teams': return opts_tags(company)
 if pool_type=='Staff': return [x.split(' — ')[0] for x in opts_staff_people(company)]
 if pool_type=='Champions': return opts_champions(company)
 if pool_type=='Factions': return opts_factions(company)
 return opts(company)

def pool_for_poster(comp,poster_type,roster_filter='All'):
 if poster_type=='Wrestler': return opts_singles(comp) if roster_filter=='Singles Wrestlers' else (opts_women(comp) if roster_filter=="Women's Roster" else opts_individuals(comp))
 if poster_type=='Tag Team': return opts_tags(comp)
 if poster_type=='Faction': return opts_factions(comp)
 if poster_type=='Staff': return opts_staff_people(comp)
 if poster_type=='Company Account': return opts_company_accounts(comp)
 return roster_pool(comp,roster_filter)

PRIORITY_SELECTOR_NAMES=frozenset(['None','Vacant','','Place Holder'])
ENTITY_SELECTOR_TYPES=['All','Wrestler','Tag Team','Faction','Staff','Company Account','Podcast Host']

def dropdown_scroll_css():
 return """<style>
div[data-baseweb="popover"]{max-height:600px!important;overflow-y:auto!important;z-index:999999!important}
ul[role="listbox"]{max-height:520px!important;overflow-y:auto!important}
div[role="listbox"]{max-height:520px!important;overflow-y:auto!important}
[data-baseweb="select"]{z-index:999999!important}
[data-testid="stSelectbox"]{overflow:visible!important}
[data-testid="stVerticalBlock"]{overflow:visible!important}
.block-container{overflow:visible!important}
</style>"""

def ensure_selector_css():
 if not st.session_state.get('_selector_css'):
  st.markdown(dropdown_scroll_css(),unsafe_allow_html=True)
  st.session_state._selector_css=True

def filter_name_list(names,search='',preserve_order=False):
 s=search.strip().lower()
 if preserve_order:
  out=list(dict.fromkeys(names))
 else:
  out=sorted(set(names),key=lambda x:x.lower())
 if s: out=[n for n in out if s in n.lower()]
 return out

def opts_podcast_hosts(company='NXT'):
 ensure_nxt_unfiltered_hosts()
 return sorted([h['name'] for h in st.session_state.nxt_unfiltered_hosts.values() if h.get('company','NXT')==company or company=='All'],key=str.lower)

def clean_name_pool(company='NXT',entity_type='All',wrestler_sub='All'):
 comps=PLAYABLE if company=='All' else [company]
 names=[]
 for c in comps:
  if entity_type in ('All','Wrestler'):
   if wrestler_sub=="Women's Roster": names.extend(opts_women(c))
   elif wrestler_sub=='Singles Wrestlers': names.extend(opts_singles(c))
   else: names.extend(opts_individuals(c))
  if entity_type in ('All','Tag Team'): names.extend(opts_tags(c))
  if entity_type in ('All','Faction'): names.extend(opts_factions(c))
  if entity_type in ('All','Staff'): names.extend(opts_staff_people(c))
  if entity_type in ('All','Company Account'): names.extend(opts_company_accounts(c))
  if entity_type in ('All','Podcast Host'): names.extend(opts_podcast_hosts(c))
 blocked=set()
 if entity_type not in ('Podcast Host',) and not st.session_state.get('podcast_hosts_booking_enabled',False):
  for h in st.session_state.get('nxt_unfiltered_hosts',{}).values():
   if not h.get('bookable',False): blocked.add(h.get('name'))
 names=[n for n in names if n not in blocked]
 return sorted(set(n for n in names if n is not None),key=str.lower)

def _build_selector_pool(options,extra_options=None,preserve_order=False):
 extra_options=extra_options or []
 if preserve_order:
  return list(dict.fromkeys(extra_options+list(options)))
 return sorted(dict.fromkeys(extra_options+list(options)),key=lambda x:(0 if x in PRIORITY_SELECTOR_NAMES else 1,str(x).lower()))

def clean_name_selector(label,key,current=None,options=None,extra_options=None,company=None,entity_type=None,company_filter=False,type_filter=False,default_company='NXT',default_entity='All',preserve_order=False,show_search=True,label_search='Search name…',label_select=None,wrestler_sub='All'):
 """Search + scrollable selectbox: full A–Z list when search empty; filtered when typing."""
 ensure_selector_css()
 label_select=label_select or label
 co=company; et=entity_type
 if company_filter or type_filter:
  ncols=2 if company_filter and type_filter else 1
  cols=st.columns(ncols)
  ci=0
  if company_filter:
   co_opts=['All']+PLAYABLE
   with cols[ci]: co=st.selectbox('Company',co_opts,index=co_opts.index(default_company) if default_company in co_opts else 0,key=f'{key}_co')
   ci+=1
  if type_filter:
   with cols[min(ci,ncols-1)]: et=st.selectbox('Type',ENTITY_SELECTOR_TYPES,index=ENTITY_SELECTOR_TYPES.index(default_entity) if default_entity in ENTITY_SELECTOR_TYPES else 0,key=f'{key}_ty')
 else:
  co=co or default_company; et=et or default_entity
 if options is None: options=clean_name_pool(co,et,wrestler_sub)
 pool=_build_selector_pool(options,extra_options,preserve_order)
 st.markdown('<div class="clean-selector-wrap">',unsafe_allow_html=True)
 search=''
 if show_search: search=st.text_input(label_search,value='',key=f'{key}_srch',placeholder='Type to filter — clear search to browse A–Z')
 browse_order=preserve_order or not search.strip()
 filtered=filter_name_list(pool,search,preserve_order=browse_order)
 if not filtered:
  st.caption('No matches — clear search or change company/type filters.')
  if extra_options: return extra_options[0]
  return current
 pick_list=list(filtered)
 if current is not None and current not in pick_list: pick_list=[current]+[x for x in pick_list if x!=current]
 idx=pick_list.index(current) if current in pick_list else 0
 pick=st.selectbox(label_select,pick_list,index=min(idx,len(pick_list)-1),key=f'{key}_sel')
 if search.strip(): st.caption(f'{len(pick_list)} match(es)')
 elif len(pick_list)>15: st.caption(f'{len(pick_list)} names — open dropdown to scroll A–Z')
 return pick

def clean_name_multiselect(label,key,options=None,company=None,entity_type=None,company_filter=False,type_filter=False,default_company='NXT',default_entity='All',label_search='Search name…'):
 ensure_selector_css()
 co=company; et=entity_type
 if company_filter or type_filter:
  ncols=2 if company_filter and type_filter else 1
  cols=st.columns(ncols)
  ci=0
  if company_filter:
   co_opts=['All']+PLAYABLE
   with cols[ci]: co=st.selectbox('Company',co_opts,index=co_opts.index(default_company) if default_company in co_opts else 0,key=f'{key}_co')
   ci+=1
  if type_filter:
   with cols[min(ci,ncols-1)]: et=st.selectbox('Type',ENTITY_SELECTOR_TYPES,index=ENTITY_SELECTOR_TYPES.index(default_entity) if default_entity in ENTITY_SELECTOR_TYPES else 0,key=f'{key}_ty')
 else:
  co=co or default_company; et=et or default_entity
 if options is None: options=clean_name_pool(co,et)
 pool=sorted(set(options),key=str.lower)
 search=st.text_input(label_search,value='',key=f'{key}_ms',placeholder='Type to filter — clear for full list')
 filtered=filter_name_list(pool,search,preserve_order=not search.strip())
 if not filtered: st.caption('No matches.'); return []
 return st.multiselect(label,filtered,key=f'{key}_mul')

def searchable_select(label,names,key,current=None,extra_options=None,per_page=24,none_option=None,preserve_order=False,**kwargs):
 kwargs.pop('per_page',None); kwargs.pop('none_option',None)
 return clean_name_selector(label=label,key=key,options=names,current=current,extra_options=extra_options,preserve_order=preserve_order,company_filter=False,type_filter=False,**kwargs)

def searchable_multiselect(label,names,key,max_show=50,**kwargs):
 return clean_name_multiselect(label=label,key=key,options=names,**kwargs)

def roster_type_selector(company,key,default='All'):
 return st.selectbox('Roster filter',['All','Singles Wrestlers',"Women's Roster",'Tag Teams','Champions','Staff','Factions'],key=f'{key}_rf',index=['All','Singles Wrestlers',"Women's Roster",'Tag Teams','Champions','Staff','Factions'].index(default) if default in ['All','Singles Wrestlers',"Women's Roster",'Tag Teams','Champions','Staff','Factions'] else 0)

def champion_pick_pool(comp,title):
 pri=['Vacant','Place Holder']
 if is_tag_title(title):
  tags=sorted(opts_tags(comp),key=str.lower)
  inds=sorted([n for n in opts_individuals(comp) if n not in tags],key=str.lower)
  return pri+tags+inds
 return pri+sorted(opts_individuals(comp),key=str.lower)

TEAM_TWEET_TYPES=['Team Promo Tweet','Tag Title Hype Tweet','Breakup Tease Tweet','Faction Statement','Rival Team Callout','Tag Match Reaction','Loss Frustration Tweet','Win Streak Tweet','Company Shot Tweet','PLE Promotion Tweet','Reply Tweet','Quote Tweet']

def team_handle(team_name):
 clean=re.sub(r'[^a-zA-Z0-9]','',team_name.replace(' ',''))
 return '@'+clean if clean else '@TagTeam'

def ensure_team_profiles():
 if 'team_profiles' not in st.session_state: st.session_state.team_profiles={}
 for w in st.session_state.roster:
  if not is_tag_team_entry(w): continue
  k=f"{w['company']}::{w['name']}"
  members=[m['name'] for m in team_members_for(w,w['company'])]
  st.session_state.team_profiles.setdefault(k,{'handle':team_handle(w['name']),'voice':'aggressive unified tag team','members':members,'tension':0,'chemistry':70})

def get_team_profile(team_w,comp):
 ensure_team_profiles()
 k=f"{comp}::{team_w['name']}"
 return st.session_state.team_profiles.setdefault(k,{'handle':team_handle(team_w['name']),'voice':'tag team','members':[],'tension':0,'chemistry':70})

def team_tweet(team_w,comp,typ,mention='',reply_context=''):
 members=team_members_for(team_w,comp)
 prof=get_team_profile(team_w,comp)
 mem_txt=', '.join([f"{m['name']} ({align(m.get('alignment','N'))})" for m in members])
 prompt=f"Write one under-280-char Twitter post for TAG TEAM {team_w['name']} ({comp}). Handle {prof['handle']}. Team voice: {prof['voice']}. Members: {mem_txt}. Type: {typ}. Record {rec(team_w)} streak {team_w.get('streak','')}. Mention: {mention}. Context: {reply_context}. Sound like a TEAM not one individual. Original dialogue only."
 out=ai(prompt)
 if out: return out.strip()
 if 'Breakup' in typ: return f"Sometimes the strongest bond is the one about to snap. — {team_w['name']}"
 if 'Rival' in typ or 'Callout' in typ: return f"{mention or 'the so-called competition'} wants smoke? {team_w['name']} brought the whole fight."
 if 'Win' in typ: return f"{team_w['name']}: another night, another win. Tag division better take notes."
 return f"{team_w['name']}: tables, ladders, gold, and no apologies. {comp} is ours this week."

def member_team_tweet(member_name,team_name,comp,typ,mention='',tone='support',reply_context=''):
 w=find(member_name)
 partner=''
 if team_name:
  mems=[m['name'] for m in team_members_for(find(team_name) or {'name':team_name},comp)]
  partner=next((x for x in mems if x!=member_name),'')
 if not w: return f"{member_name}: we're still standing."
 parent_hint=f' They are REPLYING to this post: "{reply_context[:200]}". Reference a specific line, defend or attack it, sound like a real Twitter reply.' if reply_context and len(reply_context)>20 else ''
 prompt=f"Write under-280-char Twitter post as INDIVIDUAL wrestler {member_name} ({comp}). Tag partner: {partner or 'none'} (team {team_name or 'solo'}). NEVER post as a team account or use a team handle. Tone: {tone}. Type: {typ}. Mention: {mention}.{parent_hint} In character: {char_profile(member_name)}. Sound like {member_name} only — casual, not scripted promo."
 out=ai(prompt)
 if out and not str(out).startswith('AI error'): return out.strip()
 live=twitter_live_context(comp,w,mention); live['partner']=partner
 if tone=='breakup': return pick_varied_fallback(member_name,comp,'Tag Team Drama','bitter','Breakup Tease Tweet',partner,live)
 if tone=='member_support' or tone=='support':
  if mention and len(str(reply_context or ''))>20:
   return pick_reply_fallback(member_name,{'parent_text':reply_context,'parent_author':mention,'parent_company':comp},'Defend / co-sign','Tag Team Drama','emotional','reply')
  opts=[f"{partner} had my back before the cameras — don't twist it. — {member_name}",f"Quote tweet energy: we move as individuals, win as a unit. — {member_name}",f"Tag gold hits different when {mention or 'rivals'} keep talking. — {member_name}"]
  return random.choice(opts)
 if tone=='rival_callout': return pick_varied_fallback(member_name,comp,'Rivalry','savage','Rivalry Tweet',mention,live)
 return pick_varied_fallback(member_name,comp,'Tag Team Drama','emotional',typ,mention,live)

def wrestler_tweet_text(w,comp,typ,mention=''):
 tname=tag_team_for_wrestler(w['name'],comp)
 if tname: return member_team_tweet(w['name'],tname,comp,typ,mention,'support')
 return tweet(w,typ,mention)

def apply_twitter_post_effects(post):
 ensure_wrestler_stats()
 comp=post.get('company'); effects=post.get('effects',{})
 interaction=post.get('interaction','')
 topic=post.get('topic','Wrestling Story')
 w=find(post.get('wrestler',''))
 if post.get('poster_kind')=='wrestler' and post.get('team_name'):
  tw=find(post['team_name'])
  if tw:
   prof=get_team_profile(tw,comp)
   if interaction in ('breakup','member_subtweet','callout_partner'):
    prof['tension']=min(100,prof.get('tension',0)+8)
    st.session_state.setdefault('storyline_flags',[]).insert(0,{'week':st.session_state.week,'flag':'Tag Twitter tension','target':post.get('wrestler'),'company':comp,'notes':f"{post.get('wrestler')} / {post['team_name']} breakup tease"})
   elif interaction in ('member_support','member_defend','quote_teammate'):
    prof['chemistry']=min(100,prof.get('chemistry',70)+3)
 if w:
  pop=effects.get('popularity',0); ch=apply_wrestler_deltas(w,pop=pop or (3,10) if post.get('viral') else (1,4),morale=effects.get('morale',0),momentum=effects.get('momentum',0),controversy=effects.get('controversy',0),fan_support=effects.get('fan_support',0),locker=effects.get('locker',0),sponsor=effects.get('sponsor',0),buzz=effects.get('buzz',2),rivalry=effects.get('rivalry',0))
  post['stat_changes']=ch
  if effects.get('controversy',0) and _rng(effects.get('controversy',0))>=8:
   st.session_state.setdefault('twitter_drama',[]).insert(0,{'week':st.session_state.week,'wrestler':w['name'],'company':comp,'topic':topic,'text':post.get('text','')[:200],'unresolved':True})
  if 'Political' in topic or 'Creative' in topic or 'Card' in topic:
   st.session_state.setdefault('storyline_flags',[]).insert(0,{'week':st.session_state.week,'flag':f'Twitter: {topic}','target':w['name'],'company':comp,'notes':post.get('text','')[:120],'unresolved':True})
 for rname in (post.get('mentions') or '').split(','):
  rw=find(rname.strip())
  if rw and interaction=='rival_callout': apply_wrestler_deltas(rw,rivalry=(3,6),controversy=(1,4))

def format_social_num(n):
 n=max(0,int(n))
 if n>=1_000_000_000: return f"{n/1_000_000_000:.2f}B".replace('.00B','B')
 if n>=1_000_000: return f"{n/1_000_000:.2f}M".replace('.00M','M').replace('0M','M')
 if n>=1000: return f"{n/1000:.1f}K".replace('.0K','K')
 return f"{n:,}"

def compute_tweet_engagement(w,comp,topic,tone,typ,effects=None):
 """Scale likes/views up to billions on mega-viral posts."""
 effects=effects or {}
 base=random.randint(12000,85000)
 mult=1.0
 if w:
  mult+=w.get('popularity',50)/100*1.1
  mult+=w.get('momentum',50)/100*0.55
  mult+=min(100,w.get('twitter_buzz',0))/100*0.75
  mult+=w.get('controversy_risk',20)/100*1.25
  mult+=w.get('fan_support',50)/100*0.35
  if is_champ(w['name']): mult+=0.55
  if w.get('morale',50)<35: mult+=0.2
 t=(topic or '').lower(); tn=(tone or '').lower(); ty=(typ or '').lower()
 if 'controversy' in t or t=='political/controversy': mult+=random.uniform(0.65,1.4)
 if 'creative' in t or 'card' in t: mult+=random.uniform(0.45,1.0)
 if 'political' in t: mult+=random.uniform(0.55,1.2)
 if 'rivalry' in t: mult+=0.4
 if 'ple' in t: mult+=0.35
 if 'other company' in t: mult+=0.3
 if tn in ('angry','savage','petty','bitter','political','scared'): mult+=random.uniform(0.2,0.55)
 if 'complaint' in ty or 'angry' in ty or 'drama' in ty or 'cryptic' in ty: mult+=0.35
 if 'champion' in ty: mult+=0.4
 ctr_boost=int(_rng(effects.get('controversy',0))) if effects.get('controversy') else 0
 mult+=ctr_boost/25
 views=int(min(2_500_000_000,max(5000,base*mult*random.uniform(0.9,1.35))))
 if mult>=2.8 and random.random()<0.12:
  boost=max(80_000_000,int(views*random.uniform(8,40)))
  views=min(2_500_000_000,boost)
 elif mult>=2.0 and random.random()<0.18:
  boost=max(5_000_000,int(views*random.uniform(3,12)))
  views=min(500_000_000,boost)
 likes=int(min(views//2,max(200,views*random.uniform(0.025,0.14))))
 reposts=int(min(likes,max(30,likes*random.uniform(0.08,0.35))))
 replies=int(min(likes,max(15,likes*random.uniform(0.04,0.22))))
 viral=views>=400_000 or likes>=60_000
 mega=views>=100_000_000
 controversy_score=min(100,int(25+mult*12+(ctr_boost*2)+(w.get('controversy_risk',0)//3 if w else 10)))
 return {'views':views,'likes':likes,'reposts':reposts,'replies':replies,'viral':viral,'mega':mega,'controversy_score':controversy_score}

def make_twitter_post(comp,poster_kind,display_name,handle,role,typ,text,mention='',extra=None):
 extra=extra or {}
 w_eng=extra.get('wrestler_obj')
 eng=extra.get('engagement') or compute_tweet_engagement(w_eng,comp,extra.get('topic','Wrestling Story'),extra.get('tone',''),typ,extra.get('effects',{}))
 extra.setdefault('mega',eng.get('mega',False))
 parent_snip=''
 if extra.get('reply_to_id'):
  parent=next((p for p in st.session_state.twitter_posts if p.get('id')==extra.get('reply_to_id')),None)
  if parent: parent_snip=(parent.get('text','') or '')[:120]
 if extra.get('reply_to_id'):
  parent_ref=next((p for p in st.session_state.twitter_posts if p.get('id')==extra.get('reply_to_id')),None)
  if parent_ref: parent_ref['replies']=int(parent_ref.get('replies',0) or 0)+random.randint(3,24)
 text=(text or '').strip()[:280]
 if text and is_duplicate_tweet(text):
  text=ensure_unique_tweet(lambda i: f"{text[:220]} · W{st.session_state.week}-{random.randint(100000,999999999)}")[:280]
 elif text:
  register_tweet_text(text)
 post={'id':len(st.session_state.twitter_posts)+1,'week':st.session_state.week,'company':comp,'wrestler':display_name,'role':role,'handle':handle,'post_type':typ,'text':text,
 'likes':eng['likes'],'reposts':eng['reposts'],'replies':eng['replies'],'views':eng['views'],
 'mentions':mention,'effects':extra.get('effects',{}),'viral':eng['viral'],'mega':eng.get('mega',False),'controversy_score':eng['controversy_score'],
 'ai_generated':extra.get('ai_generated',False),'poster_kind':poster_kind,'team_name':extra.get('team_name',''),'members':extra.get('members',[]),
 'reply_to_id':extra.get('reply_to_id'),'reply_to_snippet':parent_snip,'interaction':extra.get('interaction',''),
 'topic':extra.get('topic','Wrestling Story'),'tone':extra.get('tone',''),'tweet_mode':extra.get('tweet_mode','original'),
 'label':extra.get('label','AI' if extra.get('ai_generated') else 'Manual'),'stat_changes':{}}
 apply_twitter_post_effects(post)
 return post

def twitter_recruitment_post_fn(comp,kind,name,handle,role,typ,text,mention,extra):
 eff=extra.get('effects') or compute_tweet_effects(extra.get('topic','Other Company Comment'),extra.get('tone','petty'),find(name),comp,mention)
 ex={**extra,'effects':eff,'topic':extra.get('topic','Other Company Comment'),'tone':extra.get('tone','petty'),'wrestler_obj':find(name),'ai_generated':extra.get('ai_generated',True)}
 return make_twitter_post(comp,kind,name,handle or '@'+slug(name).replace('_',''),role,typ,text,mention,ex)

def render_twitter_recruitment_tab(comp,allowed_cos,tw_edit):
 twrecruit.ensure_recruitment_state()
 crisis.ensure_crisis_state()
 st.caption('Recruit or tease rival-brand wrestlers — AI decides target reaction (morale, loyalty, FA interest, bidding risk).')
 if not tw_edit: render_edit_only_notice(comp); return
 rec_co=comp if comp in PLAYABLE else (allowed_cos[0] if allowed_cos else 'NXT')
 if not is_admin() and rec_co not in allowed_cos:
  st.warning(f'You can only recruit as **{st.session_state.assigned_company}**.')
  rec_co=st.session_state.assigned_company
 st.session_state.twitter_manual_gm_response=st.toggle('Manual GM Response Mode (target brand picks reaction)',value=st.session_state.get('twitter_manual_gm_response',False),key='tw_recruit_manual_gm')
 c1,c2=st.columns(2)
 with c1:
  recruiter=clean_name_selector('Recruiter (your brand wrestler)','tw_rec_r',options=opts_twitter_wrestlers(rec_co),company=rec_co,entity_type='Wrestler',default_company=rec_co,label_search='Search recruiter')
  rw=find(recruiter)
  if rw and is_tag_team_entry(rw): st.warning('Pick an individual wrestler — not a tag team entry.')
 with c2:
  tgt_co=st.selectbox('Target brand',[c for c in PLAYABLE if c!=rec_co],key='tw_rec_tgt_co')
  tgt_opts=[w['name'] for w in st.session_state.roster if w.get('company')==tgt_co and not is_tag_team_entry(w)]
  target=clean_name_selector('Target wrestler','tw_rec_t',options=sorted(tgt_opts),extra_options=[],label_search='Search target',show_search=True)
  tw=find(target)
 if rw and tw:
  tier_lbl=twrecruit.morale_tier(int(tw.get('morale',50)))[1]
  vuln,reasons=twrecruit.recruitment_vulnerability_score(tw,tgt_co,rec_co,crisis.is_financial_crisis,None)
  st.write(f"**{target}** · Morale **{tw.get('morale')}** ({tier_lbl}) · Loyalty **{tw.get('brand_loyalty',50)}** · Vulnerability **{vuln}/100**")
  if reasons: st.caption('Why vulnerable: '+', '.join(reasons))
  if crisis.is_financial_crisis(tgt_co): st.error(f'**{tgt_co} is in Financial Crisis** — recruitment tweets are more dangerous.')
  int_map=tw.get('recruitment_interest') or {}
  if int_map: st.caption('Recruitment interest: '+', '.join(f"{k} {v}" for k,v in int_map.items()))
 tweet_type=st.selectbox('Tweet type',twrecruit.RECRUIT_TWEET_TYPES,key='tw_rec_type')
 suggested=twrecruit.suggest_recruit_tweet(recruiter or 'Star',rec_co,target or 'Talent',tgt_co,tweet_type) if recruiter and target else ''
 tweet_text=st.text_area('Tweet text',suggested or '',height=100,key='tw_rec_text')
 tampering,tamper_note=twrecruit.estimate_tampering(tweet_type,tweet_text)
 st.caption(f"**Tampering risk:** {tampering} — {tamper_note}")
 risk_est=0
 if rw and tw: risk_est=max(0,min(100,vuln))
 st.progress(risk_est/100.0,text=f'AI recruitment risk estimate: {risk_est}%')
 manual_resp=None
 if st.session_state.get('twitter_manual_gm_response') and can_edit_company(tgt_co):
  manual_resp=st.selectbox('Target brand GM chooses reaction',['(AI decides)']+twrecruit.TARGET_RESPONSES,key='tw_rec_manual_resp')
  if manual_resp=='(AI decides)': manual_resp=None
 if st.button('Post recruitment tweet',type='primary',key='tw_rec_post',disabled=not(rw and tw and not is_tag_team_entry(rw))):
  if not can_tweet_as_company(rec_co):
   st.error(f'You can only tweet as {rec_co}.'); st.stop()
  res=twrecruit.process_recruitment_tweet(rw,tw,rec_co,tgt_co,tweet_type,tweet_text.strip(),find,is_champion_name,crisis.adjust_brand_loyalty,manual_target_response=manual_resp,post_tweet_fn=twitter_recruitment_post_fn)
  if not res.get('ok'):
   st.error(res.get('error','Failed.'))
  else:
   for p in res.get('posts',[]): st.session_state.twitter_posts.insert(0,p)
   if tampering=='high' and can_edit_company(tgt_co):
    mp_add_transaction(tgt_co,'Tampering Fine',f'Twitter tampering — {recruiter} vs {target}',-random.randint(150000,450000))
   touch_universe_meta(rec_co); touch_universe_meta(tgt_co); save_universe()
   st.session_state.last_recruitment_result=res
   st.success('Recruitment tweet posted.'); st.rerun()
 if st.session_state.get('last_recruitment_result'):
  res=st.session_state.last_recruitment_result
  with bfg_card('Last recruitment result'):
   st.markdown(f"**Recruiter:** {res['record']['recruiter']} ({res['record']['recruiter_company']}) → **{res['record']['target']}** ({res['record']['target_company']})")
   st.markdown(f"**Tweet type:** {res['record']['tweet_type']} · **Tampering:** {res['tampering']}")
   st.markdown(f"**Target response:** {res['response_outcome'].replace('_',' ')}")
   if res.get('response_text') and not res['response_text'].startswith('('):
    st.markdown(f"**They said:** _{res['response_text']}_")
   st.markdown(f"**AI explanation:** {res['explanation']}")
   eff=res.get('effects',{})
   st.write(f"Morale Δ {eff.get('target_morale',0):+} · Loyalty Δ {eff.get('target_loyalty',0):+} · Buzz +{eff.get('target_buzz',0)} · FA interest +{eff.get('fa_interest',0)} · Bidding risk +{eff.get('bidding_risk',0)}")
  if st.button('Clear result',key='tw_rec_clear'): st.session_state.pop('last_recruitment_result',None); st.rerun()
 with st.expander('Recruitment history',expanded=False):
  hist=st.session_state.get('twitter_recruitment_history',[])
  if not hist: st.caption('No recruitment attempts yet.')
  for h in hist[:15]:
   st.caption(f"W{h.get('week')} **{h['recruiter']}** ({h['recruiter_company']}) → **{h['target']}** · {h.get('tweet_type')} · {h.get('response')} · vuln {h.get('vulnerability')}")

def twitter_page_stats(comp):
 posts=st.session_state.twitter_posts
 cp=[p for p in posts if p.get('company')==comp]
 wk=int(st.session_state.week)
 return {
  'total':len(posts),'brand':len(cp),
  'week':sum(1 for p in cp if int(p.get('week',-1))==wk),
  'viral':sum(1 for p in cp if p.get('viral')),
  'hot':sum(1 for p in cp if int(p.get('controversy_score',0) or 0)>=55),
  'drama':len([d for d in st.session_state.get('twitter_drama',[]) if d.get('company')==comp]),
 }

def filter_twitter_posts(posts,feed_co='All',feed_typ='All',feed_week=False,viral_only=False,contro_only=False,search=''):
 out=list(posts)
 if feed_co!='All': out=[p for p in out if p.get('company')==feed_co]
 if feed_typ=='Replies only': out=[p for p in out if p.get('reply_to_id') or p.get('post_type') in ('Reply Tweet','Quote Tweet','Tag Partner Reply')]
 elif feed_typ!='All': out=[p for p in out if p.get('post_type')==feed_typ]
 if feed_week: out=[p for p in out if int(p.get('week',-1))==int(st.session_state.week)]
 if viral_only: out=[p for p in out if p.get('viral')]
 if contro_only: out=[p for p in out if int(p.get('controversy_score',0) or 0)>=55 or p.get('topic')=='Controversy']
 if search: out=[p for p in out if search.lower() in (p.get('wrestler','')+p.get('text','')+p.get('company','')+p.get('team_name','')).lower()]
 return out

def render_tweet_card(p,compact=False):
 w=find(p.get('wrestler','')) if p.get('poster_kind')!='team' else find(p.get('team_name',''))
 verified=' ✓' if w and (is_champ(w['name']) or w['popularity']>=88) else ''
 badges=[]
 if p.get('mega'): badges.append('🌐 BILLIONS+')
 elif p.get('viral'): badges.append('🔥 VIRAL')
 if int(p.get('controversy_score',0) or 0)>=55: badges.append('⚡ HOT')
 if p.get('ai_generated'): badges.append('AI')
 else: badges.append('Manual')
 badge_txt=' · '.join(badges)
 eng=f"👁 {format_social_num(p.get('views',0))} · ♡ {format_social_num(p.get('likes',0))} · ↻ {format_social_num(p.get('reposts',0))} · 💬 {format_social_num(p.get('replies',0))}"
 if compact:
  with st.container(border=True):
   h1,h2=st.columns([.14,.86])
   with h1: show_img(p.get('wrestler',''),52) if p.get('poster_kind')!='team' else show_champion_img(p.get('team_name',''),52)
   with h2:
    st.markdown(f"**{p.get('wrestler')}** <span class='tweet-handle'>{p.get('handle','')}{verified}</span> · {p.get('company')} · W{p.get('week')}",unsafe_allow_html=True)
    st.caption(f"{p.get('post_type')} · {badge_txt}")
    if p.get('reply_to_id') and p.get('reply_to_snippet'):
     st.markdown(f"<div class='tweet-handle'>↩ #{p.get('reply_to_id')}: \"{html_escape(p.get('reply_to_snippet',''))}\"</div>",unsafe_allow_html=True)
    st.markdown(f"<div class='tweet-body'>{html_escape(p.get('text',''))}</div>",unsafe_allow_html=True)
    st.markdown(f"<div class='tweet-eng'>{eng}</div>",unsafe_allow_html=True)
  return
 with bfg_card():
  c=st.columns([.12,.88])
  with c[0]:
   if p.get('poster_kind')=='team' and p.get('team_name'): show_champion_img(p['team_name'],65)
   else: show_img(p.get('wrestler',''),65)
  with c[1]:
   tw=find(p.get('team_name','')) if p.get('poster_kind')=='team' else None
   role=p.get('role','')
   if p.get('poster_kind')=='team':
    st.markdown(f"**{p.get('team_name',p.get('wrestler'))}** (legacy team post) · {p.get('company','')} · Week {p.get('week')} · {p.get('post_type')}")
    st.caption('Archived — new posts use individual wrestler accounts only.')
   else:
    st.markdown(f"**{p.get('wrestler')}** {p.get('handle','')}{verified} · {p.get('company','')} · {role} · Week {p.get('week')} · {p.get('post_type')}")
    if p.get('team_name'): st.caption(f"Tag team: {p['team_name']}")
    if w: st.caption(f"{align_badge_html(w['alignment'])} | Pop {w['popularity']} | Morale {w['morale']} | Mom {w['momentum']} | Fan {w.get('fan_support',50)} | Controversy {w.get('controversy_risk',0)} | Record {rec(w)}")
    if p.get('stat_changes'): st.caption('Effects: '+', '.join(f"{k} {v:+}" for k,v in p['stat_changes'].items()))
    if p.get('topic'): st.caption(f"Topic: {p.get('topic')} · Tone: {p.get('tone','—')}")
   if badges: st.caption(badge_txt)
   m1,m2,m3,m4=st.columns(4)
   m1.metric('Views',format_social_num(p.get('views',0)))
   m2.metric('Likes',format_social_num(p.get('likes',0)))
   m3.metric('Reposts',format_social_num(p.get('reposts',0)))
   m4.metric('Replies',format_social_num(p.get('replies',0)))
   if p.get('reply_to_id'):
    st.caption(f"↩ Reply to #{p.get('reply_to_id')}")
    if p.get('reply_to_snippet'):
     with st.container(border=True):
      st.caption('Replying to')
      st.markdown(f"*\"{p.get('reply_to_snippet')}\"*")
    if p.get('interaction'): st.caption(f"Style: {p.get('interaction').replace('_',' ')}")
   st.markdown(p.get('text',''))
   st.caption(eng)

def is_champ(n): return any(n==c for t in st.session_state.champions.values() for c in t.values())

def ticket_price_for_episode(episode,ple=False):
 ep=(episode or 'Weekly Show').strip()
 if ple or ep in ('PLE','Stadium Show','Crossover Event'): 
  if 'Stadium' in ep: return TICKET_PRICES['Stadium Show']
  if 'Crossover' in ep: return TICKET_PRICES['Crossover Event']
  return TICKET_PRICES['PLE']
 for k,price in TICKET_PRICES.items():
  if k.lower() in ep.lower(): return price
 return TICKET_PRICES['Weekly Show']

def calc_show_attendance(company,venue,rating,ple,episode,booked_names=None,viewership=0):
 """Attendance from rating, prestige, venue, heat, hometown, buzz — capped at capacity."""
 cap=max(1,int(venue.get('capacity',15000)))
 prof=st.session_state.company_profiles.setdefault(company,{})
 prestige=float(prof.get('prestige',85))/100
 r=float(rating or 7.0)
 fill=.34+r*.055+prestige*.07
 if ple or schedule_show_is_ple(episode) or 'Stadium' in (episode or ''): fill+=.12
 if 'Go-Home' in (episode or '') or 'go-home' in (episode or '').lower(): fill+=.04
 booked=booked_names or []
 city_l=(venue.get('city') or '').lower()
 for nm in booked:
  w=find(nm)
  if w and city_l and (w.get('hometown','') or w.get('from_location','') or '').lower() in city_l:
   fill+=.07; break
 pool=roster(company)
 if pool:
  fill+=min(.05,sum(w.get('twitter_buzz',0) for w in pool)/(len(pool)*1200))
 if booked:
  fill+=min(.06,max(rivalry_heat_for(n) for n in booked)/130)
 prev_vw=get_company_last_viewership(company)
 if viewership and prev_vw:
  fill+=min(.05,max(0,(viewership-prev_vw)/max(prev_vw,400000))*.1)
 fill=min(.97,max(.30,fill))
 return int(cap*fill)

def calc_ticket_revenue(attendance,venue,episode,ple=False):
 """Ticket Revenue = Attendance × Ticket Price × venue ticket multiplier."""
 att=max(0,int(attendance))
 price=ticket_price_for_episode(episode,ple)
 mult=float(venue.get('ticket_multiplier',1.0) or 1.0)
 return int(att*price*mult)

def ticket_rev(v,rating,ple=False,attendance=None,episode='Weekly Show'):
 """Legacy helper — prefer calc_ticket_revenue + calc_show_attendance."""
 if attendance is None:
  attendance=calc_show_attendance('NXT',v,rating,ple,episode)
 return calc_ticket_revenue(attendance,v,episode,ple)
def rivalry_heat_for(name):
 heats=[r.get('heat',0) for r in st.session_state.get('rivalries',[]) if name in r.get('wrestlers',[])]
 return max(heats) if heats else 0
def random_event_penalty(name):
 pen=0
 for ev in st.session_state.get('random_event_history',[])[:12]:
  if ev.get('target')==name and ev.get('status')=='unresolved':
   if 'Injury' in ev.get('event','') or 'DUI' in ev.get('event','') or 'Assault' in ev.get('event',''): pen+=6
   elif 'Missed Flight' in ev.get('event','') or 'Travel' in ev.get('event',''): pen+=3
   else: pen+=2
 return pen
def power_score(w):
 wr=w.get('wins',0); lr=w.get('losses',0); wrate=(wr/(wr+lr)) if (wr+lr) else .5
 streak_bonus=4 if str(w.get('streak','')).startswith('W') and len(w.get('streak',''))>1 else (2 if w.get('streak','')=='W1' else 0)
 streak_pen=-3 if str(w.get('streak','')).startswith('L') else 0
 return round(w['overall']*.14+w['popularity']*.12+w['momentum']*.12+w['morale']*.07+wrate*10+streak_bonus+streak_pen+(10 if is_champ(w['name']) else 0)+rivalry_heat_for(w['name'])*.08+w.get('twitter_buzz',0)*.05+w.get('fan_investment',50)*.07+w.get('last_show_boost',0)*.4+w.get('story_grade_boost',0)*.35+w.get('ple_boost',0)*.45-random_event_penalty(w['name'])-(15 if w['status']!='Active' else 0)-(8 if w.get('injury') else 0),2)
def apply_weekly_booking_boosts(matches,promos,featured,rating,ple,company,hometown,reasons):
 for w in st.session_state.roster:
  w['last_show_boost']=int(w.get('last_show_boost',0)*.4)
  w['story_grade_boost']=max(0,w.get('story_grade_boost',0)*.5)
  if w['company']==company: w['ple_boost']=max(0,w.get('ple_boost',0)-1)
 story_boost=round(float(rating)*.6,1)
 booked=set()
 for i,m in enumerate(matches):
  main=i==len(matches)-1; title=m.get('title','None')!='None' or m.get('stip')=='Title Match'
  parts=[x for x in m.get('participants',[]) if x!='None']; booked.update(parts); win=m.get('winner')
  for n in parts:
   w=find(n)
   if not w: continue
   boost=0; notes=[]
   if main: boost+=6; notes.append('main event placement')
   if title: boost+=4; notes.append('title match')
   if n==win and win not in ('None','NC','TBD'): boost+=3; notes.append('win on show')
   if n==featured: boost+=3; notes.append('featured star')
   if ple: w['ple_boost']=min(20,w.get('ple_boost',0)+5); notes.append('PLE performance')
   w['last_show_boost']=w.get('last_show_boost',0)+boost
   w['story_grade_boost']=story_boost
   w['fan_investment']=min(100,w.get('fan_investment',50)+boost//2+int(rating))
   if rating>=8: apply_wrestler_deltas(w,pop=(2,5),fan_support=(2,4))
   elif rating<6: apply_wrestler_deltas(w,pop=(-2,-4))
   if ple: apply_wrestler_deltas(w,pop=(5,12),mom=(3,6))
   reasons[n]='; '.join(notes) if notes else 'Booked on weekly show.'
 for p in promos:
  for n in p.get('participants',[]):
   if n=='None': continue
   w=find(n)
   if w:
    w['last_show_boost']=w.get('last_show_boost',0)+2
    w['fan_investment']=min(100,w.get('fan_investment',50)+1)
    pq=(2,6) if rating>=7.5 else ((-2,-5) if rating<6 else (0,2))
    apply_wrestler_deltas(w,pop=pq,morale=(1,3) if rating>=7 else (-2,0))
    reasons[n]=reasons.get(n,'')+' Promo importance boosted ranking.'.strip()
 for n in hometown:
  w=find(n)
  if not w: continue
  if n in booked:
   w['morale']=min(100,w['morale']+4); w['fan_investment']=min(100,w.get('fan_investment',50)+4)
   apply_wrestler_deltas(w,pop=(3,8),fan_support=(4,8),morale=(3,6))
   reasons[n]=reasons.get(n,'')+' Hometown hero moment boosted popularity.'
  else:
   w['fan_investment']=max(0,w.get('fan_investment',50)-3)
   reasons[n]=reasons.get(n,'')+' Hometown talent not booked — fan investment dipped.'
def update_rank(reasons=None):
 ensure_wrestler_debut_fields()
 reasons=reasons or {}; prev={r['name']:r['rank'] for r in st.session_state.power_rankings} if st.session_state.power_rankings else {}; rows=[]
 include_nd=st.session_state.get('rankings_include_not_debuted',False)
 for w in st.session_state.roster:
  if is_not_debuted(w) and not include_nd: continue
  rows.append({'name':w['name'],'company':w['company'],'overall':w['overall'],'record':rec(w),'score':power_score(w),'streak':w.get('streak',''),'photo':w['name'],'debut_status':w.get('debut_status','')})
 rows.sort(key=lambda x:x['score'], reverse=True)
 default_reason='Ranked by record, streak, booking, promos, titles, champion status, rivalry heat, Twitter, morale, momentum, popularity, fan investment, story grade, PLE, and events.'
 for i,r in enumerate(rows,1):
  r['rank']=i; r['last_rank']=prev.get(r['name'])
  if r['last_rank'] is None: r['movement']='NEW'
  elif r['last_rank']>i: r['movement']=f"↑{r['last_rank']-i}"
  elif r['last_rank']<i: r['movement']=f"↓{i-r['last_rank']}"
  else: r['movement']='—'
  r['reason']=reasons.get(r['name'],default_reason)
  w=find(r['name'])
  if w: w['rank']=i; w['power_score']=r['score']; w['rank_reason']=r['reason']
 st.session_state.previous_power_rankings=st.session_state.power_rankings
 st.session_state.power_rankings=rows
 st.session_state.power_ranking_history.append({'week':st.session_state.week,'rankings':rows[:30]})
def brand_filter_tabs(label='Brand',key='brand_filter',include_all=False):
 opts=PLAYABLE+(['All Brands'] if include_all else [])
 comp=st.radio(label,opts,horizontal=True,key=key)
 if comp!='All Brands':
  set_active_brand(comp)
  inject_brand_theme(comp)
 return comp
def rankings_for_brand(comp_filter):
 pool=sorted(st.session_state.power_rankings,key=lambda x:x['score'],reverse=True)
 if comp_filter!='All Brands': pool=[r for r in pool if r['company']==comp_filter]
 prev_pool=sorted(st.session_state.previous_power_rankings or [],key=lambda x:x['score'],reverse=True)
 if comp_filter!='All Brands': prev_pool=[r for r in prev_pool if r['company']==comp_filter]
 prev_map={r['name']:i for i,r in enumerate(prev_pool,1)}
 out=[]
 for i,r in enumerate(pool,1):
  row=dict(r); row['display_rank']=i; lr=prev_map.get(r['name']); row['display_last_rank']=lr if lr else '—'
  if lr is None: row['display_movement']='NEW'
  elif lr>i: row['display_movement']=f"↑{lr-i}"
  elif lr<i: row['display_movement']=f"↓{i-lr}"
  else: row['display_movement']='—'
  out.append(row)
 return out
def prev_rankings_for_brand(comp_filter):
 pool=sorted(st.session_state.previous_power_rankings or [],key=lambda x:x['score'],reverse=True)
 if comp_filter!='All Brands': pool=[r for r in pool if r['company']==comp_filter]
 out=[]
 for i,r in enumerate(pool,1):
  row=dict(r); row['display_rank']=i; row['display_last_rank']='—'; row['display_movement']='snapshot'; out.append(row)
 return out
def render_rank_row(r,compact=False):
 c1,c2=st.columns([.14,.86])
 with c1: show_img(r['name'],72 if not compact else 56)
 with c2:
  st.markdown(f"<div class='gm-card' style='margin-bottom:10px'><div style='font-size:18px;font-weight:900'>#{r.get('display_rank',r.get('rank'))} {r['name']}</div><div class='small-text'>{r['company']} · OVR {r['overall']} · Record {r['record']} · Score <b>{r['score']}</b></div><div class='small-text'>Last week: #{r.get('display_last_rank','—')} · Movement: <b>{r.get('display_movement',r.get('movement','—'))}</b></div><div style='margin-top:6px;color:#ddd'>{r.get('reason','')}</div></div>",unsafe_allow_html=True)

def format_promo_line(p):
 parts=[x for x in p.get('participants',[]) if x and x!='None']
 body=p.get('story','') or p.get('purpose','')
 return f"{p.get('label','Promo')}: {', '.join(parts) or 'TBD'} — {body}".strip()

def format_match_line(m):
 parts=[x for x in m.get('participants',[]) if x and x!='None']
 vs=' vs '.join(parts) if parts else 'TBD'
 win=m.get('winner','TBD')
 extra=f" | Winner: {win}" if win not in ('None',) else ''
 title=f" | {m['title']}" if m.get('title') not in (None,'None') else ''
 return f"{m.get('label','Match')}: {vs} | {m.get('stip','Normal')}{title}{extra}"

def build_show_story(long_story,opening,promos,matches,closing):
 lines=[x.strip() for x in [long_story,opening] if x and x.strip()]
 lines+=[format_promo_line(p) for p in promos]
 lines+=[format_match_line(m) for m in matches]
 if closing and closing.strip(): lines.append(closing.strip())
 return '\n\n'.join(lines)

def section_header(title, comp=None):
 comp=comp or st.session_state.get('active_brand','NXT')
 t=get_brand_tokens(comp)
 st.markdown(f'<div class="section-header" style="border-color:{t["hdr"]}">{html_escape(title)}</div>',unsafe_allow_html=True)

def render_brand_badge(comp):
 t=get_brand_tokens(comp)
 lore=(BRAND_THEMES.get(comp,{}) or {}).get('lore','')
 sub=(lore[:96]+'…') if len(lore)>96 else lore
 st.markdown(
  f"<div class='page-top-bar'><div class='brand-badge' style='--bb-glow:{t['glow']};--bb-accent:{t['accent']};--bb-border:{t['border']};--bb-muted:{t['muted']}'><span class='brand-badge-dot'></span>"
  f"<div><div class='brand-badge-name'>{html_escape(comp)}</div><div class='brand-badge-sub'>{html_escape(t.get('tagline',''))} · {html_escape(sub)}</div></div>"
  f"<span class='brand-badge-week'>Week {st.session_state.week}</span></div></div>",
  unsafe_allow_html=True,
 )

def render_kpi_row(items):
 cols=st.columns(len(items))
 for col,(label,val,sub) in zip(cols,items):
  sub_html=f"<div class='kpi-sub'>{html_escape(sub)}</div>" if sub else ''
  col.markdown(
   f"<div class='kpi-card'><div class='kpi-label'>{html_escape(label)}</div><div class='kpi-value'>{html_escape(str(val))}</div>{sub_html}</div>",
   unsafe_allow_html=True,
  )

def render_page_shell(title, comp=None, subtitle='', show_meter=True, meter_compact=False, use_brand_tabs=False, tabs_label='Select Brand', show_badge=True):
 comp=comp or st.session_state.get('active_brand','NXT')
 if not use_brand_tabs:
  inject_brand_theme(comp)
 if show_badge:
  render_brand_badge(comp)
 section_header(title, comp)
 if subtitle:
  st.markdown(f'<div class="page-subtitle">{html_escape(subtitle)}</div>',unsafe_allow_html=True)
 if use_brand_tabs:
  comp=brand_tabs(tabs_label)
  if show_meter:
   render_money_meter(comp,compact=meter_compact,show_ticker=not meter_compact,show_sponsor=not meter_compact)
  return comp
 if show_meter:
  render_money_meter(comp,compact=meter_compact,show_ticker=not meter_compact,show_sponsor=not meter_compact)
 render_brand_permission_banner(comp)
 if st.session_state.get('logged_in'):
  autosave.render_autosave_indicator('page_as')
 return comp

def render_title_bar():
 ensure_selector_css()
 st.markdown('<div class="game-title">BOUND FOR GLORY</div>',unsafe_allow_html=True)
 st.markdown('<div class="game-title-sm">GM MODE</div>',unsafe_allow_html=True)
 st.markdown('<div class="game-subtitle">NXT • SmackDown • WCW<br>Book Shows • Build Stars • Control the War</div>',unsafe_allow_html=True)

def _meter_theme(comp):
 t=get_brand_tokens(comp)
 return {'glow':t['glow'],'accent':t['accent'],'border':t['border']}

def financial_health_pct(current,starting=STARTING_BUDGET):
 return max(0,min(100,int(round(100*int(current)/max(1,int(starting))))))

def financial_health_tier(pct):
 if pct>=80: return 'Elite Financial Position','#2ecc71'
 if pct>=60: return 'Strong','#27ae60'
 if pct>=40: return 'Stable','#f1c40f'
 if pct>=20: return 'Danger Zone','#e67e22'
 return 'Critical','#e74c3c'

def get_company_ledger_recent(company,limit=5):
 return [t for t in st.session_state.get('finance_ledger',[]) if t.get('company')==company][:limit]

def sync_last_money_change_from_ledger(company):
 fin=st.session_state.company_finance.get(company)
 if not fin: return
 if fin.get('last_money_change'): return
 recent=get_company_ledger_recent(company,1)
 if recent:
  t=recent[0]
  fin['last_money_change']={'week':t.get('week'),'category':t.get('category'),'description':t.get('description'),'amount':t.get('amount'),'budget_before':t.get('budget_before'),'budget_after':t.get('budget_after'),'timestamp':t.get('timestamp','')}

def money_meter_toast(company,amount,category,description=''):
 if not amount: return
 if amount>0:
  if 'Savings' in category:
   st.toast(f"{company} saved {money(abs(amount))} — {category}")
  else:
   st.toast(f"{company} gained {money(abs(amount))} from {category}.")
 else:
  st.toast(f"{company} lost {money(abs(amount))} from {category}.")

def render_sponsor_savings_note(company):
 rules=COMPANY_LOGISTICS_RULES.get(company,{})
 fin=st.session_state.company_finance.get(company,{})
 if company=='SmackDown' and rules.get('hotel_sponsor'):
  base=LOGISTICS_BASE['hotel']
  st.caption(f"**Marriott Hotel Savings** — Base {money(base)} → Savings −{money(base)} → **Final $0**")
 elif company=='WCW' and rules.get('transport_sponsor'):
  base=LOGISTICS_BASE['transport']
  sp=rules.get('transport_sponsor','Tesla/Mercedes')
  st.caption(f"**{sp} Transportation Savings** — Base {money(base)} → Savings −{money(base)} → **Final $0**")
 elif company=='NXT':
  st.caption(f"**NXT media/merch revenue** (season): Appearances {money(fin.get('appearance_revenue_total',0))} · Media {money(fin.get('media_revenue_total',0))} · Merch {money(fin.get('merch_revenue_total',0))} — Netflix, Marvel, DC, Mattel, Olympics, SNL, GMA, Oscars, Hollywood")

def render_money_meter(company,compact=False,show_ticker=True,show_sponsor=True,show_health=True):
 """Live sports-style bank meter for one company."""
 ensure_finance_state()
 sync_last_money_change_from_ledger(company)
 fin=st.session_state.company_finance[company]
 th=_meter_theme(company)
 cur=int(fin.get('current_budget',0))
 start=int(fin.get('starting_budget',STARTING_BUDGET))
 pct=financial_health_pct(cur,start)
 tier_label,tier_color=financial_health_tier(pct)
 last=fin.get('last_money_change') or {}
 la=int(last.get('amount',0))
 lc_col='#2ecc71' if la>=0 else '#e74c3c'
 lc_arrow='▲' if la>0 else ('▼' if la<0 else '—')
 lc_sign='+' if la>0 else ('−' if la<0 else '')
 lc_cat=last.get('category','—')
 lc_txt=f"{lc_arrow} {lc_sign}{money(abs(la))} {lc_cat}" if la else '— No transactions yet'
 show_pl=int(fin.get('weekly_last_pl',0))
 season_pl=int(fin.get('season_profit_loss',0))
 sp_col='#2ecc71' if show_pl>=0 else '#e74c3c'
 sn_col='#2ecc71' if season_pl>=0 else '#e74c3c'
 bank_cls='money-meter-bank compact' if compact else 'money-meter-bank'
 st.markdown(
  f"<div class='money-meter-wrap' style='--mm-glow:{th['glow']};--mm-accent:{th['accent']};--mm-border:{th['border']}'><div class='money-meter-company'>{company} Current Bank</div>"
  f"<div class='{bank_cls}'>{money(cur)}</div>"
  f"<div class='money-meter-change' style='color:{lc_col}'>{lc_txt}</div>"
  f"<div class='money-meter-stat'>Last Show P/L: <span style='color:{sp_col}'>{'+' if show_pl>=0 else '−'}{money(abs(show_pl))}</span></div>"
  f"<div class='money-meter-stat'>Season P/L: <span style='color:{sn_col}'>{'+' if season_pl>=0 else '−'}{money(abs(season_pl))}</span></div>"
  f"<div class='money-meter-stat'>Financial Health: <b style='color:{tier_color}'>{pct}%</b> — {tier_label}</div></div>",
  unsafe_allow_html=True,
 )
 if show_health:
  st.progress(pct/100.0, text=f'Financial Health: {pct}% — {tier_label}')
 if show_sponsor:
  render_sponsor_savings_note(company)
 flash=st.session_state.get('money_meter_flash')
 if flash and flash[0].get('company')==company:
  f=flash[0]; amt=int(f.get('amount',0))
  cls='gain' if amt>=0 else 'loss'
  sign='+' if amt>=0 else '−'
  st.markdown(f"<div class='money-meter-flash {cls}'>{company} {sign}{money(abs(amt))} — {f.get('description','')}</div>",unsafe_allow_html=True)
 lh=next((h for h in reversed(st.session_state.get('weekly_history',[])) if h.get('company')==company),None)
 if lh:
  lg=lh.get('logistics') or {}
  sq=lg.get('show_quality',{})
  sell=sq.get('sellout_status') or lg.get('sellout_status')
  if not sell and lg.get('attendance'):
   cap=max(1,int(lh.get('capacity') or lg.get('capacity',15000)))
   sell,_=sellout_label(int(lg.get('attendance',0)),cap)
  if sell:
   st.caption(f"**Last show gate:** {sell} · {sq.get('capacity_pct', lg.get('capacity_filled_pct','—'))}% capacity · {sq.get('attendance_descriptor','')[:80]}")
 if show_ticker:
  recent=get_company_ledger_recent(company,5)
  if recent:
   st.markdown(f"**Recent Money Movement — {company}**")
   for i,t in enumerate(recent,1):
    amt=int(t.get('amount',0)); col='#2ecc71' if amt>=0 else '#e74c3c'; sign='+' if amt>=0 else '−'
    st.markdown(f"<div class='money-ticker-item'>{i}. Week {t.get('week')} | {t.get('category')} | <span style='color:{col}'>{sign}{money(abs(amt))}</span></div>",unsafe_allow_html=True)

def render_money_meter_multi():
 """Side-by-side meters for multiplayer dashboard."""
 ensure_finance_state()
 cols=st.columns(3)
 for i,comp in enumerate(PLAYABLE):
  wp=st.session_state.week_progress.get(comp,{})
  with cols[i]:
   render_money_meter(comp,compact=True,show_ticker=False,show_sponsor=False,show_health=False)
   st.caption(f"**Status:** {company_week_status_badge(comp)} · Week {st.session_state.week}")

def render_money_meter_hud():
 """Top HUD — active brand live bank + quick all-brand snapshot."""
 ensure_finance_state()
 ab=st.session_state.get('active_brand','NXT')
 render_money_meter(ab,compact=True,show_ticker=False,show_sponsor=False,show_health=True)
 c1,c2,c3,c4=st.columns(4)
 for col,co in zip((c1,c2,c3,c4),PLAYABLE):
  fin=st.session_state.company_finance[co]
  last=fin.get('last_money_change') or {}
  la=int(last.get('amount',0))
  lc_col='#2ecc71' if la>=0 else '#e74c3c'
  th=_meter_theme(co)
  hi='2px solid '+th['accent'] if co==ab else '1px solid '+th['border']
  glow='0 0 18px '+th['glow']+'66' if co==ab else '0 0 8px '+th['glow']+'22'
  col.markdown(
   f"<div class='top-card' style='border:{hi};box-shadow:{glow}'><div class='card-title'>{co} Bank</div>"
   f"<div class='card-number' style='color:{th['accent']}'>{money(fin.get('current_budget',0))}</div>"
   f"<div class='small-text' style='color:{lc_col}'>{('+' if la>0 else ('−' if la<0 else ''))+money(abs(la)) if la else '—'} last</div></div>",
   unsafe_allow_html=True,
  )

def render_finance_bar():
 render_money_meter_hud()

UNIVERSE_DATA_DIR=Path('data/universe')
UNIVERSE_FILE=UNIVERSE_DATA_DIR/'universe.json'
WEEK_STATE_FILE=UNIVERSE_DATA_DIR/'week_state.json'
PENDING_TRADES_FILE=UNIVERSE_DATA_DIR/'pending_trades.json'

def get_session_id():
 return (st.session_state.get('session_id') or '').strip() or 'local'

def session_storage_dir():
 sid=get_session_id()
 if sid and sid!='local':
  return mp.session_dir(sid)
 return UNIVERSE_DATA_DIR

def session_universe_file():
 return session_storage_dir()/'universe.json'

def session_week_state_file():
 return session_storage_dir()/'week_state.json'

def session_pending_trades_file():
 return session_storage_dir()/'pending_trades.json'

def attach_session_fields(record):
 if not isinstance(record,dict): return record
 record['session_id']=get_session_id()
 record.setdefault('last_updated_by',st.session_state.get('player_name',''))
 record.setdefault('last_updated_at',date.today().isoformat())
 return record
MP_WEEK_STATUSES=['Not Started','Draft Saved','Submitted','Completed','Locked']
TRADE_STATUSES=['Proposed','Accepted','Rejected','Admin Approved','Completed']

GM_ROLE_OPTIONS={
 'Admin (all brands)':('Admin','All'),
 'NXT GM':('NXT GM','NXT'),
 'SmackDown GM':('SmackDown GM','SmackDown'),
 'WCW GM':('WCW GM','WCW'),
}

def apply_player_session(player_name,role,company,session_id='',game_name='',invite_code=''):
 ensure_week_progress_state()
 st.session_state.logged_in=True
 st.session_state.player_name=player_name
 st.session_state.role=role
 st.session_state.assigned_company=company
 st.session_state.session_id=session_id or st.session_state.get('session_id') or 'local'
 st.session_state.game_name=game_name or st.session_state.get('game_name','')
 st.session_state.invite_code=invite_code or st.session_state.get('invite_code','')
 if company!='All':
  set_active_brand(company)
  st.session_state.player_assignments[company]=player_name
  st.session_state.week_progress.setdefault(company,default_week_progress()[company])
  st.session_state.week_progress[company]['gm_player']=player_name
 else:
  for c in PLAYABLE:
   st.session_state.player_assignments[c]=st.session_state.player_assignments.get(c) or '—'
 st.session_state._universe_loaded=False
 try:
  load_universe_from_disk()
 except Exception as ex:
  st.session_state._universe_loaded=True
  raise RuntimeError(f'Joined session but could not load save data: {ex}') from ex
 st.session_state._universe_loaded=True
 try:
  save_week_state()
 except Exception:
  pass

def ensure_multiplayer_state():
 if 'logged_in' not in st.session_state: st.session_state.logged_in=False
 if 'player_name' not in st.session_state: st.session_state.player_name=''
 if 'role' not in st.session_state: st.session_state.role=''
 if 'assigned_company' not in st.session_state: st.session_state.assigned_company=''
 if 'pending_trades' not in st.session_state: st.session_state.pending_trades=[]
 if 'mp_db_warning_shown' not in st.session_state: st.session_state.mp_db_warning_shown=False
 ensure_week_progress_state()
 if st.session_state.get('logged_in') and st.session_state.get('session_id'):
  sync_session_from_storage(light=True)

def is_admin():
 return st.session_state.get('role')=='Admin'

def can_edit_company(company):
 if is_admin(): return True
 ac=st.session_state.get('assigned_company')
 if ac=='All': return True
 return ac==company

def can_tweet_as_company(company):
 if is_admin(): return True
 return st.session_state.get('assigned_company')==company

def default_week_progress():
 return {c:{'status':'Not Started','gm_player':'','show_rating':None,'attendance':0,'viewership':0,'profit_loss':0,'locked':False,'draft_saved':False,'last_updated_by':'','last_updated_at':''} for c in PLAYABLE}

def ensure_week_progress_state():
 if 'week_progress' not in st.session_state:
  st.session_state.week_progress=default_week_progress()
 if 'player_assignments' not in st.session_state:
  st.session_state.player_assignments={c:'' for c in PLAYABLE}
 for c in PLAYABLE:
  st.session_state.week_progress.setdefault(c,default_week_progress()[c])

def get_assigned_gm_display(company):
 pa=st.session_state.get('player_assignments',{})
 return pa.get(company) or st.session_state.week_progress.get(company,{}).get('gm_player') or '—'

def render_brand_permission_banner(comp):
 if can_edit_company(comp):
  st.markdown('<span class="overall-badge">Editable ✅</span>',unsafe_allow_html=True)
 else:
  st.warning('View Only 🔒 — You can view this brand, but only the assigned GM or Admin can edit it.')
  st.caption(f'Controlled by **{get_assigned_gm_display(comp)}** ({comp} GM).')

def render_edit_only_notice(comp):
 if not can_edit_company(comp):
  st.info(f'View Only — controlled by {get_assigned_gm_display(comp)}.')

def touch_universe_meta(company=None):
 """Update save metadata only — call save_universe() separately to persist."""
 st.session_state.last_updated_by=st.session_state.get('player_name','')
 st.session_state.last_updated_at=date.today().isoformat()

def database_configured():
 return sb.supabase_configured() or mp.database_url_configured()

def supabase_cloud_active():
 return sb.supabase_configured()

def render_storage_status_banner(where='sidebar'):
 """Show Supabase connected or local testing mode."""
 if supabase_cloud_active():
  msg = 'Supabase connected — multiplayer saves active.'
  if where == 'sidebar':
   st.sidebar.success(msg)
  else:
   st.success(msg)
  return
 warn = '**Local testing mode** — saves stay on this server only. Add `SUPABASE_URL` and `SUPABASE_KEY` in Streamlit secrets for shared multiplayer.'
 if where == 'sidebar':
  st.sidebar.warning(warn)
 else:
  st.warning(warn)

def load_universe_from_disk():
 root=session_storage_dir()
 root.mkdir(parents=True,exist_ok=True)
 ufile=session_universe_file()
 wfile=session_week_state_file()
 pfile=session_pending_trades_file()
 sid=get_session_id()
 sb_uni=sb.load_merged_universe(sid) if sid!='local' and sb.supabase_configured() else None
 if sb_uni:
  for k,v in sb_uni.items():
   if k in ('last_updated_by','last_updated_at','session_id'): continue
   st.session_state[k]=v
 elif (db_uni:=mp.db_load_blob('mp_universe',sid) if sid!='local' else None):
  for k,v in db_uni.items():
   if k in ('last_updated_by','last_updated_at','session_id'): continue
   st.session_state[k]=v
 elif ufile.exists():
  try:
   data=json.loads(ufile.read_text(encoding='utf-8'))
  except (json.JSONDecodeError,OSError) as ex:
   st.error(f'Universe save file is corrupted or unreadable: {ex}')
   return
  if sid!='local' and data.get('session_id') and data.get('session_id')!=sid:
   st.error('Session mismatch — wrong universe file.'); return
  for k,v in data.items():
   if k in ('last_updated_by','last_updated_at','session_id'): continue
   st.session_state[k]=v
 if not sb_uni:
  db_ws=mp.db_load_blob('mp_week_state',sid) if sid!='local' else None
  if db_ws:
   st.session_state.week_progress=db_ws.get('companies',default_week_progress())
   st.session_state.player_assignments=db_ws.get('player_assignments',st.session_state.get('player_assignments',{c:'' for c in PLAYABLE}))
   if 'current_week' in db_ws: st.session_state.week=int(db_ws['current_week'])
  elif wfile.exists():
   try:
    ws=json.loads(wfile.read_text(encoding='utf-8'))
   except (json.JSONDecodeError,OSError):
    ws={}
   st.session_state.week_progress=ws.get('companies',default_week_progress())
   st.session_state.player_assignments=ws.get('player_assignments',st.session_state.player_assignments)
   if 'current_week' in ws: st.session_state.week=int(ws['current_week'])
 if not sb_uni:
  db_tr=mp.db_load_blob('mp_pending_trades',sid) if sid!='local' else None
  if db_tr is not None:
   st.session_state.pending_trades=db_tr
  elif pfile.exists():
   try:
    st.session_state.pending_trades=json.loads(pfile.read_text(encoding='utf-8'))
   except (json.JSONDecodeError,OSError):
    st.session_state.pending_trades=[]
 storylines.ensure_storyline_state()
 sponsor_obj.ensure_sponsor_objectives(COMPANIES)
 try:
  import bfg_book_show as book_show
  book_show.migrate_weekly_history_to_archive()
 except Exception:
  pass
 st.session_state._universe_loaded=True

def sync_session_from_storage(light=False):
 """Reload shared session data so friends see each other's progress."""
 if not st.session_state.get('logged_in'):
  return
 if not light:
  load_universe_from_disk()
  return
 if get_session_id()=='local':
  return
 sid=get_session_id()
 if sb.supabase_configured():
  lite=sb.load_light_session(sid)
  if lite:
   if lite.get('week_progress'): st.session_state.week_progress=lite['week_progress']
   if lite.get('player_assignments'): st.session_state.player_assignments=lite['player_assignments']
   if 'week' in lite: st.session_state.week=int(lite['week'])
   if lite.get('pending_trades') is not None: st.session_state.pending_trades=lite['pending_trades']
   return
 wfile=session_week_state_file()
 pfile=session_pending_trades_file()
 db_ws=mp.db_load_blob('mp_week_state',sid)
 if db_ws:
  st.session_state.week_progress=db_ws.get('companies',st.session_state.week_progress)
  st.session_state.player_assignments=db_ws.get('player_assignments',st.session_state.player_assignments)
  if 'current_week' in db_ws: st.session_state.week=int(db_ws['current_week'])
 elif wfile.exists():
  try:
   ws=json.loads(wfile.read_text(encoding='utf-8'))
  except (json.JSONDecodeError,OSError):
   ws={}
  st.session_state.week_progress=ws.get('companies',st.session_state.week_progress)
  st.session_state.player_assignments=ws.get('player_assignments',st.session_state.player_assignments)
  if 'current_week' in ws: st.session_state.week=int(ws['current_week'])
 db_tr=mp.db_load_blob('mp_pending_trades',sid)
 if db_tr is not None:
  st.session_state.pending_trades=db_tr
 elif pfile.exists():
  try:
   st.session_state.pending_trades=json.loads(pfile.read_text(encoding='utf-8'))
  except (json.JSONDecodeError,OSError):
   st.session_state.pending_trades=[]

def save_universe(data=None):
 autosave.set_autosave_status('saving')
 try:
  root=session_storage_dir()
  root.mkdir(parents=True,exist_ok=True)
  save_keys=_universe_save_keys()
  payload=data or {k:st.session_state[k] for k in save_keys if k in st.session_state}
  payload['session_id']=get_session_id()
  payload['game_name']=st.session_state.get('game_name','')
  payload['last_updated_by']=st.session_state.get('player_name','')
  payload['last_updated_at']=datetime.now().isoformat(timespec='seconds')
  session_universe_file().write_text(json.dumps(payload,indent=2,default=str),encoding='utf-8')
  sid=get_session_id()
  save_week_state()
  save_pending_trades()
  if sid!='local':
   mp.db_save_blob('mp_universe',sid,payload)
   if sb.supabase_configured():
    sb.sync_session_saves(sid,payload,week_state=load_week_state(),pending_trades=st.session_state.get('pending_trades',[]))
  if get_session_id()=='local' and st.session_state.get('logged_in') and not sb.supabase_configured():
   st.session_state.mp_show_local_warning=True
  autosave.set_autosave_status('saved')
 except Exception as ex:
  autosave.set_autosave_status('failed',str(ex))
  raise

def _universe_save_keys():
 return ['roster','champions','title_prestige','champion_meta','champion_history','title_defense_history','team_profiles','factions','bank','week','month','year','character_bible','staff_character_bible','company_lore','company_profiles','company_budgets','company_finance','finance_ledger','show_finance_reports','weekly_history','saved_show','booking_mode','ai_booked_show','show_user_edited','long_story_draft','book_show_drafts','book_show_archive','last_story_analysis','last_grade','story_parse','twitter_posts','schedule_calendar','calendar_locked','calendar_ai_notes','news_feed','random_event_history','storyline_flags','storylines','sponsor_objectives','twitter_drama','power_rankings','previous_power_rankings','power_ranking_history','yearly_attractions','attractions_locked','attraction_year','attraction_history','departed','staff','appearance_history','trade_history','rivalries','test_event_preview','tag_team_overrides','custom_tag_teams','roster_show_staff','breakup_history','former_tag_teams','film_projects','logistics_reports','cameo_library','debut_history','debut_warnings','rankings_include_not_debuted','confirmed_story_debuts','free_agency_pool','negotiation_history','contract_warnings','exclusive_activity_history','exclusive_generated_ideas','exclusive_violations','nxt_unfiltered_hosts','nxt_unfiltered_episodes','nxt_unfiltered_draft','last_nxt_unfiltered','podcast_hosts_booking_enabled','pending_trades','money_meter_flash','finance_opening_applied','weekly_performance_index','company_crisis','bidding_wars','brand_loyalty_history','descriptor_recent','twitter_recruitment_history','twitter_manual_gm_response','game_name','player_assignments','week_progress']

def load_universe():
 load_universe_from_disk()
 return True

def load_company(company):
 return {'roster':[w for w in st.session_state.roster if w.get('company')==company],'champions':st.session_state.champions.get(company,{}),'finance':st.session_state.company_finance.get(company,{}),'weekly_history':[h for h in st.session_state.weekly_history if h.get('company')==company]}

def save_company(company,data=None):
 data=data or {}
 if not can_edit_company(company) and not data.get('touch'): return False
 touch_universe_meta(company)
 save_universe()
 return True

def load_week_state():
 ensure_week_progress_state()
 return {'current_week':st.session_state.week,'companies':st.session_state.week_progress,'player_assignments':st.session_state.player_assignments}

def save_week_state(data=None):
 session_storage_dir().mkdir(parents=True,exist_ok=True)
 ws=data or load_week_state()
 ws['session_id']=get_session_id()
 ws['current_week']=int(st.session_state.week)
 ws['last_updated_by']=st.session_state.get('player_name','')
 ws['last_updated_at']=date.today().isoformat()
 session_week_state_file().write_text(json.dumps(ws,indent=2,default=str),encoding='utf-8')
 sid=get_session_id()
 if sid!='local':
  mp.db_save_blob('mp_week_state',sid,ws)

def save_show(company,week,show_data):
 hist=attach_session_fields(dict(show_data))
 hist['company']=company; hist['week']=int(week)
 if hist.get('performance'):
  st.session_state.setdefault('weekly_performance_index',{})
  st.session_state.weekly_performance_index[f"{company}:{int(week)}"]=hist['performance']
 st.session_state.weekly_history.append(hist)
 wp=st.session_state.week_progress[company]
 wp.update({'status':'Completed','locked':True,'show_rating':hist.get('final_rating') or hist.get('episode_rating'),'episode_rating':hist.get('episode_rating',hist.get('final_rating')),'attendance':int((hist.get('logistics') or {}).get('attendance',hist.get('viewership',0)//1.2) or 0),'viewership':int(hist.get('viewership',0)),'profit_loss':hist.get('profit',0),'dirt_sheet':(hist.get('dirt_sheet_review') or '')[:120],'gm_player':st.session_state.get('player_name',''),'last_updated_by':st.session_state.get('player_name',''),'last_updated_at':date.today().isoformat()})
 save_week_state(); save_universe()

def save_tweet(tweet_data):
 if not can_tweet_as_company(tweet_data.get('company')): return False
 attach_session_fields(tweet_data)
 st.session_state.twitter_posts.insert(0,tweet_data)
 save_universe(); return True

def save_trade_record(trade_data):
 attach_session_fields(trade_data)
 st.session_state.trade_history.insert(0,trade_data)
 save_universe()

def save_pending_trades():
 session_storage_dir().mkdir(parents=True,exist_ok=True)
 trades=st.session_state.get('pending_trades',[])
 session_pending_trades_file().write_text(json.dumps(trades,indent=2,default=str),encoding='utf-8')
 sid=get_session_id()
 if sid!='local':
  mp.db_save_blob('mp_pending_trades',sid,trades)

def mp_add_transaction(company,category,description,amount,week=None):
 if not can_edit_company(company): return None,None
 after,entry=add_transaction(company,category,description,amount,week)
 touch_universe_meta(company); save_universe(); return after,entry

def all_companies_week_completed():
 ensure_week_progress_state()
 return all(st.session_state.week_progress[c].get('status')=='Completed' for c in PLAYABLE)

def reset_week_progress_for_new_week():
 for c in PLAYABLE:
  st.session_state.week_progress[c]=default_week_progress()[c]
  st.session_state.week_progress[c]['gm_player']=st.session_state.player_assignments.get(c,'')

def company_show_locked(company):
 return bool(st.session_state.week_progress.get(company,{}).get('locked'))

def mark_company_draft_saved(company):
 if not can_edit_company(company): return
 wp=st.session_state.week_progress[company]
 wp['status']='Draft Saved'; wp['draft_saved']=True
 wp['last_updated_by']=st.session_state.get('player_name','')
 wp['last_updated_at']=date.today().isoformat()
 save_week_state()

def admin_unlock_company_week(company):
 if not is_admin(): return
 wp=st.session_state.week_progress[company]
 wp['locked']=False; wp['status']='Draft Saved'
 save_week_state(); st.toast(f'{company} week unlocked by Admin.')

def force_advance_shared_week():
 if not is_admin(): return False
 st.session_state.week+=1
 if st.session_state.week%4==0: st.session_state.month=min(12,st.session_state.month+1)
 if st.session_state.week%52==0: st.session_state.year+=1
 reset_week_progress_for_new_week()
 for c in PLAYABLE: advance_contracts_weekly(c)
 crisis_advance_universe_week()
 save_week_state(); save_universe()
 st.session_state.news_feed.insert(0,f"Commissioner advanced universe to Week {st.session_state.week}.")
 return True

def try_advance_shared_week_after_show():
 if not all_companies_week_completed(): return False
 st.session_state.week+=1
 if st.session_state.week%4==0: st.session_state.month=min(12,st.session_state.month+1)
 if st.session_state.week%52==0: st.session_state.year+=1
 reset_week_progress_for_new_week()
 for c in PLAYABLE: advance_contracts_weekly(c)
 crisis_advance_universe_week()
 save_week_state(); save_universe()
 st.session_state.news_feed.insert(0,f"All brands completed their shows — universe advanced to Week {st.session_state.week}.")
 return True

def execute_trade_transfer(rec):
 from_comp,to_comp=rec['from'],rec['to']
 offer,request,cash=rec.get('offer',[]),rec.get('request',[]),int(rec.get('cash',0))
 for n in offer:
  w=find(n)
  if w: w['company']=to_comp; w['morale']=max(0,w['morale']-2)
 for n in request:
  w=find(n)
  if w: w['company']=from_comp; w['morale']=min(100,w['morale']+2)
 if cash>0:
  mp_add_transaction(from_comp,'Trade Cash Sent',f"Trade cash to {to_comp}",-int(cash))
  mp_add_transaction(to_comp,'Trade Cash Received',f"Trade cash from {from_comp}",int(cash))
 rec['status']='Completed'
 save_trade_record(rec)
 save_universe()

def _render_join_private_game_form():
 with bfg_card('Join Private Game'):
  st.info('You need **two codes** from the host: **Invite code** (e.g. `BFG-6051`) and your **brand access code** (8 letters, e.g. `B7SUO2R8` for NXT). Do not put the invite code in both fields.')
  invite=st.text_input('Invite code',key='mp_join_invite',placeholder='BFG-6051')
  pname=st.text_input('Player name',key='mp_join_name',placeholder='Your GM name')
  access=st.text_input('Brand access code',key='mp_join_access',placeholder='NXT / SmackDown / WCW / Admin code (8 characters)')
  st.caption('Example — game **easywork**: invite `BFG-6051` · NXT `B7SUO2R8` · SmackDown `LPYRCDMN` · WCW `VAUK5RO7` · Admin `R0143DPK`')
  if st.button('Join private game',type='primary',use_container_width=True,key='mp_join_btn'):
   if not invite.strip() or not pname.strip() or not access.strip():
    st.error('Enter invite code, player name, and brand access code.')
   else:
    info,err=mp.join_private_session(invite,pname,access)
    if err:
     if 'Invite code not found' in err:
      st.error(err)
      st.warning('This invite only works on the **same server** where the game was created (this computer, or Streamlit Cloud with Supabase). If the host created the game elsewhere, ask them to share codes from that server.')
     elif 'Invalid access code' in err:
      st.error(err)
      st.warning('Use the **8-character brand code**, not the invite code. Invite goes in the first box only.')
     else:
      st.error(err)
    else:
     try:
      apply_player_session(info['player_name'],info['role'],info['assigned_company'],session_id=info['session_id'],game_name=info['game_name'],invite_code=info['invite_code'])
      st.session_state.pop('gate_login_tab',None)
      st.toast(f"Joined {info.get('game_name','game')} as {info['role']}")
      st.rerun()
     except Exception as ex:
      st.error(str(ex))

def render_login_screen():
 mp.init_storage()
 st.markdown('<div class="game-title">BOUND FOR GLORY</div>',unsafe_allow_html=True)
 st.markdown('<div class="game-title-sm">GM MODE</div>',unsafe_allow_html=True)
 st.markdown('<div class="game-subtitle">Welcome — private friend sessions · NXT · SmackDown · WCW</div>',unsafe_allow_html=True)
 render_storage_status_banner('page')
 codes=st.session_state.get('mp_created_codes')
 if codes:
  with bfg_card('Share these codes with your friends (save them now)'):
   st.write(f"**Game:** {codes.get('game_name')}")
   st.write(f"**Invite code:** `{codes.get('invite_code')}`")
   st.write(f"**Admin / Commissioner:** `{codes.get('admin_code')}`")
   st.write(f"**NXT GM:** `{codes.get('nxt_code')}`")
   st.write(f"**SmackDown GM:** `{codes.get('smackdown_code')}`")
   st.write(f"**WCW GM:** `{codes.get('wcw_code')}`")
   st.caption('Friends join with the **invite code** + their **role code**. Random players without these codes cannot enter your universe.')
   if st.button('Enter your universe as Admin',type='primary',key='mp_enter_created'):
    apply_player_session(codes.get('created_by','Admin'),'Admin','All',session_id=codes['session_id'],game_name=codes.get('game_name',''),invite_code=codes.get('invite_code',''))
    save_universe()
    st.session_state.pop('mp_created_codes',None)
    st.rerun()
  return
 c1,c2,c3=st.columns([1,1.35,1])
 with c2:
  if st.button('← Back to intro',key='login_back'):
   st.session_state.gate_screen='intro'
   st.rerun()
  join_first=int(st.session_state.get('gate_login_tab',0))==1
  if join_first:
   _render_join_private_game_form()
   if st.button('Create a game instead',key='login_switch_create'):
    st.session_state.gate_login_tab=0
    st.rerun()
  else:
   tab_create,tab_join=st.tabs(['Create Private Game','Join Private Game'])
   with tab_create:
    with bfg_card('Create Private Game'):
     gname=st.text_input('Game session name',key='mp_create_gname',placeholder='Joshua Universe')
     cname=st.text_input('Your name (Admin)',key='mp_create_admin',placeholder='Joshua')
     st.caption('Creates a private lobby. Share the invite + role codes with friends only.')
     if st.button('Create private game',type='primary',use_container_width=True,key='mp_create_btn'):
      if not gname.strip():
       st.error('Enter a game session name.')
      elif not cname.strip():
       st.error('Enter your name.')
      else:
       meta=mp.create_private_session(gname.strip(),cname.strip())
       st.session_state.mp_created_codes=meta
       st.rerun()
   with tab_join:
    _render_join_private_game_form()
  with st.expander('Solo test mode (no invite codes)'):
   name=st.text_input('Player Name','',key='mp_login_name',placeholder='Solo GM')
   role_pick=st.selectbox('Role',list(GM_ROLE_OPTIONS.keys()),key='mp_login_role')
   if st.button('Enter solo test universe',key='mp_login_btn'):
    if not name.strip():
     st.error('Enter a player name.')
    else:
     role,company=GM_ROLE_OPTIONS[role_pick]
     apply_player_session(name.strip(),role,company,session_id='local',game_name='Solo Test')
     st.rerun()

def render_multiplayer_sidebar():
 st.sidebar.markdown('---')
 st.sidebar.markdown('<div class="sb-section">PRIVATE SESSION</div>',unsafe_allow_html=True)
 if st.session_state.get('game_name'):
  st.sidebar.write(f"**Game:** {st.session_state.game_name}")
 if st.session_state.get('invite_code') and get_session_id()!='local':
  st.sidebar.write(f"**Invite:** `{st.session_state.invite_code}`")
 if get_session_id()!='local':
  st.sidebar.caption(f"Session `{get_session_id()[:8]}…`")
 st.sidebar.write(f"**Player:** {st.session_state.get('player_name','')}")
 st.sidebar.write(f"**Role:** {st.session_state.get('role','')}")
 st.sidebar.write(f"**Company:** {st.session_state.get('assigned_company','')}")
 if st.sidebar.button('Sync universe',key='mp_sync_btn',help='Reload week progress and trades from your private session'):
  sync_session_from_storage(light=False)
  st.toast('Universe synced from shared storage.')
  st.rerun()
 ac=st.session_state.get('assigned_company')
 if ac in PLAYABLE:
  st.sidebar.markdown('<span class="overall-badge">Editable ✅</span>',unsafe_allow_html=True)
 elif ac=='All':
  st.sidebar.markdown('<span class="overall-badge">Admin · All Brands</span>',unsafe_allow_html=True)
 else:
  st.sidebar.markdown('<span class="overall-badge">View Only 🔒</span>',unsafe_allow_html=True)
 render_storage_status_banner('sidebar')
 if st.sidebar.button('Logout',key='mp_logout'):
  for k in ['logged_in','player_name','role','assigned_company','mp_show_local_warning','_universe_loaded','session_id','game_name','invite_code','mp_created_codes']:
   st.session_state[k]=False if k=='logged_in' else ''
  st.session_state.assigned_company=''
  st.rerun()

def company_week_status_badge(company):
 s=st.session_state.week_progress.get(company,{}).get('status','Not Started')
 icons={'Completed':'Completed','Locked':'Locked','Submitted':'Submitted','Draft Saved':'Submitted','Not Started':'Not Started'}
 return s

def render_weekly_control_center():
 ui_pages.render_multiplayer_dashboard()

NAV_SECTIONS={
 'MAIN':['Dashboard','Multiplayer Dashboard','Company Home','Book Show','Schedule Calendar','Weekly Performance'],
 'ROSTER / STORY':['Roster','Champions','Rivalries','Storyline Tracker','Character Editor','Power Rankings','Free Agency'],
 'MEDIA / BUSINESS':['Twitter','NXT Unfiltered','NXT Spotlight Studio','SmackDown Culture Pulse','WCW Sports Desk','Appearances','Attractions','Sponsor Objectives','Trade Center','Finance','Contracts'],
 'TOOLS':['Random Event History','Picture Manager','Save Center','Commissioner Control Center','Season Awards'],
}
NAV_PAGES=[p for sec in NAV_SECTIONS.values() for p in sec]

def render_sidebar():
 if 'nav_page' not in st.session_state or st.session_state.nav_page not in NAV_PAGES:
  st.session_state.nav_page='Dashboard'
 if st.session_state.nav_page=='Commissioner Control Center' and not is_admin():
  st.session_state.nav_page='Dashboard'
 comp=st.session_state.get('active_brand','NXT')
 if comp not in PLAYABLE:
  comp='NXT'
 theme_comp=st.session_state.get('sidebar_brand',comp)
 if theme_comp not in PLAYABLE:
  theme_comp=comp
 st.sidebar.markdown(sidebar_theme(theme_comp),unsafe_allow_html=True)
 st.sidebar.markdown(
  '<div class="sb-header"><div class="sb-title">BOUND FOR GLORY</div>'
  '<div class="sb-title-sm">GM MODE</div>'
  '<div class="sb-sub">Book Shows · Build Stars · Control the War</div></div>',
  unsafe_allow_html=True,
 )
 st.sidebar.markdown('<div class="sb-company-label">ACTIVE BRAND</div>',unsafe_allow_html=True)
 picked=st.sidebar.radio('Company',PLAYABLE,index=PLAYABLE.index(comp),key='sidebar_brand',label_visibility='collapsed')
 st.session_state.active_brand=picked
 st.sidebar.markdown('---')
 clicked=None
 for section,pages in NAV_SECTIONS.items():
  st.sidebar.markdown(f'<div class="sb-section">{section}</div>',unsafe_allow_html=True)
  for label in pages:
   if label=='Commissioner Control Center' and not is_admin():
    continue
   active=st.session_state.nav_page==label
   if st.sidebar.button(label,key=f'sb_nav_{label}',use_container_width=True,type='primary' if active else 'secondary'):
    clicked=label
 if clicked:
  st.session_state.nav_page=clicked
  st.rerun()
 render_multiplayer_sidebar()
 return st.session_state.nav_page
def venue_selector(k):
 country=st.selectbox('Country', sorted(set(COUNTRIES+[v['country'] for v in VENUES])), key=k+'country')
 if country=='United States':
  venue_regs=sorted(set(v['region'] for v in VENUES if v['country']=='United States'))
  regs=sorted(set(US_STATES+venue_regs))
 else:
  regs=sorted(set(v['region'] for v in VENUES if v['country']==country)) or ['Custom Region']
 reg=st.selectbox('State/Region', regs, key=k+'reg')
 cities=sorted(set(v['city'] for v in VENUES if v['country']==country and v['region']==reg)) or ['Custom City']
 city=st.selectbox('City', cities, key=k+'city')
 vs=[v for v in VENUES if v['country']==country and v['region']==reg and v['city']==city]
 names=[v['venue'] for v in vs]+['Custom Venue']
 vn=st.selectbox('Arena/Stadium', names, key=k+'venue')
 if vn=='Custom Venue':
  return {'country':country,'region':reg,'city':city,'venue':st.text_input('Custom venue name','Custom Venue', key=k+'cv'),'capacity':st.number_input('Capacity',1000,150000,15000,key=k+'cap'),'type':st.selectbox('Type',['Arena','Stadium'],key=k+'type'),'rental_cost':st.number_input('Rental',0,10000000,400000,key=k+'rent'),'security_cost':st.number_input('Security',0,5000000,125000,key=k+'sec'),'travel_cost':st.number_input('Travel / Logistics',0,5000000,100000,key=k+'trv'),'travel_multiplier':st.number_input('Travel Multiplier',.5,3.0,1.1,key=k+'tm'),'ticket_multiplier':st.number_input('Ticket Multiplier',.5,3.0,1.0,key=k+'tick'),'market_bonus':st.number_input('Market Bonus',0,5000000,150000,key=k+'mb'),'prestige':st.slider('Prestige',1,10,5,key=k+'prest')}
 v=next(x for x in vs if x['venue']==vn); v=dict(v); v.setdefault('travel_cost',int(250000*v.get('travel_multiplier',1.1))); return v
def apply_record(w,result,tag=False,title=False):
 if result=='W':
  w['wins']+=1; w['singles_wins']+=0 if tag else 1; w['tag_wins']+=1 if tag else 0; w['title_wins']+=1 if title else 0
  w['momentum']=min(100,w['momentum']+4)
  apply_wrestler_deltas(w,pop=(8,15) if title else (3,8),mom=(3,6),fan_support=(2,5))
  n=int(w['streak'][1:])+1 if w.get('streak','').startswith('W') and w['streak'][1:].isdigit() else 1; w['streak']=f'W{n}'; w['last_result']='W'
 elif result=='L':
  w['losses']+=1; w['singles_losses']+=0 if tag else 1; w['tag_losses']+=1 if tag else 0; w['title_losses']+=1 if title else 0
  w['momentum']=max(0,w['momentum']-3); w['morale']=max(0,w['morale']-1)
  streak_l=int(w['streak'][1:]) if str(w.get('streak','')).startswith('L') and w['streak'][1:].isdigit() else 1
  apply_wrestler_deltas(w,pop=(-8,-3) if streak_l>=3 else (-3,-1),mom=(-3,-1),morale=(-2,0))
  n=int(w['streak'][1:])+1 if w.get('streak','').startswith('L') and w['streak'][1:].isdigit() else 1; w['streak']=f'L{n}'; w['last_result']='L'
 else:
  w['draws']+=1; w['last_result']='NC'; w['streak']='NC'
def match_is_tag(stip,participants):
 return stip in ('Tag Team','Six-Man Tag','Eight-Man Tag','Mixed Tag','WarGames','Anarchy in the Arena') or '&' in ' '.join(participants)
def apply_match_result(m,company=None,show_name='',rating=7,main_event=False):
 names=[x for x in m.get('participants',[]) if x and x!='None']; win=m.get('winner','None'); stip=m.get('stip','Normal'); title_name=m.get('title','None'); title_match=title_name!='None' or stip=='Title Match'
 tag=match_is_tag(stip,names)
 if company and title_match and title_name!='None':
  holder=st.session_state.champions.get(company,{}).get(title_name)
  if holder and (win==holder or (win in names and holder in names)):
   record_title_defense(company,title_name,holder,rating,show_name,main_event)
 for n in names:
  w=find(n)
  if not w: continue
  apply_record(w,'W' if n==win and win!='None' else ('L' if win!='None' else 'NC'),tag=tag,title=title_match)
  eff=MATCH_EFFECTS.get(stip,DEFAULT_MATCH_EFFECT)
  w['stamina']=max(0,w['stamina']-int(eff.get('stamina',2)))
  if random.random()<eff.get('injury',1)*.04: w['injury']=True; w['status']='Injured'
  if eff.get('viral',0)>1.2 and random.random()<.35: w['twitter_buzz']=min(100,w.get('twitter_buzz',0)+8); w['popularity']=min(100,w['popularity']+2)
def get_openai_api_key():
 key=os.getenv('OPENAI_API_KEY','')
 try: key=key or st.secrets.get('OPENAI_API_KEY','')
 except Exception: pass
 try:
  tts=st.secrets.get('tts',{})
  if isinstance(tts,dict): key=key or tts.get('api_key','')
 except Exception: pass
 try: key=key or (st.session_state.get('openai_api_key_override') or '')
 except Exception: pass
 key=(key or '').strip()
 if key.startswith('sk-your') or 'your-openai-api-key' in key: return ''
 return key

def render_openai_key_helper():
 """Let user paste a key for this session when .env / secrets are empty."""
 if get_openai_api_key():
  return
 with st.expander('Connect OpenAI API key (this session)',expanded=True):
  st.caption('Your key is stored only in this browser session (not saved to disk). For permanent setup, edit `.env` or `.streamlit/secrets.toml` and restart Streamlit.')
  pasted=st.text_input('OpenAI API key',type='password',key='openai_key_paste',placeholder='sk-...')
  c1,c2=st.columns(2)
  if c1.button('Use key for this session',key='openai_key_apply'):
   k=(pasted or '').strip()
   if not k.startswith('sk-'):
    st.error('Paste a valid key from https://platform.openai.com/api-keys (starts with sk-).')
   else:
    st.session_state.openai_api_key_override=k
    os.environ['OPENAI_API_KEY']=k
    st.success('Key applied — generate again. AI scripts and OpenAI TTS are enabled for this session.')
    st.rerun()
  if c2.button('Clear session key',key='openai_key_clear'):
   st.session_state.pop('openai_api_key_override',None)
   st.session_state.pop('openai_quota_exceeded',None)
   if os.environ.get('OPENAI_API_KEY','').startswith('sk-'):
    os.environ.pop('OPENAI_API_KEY',None)
   load_project_env()
   st.rerun()
  if st.session_state.get('openai_quota_exceeded'):
   if st.button('Retry AI after billing fix',key='openai_quota_retry'):
    st.session_state.openai_quota_exceeded=False
    st.rerun()
   st.info('**429 insufficient_quota** — OpenAI rejected the request for billing, not because the key is missing. Rule-based NXT Unfiltered / Twitter still generate offline.')
  st.markdown('**Permanent setup:** open `.env` in the project folder and set `OPENAI_API_KEY=sk-...` on one line (no quotes), then stop and restart Streamlit (`Ctrl+C`, then `python3 -m streamlit run app.py`).')

def builtin_ai_env_on():
 """Default ON — free built-in scripts unless .env sets BFG_BUILTIN_AI_ONLY=false."""
 return os.getenv('BFG_BUILTIN_AI_ONLY','true').lower() not in ('0','false','no','off')

def ensure_ai_mode_prefs():
 if builtin_ai_env_on() or st.session_state.get('openai_quota_exceeded'):
  st.session_state.bfg_force_builtin_ai=True
 elif 'bfg_force_builtin_ai' not in st.session_state:
  st.session_state.bfg_force_builtin_ai=False

def should_use_openai_ai():
 ensure_ai_mode_prefs()
 if builtin_ai_env_on(): return False
 if st.session_state.get('bfg_force_builtin_ai'): return False
 if st.session_state.get('openai_quota_exceeded'): return False
 return bool(get_openai_api_key())

def get_ai_status():
 ensure_ai_mode_prefs()
 key=get_openai_api_key()
 builtin=not should_use_openai_ai()
 if builtin:
  return {
   'ready':False,'mode':'builtin',
   'message':'Free mode — built-in scripts + Edge TTS (no OpenAI charges).',
   'help':'Set `BFG_BUILTIN_AI_ONLY=false` in `.env` and restart Streamlit when you want paid ChatGPT scripts again.',
  }
 if not key:
  return {
   'ready':False,'mode':'none',
   'message':'No OpenAI API key found.',
   'help':'Set `OPENAI_API_KEY=sk-...` in `.env` (see `.env.example`), or paste a key below. Built-in scripts work without a key.',
  }
 return {'ready':True,'mode':'openai','message':'OpenAI AI generation enabled.','help':''}

def format_ai_error(exc):
 """Turn OpenAI SDK errors into short, actionable messages."""
 raw=str(exc or '')
 low=raw.lower()
 if 'insufficient_quota' in low or ('429' in raw and 'quota' in low):
  try:
   st.session_state.openai_quota_exceeded=True
   st.session_state.bfg_force_builtin_ai=True
  except Exception: pass
  return (
   'OpenAI quota exceeded (billing). Your API key works, but the account has no remaining credits. '
   'Open https://platform.openai.com/account/billing to add a payment method or top up, then try again. '
   'This episode used the built-in rule-based script instead.'
  )
 if 'rate_limit' in low or '429' in raw:
  return 'OpenAI rate limit (too many requests). Wait a minute and try again, or use a smaller prompt.'
 if 'invalid_api_key' in low or 'incorrect api key' in low:
  return 'Invalid OpenAI API key. Check `.env` or paste a new key in Connect OpenAI API key.'
 if 'model' in low and ('not found' in low or 'does not exist' in low):
  return f'OpenAI model not available: {raw[:200]}. Set OPENAI_MODEL in `.env` (e.g. gpt-4o-mini).'
 return f'AI error: {raw[:400]}'

def ai(prompt,model=None,max_input=30000,max_output=14000,temperature=0.55):
 if not should_use_openai_ai(): return None
 key=get_openai_api_key()
 if not key: return None
 text=(prompt or '')[:max_input]
 model=model or os.getenv('OPENAI_MODEL','gpt-4.1-mini')
 temp=float(temperature)
 try:
  from openai import OpenAI
  client=OpenAI(api_key=key)
  try:
   resp=client.responses.create(model=model,input=text,temperature=temp,max_output_tokens=max_output)
   out=getattr(resp,'output_text',None) or ''
   if out and str(out).strip():
    st.session_state.openai_quota_exceeded=False
    return str(out).strip()
  except Exception as e:
   if 'insufficient_quota' in str(e).lower() or '429' in str(e):
    return 'AI error: ' + format_ai_error(e)
  chat=client.chat.completions.create(
   model=model,
   messages=[{'role':'user','content':text}],
   temperature=temp,
   max_tokens=max_output,
  )
  out=(chat.choices[0].message.content or '').strip()
  if out:
   st.session_state.openai_quota_exceeded=False
   return out
  return None
 except Exception as e:
  return 'AI error: ' + format_ai_error(e)
def char_profile(n):
 p=st.session_state.character_bible.get(n,{}); return f"{n}: {p.get('archetype','Custom')}. Voice: {p.get('promo','')}. Do: {', '.join(p.get('should_do',[]))}. Do not: {', '.join(p.get('should_not',[]))}."
TWITTER_TOPICS=['Wrestling Story','Rivalry','PLE Emotion','Creative Complaint','Card Complaint','Controversy','Other Company Comment','Sports','Movie/Show','Music/Award Show','Political/Controversy','Travel','Sponsor/Media','Hometown','Random Event Reaction','Champion Pride','Contract Drama','Injury Update','Trade Rumor','Debut Hype','Tag Team Drama','GM Authority','Fan Gratitude']
TWITTER_TONES=['angry','emotional','cocky','funny','cryptic','respectful','bitter','grateful','political','corporate','scared','exhausted','inspired','petty','savage','hopeful']
TWEET_PRESETS=[
 ('Post-show heat','Rivalry','savage','Rivalry Tweet'),('Creative frustration','Creative Complaint','bitter','Creative Complaint Tweet'),
 ('Champion flex','Champion Pride','cocky','Champion Tweet'),('City night','Hometown','grateful','Live From City Tweet'),
 ('Brand war','Other Company Comment','petty','Rival Brand Shade'),('Locker room leak','Wrestling Story','cryptic','Locker Room Drama Tweet'),
 ('Sponsor shout','Sponsor/Media','corporate','Sponsor Promotion Tweet'),('PLE aftermath','PLE Emotion','emotional','PLE Promotion Tweet'),
]
CONTROVERSY_SCENARIOS=[
 ('Locker room leak','Controversy','cryptic','Locker Room Drama Tweet'),('Creative mutiny','Creative Complaint','bitter','Creative Complaint Tweet'),
 ('Card revolt','Card Complaint','angry','Angry Tweet'),('Political refusal','Political/Controversy','political','Normal Tweet'),
 ('Public apology demand','Controversy','emotional','Normal Tweet'),('Sponsor scandal','Controversy','corporate','Sponsor Promotion Tweet'),
 ('Subtweet war','Controversy','petty','Cryptic Tweet'),('GM cover-up','Controversy','savage','GM Official Statement'),
 ('Injury cover-up','Controversy','scared','Injury Update Tweet'),('Trade tampering','Trade Rumor','cryptic','Contract Tease Tweet'),
]
TWEET_TYPE_HINTS={
 'Rivalry Tweet':('Rivalry','savage'),'Champion Tweet':('Champion Pride','cocky'),'Creative Complaint Tweet':('Creative Complaint','bitter'),
 'Locker Room Drama Tweet':('Controversy','cryptic'),'Cryptic Tweet':('Controversy','cryptic'),'Angry Tweet':('Controversy','angry'),
 'Positive Tweet':('Fan Gratitude','grateful'),'Win Streak Tweet':('Wrestling Story','cocky'),'Losing Streak Tweet':('Wrestling Story','bitter'),
 'Hometown Tweet':('Hometown','emotional'),'Travel Complaint Tweet':('Travel','exhausted'),'Contract Tease Tweet':('Contract Drama','cryptic'),
 'Injury Update Tweet':('Injury Update','scared'),'PLE Promotion Tweet':('PLE Emotion','emotional'),'Rival Brand Shade':('Other Company Comment','petty'),
 'GM Official Statement':('GM Authority','corporate'),'Owner Brand Statement':('GM Authority','cocky'),'Live From City Tweet':('Hometown','grateful'),
 'NBA Game Reaction':('Sports','funny'),'NFL Game Reaction':('Sports','funny'),'Netflix/Marvel/DC Reaction':('Movie/Show','cocky'),
 'Random Event Reaction':('Random Event Reaction','angry'),'Tag Partner Reply':('Tag Team Drama','emotional'),'Breakup Tease Tweet':('Tag Team Drama','bitter'),
 'Card Complaint Tweet':('Card Complaint','bitter'),'Company Shot Tweet':('Controversy','petty'),
}

def recent_tweets_for(name,n=5):
 return [p for p in st.session_state.twitter_posts if p.get('wrestler')==name or name in (p.get('mentions') or '')][:n]

def tweet_text_fingerprint(text):
 t=re.sub(r'\s+',' ',(text or '').strip().lower())
 t=re.sub(r'[^\w\s@#\'-]','',t)
 return hashlib.md5(t.encode('utf-8')).hexdigest()

def ensure_twitter_unique_registry():
 if 'twitter_text_hashes' not in st.session_state:
  st.session_state.twitter_text_hashes=set()
  for p in st.session_state.get('twitter_posts',[]):
   tx=(p.get('text') or '').strip()
   if len(tx)>6: st.session_state.twitter_text_hashes.add(tweet_text_fingerprint(tx))
 if 'twitter_force_ai' not in st.session_state:
  st.session_state.twitter_force_ai=True

def register_tweet_text(text):
 ensure_twitter_unique_registry()
 fp=tweet_text_fingerprint(text)
 st.session_state.twitter_text_hashes.add(fp)
 return fp

def is_duplicate_tweet(text):
 ensure_twitter_unique_registry()
 return tweet_text_fingerprint(text) in st.session_state.twitter_text_hashes

def recent_tweet_texts(limit=80):
 ensure_twitter_unique_registry()
 return [(p.get('text') or '').strip() for p in st.session_state.get('twitter_posts',[])[:limit] if (p.get('text') or '').strip()]

def twitter_ai_enabled():
 return bool(st.session_state.get('twitter_force_ai',True)) and should_use_openai_ai()

def ensure_unique_tweet(generate_fn,max_tries=32):
 """Never return duplicate text — procedural suffix as last resort."""
 for i in range(max_tries):
  raw=generate_fn(i)
  if not raw: continue
  t=str(raw).strip().replace('\n',' ')[:280]
  if len(t)<8: continue
  if not is_duplicate_tweet(t):
   register_tweet_text(t)
   return t
 base=(generate_fn(0) or 'New post').strip()[:240]
 for _ in range(8):
  t=f"{base} · W{st.session_state.week}-{random.randint(100000,999999999)}"[:280]
  if not is_duplicate_tweet(t):
   register_tweet_text(t)
   return t
 t=f"{base} · {random.randint(10**9,10**10-1)}"[:280]
 register_tweet_text(t)
 return t

def _tweet_slots(nm,comp,topic,tone,mention,ctx,w=None):
 other=ctx.get('other_brands',['SmackDown','WCW'])
 partner=ctx.get('partner','') or 'my partner'
 riv=mention or (random.choice(ctx.get('rivalries',['the feud'])) if ctx.get('rivalries') else 'the feud')
 ev=random.choice(ctx.get('unresolved',['backstage noise'])) if ctx.get('unresolved') else 'backstage noise'
 champ=random.choice(ctx.get('champions',['the title picture'])) if ctx.get('champions') else 'the title picture'
 last=ctx.get('last_show','last night')
 city=(last.split(' in ')[-1] if ' in ' in last else 'this city')
 rating=re.search(r'(\d+(?:\.\d+)?)/10',last)
 rating=rating.group(1) if rating else '7'
 rec_txt=rec(w) if w else '0-0'
 return {
  'nm':nm,'comp':comp,'topic':topic,'tone':tone,'mention':mention or riv,'riv':riv,'partner':partner,
  'week':st.session_state.week,'city':city,'champ':champ,'ev':ev,'last':last[:70],'rating':rating,'record':rec_txt,
  'stamp':random.randint(100000,999999999),'brand':(ctx.get('brand','') or '')[:40],
 }

def _expand_tweet_lines(slots,hooks,cores,closers):
 out=[]
 for h in hooks:
  for c in cores:
   for cl in closers:
    try:
     line=(h.format(**slots)+' '+c.format(**slots)+' '+cl.format(**slots)).strip()
     line=re.sub(r'\s+',' ',line)
     if 12<=len(line)<=280: out.append(line)
    except Exception: pass
 return out

def generate_procedural_tweet(nm,comp,topic,tone,mention,ctx,w=None):
 slots=_tweet_slots(nm,comp,topic,tone,mention,ctx,w)
 hooks=[
  'Week {week} on {comp}:','Honestly,','Real talk from {city}:','Before the timeline spins this —',
  'Not me being loud but','{nm} checking in:','Arena still ringing —','Hot take hour:',
  'If you were in the building','Road life, same standards:','Press will twist this —',
 ]
 closers=['— {nm}','— {nm} · #{stamp}','Book the follow-up. — {nm}','We move. — {nm}','Say less. — {nm}']
 cores_by_topic={
  'Rivalry':[
   '{mention} talked for days — then froze when the lights hit.','I do not owe {mention} peace, I owe them a receipt.',
   'Everyone quoting {mention} — nobody booking the rematch.','The feud is not Twitter fiction, it is personal.',
   '{riv} ends when someone admits what {last} cost us.',
  ],
  'Creative Complaint':[
   'Stop calling it a "angle" when it is just neglect.','My name on the poster means the story matters.',
   'Three weeks sideways — patience is not infinite.','Creative wants heat — give me motive, not montages.',
  ],
  'Controversy':[
   'I am not apologizing for what the crowd already saw.','Delete the clip — the reaction is archived.',
   '{mention} wants smoke? Good — I am not hiding.','Sources say the office is nervous. They should be.',
   'This is accountability, not a work.','The timeline is not the locker room — but both are loud today.',
  ],
  'Champion Pride':[
   '{champ} — and I am still the photo they use first.','Gold hits different when you defend it.',
   'Talk is free; the belt is not.','Champions do not ask permission to lead.',
  ],
  'PLE Emotion':[
   '{last} still sits in my chest. Worth it.','The crowd paid for honesty — we delivered.',
   'That finish will haunt {mention or riv} longer than me.','PLE nights rewrite careers.',
  ],
  'Wrestling Story':[
   '{comp} is not background noise this week.','Morale low, standards high — watch anyway.',
   '{mention} — see you where the story actually matters.','Record {record} — story still open.',
  ],
  'Tag Team Drama':[
   '{partner} and I built this in the dark.','Tag partners share targets, not always trust.',
   'Read between the lines on {partner}\'s last post.','Teams break when egos outrun receipts.',
  ],
  'Other Company Comment':[
   'Other brands can keep press releases — {comp} owns the night.',
   'I study other rosters for mistakes, not inspiration.',
  ],
  'Hometown':[
   '{city} raised me louder than this building.','Home crowds tell the truth first.',
   'Back where it started — still climbing.',
  ],
  'Fan Gratitude':[
   'You carried me when the match tried to break me.','This roster fights for you even when cameras are off.',
   'Thank you for caring when the story hurt.',
  ],
  'GM Authority':[
   'Decisions happen in the office — outcomes happen in the ring.','Fans deserve answers, not spin.',
  ],
 }
 if topic=='Other Company Comment':
  ob=random.choice(ctx.get('other_brands',['SmackDown','WCW']))
  cores_by_topic['Other Company Comment']=[
   f'{ob} can keep press releases — {comp} owns the conversation.',
   f'Cross-brand noise is loud; championships are louder.',
   f'I do not watch {ob} — I study their mistakes.',
  ]
 cores=cores_by_topic.get(topic,cores_by_topic['Wrestling Story'])
 if tone in ('cryptic','petty'):
  cores=[c.replace('—','…') for c in cores]+cores
 lines=_expand_tweet_lines(slots,hooks,cores,closers)
 if not lines:
  return f"Week {slots['week']}: {comp} story still cooking. — {nm}"
 return random.choice(lines)

def infer_topic_tone_from_type(typ,w=None):
 if typ in TWEET_TYPE_HINTS:
  t,tn=TWEET_TYPE_HINTS[typ]; return t,tn
 if w:
  if w.get('morale',50)<40: return 'Creative Complaint','bitter'
  if w.get('momentum',50)>75: return 'Wrestling Story','cocky'
  if is_champ(w['name']): return 'Champion Pride','cocky'
 return 'Wrestling Story','emotional'

def twitter_live_context(comp,w=None,mention=''):
 ctx={'week':st.session_state.week,'company':comp,'mention':mention,'other_brands':[c for c in PLAYABLE if c!=comp]}
 last=next((h for h in reversed(st.session_state.weekly_history) if h.get('company')==comp),None)
 if last:
  ctx['last_show']=f"{last.get('show_name','')} rating {last.get('episode_rating',last.get('final_rating','—'))}/10 in {last.get('city','')}"
 else: ctx['last_show']='no recent show'
 ctx['champions']=[f"{t}: {v}" for t,v in st.session_state.champions.get(comp,{}).items() if v and v not in ('Vacant','Place Holder')][:5]
 ctx['rivalries']=[r.get('name','') for r in st.session_state.rivalries if r.get('company',comp)==comp or 'company' not in r][:4]
 ctx['unresolved']=[e.get('event','') for e in st.session_state.random_event_history if e.get('status')=='unresolved' and e.get('company',comp)==comp][:4]
 ctx['flags']=[f.get('flag','') for f in st.session_state.get('storyline_flags',[]) if f.get('company',comp)==comp][:4]
 sched=get_scheduled_show(comp,next_bookable_week())
 ctx['upcoming']=f"Week {sched.get('week')} {sched.get('show_name','')} in {sched.get('city','')}" if sched else 'no locked week'
 ctx['brand']=BRAND_THEMES.get(comp,{}).get('lore','')[:160]
 if w:
  ctx['wrestler']=f"{w['name']} OVR {w['overall']} pop {w['popularity']} mom {w['momentum']} morale {w['morale']} record {rec(w)}"
  ctx['partner']=tag_team_for_wrestler(w['name'],comp) or ''
  ctx['profile']=char_profile(w['name'])[:220]
 return ctx

def pick_varied_fallback(nm,comp,topic,tone,typ,mention='',ctx=None,mode='original'):
 ctx=ctx or {}
 other=ctx.get('other_brands',['SmackDown','WCW'])
 partner=ctx.get('partner','')
 last=ctx.get('last_show','')
 riv=random.choice(ctx.get('rivalries',['the main feud'])) if ctx.get('rivalries') else 'the main feud'
 ev=random.choice(ctx.get('unresolved',['backstage tension'])) if ctx.get('unresolved') else ''
 champ=random.choice(ctx.get('champions',['the title scene'])) if ctx.get('champions') else 'gold'
 city=(last.split(' in ')[-1] if ' in ' in last else 'this city')
 bank={
  'Rivalry':[f"{mention or riv} talked all week — then folded when the lights hit. Pathetic. — {nm}",f"I don't do rematches for free. {mention or riv} owes me a receipt. — {nm}",f"Everyone saw what {mention or riv} did. I'm not pretending we're cool. — {nm}"],
  'Creative Complaint':[f"Stop booking fear and calling it 'story'. I want stakes, not montages. — {nm}",f"If my name is on the poster, put me in the story that matters. — {nm}",f"Three weeks of sideways angles — I'm done being patient. — {nm}"],
  'PLE Emotion':[f"My chest still hurts from last night. {last[:50]}. Worth every second. — {nm}",f"The crowd didn't pay to watch me quit — they paid to watch me fight. — {nm}",f"That finish will haunt {mention or 'someone'} longer than it haunts me. — {nm}"],
  'Champion Pride':[f"{champ} — and I'm still the one they photograph first. — {nm}",f"Gold looks different when you've actually defended it. — {nm}",f"Talk is cheap. The belt isn't. — {nm}"],
  'Other Company Comment':[f"{random.choice(other)} can keep their press releases. {comp} still owns the conversation. — {nm}",f"I don't watch other rosters — I study their mistakes. — {nm}",f"Cross-brand noise is loud. Championships are louder. — {nm}"],
  'Hometown':[f"{city} raised me louder than this building can hold. — {nm}",f"Home crowds don't lie — they either love you or they tell you the truth. — {nm}",f"Back where it started. Still climbing. — {nm}"],
  'Random Event Reaction':[f"{ev or 'Something broke backstage'} — and somehow I'm the headline? Fine. — {nm}",f"The rumors are half true. The other half will cost someone money. — {nm}",f"Universe chaos week: {comp} edition. — {nm}"],
  'Tag Team Drama':[f"{partner+' and I' if partner else 'We'} built this in the dark. Don't tweet like you were there. — {nm}",f"Tag partners don't share everything — but we share targets. — {nm}",f"If {partner or 'my partner'} posts again, read between the lines. — {nm}"],
  'Travel':[f"Airport. Delay. Still expected to main event. Cool. — {nm}",f"Another city, another hotel room, same pressure. — {nm}",f"My bag is packed; my patience isn't. — {nm}"],
  'Sports':[f"Game night in {city} — everybody's loud, everybody's emotional. Sounds familiar. — {nm}",f"Championship energy in the arena next door. We're not second place tonight. — {nm}"],
  'Movie/Show':[f"Red carpet season overlaps with road season. Multitasking champion. — {nm}",f"That premiere crowd? Same hunger as ours. — {nm}"],
  'Political/Controversy':[f"I won't perform in a place that asks me to shrink. — {nm}",f"Platforms matter. Silence is a choice. — {nm}"],
  'Sponsor/Media':[f"Partnerships pay bills — championships pay legacy. — {nm}",f"Cameras on, brand up, standards higher. — {nm}"],
  'GM Authority':[f"The office makes decisions. The ring settles them. — {nm}",f"Fans deserve answers this week — not spin. — {nm}"],
  'Fan Gratitude':[f"Y'all carried me when the match tried to break me. — {nm}",f"This roster fights for you even when you can't see it. — {nm}"],
  'Wrestling Story':[f"Week {st.session_state.week}: {comp} isn't background noise. — {nm}",f"{mention or riv} — see you where the story actually matters. — {nm}",f"Morale low, standards high. Watch anyway. — {nm}"],
  'Controversy':[f"I'm not apologizing for what everyone already saw. — {nm}",f"The edit made me look weak — that was a choice, not an accident. — {nm}",f"{mention or 'Someone'} wants smoke? Good. I'm not hiding. — {nm}",f"Sources close to me say the office is nervous. They're right. — {nm}",f"Delete the clip all you want — the crowd already reacted. — {nm}",f"This isn't 'heat' — this is accountability. — {nm}"],
  'Card Complaint':[f"My match wasn't the problem — the placement was. — {nm}",f"You don't put me third on the card and act surprised I'm loud. — {nm}",f"Book the story you promised or stop using my name. — {nm}"],
 }
 lines=bank.get(topic,bank['Wrestling Story'])
 if mode in ('reply','quote'):
  return pick_reply_fallback(nm,{'parent_text':ctx.get('parent_text',''),'parent_author':ctx.get('parent_author',mention or ''),'parent_handle':ctx.get('parent_handle','')},ctx.get('reply_style','Clap back'),topic,tone,mode)
 if mode=='reply' and mention: lines=[f"@{slug(mention).replace('@','')} — read that again. Slowly. — {nm}",f"You wanted a response. Here it is. — {nm}"]+lines
 if tone in ('cryptic','petty'): lines=[x.replace('—','…') for x in lines[:2]]+lines
 w=find(nm)
 def gen(attempt):
  if attempt%3!=2:
   return generate_procedural_tweet(nm,comp,topic,tone,mention,ctx,w)
  return random.choice(lines)
 return ensure_unique_tweet(gen)

def compute_tweet_effects(topic,tone,w,comp,mention=''):
 eff={'buzz':random.randint(2,8),'popularity':0,'morale':0,'momentum':0,'controversy':0,'fan_support':0,'sponsor':0,'locker':0,'rivalry':0}
 t=topic.lower(); tn=tone.lower()
 if 'ple' in t or 'emotional' in tn: eff.update({'popularity':(2,5),'fan_support':(3,6),'morale':(1,4)})
 if 'creative' in t or 'card' in t: eff.update({'controversy':(5,10),'morale':(-4,-1),'buzz':(4,10),'locker':(3,7)})
 if 'political' in t: eff.update({'controversy':(10,18),'sponsor':(-6,-2),'buzz':(6,12),'popularity':random.choice([(3,8),(-8,-3)])})
 if 'rivalry' in t: eff.update({'rivalry':(4,10),'momentum':(2,5),'buzz':(3,8)})
 if 'other company' in t: eff.update({'buzz':(4,9),'popularity':(1,4)})
 if 'sports' in t: eff.update({'buzz':(2,6),'popularity':(1,3)})
 if 'movie' in t or 'music' in t: eff.update({'popularity':(2,6),'buzz':(4,8)})
 if 'hometown' in t: eff.update({'fan_support':(3,7),'popularity':(2,5)})
 if 'travel' in t: eff.update({'stamina':(-4,-1),'morale':(-3,0)})
 if 'controversy' in t or 'card complaint' in t: eff.update({'controversy':(6,14),'buzz':(5,12),'popularity':random.choice([(2,6),(-6,-2)]),'sponsor':(-4,0)})
 if w and w.get('morale',50)<40 and 'angry' in tn: eff['morale']=(-2,1); eff['controversy']=(3,8)
 return eff

def sync_options_from_type(typ,w=None):
 """Map tweet type dropdown → topic + tone used for generation."""
 if typ in TWEET_TYPE_HINTS:
  return TWEET_TYPE_HINTS[typ]
 return infer_topic_tone_from_type(typ,w)

def build_tweet_extra(n,comp,w,eff,topic,tone,mode,**kw):
 extra=twitter_wrestler_extra(n,comp,**kw)
 extra.update({'effects':eff,'topic':topic,'tone':tone,'tweet_mode':mode,'wrestler_obj':w})
 return extra

REPLY_STYLES=['Clap back','Defend / co-sign','Sarcastic one-liner','Demand a rematch','Subtweet (no @)','Quote tweet dunk','Public denial','Agree & escalate','GM / office shutdown','Fan-style reaction','Ask what they meant','Petty ratio']
REPLY_STYLE_TOPICS={
 'Clap back':('Rivalry','savage'),'Defend / co-sign':('Wrestling Story','respectful'),'Sarcastic one-liner':('Wrestling Story','funny'),
 'Demand a rematch':('Rivalry','angry'),'Subtweet (no @)':('Controversy','cryptic'),'Quote tweet dunk':('Rivalry','petty'),
 'Public denial':('Controversy','corporate'),'Agree & escalate':('Rivalry','savage'),'GM / office shutdown':('GM Authority','corporate'),
 'Fan-style reaction':('Fan Gratitude','emotional'),'Ask what they meant':('Wrestling Story','cryptic'),'Petty ratio':('Controversy','petty'),
}

def parent_tweet_pack(parent):
 if not parent: return {}
 return {'parent_id':parent.get('id'),'parent_author':parent.get('wrestler',''),'parent_handle':parent.get('handle',''),
  'parent_text':parent.get('text',''),'parent_topic':parent.get('topic',''),'parent_type':parent.get('post_type',''),
  'parent_company':parent.get('company',''),'parent_viral':bool(parent.get('viral'))}

def pick_reply_fallback(nm,parent_ctx,reply_style,topic,tone,mode='reply'):
 author=parent_ctx.get('parent_author') or 'someone'
 pt=(parent_ctx.get('parent_text') or '').strip()
 snippet=(pt[:72]+'…') if len(pt)>72 else (pt or 'that take')
 at=f"@{slug(author).replace('_','')}" if author else ''
 style=(reply_style or 'Clap back').lower()
 quote_open=f'"{snippet}"' if pt else 'that post'
 if mode=='quote':
  banks={
   'default':[f"{quote_open} — and that's why {author or 'they'} stay loud online instead of in the ring. — {nm}",f"RT energy: {snippet} … couldn't have said it worse myself. — {nm}",f"Leaving this here so the timeline remembers who started it. — {nm}"],
  }
 else:
  banks={
   'clap':[f"{at} really typed \"{snippet}\" with a straight face? Bold. — {nm}",f"Read {at}'s post again. Still wrong. — {nm}",f"You wanted a response — here: prove it Friday. — {nm}"],
   'defend':[f"{at} is telling the truth and y'all are mad about it. — {nm}",f"Don't twist {at}'s words — I was in that building. — {nm}",f"Team {author}: we ride. — {nm}"],
   'sarcastic':[f"Wow. Revolutionary take from {at}. — {nm}",f"\"{snippet}\" — inspirational, truly. — {nm}",f"Someone give {at} a medal for courage on the keyboard. — {nm}"],
   'rematch':[f"{at} — stop tweeting, start booking the rematch. — {nm}",f"\"{snippet}\" Cool story. See you in the ring. — {nm}",f"You talk like that online, act different face-to-face. — {nm}"],
   'subtweet':[f"Certain people really said \"{snippet[:40]}…\" and thought we'd ignore it. — {nm}",f"Not naming names but that last post aged like milk. — {nm}",f"If the shoe fits, lace it and walk to the ring. — {nm}"],
   'deny':[f"That rumor isn't true. Full stop. — {nm}",f"I wasn't even in the building — check the footage. — {nm}",f"Fake narrative. Real receipts coming. — {nm}"],
   'escalate':[f"{at} is right AND it's worse than they said. — {nm}",f"\"{snippet}\" — now imagine saying it to my face. — {nm}",f"Keep talking. You're making my week easier. — {nm}"],
   'gm':[f"The company is aware of social posts. Business will be handled internally. — {nm}",f"Talent are entitled to opinions; decisions happen in the office. — {nm}",f"We don't book matches on Twitter — but we hear you. — {nm}"],
   'fan':[f"\"{snippet}\" — THIS is why I watch {parent_ctx.get('parent_company','')}. — {nm}",f"{author} said what we were all thinking. — {nm}",f"Timeline won tonight. — {nm}"],
   'ask':[f"{at} — clarify \"{snippet}\" before the interview crew asks. — {nm}",f"Genuine question: was that a shoot or a work? — {nm}",f"Which part of that post was the lie? — {nm}"],
   'petty':[f"Ratio incoming. \"{snippet}\" — delete it. — {nm}",f"{at} thought this was Twitter Hall of Fame material? — {nm}",f"Likes won't save that take. — {nm}"],
  }
 key='clap' if 'clap' in style or 'back' in style else 'defend' if 'defend' in style or 'co-sign' in style else 'sarcastic' if 'sarcastic' in style else 'rematch' if 'rematch' in style else 'subtweet' if 'sub' in style else 'deny' if 'denial' in style else 'escalate' if 'escalat' in style else 'gm' if 'gm' in style or 'shutdown' in style else 'fan' if 'fan' in style else 'ask' if 'meant' in style else 'petty' if 'petty' in style or 'ratio' in style else 'clap'
 if mode=='quote': lines=banks['default']
 else: lines=banks.get(key,banks['clap'])
 def gen(attempt):
  if attempt%2==0 and pt:
   snippet=(pt[:55]+'…') if len(pt)>55 else pt
   return f'{at} — re: "{snippet}" — not buying it. — {nm}' if mode!='quote' else f'"{snippet}" — worst take on the timeline. — {nm}'
  return random.choice(lines)
 return ensure_unique_tweet(gen)

def deep_tweet_generate(w,comp,topic,tone,mode='original',mention='',reply_context='',staff=None,typ='Normal Tweet',parent_post=None,reply_style=''):
 ensure_wrestler_stats()
 live=twitter_live_context(comp,w,mention)
 pp=parent_tweet_pack(parent_post) if parent_post else {}
 if pp:
  live.update(pp); live['reply_style']=reply_style
  if not mention: mention=pp.get('parent_author','')
 recent=recent_tweet_texts(50)
 nm=w['name'] if w else (staff['name'] if staff else comp)
 parent_line=''
 if pp.get('parent_text'):
  parent_line=f" PARENT POST by {pp.get('parent_author')} ({pp.get('parent_handle')}): \"{pp['parent_text'][:240]}\". Parent topic: {pp.get('parent_topic')}. Reply style: {reply_style or 'natural'}."
 ctx=f"Week {live['week']}. Brand {comp}: {live['brand']}. Topic {topic}. Tone {tone}. Tweet type {typ}. Mode {mode}. Mention {mention}.{parent_line} Extra context: {reply_context[:120]}. Last show: {live['last_show']}. Upcoming: {live['upcoming']}. Champions: {live['champions']}. Rivalries: {live['rivalries']}. Unresolved events: {live['unresolved']}. Flags: {live['flags']}. NEVER repeat or paraphrase these recent posts: {recent[:15]}."
 if w: ctx+=f" Wrestler: {live.get('wrestler','')}. Partner team: {live.get('partner','')}. Voice: {live.get('profile','')}."
 elif staff: ctx+=f" Staff {staff['name']} ({staff['role']}) voice {staff.get('style','')}."
 prompt=f"Write ONE brand-new under-280-char wrestling Twitter post. MUST match topic={topic}, tone={tone}, type={typ}. Sound like a real person — no generic hype, no repeated catchphrases. Use specific details from context. {ctx}"
 if topic=='Controversy' or 'Controversy' in topic: prompt+=' Make it controversial — receipts, leaks, call-outs, or public friction.'
 if mode=='reply':
  prompt+=f' Write a DIRECT REPLY on Twitter: react to the parent post, reference a specific line or claim from it, sound spontaneous (not a press release). You are {nm} replying to {pp.get("parent_author") or mention}.'
 if mode=='quote':
  prompt+=f' Write a QUOTE TWEET: embed the idea from the parent post ("{pp.get("parent_text","")[:100]}") then add your sharp opinion. You are {nm}.'
 if twitter_ai_enabled():
  for attempt in range(6):
   uniq=f" Unique batch {random.randint(10**9,10**10-1)} — wording must be totally fresh."
   out=ai(prompt+uniq,temperature=0.82+attempt*0.04,max_output=500)
   if out and not str(out).startswith('AI error') and len(out.strip())>12:
    t=out.strip().replace('\n',' ')[:280]
    if not is_duplicate_tweet(t):
     register_tweet_text(t)
     return t
 if mode in ('reply','quote'):
  return pick_reply_fallback(nm,pp or {'parent_text':reply_context,'parent_author':mention},reply_style,topic,tone,mode)
 return pick_varied_fallback(nm,comp,topic,tone,typ,mention,live,mode)

def tweet(w,typ,mention='',topic=None,tone=None,mode='original',reply_context=''):
 dt,tn=sync_options_from_type(typ,w)
 topic=topic or dt; tone=tone or tn
 return deep_tweet_generate(w,w['company'],topic,tone,mode,mention,reply_context,typ=typ)

def generate_poster_tweet(w,staff,comp,typ,topic,tone,mode,mention,reply_context='',force_options=True,parent_post=None,reply_style=''):
 if force_options and (not topic or not tone):
  dt,tn=sync_options_from_type(typ,w); topic=topic or dt; tone=tone or tn
 if reply_style and reply_style in REPLY_STYLE_TOPICS and mode in ('reply','quote'):
  tpc,tn=REPLY_STYLE_TOPICS[reply_style]; topic=topic or tpc; tone=tone or tn
 if w: return deep_tweet_generate(w,comp,topic,tone,mode,mention,reply_context,typ=typ,parent_post=parent_post,reply_style=reply_style)
 if staff: return deep_tweet_generate(None,comp,topic,tone,mode,mention,reply_context,staff=staff,typ=typ,parent_post=parent_post,reply_style=reply_style)
 return f"{comp}: week {st.session_state.week} — stay tuned."

def twitter_post_reply(comp,name,w,staff,parent,reply_style,topic='',tone='',as_quote=False):
 """Create a reply/quote post linked to parent."""
 if not parent: return None
 mode='quote' if as_quote else 'reply'
 typ='Quote Tweet' if as_quote else 'Reply Tweet'
 tpc,tone=REPLY_STYLE_TOPICS.get(reply_style,('Wrestling Story','emotional'))
 topic=topic or tpc; tone=tone or tn
 mention=parent.get('wrestler','')
 if w:
  eff=compute_tweet_effects(topic,tone,w,comp,mention)
  text=generate_poster_tweet(w,None,comp,typ,topic,tone,mode,mention,'',force_options=False,parent_post=parent,reply_style=reply_style)
  extra=build_tweet_extra(name,comp,w,eff,topic,tone,mode,ai_generated=twitter_ai_enabled(),reply_to_id=parent['id'],interaction=reply_style.lower().replace(' ','_'))
  return make_twitter_post(comp,'wrestler',name,'@'+slug(name).replace('_',''),'Wrestler',typ,text,mention,extra)
 if staff:
  eff={'buzz':random.randint(3,9)}
  text=generate_poster_tweet(None,staff,comp,typ,topic,tone,mode,mention,'',force_options=False,parent_post=parent,reply_style=reply_style)
  return make_twitter_post(comp,'staff',staff['name'],staff['handle'],staff['role'],typ,text,mention,{'ai_generated':twitter_ai_enabled(),'effects':eff,'topic':topic,'tone':tone,'tweet_mode':mode,'reply_to_id':parent['id'],'interaction':reply_style})
 return None

def queue_tw_compose_opts(topic,tone,typ):
 """Queue topic/tone/type for next run — must not set widget keys after widgets exist (all tabs run in one pass)."""
 st.session_state['_tw_pending_compose']={'topic':topic,'tone':tone,'typ':typ}

def apply_pending_tw_compose_opts():
 """Apply queued preset before widgets render — never touch widget keys after instantiate."""
 p=st.session_state.pop('_tw_pending_compose',None)
 if not p: return
 if p.get('topic') in TWITTER_TOPICS:
  st.session_state['_tw_default_topic']=p['topic']
 if p.get('tone') in TWITTER_TONES:
  st.session_state['_tw_default_tone']=p['tone']
 if p.get('typ'):
  st.session_state['_tw_default_typ']=p['typ']

def tw_select_defaults(fallback_topic,fallback_tone):
 """Safe defaults for Twitter compose widgets (avoids Streamlit session_state conflicts)."""
 t=st.session_state.pop('_tw_default_topic',None) or st.session_state.get('tw_topic') or fallback_topic
 tn=st.session_state.pop('_tw_default_tone',None) or st.session_state.get('tw_tone') or fallback_tone
 if t not in TWITTER_TOPICS: t=fallback_topic if fallback_topic in TWITTER_TOPICS else TWITTER_TOPICS[0]
 if tn not in TWITTER_TONES: tn=fallback_tone if fallback_tone in TWITTER_TONES else TWITTER_TONES[0]
 return t,tn

def generate_reply_pile_on(parent,comp,count=5):
 """Several wrestlers reply to the same parent — feels like a real timeline."""
 posts=[]
 author=parent.get('wrestler','')
 pool=[n for n in opts_twitter_wrestlers(comp) if n!=author]
 if not pool: return posts
 random.shuffle(pool)
 for name in pool[:count]:
  ww=find(name)
  if not ww: continue
  style=random.choice(REPLY_STYLES)
  p=twitter_post_reply(comp,name,ww,None,parent,style)
  if p: posts.append(p)
 return posts

def simulate_world_twitter_wave(per_brand=2):
 scenarios=[
  ('Rivalry','savage','Rivalry Tweet'),('Champion Pride','cocky','Champion Tweet'),('Random Event Reaction','angry','Locker Room Drama Tweet'),
  ('PLE Emotion','emotional','PLE Promotion Tweet'),('Creative Complaint','bitter','Creative Complaint Tweet'),('Other Company Comment','petty','Rival Brand Shade'),
  ('Hometown','grateful','Live From City Tweet'),('Sports','funny','NBA Game Reaction'),('Movie/Show','cocky','Netflix/Marvel/DC Reaction'),
 ]
 posts=[]
 for comp2 in PLAYABLE:
  pool=opts_twitter_wrestlers(comp2)
  if not pool: continue
  for name in random.sample(pool,min(per_brand,len(pool))):
   ww=find(name)
   if not ww: continue
   topic,tone,typ=random.choice(scenarios)
   mention=''
   if topic=='Rivalry':
    riv=[r for r in st.session_state.rivalries if name in r.get('wrestlers',[]) and (r.get('company',comp2)==comp2 or 'company' not in r)]
    if riv: mention=next((x for x in riv[0].get('wrestlers',[]) if x!=name),'')
   eff=compute_tweet_effects(topic,tone,ww,comp2,mention)
   text=generate_poster_tweet(ww,None,comp2,typ,topic,tone,'original',mention)
   extra=build_tweet_extra(name,comp2,ww,eff,topic,tone,'original',ai_generated=twitter_ai_enabled())
   posts.append(make_twitter_post(comp2,'wrestler',name,'@'+slug(name).replace('_',''),'Wrestler',typ,text,mention,extra))
  teams_done=set()
  for post in posts[-8:]:
   if post.get('company')!=comp2: continue
   tn=tag_team_for_wrestler(post.get('wrestler',''),comp2)
   if not tn or tn in teams_done or random.random()>=.55: continue
   mems=[m['name'] for m in team_members_for(find(tn),comp2)] if find(tn) else []
   pr=next((x for x in mems if x!=post.get('wrestler')),None)
   if not pr: continue
   teams_done.add(tn)
   text2=member_team_tweet(pr,tn,comp2,'Tag Partner Reply',post.get('wrestler',''),'member_support',reply_context=post.get('text','')[:100])
   eff2=compute_tweet_effects('Tag Team Drama','emotional',find(pr),comp2,post.get('wrestler',''))
   ex2=build_tweet_extra(pr,comp2,find(pr),eff2,'Tag Team Drama','emotional','reply',reply_to_id=post['id'],interaction='member_support',ai_generated=twitter_ai_enabled())
   posts.append(make_twitter_post(comp2,'wrestler',pr,'@'+slug(pr).replace('_',''),'Wrestler','Tag Partner Reply',text2,post.get('wrestler',''),ex2))
  if posts and random.random()<.4:
   seed=random.choice([p for p in posts if p.get('company')==comp2][-4:] or posts[-1:])
   posts.extend(generate_reply_pile_on(seed,comp2,random.randint(2,4)))
 return posts

def simulate_controversy_wave(comp,count=8):
 """Generate high-engagement controversial posts (views up to 2M)."""
 posts=[]
 pool=opts_twitter_wrestlers(comp)
 if not pool: return posts
 ranked=sorted(pool,key=lambda n:-(find(n) or {'controversy_risk':0}).get('controversy_risk',0))
 hot=ranked[:max(6,len(ranked)//2)] or pool
 for _ in range(count):
  name=random.choice(hot)
  ww=find(name)
  if not ww: continue
  _lbl,topic,tone,typ=random.choice(CONTROVERSY_SCENARIOS)
  mention=''
  if random.random()<.45:
   others=[x for x in pool if x!=name]
   if others: mention=random.choice(others)
  eff=compute_tweet_effects(topic,tone,ww,comp,mention)
  text=generate_poster_tweet(ww,None,comp,typ,topic,tone,'original',mention)
  extra=build_tweet_extra(name,comp,ww,eff,topic,tone,'original',ai_generated=twitter_ai_enabled())
  posts.append(make_twitter_post(comp,'wrestler',name,'@'+slug(name).replace('_',''),'Wrestler',typ,text,mention,extra))
 return posts

def simulate_mega_twitter_wave(comp,count=25):
 """Many unique posts for one brand — billions of possible lines via procedural mix."""
 ensure_twitter_unique_registry()
 posts=[]
 pool=opts_twitter_wrestlers(comp)
 if not pool: return posts
 keys=list(TWEET_TYPE_HINTS.keys())
 for _ in range(count):
  name=random.choice(pool)
  ww=find(name)
  if not ww: continue
  typ=random.choice(keys) if keys else 'Normal Tweet'
  topic,tone=sync_options_from_type(typ,ww)
  mention=''
  if topic=='Rivalry':
   riv=[r for r in st.session_state.rivalries if name in r.get('wrestlers',[])]
   if riv: mention=next((x for x in riv[0].get('wrestlers',[]) if x!=name),'')
  eff=compute_tweet_effects(topic,tone,ww,comp,mention)
  text=generate_poster_tweet(ww,None,comp,typ,topic,tone,'original',mention,force_options=False)
  posts.append(make_twitter_post(comp,'wrestler',name,'@'+slug(name).replace('_',''),'Wrestler',typ,text,mention,build_tweet_extra(name,comp,ww,eff,topic,tone,'original',ai_generated=twitter_ai_enabled())))
 return posts

GRADE_WEIGHTS={'story_continuity':.25,'emotion_fan':.20,'character_accuracy':.15,'rivalry_heat':.15,'champion_usage':.10,'match_promo_quality':.10,'business_venue':.05}
GRADE_WEIGHT_LABELS={'story_continuity':'Story Continuity','emotion_fan':'Emotion / Fan Investment','character_accuracy':'Character Accuracy','rivalry_heat':'Rivalry Heat','champion_usage':'Champion Usage','match_promo_quality':'Promo / Match Quality','business_venue':'Business / Venue Fit'}
PERFORMANCE_GRADE_LABELS={'story_continuity':'Story Continuity Grade','emotion_fan':'Emotion / Fan Investment Grade','character_accuracy':'Character Accuracy Grade','rivalry_heat':'Rivalry Heat Grade','champion_usage':'Champion Usage Grade','match_promo_quality':'Promo / Match Quality Grade','business_venue':'Business / Venue Fit Grade'}

def _grade_letter(score):
 return 'A+' if score>=9 else 'A' if score>=8 else 'B' if score>=7 else 'C' if score>=6 else 'D' if score>=5 else 'Disaster'

def booking_context_pack(company,venue,featured,rivalry,sched=None,week=None):
 wk=week or next_bookable_week()
 hist=[h for h in st.session_state.weekly_history if h.get('company')==company][-3:]
 last=hist[-1] if hist else {}
 champs=st.session_state.champions.get(company,{})
 rivals=[r for r in st.session_state.rivalries if r.get('company',company)==company or 'company' not in r][:5]
 tweets=st.session_state.twitter_posts[:8]
 unresolved=[e for e in st.session_state.random_event_history if e.get('status')=='unresolved' and e.get('company',company)==company][:6]
 apps=st.session_state.appearance_history[:5]
 top10=st.session_state.power_rankings[:10]
 roster_snip=', '.join(f"{w['name']}({w['momentum']}m)" for w in sorted(roster(company),key=lambda x:-x['momentum'])[:12])
 return {
  'week':wk,'company':company,'venue':venue,'featured':featured,'rivalry':rivalry,'sched':sched,
  'last_show':last,'history':hist,'champions':champs,'rivals':rivals,'tweets':tweets,
  'unresolved':unresolved,'appearances':apps,'rankings':top10,'roster':roster_snip,
  'lore':st.session_state.company_lore.get(company,BRAND_THEMES[company]['lore']),
 }

def official_rating_enabled():
 return not (st.session_state.get('ai_booked_show') and not st.session_state.get('show_user_edited'))

def grade_story(text,featured,rivalry,venue,ple,company='NXT',matches=None,promos=None,sched=None,mode='Structured'):
 low=(text or '').lower(); matches=matches or []; promos=promos or []
 fb={'summary':'','worked':[],'struggled':[],'made_sense':[],'no_sense':[],'in_character':[],'off_character':[],'continued':[],'dropped':[],'fans_care':[],'fans_skip':[],'emotion_hit':[],'emotion_miss':[],'venue_fit':'','hometown':'','next_week':'','tweet':'','twitter_fallout':[],'story_impact':'','attendance_impact':'','viewership_impact':'','money_impact':'','attraction':'','appearance':'','logistics':'','champion_notes':[],'rivalry_notes':[],'pacing_notes':[]}
 scores={'story_continuity':5.5,'emotion_fan':5.5,'character_accuracy':6.0,'rivalry_heat':5.5,'champion_usage':5.5,'match_promo_quality':6.0,'pacing':6.0,'business_venue':6.0}
 struct_pts=sum(.35 for wd in ['opening','promo','match','main event','closing','segment','backstage'] if wd in low)
 scores['pacing']+=min(2.5,struct_pts)
 scores['match_promo_quality']+=min(2,len(matches)*.35+len(promos)*.25)
 emo_kw=['attack','betray','challenge','revenge','personal','blood','contract','interference','title','stolen','cried','angry','family','hometown','crowd','chant']
 emo_hits=sum(1 for w in emo_kw if w in low)
 scores['emotion_fan']+=min(3,emo_hits*.35)
 if emo_hits>=4: fb['emotion_hit'].append('Emotional stakes (anger, revenge, title obsession, or crowd reaction) are present.')
 else: fb['emotion_miss'].append('Add a clearer emotional hook — betrayal, revenge, hometown pop, or championship obsession.')
 hist=[h for h in st.session_state.weekly_history if h.get('company')==company]
 if hist:
  last=hist[-1]
  if last.get('featured_star') and str(last['featured_star']).lower() in low:
   scores['story_continuity']+=1.8; fb['continued'].append(f"{last['featured_star']} continued from last week.")
  else:
   scores['story_continuity']-=1.2; fb['dropped'].append(f"Last week's featured star ({last.get('featured_star','')}) was not followed up.")
  if last.get('top_rivalry') and str(last['top_rivalry']).lower() not in ('none','') and str(last['top_rivalry']).lower() in low:
   scores['story_continuity']+=1.5; scores['rivalry_heat']+=1.5; fb['continued'].append(f"Rivalry '{last['top_rivalry']}' advanced.")
  elif rivalry and str(rivalry).lower() not in ('none','') and str(rivalry).lower() in low:
   scores['rivalry_heat']+=1.2; fb['continued'].append(f"Planned rivalry '{rivalry}' is on the show.")
  else:
   scores['story_continuity']-=1; scores['rivalry_heat']-=1; fb['dropped'].append('Top rivalry from last week was not advanced.')
 else:
  fb['continued'].append('First show or no prior week for this brand — continuity baseline applied.')
 for ev in st.session_state.get('random_event_history',[]):
  if ev.get('status')=='unresolved' and ev.get('company',company)==company:
   if ev.get('event','').lower() in low:
    scores['story_continuity']+=1; fb['continued'].append(f"Unresolved random event followed up: {ev['event']}.")
   else:
    fb['dropped'].append(f"Unresolved event not addressed: {ev.get('event')} ({ev.get('target','')}).")
 for td in st.session_state.get('twitter_drama',[])[:8]:
  if td.get('unresolved') and td.get('company')==company:
   if td.get('wrestler','').lower() in low: scores['story_continuity']+=.8; fb['continued'].append(f"Twitter drama followed up: {td.get('wrestler')}.")
   else: fb['dropped'].append(f"Major tweet drama ignored: {td.get('wrestler')} — {td.get('text','')[:60]}")
 for sf in st.session_state.get('storyline_flags',[])[:10]:
  if sf.get('unresolved') and sf.get('company')==company and sf.get('target','').lower() in low:
   scores['story_continuity']+=.5; fb['continued'].append(f"Storyline flag addressed: {sf.get('flag')}.")
 if featured and featured in st.session_state.character_bible:
  p=st.session_state.character_bible[featured]; hits=sum(1 for x in p.get('should_do',[]) if x and x.lower() in low)
  scores['character_accuracy']+=min(2,hits*.45)
  if hits>=2: fb['in_character'].append(f'{featured} sounded accurate to Character Editor ({p.get("archetype","")}).')
  else: fb['off_character'].append(f'{featured} could lean harder into promo style and should/should-not rules.')
 for n in roster(company):
  if n['name'].lower() in low and is_champ(n['name']):
   scores['champion_usage']+=.8; fb['champion_notes'].append(f"Champion {n['name']} appeared on the card.")
 if not fb['champion_notes']: fb['champion_notes'].append('Champions were underused or absent — title prestige may drop.')
 if rivalry and str(rivalry).lower() not in ('none',''):
  if str(rivalry).lower() in low: scores['rivalry_heat']+=1.5; fb['rivalry_notes'].append(f'Rivalry "{rivalry}" had screen time.')
  else: scores['rivalry_heat']-=1; fb['rivalry_notes'].append(f'Rivalry "{rivalry}" was planned but barely used.')
 if any(x in low for x in ['random','filler','squash']) and emo_hits<2:
  scores['match_promo_quality']-=1.2; fb['struggled'].append('Matches feel random without story reason.')
 if 'closing' in low or 'cliffhanger' in low or 'next week' in low:
  scores['pacing']+=.8; fb['worked'].append('Closing angle or next-week hook exists.')
 else:
  fb['struggled'].append('Weak or missing closing hook for next week.')
 scores['business_venue']+=min(2,venue.get('prestige',5)*.2)
 if ple:
  scores['business_venue']+=.4; scores['emotion_fan']+=.3
  title_hits=sum(1 for m in matches if m.get('title') not in (None,'None') or m.get('stip')=='Title Match')
  if title_hits<1: scores['champion_usage']-=1.5; fb['struggled'].append('PLE lacked a meaningful title match — prestige cannot score high.')
  if emo_hits<3: scores['emotion_fan']-=1.2; fb['struggled'].append('PLE needs stronger emotional payoff — not enough stakes landed.')
  if 'closing' not in low and 'cliffhanger' not in low: scores['pacing']-=1; fb['struggled'].append('PLE ending felt flat — consequences for next week are weak.')
  if any(x in low for x in ['random','filler','squash']) and emo_hits<3:
   scores['match_promo_quality']-=2; scores['story_continuity']-=1.5; fb['no_sense'].append('PLE had random matches with no story — graded harder than a weekly show.')
  if title_hits>=1 and emo_hits>=3: fb['fans_care'].append('PLE delivered title stakes and emotional payoff.')
  else: fb['fans_care'].append('PLE stakes present but payoff was incomplete.')
 else:
  fb['fans_care'].append('Weekly show focused on continuation and next-week hooks.')
 if sched and sched.get('hometown'):
  ht=', '.join(sched['hometown'])
  if any(h.lower() in low for h in sched['hometown']): scores['business_venue']+=1; fb['hometown']=f'Hometown talent ({ht}) used in {venue.get("city","")}.'
  else: fb['struggled'].append(f'Hometown wrestlers ({ht}) were scheduled but not spotlighted in {sched.get("city","")}.')
 if company=='NXT' and any(x in low for x in ['netflix','marvel','oscar','olympic','hollywood','snl','gma']): scores['story_continuity']+=.4; fb['made_sense'].append('NXT entertainment lane referenced logically.')
 if company=='SmackDown' and any(x in low for x in ['grammy','music','celebrity','paramount']): scores['story_continuity']+=.4
 if company=='WCW' and any(x in low for x in ['espn','nba','nfl','draft','halftime','sports']): scores['story_continuity']+=.4
 if venue.get('prestige',0)>=9 and emo_hits<3: fb['no_sense'].append(f'{venue.get("venue")} is a major arena — story heat may be too low for sellout.')
 if len(matches)>=6 and emo_hits<3: fb['pacing_notes'].append('Card may be too crowded without enough emotional breathing room.')
 for m in matches:
  if m.get('winner') in ('None','TBD'): fb['struggled'].append(f"Winner unclear for {m.get('label','match')} — hurts logic.")
 if not fb['worked']: fb['worked'].append('Show has basic structure and forward momentum.')
 if not fb['struggled']: fb['struggled'].append('Tighten dropped threads and sharpen the main-event emotional payoff.')
 if not fb['made_sense']: fb['made_sense'].append('Core angles follow wrestling logic (motivation → conflict → consequence).')
 fb['venue_fit']='Excellent market/arena fit.' if venue.get('prestige',0)>=8 else 'Venue works but needs more city-specific crowd emotion.'
 fb['next_week']=f"Escalate {rivalry or featured or 'the top feud'} with a contract segment, title stipulation, or GM announcement."
 fb['tweet']=f"Post-show Twitter: {featured or 'top star'} should mock, threaten, or celebrate with a hometown/rivalry angle."
 fb['twitter_fallout']=[fb['tweet'],'Tag partners or rivals in quote tweets if heat is high.']
 fb['story_impact']='Main rivalry heat should rise.' if scores['rivalry_heat']>=7 else 'Story heat is flat — rankings may stall.'
 fb['attendance_impact']='Attendance should improve next week if emotion landed.' if scores['emotion_fan']>=7 else 'Attendance may dip without stronger fan investment.'
 fb['viewership_impact']='Viewership should rise with cliffhanger and continuity.' if scores['story_continuity']>=7 else 'Viewership risk if stories feel dropped.'
 est_r=7.5 if ple else 7.0
 log=compute_show_logistics(company,venue,matches,promos,est_r,ple,schedule_to_episode_type(sched.get('show_type','Weekly Show')) if sched else 'Weekly Show','')
 fb['money_impact']=f"Projected profit/loss {money(log.get('profit_loss',0))} — story quality affects merch/ticket ceiling."
 fb['attraction']='Spa/Massage if stamina low; Media Tour if sponsors need hype.'
 fb['appearance']=APPEARANCE_LANES.get(company,['Media'])[0]
 lr=COMPANY_LOGISTICS_RULES.get(company,{})
 fb['logistics']=f"{lr.get('hotel_note','')} {lr.get('transport_note','')}"
 for k in scores: scores[k]=max(1,min(10,round(scores[k],1)))
 wsum=sum(GRADE_WEIGHTS.values())
 final=round(sum(scores[k]*GRADE_WEIGHTS[k] for k in GRADE_WEIGHTS)/wsum,1)
 if ple:
  if final>=8.5: final=min(10,final)
  elif final>=7: final=round(final-.15,1)
  else: final=round(final-.35,1)
 final=max(1,min(10,final))
 grade=_grade_letter(final)
 breakdown={GRADE_WEIGHT_LABELS.get(k,k.replace('_',' ').title()):scores[k] for k in GRADE_WEIGHTS}
 fb['summary']=f"Story-forward grade: continuity and emotion drive the score. Final {final}/10."
 notes=fb['continued'][:2]+fb['worked'][:2]+fb['struggled'][:1]+[fb['next_week']]
 return final,grade,notes,fb,breakdown

def enrich_grade_with_ai(base_result,ctx,text):
 rating,grade,notes,fb,breakdown=base_result
 prompt=f"""You are a senior wrestling creative analyst (ChatGPT/Claude style). Grade this {ctx['company']} TV show for Bound For Glory GM Mode.
Week {ctx['week']}. Venue: {ctx['venue'].get('venue')} in {ctx['venue'].get('city')}. PLE stakes: {ctx.get('ple')}. Featured: {ctx['featured']}. Rivalry: {ctx['rivalry']}.
Last show: {ctx['last_show']}. Champions: {ctx['champions']}. Unresolved events: {ctx['unresolved']}.
Heuristic score: {rating}/10. Breakdown: {breakdown}.
Show text (excerpt): {(text or '')[:4500]}
Respond in clear sections with bullet points:
1. Quick Summary (2 sentences)
2. Why This Show Worked (3-5 bullets)
3. Why This Show Struggled (3-5 bullets)
4. What Made Sense
5. What Did Not Make Sense
6. Character Accuracy
7. Story Continuity
8. Emotional Investment
9. Champion Usage
10. Rivalry Heat
11. Attendance/Viewership Impact
12. Money/Business Impact
13. Twitter Fallout
14. Next Week Suggestions (specific: open, segment, tweet)"""
 out=ai(prompt)
 if out and not out.startswith('AI error'):
  fb['ai_narrative']=out
 return rating,grade,notes,fb,breakdown

def build_grade_result(text,featured,rivalry,venue,ple,company,matches,promos,sched,mode,use_ai=True):
 ctx=booking_context_pack(company,venue,featured,rivalry,sched); ctx['ple']=ple
 base=grade_story(text,featured,rivalry,venue,ple,company,matches,promos,sched,mode)
 if use_ai: base=enrich_grade_with_ai(base,ctx,text)
 rating,grade,notes,fb,breakdown=base
 return {'rating':rating,'grade':grade,'notes':notes,'feedback':fb,'breakdown':breakdown,'official':True,'disabled_reason':''}

def run_book_show_week(company,run_week,show_name,episode,venue,ple,featured,rival,sched,full,matches,promos,mode,opening,closing,long_story,sid,beat,ple_build,ple_pay,end_st,segments,draft=None,meta=None):
 """Run graded show for current bookable week — finances, performance, storylines, sponsors."""
 if st.session_state.get('calendar_locked') and not sched:
  st.error(f'Cannot run — no locked Week {run_week} entry for {company}.')
  return
 gr=build_grade_result(full,featured,rival,venue,ple,company,matches,promos,sched,mode,use_ai=should_use_openai_ai())
 rating,grade,notes,feedback,breakdown=gr['rating'],gr['grade'],gr['notes'],gr['feedback'],gr['breakdown']
 gr['official']=official_rating_enabled()
 if not gr['official']:
  gr['disabled_reason']='AI-booked show — performance still scored from story analysis (not manual entry).'
 st.session_state.last_grade=gr
 reasons={}
 ht=sched.get('hometown',[]) if sched else []
 booked_names=process_show_booking_debuts(matches,promos,full,company,show_name,run_week)
 booked_set=booked_names_from_show(matches,promos)
 stat_before=capture_roster_stat_snapshot(company,booked_set)
 rival_before=capture_rivalry_heat_snapshot(company,booked_set)
 buzz_before=company_roster_buzz_sum(company,booked_set)
 for i,m in enumerate(matches): apply_match_result(m,company=company,show_name=show_name,rating=rating,main_event=(i==len(matches)-1))
 for p in promos:
  for n in p.get('participants',[]):
   if n!='None' and find(n): find(n)['momentum']=min(100,find(n)['momentum']+2)
 apply_weekly_booking_boosts(matches,promos,featured,rating,ple,company,ht,reasons)
 advance_debut_week_tracking(company,booked_names)
 advance_contracts_weekly(company)
 unused_warns=apply_debut_unused_penalties(company)
 for uw in unused_warns[:4]: st.session_state.news_feed.insert(0,f"Week {run_week}: {uw}")
 st.session_state.confirmed_story_debuts=[]
 log=compute_show_logistics(company,venue,matches,promos,rating,ple,episode,show_name)
 vd_preview=calculate_show_viewership(company,rating,feedback,breakdown,venue,featured,rival,ple,sched,matches,promos,log)
 log=reconcile_show_logistics_with_results(log,rating,vd_preview,episode,venue,company,matches,promos,ple,breakdown,feedback,featured,rival)
 apply_post_show_consequences(company,rating,breakdown,ple,feedback,log)
 fin_report=apply_show_finances(company,log,run_week)
 st.session_state.logistics_reports.insert(0,log)
 profit=log['profit_loss']
 finance_flash(company,profit,f"{show_name} final profit/loss")
 if log.get('hotel_savings',0): finance_flash(company,log['hotel_savings'],f"{log.get('hotel_sponsor','Sponsor')} hotel savings")
 if log.get('transport_savings',0): finance_flash(company,log['transport_savings'],f"{log.get('transport_sponsor','Sponsor')} transportation savings")
 evrec=None
 if run_week%4==0:
  tgt=random.choice(opts(company))
  evrec=build_random_event(company,target=tgt,venue=venue)
  apply_random_event_record(evrec)
  mp_add_transaction(company,'Random Event',f"{evrec['event']} ({tgt})",int(evrec.get('money',0)),run_week)
  finance_flash(company,int(evrec.get('money',0)),f"random event: {evrec['event']}")
 update_rank(reasons)
 hist={'week':run_week,'show_name':show_name,'company':company,'country':venue['country'],'region':venue['region'],'city':venue['city'],'venue':venue['venue'],'capacity':venue['capacity'],'show_type':episode,'final_rating':rating,'episode_rating':rating,'grade':grade,'rating_breakdown':breakdown,'official_rating':official_rating_enabled(),'booking_mode':mode,'ai_booked':st.session_state.get('ai_booked_show'),'user_edited':st.session_state.get('show_user_edited'),'ticket_revenue':log['ticket_revenue'],'venue_cost':log['venue_rental'],'travel_cost':log['transport_final'],'security_cost':log['security_cost'],'market_bonus':log['market_bonus'],'profit':profit,'featured_star':featured,'top_rivalry':rival,'summary':full[:500],'matches':matches,'promos':promos,'random_event':evrec,'power_rankings':st.session_state.power_rankings[:20],'ai_feedback':feedback,'logistics':log,'viewership':vd_preview['viewership'],'is_ple':ple,'opening':opening,'closing':closing,'long_story':long_story[:2000] if long_story else ''}
 hist,vd,review=apply_show_viewership_and_dirt_sheet(hist,company,rating,feedback,breakdown,venue,featured,rival,ple,sched,matches,promos,log,text=full)
 stat_after=capture_roster_stat_snapshot(company,booked_set)
 rival_after=capture_rivalry_heat_snapshot(company,booked_set)
 buzz_after=company_roster_buzz_sum(company,booked_set)
 attach_show_performance(hist,fin_report,stat_before,stat_after,rival_before,rival_after,buzz_before,buzz_after,grade_result=gr,view_data=vd,reasons=reasons,ple=ple)
 st.session_state.ai_booked_show=False
 st.session_state.last_dirt_sheet=hist
 import bfg_book_show as book_show
 st.session_state.last_storyline_updates=book_show.apply_storylines_from_booking(company,run_week,rating,feedback,featured,rival,ple,segments,sid,beat,ple_build,ple_pay,end_st)
 sponsor_obj.check_show_sponsor_progress(company,COMPANIES.get(company,{}).get('sponsors',[]),rating)
 save_show(company,run_week,hist)
 if draft is not None:
  book_show.remember_completed_show(company,run_week,draft,meta or {},venue,mode,opening,closing,long_story,segments,matches,promos,full,hist)
 touch_universe_meta(company); save_universe()
 st.session_state.news_feed.insert(0,f"Week {run_week}: {show_name} ({company}) — {rating}/10 · {vd['viewership']:,} viewers · {money(profit)}. {logistics_ai_summary(log)}")
 mark_schedule_completed(company,run_week,hist,log,rating)
 st.session_state.last_show_finance_report=fin_report
 advanced=try_advance_shared_week_after_show()
 if advanced:
  st.success(f'All brands finished Week {run_week}. Universe advanced to Week {st.session_state.week}. Rating {rating}/10 · Viewership {vd["viewership"]:,}. Profit {money(profit)}.')
 else:
  st.success(f'{company} Week {run_week} completed. Rating {rating}/10 · Viewership {vd["viewership"]:,}. Profit {money(profit)}. Waiting on other GMs.')

def book_show_helpers():
 """Namespace of app callables for bfg_book_show.render_book_show_page."""
 from types import SimpleNamespace
 import bfg_book_show as book_show
 return SimpleNamespace(
  migrate_schedule_calendar=migrate_schedule_calendar,
  render_page_shell=render_page_shell,
  can_edit_company=can_edit_company,
  company_show_locked=company_show_locked,
  is_admin=is_admin,
  next_bookable_week=next_bookable_week,
  get_scheduled_show=get_scheduled_show,
  format_schedule_location=format_schedule_location,
  schedule_to_episode_type=schedule_to_episode_type,
  schedule_show_is_ple=schedule_show_is_ple,
  clean_name_selector=clean_name_selector,
  venue_selector=venue_selector,
  COMPANIES=COMPANIES,
  bfg_card=bfg_card,
  build_show_story=build_show_story,
  build_grade_result=build_grade_result,
  booking_context_pack=booking_context_pack,
  official_rating_enabled=official_rating_enabled,
  calculate_show_viewership=calculate_show_viewership,
  parse_long_story=parse_long_story,
  ai_suggest_improvements=ai_suggest_improvements,
  ai_book_show=ai_book_show,
  run_book_show_week=run_book_show_week,
  touch_universe_meta=touch_universe_meta,
  save_universe=save_universe,
  money=money,
  render_viewership_dirt_sheet=render_viewership_dirt_sheet,
  render_grade_report=render_grade_report,
  render_book_show_page=book_show.render_book_show_page,
  mark_company_draft_saved=mark_company_draft_saved,
 )

COMPANY_VIEWERSHIP_BASELINE={'NXT':1800000,'SmackDown':1600000,'WCW':1700000}
VIEWERSHIP_MIN=500000
VIEWERSHIP_MAX=5000000
RATING_VIEWERSHIP_PCT={10:0.18,9:0.14,8:0.10,7:0.06,6:0.03,5:0.0,4:-0.03,3:-0.06,2:-0.10,1:-0.14}

def _breakdown_val(breakdown,needle,default=5.5):
 for k,v in (breakdown or {}).items():
  if needle.lower() in str(k).lower(): return float(v)
 return default

def get_company_last_viewership(company):
 for h in reversed(st.session_state.weekly_history):
  if h.get('company')==company:
   return int(h.get('viewership') or h.get('episode_viewership') or 0)
 prof=st.session_state.company_profiles.setdefault(company,{})
 return int(prof.get('last_viewership') or COMPANY_VIEWERSHIP_BASELINE.get(company,1600000))

def rating_viewership_modifier(rating):
 r=max(1.0,min(10.0,float(rating or 5)))
 lo,hi=int(r),min(10,int(r)+1)
 if lo==hi: return RATING_VIEWERSHIP_PCT.get(lo,0)
 t=r-lo
 return RATING_VIEWERSHIP_PCT.get(lo,0)*(1-t)+RATING_VIEWERSHIP_PCT.get(hi,RATING_VIEWERSHIP_PCT.get(lo,0))*t

def calculate_show_viewership(company,rating,feedback,breakdown,venue,featured,rival,ple,sched,matches,promos,log=None):
 hist_co=[h for h in st.session_state.weekly_history if h.get('company')==company]
 base=COMPANY_VIEWERSHIP_BASELINE.get(company,1600000) if not hist_co else get_company_last_viewership(company)
 if base<VIEWERSHIP_MIN: base=COMPANY_VIEWERSHIP_BASELINE.get(company,1600000)
 mult=1.0; notes=[]
 pct=rating_viewership_modifier(rating)
 mult+=pct; notes.append(f'Episode rating {rating}/10 → {pct*100:+.1f}%')
 story=_breakdown_val(breakdown,'Story'); emo=_breakdown_val(breakdown,'Emotion'); riv=_breakdown_val(breakdown,'Rivalry')
 champ=_breakdown_val(breakdown,'Champion'); promo=_breakdown_val(breakdown,'Promo'); pace=_breakdown_val(breakdown,'Pacing')
 if story>=8: mult+=0.04; notes.append(f'Strong story continuity ({story}/10) → +4%')
 elif story<5: mult-=0.05; notes.append(f'Weak continuity ({story}/10) → -5%')
 if emo>=8: mult+=0.05; notes.append(f'High emotional investment ({emo}/10) → +5%')
 elif emo<5: mult-=0.04; notes.append(f'Low emotion ({emo}/10) → -4%')
 if riv>=8: mult+=0.04; notes.append(f'Hot rivalry usage ({riv}/10) → +4%')
 elif riv<5: mult-=0.03; notes.append('Flat rivalry heat → -3%')
 if champ>=7: mult+=0.02; notes.append(f'Champions used well ({champ}/10) → +2%')
 elif champ<5: mult-=0.02; notes.append('Champions underused → -2%')
 if promo>=7: mult+=0.02; notes.append(f'Strong promo/match quality ({promo}/10) → +2%')
 if pace>=7 and (feedback or {}).get('fans_care'): mult+=0.03; notes.append('Fans will care about the ending → +3%')
 if (feedback or {}).get('dropped'): mult-=0.05; notes.append('Dropped threads hurt tune-in → -5%')
 if ple: mult+=0.08; notes.append('PLE / special stakes → +8%')
 if sched and sched.get('hometown') and (feedback or {}).get('hometown'): mult+=0.03; notes.append('Hometown talent featured → +3%')
 if venue and int(venue.get('prestige',5))>=9: mult+=0.03; notes.append('Major venue prestige → +3%')
 prof=st.session_state.company_profiles.setdefault(company,{}); prest=int(prof.get('prestige',85))
 if prest>=85: mult+=0.01*((prest-80)//5); notes.append(f'Company prestige ({prest}) → small boost')
 fw=find(featured) if featured else None
 if fw and fw.get('popularity',0)>=85: mult+=0.04; notes.append(f'Star power ({featured} pop {fw["popularity"]}) → +4%')
 elif fw and fw.get('popularity',0)>=75: mult+=0.02; notes.append(f'Solid featured star ({featured}) → +2%')
 if rival and str(rival).lower() not in ('none',''):
  rh=next((int(r.get('heat',50)) for r in st.session_state.rivalries if r.get('company',company)==company and rival in r.get('name','')),50)
  if rh>=70: mult+=0.04; notes.append(f'Rivalry heat {rh} → +4%')
  elif rh>=55: mult+=0.02; notes.append(f'Active rivalry ({rh} heat) → +2%')
 tw=sum(1 for p in st.session_state.twitter_posts[:12] if p.get('company')==company)
 if tw>=3: mult+=0.02; notes.append('Twitter buzz this week → +2%')
 apps=len([a for a in st.session_state.appearance_history[:8] if a.get('company')==company])
 if apps: mult+=min(0.04,apps*0.01); notes.append(f'Media appearances ({apps}) → +{min(4,apps)}%')
 ev=len([e for e in st.session_state.random_event_history if e.get('company')==company and e.get('status')=='unresolved'])
 if ev and (feedback or {}).get('dropped'): mult-=0.03; notes.append('Unresolved random events ignored → -3%')
 nm=len(matches or [])+len(promos or [])
 if nm>=6 and story>=7: mult+=0.02; notes.append('Card felt important (depth + story) → +2%')
 view=int(base*mult)
 view=max(VIEWERSHIP_MIN,min(VIEWERSHIP_MAX,view))
 change=view-base
 return {'viewership':view,'base':base,'multiplier':round(mult,3),'change':change,'modifiers':notes,'episode_rating':round(float(rating),1)}

def rule_based_dirt_sheet(company,show_name,week,rating,viewership,feedback,breakdown,view_data,log=None):
 fb=feedback or {}; worked=fb.get('worked',[])[:3]; struggled=fb.get('struggled',[])[:3]
 sense=fb.get('made_sense',[])[:2]; nosense=fb.get('no_sense',[])[:2]
 headline='STRONG WEEK' if rating>=8 else 'MIXED BAG' if rating>=6 else 'ROUGH NIGHT'
 sq=(log or {}).get('show_quality',{}) if log else {}
 sell=sq.get('sellout_status') or view_data.get('sellout_status','')
 lines=[f"**{company} Dirt Sheet — Week {week}** · *{show_name}*",f"**Headline:** {headline} · **Episode Rating:** {rating}/10 · **Viewership:** {viewership:,} ({view_data.get('change',0):+,} vs last week)"]
 if sell: lines.append(f"**Gate:** {sell} ({sq.get('capacity_pct', view_data.get('capacity_pct','—'))}% capacity)")
 if sq.get('show_descriptor'): lines.append(f"**Show read:** {sq['show_descriptor']}")
 lines.append('')
 lines.append(f"**Why it worked:** {worked[0] if worked else 'The show had forward momentum.'}")
 if len(worked)>1: lines.append(f"• {worked[1]}")
 lines.append(f"**Why it struggled:** {struggled[0] if struggled else 'Minor pacing or follow-up issues.'}")
 if sense: lines.append(f"**Made sense:** {sense[0]}")
 if nosense: lines.append(f"**Did not make sense:** {nosense[0]}")
 lines.append(f"**Viewership math:** Base {view_data.get('base',0):,} × {view_data.get('multiplier',1):.2f} = {viewership:,}")
 for n in view_data.get('modifiers',[])[:6]: lines.append(f"• {n}")
 if fb.get('next_week'): lines.append(f"**Next week:** {fb['next_week']}")
 return '\n'.join(lines)

def generate_dirt_sheet_review(company,show_name,week,rating,viewership,feedback,breakdown,view_data,text='',featured='',rival='',log=None):
 sq=(log or {}).get('show_quality',{}) if log else {}
 sq_line=sq.get('show_descriptor','')
 prompt=f"""Write a wrestling DIRTSHEET / insider newsletter review for Bound For Glory.
Company: {company} · Week {week} · Show: {show_name}
Episode Rating: {rating}/10 (1.0-10.0 scale)
Viewership: {viewership:,} fans (range 500K-5M)
Viewership change vs last week: {view_data.get('change',0):+,}
Rating breakdown: {breakdown}
Creative notes: worked={feedback.get('worked',[])[:4]} struggled={feedback.get('struggled',[])[:4]} continued={feedback.get('continued',[])[:3]} dropped={feedback.get('dropped',[])[:3]}
Featured: {featured} · Rivalry: {rival}
Sellout / gate: {sq.get('sellout_status','')} · Champion usage: {sq.get('champion_descriptor','')}
Show quality line (weave in naturally): {sq_line}
Sponsor ads: {[a.get('descriptor') for a in sq.get('sponsor_ads',[])[:2]]}
Show excerpt: {(text or '')[:3500]}
Sections required:
1. Dirt Sheet Headline (one punchy line)
2. Episode Rating Verdict (why {rating}/10)
3. Why The Show Was Good (bullets)
4. Why The Show Was Bad (bullets)
5. Viewership Analysis (why fans tuned in or out)
6. Locker Room Whisper
7. What Fans Are Saying Online
8. Next Week Prediction
Tone: cynical but fair insider columnist. Under 450 words."""
 out=ai(prompt)
 if out and not str(out).startswith('AI error'): return out.strip(),True
 return rule_based_dirt_sheet(company,show_name,week,rating,viewership,feedback,breakdown,view_data,log=log),False

def apply_show_viewership_and_dirt_sheet(hist,company,rating,feedback,breakdown,venue,featured,rival,ple,sched,matches,promos,log=None,text=''):
 vd=calculate_show_viewership(company,rating,feedback,breakdown,venue,featured,rival,ple,sched,matches,promos,log)
 if log and log.get('show_quality'):
  om=float(vd.get('multiplier',1.0) or 1.0)
  vd=showq.enrich_viewership_modifiers(vd,log['show_quality'],rating,breakdown)
  nm=float(vd.get('multiplier',1.0) or 1.0)
  vd['viewership']=max(VIEWERSHIP_MIN,min(VIEWERSHIP_MAX,int(vd['viewership']*nm/max(0.01,om))))
  vd['change']=vd['viewership']-vd.get('base',vd['viewership'])
 review,ai_flag=generate_dirt_sheet_review(company,hist.get('show_name',''),hist.get('week',st.session_state.week),rating,vd['viewership'],feedback,breakdown,vd,text,featured,rival,log=log)
 hist['viewership']=vd['viewership']; hist['episode_viewership']=vd['viewership']; hist['episode_rating']=vd['episode_rating']
 hist['viewership_base']=vd['base']; hist['viewership_multiplier']=vd['multiplier']; hist['viewership_change']=vd['change']; hist['viewership_modifiers']=vd['modifiers']
 hist['dirt_sheet_review']=review; hist['dirt_sheet_ai']=ai_flag; hist['dirt_sheet_label']='AI' if ai_flag else 'Rule-based'
 prof=st.session_state.company_profiles.setdefault(company,{}); prof['last_viewership']=vd['viewership']
 if log is not None: log['viewership']=vd['viewership']
 return hist,vd,review

def render_viewership_dirt_sheet(hist=None,grade=None,compact=False):
 data=hist or {}
 if grade and not data.get('viewership'):
  data={**data,'episode_rating':grade.get('rating'),'viewership':data.get('viewership')}
 vw=int(data.get('viewership') or data.get('episode_viewership') or 0)
 if not vw and not data.get('dirt_sheet_review'): return
 with bfg_card('Viewership & Dirt Sheet'):
  c1,c2,c3=st.columns(3)
  c1.metric('Episode Rating',f"{data.get('episode_rating',data.get('final_rating','—'))}/10")
  c2.metric('Viewership',f"{vw:,}" if vw else '—')
  ch=int(data.get('viewership_change',0)); c3.metric('Vs Last Week',f"{ch:+,}" if ch else '—')
  if data.get('viewership_modifiers') and not compact:
   with st.expander('Viewership modifiers',expanded=False):
    for n in data.get('viewership_modifiers',[]): st.caption('• '+n)
 if data.get('dirt_sheet_review'):
  render_long_markdown(data['dirt_sheet_review'],f"Dirt Sheet Review ({data.get('dirt_sheet_label','')})",expanded=len(data['dirt_sheet_review'])>320)

def render_grade_report(g):
 if not g: return
 fb=g.get('feedback',{}) or {}
 if g.get('official') is False:
  st.warning(g.get('disabled_reason') or 'AI-booked show. Official rating disabled.')
  if fb.get('ai_narrative'):
   render_ai_analysis(fb['ai_narrative'],'Creative Analyst Notes')
  return
 st.markdown(f"### Final Show Rating: **{g['rating']}** / 10")
 st.caption(f"Letter grade: **{g.get('grade','—')}**")
 if g.get('breakdown'):
  with st.expander('Rating Breakdown',expanded=True):
   st.caption('Weights: Story Continuity 25% · Emotion 20% · Character 15% · Rivalry 15% · Champion 10% · Promo/Match 10% · Business/Venue 5% (PLEs graded harder)')
   cols=st.columns(3)
   for i,(k,v) in enumerate(g['breakdown'].items()):
    cols[i%3].metric(k,f"{v}/10")
 if fb.get('summary'):
  st.markdown('**Summary**')
  st.markdown(fb['summary'])
 impact_map=[
  ('Story Logic','story_impact'),('What Worked','worked'),('What Did Not Work','struggled'),
  ('Morale Impact','morale_impact'),('Popularity Impact','popularity_impact'),('Money Impact','money_impact'),
  ('Viewership Impact','viewership_impact'),('Next Week Suggestion','next_week'),
 ]
 list_sections=[
  ('What Worked','worked'),('What Did Not Work','struggled'),('Story Logic','made_sense'),
  ('Continuity','continued'),('Dropped Threads','dropped'),('Character Accuracy','in_character'),
  ('Emotional Beats','emotion_hit'),('Rivalry Heat','rivalry_notes'),('Pacing','pacing_notes'),
 ]
 for title,key in list_sections:
  items=fb.get(key,[])
  if not items: continue
  with st.expander(title,expanded=(title in ('What Worked','What Did Not Work','Next Week Suggestion'))):
   for x in items[:12]:
    st.markdown(f'- {x}')
 for title,key in impact_map:
  val=fb.get(key)
  if isinstance(val,list) and val:
   with st.expander(title,expanded=False):
    for x in val[:10]: st.markdown(f'- {x}')
  elif val and not isinstance(val,list):
   st.markdown(f'**{title}:** {val}')
 if fb.get('ai_narrative'):
  render_ai_analysis(fb['ai_narrative'],'Creative Analyst Report')
 if fb.get('twitter_fallout'):
  st.caption('Twitter ideas: '+', '.join(str(x) for x in fb['twitter_fallout'][:3]))
 if g.get('viewership') or g.get('dirt_sheet_review'):
  render_viewership_dirt_sheet(g,compact=False)

def ai_suggest_improvements(text,company,ctx):
 prompt=f"""Bound For Glory GM — give creative advice ONLY (do not write the full show). Company {company}, week {ctx['week']}.
Venue {ctx['venue'].get('venue')}, {ctx['venue'].get('city')}. Rivalry {ctx['rivalry']}. Champions {ctx['champions']}.
Unresolved: {ctx['unresolved']}. Last show summary: {ctx['last_show'].get('summary','')[:400]}
Current booking excerpt: {(text or '')[:2500]}
List: 5 improvements, 3 continuity fixes, 3 emotion beats, 2 Twitter ideas."""
 return ai(prompt) or 'Strengthen continuity from last week, add a personal emotional stake to the main rivalry, and end with a cliffhanger GM or title angle.'

def ai_analyze_story(text,company,ctx):
 prompt=f"""Analyze this wrestling show story like a TV critic. Company {company}, week {ctx['week']}. Do NOT assign a numeric score.
Cover: strengths, weaknesses, logic, continuity, emotion, character accuracy, fan investment, champion usage, rivalry heat, business/venue fit, Twitter fallout, next week hooks.
Show: {(text or '')[:5000]}"""
 return ai(prompt) or 'Story analysis unavailable — use Grade Show for a scored breakdown.'

def ai_book_show(company,ctx,long_format=True):
 nw=ctx['week']
 prompt=f"""Write a complete Bound For Glory {company} TV show for week {nw}.
Venue: {ctx['venue'].get('venue')}, {ctx['venue'].get('city')}, {ctx['venue'].get('country')}.
Featured star: {ctx['featured']}. Main rivalry: {ctx['rivalry']}. Champions: {ctx['champions']}.
Roster momentum leaders: {ctx['roster']}. Active rivalries: {ctx['rivals']}.
Last show: {ctx['last_show']}. Unresolved events: {ctx['unresolved']}. Recent tweets: {[t.get('text','')[:80] for t in ctx['tweets'][:4]]}.
Brand lore: {ctx['lore']}. Calendar notes: {ctx['sched']}.
Include: opening segment, 2-3 promos, 4-6 matches with winners and finishes, backstage bits, commentary notes, closing cliffhanger, Twitter fallout ideas, next-week hooks.
Match character voices from Character Editor. Continue last week's stories. {'Write as one long narrative script.' if long_format else 'Write structured sections.'}"""
 return ai(prompt) or f"OPENING: {ctx['featured']} addresses the crowd in {ctx['venue'].get('city')}.\n\nPROMO: {ctx['rivalry']} escalates.\n\nMAIN EVENT: Championship stakes close the show with a cliffhanger."

def parse_long_story(text,company):
 low=text.lower(); names=[w['name'] for w in roster(company)]; detected={'promos':[],'matches':[],'winners':[],'losers':[],'main_event':'','title_matches':[],'rivalries':[],'characters':[],'champions':[],'factions':[],'show_rating':7.0,'power_impact':'Moderate','unclear':[]}
 for f in WCW_FACTIONS:
  if f.lower() in low: detected['factions'].append(f)
 for n in names:
  if n.lower() in low: detected['characters'].append(n)
 for t,v in st.session_state.champions.get(company,{}).items():
  if v and v!='Place Holder' and str(v).lower() in low: detected['champions'].append(f'{t}: {v}')
 promo_kw=['promo','segment','interview','backstage','opening','contract signing']
 for i,line in enumerate(text.split('\n')):
  ll=line.lower().strip()
  if not ll: continue
  if any(k in ll for k in promo_kw) and not any(x in ll for x in ['defeated','def ',' beat ',' wins ']):
   parts=[n for n in names if n.lower() in ll]; detected['promos'].append({'line':line.strip(),'participants':parts or ['Unknown'],'purpose':'Story promo'})
  if any(x in ll for x in [' vs ',' versus ',' defeated ',' beat ',' def. ',' def ']):
   parts=[n for n in names if n.lower() in ll]; winner=''; loser=''
   for pat in [r'(\w[\w\s\'&\.-]+)\s+defeated\s+(\w[\w\s\'&\.-]+)', r'(\w[\w\s\'&\.-]+)\s+beat\s+(\w[\w\s\'&\.-]+)', r'(\w[\w\s\'&\.-]+)\s+def\.?\s+(\w[\w\s\'&\.-]+)']:
    m=re.search(pat,line,re.I)
    if m:
     w1,w2=m.group(1).strip(),m.group(2).strip()
     winner=next((n for n in names if n.lower() in w1.lower()), w1); loser=next((n for n in names if n.lower() in w2.lower()), w2); break
   if len(parts)>=2 and not winner:
    if 'no contest' in ll or 'draw' in ll: winner='NC'
    else: detected['unclear'].append({'line':line.strip(),'participants':parts})
   stip='Title Match' if 'title' in ll else ('Ultimate X' if 'ultimate x' in ll else ('Anarchy in the Arena' if 'anarchy' in ll else 'Normal'))
   if stip=='Title Match': detected['title_matches'].append(parts)
   detected['matches'].append({'line':line.strip(),'participants':parts[:4] if parts else ['A','B'],'winner':winner or 'TBD','loser':loser,'stip':stip,'title':'Title Match' if stip=='Title Match' else 'None','rivalry':''})
 if detected['matches']: detected['main_event']=detected['matches'][-1].get('line','')
 detected['story_hooks']=[ln.strip() for ln in text.split('\n') if any(k in ln.lower() for k in ['cliffhanger','next week','to be continued','after the show','hook'])]
 detected['opening']=next((ln.strip() for ln in text.split('\n') if 'opening' in ln.lower()[:30]),'')
 detected['closing']=next((ln.strip() for ln in text.split('\n') if any(k in ln.lower() for k in ['closing','final','aftermath'])),'')
 detected['twitter_refs']=[ln.strip() for ln in text.split('\n') if 'twitter' in ln.lower() or '@' in ln]
 detected['win_loss_updates']=[{'winner':m.get('winner'),'loser':m.get('loser'),'line':m.get('line')} for m in detected['matches'] if m.get('winner') not in ('','TBD','NC')]
 detected['show_rating']=min(10,6+len(detected['matches'])*.25+len(detected['promos'])*.15)
 detected['potential_debuts']=[n for n in detected.get('characters',[]) if find(n) and is_not_debuted(find(n))]
 return detected


# ---------------- EXTENDED PART 2 / FULL DREAM BUILD DATA ----------------
BRAND_THEMES={
 'NXT':{'primary':'black','accent':'purple/gold','lore':'The cinematic flagship brand. Netflix, Marvel, DC, Oscars, Olympics, SNL and Good Morning America turn NXT stars into global entertainment attractions.'},
 'SmackDown':{'primary':'deep blue','accent':'white/red','lore':'The mainstream TV and music brand. Grammys, celebrity culture, USA/TNT/Paramount Plus and guest stars make SmackDown feel like pop culture.'},
 'WCW':{'primary':'black/dark red','accent':'gold/steel','lore':'The sports legacy brand. ESPN, CBS, NBA/NFL halftime, draft pick announcements and championship prestige make WCW feel like a real sports property.'},
}
STAFF={
 'NXT':[{'name':'Eric Bischoff','role':'Owner / GM','handle':'@EricBischoffNXT','style':'smug media power-broker, ratings-obsessed, Hollywood-savvy'}, {'name':'Mauro Ranallo','role':'Commentator','handle':'@MauroNXT','style':'dramatic, emotional, poetic, big-fight'}, {'name':'Pat McAfee','role':'Commentator','handle':'@PatNXT','style':'energetic, funny, loud, fan-like'}, {'name':'Jerry Lawler','role':'Commentator','handle':'@KingNXT','style':'old-school, witty'}, {'name':'R-Truth','role':'Commentator','handle':'@TruthNXT','style':'funny, confused, entertaining'}, {'name':'Samantha Irvin','role':'Ring Announcer','handle':'@SamanthaNXT','style':'emotional, entrance-focused, historic moment hype'}, {'name':'NXT Official','role':'Company Account','handle':'@NXTImmortal','style':'official brand account'}],
 'SmackDown':[{'name':'Ric Flair','role':'Owner','handle':'@RicFlairSD','style':'loud, stylish, arrogant, celebrity-driven, WOOOO energy'}, {'name':'Ava','role':'GM','handle':'@AvaSDGM','style':'young modern authority figure, professional, direct, confident'}, {'name':'Eric Collins','role':'Commentator','handle':'@EricCollinsSD','style':'intense highlight-reel style'}, {'name':'Ernie Johnson','role':'Commentator','handle':'@ErnieSD','style':'professional studio host'}, {'name':'Dick Vitale','role':'Commentator','handle':'@DickieVSD','style':'excited sports-broadcast style'}, {'name':'Mike Walczewski','role':'Ring Announcer','handle':'@MikeWSD','style':'classic big-fight arena announcer'}, {'name':'SmackDown Official','role':'Company Account','handle':'@SmackDownBFG','style':'mainstream TV brand account'}],
 'WCW':[{'name':'Stephanie McMahon','role':'Owner','handle':'@StephanieWCW','style':'corporate sports-network owner, serious and competitive'}, {'name':'Shane McMahon','role':'Owner','handle':'@ShaneWCW','style':'risk-taking corporate sports promoter'}, {'name':'Nick Aldis','role':'GM','handle':'@NickAldisWCW','style':'serious GM protecting championship legitimacy'}, {'name':'Michael Cole','role':'Commentator','handle':'@ColeWCW','style':'official and polished'}, {'name':'Corey Graves','role':'Commentator','handle':'@GravesWCW','style':'sarcastic, sharp, heel-leaning'}, {'name':'Jim Ross','role':'Commentator','handle':'@JrWCW','style':'old-school, serious, legendary, big-fight'}, {'name':'Michael Buffer','role':'Ring Announcer','handle':'@BufferWCW','style':'grand, prestigious, fight-night style'}, {'name':'WCW Official','role':'Company Account','handle':'@WCWLegacy','style':'sports league brand account'}],
}
NXT_EXCLUSIVE_PARTNERS={'Netflix','Marvel','DC','Hollywood','SNL','Good Morning America','Olympics','Oscars','FOX','NBC Sports','Comic-Con','Mattel','Barbie','Academy Awards','Marvel/DC','Documentary','Toy Campaign'}
NXT_CAMEO_PARTNERS=['Netflix','Marvel','DC','Hollywood','SNL','Good Morning America','Olympics','Oscars','FOX','NBC Sports','Comic-Con','Mattel','Barbie']
CAMEO_PROJECT_TYPES=['movie cameo','superhero movie cameo','villain cameo','Netflix drama cameo','Netflix documentary','Netflix reality show','sports documentary','SNL sketch','Good Morning America interview','Olympics media segment','red carpet interview','Comic-Con panel','movie trailer','toy commercial','comic book cover reveal','backstage documentary scene','press tour segment','press interview','sponsor commercial','documentary segment','trailer voiceover']
CAMEO_TONES=['serious','funny','dark','heroic','villainous','arrogant','emotional','inspirational','chaotic','sports-like','Hollywood blockbuster','documentary realism']
CAMEO_LENGTHS=['30 seconds','1 minute','2-3 minutes','5 minutes','Full segment','Press tour day','1 week filming','2 weeks filming','1 month filming']
NXT_CHARACTER_FIT={
 'Christian Rose':{'partners':['Netflix','Marvel','DC','Hollywood','Oscars','SNL'],'projects':['movie cameo','villain cameo','Netflix drama cameo','press tour segment'],'role':'manipulative executive / blockbuster villain','avoid':['goofy SNL unless joke protects arrogance, not weakness']},
 'Lani Rose':{'partners':['Good Morning America','Olympics','Netflix','Hollywood'],'projects':['Good Morning America interview','Olympics media segment','superhero movie cameo'],'role':'fiery champion / inspirational athlete','avoid':['dark horror tone']},
 'Raven':{'partners':['Netflix','DC','Marvel'],'projects':['Netflix documentary','villain cameo','dark thriller cameo'],'role':'cryptic dark presence','avoid':['goofy SNL unless joke protects darkness']},
 'CM Punk':{'partners':['Netflix','Good Morning America','FOX'],'projects':['Netflix documentary','press interview','documentary segment'],'role':'truth-teller / anti-corporate voice','avoid':['corporate sponsor commercial']},
 'Roman Reigns':{'partners':['Netflix','Hollywood','Olympics','Marvel'],'projects':['superhero movie cameo','sports documentary','movie trailer'],'role':'final-boss prestige / family legacy','avoid':['comedy sketch that makes him look weak']},
 'Seth Rollins':{'partners':['Hollywood','Oscars','SNL','DC'],'projects':['villain cameo','red carpet interview','SNL sketch'],'role':'flashy villain / fashion red carpet','avoid':['wholesome GMA unless heel spin']},
 'Rhea Ripley':{'partners':['Marvel','DC','Hollywood','Netflix'],'projects':['superhero movie cameo','villain cameo','action movie cameo'],'role':'dominant action villain','avoid':[]},
 'Jade Cargill':{'partners':['Marvel','DC','Mattel','Barbie'],'projects':['superhero movie cameo','comic book cover reveal','toy commercial'],'role':'superhero / action icon','avoid':[]},
 'Bianca Belair':{'partners':['Olympics','Good Morning America','Mattel','Barbie'],'projects':['Olympics media segment','Good Morning America interview','toy commercial'],'role':'inspirational sports star','avoid':['dark villain roles']},
 'Gunther':{'partners':['Netflix','Olympics','NBC Sports'],'projects':['sports documentary','documentary segment','press interview'],'role':'serious European prestige','avoid':['chaotic comedy']},
 'Chad Gable':{'partners':['Olympics','NBC Sports','Netflix'],'projects':['Olympics media segment','sports documentary'],'role':'Olympic/training center credibility','avoid':[]},
 'John Cena':{'partners':['Hollywood','Good Morning America','Mattel'],'projects':['movie cameo','toy commercial','Good Morning America interview'],'role':'mainstream hero','avoid':[]},
 'Shinsuke Nakamura':{'partners':['Netflix','Comic-Con'],'projects':['documentary segment','Comic-Con panel'],'role':'artistic international star','avoid':[]},
}
CAMEO_GENERATOR_BUTTONS={
 'Generate Cameo Idea':{'mode':'idea'},
 'Generate Full Cameo Script':{'mode':'full'},
 'Generate Press Interview':{'mode':'full','project':'press tour segment'},
 'Generate SNL Sketch':{'mode':'full','project':'SNL sketch'},
 'Generate Movie Scene':{'mode':'full','project':'movie cameo'},
 'Generate Netflix Documentary Segment':{'mode':'full','project':'Netflix documentary','partner':'Netflix'},
 'Generate Good Morning America Segment':{'mode':'full','project':'Good Morning America interview','partner':'Good Morning America'},
 'Generate Olympics Segment':{'mode':'full','project':'Olympics media segment','partner':'Olympics'},
 'Generate Red Carpet Interview':{'mode':'full','project':'red carpet interview','partner':'Oscars'},
 'Generate Comic-Con Panel':{'mode':'full','project':'Comic-Con panel','partner':'Comic-Con'},
 'Generate Trailer Voiceover':{'mode':'full','project':'trailer voiceover','partner':'Hollywood'},
 'Generate Sponsor Commercial':{'mode':'full','project':'sponsor commercial'},
}
APPEARANCE_LANES={
 'NXT':['Hollywood Press Tour','Netflix Show Cameo','Netflix Documentary Offer','Marvel Cameo Offer','DC Movie Cameo Offer','Marvel-Style Superhero Cameo','DC-Style Villain Cameo','Hollywood Movie Role','TV Show Crossover','SNL Sketch Invitation','Good Morning America Feature','Olympic Games Media Appearance','Olympic Athlete Guest Spot','Oscars Red Carpet Invite','Academy Awards Presenter Offer','Comic-Con Panel Invite','Movie Trailer Appearance','Red Carpet Movie Premiere','Documentary Segment','Toy/Comic Campaign (Mattel/Barbie/DC)','DC Comic Cover Reveal','Mattel Toy Campaign','Barbie Crossover Campaign','Hollywood Reporter Interview','NXT Unfiltered'],
 'SmackDown':['Grammys Appearance','Grammy Winner Announcement','Grammys Red Carpet Invite','Grammy Presenter Offer','BET Awards Appearance','MTV VMA Segment','Billboard Music Awards Invite','Music Video Cameo Offer','Album Release Party Invite','Concert Appearance','Music Festival Appearance','Celebrity Music Special','Paramount Plus Celebrity Segment','USA Network Celebrity TV','TNT Celebrity Special','Red Carpet Music Event','Concert Cameo Goes Viral'],
 'WCW':['NBA Appearance','NFL Appearance','NBA Halftime Show','NFL Halftime Show','NBA Draft Pick Announcement','NFL Draft Pick Announcement','ESPN SportsCenter Segment','CBS Sports Panel Invite','ESPN Debate Show','Super Bowl Media Row','NBA All-Star Weekend','NFL Draft Weekend','College Football Appearance','Amazon Prime Sports Segment','Sports Documentary Appearance','Championship Belt Presented At Sports Game','College Football Halftime Segment','Amazon Prime Sports Crossover','ESPN Draft Desk Guest','CBS Sports Draft Panel'],
}
BRAND_EXCLUSIVE_LANES={
 'NXT':[
  {'lane':'Hollywood / Netflix Lane','activities':['Hollywood Press Tour','Netflix Show Cameo','Netflix Documentary Offer','Hollywood Movie Role','TV Show Crossover','Documentary Segment']},
  {'lane':'Marvel / DC Lane','activities':['Marvel Cameo Offer','DC Movie Cameo Offer','Marvel-Style Superhero Cameo','DC-Style Villain Cameo','DC Comic Cover Reveal']},
  {'lane':'Oscars / Red Carpet Lane','activities':['Oscars Red Carpet Invite','Academy Awards Presenter Offer','Red Carpet Movie Premiere','Movie Trailer Appearance']},
  {'lane':'SNL / GMA / Olympics Lane','activities':['SNL Sketch Invitation','Good Morning America Feature','Olympic Games Media Appearance','Olympic Athlete Guest Spot']},
  {'lane':'Comic-Con / Toys / Merch Lane','activities':['Comic-Con Panel Invite','Mattel Toy Campaign','Barbie Crossover Campaign','Toy/Comic Campaign (Mattel/Barbie/DC)']},
  {'lane':'NXT Unfiltered','activities':['NXT Unfiltered','Hollywood Reporter Interview']},
 ],
 'SmackDown':[
  {'lane':'Grammys / Music Awards Lane','activities':['Grammys Appearance','Grammy Winner Announcement','Grammys Red Carpet Invite','Grammy Presenter Offer','BET Awards Appearance','MTV VMA Segment','Billboard Music Awards Invite']},
  {'lane':'Music Video / Concert Lane','activities':['Music Video Cameo Offer','Album Release Party Invite','Concert Appearance','Music Festival Appearance','Celebrity Music Special','Concert Cameo Goes Viral']},
  {'lane':'Celebrity TV Lane','activities':['Paramount Plus Celebrity Segment','USA Network Celebrity TV','TNT Celebrity Special','Red Carpet Music Event']},
 ],
 'WCW':[
  {'lane':'NBA / NFL Lane','activities':['NBA Appearance','NFL Appearance','NBA Halftime Show','NFL Halftime Show','NBA All-Star Weekend','NFL Draft Weekend','College Football Appearance','College Football Halftime Segment']},
  {'lane':'Draft Pick Lane','activities':['NBA Draft Pick Announcement','NFL Draft Pick Announcement','ESPN Draft Desk Guest','CBS Sports Draft Panel']},
  {'lane':'ESPN / CBS Sports Lane','activities':['ESPN SportsCenter Segment','CBS Sports Panel Invite','ESPN Debate Show','Amazon Prime Sports Segment','Sports Documentary Appearance','Super Bowl Media Row','Championship Belt Presented At Sports Game']},
 ],
}
ACTIVITY_BRAND={}
for _co,_acts in APPEARANCE_LANES.items():
 for _a in _acts: ACTIVITY_BRAND[_a]=_co
WRONG_BRAND_WARN={
 ('NXT','SmackDown'):'Grammys, music awards, VMAs, and concert crossovers are SmackDown-exclusive. Forcing this may upset SmackDown partners.',
 ('NXT','WCW'):'NBA/NFL, ESPN/CBS sports desk, halftime shows, and draft announcements are WCW-exclusive. Forcing this may create controversy.',
 ('SmackDown','NXT'):'Olympics, Oscars, Netflix, Marvel/DC, SNL, and Good Morning America are NXT-exclusive. Forcing this may create media backlash.',
 ('SmackDown','WCW'):'NBA/NFL and ESPN/CBS sports properties are WCW-exclusive on this universe.',
 ('WCW','NXT'):'Olympics, Oscars, Netflix, Marvel/DC, SNL, and Hollywood press are NXT-exclusive. Forcing this may create media backlash.',
 ('WCW','SmackDown'):'Grammys and music-award lanes are SmackDown-exclusive. Forcing this may upset music partners.',
}
BRAND_EXCLUSIVE_BEST={
 'NXT':['Christian Rose','CM Punk','Raven','Lani Rose','Roman Reigns','Seth Rollins','Rhea Ripley','Jade Cargill','Bianca Belair','John Cena'],
 'SmackDown':['Logan Paul','Bad Bunny','Becky Lynch','Liv Morgan','Undertaker','Randy Orton','Alexa Bliss','Bayley','Chelsea Green','KSI'],
 'WCW':['Triple H','The Rock','Cody Rhodes','Shawn Michaels','Eddie Guerrero','Rey Mysterio','Goldberg','Kevin Nash','Scott Hall','Jordan Burroughs'],
}
EXTRA_WRESTLERS=[
 ('Noam Dar & Oro Mensah','SmackDown','World Tag Team',78,'N',300000),('The Family','SmackDown','World Tag Team',78,'H',300000),('La Parka & Mr. Iguana','SmackDown','World Tag Team',84,'N',600000),('Hank & Tank','SmackDown','World Tag Team',83,'N',400000),('Noam Dar & Rey Fenix','SmackDown','World Tag Team',82,'N',500000),('Piper Niven','SmackDown','Women',82,'H',400000),('Maxxine Dupri','SmackDown','Women',82,'F',500000),('Jacy Jayne','SmackDown','Women',82,'H',500000),('Ava Moreno','SmackDown','Women',90,'F',2000000),('Tatum Paxley','SmackDown','Women',84,'F',2000000),('Wendy Choo','SmackDown','Women',81,'H',400000),('Eve Torres','SmackDown','Women',87,'H',3800000),('Lash Legend','SmackDown','Women',88,'N',2500000),('Tegan Nox','SmackDown','Women',83,'H',600000),('Diana Vegas','SmackDown','Women',87,'F',500000),('Jazmyn Nyx','SmackDown','Women',80,'H',300000),
 ('Shawn Spears','WCW','WCW Television Title',82,'H',250000),('Faarooq','WCW','WCW Television Title',83,'N',500000),('El Ordinario','WCW','WCW Television Title',80,'F',300000),('Sid Justice','WCW','WCW Television Title',85,'H',350000),('Giovanni Vinci','WCW','WCW Television Title',80,'H',200000),('New Day','WCW','World Tag Team',90,'H',1350000),('LWO','WCW','World Tag Team',84,'F',500000),('Wyatt 6','WCW','World Tag Team',88,'N',1000000),('Hart Foundation','WCW','World Tag Team',89,'F',1000000),('The Outsiders','WCW','World Tag Team',90,'H',1600000),('War Raiders','WCW','World Tag Team',85,'F',1000000),('Dudley Boyz','WCW','World Tag Team',88,'F',1000000),('WCW Originals','WCW','World Tag Team',86,'N',2000000),('Briggs and Jensen','WCW','World Tag Team',78,'H',500000),('Billy Gunn and Road Dogg','WCW','World Tag Team',84,'H',1000000),('Haku and Tama','WCW','World Tag Team',84,'F',1000000),('Psycho Clown and Pagano','WCW','World Tag Team',84,'H',600000),('No Quarter Catch Crew','WCW','World Tag Team',83,'H',800000),('JD McDonagh','WCW','Cruiserweight',82,'H',500000),('Dominik Mysterio','WCW','Cruiserweight',83,'H',750000),('Hector Flores','WCW','Cruiserweight',80,'F',200000),('Octagon Jr','WCW','Cruiserweight',83,'F',450000),('Ilja Dragunov','WCW','WCW Television Title',89,'F',800000),
]
TWEET_TYPES=['Normal Tweet','Positive Tweet','Angry Tweet','Rivalry Tweet','Champion Tweet','Cryptic Tweet','Company Shot Tweet','Locker Room Drama Tweet','Hometown Tweet','Win Streak Tweet','Losing Streak Tweet','Creative Complaint Tweet','PLE Promotion Tweet','Movie/Show Promotion Tweet','Sponsor Promotion Tweet','Injury Update Tweet','Travel Complaint Tweet','Contract Tease Tweet','Live From City Tweet','Local Sports Reaction','NBA Game Reaction','NFL Game Reaction','MLB Game Reaction','College Football Reaction','City Crowd Hype','Movie/Show Reaction','Other Company PLE Reaction','Rival Brand Shade','Broadcast Desk Reaction','Ring Announcer Hype','GM Official Statement','Owner Brand Statement','Sponsor/Media Promotion','Award Show Reaction','Sports Crossover Reaction','Trade Rumor Reaction','Draft Pick Reaction','Halftime Show Reaction','Oscars Reaction','Grammys Reaction','Olympics Reaction','Netflix/Marvel/DC Reaction']

REMOVED_WRESTLERS=frozenset({'Max Caster','Jon Moxley','Claudio Castagnoli'})
REMOVED_TAG_TEAMS=frozenset({'A Town Under','Combat Club'})

def purge_removed_talent():
 """Drop real-world talent the user removed — also cleans existing saves."""
 if 'roster' not in st.session_state: return
 gone=REMOVED_WRESTLERS|REMOVED_TAG_TEAMS
 st.session_state.roster=[w for w in st.session_state.roster if w.get('name') not in gone]
 for comp in PLAYABLE:
  if comp in st.session_state.get('factions',{}):
   st.session_state.factions[comp]=[f for f in st.session_state.factions[comp] if f not in REMOVED_TAG_TEAMS and f!='Combat Club']
  for t,titles in list(st.session_state.get('champions',{}).get(comp,{}).items()):
   if titles in gone: st.session_state.champions[comp][t]='Place Holder'
 if st.session_state.get('twitter_posts'):
  st.session_state.twitter_posts=[p for p in st.session_state.twitter_posts if p.get('wrestler') not in gone and p.get('team_name') not in gone]

def fix_roster_divisions():
 for w in st.session_state.roster:
  if w['company']=='SmackDown' and w['name'] in SD_DIVISIONS: w['division']=SD_DIVISIONS[w['name']]
  if w['company']=='WCW' and w['name'] in WCW_DIVISIONS: w['division']=WCW_DIVISIONS[w['name']]

def ensure_extended_state():
 purge_removed_talent()
 existing={w['name'] for w in st.session_state.roster}
 for n,c,d,o,a,s in EXTRA_WRESTLERS:
  if n not in existing:
   st.session_state.roster.append(W(n,c,d,o,a,s)); existing.add(n)
 fix_roster_divisions()
 for w in st.session_state.roster:
  w.setdefault('fan_investment',50); w.setdefault('last_show_boost',0); w.setdefault('story_grade_boost',0)
 if 'staff' not in st.session_state: st.session_state.staff=json.loads(json.dumps(STAFF))
 if 'company_lore' not in st.session_state: st.session_state.company_lore={k:v['lore'] for k,v in BRAND_THEMES.items()}
 if 'company_profiles' not in st.session_state:
  st.session_state.company_profiles={}
  for comp in PLAYABLE:
   cp=dict(COMPANY_PROFILES[comp]); cp['owner']=COMPANIES[comp]['owner']; cp['gm']=COMPANIES[comp]['gm']
   st.session_state.company_profiles[comp]=cp
 ensure_finance_state()
 if 'calendar_ai_notes' not in st.session_state: st.session_state.calendar_ai_notes=[]
 migrate_schedule_calendar()
 if 'appearance_history' not in st.session_state: st.session_state.appearance_history=[]
 if 'cameo_library' not in st.session_state: st.session_state.cameo_library=[]
 if 'last_cameo' not in st.session_state: st.session_state.last_cameo=None
 migrate_appearance_records()
 ensure_champion_state()
 if 'trade_history' not in st.session_state: st.session_state.trade_history=[]
 if 'factions' not in st.session_state: st.session_state.factions={c:[] for c in PLAYABLE}
 if 'story_parse' not in st.session_state: st.session_state.story_parse=None
 if 'storyline_flags' not in st.session_state: st.session_state.storyline_flags=[]
 storylines.ensure_storyline_state()
 sponsor_obj.ensure_sponsor_objectives(COMPANIES)
 if 'twitter_drama' not in st.session_state: st.session_state.twitter_drama=[]
 ensure_wrestler_stats(); ensure_wrestler_debut_fields(); ensure_contract_fields()
 crisis.ensure_crisis_state()
 showq.ensure_descriptor_state()
 twrecruit.ensure_recruitment_state()
 if 'debut_history' not in st.session_state: st.session_state.debut_history=[]
 if 'debut_warnings' not in st.session_state: st.session_state.debut_warnings=[]
 if 'rankings_include_not_debuted' not in st.session_state: st.session_state.rankings_include_not_debuted=False
 if 'confirmed_story_debuts' not in st.session_state: st.session_state.confirmed_story_debuts=[]
 if 'booking_mode' not in st.session_state: st.session_state.booking_mode='Match Card Mode'
 if 'book_show_drafts' not in st.session_state: st.session_state.book_show_drafts={}
 if 'book_show_archive' not in st.session_state: st.session_state.book_show_archive={}
 if 'ai_booked_show' not in st.session_state: st.session_state.ai_booked_show=False
 if 'show_user_edited' not in st.session_state: st.session_state.show_user_edited=False
 if 'long_story_draft' not in st.session_state: st.session_state.long_story_draft=''
 if 'last_story_analysis' not in st.session_state: st.session_state.last_story_analysis=None
 if 'active_brand' not in st.session_state: st.session_state.active_brand='NXT'
 if 'staff_character_bible' not in st.session_state:
  st.session_state.staff_character_bible={}
  for comp,rows in STAFF.items():
   for s in rows:
    st.session_state.staff_character_bible[s['name']]={'company':comp,'role':s['role'],'archetype':s['role'],'promo':s['style'],'should_do':['protect brand identity','react to shows','promote big moments'],'should_not':['sound generic'],'notes':'','handle':s['handle'],'authority':8 if 'Owner' in s['role'] or 'GM' in s['role'] else 4,'sponsor_trust':7 if 'Owner' in s['role'] else 5,'broadcast_credibility':9 if 'Commentator' in s['role'] or 'Announcer' in s['role'] else 5}
 if 'Ava' in st.session_state.staff_character_bible:
  st.session_state.staff_character_bible['Ava'].update({'archetype':'young modern authority figure controlling chaotic celebrity-heavy SmackDown','promo':'professional, direct, confident, sometimes defensive','should_do':['make matches','respond to drama','defend SmackDown'],'should_not':['sound timid','ignore roster chaos']})
 if 'tag_team_overrides' not in st.session_state: st.session_state.tag_team_overrides={}
 if 'custom_tag_teams' not in st.session_state: st.session_state.custom_tag_teams={}
 merge_custom_tag_teams_into_globals()
 if 'roster_show_staff' not in st.session_state: st.session_state.roster_show_staff=True
 if 'breakup_history' not in st.session_state: st.session_state.breakup_history=[]
 if 'former_tag_teams' not in st.session_state: st.session_state.former_tag_teams={c:[] for c in PLAYABLE}
 if 'film_projects' not in st.session_state: st.session_state.film_projects=[]
 if 'logistics_reports' not in st.session_state: st.session_state.logistics_reports=[]
 if 'exclusive_activity_history' not in st.session_state: st.session_state.exclusive_activity_history=[]
 if 'exclusive_generated_ideas' not in st.session_state: st.session_state.exclusive_generated_ideas=[]
 if 'exclusive_violations' not in st.session_state: st.session_state.exclusive_violations=[]
 ensure_nxt_unfiltered_hosts()
 apply_default_hometowns()
 sync_tag_team_individuals()
 ensure_team_profiles()
 update_rank()

def brand_tabs(label='Select Brand',key='brand_tabs'):
 prev=st.session_state.get('active_brand','NXT')
 if prev not in PLAYABLE:
  prev='NXT'
 st.markdown('<div class="brand-tabs-wrap">',unsafe_allow_html=True)
 if label: st.markdown(f'<div class="small-text" style="margin-bottom:6px"><b>{label}</b></div>',unsafe_allow_html=True)
 cols=st.columns(len(PLAYABLE))
 comp=prev
 for i,c in enumerate(PLAYABLE):
  with cols[i]:
   if st.button(c,key=f'{key}_btn_{c}',use_container_width=True,type='primary' if prev==c else 'secondary'):
    set_active_brand(c)
    st.toast(f'Now viewing {c}')
    st.rerun()
 st.session_state.active_brand=comp
 st.markdown('</div>',unsafe_allow_html=True)
 inject_brand_theme(comp)
 render_brand_permission_banner(comp)
 return comp

def roster_brand_tabs(key='rostbrand'):
 st.markdown('<div class="brand-tabs-wrap"><div class="small-text" style="margin-bottom:8px"><b>COMPANY ROSTER</b> — NXT · SmackDown · WCW</div>',unsafe_allow_html=True)
 comp=st.radio('Company',PLAYABLE,horizontal=True,key=key,label_visibility='collapsed')
 prev=st.session_state.get('_last_roster_brand')
 if prev and prev!=comp:
  st.toast(f'Now viewing {comp} roster')
  st.session_state['_roster_toast_shown']=comp
 st.session_state._last_roster_brand=comp
 if st.session_state.get('active_brand')!=comp:
  set_active_brand(comp)
 else:
  st.session_state.active_brand=comp
 inject_brand_theme(comp)
 return comp

def apply_default_hometowns():
 apply_from_locations()

def is_tag_team_entry(w):
 n=w['name']; d=w.get('division','')
 if '&' in n or ' and ' in n.lower(): return True
 if 'Tag Team' in d or 'tag team' in d.lower(): return True
 if n in TAG_TEAM_MEMBERS: return True
 return False

def is_women_entry(w):
 d=w.get('division','')
 return any(k in d for k in WOMEN_DIVISION_KW) or d=='Women'

def is_singles_entry(w):
 return not is_tag_team_entry(w) and not is_women_entry(w)

def align_badge_html(a):
 return f"<span class='align-badge-{a}'>{align(a)} ({a})</span>"

def stat_progress(label,val,color='#b026ff'):
 v=min(100,max(0,int(val)))
 return f"<div style='margin:6px 0'><div class='small-text'>{label} {v}</div><div style='background:#222;border-radius:6px;height:8px'><div style='width:{v}%;background:{color};height:8px;border-radius:6px;transition:width .2s ease-in-out'></div></div></div>"

def team_override_key(comp,name): return f'{comp}::{name}'

def get_team_override(comp,name):
 return st.session_state.tag_team_overrides.get(team_override_key(comp,name),{})

def resolve_member(mdef,comp):
 w=find(mdef['name'])
 if w:
  return {'name':w['name'],'overall':w['overall'],'alignment':w['alignment'],'from':w.get('from_location') or w.get('hometown') or mdef.get('from','Unknown'),'status':w['status'],'salary':w['salary'],'morale':w['morale'],'momentum':w['momentum'],'popularity':w['popularity'],'stamina':w['stamina'],'record':rec(w),'streak':w.get('streak','')}
 m=dict(mdef); m.setdefault('salary',default_member_salary(m.get('overall',80),900000)); return m

def tag_team_member_defs(team_name):
 if team_name in st.session_state.get('custom_tag_teams',{}):
  return list(st.session_state.custom_tag_teams[team_name])
 return TAG_TEAM_MEMBERS.get(team_name,[])

def merge_custom_tag_teams_into_globals():
 for team,members in st.session_state.get('custom_tag_teams',{}).items():
  TAG_TEAM_MEMBERS[team]=list(members)

def opts_available_tag_members(comp):
 names=[]
 for w in roster(comp):
  if is_tag_team_entry(w) or is_women_entry(w): continue
  other=tag_team_for_wrestler(w['name'],comp)
  if other and is_team_active(comp,other): continue
  names.append(w['name'])
 return sorted(set(names),key=str.lower)

def create_tag_team(comp,team_name,member_names,alignment='N',overall=None,salary=900000):
 team_name=(team_name or '').strip()
 if not team_name: return False,'Enter a team name.'
 if find(team_name): return False,f'"{team_name}" already exists on the roster.'
 uniq=[]
 for nm in member_names:
  nm=(nm or '').strip()
  if nm and nm not in uniq: uniq.append(nm)
 if len(uniq)<2: return False,'Pick at least 2 wrestlers for the team.'
 if len(uniq)>4: return False,'Maximum 4 members per team.'
 defs=[]; ovs=[]
 for nm in uniq:
  w=find(nm)
  if not w: return False,f'Could not find {nm}.'
  if w.get('company')!=comp: return False,f'{nm} is not on {comp}.'
  if is_tag_team_entry(w): return False,f'{nm} is a team name, not an individual.'
  other=tag_team_for_wrestler(nm,comp)
  if other and is_team_active(comp,other): return False,f'{nm} is already on active team {other}.'
  defs.append({'name':nm,'overall':w['overall'],'alignment':w.get('alignment',alignment),'from':w.get('from_location') or w.get('hometown') or HOMETOWNS.get(nm,''),'status':'Active'})
  ovs.append(w['overall'])
 st.session_state.setdefault('custom_tag_teams',{})[team_name]=defs
 TAG_TEAM_MEMBERS[team_name]=defs
 if comp=='WCW': WCW_DIVISIONS[team_name]='World Tag Team'
 elif comp=='SmackDown': SD_DIVISIONS[team_name]='World Tag Team'
 tovr=int(overall) if overall else int(round(sum(ovs)/len(ovs)))
 tw=W(team_name,comp,'World Tag Team',tovr,alignment,int(salary))
 st.session_state.roster.append(tw)
 st.session_state.tag_team_overrides[team_override_key(comp,team_name)]={'active':True,'chemistry_bonus':0,'history_bonus':0,'streak_bonus':0,'morale_penalty':0,'tension_penalty':0}
 sync_tag_team_individuals(); ensure_team_profiles(); sync_company_payroll_stats()
 st.session_state.news_feed.insert(0,f"{comp}: NEW TAG TEAM **{team_name}** — {', '.join(uniq)}.")
 post_team_tweet(comp,f"OFFICIAL: {team_name} are now a tag team on {comp}. {' & '.join(uniq)}.")
 return True,f'Created tag team **{team_name}** with {len(uniq)} members.'

def team_members_for(team_w,comp):
 raw=tag_team_member_defs(team_w['name'])
 if not raw:
  parts=re.split(r'\s*&\s*|\s+and\s+',team_w['name'],flags=re.I)
  raw=[{'name':p.strip(),'overall':team_w['overall'],'alignment':team_w['alignment'],'from':'','status':'Active'} for p in parts if p.strip()]
 return [resolve_member(m,comp) for m in raw]

def calc_team_alignment(members,override=None):
 if override in ('F','H','N'): return override
 alns=[m.get('alignment','N') for m in members]
 if alns and all(a=='F' for a in alns): return 'F'
 if alns and all(a=='H' for a in alns): return 'H'
 return 'N'

def calc_team_overall(team_w,members,ov):
 if ov.get('overall_manual') is not None: return int(ov['overall_manual'])
 if not members: return team_w['overall']
 base=sum(m['overall'] for m in members)/len(members)
 bonus=ov.get('chemistry_bonus',0)+ov.get('history_bonus',0)+ov.get('streak_bonus',0)-ov.get('morale_penalty',0)-ov.get('tension_penalty',0)
 return int(round(base+bonus))

def tag_team_record(team_w):
 return rec(team_w)

def is_team_active(comp,team_name):
 return get_team_override(comp,team_name).get('active',True)

def member_salary(m,comp):
 w=find(m['name'])
 return int(w['salary']) if w else int(m.get('salary',800000))

def team_salary_total(team_w,comp):
 members=team_members_for(team_w,comp)
 ov=get_team_override(comp,team_w['name'])
 bonus=int(ov.get('team_contract_bonus',0))
 return sum(member_salary(m,comp) for m in members)+bonus

def payroll_wrestlers(comp):
 return [w for w in roster(comp) if not is_tag_team_entry(w)]

def company_payroll(comp):
 return sum(w['salary'] for w in payroll_wrestlers(comp))

def _new_company_finance(comp):
 pay=company_payroll(comp)
 saved_b=st.session_state.get('company_budgets',{}).get(comp)
 fin_rec=(st.session_state.get('company_finance') or {}).get(comp) if isinstance(st.session_state.get('company_finance'),dict) else None
 if isinstance(fin_rec,dict) and fin_rec.get('current_budget') is not None:
  cur=int(fin_rec['current_budget'])
 elif saved_b is not None and (st.session_state.get('week',0)>0 or int(saved_b)!=STARTING_BUDGET):
  cur=int(saved_b)
 else:
  cur=STARTING_BUDGET
 return {
  'starting_budget':STARTING_BUDGET,'payroll':pay,'current_budget':cur,
  'season_revenue':0,'season_expenses':0,'season_profit_loss':0,'weekly_last_pl':0,
  'sponsor_savings_total':0,'merch_revenue_total':0,'media_revenue_total':0,
  'appearance_revenue_total':0,'trade_cash_out':0,'trade_cash_in':0,'attraction_spending':0,
  'contract_spending_total':0,'random_event_net':0,'biggest_gain':{'amount':0,'label':''},'biggest_expense':{'amount':0,'label':''},'last_money_change':None,
 }

def apply_season_opening_payroll():
 """Deduct each company's payroll once at season start — ledger + separate banks."""
 if st.session_state.get('finance_opening_applied'): return
 # Mark applied before add_transaction — add_transaction calls ensure_finance_state which would re-enter here.
 st.session_state.finance_opening_applied=True
 cf=st.session_state.get('company_finance') or {}
 for c in PLAYABLE:
  fin=cf.get(c) or {}
  pay=int(fin.get('payroll',0) or company_payroll(c))
  if pay<=0: continue
  already=any(t.get('company')==c and t.get('category')=='Payroll' for t in st.session_state.get('finance_ledger',[]))
  if not already:
   st.session_state.company_finance[c]['current_budget']=STARTING_BUDGET
   add_transaction(c,'Payroll',f'Season opening payroll — {c} roster salaries',-pay,0,source='season_start',toast=False)

def ensure_finance_state():
 st.session_state.finance_ledger=st.session_state.get('finance_ledger',[])
 st.session_state.show_finance_reports=st.session_state.get('show_finance_reports',[])
 if not isinstance(st.session_state.get('company_finance'),dict):
  st.session_state.company_finance={}
 cf=st.session_state.company_finance
 fin_keys={'starting_budget','payroll','current_budget'}
 for c in PLAYABLE:
  rec=cf.get(c)
  if not isinstance(rec,dict) or not fin_keys.issubset(rec.keys()):
   cf[c]=_new_company_finance(c)
  else:
   rec['payroll']=company_payroll(c)
   rec.setdefault('starting_budget',STARTING_BUDGET)
   rec.setdefault('season_revenue',0); rec.setdefault('season_expenses',0); rec.setdefault('season_profit_loss',0)
   rec.setdefault('weekly_last_pl',0); rec.setdefault('sponsor_savings_total',0); rec.setdefault('merch_revenue_total',0)
   rec.setdefault('media_revenue_total',0); rec.setdefault('appearance_revenue_total',0)
   rec.setdefault('trade_cash_out',0); rec.setdefault('trade_cash_in',0); rec.setdefault('attraction_spending',0)
   rec.setdefault('contract_spending_total',0)
   rec.setdefault('random_event_net',0); rec.setdefault('biggest_gain',{'amount':0,'label':''}); rec.setdefault('biggest_expense',{'amount':0,'label':''})
   rec.setdefault('last_money_change',rec.get('last_money_change'))
  st.session_state.company_budgets[c]=int(cf[c]['current_budget'])
 if st.session_state.get('week',0)>0 or len(st.session_state.get('finance_ledger',[]))>3:
  st.session_state.finance_opening_applied=True
 else:
  apply_season_opening_payroll()
 sync_universe_bank()

def sync_universe_bank():
 st.session_state.bank=sum(st.session_state.company_finance[c]['current_budget'] for c in PLAYABLE) if st.session_state.get('company_finance') else st.session_state.get('bank',STARTING_BUDGET*3)

def get_company_budget(comp):
 ensure_finance_state()
 return int(st.session_state.company_finance[comp]['current_budget'])

def company_remaining_budget(comp):
 return get_company_budget(comp)

def sync_company_payroll_stats():
 """Refresh payroll totals only; does not reset current budgets."""
 ensure_finance_state()
 for c in PLAYABLE:
  st.session_state.company_finance[c]['payroll']=company_payroll(c)

def sync_company_budgets():
 """Legacy alias — payroll refresh only."""
 sync_company_payroll_stats()

def _track_finance_category(fin,category,amount):
 if amount>0:
  if 'Savings' in category or category=='Sponsor Savings': fin['sponsor_savings_total']+=amount
  elif category=='Merchandise Revenue': fin['merch_revenue_total']+=amount
  elif category in ('Media Revenue','Cameo Revenue','Film Revenue'): fin['media_revenue_total']+=amount
  elif category in ('Appearance Revenue','Exclusive Appearance'): fin['appearance_revenue_total']+=amount
  elif category=='Trade Cash Received': fin['trade_cash_in']+=amount
  if amount>fin['biggest_gain']['amount']: fin['biggest_gain']={'amount':amount,'label':category}
 else:
  a=abs(amount)
  if category=='Attraction Cost': fin['attraction_spending']+=a
  elif category=='Trade Cash Sent': fin['trade_cash_out']+=a
  elif category in ('Signing Bonus','Free Agent Signing Bonus','Release Fee','Contract Bonus','Renewal Bonus'): fin['contract_spending_total']+=a
  elif category=='Random Event': fin['random_event_net']+=amount
  if a>fin['biggest_expense']['amount']: fin['biggest_expense']={'amount':a,'label':category}

def add_transaction(company,category,description,amount,week=None,source='',toast=None):
 ensure_finance_state()
 week=int(week if week is not None else st.session_state.week)
 fin=st.session_state.company_finance[company]
 before=int(fin['current_budget'])
 after=before+int(amount)
 fin['current_budget']=after
 st.session_state.company_budgets[company]=after
 if amount>=0:
  fin['season_revenue']+=amount
 else:
  fin['season_expenses']+=abs(amount)
 fin['season_profit_loss']=fin['season_revenue']-fin['season_expenses']
 _track_finance_category(fin,category,amount)
 ts=datetime.now().isoformat(timespec='seconds')
 entry={'week':week,'company':company,'category':category,'description':description,'amount':int(amount),'budget_before':before,'budget_after':after,'source':source or category,'timestamp':ts}
 st.session_state.finance_ledger.insert(0,entry)
 fin['last_money_change']={'week':week,'category':category,'description':description,'amount':int(amount),'budget_before':before,'budget_after':after,'timestamp':ts}
 if int(amount):
  st.session_state.setdefault('money_meter_flash',[])
  st.session_state.money_meter_flash.insert(0,{'company':company,'amount':int(amount),'category':category,'description':description})
  st.session_state.money_meter_flash=st.session_state.money_meter_flash[:8]
 sync_universe_bank()
 do_toast=toast if toast is not None else bool(amount)
 if do_toast and amount:
  money_meter_toast(company,int(amount),category,description)
 return after,entry

def finance_flash(company,amount,description):
 if amount: money_meter_toast(company,int(amount),description,description)
 color='#2ecc71' if amount>=0 else '#e74c3c'
 sign='+' if amount>=0 else '−'
 st.markdown(f"<div class='money-meter-flash {'gain' if amount>=0 else 'loss'}'>{company} {sign}{money(abs(amount))} — {description}. New bank: {money(get_company_budget(company))}.</div>",unsafe_allow_html=True)

def appearance_revenue_for(company,appearance):
 ranges={
  'NXT':{'Netflix':(1500000,3000000),'Marvel':(3000000,7000000),'DC':(3000000,7000000),'Hollywood':(5000000,12000000),'SNL':(500000,1500000),'Good Morning America':(300000,900000),'Olympics':(600000,1500000),'Oscars':(800000,2000000),'Mattel':(1000000,5000000),'Barbie':(1000000,5000000)},
  'SmackDown':{'Grammys':(1000000,4000000),'music video':(500000,2000000),'concert':(750000,2500000),'Paramount':(1000000,3000000),'USA Network':(1000000,3000000),'TNT':(1000000,3000000)},
  'WCW':{'NBA':(1500000,4000000),'NFL':(2000000,6000000),'Draft':(750000,2000000),'ESPN':(500000,2000000),'CBS':(500000,2000000),'Super Bowl':(2000000,7000000)},
 }
 base={'NXT':1200000,'SmackDown':900000,'WCW':1100000}.get(company,800000)
 lo,hi=base,base+random.randint(200000,900000)
 app_l=appearance.lower()
 for comp_tbl in (ranges.get(company,{}),ranges.get('NXT',{})):
  for k,v in comp_tbl.items():
   if k.lower() in app_l: lo,hi=v; break
 return random.randint(lo,hi)

def random_event_cash(event_or_rec):
 if isinstance(event_or_rec,dict): return int(event_or_rec.get('money',0))
 ev=str(event_or_rec)
 for t in RANDOM_EVENT_CATALOG:
  if t['name'] in ev and t.get('money'):
   m=t['money']; return random.randint(m[0],m[1]) if isinstance(m,tuple) else int(m)
 return random.choice([-500000,250000,750000,1200000])

def apply_show_finances(company,log,week=None):
 week=int(week if week is not None else st.session_state.week)
 old=get_company_budget(company)
 rev_rows=[
  ('Ticket Revenue','Ticket sales',log.get('ticket_revenue',0)),
  ('Merchandise Revenue','Merchandise sales',log.get('merchandise_revenue',0)),
  ('Sponsor Revenue','Sponsor activation',log.get('sponsor_revenue',0)),
  ('Media Revenue','Media production',log.get('media_revenue',0)),
  ('Film Revenue','Active filming revenue',log.get('movie_revenue',0)),
  ('Market Bonus','City/market bonus',log.get('market_bonus',0)),
  ('PLE Bonus','PLE gate bonus',log.get('ple_bonus',0)),
  ('Stadium Bonus','Stadium show bonus',log.get('stadium_bonus',0)),
  ('Viral Twitter Bonus','Twitter buzz bonus',log.get('viral_twitter_bonus',0)),
 ]
 exp_rows=[
  ('Venue Rental','Arena rental',log.get('venue_rental',0)),
  ('Security','Event security',log.get('security_cost',0)),
  ('Production','Show production',log.get('production_cost',0)),
  ('Catering','Roster catering',log.get('catering_cost',0)),
  ('Insurance','Event insurance',log.get('insurance_cost',0)),
  ('Advertising','Weekly/ PLE advertising',log.get('advertising_cost',0)),
  ('Sponsor Activation','Sponsor activation spend',log.get('sponsor_activation_cost',0)),
  ('Special Match Production','Special stipulations',log.get('special_match_production',0)),
  ('Media Production Cost','Extra media production',log.get('media_production_cost',0)),
  ('International Travel','International fees',log.get('international_travel_fees',0)),
  ('Medical Cost','Medical / injury care',log.get('medical_cost',0)),
 ]
 for cat,desc,amt in rev_rows:
  if amt: add_transaction(company,cat,f"{log.get('show_name','Show')}: {desc}",int(amt),week,toast=False)
 if log.get('hotel_base',0):
  add_transaction(company,'Hotel Cost',f"Hotel base ({log.get('show_name','')})",-int(log['hotel_base']),week,toast=False)
 if log.get('hotel_savings',0):
  sp=log.get('hotel_sponsor') or 'Marriott'
  add_transaction(company,f'{sp} Hotel Savings',f"{sp} covered hotel costs (saved {money(log['hotel_savings'])})",int(log['hotel_savings']),week,source='sponsor',toast=False)
 if log.get('transport_base',0):
  add_transaction(company,'Transportation Cost',f"Transportation base",-int(log['transport_base']),week,toast=False)
 if log.get('transport_savings',0):
  sp=log.get('transport_sponsor') or 'Tesla/Mercedes'
  add_transaction(company,f'{sp} Transportation Savings',f"{sp} covered transportation (saved {money(log['transport_savings'])})",int(log['transport_savings']),week,source='sponsor',toast=False)
 for cat,desc,amt in exp_rows:
  if amt: add_transaction(company,cat,f"{log.get('show_name','Show')}: {desc}",-int(amt),week,toast=False)
 profit=int(log.get('profit_loss',0))
 if profit:
  money_meter_toast(company,profit,'Show Profit/Loss',f"{log.get('show_name','Show')} final P/L")
 new=get_company_budget(company)
 st.session_state.company_finance[company]['weekly_last_pl']=profit
 report={
  'week':week,'company':company,'show_name':log.get('show_name',''),'venue':log.get('venue',''),'city':log.get('city',''),
  'revenue':{'ticket':log.get('ticket_revenue',0),'merchandise':log.get('merchandise_revenue',0),'sponsor':log.get('sponsor_revenue',0),'media':log.get('media_revenue',0),'film':log.get('movie_revenue',0),'market_bonus':log.get('market_bonus',0),'ple_bonus':log.get('ple_bonus',0),'stadium_bonus':log.get('stadium_bonus',0),'viral_twitter_bonus':log.get('viral_twitter_bonus',0)},
  'attendance':log.get('attendance',0),'viewership':log.get('viewership',0),
  'expenses':{'venue':log.get('venue_rental',0),'security':log.get('security_cost',0),'production':log.get('production_cost',0),'hotel_base':log.get('hotel_base',0),'hotel_savings':log.get('hotel_savings',0),'hotel_final':log.get('hotel_final',0),'transport_base':log.get('transport_base',0),'transport_savings':log.get('transport_savings',0),'transport_final':log.get('transport_final',0),'medical':log.get('medical_cost',0),'advertising':log.get('advertising_cost',0),'special_match':log.get('special_match_production',0)},
  'total_revenue':log.get('weekly_income',0),'total_expenses':log.get('weekly_expenses',0),'profit_loss':profit,
  'budget_before':old,'budget_after':new,'ai_notes':log.get('ai_notes',[]),
 }
 st.session_state.show_finance_reports.insert(0,report)
 st.session_state.last_profit_loss=profit
 st.session_state.last_money_generated=log.get('weekly_income',0)
 st.session_state.last_money_lost=log.get('weekly_expenses',0)
 st.session_state.last_transportation_cost=log.get('transport_final',0)+log.get('security_cost',0)
 st.session_state.last_medical_cost=log.get('medical_cost',0)
 st.session_state.last_ad_money=log.get('media_revenue',0)+log.get('sponsor_revenue',0)
 st.session_state.last_hotel_cost=log.get('hotel_final',0)
 st.session_state.last_hotel_savings=log.get('hotel_savings',0)
 st.session_state.last_transport_savings=log.get('transport_savings',0)
 return report

def default_member_salary(overall,team_salary):
 return max(300000,min(2000000,int(team_salary*0.45) if team_salary else overall*10000))

def sync_tag_team_individuals():
 existing={w['name'] for w in st.session_state.roster}
 for tw in list(st.session_state.roster):
  if not is_tag_team_entry(tw): continue
  comp=tw['company']; team=tw['name']
  if not is_team_active(comp,team): continue
  defs=tag_team_member_defs(team)
  if not defs:
   parts=re.split(r'\s*&\s*|\s+and\s+',team,flags=re.I)
   defs=[{'name':p.strip(),'overall':tw['overall'],'alignment':tw['alignment'],'from':'','status':'Active'} for p in parts if p.strip()]
  sing_div=DEFAULT_SINGLES_DIV.get(comp,'Roster')
  for m in defs:
   nm=m['name']
   if nm in existing:
    ind=find(nm)
    if ind:
     ind['tag_team_affiliation']=team
     if not ind.get('hometown'): ind['hometown']=m.get('from',HOMETOWNS.get(nm,''))
    continue
   sal=default_member_salary(m['overall'],tw.get('salary',900000))
   nw=W(nm,comp,sing_div,m['overall'],m.get('alignment','N'),sal)
   nw['hometown']=m.get('from',HOMETOWNS.get(nm,''))
   nw['tag_team_affiliation']=team
   st.session_state.roster.append(nw); existing.add(nm)
 sync_company_payroll_stats()

def post_team_tweet(comp,text,tag='Tag Team Update'):
 st.session_state.twitter_posts.insert(0,{'id':len(st.session_state.twitter_posts)+1,'week':st.session_state.week,'company':comp,'wrestler':comp+' Desk','role':'Company','handle':'@'+slug(comp),'post_type':tag,'text':text,'likes':random.randint(1500,45000),'reposts':random.randint(100,9000),'replies':random.randint(50,2500),'views':random.randint(20000,400000),'mentions':'','effects':{},'viral':random.random()>.7,'ai_generated':False})

def break_up_team(team_w,comp):
 ok=team_override_key(comp,team_w['name'])
 ov=st.session_state.tag_team_overrides.setdefault(ok,{})
 ov['active']=False
 members=team_members_for(team_w,comp)
 sing_div=DEFAULT_SINGLES_DIV.get(comp,'Roster')
 names=[]
 for m in members:
  ind=find(m['name'])
  if not ind: continue
  names.append(ind['name'])
  ind['division']=sing_div
  ind['tag_team_affiliation']=''
  ind['morale']=max(0,min(100,ind['morale']-random.randint(4,14)))
  ind['momentum']=max(0,ind['momentum']-random.randint(0,6))
 rec_bp={'week':st.session_state.week,'company':comp,'team':team_w['name'],'members':names,'reason':'Break up'}
 st.session_state.breakup_history.insert(0,rec_bp)
 st.session_state.former_tag_teams.setdefault(comp,[]).append(team_w['name'])
 if len(names)>=2:
  st.session_state.rivalries.append({'wrestlers':names[:2],'heat':random.randint(6,12),'story':f'Former {team_w["name"]} partners — breakup fallout','week':st.session_state.week})
 post_team_tweet(comp,f"BREAKING: {team_w['name']} have broken up on {comp}. Former partners may collide soon.")
 st.session_state.news_feed.insert(0,f"{comp}: {team_w['name']} broken up. Members moved to singles roster.")
 sync_company_payroll_stats()

def move_member_to_singles(comp,team_name,member_name):
 ind=find(member_name)
 if ind:
  ind['division']=DEFAULT_SINGLES_DIV.get(comp,'Roster')
  ind['tag_team_affiliation']=''
  st.session_state.news_feed.insert(0,f"{member_name} moved to singles division on {comp}.")

def set_team_alignment(comp,team_name,align_code):
 ov=st.session_state.tag_team_overrides.setdefault(team_override_key(comp,team_name),{})
 ov['alignment_manual']=align_code
 members=tag_team_member_defs(team_name)
 for m in members:
  w=find(m['name'])
  if w: w['alignment']=align_code

def set_member_alignment(member_name,align_code):
 w=find(member_name)
 if w: w['alignment']=align_code

def save_tag_team_defs(team_name,defs):
 TAG_TEAM_MEMBERS[team_name]=list(defs)
 if team_name in st.session_state.get('custom_tag_teams',{}):
  st.session_state.custom_tag_teams[team_name]=list(defs)

def add_tag_member(comp,team_name,new_name,overall=None):
 defs=tag_team_member_defs(team_name)
 if any(m['name']==new_name for m in defs): return
 defs.append({'name':new_name,'overall':overall or 80,'alignment':'N','from':HOMETOWNS.get(new_name,''),'status':'Active'})
 save_tag_team_defs(team_name,defs)
 if not find(new_name):
  nw=W(new_name,comp,DEFAULT_SINGLES_DIV.get(comp,'Roster'),overall or 80,'N',800000)
  nw['hometown']=HOMETOWNS.get(new_name,''); nw['tag_team_affiliation']=team_name
  st.session_state.roster.append(nw)
 else:
  find(new_name)['tag_team_affiliation']=team_name
 sync_tag_team_individuals()

def replace_tag_member(comp,team_name,old_name,new_name,overall=None):
 defs=tag_team_member_defs(team_name)
 if old_name and old_name!='__none__':
  defs=[m for m in defs if m['name']!=old_name]
  move_member_to_singles(comp,team_name,old_name)
 if not any(m['name']==new_name for m in defs):
  defs.append({'name':new_name,'overall':overall or 80,'alignment':'N','from':HOMETOWNS.get(new_name,''),'status':'Active'})
 save_tag_team_defs(team_name,defs)
 if not find(new_name):
  nw=W(new_name,comp,DEFAULT_SINGLES_DIV.get(comp,'Roster'),overall or 80,'N',800000)
  nw['hometown']=HOMETOWNS.get(new_name,''); nw['tag_team_affiliation']=team_name
  st.session_state.roster.append(nw)
 else:
  find(new_name)['tag_team_affiliation']=team_name
 sync_tag_team_individuals()

def booked_names_from_show(matches,promos):
 names=set()
 for m in matches:
  for n in m.get('participants',[]):
   if n not in ('None','TBD','NC'): names.add(n)
 for p in promos:
  for n in p.get('participants',[]):
   if n!='None': names.add(n)
 return names

def calc_merchandise_revenue(company,booked_names,rating,ple):
 rules=COMPANY_LOGISTICS_RULES[company]
 base=180000
 total=base
 notes=[]
 for nm in booked_names:
  w=find(nm)
  if not w or w['company']!=company: continue
  pop=w['popularity']; mom=w['momentum']; heat=w.get('rivalry_heat',0)+rivalry_heat_for(nm)
  rev=pop*1200+mom*800+heat*5000
  if is_champ(nm): rev+=250000; notes.append(f'{nm} title replica sales')
  if pop>=85 and mom>=75:
   rev+=random.randint(400000,1200000)
   partner=random.choice(rules.get('merch_partners',['Partner']))
   notes.append(f'{partner} merch boom — {nm}')
  if w.get('twitter_buzz',0) or pop>=80: rev+=random.randint(50000,200000)
  total+=int(rev)
 if ple: total=int(total*1.35)
 total=int(total*(1+rating*.04))
 return total,notes

def calc_media_revenue(company,rating,ple):
 mult={'NXT':1.15,'SmackDown':1.05,'WCW':1.1}.get(company,1)
 base=200000*mult
 if ple: base*=1.6
 return int(base*(1+rating*.05))

def calc_sponsor_revenue(company,rating,ple):
 sponsors=COMPANIES[company]['sponsors']
 base=len(sponsors)*25000
 if ple: base*=2.2
 return int(base*(1+rating*.06))

def active_filming_revenue(company):
 total=0
 for f in st.session_state.get('film_projects',[]):
  if f.get('company')==company and f.get('status')=='active':
   total+=int(f.get('revenue',0))
 return total

def compute_show_logistics(company,venue,matches,promos,rating,ple,episode,show_name):
 rules=COMPANY_LOGISTICS_RULES[company]
 tm=venue.get('travel_multiplier',1.1)
 hotel_base=int(LOGISTICS_BASE['hotel']*tm)
 transport_base=int(LOGISTICS_BASE['transport']*tm)
 hotel_cov=rules.get('hotel_coverage',0)
 transport_cov=rules.get('transport_coverage',0)
 hotel_savings=int(hotel_base*hotel_cov) if rules.get('hotel_sponsor') else 0
 transport_savings=int(transport_base*transport_cov) if rules.get('transport_sponsor') else 0
 hotel_final=max(0,hotel_base-hotel_savings)
 transport_final=max(0,transport_base-transport_savings)
 venue_rental=int(venue.get('rental_cost',400000))
 security=int(venue.get('security_cost',125000))
 production=int(LOGISTICS_BASE['production'])
 special_prod=0
 medical=int(LOGISTICS_BASE['medical'])
 for m in matches:
  eff=MATCH_EFFECTS.get(m.get('stip','Normal'),DEFAULT_MATCH_EFFECT)
  production+=int(80000*eff.get('cost',0))
  special_prod+=int(120000*max(0,eff.get('cost',0)))
  medical+=int(25000*eff.get('injury',1))
 catering=int(LOGISTICS_BASE['catering']*tm)
 insurance=int(LOGISTICS_BASE['insurance'])
 advertising=int(LOGISTICS_BASE['advertising_ple' if ple else 'advertising_weekly'])
 sponsor_activation=int(LOGISTICS_BASE['sponsor_activation_ple' if ple else 'sponsor_activation_weekly'])
 media_production=int(LOGISTICS_BASE['media_production'])
 intl_fees=200000 if venue.get('country')!='United States' else 0
 booked=booked_names_from_show(matches,promos)
 attendance=calc_show_attendance(company,venue,rating,ple,episode,booked)
 ticket_revenue=calc_ticket_revenue(attendance,venue,episode,ple)
 merch_rev,merch_notes=calc_merchandise_revenue(company,booked,rating,ple)
 media_rev=calc_media_revenue(company,rating,ple)
 sponsor_rev=calc_sponsor_revenue(company,rating,ple)
 movie_rev=active_filming_revenue(company)
 market_bonus=int(venue.get('market_bonus',0))
 ple_bonus=int(250000 if ple else 0)
 stadium_bonus=int(400000 if 'Stadium' in (episode or '') else 0)
 tw_buzz=sum(1 for p in st.session_state.twitter_posts[:15] if p.get('company')==company)
 viral_twitter_bonus=int(min(350000,tw_buzz*50000)) if float(rating or 7)>=7.5 and tw_buzz>=2 else 0
 weekly_income=ticket_revenue+merch_rev+media_rev+sponsor_rev+movie_rev+market_bonus+ple_bonus+stadium_bonus+viral_twitter_bonus
 weekly_expenses=venue_rental+security+production+hotel_final+transport_final+medical+catering+insurance+advertising+sponsor_activation+special_prod+media_production+intl_fees
 profit=weekly_income-weekly_expenses
 ai_notes=[]
 if rules.get('hotel_sponsor'): ai_notes.append(f"{company} saved money because {rules['hotel_sponsor']} covered hotels ({money(hotel_savings)}).")
 elif company=='NXT': ai_notes.append('NXT paid full hotel and transportation, but can offset costs through Mattel/DC/Netflix merchandise.')
 if rules.get('transport_sponsor'): ai_notes.append(f"{company} saved money because {rules['transport_sponsor']} covered transportation ({money(transport_savings)}).")
 if any('Ultimate X' in m.get('stip','') for m in matches): ai_notes.append('Ultimate X match increased production and medical risk.')
 if any('Anarchy' in m.get('stip','') for m in matches): ai_notes.append('Anarchy in the Arena match cost more but can boost rating.')
 if merch_notes: ai_notes.append(merch_notes[0])
 return {
  'show_name':show_name,'company':company,'venue':venue.get('venue',''),'city':venue.get('city',''),'region':venue.get('region',''),'country':venue.get('country',''),
  'attendance':attendance,'ticket_revenue':ticket_revenue,'merchandise_revenue':merch_rev,'media_revenue':media_rev,'sponsor_revenue':sponsor_rev,'movie_revenue':movie_rev,'market_bonus':market_bonus,'ple_bonus':ple_bonus,'stadium_bonus':stadium_bonus,'viral_twitter_bonus':viral_twitter_bonus,'ticket_price':ticket_price_for_episode(episode,ple),
  'venue_rental':venue_rental,'security_cost':security,'production_cost':production,'hotel_base':hotel_base,'hotel_sponsor':rules.get('hotel_sponsor'),'hotel_savings':hotel_savings,'hotel_final':hotel_final,
  'transport_base':transport_base,'transport_sponsor':rules.get('transport_sponsor'),'transport_savings':transport_savings,'transport_final':transport_final,
  'medical_cost':medical,'catering_cost':catering,'insurance_cost':insurance,'advertising_cost':advertising,'sponsor_activation_cost':sponsor_activation,
  'special_match_production':special_prod,'media_production_cost':media_production,'international_travel_fees':intl_fees,
  'weekly_income':weekly_income,'weekly_expenses':weekly_expenses,'profit_loss':profit,'merch_notes':merch_notes,'ai_notes':ai_notes,
 }

def reconcile_show_logistics_with_results(log,rating,view_data,episode,venue,company,matches,promos,ple,breakdown=None,feedback=None,featured='',rival=''):
 """Recalc attendance/ticket/revenue after final grade and viewership — only affects this company."""
 booked=booked_names_from_show(matches,promos)
 vw=int(view_data.get('viewership',0))
 att=calc_show_attendance(company,venue,rating,ple,episode,booked,vw)
 ticket=calc_ticket_revenue(att,venue,episode,ple)
 merch_rev,merch_notes=calc_merchandise_revenue(company,booked,rating,ple)
 media_rev=calc_media_revenue(company,rating,ple)+max(0,vw//800)
 sponsor_rev=calc_sponsor_revenue(company,rating,ple)
 if vw>=2_500_000: sponsor_rev=int(sponsor_rev*1.08)
 ple_bonus=int(log.get('ple_bonus',250000 if ple else 0))
 stadium_bonus=int(log.get('stadium_bonus',0))
 tw_buzz=sum(1 for p in st.session_state.twitter_posts[:15] if p.get('company')==company)
 viral=int(log.get('viral_twitter_bonus',0))
 if float(rating or 7)>=7.5 and tw_buzz>=2: viral=max(viral,int(min(350000,tw_buzz*50000)))
 weekly_income=ticket+merch_rev+media_rev+sponsor_rev+log.get('movie_revenue',0)+log.get('market_bonus',0)+ple_bonus+stadium_bonus+viral
 weekly_expenses=log.get('weekly_expenses',0)
 log.update({'attendance':att,'ticket_revenue':ticket,'ticket_price':ticket_price_for_episode(episode,ple),'merchandise_revenue':merch_rev,'media_revenue':media_rev,'sponsor_revenue':sponsor_rev,'ple_bonus':ple_bonus,'stadium_bonus':stadium_bonus,'viral_twitter_bonus':viral,'viewership':vw,'weekly_income':weekly_income,'profit_loss':weekly_income-weekly_expenses,'merch_notes':merch_notes})
 if merch_notes and log.get('ai_notes') is not None: log['ai_notes']=list(log.get('ai_notes',[]))+merch_notes[:1]
 sponsors=COMPANIES.get(company,{}).get('sponsors',[])
 log,_pkg=showq.apply_show_quality_to_log(log,company,venue,matches,promos,rating,feedback or {},breakdown or {},featured,rival,ple,find,is_champion_name,rivalry_heat_for,sponsors=sponsors)
 return log

def logistics_ai_summary(log):
 return ' '.join(log.get('ai_notes',[])[:4])

def capture_roster_stat_snapshot(company,names):
 out={}
 for nm in names or []:
  w=find(nm)
  if w and w.get('company')==company:
   out[nm]={'popularity':int(w.get('popularity',0)),'morale':int(w.get('morale',0)),'momentum':int(w.get('momentum',0)),'twitter_buzz':int(w.get('twitter_buzz',0))}
 return out

def capture_rivalry_heat_snapshot(company,names):
 out={}
 nm_set=set(names or [])
 for r in st.session_state.get('rivalries',[]):
  if r.get('company',company)!=company: continue
  involved=any(n in r.get('name','') or n in (r.get('wrestlers') or []) for n in nm_set)
  if involved or not nm_set:
   out[r.get('name',r.get('id','Rivalry'))]=int(r.get('heat',50))
 return out

def company_roster_buzz_sum(company,names=None):
 total=0
 for nm in (names or [w['name'] for w in roster(company)]):
  w=find(nm)
  if w: total+=int(w.get('twitter_buzz',0))
 return total

def sellout_label(attendance,capacity):
 cap=max(1,int(capacity or 1)); att=max(0,int(attendance or 0)); pct=100*att/cap
 if pct>=97: return 'Sellout',pct
 if pct>=90: return 'Near Sellout',pct
 if pct>=80: return 'Strong Crowd',pct
 if pct>=65: return 'Good Crowd',pct
 if pct>=50: return 'Soft Crowd',pct
 return 'Weak Attendance',pct

def performance_rating_label(score):
 s=float(score or 0)
 if s>=9.5: return 'Legendary show'
 if s>=9: return 'Excellent'
 if s>=8: return 'Strong'
 if s>=7: return 'Good'
 if s>=6: return 'Average'
 if s>=5: return 'Weak'
 return 'Bad show'

def wrestler_change_reason(name,ch,fb,reasons,featured,rival):
 pop=ch.get('popularity',0); mor=ch.get('morale',0); mom=ch.get('momentum',0)
 if pop>4 or mom>4:
  if name==featured: return f'Featured star momentum — strong main-event usage paid off.'
  if reasons.get(name): return reasons[name][:200]
  if fb.get('worked'): return str(fb['worked'][0])[:200]
  return 'Strong in-ring or promo work connected with fans this week.'
 if pop<-2 or mor<-3:
  if fb.get('dropped') and any(name.lower() in str(d).lower() for d in fb.get('dropped',[])): return f"Story ignored {name} for another week — fans stopped investing."
  if fb.get('struggled'): return f"Weak segment usage — {str(fb['struggled'][0])[:120]}"
  return 'Limited story follow-up — crowd investment cooled.'
 if mor>2: return 'Locker room morale lifted after a solid showing.'
 if mor<-2: return 'Frustration from poor booking or ignored angle.'
 if rival and name in str(rival): return f'Rivalry with {rival} advanced — heat changed locker-room energy.'
 return 'Routine weekly roster movement from show quality and usage.'

def rivalry_change_reason(name,delta,fb):
 if delta>5: return 'The feud advanced emotionally with strong TV usage and crowd investment.'
 if delta>0: return 'Story progressed — fans are still tracking the angle.'
 if delta<-5: return 'The angle was not followed up — fan investment dropped.'
 if delta<0: return 'Weak follow-up hurt momentum for this rivalry.'
 if fb.get('dropped'): return str(fb['dropped'][0])[:200]
 return 'Rivalry held steady with limited advancement.'

def apply_post_show_consequences(company,rating,breakdown,ple,feedback,log=None):
 """AI-determined prestige, sponsor, and title consequences — stronger on PLEs."""
 prof=st.session_state.company_profiles.setdefault(company,{})
 r=float(rating or 7); story=_breakdown_val(breakdown,'Story'); emo=_breakdown_val(breakdown,'Emotion')
 champ=_breakdown_val(breakdown,'Champion'); mult=1.6 if ple else 1.0
 notes=[]
 if r>=8:
  dp=int(round((2+(r-8)*2)*mult)); notes.append(f'Company prestige +{dp}')
 elif r<6:
  dp=-int(round((2+(6-r)*1.2)*mult)); notes.append(f'Company prestige {dp}')
 else:
  dp=0; notes.append('Company prestige held steady')
 prof['prestige']=max(1,min(100,int(prof.get('prestige',85))+dp))
 sc=int(prof.get('sponsor_confidence',85))
 if r>=8: sc+=int(round(3*mult)); notes.append(f'Sponsor confidence +{int(round(3*mult))}')
 elif r<6: sc-=int(round(4*mult)); notes.append(f'Sponsor confidence -{int(round(4*mult))}')
 prof['sponsor_confidence']=max(1,min(100,sc))
 if ple and champ<6:
  for t in st.session_state.champions.get(company,{}):
   adjust_title_prestige(company,t,-4)
  notes.append('Title prestige -4 (weak PLE title usage)')
 elif ple and champ>=8:
  for t in st.session_state.champions.get(company,{}):
   adjust_title_prestige(company,t,4)
  notes.append('Title prestige +4 (strong PLE title matches)')
 if log is not None:
  log['prestige_delta']=dp; log['sponsor_confidence']=prof['sponsor_confidence']; log['consequence_notes']=notes
  sq=log.get('show_quality',{}) if isinstance(log,dict) else {}
  cu=sq.get('champion_usage',{}) or {}
  tp=int((cu.get('multipliers') or {}).get('title_prestige',0))
  if tp:
   for t in st.session_state.champions.get(company,{}):
    adjust_title_prestige(company,t,tp)
   notes.append(f'Title prestige {tp:+} from champion usage')
  for ign in cu.get('ignored',[]) or []:
   w=find(ign)
   if w and w.get('company')==company:
    w['fan_investment']=max(0,int(w.get('fan_investment',50))-3)
    w['fan_support']=w['fan_investment']
 return notes

def build_ai_performance_analysis(hist,grade_result,view_data,fin_report,log,stat_before,stat_after,rival_before,rival_after,buzz_before,buzz_after,reasons=None,ple=False):
 """Full AI-determined weekly performance record from show grade + outcomes."""
 rating=float(grade_result.get('rating',hist.get('episode_rating',7)))
 breakdown=grade_result.get('breakdown',hist.get('rating_breakdown',{}))
 fb=grade_result.get('feedback',hist.get('ai_feedback',{})) or {}
 reasons=reasons or {}
 lg=hist.get('logistics') or {}
 company=hist.get('company'); week=int(hist.get('week',0))
 cap=int(hist.get('capacity') or lg.get('capacity',15000))
 att=int(lg.get('attendance',0))
 status,pct=sellout_label(att,cap)
 stat_changes={}
 wrestler_rows=[]
 for nm in sorted(set(stat_before)|set(stat_after)):
  b=stat_before.get(nm,{}); a=stat_after.get(nm,{})
  if not b and not a: continue
  ch={'popularity':int(a.get('popularity',0))-int(b.get('popularity',0)),'morale':int(a.get('morale',0))-int(b.get('morale',0)),'momentum':int(a.get('momentum',0))-int(b.get('momentum',0)),'twitter_buzz':int(a.get('twitter_buzz',0))-int(b.get('twitter_buzz',0)),'before':b,'after':a}
  ch['reason']=wrestler_change_reason(nm,ch,fb,reasons,hist.get('featured_star'),hist.get('top_rivalry'))
  stat_changes[nm]=ch
  wrestler_rows.append({'name':nm,**ch})
 rivalry_rows=[]
 rivalry_changes={}
 for rk in sorted(set(rival_before)|set(rival_after)):
  hb=rival_before.get(rk,50); ha=rival_after.get(rk,hb); d=ha-hb
  rivalry_changes[rk]=d
  rivalry_rows.append({'name':rk,'heat_before':hb,'heat_after':ha,'delta':d,'reason':rivalry_change_reason(rk,d,fb)})
 prev=get_previous_company_show(company,week)
 comp=build_week_comparison(hist,prev)
 vw_prev=int(comp.get('viewership_prev',view_data.get('base',0)))
 vw_now=int(hist.get('viewership',view_data.get('viewership',0)))
 consequence_notes=list((log or {}).get('consequence_notes',[]) if isinstance(log,dict) else [])
 if not consequence_notes:
  consequence_notes=apply_post_show_consequences(company,rating,breakdown,ple,fb,log if isinstance(log,dict) else None)
 grade_scores={}
 for k in GRADE_WEIGHTS:
  label=GRADE_WEIGHT_LABELS[k]
  grade_scores[PERFORMANCE_GRADE_LABELS[k]]=float(breakdown.get(label,breakdown.get(k,5.5)))
 if not grade_scores:
  grade_scores={k:v for k,v in (breakdown or {}).items()}
 analysis={
  'performance_rating':round(rating,1),'performance_label':performance_rating_label(rating),
  'is_ple':bool(ple),'quick_summary':fb.get('summary') or f"{company} scored {rating}/10 — story and emotion drive the result.",
  'why_worked':list(fb.get('worked',[])[:6]),'why_struggled':list(fb.get('struggled',[])[:6]),
  'made_sense':list(fb.get('made_sense',[])[:5]),'did_not_make_sense':list(fb.get('no_sense',[])[:5]),
  'grade_scores':grade_scores,'breakdown':breakdown,
  'best_segment':(fb.get('worked') or ['—'])[0],'weakest_segment':(fb.get('struggled') or ['—'])[0],
  'biggest_winner':hist.get('featured_star') or (wrestler_rows[0]['name'] if wrestler_rows else '—'),
  'biggest_loser':(fb.get('struggled') or ['—'])[0] if fb.get('struggled') else '—',
  'wrestler_changes':wrestler_rows,'rivalry_changes':rivalry_rows,
  'viewership_last_week':vw_prev,'viewership_this_week':vw_now,'viewership_change':int(vw_now-vw_prev),
  'viewership_reason':' '.join((hist.get('viewership_modifiers') or view_data.get('modifiers',[]))[:4]) or comp.get('ai_reason',''),
  'attendance':att,'capacity':cap,'capacity_filled_pct':round(pct,1),'sellout_status':status,
  'attendance_reason':fb.get('attendance_impact') or fb.get('venue_fit','Attendance reflects show rating, story heat, and market fit.'),
  'money_impact':fb.get('money_impact') or f"Profit/loss {money(hist.get('profit',0))} from ticket, merch, sponsor, and logistics.",
  'popularity_impact':comp.get('popularity_delta',0),'morale_impact':comp.get('morale_delta',0),'momentum_impact':comp.get('momentum_delta',0),
  'next_week_must_follow':fb.get('next_week') or 'Escalate the top feud with a consequence segment.',
  'dirt_sheet_headline':_extract_dirt_headline(hist.get('dirt_sheet_review','')),
  'consequence_notes':consequence_notes,'fans_care':fb.get('fans_care',[]),'dropped_stories':fb.get('dropped',[]),
  'comparison':comp,'ai_determined':True,
 }
 if fb.get('ai_narrative'):
  analysis['ai_narrative']=fb['ai_narrative']
 sq=(log or {}).get('show_quality',{}) if isinstance(log,dict) else {}
 if sq:
  analysis['show_descriptor']=sq.get('show_descriptor','')
  analysis['attendance_descriptor']=sq.get('attendance_descriptor','')
  analysis['champion_descriptor']=sq.get('champion_descriptor','')
  analysis['main_event_descriptor']=sq.get('main_event_descriptor','')
  analysis['money_descriptor']=sq.get('money_descriptor','')
  analysis['sponsor_ads']=sq.get('sponsor_ads',[])
  analysis['quality_notes']=sq.get('quality_notes',[])
 return analysis

def _extract_dirt_headline(review):
 if not review: return 'Weekly Performance Report'
 for line in str(review).split('\n'):
  ll=line.strip().replace('*','')
  if 'headline' in ll.lower() and ':' in ll: return ll.split(':',1)[-1].strip()[:120]
  if ll and len(ll)<120 and not ll.startswith('**'): return ll[:120]
 return (review[:80]+'…') if len(review)>80 else review

def ensure_hist_ai_analysis(hist,regenerate=False):
 if hist.get('ai_analysis') and not regenerate: return hist['ai_analysis']
 rating=float(hist.get('episode_rating') or hist.get('final_rating') or 7)
 breakdown=hist.get('rating_breakdown',{})
 ple=schedule_show_is_ple(hist.get('show_type','')) or 'PLE' in (hist.get('show_type') or '')
 vd={'viewership':hist.get('viewership',0),'base':hist.get('viewership_base',0),'change':hist.get('viewership_change',0),'modifiers':hist.get('viewership_modifiers',[])}
 gr={'rating':rating,'breakdown':breakdown,'feedback':hist.get('ai_feedback',{})}
 perf=hist.get('performance') or {}
 stat_changes=perf.get('stat_changes',{})
 stat_before={}; stat_after={}
 for nm,ch in stat_changes.items():
  stat_before[nm]={'popularity':0,'morale':0,'momentum':0,'twitter_buzz':0}
  stat_after[nm]={k:stat_before[nm].get(k,0)+ch.get(k,0) for k in ('popularity','morale','momentum','twitter_buzz')}
 rh=perf.get('rivalry_heat_changes',{})
 rival_before={k:max(40,int(50-v)) for k,v in rh.items()}
 rival_after={k:rival_before.get(k,50)+int(v) for k,v in rh.items()}
 analysis=build_ai_performance_analysis(hist,gr,vd,None,hist.get('logistics'),stat_before,stat_after,rival_before,rival_after,perf.get('twitter_buzz_before',0),perf.get('twitter_buzz_after',0),ple=ple)
 hist['ai_analysis']=analysis
 return analysis

def get_fin_report_for_show(company,week,show_name=None):
 wk=int(week)
 for r in st.session_state.get('show_finance_reports',[]):
  if r.get('company')==company and int(r.get('week',-1))==wk:
   if not show_name or r.get('show_name')==show_name: return r
 return None

def get_previous_company_show(company,week):
 wk=int(week)
 prev=None
 for h in st.session_state.get('weekly_history',[]):
  if h.get('company')!=company: continue
  hw=int(h.get('week',-1))
  if hw<wk and (prev is None or hw>int(prev.get('week',-1))): prev=h
 return prev

def build_comparison_ai_reason(hist,prev,comp):
 parts=[]
 fb=hist.get('ai_feedback') or {}
 if comp.get('rating_delta',0)>0.3:
  parts.append('The episode rated higher with stronger story and emotional hooks.')
 elif comp.get('rating_delta',0)<-0.3:
  parts.append('Rating dipped due to weaker continuity or less fan investment.')
 if comp.get('viewership_delta',0)>100000:
  parts.append('Viewership climbed as more fans tuned in after last week.')
 if comp.get('profit_delta',0)>0:
  parts.append('Profit improved thanks to better attendance and revenue mix.')
 if fb.get('worked'): parts.append(str(fb['worked'][0]))
 if fb.get('continued'): parts.append(f"Continued: {fb['continued'][0]}")
 if fb.get('fans_care'): parts.append(str(fb['fans_care'][0]))
 if hist.get('city') and fb.get('hometown'): parts.append(f"Hometown energy in {hist.get('city')} boosted the crowd.")
 return ' '.join(parts)[:420] if parts else 'Week-over-week shift reflects booking quality, star usage, and how well last week\'s stories paid off.'

def build_week_comparison(hist,prev):
 comp={'rating_delta':0,'viewership_delta':0,'attendance_delta':0,'attendance_pct_delta':0,'profit_delta':0,'twitter_buzz_delta':0,'popularity_delta':0,'morale_delta':0,'momentum_delta':0,'rivalry_heat_delta':0}
 if not prev:
  comp['ai_reason']='First recorded show for this brand — no prior week to compare.'
  return comp
 lg=hist.get('logistics') or {}; plg=prev.get('logistics') or {}
 cap=int(hist.get('capacity') or lg.get('capacity',15000)); pcap=int(prev.get('capacity') or plg.get('capacity',15000))
 att=int(lg.get('attendance',0)); patt=int(plg.get('attendance',0))
 _,ap=sellout_label(att,cap); _,pap=sellout_label(patt,pcap)
 r_now=float(hist.get('episode_rating') or hist.get('final_rating') or 0)
 r_prev=float(prev.get('episode_rating') or prev.get('final_rating') or 0)
 vw_now=int(hist.get('viewership',0)); vw_prev=int(prev.get('viewership',0))
 pr_now=int(hist.get('profit',0)); pr_prev=int(prev.get('profit',0))
 perf=hist.get('performance') or {}; pperf=prev.get('performance') or {}
 sc=perf.get('stat_changes') or {}
 psc=pperf.get('stat_changes') or {}
 pop_d=sum(v.get('popularity',0) for v in sc.values())-sum(v.get('popularity',0) for v in psc.values()) if sc else 0
 mor_d=sum(v.get('morale',0) for v in sc.values())-sum(v.get('morale',0) for v in psc.values()) if sc else 0
 mom_d=sum(v.get('momentum',0) for v in sc.values())-sum(v.get('momentum',0) for v in psc.values()) if sc else 0
 comp.update({
  'prev_week':int(prev.get('week',0)),'rating_prev':r_prev,'rating_now':r_now,'rating_delta':round(r_now-r_prev,1),
  'viewership_prev':vw_prev,'viewership_now':vw_now,'viewership_delta':vw_now-vw_prev,
  'attendance_prev':patt,'attendance_now':att,'attendance_pct_prev':round(pap,1),'attendance_pct_now':round(ap,1),'attendance_pct_delta':round(ap-pap,1),
  'profit_prev':pr_prev,'profit_now':pr_now,'profit_delta':pr_now-pr_prev,
  'twitter_buzz_prev':int(perf.get('twitter_buzz_before',0)),'twitter_buzz_now':int(perf.get('twitter_buzz_after',0)),
  'twitter_buzz_delta':int(perf.get('twitter_buzz_after',0))-int(perf.get('twitter_buzz_before',0)),
  'popularity_delta':pop_d,'morale_delta':mor_d,'momentum_delta':mom_d,
 })
 comp['ai_reason']=build_comparison_ai_reason(hist,prev,comp)
 return comp

def attach_show_performance(hist,fin_report,stat_before,stat_after,rival_before,rival_after,buzz_before,buzz_after,grade_result=None,view_data=None,reasons=None,ple=False):
 company=hist.get('company'); week=int(hist.get('week',0))
 prev=get_previous_company_show(company,week)
 lg=hist.get('logistics') or {}
 cap=int(hist.get('capacity') or lg.get('capacity',15000))
 att=int(lg.get('attendance',0))
 status,pct=sellout_label(att,cap)
 stat_changes={}
 for nm in set(stat_before)|set(stat_after):
  b=stat_before.get(nm,{}); a=stat_after.get(nm,{})
  if b or a:
   stat_changes[nm]={'popularity':int(a.get('popularity',0))-int(b.get('popularity',0)),'morale':int(a.get('morale',0))-int(b.get('morale',0)),'momentum':int(a.get('momentum',0))-int(b.get('momentum',0)),'twitter_buzz':int(a.get('twitter_buzz',0))-int(b.get('twitter_buzz',0))}
 rivalry_changes={}
 for rk in set(rival_before)|set(rival_after):
  rivalry_changes[rk]=int(rival_after.get(rk,0))-int(rival_before.get(rk,0))
 rev=fin_report.get('revenue',{}) if fin_report else {}
 exp=fin_report.get('expenses',{}) if fin_report else {}
 fb=(grade_result or {}).get('feedback',hist.get('ai_feedback',{})) or {}
 gr=grade_result or {'rating':hist.get('episode_rating',7),'breakdown':hist.get('rating_breakdown',{}),'feedback':fb}
 vd=view_data or {'viewership':hist.get('viewership',0),'base':hist.get('viewership_base',0),'change':hist.get('viewership_change',0),'modifiers':hist.get('viewership_modifiers',[])}
 ai=build_ai_performance_analysis(hist,gr,vd,fin_report,lg,stat_before,stat_after,rival_before,rival_after,buzz_before,buzz_after,reasons=reasons,ple=ple)
 perf={
  'total_revenue':int(fin_report.get('total_revenue',lg.get('weekly_income',0)) if fin_report else lg.get('weekly_income',0)),
  'total_expenses':int(fin_report.get('total_expenses',lg.get('weekly_expenses',0)) if fin_report else lg.get('weekly_expenses',0)),
  'budget_before':int(fin_report.get('budget_before',0) if fin_report else 0),
  'budget_after':int(fin_report.get('budget_after',0) if fin_report else 0),
  'revenue_breakdown':rev,'expense_breakdown':exp,
  'capacity_filled_pct':round(pct,1),'sellout_status':status,
  'stat_changes':stat_changes,'rivalry_heat_changes':rivalry_changes,
  'twitter_buzz_before':int(buzz_before),'twitter_buzz_after':int(buzz_after),
  'twitter_buzz_delta':int(buzz_after)-int(buzz_before),
  'best_segment':ai.get('best_segment'),'weakest_segment':ai.get('weakest_segment'),
  'biggest_winner':ai.get('biggest_winner'),'biggest_loser':ai.get('biggest_loser'),
  'dirt_sheet_headline':ai.get('dirt_sheet_headline'),
  'comparison':ai.get('comparison') or build_week_comparison(hist,prev),
  'ai_analysis':ai,'performance_rating':ai.get('performance_rating'),'ai_determined':True,
 }
 hist['performance']=perf
 hist['ai_analysis']=ai
 hist['episode_rating']=ai.get('performance_rating')
 if grade_result: hist['rating_breakdown']=gr.get('breakdown',hist.get('rating_breakdown',{}))
 st.session_state.setdefault('weekly_performance_index',{})
 st.session_state.weekly_performance_index[f"{company}:{week}"]=perf
 return perf

def resolve_show_performance(hist):
 if hist.get('performance'):
  perf=dict(hist['performance'])
  if not perf.get('ai_analysis'): perf['ai_analysis']=ensure_hist_ai_analysis(hist)
  return perf
 company=hist.get('company'); week=int(hist.get('week',0))
 fin=get_fin_report_for_show(company,week,hist.get('show_name'))
 lg=hist.get('logistics') or {}
 cap=int(hist.get('capacity') or lg.get('capacity',15000))
 att=int(lg.get('attendance',0))
 status,pct=sellout_label(att,cap)
 prev=get_previous_company_show(company,week)
 return {
  'total_revenue':int(lg.get('weekly_income',hist.get('ticket_revenue',0))),
  'total_expenses':int(lg.get('weekly_expenses',0)),
  'budget_before':int(fin.get('budget_before',0)) if fin else 0,
  'budget_after':int(fin.get('budget_after',0)) if fin else 0,
  'revenue_breakdown':fin.get('revenue',{}) if fin else {'ticket':hist.get('ticket_revenue',0)},
  'expense_breakdown':fin.get('expenses',{}) if fin else {},
  'capacity_filled_pct':round(pct,1),'sellout_status':status,
  'stat_changes':{},'rivalry_heat_changes':{},
  'twitter_buzz_before':0,'twitter_buzz_after':0,'twitter_buzz_delta':0,
  'best_segment':'—','weakest_segment':'—','biggest_winner':hist.get('featured_star','—'),'biggest_loser':'—',
  'dirt_sheet_headline':(hist.get('dirt_sheet_review') or '')[:80],
  'comparison':build_week_comparison(hist,prev),
 }

def filter_weekly_shows(company=None,filters=None):
 filters=filters or {}
 out=[h for h in st.session_state.get('weekly_history',[]) if h.get('logistics') or h.get('viewership') or h.get('profit') is not None or h.get('episode_rating') is not None or h.get('final_rating') is not None]
 if company and company!='All Brands':
  out=[h for h in out if h.get('company')==company]
 wk=filters.get('week')
 if wk and wk!='All':
  out=[h for h in out if int(h.get('week',-1))==int(wk)]
 stype=filters.get('show_type')
 if stype and stype!='All':
  out=[h for h in out if stype.lower() in (h.get('show_type') or '').lower()]
 rmin,rmax=filters.get('rating_min',1.0),filters.get('rating_max',10.0)
 out=[h for h in out if rmin<=float(h.get('episode_rating') or h.get('final_rating') or 0)<=rmax]
 plf=filters.get('profit_filter','All')
 if plf=='Profitable': out=[h for h in out if int(h.get('profit',0))>0]
 elif plf=='Lost Money': out=[h for h in out if int(h.get('profit',0))<0]
 vmin,vmax=filters.get('viewership_min',0),filters.get('viewership_max',10_000_000)
 out=[h for h in out if vmin<=int(h.get('viewership',0))<=vmax]
 sell=filters.get('sellout','All')
 if sell!='All':
  out=[h for h in out if resolve_show_performance(h).get('sellout_status')==sell]
 if filters.get('ple_only'):
  out=[h for h in out if schedule_show_is_ple(h.get('show_type','')) or 'PLE' in (h.get('show_type') or '')]
 if filters.get('weekly_only'):
  out=[h for h in out if not schedule_show_is_ple(h.get('show_type','')) and 'PLE' not in (h.get('show_type') or '')]
 return sorted(out,key=lambda x:(int(x.get('week',0)),x.get('company','')),reverse=True)

def admin_delete_weekly_show(company,week):
 wk=int(week)
 st.session_state.weekly_history=[h for h in st.session_state.get('weekly_history',[]) if not (h.get('company')==company and int(h.get('week',-1))==wk)]
 st.session_state.show_finance_reports=[r for r in st.session_state.get('show_finance_reports',[]) if not (r.get('company')==company and int(r.get('week',-1))==wk)]
 st.session_state.weekly_performance_index={k:v for k,v in st.session_state.get('weekly_performance_index',{}).items() if not k.startswith(f"{company}:{wk}")}
 save_universe()

def _delta_html(label,prev_val,new_val,fmt='num',money_fmt=False):
 if prev_val is None: return ''
 if money_fmt:
  d=int(new_val)-int(prev_val); col='#2ecc71' if d>=0 else '#e74c3c'; sign='+' if d>=0 else '−'
  return f"<div class='money-meter-stat'><b>{label}:</b> {money(prev_val)} → {money(new_val)} <span style='color:{col}'>{sign}{money(abs(d))}</span></div>"
 if fmt=='pct':
  d=float(new_val)-float(prev_val); col='#2ecc71' if d>=0 else '#e74c3c'; sign='+' if d>=0 else '−'
  return f"<div class='money-meter-stat'><b>{label}:</b> {prev_val:.0f}% → {new_val:.0f}% <span style='color:{col}'>{sign}{abs(d):.0f}%</span></div>"
 if fmt=='rating':
  d=float(new_val)-float(prev_val); col='#2ecc71' if d>=0 else '#e74c3c'; sign='+' if d>=0 else '−'
  return f"<div class='money-meter-stat'><b>{label}:</b> {prev_val:.1f} → {new_val:.1f} <span style='color:{col}'>{sign}{abs(d):.1f}</span></div>"
 if fmt=='view':
  d=int(new_val)-int(prev_val); col='#2ecc71' if d>=0 else '#e74c3c'; sign='+' if d>=0 else '−'
  return f"<div class='money-meter-stat'><b>{label}:</b> {prev_val/1_000_000:.1f}M → {new_val/1_000_000:.1f}M <span style='color:{col}'>{sign}{abs(d)/1_000_000:.1f}M</span></div>"
 d=int(new_val)-int(prev_val); col='#2ecc71' if d>=0 else '#e74c3c'; sign='+' if d>=0 else '−'
 return f"<div class='money-meter-stat'><b>{label}:</b> {prev_val:,} → {new_val:,} <span style='color:{col}'>{sign}{abs(d):,}</span></div>"

def _company_shows_chronological(company):
 return sorted(
  [h for h in st.session_state.get('weekly_history',[]) if h.get('company')==company and (h.get('episode_rating') is not None or h.get('final_rating') is not None or h.get('viewership'))],
  key=lambda x:int(x.get('week',0)),
 )

def _dirt_sheet_headline(hist):
 review=(hist.get('dirt_sheet_review') or '').strip()
 if not review: return '—'
 for line in review.split('\n'):
  ln=line.strip()
  if 'headline' in ln.lower() and ':' in ln:
   return ln.split(':',1)[-1].strip().strip('*')[:120]
 first=review.split('\n')[0].strip()
 return first[:100] if first else '—'

def _metrics_chart_df(company):
 import pandas as pd
 rows=[]
 for h in _company_shows_chronological(company):
  wk=int(h.get('week',0))
  vw=int(h.get('viewership',0))
  att=int((h.get('logistics') or {}).get('attendance',0))
  rows.append({
   'Week':wk,
   'Episode Rating':round(float(h.get('episode_rating') or h.get('final_rating') or 0),1),
   'Viewership (millions)':round(vw/1_000_000,2),
   'Attendance (thousands)':round(att/1000,1),
  })
 return pd.DataFrame(rows) if rows else None

def _all_brands_chart_df(metric_key):
 """metric_key: 'Episode Rating' or 'Viewership (millions)'"""
 import pandas as pd
 weeks=sorted({int(h.get('week',0)) for h in st.session_state.get('weekly_history',[])})
 if not weeks: return None
 data={'Week':weeks}
 for co in PLAYABLE:
  col=[]
  by_wk={int(h.get('week',0)):h for h in _company_shows_chronological(co)}
  for wk in weeks:
   h=by_wk.get(wk)
   if not h:
    col.append(None)
   elif metric_key=='Episode Rating':
    col.append(round(float(h.get('episode_rating') or h.get('final_rating') or 0),1))
   else:
    col.append(round(int(h.get('viewership',0))/1_000_000,2))
  data[co]=col
 return pd.DataFrame(data).set_index('Week')

def render_fan_view_rating_charts(company=None):
 """Line charts: episode rating, fan viewership, attendance trend."""
 st.markdown('<div class="section-header">Fan View & Rating Trends</div>',unsafe_allow_html=True)
 st.caption('Episode rating (1–10) and fan viewership from completed **Book Show** runs — updates each week.')
 if company and company in PLAYABLE:
  df=_metrics_chart_df(company)
  if df is None or df.empty:
   st.info(f'No {company} show history yet. Book and run a show to populate this graph.')
   return
  c1,c2=st.columns(2)
  with c1:
   st.markdown('**Episode rating by week**')
   st.line_chart(df.set_index('Week')[['Episode Rating']],height=220)
  with c2:
   st.markdown('**Fan viewership by week**')
   st.line_chart(df.set_index('Week')[['Viewership (millions)']],height=220)
  st.markdown('**Combined metrics**')
  st.line_chart(df.set_index('Week'),height=260)
  if len(df)>=2:
   last=df.iloc[-1]; prev=df.iloc[-2]
   d1,d2,d3=st.columns(3)
   dr=float(last['Episode Rating'])-float(prev['Episode Rating'])
   dv=float(last['Viewership (millions)'])-float(prev['Viewership (millions)'])
   d1.metric('Latest rating',f"{last['Episode Rating']}/10",f"{dr:+.1f} vs prior week")
   d2.metric('Latest viewership',f"{last['Viewership (millions)']:.2f}M",f"{dv:+.2f}M vs prior week")
   d3.metric('Latest attendance',f"{int(last['Attendance (thousands)']*1000):,}",f"Week {int(last['Week'])}")
  return
 st.markdown('**All brands — episode rating**')
 df_r=_all_brands_chart_df('Episode Rating')
 if df_r is not None and not df_r.empty:
  st.line_chart(df_r,height=240)
 else:
  st.caption('No rating history yet.')
 st.markdown('**All brands — fan viewership (millions)**')
 df_v=_all_brands_chart_df('Viewership (millions)')
 if df_v is not None and not df_v.empty:
  st.line_chart(df_v,height=240)
 else:
  st.caption('No viewership history yet.')

def render_dirt_sheet_grading_hub(company,shows=None):
 """Dirt Sheet letter grades + category breakdown per completed show."""
 st.markdown('<div class="section-header">Dirt Sheet Grading</div>',unsafe_allow_html=True)
 st.caption('Insider-style grades from the same story-first rubric used when you **Grade Show** — headline, letter grade, and category scores.')
 pool=shows if shows is not None else _company_shows_chronological(company)
 pool=sorted(pool,key=lambda x:int(x.get('week',0)),reverse=True)
 if not pool:
  st.info(f'No {company} Dirt Sheet grades yet. Complete a show on **Book Show** to generate reviews.')
  return
 summary=[]
 for h in pool[:24]:
  wk=int(h.get('week',0))
  rating=float(h.get('episode_rating') or h.get('final_rating') or 0)
  br=h.get('rating_breakdown') or {}
  summary.append({
   'Week':wk,
   'Show':(h.get('show_name') or 'Show')[:36],
   'Rating':f'{rating:.1f}',
   'Letter':h.get('grade') or _grade_letter(rating),
   'Viewership':f"{int(h.get('viewership',0)):,}",
   'Dirt Sheet':_dirt_sheet_headline(h)[:70],
   'Source':h.get('dirt_sheet_label','Built-in') or 'Built-in',
  })
 st.dataframe(summary,use_container_width=True,hide_index=True)
 pick=pool[0]
 with st.expander(f"Latest — Week {int(pick.get('week',0))} · {pick.get('show_name','Show')}",expanded=True):
  _render_dirt_sheet_grade_card(pick)
 st.markdown('**Prior weeks**')
 for h in pool[1:12]:
  wk=int(h.get('week',0))
  rating=float(h.get('episode_rating') or h.get('final_rating') or 0)
  with st.expander(f"Week {wk} — {h.get('show_name','Show')} · {rating:.1f}/10 · {h.get('grade',_grade_letter(rating))}",expanded=False):
   _render_dirt_sheet_grade_card(h)

def _render_dirt_sheet_grade_card(hist):
 company=hist.get('company','')
 week=int(hist.get('week',0))
 rating=float(hist.get('episode_rating') or hist.get('final_rating') or 0)
 letter=hist.get('grade') or _grade_letter(rating)
 br=hist.get('rating_breakdown') or {}
 vw=int(hist.get('viewership',0))
 ch=int(hist.get('viewership_change',0))
 m1,m2,m3,m4=st.columns(4)
 m1.metric('Episode rating',f'{rating:.1f}/10')
 m2.metric('Letter grade',letter)
 m3.metric('Fan viewership',f'{vw:,}' if vw else '—')
 m4.metric('Vs last week',f'{ch:+,}' if ch else '—')
 if br:
  with bfg_card('Category grades (Dirt Sheet rubric)'):
   st.caption('Weights: Story 25% · Emotion 20% · Character 15% · Rivalry 15% · Champion 10% · Promo/Match 10% · Business/Venue 5%')
   cols=st.columns(4)
   for i,(label,score) in enumerate(br.items()):
    cols[i%4].metric(label,f'{float(score):.1f}/10',_grade_letter(float(score)))
 if hist.get('viewership_modifiers'):
  with st.expander('Why viewership moved',expanded=False):
   for n in hist.get('viewership_modifiers',[])[:8]: st.caption('• '+str(n))
 headline=_dirt_sheet_headline(hist)
 if headline and headline!='—':
  st.markdown(f"**Dirt Sheet headline:** {headline}")
 if hist.get('dirt_sheet_review'):
  render_long_markdown(hist['dirt_sheet_review'],f"Dirt Sheet — Week {week} ({hist.get('dirt_sheet_label','Review')})",expanded=len(hist.get('dirt_sheet_review',''))<900)
 else:
  st.caption('No full Dirt Sheet write-up stored for this week.')

def render_weekly_performance_card(hist):
 company=hist.get('company',''); week=int(hist.get('week',0))
 ai=ensure_hist_ai_analysis(hist)
 perf=resolve_show_performance(hist)
 fin=get_fin_report_for_show(company,week,hist.get('show_name'))
 lg=hist.get('logistics') or {}
 rules=COMPANY_LOGISTICS_RULES.get(company,{})
 profit=int(hist.get('profit',0))
 pl_col='#2ecc71' if profit>=0 else '#e74c3c'
 th=_meter_theme(company)
 rating=float(ai.get('performance_rating',hist.get('episode_rating',0)))
 ple_tag=' · **PLE**' if ai.get('is_ple') else ''
 st.markdown(
  f"<div class='event-box' style='border-color:{th['border']};box-shadow:0 0 16px {th['glow']}44'>"
  f"<div class='section-header' style='font-size:22px;border-color:{th['glow']}'>{company} Week {week}{ple_tag}</div>"
  f"<div style='font-size:18px;font-weight:800'>{hist.get('show_name','Show')}</div>"
  f"<div class='small-text'>{hist.get('show_type','Weekly Show')} · {hist.get('venue','')} · {hist.get('city','')}</div>"
  f"<div style='margin-top:8px;font-size:28px;font-weight:950'>AI Performance: {rating:.1f}/10</div>"
  f"<div class='small-text'>{ai.get('performance_label','')} · AI-determined (not random)</div></div>",
  unsafe_allow_html=True)
 st.info(ai.get('quick_summary',''))
 m1,m2,m3,m4=st.columns(4)
 m1.metric('Viewership',f"{ai.get('viewership_this_week',0):,}")
 m2.metric('Attendance',f"{ai.get('attendance',0):,}")
 m3.metric('Capacity',f"{ai.get('capacity_filled_pct',0):.0f}%")
 m4.metric('Sellout',ai.get('sellout_status','—'))
 if ai.get('show_descriptor'):
  st.success(f"**Show read:** {ai.get('show_descriptor')}")
 with bfg_card('AI Viewership & Attendance'):
  st.write(f"**Last week:** {ai.get('viewership_last_week',0):,} → **This week:** {ai.get('viewership_this_week',0):,} ({ai.get('viewership_change',0):+,})")
  st.caption(f"**AI reason:** {ai.get('viewership_reason','')}")
  st.write(f"**Venue capacity:** {ai.get('capacity',0):,} · **Attendance:** {ai.get('attendance',0):,} ({ai.get('capacity_filled_pct',0):.0f}% filled)")
  st.caption(f"**Attendance impact:** {ai.get('attendance_reason','')}")
  if ai.get('attendance_descriptor'): st.caption(f"**Gate descriptor:** {ai['attendance_descriptor']}")
 with bfg_card('Show Quality Descriptors'):
  if ai.get('main_event_descriptor'): st.write(f"**Main event:** {ai['main_event_descriptor']}")
  if ai.get('champion_descriptor'): st.write(f"**Champion usage:** {ai['champion_descriptor']}")
  if ai.get('money_descriptor'): st.write(f"**Money read:** {ai['money_descriptor']}")
  for ad in (ai.get('sponsor_ads') or [])[:3]:
   st.caption(f"Sponsor — {ad.get('style', ad.get('type','Ad'))}: _{ad.get('descriptor','')}_ (+{money(ad.get('revenue',0))})")
  for qn in (ai.get('quality_notes') or [])[:5]:
   st.caption('• '+str(qn))
 with bfg_card('AI Grade Breakdown'):
  cols=st.columns(4)
  for i,(label,score) in enumerate(list((ai.get('grade_scores') or {}).items())[:8]):
   cols[i%4].metric(label,f"{score:.1f}/10")
 c1,c2=st.columns(2)
 with c1:
  with bfg_card('Why The Show Worked'):
   for x in ai.get('why_worked',[])[:6]: st.write('• '+str(x))
  with bfg_card('What Made Sense'):
   for x in ai.get('made_sense',[])[:5]: st.write('• '+str(x))
 with c2:
  with bfg_card('Why The Show Struggled'):
   for x in ai.get('why_struggled',[])[:6]: st.write('• '+str(x))
  with bfg_card('What Did Not Make Sense'):
   for x in ai.get('did_not_make_sense',[])[:5]: st.write('• '+str(x))
 with bfg_card('Segments & Stars'):
  st.write(f"**Best segment:** {ai.get('best_segment','—')}")
  st.write(f"**Weakest segment:** {ai.get('weakest_segment','—')}")
  st.write(f"**Biggest winner:** {ai.get('biggest_winner','—')} · **Biggest loser:** {ai.get('biggest_loser','—')}")
 rev=perf.get('revenue_breakdown') or {}
 exp=perf.get('expense_breakdown') or {}
 with bfg_card('Money — AI-calculated from show quality'):
  st.write(f"**Old bank:** {money(perf.get('budget_before',0))} · **New bank:** {money(perf.get('budget_after',0))}")
  st.caption(ai.get('money_impact',''))
  mc1,mc2=st.columns(2)
  with mc1:
   st.markdown('**Revenue**')
   for k,v in [('Ticket',rev.get('ticket')),('Merchandise',rev.get('merchandise')),('Sponsor',rev.get('sponsor')),('Media',rev.get('media')),('Film',rev.get('film')),('Market',rev.get('market_bonus'))]:
    if v: st.markdown(f"<span style='color:#2ecc71'>+{money(v)} {k}</span>",unsafe_allow_html=True)
   st.markdown(f"**Total:** <span style='color:#2ecc71'>+{money(perf.get('total_revenue',0))}</span>",unsafe_allow_html=True)
  with mc2:
   st.markdown('**Expenses**')
   for k,v in [('Venue',exp.get('venue')),('Security',exp.get('security')),('Production',exp.get('production')),('Hotel base',exp.get('hotel_base')),('Hotel final',exp.get('hotel_final')),('Transport base',exp.get('transport_base')),('Transport final',exp.get('transport_final'))]:
    if v: st.markdown(f"<span style='color:#e74c3c'>−{money(v)} {k}</span>",unsafe_allow_html=True)
   if company=='SmackDown' and lg.get('hotel_savings'): st.caption(f"**Marriott Hotel Savings:** −{money(lg['hotel_savings'])} (final hotel $0)")
   if company=='WCW' and lg.get('transport_savings'): st.caption(f"**Tesla/Mercedes Transportation Savings:** −{money(lg['transport_savings'])} (final transport $0)")
   if company=='NXT': st.caption('NXT pays full hotel and transportation — can offset via Netflix/Marvel/media merch.')
   st.markdown(f"**Total:** <span style='color:#e74c3c'>−{money(perf.get('total_expenses',0))}</span>",unsafe_allow_html=True)
  st.markdown(f"**Final P/L:** <span style='color:{pl_col}'>{'+' if profit>=0 else '−'}{money(abs(profit))}</span>",unsafe_allow_html=True)
 if ai.get('consequence_notes'):
  st.caption('**PLE / prestige impact:** '+' · '.join(ai['consequence_notes']))
 comp=ai.get('comparison') or perf.get('comparison') or {}
 if comp.get('prev_week'):
  with bfg_card('Compared To Last Week'):
   for fn in [_delta_html('Rating',comp.get('rating_prev'),comp.get('rating_now'),fmt='rating'),_delta_html('Viewership',comp.get('viewership_prev'),comp.get('viewership_now'),fmt='view'),_delta_html('Attendance %',comp.get('attendance_pct_prev'),comp.get('attendance_pct_now'),fmt='pct'),_delta_html('Profit/Loss',comp.get('profit_prev'),comp.get('profit_now'),money_fmt=True)]:
    if fn: st.markdown(fn,unsafe_allow_html=True)
   st.info(comp.get('ai_reason',''))
 wr=ai.get('wrestler_changes') or []
 if wr:
  with bfg_card('Popularity / Morale / Momentum Changes'):
   st.table([{'Wrestler':r['name'],'Pop Δ':r.get('popularity',0),'Morale Δ':r.get('morale',0),'Momentum Δ':r.get('momentum',0),'Reason':r.get('reason','')[:90]} for r in wr[:15]])
 rr=ai.get('rivalry_changes') or []
 if rr:
  with bfg_card('Rivalry Heat Changes'):
   for r in rr: st.write(f"**{r['name']}** — {r.get('heat_before',0)} → {r.get('heat_after',0)} ({r.get('delta',0):+}) · _{r.get('reason','')}_")
 if ai.get('dropped_stories'):
  st.warning('**Stories ignored:** '+' · '.join(ai.get('dropped_stories',[])[:4]))
 st.success(f"**Next week must follow up:** {ai.get('next_week_must_follow','')}")
 with st.expander(f"Dirt Sheet AI — {ai.get('dirt_sheet_headline','Review')}",expanded=False):
  render_long_markdown(hist.get('dirt_sheet_review') or '_No dirt sheet._',f"Dirt Sheet ({hist.get('dirt_sheet_label','AI')})",expanded=True)
 if ai.get('ai_narrative'):
  with st.expander('Extended AI creative analysis',expanded=False):
   render_long_markdown(ai['ai_narrative'],'Full AI Report',expanded=True)
 if is_admin():
  if st.button(f'Admin: remove Week {week} {company} record',key=f'wp_del_{company}_{week}'):
   admin_delete_weekly_show(company,week); st.toast(f'Removed {company} Week {week}'); st.rerun()

def render_all_brands_performance(week_filter):
 weeks=sorted({int(h.get('week',0)) for h in st.session_state.get('weekly_history',[])},reverse=True)
 if not weeks:
  st.info('No completed shows yet. Run shows on **Book Show** to populate Weekly Performance.')
  return
 wk=int(week_filter) if week_filter and week_filter!='Latest' else weeks[0]
 shows={co:next((h for h in st.session_state.weekly_history if h.get('company')==co and int(h.get('week',-1))==wk),None) for co in PLAYABLE}
 rows=[]
 for co,h in shows.items():
  if not h: continue
  perf=resolve_show_performance(h)
  rows.append({'Company':co,'Show Rating':f"{float(h.get('episode_rating') or h.get('final_rating') or 0):.1f}",'Viewership':f"{int(h.get('viewership',0)):,}",'Attendance':f"{int((h.get('logistics') or {}).get('attendance',0)):,}",'Capacity %':f"{perf.get('capacity_filled_pct',0):.0f}%",'Profit/Loss':money(h.get('profit',0)),'Current Bank':money(perf.get('budget_after',get_company_budget(co))),'Biggest Star':h.get('featured_star','—'),'Best Segment':perf.get('best_segment','—'),'Dirt Sheet':perf.get('dirt_sheet_headline','—')[:60]})
 if rows:
  st.markdown(f'### Week {wk} — All Brands Comparison')
  st.table(rows)
 rated=sorted([(co,float(h.get('episode_rating') or h.get('final_rating') or 0)) for co,h in shows.items() if h],key=lambda x:-x[1])
 viewed=sorted([(co,int(h.get('viewership',0))) for co,h in shows.items() if h],key=lambda x:-x[1])
 prof=sorted([(co,int(h.get('profit',0))) for co,h in shows.items() if h],key=lambda x:-x[1])
 c1,c2,c3=st.columns(3)
 with c1:
  st.markdown('**Best Show This Week**')
  for i,(co,r) in enumerate(rated,1): st.write(f"{i}. {co} — {r:.1f} / 10")
 with c2:
  st.markdown('**Most Viewed**')
  for i,(co,v) in enumerate(viewed,1): st.write(f"{i}. {co} — {v:,}")
 with c3:
  st.markdown('**Most Profitable**')
  for i,(co,p) in enumerate(prof,1): st.write(f"{i}. {co} — {money(p)}")
 if rated:
  st.markdown(f"**Best story angle (top rated):** {rated[0][0]} — {rated[0][1]:.1f}/10")
  worst_fu=None
  for co,h in shows.items():
   if not h: continue
   ai=ensure_hist_ai_analysis(h)
   for d in ai.get('dropped_stories',[])[:1]:
    worst_fu=f"{co}: {d}"; break
  if worst_fu: st.markdown(f"**Weakest follow-up:** {worst_fu}")
 for co,h in shows.items():
  if h:
   with st.expander(f'{co} — Week {wk} detail',expanded=False):
    render_weekly_performance_card(h)

def render_weekly_performance_page():
 ensure_finance_state()
 render_page_shell('Weekly Performance',subtitle='Fan view graphs, Dirt Sheet grading, ratings, viewership, attendance, and money from Book Show — read-only in multiplayer.',show_meter=False,show_badge=True)
 brand=st.radio('Brand',PLAYABLE+['All Brands'],horizontal=True,key='wp_brand',index=PLAYABLE.index(st.session_state.get('active_brand','NXT')) if st.session_state.get('active_brand') in PLAYABLE else 0)
 if brand!='All Brands':
  set_active_brand(brand)
  inject_brand_theme(brand)
 if brand=='All Brands':
  render_money_meter_multi()
 else:
  render_money_meter(brand,compact=False,show_ticker=True,show_sponsor=True)
  render_brand_hub_embed(brand,compact=True,key_prefix='wp_hub')
 weeks=sorted({int(h.get('week',0)) for h in st.session_state.get('weekly_history',[])},reverse=True)
 week_opts=['All']+([str(w) for w in weeks] if weeks else [])
 with st.expander('Filters',expanded=False):
  fc1,fc2,fc3,fc4=st.columns(4)
  with fc1:
   fw=st.selectbox('Week',week_opts,index=0,key='wp_f_week')
   fst=st.selectbox('Show Type',['All','Weekly Show','PLE','TV Special','Stadium Show','International Tour','Tournament','Go-Home Show','Fallout Show','Homecoming Show','Crossover Event'],key='wp_f_stype')
  with fc2:
   fr1,fr2=st.slider('Rating range',1.0,10.0,(1.0,10.0),0.1,key='wp_f_rating')
   fpl=st.selectbox('Profit/Loss',['All','Profitable','Lost Money'],key='wp_f_pl')
  with fc3:
   fv1,fv2=st.slider('Viewership',0,5_000_000,(0,5_000_000),50_000,key='wp_f_vw')
   fsell=st.selectbox('Sellout Status',['All','Sellout','Near Sellout','Strong Crowd','Good Crowd','Soft Crowd','Weak Attendance'],key='wp_f_sell')
  with fc4:
   fple=st.checkbox('PLE only',key='wp_f_ple')
   fweekly=st.checkbox('Weekly shows only',key='wp_f_weekly')
 filters={'week':fw if fw!='All' else None,'show_type':fst if fst!='All' else None,'rating_min':fr1,'rating_max':fr2,'profit_filter':fpl,'viewership_min':fv1,'viewership_max':fv2,'sellout':fsell if fsell!='All' else 'All','ple_only':fple,'weekly_only':fweekly}
 if brand=='All Brands':
  render_fan_view_rating_charts(company=None)
  st.divider()
  render_all_brands_performance(fw if fw!='All' else 'Latest')
  for co in PLAYABLE:
   co_shows=_company_shows_chronological(co)
   if co_shows:
    with st.expander(f'{co} — Dirt Sheet grades',expanded=(co==st.session_state.get('active_brand','NXT'))):
     render_dirt_sheet_grading_hub(co,shows=co_shows)
  return
 tab_trends,tab_dirt,tab_detail=st.tabs(['Fan View Trends','Dirt Sheet Grades','Show Reports'])
 shows=filter_weekly_shows(brand,filters)
 with tab_trends:
  render_fan_view_rating_charts(company=brand)
 with tab_dirt:
  render_dirt_sheet_grading_hub(brand,shows=shows if shows else _company_shows_chronological(brand))
 with tab_detail:
  if not shows:
   st.info(f'No completed {brand} shows match these filters yet.')
  else:
   st.caption(f"Showing **{len(shows)}** completed show(s) for **{brand}**.")
   for h in shows:
    render_weekly_performance_card(h)

def crisis_story_fn(w,company):
 return crisis.wrestler_storyline_importance(w,company,lambda:st.session_state.rivalries,is_champion_name,st.session_state.weekly_history)

def crisis_advance_universe_week():
 crisis.advance_financial_crisis_week(lambda c:payroll_wrestlers(c),lambda c:payroll_wrestlers(c))
 for c in PLAYABLE:
  crisis.refresh_crisis_status_from_budget(c,get_company_budget(c))

def crisis_bidding_reactions(w,from_comp,to_comp,outcome):
 tw=''; lock=''
 if outcome=='accept' and to_comp:
  tw=f"BREAKING: {w['name']} is leaning toward {to_comp} amid {from_comp}'s financial crisis. Fans are split."
  lock=f"Locker room at {from_comp} is shaken — {w['name']} may be leaving."
 elif outcome=='stay_loyal':
  tw=f"{w['name']} posts loyalty to {from_comp} despite bankruptcy rumors. Respect or delusion?"
  lock=f"{from_comp} locker room rallies behind {w['name']} staying loyal."
 elif outcome=='renegotiate':
  tw=f"{w['name']} demands a new deal before {from_comp} collapses. Negotiations heating up."
  lock='Contract talks dominate backstage.'
 elif outcome=='request_release':
  tw=f"{w['name']} wants out of {from_comp}. Free agency rumors explode."
  lock=f"{from_comp} morale drops — star wants release."
 elif outcome=='delay':
  tw=f"{w['name']} says decision waits until after the PLE. Smart business or stall tactic?"
  lock='Storyline protected — no roster move yet.'
 else:
  tw=f"{w['name']} rejected all bids during {from_comp}'s crisis."
  lock='Rivals back off for now.'
 if tw and can_tweet_as_company(from_comp):
  make_twitter_post(from_comp,'wrestler',w['name'],'@'+slug(w['name']).replace('_',''),'Wrestler','Crisis Bidding',tw,'',{'ai_generated':True,'topic':'Financial Crisis','effects':{'buzz':(4,12),'controversy':(2,8)}})
 return tw,lock

def execute_bidding_outcome(bw,dec,admin_force=None):
 w=find(bw.get('wrestler'))
 if not w: return False,'Wrestler not found.'
 from_comp=bw.get('from_company')
 outcome=admin_force or dec.get('outcome')
 if dec.get('delay') and not admin_force:
  bw['status']='delayed'; bw['ai_decision']=dec
  st.session_state.news_feed.insert(0,f"Bidding delayed: {w['name']} central to storyline — continuity protected.")
  st.session_state.setdefault('storyline_flags',[]).insert(0,{'week':st.session_state.week,'flag':'Bidding delayed — storyline','target':w['name'],'company':from_comp,'notes':dec.get('reason','')[:200]})
  bw['history'].append({'week':st.session_state.week,'action':'delayed','detail':dec.get('reason','')})
  return True,'Decision delayed until after PLE payoff.'
 tw,lock=crisis_bidding_reactions(w,from_comp,dec.get('target_company'),outcome)
 bw['twitter_reaction']=tw; bw['locker_room_reaction']=lock
 bw['sponsor_reaction']=f"Sponsors watch {w['name']} — trust {w.get('sponsor_trust',60)} · {from_comp} debt week {st.session_state.company_crisis.get(from_comp,{}).get('weeks_below_zero',0)}"
 if outcome=='accept' and dec.get('target_company'):
  to_comp=dec['target_company']
  old_sal=int(w.get('salary',0))
  bo=dec.get('best_offer') or {}
  w['company']=to_comp; w['previous_company']=from_comp
  w['salary']=int(bo.get('salary',w['salary']))
  w['contract_length_years']=int(bo.get('years',2))
  w['contract_weeks_remaining']=int(bo.get('years',2))*52
  w['renewal_status']='Accepted'; w['contract_status']='Active'
  recompute_contract_counters(w)
  bonus=int(bo.get('bonus',0))
  if bonus>0: mp_add_transaction(to_comp,'Signing Bonus',f"Crisis bid — {w['name']}",-bonus)
  crisis.adjust_brand_loyalty(w,8,f'Signed with {to_comp} during crisis')
  for ow in payroll_wrestlers(from_comp):
   if ow['name']!=w['name']: ow['morale']=max(0,int(ow.get('morale',50))-random.randint(1,3))
  sync_company_payroll_stats()
  st.session_state.news_feed.insert(0,f"**CRISIS BID:** {w['name']} leaves {from_comp} for {to_comp}. Payroll shift {money(old_sal)} → {money(w['salary'])}.")
  st.session_state.setdefault('storyline_flags',[]).insert(0,{'week':st.session_state.week,'flag':'Crisis roster exit','target':w['name'],'company':from_comp,'notes':f"Moved to {to_comp}. {dec.get('reason','')[:120]}"})
  bw['payroll_change']=old_sal-w['salary']
  bw['status']='completed'
 elif outcome=='stay_loyal':
  crisis.adjust_brand_loyalty(w,random.randint(3,8),f'Loyalty during {from_comp} crisis')
  w['morale']=min(100,int(w.get('morale',50))+random.randint(1,4))
  bw['status']='completed'
 elif outcome=='renegotiate':
  w['renewal_status']='Wants More Money'; w['negotiation_offer_salary']=int(w['salary']*1.12)
  crisis.adjust_brand_loyalty(w,-2,'Demands renegotiation during crisis')
  bw['status']='renegotiate'
 elif outcome=='request_release':
  w['requested_release']=True; w['morale']=max(0,int(w.get('morale',50))-5)
  crisis.adjust_brand_loyalty(w,-10,'Requested release during crisis')
  bw['status']='release_requested'
 else:
  bw['status']='completed'
 bw['ai_decision']=dec; bw['history'].append({'week':st.session_state.week,'action':outcome,'detail':dec.get('reason',''),'admin':bool(admin_force)})
 save_universe()
 return True,outcome

def render_financial_crisis_panel(comp,show_tools=True,key_prefix='crisis'):
 crisis.ensure_crisis_state()
 ensure_finance_state()
 crisis.render_financial_crisis_banner(comp,lambda:get_company_budget(comp))
 cr=st.session_state.company_crisis.get(comp,crisis.default_crisis_rec())
 status=cr.get('status','Healthy')
 in_crisis=status=='Financial Crisis'
 vuln=[]
 ac=st.session_state.get('assigned_company')
 rival_bid=ac in PLAYABLE and ac!=comp and in_crisis
 can_manage=can_edit_company(comp) or is_admin()
 with bfg_card(f'{comp} — Financial Crisis & Bidding'):
  if in_crisis:
   vuln=crisis.identify_vulnerable_wrestlers(comp,payroll_wrestlers,is_champion_name,crisis_story_fn)
   if vuln:
    st.markdown('**Vulnerable talent** (rivals may bid after Financial Crisis):')
    for v in vuln[:8]:
     w=v['wrestler']
     st.caption(f"**{w['name']}** · Loyalty {w.get('brand_loyalty',50)} ({crisis.loyalty_tier(w.get('brand_loyalty',50))}) · Morale {w.get('morale')} · {', '.join(v['reasons'])}")
   else:
    st.caption('No highly vulnerable wrestlers flagged this week.')
  else:
   st.caption('Bidding wars unlock after 3 consecutive weeks below $0.')
  wars=[bw for bw in st.session_state.bidding_wars if bw.get('from_company')==comp]
  if wars:
   st.markdown('**Active bidding wars**')
   for bw in wars[:6]:
    w=find(bw.get('wrestler'))
    with st.expander(f"#{bw.get('id')} {bw.get('wrestler')} — {bw.get('status')}",expanded=(bw.get('status')=='ai_decided')):
     if bw.get('offers'):
      for o in bw['offers']: st.write(f"- {o.get('company')}: {money(o.get('salary'))} / {o.get('years',2)}yr · bonus {money(o.get('bonus',0))}")
     if bw.get('ai_decision') and w:
      crisis.render_ai_decision_card(bw['ai_decision'],w,comp)
      if bw.get('twitter_reaction'): st.caption(f"Twitter: {bw['twitter_reaction']}")
      if bw.get('locker_room_reaction'): st.caption(f"Locker room: {bw['locker_room_reaction']}")
     if can_manage and bw.get('status') in ('ai_decided','open','delayed') and w and bw.get('ai_decision'):
      o1,o2,o3=st.columns(3)
      if o1.button('Approve AI decision',key=f'{key_prefix}_app_{bw["id"]}'):
       ok,msg=execute_bidding_outcome(bw,bw['ai_decision']); st.success(msg) if ok else st.error(msg); st.rerun()
      if o2.button('Block (stay)',key=f'{key_prefix}_blk_{bw["id"]}'):
       execute_bidding_outcome(bw,{'outcome':'stay_loyal','target_company':comp,'reason':'Admin blocked move — wrestler stays.'},admin_force='stay_loyal'); st.rerun()
      if is_admin() and o3.button('Admin override → accept best',key=f'{key_prefix}_ov_{bw["id"]}'):
       bo=(bw.get('ai_decision') or {}).get('best_offer')
       if bo: execute_bidding_outcome(bw,bw['ai_decision'],admin_force='accept'); st.rerun()
  if rival_bid and vuln:
   st.markdown(f'**Submit rival bid** ({ac} → {comp} in crisis)')
   names=[v['wrestler']['name'] for v in vuln]
   tgt=st.selectbox('Target wrestler',names,key=f'{key_prefix}_bid_tgt_{comp}')
   w=find(tgt)
   if w:
    bw=crisis.get_open_bidding_for_wrestler(tgt,comp) or crisis.create_bidding_war(w,comp)
    sal=st.number_input('Salary offer',100000,25000000,int(w['salary']*1.08),step=50000,key=f'{key_prefix}_sal_{tgt}')
    yrs=st.number_input('Years',1,5,3,key=f'{key_prefix}_yrs_{tgt}')
    bon=st.number_input('Signing bonus',0,5000000,500000,step=50000,key=f'{key_prefix}_bon_{tgt}')
    creative=st.checkbox('Creative promise',True,key=f'{key_prefix}_cr_{tgt}')
    title_o=st.checkbox('Title opportunity',key=f'{key_prefix}_tit_{tgt}')
    sponsor=st.checkbox('Sponsor/media opportunity',key=f'{key_prefix}_spo_{tgt}')
    if st.button('Submit offer',key=f'{key_prefix}_sub_{tgt}'):
     offer={'company':ac,'salary':sal,'years':yrs,'bonus':bon,'creative_promise':creative,'title_opportunity':title_o,'sponsor_media':sponsor,'submitted_by':st.session_state.get('player_name','')}
     bw['offers']=[o for o in bw.get('offers',[]) if o.get('company')!=ac]+[offer]
     bw['status']='open'
     st.session_state.news_feed.insert(0,f"{ac} submitted crisis bid for {tgt} ({money(sal)}/yr).")
     save_universe(); st.success('Offer submitted.'); st.rerun()
  if show_tools and in_crisis and can_manage:
   with st.expander('Financial Crisis tools',expanded=False):
    pool=payroll_wrestlers(comp)
    if not pool: st.caption('No payroll wrestlers.')
    else:
     tw_sel=st.selectbox('Wrestler',sorted([w['name'] for w in pool]),key=f'{key_prefix}_tool_w')
     w=find(tw_sel)
     t1,t2,t3,t4=st.columns(4)
     if t1.button('Ask pay cut',key=f'{key_prefix}_pcut'):
      if w['salary']>400000:
       w['salary']=int(w['salary']*.9); w['rejected_pay_cut']=random.random()<.35
       if w['rejected_pay_cut']: crisis.adjust_brand_loyalty(w,-12,'Rejected pay cut'); w['morale']=max(0,w['morale']-8); st.warning(f"{w['name']} rejected the pay cut.")
       else: crisis.adjust_brand_loyalty(w,-4,'Accepted pay cut'); st.success('Pay cut accepted.')
      else: st.warning('Salary too low to cut further.')
      save_universe(); st.rerun()
     if t2.button('Defer salary (1 wk)',key=f'{key_prefix}_defer'):
      mp_add_transaction(comp,'Salary Deferred',f"Deferred {w['name']} payroll",int(w['salary']//52))
      w['pay_cut_week']=st.session_state.week; st.toast('Salary deferred one week.')
      save_universe(); st.rerun()
     if t3.button('Creative promise (+loyalty)',key=f'{key_prefix}_prom'):
      crisis.adjust_brand_loyalty(w,6,'Creative promise during crisis'); w['morale']=min(100,w['morale']+4); save_universe(); st.rerun()
     if t4.button('Request AI bidding review',key=f'{key_prefix}_ai'):
      if not in_crisis: st.error('Financial Crisis required.')
      else:
       bw=crisis.get_open_bidding_for_wrestler(w['name'],comp) or crisis.create_bidding_war(w,comp)
       if not bw.get('offers'): st.warning('No rival offers yet — rivals must submit bids first.')
       else:
        dec=crisis.ai_bidding_decision(w,bw['offers'],comp,find,is_champion_name,crisis_story_fn)
        bw['ai_decision']=dec; bw['status']='delayed' if dec.get('delay') else 'ai_decided'
        if dec.get('delay'): st.warning(dec.get('reason',''))
        save_universe(); st.rerun()
     if st.button('Release wrestler',key=f'{key_prefix}_rel'):
      release_wrestler_contract(w,comp); crisis.adjust_brand_loyalty(w,-20,'Released during crisis'); st.rerun()
  if st.session_state.brand_loyalty_history:
   with st.expander('Brand loyalty history',expanded=False):
    for h in [x for x in st.session_state.brand_loyalty_history if x.get('company')==comp][:15]:
     st.caption(f"Week {h.get('week')} — {h.get('name')}: {h.get('delta'):+} → {h.get('loyalty')} ({h.get('reason','')})")

def render_finance_company_panel(comp):
 ensure_finance_state()
 render_money_meter(comp,compact=False,show_ticker=True,show_sponsor=True,show_health=True)
 render_financial_crisis_panel(comp,show_tools=True,key_prefix=f'fin_{comp}')
 render_brand_hub_embed(comp,compact=True,key_prefix=f'fin_hub_{comp}')
 render_brand_exclusives_section(comp,f'fin_ex_{comp}',compact=True)
 fin=st.session_state.company_finance[comp]
 pay=int(fin.get('payroll',0) or company_payroll(comp)); rem_after_pay=fin['starting_budget']-pay
 rules=COMPANY_LOGISTICS_RULES[comp]
 pl=fin['weekly_last_pl']
 pl_disp=f"<span style='color:#2ecc71'>{money(pl)}</span>" if pl>=0 else f"<span style='color:#e74c3c'>{money(pl)}</span>"
 c1,c2,c3,c4=st.columns(4)
 c1.metric('Starting Budget',money(fin['starting_budget'])); c2.metric('Total Payroll',money(pay)); c3.metric('Current Bank After Payroll',money(rem_after_pay)); c4.metric('Current Bank',money(fin['current_budget']))
 c5,c6,c7,c8=st.columns(4)
 c5.markdown(f'<div class="top-card"><div class="card-title">Last Show P/L</div><div class="card-number">{pl_disp}</div></div>',unsafe_allow_html=True)
 c6.metric('Season Revenue',money(fin['season_revenue'])); c7.metric('Season Expenses',money(fin['season_expenses'])); c8.metric('Season P/L',money(fin['season_profit_loss']))
 with bfg_card(f'{comp} season totals'):
  st.write(f"**Sponsor savings:** {money(fin['sponsor_savings_total'])} · **Merchandise:** {money(fin['merch_revenue_total'])} · **Media:** {money(fin['media_revenue_total'])} · **Appearances:** {money(fin['appearance_revenue_total'])}")
  st.write(f"**Contract spending:** {money(fin.get('contract_spending_total',0))} · **Trade in/out:** {money(fin['trade_cash_in'])} / {money(fin['trade_cash_out'])} · **Attractions:** {money(fin['attraction_spending'])} · **Random events net:** {money(fin['random_event_net'])}")
  st.write(f"**Biggest gain:** {fin['biggest_gain']['label'] or '—'} ({money(fin['biggest_gain']['amount'])}) · **Biggest expense:** {fin['biggest_expense']['label'] or '—'} ({money(fin['biggest_expense']['amount'])})")
  st.caption(f"{rules.get('hotel_note','')} · {rules.get('transport_note','')}")
 lh=next((h for h in reversed(st.session_state.get('weekly_history',[])) if h.get('company')==comp),None)
 if lh:
  sq=(lh.get('logistics') or {}).get('show_quality',{})
  sell=sq.get('sellout_status') or (lh.get('logistics') or {}).get('sellout_status')
  if sell:
   st.write(f"**Last show gate:** {sell} · {sq.get('show_descriptor','')[:100]}")
 ledger=[t for t in st.session_state.finance_ledger if t.get('company')==comp]
 with bfg_card(f'{comp} transaction ledger'):
  if not ledger: st.caption('No transactions yet — payroll, shows, appearances, trades, and events post here.')
  else:
   lp=st.selectbox('Entries per page',[15,25,40,60],index=1,key=f'led_per_{comp}')
   pages=max(1,(len(ledger)+lp-1)//lp); lpg=st.number_input('Page',1,pages,1,key=f'led_pg_{comp}')
   for t in ledger[(lpg-1)*lp:lpg*lp]:
    amt=t['amount']; col='#2ecc71' if amt>=0 else '#e74c3c'; sign='+' if amt>=0 else '−'
    src=t.get('source','')
    st.markdown(f"<div class='small-text'><b>Week {t['week']}</b> · {t['company']} · {t['category']} · <span style='color:{col}'>{sign}{money(abs(amt))}</span><br>{t['description']}<br>Budget {money(t['budget_before'])} → {money(t['budget_after'])}{(' · '+src) if src else ''}</div>",unsafe_allow_html=True)
 reports=[r for r in st.session_state.show_finance_reports if r.get('company')==comp]
 with bfg_card(f'{comp} show finance history'):
  if not reports: st.caption('Run a show to build finance reports for this brand.')
  else:
   for r in reports[:6]:
    pl=r.get('profit_loss',0); pc='#2ecc71' if pl>=0 else '#e74c3c'
    with st.expander(f"Week {r.get('week')} — {r.get('show_name')} — P/L {money(pl)}",expanded=(r==reports[0])):
     st.markdown(f"**{r.get('venue')}, {r.get('city')}** · Attendance {r.get('attendance',0):,} · Viewership {r.get('viewership',0):,}")
     st.write('**Revenue**')
     for k,v in r.get('revenue',{}).items():
      if v: st.write(f"• {k.replace('_',' ').title()}: {money(v)}")
     st.write('**Expenses**')
     for k,v in r.get('expenses',{}).items():
      if v: st.write(f"• {k.replace('_',' ').title()}: {money(v)}")
     st.markdown(f"**Total revenue:** {money(r.get('total_revenue',0))} · **Total expenses:** {money(r.get('total_expenses',0))} · **Profit/Loss:** <span style='color:{pc}'>{money(pl)}</span>",unsafe_allow_html=True)
     st.markdown(f"**Bank:** {money(r.get('budget_before',0))} → {money(r.get('budget_after',0))}")
 with st.expander('Movie / Filming Projects',expanded=False):
  film_opts=list(FILMING_TEMPLATES.keys())
  fw=find(clean_name_selector('Wrestler',f'film_w_{comp}',company=comp,entity_type='Wrestler',default_company=comp)) if opts(comp) else None
  ft=st.selectbox('Project template',film_opts,key=f'film_t_{comp}')
  if st.button('Start filming project',key=f'film_go_{comp}') and fw:
   tpl=FILMING_TEMPLATES[ft]
   rec_f={'week':st.session_state.week,'company':comp,'wrestler':fw['name'],'template':ft,'partner':tpl['partner'],'type':tpl['type'],'length':tpl['length'],'revenue':tpl['revenue'],'status':'active'}
   st.session_state.film_projects.insert(0,rec_f)
   fw['popularity']=min(100,fw['popularity']+tpl['popularity'])
   fw['stamina']=max(0,fw['stamina']+tpl['stamina'])
   if random.random()<tpl.get('miss_risk',0): fw['status']='Part-Time'; st.warning(f"{fw['name']} may miss shows while filming.")
   if random.random()<tpl.get('tension',0):
    for ow in random.sample(payroll_wrestlers(comp),min(2,len(payroll_wrestlers(comp)))):
     if ow['name']!=fw['name']: ow['morale']=max(0,ow['morale']-3)
   add_transaction(comp,'Film Revenue',f"{fw['name']} filming — {ft}",int(tpl['revenue']),source='filming')
   finance_flash(comp,int(tpl['revenue']),f"filming project started")
   st.session_state.news_feed.insert(0,f"{fw['name']} filming ({tpl['partner']}): +{money(tpl['revenue'])} · popularity +{tpl['popularity']}")
   st.success('Filming project started.'); st.rerun()
  for f in [x for x in st.session_state.film_projects if x.get('company')==comp][:8]:
   st.write(f"Week {f.get('week')} — {f.get('wrestler')} — {f.get('template')} — {money(f.get('revenue',0))} — {f.get('status')}")
 filt=[h for h in st.session_state.weekly_history if h.get('company')==comp]
 with bfg_card(f'{comp} show logistics & viewership'):
  for h in filt[-8:][::-1]:
   lg=h.get('logistics') or {}
   att=int(lg.get('attendance') or 0); tp=lg.get('ticket_price',65)
   vw=int(h.get('viewership',0)); er=h.get('episode_rating',h.get('final_rating','—'))
   plc='#2ecc71' if h.get('profit',0)>=0 else '#e74c3c'
   st.markdown(f"<div class='event-box'><b>Week {h['week']} — {h.get('show_name')}</b> — {h.get('venue')}, {h.get('city')}<br><b>Rating:</b> {er}/10 · <b>Viewership:</b> {vw:,}<br>Attendance {att:,} × ${tp} ticket · Revenue {money(lg.get('ticket_revenue',0))} · P/L <span style='color:{plc}'>{money(h.get('profit',0))}</span><br>{logistics_ai_summary(lg) if lg else ''}</div>",unsafe_allow_html=True)

CALENDAR_SHOW_TYPES=['Weekly Show','Go-Home Show','Fallout Show','TV Special','PLE','Stadium Show','International Tour','Tournament','Crossover Event','Sponsor Activation','Media Appearance','Travel Week','Off Week','Homecoming Show']
CALENDAR_STATUSES=['Planned','Draft','Locked','Completed','Needs Info','Sponsor Pending']
CALENDAR_MONTHS=['January','February','March','April','May','June','July','August','September','October','November','December']

def next_bookable_week():
 return int(st.session_state.get('week',0))+1

def get_scheduled_show(company,week):
 wk=int(week)
 for e in st.session_state.schedule_calendar:
  if int(e.get('week',-1))==wk and e.get('company')==company:
   return e
 return None

def schedule_entry_status(e):
 if e.get('status')=='Completed': return 'Completed'
 if st.session_state.get('calendar_locked') and e.get('status')!='Completed':
  return 'Locked' if e.get('status') in ('Locked','Planned','') or not e.get('status') else e.get('status')
 return e.get('status') or 'Planned'

def schedule_show_is_ple(show_type):
 return show_type in ('PLE','Stadium Show','Crossover Event')

def schedule_to_episode_type(show_type):
 m={'Weekly Show':'Weekly Show','PLE':'PLE','TV Special':'TV Special','Stadium Show':'Stadium Show','International Tour':'International Tour','Tournament':'Tournament','Go-Home Show':'Go-home before PLE','Fallout Show':'Fallout after PLE','Homecoming Show':'Homecoming Show','Crossover Event':'TV Special'}
 return m.get(show_type,show_type)

def normalize_schedule_entry(e):
 vdata=e.get('venue_data') or {}
 if not vdata and e.get('venue'):
  vdata=next((dict(x) for x in VENUES if x.get('venue')==e.get('venue') and x.get('city')==e.get('city')),{})
  e['venue_data']=vdata
 cap=int(e.get('capacity') or vdata.get('capacity',15000))
 vdata['capacity']=cap; e['venue_data']=vdata; e['capacity']=cap
 if not e.get('show_name'):
  e['show_name']={'NXT':'NXT','SmackDown':'SmackDown','WCW':'WCW'}.get(e.get('company',''),'')+f" Week {e.get('week','')}"
 proj=project_schedule_entry(e.get('company','NXT'),vdata,e.get('show_type','Weekly Show'),e.get('show_name',''))
 for k,v in proj.items(): e.setdefault(k,v)
 e.setdefault('status','Planned')
 return e

def project_schedule_entry(company,venue,show_type,show_name=''):
 ple=schedule_show_is_ple(show_type)
 rating_est=7.8 if ple else 7.0
 log=compute_show_logistics(company,venue,[],[],rating_est,ple,schedule_to_episode_type(show_type),show_name or 'Schedule Preview')
 sponsors=COMPANIES.get(company,{}).get('sponsors',[])
 log,_=showq.apply_show_quality_to_log(log,company,venue,[],[],rating_est,{}, {},'','',ple,find,is_champion_name,rivalry_heat_for,sponsors=sponsors)
 rules=COMPANY_LOGISTICS_RULES.get(company,{})
 cap=max(1,int(venue.get('capacity',15000)))
 sellout_pct=min(100,int(100*log.get('attendance',0)/cap)) if cap else 0
 sell_lbl,_=sellout_label(int(log.get('attendance',0)),cap)
 return {
  'projected_attendance':int(log.get('attendance',0)),'projected_profit_loss':int(log.get('profit_loss',0)),
  'projected_revenue':int(log.get('weekly_income',0)),'projected_expenses':int(log.get('weekly_expenses',0)),
  'projected_ticket_revenue':int(log.get('ticket_revenue',0)),'projected_sellout_pct':sellout_pct,'projected_sellout_label':sell_lbl,
  'venue_cost':int(log.get('venue_rental',0)),'security_cost':int(log.get('security_cost',0)),
  'production_cost':int(log.get('production_cost',0)),'hotel_estimate':int(log.get('hotel_final',0)),
  'hotel_base':int(log.get('hotel_base',0)),'hotel_savings':int(log.get('hotel_savings',0)),
  'transport_estimate':int(log.get('transport_final',0)),'transport_base':int(log.get('transport_base',0)),
  'transport_savings':int(log.get('transport_savings',0)),
  'hotel_sponsor':rules.get('hotel_sponsor'),'transport_sponsor':rules.get('transport_sponsor'),
 }

def migrate_schedule_calendar():
 cal=st.session_state.get('schedule_calendar',[])
 for i,e in enumerate(cal):
  cal[i]=normalize_schedule_entry(dict(e))
 st.session_state.schedule_calendar=cal

def lock_year_schedule():
 migrate_schedule_calendar()
 for e in st.session_state.schedule_calendar:
  if e.get('status')!='Completed': e['status']='Locked'
 st.session_state.calendar_locked=True
 st.session_state.calendar_ai_notes=analyze_year_schedule(st.session_state.schedule_calendar)

def reset_year_schedule(clear_entries=False):
 st.session_state.calendar_locked=False
 st.session_state.cal_lock_confirm=False
 st.session_state.cal_reset_confirm=False
 if clear_entries:
  st.session_state.schedule_calendar=[]
  st.session_state.calendar_ai_notes=[]

def format_schedule_location(e):
 city=(e.get('city') or '').strip() or 'TBD'
 region=(e.get('region') or '').strip()
 country=(e.get('country') or '').strip()
 if country in ('United States','U.S.','US','USA'):
  if region and region!=city: return f'{city}, {region}, USA'
  return f'{city}, USA' if city else 'USA'
 if country in ('United Kingdom','UK','Great Britain'):
  rg=region or 'England'
  return f'{city}, {rg}, UK' if city else 'UK'
 if country in ('Canada',):
  if region and region!=city: return f'{city}, {region}, Canada'
  return f'{city}, Canada' if city else 'Canada'
 if country in ('Puerto Rico',):
  return f'{city}, Puerto Rico' if city else 'Puerto Rico'
 if region and region!=city and country: return f'{city}, {region}, {country}'
 if country: return f'{city}, {country}' if city else country
 return city

def format_schedule_date_short(e):
 d=str(e.get('date') or '').strip()
 if not d: return '—'
 try:
  parts=d.split('-')
  if len(parts)>=3:
   y,m,day=int(parts[0]),int(parts[1]),int(parts[2])
   months=['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
   return f'{months[m]} {day}, {y}' if m<13 else d
 except (ValueError, IndexError): pass
 return d[:14]

def format_schedule_pl_display(e):
 pl=int(e.get('projected_profit_loss',0) or 0)
 sign='+' if pl>=0 else '−'
 return f'{sign}{money(abs(pl))}', 'cal-pl-pos' if pl>=0 else 'cal-pl-neg'

def filter_calendar_table_rows(rows,brand=None,show_type=None,month=None,status=None,country=None,search='',week_only=None):
 out=list(rows)
 if brand and brand!='All': out=[e for e in out if e.get('company')==brand]
 if show_type and show_type!='All': out=[e for e in out if e.get('show_type')==show_type]
 if month and month!='All': out=[e for e in out if (e.get('month') or '')==month]
 if status and status!='All':
  out=[e for e in out if schedule_entry_status(e)==status or (e.get('status') or '')==status]
 if country and country!='All': out=[e for e in out if (e.get('country') or '')==country]
 if week_only is not None: out=[e for e in out if int(e.get('week',0))==int(week_only)]
 if search and search.strip():
  q=search.strip().lower()
  out=[e for e in out if q in ' '.join([str(e.get(k,'')) for k in ('show_name','venue','city','region','country','company','notes','month')]).lower()]
 return out

def render_calendar_readable_cards(rows):
 """Full-text schedule cards — every word visible, no truncation."""
 if not rows: return
 st.caption(f'**{len(rows)}** events — full text below (scroll if needed)')
 parts=['<div class="cal-readable-list">']
 for e in rows:
  loc=format_schedule_location(e)
  venue=(e.get('venue') or '—').strip()
  show=(e.get('show_name') or '—').strip()
  stype=(e.get('show_type') or '—').strip()
  pl_txt,pl_cls=format_schedule_pl_display(e)
  stt=schedule_entry_status(e)
  head=f"Week {int(e.get('week',0))} · {format_schedule_date_short(e)} · {e.get('company','')} · {stype}"
  parts.append(
   f'<div class="cal-readable-card">'
   f'<div class="cal-r-head">{html_escape(head)}</div>'
   f'<div class="cal-r-line"><span class="cal-r-label">Show name</span> <span class="cal-r-val">{html_escape(show)}</span></div>'
   f'<div class="cal-r-line"><span class="cal-r-label">Location</span> <span class="cal-r-loc">{html_escape(loc)}</span></div>'
   f'<div class="cal-r-line"><span class="cal-r-label">Venue</span> <span class="cal-r-venue">{html_escape(venue)}</span></div>'
   f'<div class="cal-r-line"><span class="cal-r-label">Capacity</span> <span class="cal-r-val">{int(e.get("capacity",0)):,}</span></div>'
   f'<div class="cal-r-line"><span class="cal-r-label">Est. attendance</span> <span class="cal-r-val">{int(e.get("projected_attendance",0)):,}</span></div>'
   f'<div class="cal-r-line"><span class="cal-r-label">Est. profit/loss</span> <span class="{pl_cls}">{html_escape(pl_txt)}</span></div>'
   f'<div class="cal-r-line"><span class="cal-r-label">Status</span> <span class="cal-status-pill">{html_escape(stt)}</span></div>'
   f'</div>'
  )
 parts.append('</div>')
 st.markdown(''.join(parts),unsafe_allow_html=True)

def render_calendar_year_table(rows):
 if not rows: return
 parts=['<div class="cal-yscroll"><table class="cal-schedule-table"><thead><tr>',
  '<th class="col-week">Week</th><th class="col-date">Date</th><th class="col-brand">Brand</th>',
  '<th class="col-show">Show</th><th class="col-type">Type</th><th class="col-location">Location</th>',
  '<th class="col-venue">Venue</th><th class="col-cap">Capacity</th><th class="col-att">Est. Att.</th>',
  '<th class="col-pl">Est. P/L</th><th class="col-status">Status</th></tr></thead><tbody>']
 for e in rows:
  loc=html_escape(format_schedule_location(e))
  venue=html_escape((e.get('venue') or '—').strip())
  show=html_escape((e.get('show_name') or '—').strip())
  pl_txt,pl_cls=format_schedule_pl_display(e)
  stt=html_escape(schedule_entry_status(e))
  parts.append(
   f'<tr>'
   f'<td class="col-week">Week {int(e.get("week",0))}</td>'
   f'<td class="col-date">{html_escape(format_schedule_date_short(e))}</td>'
   f'<td class="col-brand">{html_escape(e.get("company",""))}</td>'
   f'<td class="col-show">{show}</td>'
   f'<td class="col-type">{html_escape(e.get("show_type") or "—")}</td>'
   f'<td class="col-location">{loc}</td>'
   f'<td class="col-venue">{venue}</td>'
   f'<td class="col-cap">{int(e.get("capacity",0)):,}</td>'
   f'<td class="col-att">{int(e.get("projected_attendance",0)):,}</td>'
   f'<td class="col-pl {pl_cls}">{html_escape(pl_txt)}</td>'
   f'<td class="col-status"><span class="cal-status-pill">{stt}</span></td></tr>'
  )
 parts.append('</tbody></table></div>')
 st.markdown(''.join(parts),unsafe_allow_html=True)

def calendar_entry_index(e):
 return f"{e.get('company','')}|{int(e.get('week',0))}"

def load_calendar_entry_into_form(e):
 st.session_state.cal_month=e.get('month',CALENDAR_MONTHS[0])
 st.session_state.cal_week=int(e.get('week',1))
 try:
  st.session_state.cal_date=date.fromisoformat(str(e.get('date',''))[:10])
 except (ValueError, TypeError):
  st.session_state.cal_date=date.today()
 st.session_state.cal_sname=e.get('show_name',f"{e.get('company')} Week {e.get('week')}")
 st.session_state.cal_stype=e.get('show_type','Weekly Show')
 st.session_state.cal_cap=int(e.get('capacity',15000))
 st.session_state.cal_ticket=int(e.get('ticket_price',65))
 st.session_state.cal_status=e.get('status','Planned')
 st.session_state.cal_travel=bool(e.get('travel_required'))
 st.session_state.cal_hotel=bool(e.get('hotel_required'))
 st.session_state.cal_transport=bool(e.get('transportation_required'))
 st.session_state.cal_rivalry=e.get('planned_rivalry','')
 st.session_state.cal_notes=e.get('notes','')

def mark_schedule_completed(company,week,hist,log,rating):
 wk=int(week)
 for e in st.session_state.schedule_calendar:
  if int(e.get('week',-1))==wk and e.get('company')==company:
   e['status']='Completed'
   e['actual_attendance']=int(log.get('attendance',0))
   e['actual_profit_loss']=int(log.get('profit_loss',0))
   e['actual_rating']=rating
   e['viewership']=int(hist.get('viewership') or log.get('viewership') or int(log.get('attendance',0)*1.2))
   e['episode_rating']=hist.get('episode_rating',rating)
   e['dirt_sheet_headline']=(hist.get('dirt_sheet_review') or '')[:80]
   sq=log.get('show_quality',{})
   e['sellout_status']=sq.get('sellout_status') or log.get('sellout_status')
   e['sellout_label']=e.get('sellout_status')
   e['show_descriptor']=sq.get('show_descriptor','')[:120]
   e['booked']=True
   break

def analyze_year_schedule(entries):
 warns=[]
 for comp in PLAYABLE:
  ent=sorted([e for e in entries if e.get('company')==comp],key=lambda x:int(x.get('week',0)))
  if not ent: continue
  intl_run=0
  for e in ent:
   cap=int(e.get('capacity') or e.get('venue_data',{}).get('capacity',15000))
   wk=int(e.get('week',0))
   vn=e.get('venue','venue')
   sn=e.get('show_name',e.get('show_type','Show'))
   if e.get('country')!='United States':
    intl_run+=1
    if intl_run>=2: warns.append(f'{comp} Week {wk}: back-to-back international travel — hotel/transport costs stack up.')
   else: intl_run=0
   if cap>=55000: warns.append(f'{comp} should build the main rivalry for at least 4 weeks before running {vn} at Week {wk} (stadium sellout risk).')
   if e.get('show_type')=='PLE': warns.append(f'This PLE is locked for Week {wk} ({sn}). Start building the main rivalry by Week {max(1,wk-4)}.')
   pl=int(e.get('projected_profit_loss',0))
   if pl<-500000: warns.append(f'{comp} Week {wk} ({vn}) projects a loss of {money(pl)} — improve story heat or downsize venue.')
   ht=e.get('hometown') or []
   city=(e.get('city') or '').lower()
   if ht and city and not any((find(h) or {}).get('hometown','').lower() in city or h.lower() in city for h in ht):
    warns.append(f'{comp} Week {wk}: hometown star(s) {", ".join(ht)} may not match {e.get("city")} — plan a homecoming angle.')
   if cap>=40000 and int(e.get('projected_sellout_pct',0))<55:
    warns.append(f'{comp} Week {wk}: stadium may be too large for current projected sellout — story must improve to sell out.')
  if comp=='SmackDown': warns.append('SmackDown saves hotel money through Marriott, so some travel weeks are less risky.')
  if comp=='WCW': warns.append('WCW has transportation savings from Tesla/Mercedes, but stadium rental can still be expensive.')
  if comp=='NXT': warns.append('NXT pays full hotel/transport but can offset costs with Mattel/DC/Netflix/Olympics media revenue.')
 return warns[:24]

def schedule_ai_analysis(entries,company=None):
 migrate_schedule_calendar()
 warns=analyze_year_schedule(entries)
 lines=['Full-year schedule analysis:']+['• '+w for w in warns]
 if company:
  ent=[e for e in entries if e.get('company')==company]
  lines.append(f'{company} has {len(ent)} scheduled shows.')
 prompt='Bound For Glory GM schedule analyst. Give 6 short bullet warnings about this yearly wrestling calendar:\n'+'\n'.join(f"Week {e.get('week')} {e.get('company')} {e.get('show_type')} {e.get('show_name')} at {e.get('venue')} {e.get('city')} proj P/L {money(e.get('projected_profit_loss',0))}" for e in sorted(entries,key=lambda x:(x.get('week',0)))[:40])
 extra=ai(prompt)
 if extra: lines.append(extra)
 return lines

def render_schedule_lock_badge():
 locked=st.session_state.get('calendar_locked',False)
 if locked:
  st.markdown("<span style='background:linear-gradient(90deg,#d4af37,#2ecc71);color:#111;padding:6px 14px;border-radius:999px;font-weight:900'>● LOCKED</span>",unsafe_allow_html=True)
 else:
  st.markdown("<span style='background:#444;color:#ccc;padding:6px 14px;border-radius:999px;font-weight:700'>○ UNLOCKED</span>",unsafe_allow_html=True)

def sort_roster_list(data,sort_by):
 if sort_by=='Overall high to low': return sorted(data,key=lambda x:-x['overall'])
 if sort_by=='Popularity high to low': return sorted(data,key=lambda x:-x['popularity'])
 if sort_by=='Momentum high to low': return sorted(data,key=lambda x:-x['momentum'])
 if sort_by=='Salary high to low': return sorted(data,key=lambda x:-x['salary'])
 if sort_by=='Division': return sorted(data,key=lambda x:(x.get('division',''),x['name'].lower()))
 if sort_by=='Record best to worst': return sorted(data,key=lambda x:-(x.get('wins',0)-x.get('losses',0)))
 return sorted(data,key=lambda x:x['name'].lower())

def filter_roster_list(data,search,div_f,align_f,status_f,champs_only,comp,debut_f='All'):
 out=data
 if search: out=[w for w in out if search.lower() in w['name'].lower()]
 if div_f!='All': out=[w for w in out if w.get('division')==div_f]
 if align_f!='All': out=[w for w in out if w['alignment']==align_f]
 if status_f!='All': out=[w for w in out if w.get('status')==status_f]
 if debut_f=='Not Debuted': out=[w for w in out if w.get('debut_status')=='Not Debuted']
 elif debut_f=='Debuted': out=[w for w in out if w.get('debut_status')=='Debuted']
 elif debut_f=='Ignored After Debut': out=[w for w in out if w.get('debut_status')=='Debuted' and int(w.get('weeks_not_used_after_debut',0))>=2]
 elif debut_f=='Returning Soon': out=[w for w in out if w.get('debut_status')=='Returning Soon']
 elif debut_f=='On Hiatus': out=[w for w in out if w.get('debut_status')=='On Hiatus']
 if champs_only:
  ch=set()
  for t,v in st.session_state.champions.get(comp,{}).items():
   if v and v!='Vacant' and v!='Place Holder': ch.add(v)
  out=[w for w in out if w['name'] in ch]
 return out

def render_wrestler_card(w,comp,div_opts,key_prefix,editable=True):
 with bfg_card(w['name']):
  c1,c2=st.columns([.22,.78])
  with c1: show_img(w['name'],105)
  with c2:
   st.markdown(f"<div style='font-size:20px;font-weight:900;margin-bottom:6px'>{w['name']}</div>",unsafe_allow_html=True)
   st.markdown(f"{align_badge_html(w['alignment'])} <span class='overall-badge'>OVR {w['overall']}</span>",unsafe_allow_html=True)
   aff=f" · Tag: <b>{w.get('tag_team_affiliation')}</b>" if w.get('tag_team_affiliation') else ''
   ensure_contract_fields(); sync_wrestler_from(w)
   st.markdown(f"<div class='small-text' style='margin-top:8px'><b>{w['company']}</b> · {w.get('division','')} · From: <b>{w.get('from_location') or w.get('hometown') or 'Unknown'}</b>{aff}</div>",unsafe_allow_html=True)
   st.markdown(f"<div class='small-text'>Record <b>{rec(w)}</b> · Pop <b>{w['popularity']}</b> · Mom <b>{w['momentum']}</b> · Salary <b>{money(w['salary'])}</b></div>",unsafe_allow_html=True)
   st.markdown(f"<div class='small-text'>{contract_display_line(w)} · Status <b>{w.get('contract_status','Active')}</b> · Renewal <b>{w.get('renewal_status','Not Started')}</b></div>",unsafe_allow_html=True)
   ensure_wrestler_debut_fields()
   lb=w.get('last_booked_week'); lb_s=str(lb) if lb is not None else '—'
   wks_unused=int(w.get('weeks_not_used_after_debut',0))
   st.markdown(f"<div class='small-text'><b>Debut Status:</b> {w.get('debut_status','Debuted')} · <b>Debut Week:</b> {w.get('debut_week') or '—'} · <b>Last Booked:</b> {lb_s} · <b>Weeks Since Last Used:</b> {wks_unused} · Debut rating {w.get('debut_rating') or '—'}/10</div>",unsafe_allow_html=True)
   if w.get('debut_status')=='Debuted' and wks_unused>=2: st.warning(f"{w['name']} debuted but has not been booked for {wks_unused} week(s). Morale/momentum at risk.")
   st.markdown(stat_progress('Morale',w['morale'],'#9b59b6'),unsafe_allow_html=True)
   st.markdown(stat_progress('Momentum',w['momentum'],'#3498db'),unsafe_allow_html=True)
   st.markdown(stat_progress('Popularity',w['popularity'],'#e67e22'),unsafe_allow_html=True)
   st.markdown(stat_progress('Stamina',w['stamina'],'#2ecc71'),unsafe_allow_html=True)
   cal_locked=calendar_year_locked()
   stats_editable=editable and not cal_locked
   if editable:
    e1,e2,e3=st.columns(3)
    w['overall']=e1.number_input('Overall',50,100,int(w['overall']),disabled=not stats_editable,key=f'{key_prefix}ov_{w["name"]}')
    w['alignment']=e2.selectbox('Align F/H/N',['F','H','N'],index=['F','H','N'].index(w['alignment']) if w['alignment'] in ['F','H','N'] else 2,key=f'{key_prefix}al_{w["name"]}')
    w['from_display']=e3.text_input('From',w.get('from_location') or w.get('hometown','Unknown'),disabled=cal_locked,key=f'{key_prefix}from_{w["name"]}')
    w['from_location']=w.get('from_display',w.get('from_location','Unknown')); w['hometown']=w['from_location']
    e4,e5,e6=st.columns(3)
    w['division']=e4.selectbox('Division',div_opts,index=div_opts.index(w['division']) if w['division'] in div_opts else 0,key=f'{key_prefix}div_{w["name"]}')
    w['status']=e5.selectbox('Status',['Active','Injured','Suspended','Part-Time'],index=['Active','Injured','Suspended','Part-Time'].index(w['status']) if w['status'] in ['Active','Injured','Suspended','Part-Time'] else 0,key=f'{key_prefix}st_{w["name"]}')
    w['salary']=e6.number_input('Salary',100000,20000000,int(w['salary']),step=50000,disabled=cal_locked,key=f'{key_prefix}sal_{w["name"]}')
    if st.button('Update payroll stat',key=f'{key_prefix}pay_{w["name"]}'): sync_company_payroll_stats(); st.toast(f'{comp} payroll: {money(company_payroll(comp))} · budget: {money(get_company_budget(comp))}')
    w['morale']=st.slider('Morale',0,100,int(w['morale']),disabled=not stats_editable,key=f'{key_prefix}mor_{w["name"]}')
    w['momentum']=st.slider('Momentum',0,100,int(w['momentum']),disabled=not stats_editable,key=f'{key_prefix}mom_{w["name"]}')
    w['popularity']=st.slider('Popularity',0,100,int(w['popularity']),disabled=not stats_editable,key=f'{key_prefix}pop_{w["name"]}')
    w['controversy_risk']=st.slider('Controversy Risk',0,100,int(w.get('controversy_risk',20)),key=f'{key_prefix}cont_{w["name"]}')
    w['fan_support']=st.slider('Fan Support',0,100,int(w.get('fan_support',50)),key=f'{key_prefix}fan_{w["name"]}')
    w['locker_room_reputation']=st.slider('Locker Room Rep',0,100,int(w.get('locker_room_reputation',55)),key=f'{key_prefix}lock_{w["name"]}')
    w['sponsor_trust']=st.slider('Sponsor Trust',0,100,int(w.get('sponsor_trust',60)),key=f'{key_prefix}spon_{w["name"]}')
    w['stamina']=st.slider('Stamina',0,100,int(w['stamina']),disabled=not stats_editable,key=f'{key_prefix}sta_{w["name"]}')
    with st.expander('Contract (Pre-Season / Active)',expanded=not cal_locked):
     if cal_locked: st.caption('Year Locked — Contracts Active. Negotiate on the **Contracts** page.')
     else: st.success('Pre-Season Contract Editing Enabled')
     cy=game_contract_year()
     w['contract_length_years']=st.number_input('Contract length (years)',1,10,int(w.get('contract_length_years',3)),disabled=cal_locked,key=f'{key_prefix}cly_{w["name"]}')
     w['contract_start_year']=st.number_input('Start year',2020,2045,int(w.get('contract_start_year',cy)),disabled=cal_locked,key=f'{key_prefix}csy_{w["name"]}')
     w['contract_expiration_year']=st.number_input('Expiration year',2020,2055,int(w.get('contract_expiration_year',cy+int(w.get('contract_length_years',3)))),disabled=cal_locked,key=f'{key_prefix}cey_{w["name"]}')
     w['contract_status']=st.selectbox('Contract status',CONTRACT_STATUSES,index=CONTRACT_STATUSES.index(w.get('contract_status','Active')) if w.get('contract_status') in CONTRACT_STATUSES else 0,disabled=cal_locked,key=f'{key_prefix}cst_{w["name"]}')
     w['renewal_status']=st.selectbox('Renewal status',RENEWAL_STATUSES,index=RENEWAL_STATUSES.index(w.get('renewal_status','Not Started')) if w.get('renewal_status') in RENEWAL_STATUSES else 0,disabled=cal_locked,key=f'{key_prefix}rst_{w["name"]}')
     if st.button('Apply contract dates',key=f'{key_prefix}capply_{w["name"]}',disabled=cal_locked):
      recompute_contract_counters(w); sync_company_payroll_stats(); st.rerun()
    with st.expander('Debut status controls',expanded=False):
     w['debut_status']=st.selectbox('Debut status',DEBUT_STATUSES,index=DEBUT_STATUSES.index(w.get('debut_status','Debuted')) if w.get('debut_status') in DEBUT_STATUSES else 1,key=f'{key_prefix}ds_{w["name"]}')
     w['debut_week']=st.number_input('Debut week',0,200,int(w['debut_week'] or 0),key=f'{key_prefix}dw_{w["name"]}') or None
     if w['debut_week']==0: w['debut_week']=None
     w['last_booked_week']=st.number_input('Last booked week',0,200,int(w['last_booked_week'] or 0),key=f'{key_prefix}lb_{w["name"]}') or None
     if w['last_booked_week']==0: w['last_booked_week']=None
     d1,d2,d3,d4=st.columns(4)
     ck=f'{key_prefix}debut_confirm_{w["name"]}'
     if cal_locked and not st.session_state.get(ck): st.caption('Calendar locked — use confirm checkbox before manual debut edits.')
     if cal_locked: st.checkbox('Confirm manual debut edit',key=ck)
     allow=not cal_locked or st.session_state.get(ck)
     if d1.button('Mark As Debuted',key=f'{key_prefix}mdb_{w["name"]}',disabled=not allow):
      mark_wrestler_debuted(w,comp,debut_type='Match Debut',week=w.get('debut_week') or st.session_state.week); st.rerun()
     if d2.button('Mark As Not Debuted',key=f'{key_prefix}mnd_{w["name"]}',disabled=not allow):
      set_wrestler_debut_status(w,'Not Debuted'); st.rerun()
     if d3.button('Set Returning Soon',key=f'{key_prefix}ret_{w["name"]}',disabled=not allow):
      set_wrestler_debut_status(w,'Returning Soon'); st.rerun()
     if d4.button('Set On Hiatus',key=f'{key_prefix}hi_{w["name"]}',disabled=not allow):
      set_wrestler_debut_status(w,'On Hiatus'); st.rerun()
    if st.button(f'Remove {w["name"]}',key=f'{key_prefix}rem_{w["name"]}'):
     st.session_state.roster=[x for x in st.session_state.roster if x['name']!=w['name']]; st.session_state.departed.append(w['name']); update_rank(); st.rerun()

def render_tag_team_card(team_w,comp):
 with bfg_card(team_w['name']):
  members=team_members_for(team_w,comp)
  ok=team_override_key(comp,team_w['name'])
  ov=st.session_state.tag_team_overrides.setdefault(ok,{})
  talign=calc_team_alignment(members,ov.get('alignment_manual'))
  tovr=calc_team_overall(team_w,members,ov)
  tsal=team_salary_total(team_w,comp)
  member_lines=''.join([f"<div class='member-line'>• <b>{m['name']}</b> | From: {m.get('from') or '—'} | OVR {m['overall']} | {align_badge_html(m.get('alignment','N'))} | Salary {money(m.get('salary',0))} | {m.get('status','Active')}</div>" for m in members])
  c1,c2=st.columns([.2,.8])
  with c1: show_img(team_w['name'],110)
  with c2:
   st.markdown(f"<div style='font-size:24px;font-weight:900;margin-bottom:8px'>{team_w['name']}</div>",unsafe_allow_html=True)
   st.markdown(f"<div style='font-size:16px;margin:6px 0'>Team Overall: <b>{tovr}</b></div>",unsafe_allow_html=True)
   st.markdown(f"<div class='small-text'>Company: <b>{team_w['company']}</b></div>",unsafe_allow_html=True)
   st.markdown(f"<div class='small-text'>Division: <b>{team_w.get('division','World Tag Team')}</b></div>",unsafe_allow_html=True)
   st.markdown(f"<div style='margin:8px 0'>Alignment: {align_badge_html(talign)}</div>",unsafe_allow_html=True)
   st.markdown(f"<div class='small-text'>Tag Record: <b>{tag_team_record(team_w)}</b> · Tag Streak: <b>{team_w.get('streak') or '—'}</b></div>",unsafe_allow_html=True)
   st.markdown(f"<div class='small-text'>Team Salary Total: <b>{money(tsal)}</b> (members + contract bonus)</div>",unsafe_allow_html=True)
   st.markdown('<div style="margin-top:12px;font-weight:800">Members:</div>',unsafe_allow_html=True)
   st.markdown(member_lines,unsafe_allow_html=True)
   with st.expander('Team actions',expanded=False):
    ac1,ac2,ac3=st.columns(3)
    if ac1.button('Break Up Team',key=f'break_{ok}'):
     break_up_team(team_w,comp); st.rerun()
    mem_names=[m['name'] for m in members]
    move_who=ac2.selectbox('Move to singles',mem_names,key=f'mv_{ok}') if mem_names else None
    if ac2.button('Move Member To Singles',key=f'mvbtn_{ok}',disabled=not move_who):
     move_member_to_singles(comp,team_w['name'],move_who); st.rerun()
    talign_act=ac3.selectbox('Turn team',['F','H','N'],key=f'ta_{ok}')
    if ac3.button('Apply Team Alignment',key=f'tab_{ok}'):
     set_team_alignment(comp,team_w['name'],talign_act); st.rerun()
    bc1,bc2,bc3=st.columns(3)
    rep_old=bc1.selectbox('Replace member',mem_names,key=f'ro_{ok}') if mem_names else None
    rep_new=clean_name_selector('New member',f'rn_{ok}',options=opts_individuals(comp),company=comp,entity_type='Wrestler',label_select='Select replacement',show_search=True)
    if bc1.button('Replace Team Member',key=f'rep_{ok}',disabled=not(rep_old and rep_new)):
     replace_tag_member(comp,team_w['name'],rep_old,rep_new); st.rerun()
    add_nm=clean_name_selector('Add member',f'addm_{ok}',options=opts_individuals(comp),company=comp,entity_type='Wrestler',label_select='Select wrestler',show_search=True)
    if bc2.button('Add Team Member',key=f'addmb_{ok}',disabled=not add_nm):
     add_tag_member(comp,team_w['name'],add_nm); st.rerun()
    rem_who=bc3.selectbox('Remove member',mem_names,key=f'rm_{ok}') if mem_names else None
    if bc3.button('Remove Team Member',key=f'rmb_{ok}',disabled=not rem_who):
     defs=[m for m in tag_team_member_defs(team_w['name']) if m['name']!=rem_who]
     save_tag_team_defs(team_w['name'],defs)
     move_member_to_singles(comp,team_w['name'],rem_who); st.rerun()
    ma1,ma2,ma3=st.columns(3)
    mal=ma1.selectbox('Member alignment',mem_names,key=f'maln_{ok}') if mem_names else None
    mal_code=ma2.selectbox('F/H/N',['F','H','N'],key=f'malc_{ok}')
    if ma2.button('Turn Member Alignment',key=f'malbtn_{ok}',disabled=not mal):
     set_member_alignment(mal,mal_code); st.rerun()
    st.caption('Breaking up keeps all members on the singles roster. AI/Twitter/rivalry effects apply automatically.')
   with st.expander('Team bonuses & manual overrides',expanded=False):
    ov['team_contract_bonus']=st.number_input('Team contract bonus',0,5000000,int(ov.get('team_contract_bonus',0)),step=50000,key=f'tbonus_{ok}')
    col1,col2=st.columns(2)
    use_manual=col1.checkbox('Override team overall',ov.get('overall_manual') is not None,key=f'tov_use_{ok}')
    if use_manual:
     ov['overall_manual']=col1.number_input('Team overall',50,100,int(ov.get('overall_manual') or calc_team_overall(team_w,members,{})),key=f'tov_{ok}')
    else: ov['overall_manual']=None
    aln_pick=col2.selectbox('Team alignment',['Auto','F','H','N'],index=['Auto','F','H','N'].index(ov.get('alignment_manual') if ov.get('alignment_manual') in ('F','H','N') else 'Auto'),key=f'tal_{ok}')
    ov['alignment_manual']=None if aln_pick=='Auto' else aln_pick
    b1,b2,b3,b4,b5=st.columns(5)
    if b1.button('+Chemistry',key=f'chem_{ok}'): ov['chemistry_bonus']=ov.get('chemistry_bonus',0)+2
    if b2.button('+History',key=f'hist_{ok}'): ov['history_bonus']=ov.get('history_bonus',0)+2
    if b3.button('+Win streak',key=f'wstr_{ok}'): ov['streak_bonus']=ov.get('streak_bonus',0)+1
    if b4.button('Low morale',key=f'mor_{ok}'): ov['morale_penalty']=ov.get('morale_penalty',0)+2
    if b5.button('Tension',key=f'ten_{ok}'): ov['tension_penalty']=ov.get('tension_penalty',0)+2
    if st.button('Reset bonuses',key=f'reset_{ok}'):
     for k in ['chemistry_bonus','history_bonus','streak_bonus','morale_penalty','tension_penalty']: ov[k]=0
     st.rerun()
    st.caption(f"Bonuses: chem +{ov.get('chemistry_bonus',0)} · history +{ov.get('history_bonus',0)} · streak +{ov.get('streak_bonus',0)} · morale -{ov.get('morale_penalty',0)} · tension -{ov.get('tension_penalty',0)}")

BELT_SLUG={
 ('NXT','NXT Crown Jewels Title'):'nxt_crown_jewels_title',('NXT','I.C Title'):'nxt_ic_title',('NXT','World Tag Team Champions'):'nxt_world_tag_team_champions',
 ('NXT',"Women's Title"):'nxt_womens_title',('NXT',"Women's N.A Title"):'nxt_womens_na_title',
 ('SmackDown','Undisputed WWE Championship'):'smackdown_undisputed_wwe_championship',('SmackDown','N.A Championship'):'smackdown_na_championship',
 ('SmackDown','World Tag Team Champions'):'smackdown_world_tag_team_championship',('SmackDown',"Women's World Championship"):'smackdown_womens_world_championship',
 ('SmackDown',"Women's U.S. Championship"):'smackdown_womens_us_championship',
 ('WCW','World Heavyweight Championship'):'wcw_world_heavyweight_championship',('WCW','United States Title'):'wcw_united_states_title',
 ('WCW','World Tag Team Champions'):'wcw_world_tag_team_championship',('WCW','WCW Television Title'):'wcw_television_title',('WCW','Cruiserweight Title'):'wcw_cruiserweight_title',
}
DEFAULT_TITLE_PRESTIGE={
 'NXT Crown Jewels Title':98,'I.C Title':88,'World Tag Team Champions':86,"Women's Title":90,"Women's N.A Title":82,
 'Undisputed WWE Championship':96,'N.A Championship':85,'World Tag Team Champions':84,"Women's World Championship":91,"Women's U.S. Championship":83,
 'World Heavyweight Championship':94,'United States Title':86,'WCW Television Title':80,'Cruiserweight Title':84,
}

def title_meta_key(comp,title): return f'{comp}::{title}'

def is_vacant_champion(name):
 return not name or name in ('Vacant','Place Holder','TBD - Tournament','TBD - Title Match')

def is_tag_title(title):
 return 'Tag Team' in title

def belt_file_slug(comp,title):
 return BELT_SLUG.get((comp,title),slug(title))

def ensure_champion_state():
 st.session_state.champions.setdefault('NXT',{}); st.session_state.champions.setdefault('SmackDown',{}); st.session_state.champions.setdefault('WCW',{})
 if 'title_prestige' not in st.session_state:
  st.session_state.title_prestige={}
  for comp in PLAYABLE:
   for t in COMPANIES[comp]['titles']:
    st.session_state.title_prestige[title_meta_key(comp,t)]=DEFAULT_TITLE_PRESTIGE.get(t,82)
 if 'champion_meta' not in st.session_state: st.session_state.champion_meta={}
 if 'champion_history' not in st.session_state: st.session_state.champion_history=[]
 if 'title_defense_history' not in st.session_state: st.session_state.title_defense_history=[]
 cj_prest_key=title_meta_key('NXT','NXT Crown Jewels Title')
 if st.session_state.title_prestige.get(cj_prest_key,98)<98:
  st.session_state.title_prestige[cj_prest_key]=98
 for comp in PLAYABLE:
  for t in COMPANIES[comp]['titles']:
   holder=st.session_state.champions.get(comp,{}).get(t,'Vacant')
   mk=title_meta_key(comp,t)
   meta=st.session_state.champion_meta.setdefault(mk,{'holder':'','reign_start_week':0,'defenses':0,'major_defenses':[],'last_defense_week':None,'last_defense_show':'','next_challenger':''})
   if not is_vacant_champion(holder) and meta.get('holder')!=holder:
    meta['holder']=holder; meta['reign_start_week']=st.session_state.week; meta['defenses']=0; meta['major_defenses']=[]

def get_title_prestige(comp,title):
 return int(st.session_state.title_prestige.get(title_meta_key(comp,title),DEFAULT_TITLE_PRESTIGE.get(title,82)))

def adjust_title_prestige(comp,title,delta):
 k=title_meta_key(comp,title)
 st.session_state.title_prestige[k]=max(50,min(100,int(st.session_state.title_prestige.get(k,82))+delta))

def get_champion_meta(comp,title):
 return st.session_state.champion_meta.setdefault(title_meta_key(comp,title),{'holder':'','reign_start_week':0,'defenses':0,'major_defenses':[],'last_defense_week':None,'last_defense_show':'','next_challenger':''})

def reign_weeks(meta):
 if not meta.get('reign_start_week'): return 0
 return max(0,st.session_state.week-int(meta['reign_start_week']))

def close_champion_reign(comp,title,holder,prestige):
 if is_vacant_champion(holder): return
 meta=get_champion_meta(comp,title)
 st.session_state.champion_history.append({'company':comp,'title':title,'champion':holder,'won_week':meta.get('reign_start_week',0),'lost_week':st.session_state.week,'reign_weeks':reign_weeks(meta),'defenses':meta.get('defenses',0),'major_defenses':list(meta.get('major_defenses',[])),'prestige_end':prestige})

def set_champion(comp,title,new_holder,old_holder):
 st.session_state.champions.setdefault(comp,{})
 new_holder='Vacant' if is_vacant_champion(new_holder) else new_holder
 old_holder=old_holder or st.session_state.champions[comp].get(title,'Vacant')
 if new_holder==old_holder: return False
 prest=get_title_prestige(comp,title)
 if not is_vacant_champion(old_holder):
  close_champion_reign(comp,title,old_holder,prest)
  if old_holder and find(old_holder):
   lw=find(old_holder)
   if lw.get('streak','').startswith('L'): adjust_title_prestige(comp,title,-2)
 adjust_title_prestige(comp,title,-3 if not is_vacant_champion(old_holder) and not is_vacant_champion(new_holder) else 0)
 st.session_state.champions[comp][title]=new_holder
 meta=get_champion_meta(comp,title)
 if is_vacant_champion(new_holder):
  meta.update({'holder':'','reign_start_week':0,'defenses':0,'major_defenses':[],'last_defense_week':None,'last_defense_show':''})
 else:
  meta.update({'holder':new_holder,'reign_start_week':st.session_state.week,'defenses':0,'major_defenses':[],'last_defense_week':None,'last_defense_show':''})
  w=find(new_holder)
  if w and w['overall']>=90: adjust_title_prestige(comp,title,3)
  elif w and w['overall']>=85: adjust_title_prestige(comp,title,1)
  st.session_state.champion_history.append({'company':comp,'title':title,'champion':new_holder,'won_week':st.session_state.week,'lost_week':None,'reign_weeks':0,'defenses':0,'major_defenses':[],'prestige_start':get_title_prestige(comp,title)})
  st.session_state.twitter_posts.insert(0,{'id':len(st.session_state.twitter_posts)+1,'week':st.session_state.week,'company':comp,'wrestler':new_holder,'role':'Wrestler','handle':'@'+slug(new_holder).replace('_',''),'post_type':'Champion Tweet','text':f"NEW CHAMPION: {new_holder} is now {title} champion on {comp}.",'likes':random.randint(3000,80000),'reposts':random.randint(300,15000),'replies':random.randint(100,5000),'views':random.randint(40000,900000),'mentions':title,'effects':{},'viral':True,'ai_generated':False})
  st.session_state.news_feed.insert(0,f"{new_holder} is now {comp} {title} champion.")
 update_rank({new_holder:f"Became {title} champion."} if not is_vacant_champion(new_holder) else {})
 return True

def record_title_defense(comp,title,holder,rating,show_name='',main_event=False):
 if is_vacant_champion(holder) or is_vacant_champion(st.session_state.champions.get(comp,{}).get(title)): return
 meta=get_champion_meta(comp,title)
 meta['defenses']=meta.get('defenses',0)+1
 meta['last_defense_week']=st.session_state.week
 meta['last_defense_show']=show_name or f'Week {st.session_state.week}'
 if rating>=8 or main_event:
  meta.setdefault('major_defenses',[]).append({'week':st.session_state.week,'rating':rating,'show':meta['last_defense_show']})
  adjust_title_prestige(comp,title,2 if rating>=9 else 1)
 else:
  adjust_title_prestige(comp,title,1 if rating>=7 else 0)
 w=find(holder)
 if w and w.get('streak','').startswith('W'): adjust_title_prestige(comp,title,1)
 st.session_state.title_defense_history.insert(0,{'week':st.session_state.week,'company':comp,'title':title,'champion':holder,'rating':rating,'show':show_name,'main_event':main_event})

def asset_path(kind,name):
 base={'wrestler':'assets/wrestlers','owner':'assets/owners','gm':'assets/gm','commentator':'assets/staff','podcast_host':'assets/podcast_hosts','logo':'assets/logos','banner':'assets/banners','belt':'assets/belts'}.get(kind,'assets/wrestlers')
 for e in ['.png','.jpg','.jpeg','.webp']:
  p=Path(base)/f'{slug(name)}{e}'
  if p.exists() and image_file_ok(p): return str(p)
 return ''

def show_img_slot(label,w=100,h=None):
 style=f"width:{w}px;"+(f"min-height:{h}px;" if h else "min-height:90px;")
 st.markdown(f"<div class='img-slot' style='{style}'>{label}</div>",unsafe_allow_html=True)

def show_belt_img(comp,title,w=130):
 p=asset_path('belt',belt_file_slug(comp,title))
 if p: safe_st_image(p,w,'Belt Image',100)
 else: show_img_slot('Belt Image',w,100)

def show_champion_img(name,w=110):
 p=img_path(name) or asset_path('wrestler',name)
 if p: safe_st_image(p,w,'Champion Image',105)
 else: show_img_slot('Champion Image',w,105)

def show_entity_img(name,kind='wrestler',w=80):
 lbl={'belt':'Belt Image','wrestler':'Champion Image','logo':'Logo','owner':'Owner','gm':'GM','banner':'Banner'}.get(kind,'IMG')
 if not name:
  show_img_slot(lbl,w,w-10 if w>50 else 70); return
 p=asset_path(kind,name) or (img_path(name) if kind=='wrestler' else '')
 if p: safe_st_image(p,w,lbl,w-10 if w>50 else 70)
 else: show_img_slot(lbl,w,w-10 if w>50 else 70)

def company_owner_photo_names(comp):
 """WCW uses two owners in STAFF — avoid combined 'A / B' string for file slugs."""
 owners=[s['name'] for s in STAFF.get(comp,[]) if (s.get('role') or '').lower()=='owner']
 if owners: return owners
 prof=st.session_state.company_profiles.get(comp,{})
 o=(prof.get('owner') or COMPANIES.get(comp,{}).get('owner') or '').strip()
 if not o: return []
 if ' / ' in o: return [x.strip() for x in o.split('/') if x.strip()]
 return [o]

def show_company_owner_imgs(comp,w=110):
 names=company_owner_photo_names(comp)
 if not names:
  show_img_slot('Owner Image',w,100); return
 if len(names)==1:
  show_entity_img(names[0],'owner',w); return
 cols=st.columns(min(len(names),3))
 for col,nm in zip(cols,names):
  with col:
   show_entity_img(nm,'owner',max(72,w-28))
   st.caption(nm.split()[0])

def picture_folder_map():
 return {'wrestler':'assets/wrestlers','owner':'assets/owners','gm':'assets/gm','commentator':'assets/staff','podcast host':'assets/podcast_hosts','logo':'assets/logos','banner':'assets/banners','championship belt':'assets/belts'}

def save_picture_asset(kind,pic_comp,target,f=None,url=''):
 folder_map=picture_folder_map()
 folder=folder_map.get(kind,'assets/wrestlers')
 Path(folder).mkdir(parents=True,exist_ok=True)
 if kind in ('logo','banner'): fname=slug(pic_comp)
 elif kind=='championship belt': fname=belt_file_slug(pic_comp,target)
 else: fname=slug(target or '')
 if not fname: return False,'Pick a person or title before saving.'
 if f:
  try:
   ext='.'+(f.name.split('.')[-1].lower() if getattr(f,'name',None) else 'png')
   if ext not in ('.png','.jpg','.jpeg','.webp'): return False,'Use png, jpg, jpeg, or webp.'
   raw=f.getvalue() if hasattr(f,'getvalue') else f.read()
   if not raw: return False,'Upload failed — pick the image file again and retry.'
   p=Path(folder)/f'{fname}{ext}'
   p.write_bytes(raw)
   if not image_file_ok(p):
    try: p.unlink(missing_ok=True)
    except OSError: pass
    return False,'Upload failed — file is not a valid image. Use png, jpg, jpeg, or webp.'
   return True,f'Image saved as {p.as_posix()}'
  except OSError as ex:
   return False,f'Could not write file: {ex}'
  except Exception as ex:
   return False,f'Upload error: {ex}'
 if url and url.strip():
  try:
   import urllib.request
   ext='.png' if '.png' in url.lower() else '.jpg'
   p=Path(folder)/f'{fname}{ext}'
   urllib.request.urlretrieve(url.strip(),p)
   return True,f'Image downloaded to {p.as_posix()}'
  except Exception as e:
   return False,str(e)
 return False,'Upload a file or provide a URL.'

def render_company_home_photo_panel(comp,can_edit):
 owner_choices=company_owner_photo_names(comp)
 with st.expander('Manage photos (logo & owners)',expanded=False):
  st.caption(f'**{comp}** — logo → `assets/logos/{slug(comp)}.png` · each owner portrait uses their own name below.')
  if comp=='WCW':
   st.info('WCW has **two owners** — upload **Stephanie McMahon** and **Shane McMahon** separately (not the combined owner line).')
  c1,c2=st.columns(2)
  with c1:
   st.markdown('**Logo preview**')
   show_entity_img(comp,'logo',100)
   logo_f=st.file_uploader('Upload logo',type=['png','jpg','jpeg','webp'],key=f'home_logo_up_{comp}')
  with c2:
   st.markdown('**Owner preview**')
   show_company_owner_imgs(comp,90)
   if not owner_choices:
    st.warning('No owner names found for this brand.')
    owner_pick=None
   else:
    owner_pick=st.selectbox('Owner to upload',owner_choices,key=f'home_owner_pick_{comp}')
   owner_f=st.file_uploader('Upload owner portrait',type=['png','jpg','jpeg','webp'],key=f'home_owner_up_{comp}')
  if not can_edit:
   st.caption('View only — you cannot upload photos for this brand.')
   return
  if st.button('Save home photos',key=f'home_pic_save_{comp}',type='primary'):
   msgs=[]; ok_any=False
   if logo_f:
    ok,msg=save_picture_asset('logo',comp,comp,f=logo_f)
    msgs.append(msg if ok else f'Logo: {msg}'); ok_any=ok_any or ok
   if owner_f:
    if not owner_pick or owner_pick=='Owner':
     msgs.append('Owner: pick Stephanie McMahon or Shane McMahon (WCW) before uploading.')
    else:
     ok,msg=save_picture_asset('owner',comp,owner_pick,f=owner_f)
     msgs.append(msg if ok else f'Owner: {msg}'); ok_any=ok_any or ok
   if not logo_f and not owner_f:
    st.warning('Choose a logo file and/or owner file first.')
   else:
    for m in msgs:
     if 'saved' in m.lower() or 'downloaded' in m.lower(): st.success(m)
     else: st.error(m)
    if ok_any: st.rerun()

def render_champion_card(comp,title):
 st.session_state.champions.setdefault(comp,{})
 cur=st.session_state.champions[comp].get(title,'Vacant')
 meta=get_champion_meta(comp,title)
 prest=get_title_prestige(comp,title)
 tk=title_meta_key(comp,title).replace(' ','_').replace("'",'')
 st.markdown('<div class="champion-card">',unsafe_allow_html=True)
 st.markdown(f'<div class="champ-title">{comp} — {display_title(title)}</div>',unsafe_allow_html=True)
 belt_col,hero_col=st.columns([.32,.68])
 with belt_col:
  show_belt_img(comp,title,140)
  st.markdown(f"<span class='champ-prestige-badge'>Title Prestige {prest}</span>",unsafe_allow_html=True)
 with hero_col:
  if is_vacant_champion(cur):
   show_img_slot('Champion Image',120,110)
   st.markdown("<div class='champ-name-large'>Vacant</div>",unsafe_allow_html=True)
   st.markdown(f"<div class='champ-meta-line'><b>{comp}</b> championship awaiting a new champion.</div>",unsafe_allow_html=True)
  elif is_tag_title(title) or is_tag_team_entry({'name':cur,'division':'World Tag Team'}):
   tw=find(cur)
   if tw: show_champion_img(cur,120)
   else: show_img_slot('Champion Image',120,110)
   members=team_members_for(tw,comp) if tw else team_members_for({'name':cur,'overall':85,'alignment':'N'},comp)
   tovr=calc_team_overall(tw,members,{}) if tw else '—'
   tal=calc_team_alignment(members)
   st.markdown(f"<div class='champ-name-large'>{cur}</div>",unsafe_allow_html=True)
   st.markdown(f"<div class='champ-stat-row'><span class='champ-ovr-badge'>Team OVR {tovr}</span>{align_badge_html(tal)}</div>",unsafe_allow_html=True)
   st.markdown(f"<div class='champ-meta-line'><b>{comp}</b> · Tag Team Champions · Record <b>{rec(tw) if tw else '—'}</b> · Streak <b>{tw.get('streak') if tw else '—'}</b></div>",unsafe_allow_html=True)
   if tw:
    st.markdown(stat_progress('Team Popularity',tw.get('popularity',70),'#e67e22'),unsafe_allow_html=True)
    st.markdown(stat_progress('Team Momentum',tw.get('momentum',55),'#3498db'),unsafe_allow_html=True)
    st.markdown(stat_progress('Team Morale',tw.get('morale',60),'#9b59b6'),unsafe_allow_html=True)
   st.markdown("<div class='champ-meta-line' style='margin-top:10px;font-weight:800'>Members</div>",unsafe_allow_html=True)
   for m in members:
    st.markdown(f"<div class='member-line'>• <b>{m['name']}</b> | From: {m.get('from') or m.get('hometown') or '—'} | OVR {m['overall']} | {align_badge_html(m.get('alignment','N'))}</div>",unsafe_allow_html=True)
  else:
   w=find(cur)
   if w: show_champion_img(cur,120)
   else: show_img_slot('Champion Image',120,110)
   disp=cur if not w else w['name']
   st.markdown(f"<div class='champ-name-large'>{disp}</div>",unsafe_allow_html=True)
   if w:
    st.markdown(f"<div class='champ-stat-row'><span class='champ-ovr-badge'>OVR {w['overall']}</span>{align_badge_html(w['alignment'])}</div>",unsafe_allow_html=True)
    ensure_contract_fields(); sync_wrestler_from(w)
    st.markdown(f"<div class='champ-meta-line'>From: <b>{w.get('from_location') or w.get('hometown') or 'Unknown'}</b></div>",unsafe_allow_html=True)
    st.markdown(f"<div class='champ-meta-line'><b>{w['company']}</b> · {w.get('division','')}</div>",unsafe_allow_html=True)
    st.markdown(f"<div class='champ-meta-line'>{contract_display_line(w)} · Contract status <b>{w.get('contract_status','Active')}</b></div>",unsafe_allow_html=True)
    st.markdown(f"<div class='champ-meta-line'>Record <b>{rec(w)}</b> · Streak <b>{w.get('streak') or '—'}</b></div>",unsafe_allow_html=True)
    st.markdown(stat_progress('Popularity',w['popularity'],'#e67e22'),unsafe_allow_html=True)
    st.markdown(stat_progress('Momentum',w['momentum'],'#3498db'),unsafe_allow_html=True)
    st.markdown(stat_progress('Morale',w['morale'],'#9b59b6'),unsafe_allow_html=True)
   else:
    st.caption('Champion not found in roster database.')
 if not is_vacant_champion(cur):
  rw=reign_weeks(meta)
  st.markdown(f"<div class='champ-reign-line'>Weeks as champion: <b>{rw}</b> · Successful defenses: <b>{meta.get('defenses',0)}</b> · Last title defense: <b>{meta.get('last_defense_show') or 'None yet'}</b></div>",unsafe_allow_html=True)
 with st.expander('Edit Champion',expanded=False):
  pool=champion_pick_pool(comp,title)
  cur_pick=cur if not is_vacant_champion(cur) else 'Vacant'
  sel=clean_name_selector('Select Champion',f'champ_sel_{tk}',options=pool,current=cur_pick,preserve_order=True,label_search='Search Champion',show_search=True)
  if st.button('Save Champion',key=f'champ_save_{tk}'):
   new_h='Vacant' if sel in ('Vacant','Place Holder') else sel
   if set_champion(comp,title,new_h,cur):
    st.toast(f'{new_h if new_h!="Vacant" else "Vacancy"} — {title} updated.')
    st.success(f'{sel} is now {comp} {title} champion.' if sel not in ('Vacant','Place Holder') else f'{title} is now vacant.')
   else: st.info('No change.')
   st.rerun()
 with st.expander('Champion History',expanded=False):
  hist=[h for h in st.session_state.champion_history if h.get('company')==comp and h.get('title')==title]
  if not hist: st.caption('No reign history recorded yet.')
  else:
   hp=5; hpages=max(1,(len(hist)+hp-1)//hp); hpg=st.number_input('History page',1,hpages,1,key=f'hist_pg_{tk}')
   for h in hist[(hpg-1)*hp:(hpg)*hp]:
    lost=f" → lost Week {h['lost_week']}" if h.get('lost_week') else ' (reigning)'
    st.markdown(f"<div class='small-text'><b>{h.get('champion')}</b> · won Week {h.get('won_week')}{lost} · {h.get('reign_weeks',0)} weeks · {h.get('defenses',0)} defenses · prestige {h.get('prestige_end',h.get('prestige_start','—'))}</div>",unsafe_allow_html=True)
  defs=[d for d in st.session_state.title_defense_history if d.get('company')==comp and d.get('title')==title]
  if defs:
   st.caption('Recent defenses')
   dp=4; dpages=max(1,(len(defs)+dp-1)//dp); dpg=st.number_input('Defense log page',1,dpages,1,key=f'def_pg_{tk}')
   for d in defs[(dpg-1)*dp:dpg*dp]:
    st.markdown(f"<div class='small-text'>Week {d['week']} — {d.get('champion')} — rating {d.get('rating')} — {d.get('show','')}</div>",unsafe_allow_html=True)

def staff_options(company):
 return [f"{s['name']} — {s['role']}" for s in st.session_state.staff.get(company,[])]

def get_staff(company,label):
 name=label.split(' — ')[0]
 return next((s for s in st.session_state.staff.get(company,[]) if s['name']==name),None)

def staff_tweet(staff,company,typ,city='',mention=''):
 style=staff.get('style','official')
 prompt=f"Write an under-280-character in-universe Twitter/X post. Person: {staff['name']}. Role: {staff['role']}. Company: {company}. Voice: {style}. Tweet type: {typ}. City/venue context: {city}. Mention/context: {mention}. Brand identity: {BRAND_THEMES[company]['lore']}. They can mention sports games, movies, shows, other company PLEs, sponsors, local city culture if it fits."
 out=ai(prompt)
 if out: return out.strip()
 if 'Live From City' in typ or 'City' in typ: return f"{city or 'This city'} feels alive tonight. {company} is bringing a show worthy of the moment."
 if 'Other Company' in typ or 'Rival Brand' in typ: return f"Respect to the other brands, but {company} is not interested in second place."
 if 'Sports' in typ or 'NBA' in typ or 'NFL' in typ or 'Draft' in typ: return f"Big-game energy all over {city or 'town'} tonight. {company} understands pressure, legacy, and championship moments."
 if 'Award' in typ or 'Oscars' in typ or 'Grammys' in typ: return f"Red carpets, bright lights, and brand power. {company} belongs in the conversation beyond the ring."
 return f"{company} has a message tonight: the brand, the roster, and the fans are moving in the same direction."

def activity_owner_brand(activity):
 return ACTIVITY_BRAND.get(activity,'NXT')

def check_exclusive_brand(comp,activity):
 owner=activity_owner_brand(activity)
 if owner==comp: return True,None
 return False,WRONG_BRAND_WARN.get((owner,comp),f'{activity} is {owner}-exclusive.')

def exclusive_activity_meta(activity,comp):
 owner=activity_owner_brand(activity)
 rev=appearance_revenue_for(comp,activity)
 lo,hi=int(rev*.85),int(rev*1.15)
 pop=(3,8) if 'Netflix' in activity or 'Grammy' in activity or 'NBA' in activity else (2,6)
 morale=(1,5); sponsor=(2,6); view=(2,7)
 risk='Low' if owner==comp else 'High'
 if 'Documentary' in activity or 'Podcast' in activity: pop=(2,5); morale=(2,6)
 if 'Draft' in activity: view=(5,12); sponsor=(4,9)
 if 'Halftime' in activity: view=(8,15); pop=(4,10)
 if 'Unfiltered' in activity: morale=(3,8); pop=(2,5); risk='Medium'
 best=[n for n in BRAND_EXCLUSIVE_BEST.get(owner,[]) if find(n) and find(n)['company']==comp][:6]
 if not best: best=[w['name'] for w in sorted(roster(comp),key=lambda x:-x['popularity'])[:5]]
 return {'name':activity,'owner':owner,'description':f'{owner} exclusive media crossover — builds brand identity and outside buzz.','best_for':best,'revenue_lo':lo,'revenue_hi':hi,'pop':pop,'morale':morale,'sponsor':sponsor,'viewership':view,'risk':risk,'partner':activity.split()[0]}

def recommend_brand_exclusives(comp,limit=3):
 ensure_extended_state()
 rec=[]; acts=APPEARANCE_LANES.get(comp,[])
 hot_riv=next((r for r in st.session_state.rivalries if r.get('company')==comp and int(r.get('heat',0))>=60),None)
 sched=get_scheduled_show(comp,next_bookable_week())
 city=(sched or {}).get('city','') or ''
 stadium='Stadium' in (sched or {}).get('show_type','')
 if comp=='NXT':
  if hot_riv and hot_riv.get('wrestlers'): rec.append({'activity':'Netflix Documentary Offer','reason':f"{hot_riv['name']} is hot — consider a Netflix documentary segment or NXT Unfiltered episode."})
  else: rec.append({'activity':'NXT Unfiltered','reason':'Strong NXT stories benefit from an NXT Unfiltered episode discussing morale, controversy, and PLE fallout.'})
  rec.append({'activity':'Oscars Red Carpet Invite','reason':'NXT Hollywood lane — red carpet prestige before your next major show.'})
 elif comp=='SmackDown':
  celebs=[w['name'] for w in roster(comp) if w['name'] in ('Logan Paul','Bad Bunny','KSI','Glorilla') and w['popularity']>=80]
  if celebs: rec.append({'activity':'Music Video Cameo Offer','reason':f"{', '.join(celebs[:2])} trending — Grammys or music video crossover fits SmackDown."})
  rec.append({'activity':'Grammy Winner Announcement','reason':'SmackDown music-awards lane — celebrity TV momentum.'})
  rec.append({'activity':'Paramount Plus Celebrity Segment','reason':'Paramount/USA/TNT celebrity TV fits the mainstream SmackDown brand.'})
 elif comp=='WCW':
  if stadium or 'Dallas' in city or 'Arlington' in city: rec.append({'activity':'NFL Halftime Show','reason':f'WCW is headed to {city or "a stadium market"} — NFL or ESPN crossover fits.'})
  for w in roster(comp):
   ht=w.get('from_location','')
   if ht and city and any(p in ht for p in city.split(',')[0].split()):
    rec.append({'activity':'NBA Appearance','reason':f"Hometown connection: {w['name']} ({ht}) near {city} — sports crossover."}); break
  rec.append({'activity':'ESPN SportsCenter Segment','reason':'WCW sports-network lane — SportsCenter builds league prestige.'})
  rec.append({'activity':'NBA Draft Pick Announcement','reason':'Draft announcement lane — Twitter and sponsor value.'})
 out=[]
 for r in rec:
  if r['activity'] in acts and r['activity'] not in [x['activity'] for x in out]: out.append(r)
 for a in acts:
  if len(out)>=limit: break
  if a not in [x['activity'] for x in out]: out.append({'activity':a,'reason':f'Core {comp} exclusive opportunity.'})
 return out[:limit]

def generate_exclusive_idea(comp,activity,person):
 meta=exclusive_activity_meta(activity,comp)
 w=find(person)
 prompt=f"""Bound For Glory — {comp} exclusive activity idea.
Activity: {activity} ({meta['owner']} exclusive)
Talent: {person} ({fmt_display(w.get('from_location') if w else None,'Unknown')})
Week {st.session_state.week}. Why it fits {comp} brand: {BRAND_THEMES[comp]['lore'][:200]}
Explain: wrestler fit, story help, popularity/morale/momentum, money, attendance/viewership, risks. Under 200 words."""
 return ai(prompt) or f"{person} on {activity}: fits {comp}'s {meta['owner']} lane — builds buzz, {money(meta['revenue_lo'])}-{money(meta['revenue_hi'])} range, {meta['risk']} risk."

def apply_exclusive_violation(comp,activity,person):
 w=find(person)
 if w: apply_wrestler_deltas(w,controversy=(4,9),morale=(-3,0),sponsor=(-4,-1))
 st.session_state.setdefault('exclusive_violations',[]).insert(0,{'week':st.session_state.week,'company':comp,'activity':activity,'owner':activity_owner_brand(activity),'person':person})
 st.session_state.setdefault('storyline_flags',[]).insert(0,{'week':st.session_state.week,'flag':'Cross-brand exclusive violation','target':person,'company':comp,'notes':f'Forced {activity} on wrong brand'})
 owner=activity_owner_brand(activity)
 if owner!=comp and owner in PLAYABLE and w:
  make_twitter_post(owner,'wrestler',w['name'],'@'+slug(w['name']).replace('_',''),'Wrestler','Rival Brand Shade',f"If they don't appreciate you over there, there's always room on our side. — {w['name']}",comp,{'ai_generated':True,'topic':'Cross-Brand','effects':{'controversy':(3,6)}})
  prof=st.session_state.company_profiles.get(comp,{})
  staf=next((s for s in st.session_state.staff.get(comp,[]) if 'Owner' in s.get('role','') or 'GM' in s.get('role','')),None)
  if staf: make_twitter_post(comp,'staff',staf['name'],staf['handle'],staf['role'],'Brand Statement',f"We handle our business professionally. {person}'s outside appearance is being reviewed.",person,{'ai_generated':True,'topic':'Cross-Brand'})

def run_brand_exclusive(comp,activity,person,week,notes='',force=False):
 ok,msg=check_exclusive_brand(comp,activity)
 if not ok and not force: return False,msg
 meta=exclusive_activity_meta(activity,comp)
 w=find(person)
 eff=appearance_effect(comp,person,activity)
 if not ok and force:
  apply_exclusive_violation(comp,activity,person)
  eff['risk']='High'; eff['revenue']=int(eff['revenue']*.75)
 if w:
  apply_wrestler_deltas(w,pop=meta['pop'],morale=meta['morale'],sponsor=meta['sponsor'])
  w['twitter_buzz']=min(100,w.get('twitter_buzz',0)+random.randint(*meta['viewership']))
  if 'Unfiltered' in activity:
   w['morale']=clamp_stat(w['morale']+random.randint(2,6)); w['momentum']=clamp_stat(w['momentum']+random.randint(1,4))
 rev=int(eff['revenue'])
 add_transaction(comp,'Exclusive Appearance',f"{person} — {activity}",rev,int(week))
 finance_flash(comp,rev,f"exclusive: {activity}")
 rec=normalize_appearance_record({'week':int(week),'company':comp,'person':person or '—','activity':activity,'appearance':activity,'notes':notes or '','effects':eff,'revenue':rev,'exclusive':True,'owner_brand':meta['owner'],'forced':force and not ok,'controversy_risk':eff.get('risk','Low'),'risk_level':eff.get('risk','Low')})
 st.session_state.appearance_history.insert(0,rec)
 st.session_state.setdefault('exclusive_activity_history',[]).insert(0,rec)
 st.session_state.news_feed.insert(0,f"{comp} exclusive: {person} — {activity} — {money(rev)}")
 if w and random.random()<.45: make_twitter_post(comp,'wrestler',person,'@'+slug(person).replace('_',''),'Wrestler','Exclusive Media Tweet',f"Outside the ring, the spotlight still matters. — {person}",'',{'ai_generated':True,'topic':'Media','effects':{'buzz':(3,7)}})
 return True,'Exclusive activity completed.'

def save_exclusive_to_calendar(comp,activity,person,notes=''):
 sched=get_scheduled_show(comp,next_bookable_week()) or {}
 wk=next_bookable_week()
 entry={'week':wk,'company':comp,'show_name':sched.get('show_name',f'{comp} Week {wk}'),'notes':f"EXCLUSIVE: {person} — {activity}. {notes}",'exclusive_activity':activity,'exclusive_talent':person}
 st.session_state.schedule_calendar=[e for e in st.session_state.schedule_calendar if not (int(e.get('week',-1))==wk and e.get('company')==comp and 'EXCLUSIVE' in (e.get('notes') or ''))]
 base=normalize_schedule_entry(dict(sched)) if sched else {'week':wk,'company':comp,'show_name':f'{comp} Week {wk}','show_type':'Weekly Show','status':'Planned','notes':entry['notes']}
 if sched: base=dict(sched); base['notes']=(base.get('notes','')+' | '+entry['notes']).strip(' |')
 else: base=entry
 st.session_state.schedule_calendar.append(normalize_schedule_entry(base))
 st.session_state.setdefault('calendar_ai_notes',[]).insert(0,f"Week {wk} {comp}: plan exclusive — {activity} for {person}.")

def render_brand_exclusives_section(comp,key_prefix,compact=False,show_suggestions=True):
 ensure_extended_state()
 section_header('Brand Exclusives' if compact else 'Exclusive Brand Opportunities', comp)
 st.caption(f'**{comp}** exclusive lanes — toggling NXT / SmackDown / WCW updates this section automatically.')
 if show_suggestions:
  recs=recommend_brand_exclusives(comp,3 if compact else 4)
  if recs:
   with bfg_card('Smart Suggestions'):
    for r in recs: st.write(f"• **{r['activity']}** — {r['reason']}")
 lanes=BRAND_EXCLUSIVE_LANES.get(comp,[])
 if compact:
  for r in recommend_brand_exclusives(comp,3):
   meta=exclusive_activity_meta(r['activity'],comp)
   st.markdown(f"<div class='gm-card'><b>{r['activity']}</b> · Exclusive to {meta['owner']}<br><span class='small-text'>{r['reason']}</span><br>Revenue {money(meta['revenue_lo'])}–{money(meta['revenue_hi'])} · Risk {meta['risk']}</div>",unsafe_allow_html=True)
  st.caption('Open **Appearances** or **Company Home** for full exclusive cards and actions.')
  return
 for lane in lanes:
  with st.expander(lane['lane'],expanded=False):
   for act in lane['activities']:
    meta=exclusive_activity_meta(act,comp)
    ok_brand,warn=check_exclusive_brand(comp,act)
    st.markdown(f"<div class='gm-card'><b>{act}</b><br><span class='small-text'>Exclusive to: <b>{meta['owner']}</b> · {meta['description']}</span><br>Best for: {', '.join(meta['best_for'][:5])}<br>Revenue: {money(meta['revenue_lo'])} – {money(meta['revenue_hi'])} · Pop +{meta['pop'][0]}-{meta['pop'][1]} · Morale +{meta['morale'][0]}-{meta['morale'][1]} · Sponsor +{meta['sponsor'][0]}-{meta['sponsor'][1]} · Viewership +{meta['viewership'][0]}-{meta['viewership'][1]} · Risk: <b>{meta['risk']}</b></div>",unsafe_allow_html=True)
    if not ok_brand: st.warning(warn)
    act_key=slug(act) or 'activity'
    person=clean_name_selector('Talent',f'{key_prefix}_{comp}_{act_key}_p',company=comp,entity_type='Wrestler',default_company=comp,label_select='Wrestler',show_search=True)
    wk=st.number_input('Week',1,52,st.session_state.week+1,key=f'{key_prefix}_{comp}_{act_key}_wk')
    notes=st.text_input('Story notes',key=f'{key_prefix}_{comp}_{act_key}_n',value='')
    force=False
    if not ok_brand:
     force=st.checkbox('Force cross-brand (confirm)',key=f'{key_prefix}_{comp}_{act_key}_force')
    b1,b2,b3=st.columns(3)
    if b1.button('Generate Idea',key=f'{key_prefix}_{comp}_{act_key}_idea'):
     idea=generate_exclusive_idea(comp,act,person)
     st.session_state.setdefault('exclusive_generated_ideas',[]).insert(0,{'week':st.session_state.week,'company':comp,'activity':act,'person':person,'idea':idea})
     st.info(idea)
    if b2.button('Run Appearance',key=f'{key_prefix}_{comp}_{act_key}_run'):
     success,msg=run_brand_exclusive(comp,act,person,wk,notes,force)
     if success: st.success(msg); st.rerun()
     else: st.error(msg)
    if b3.button('Save To Calendar',key=f'{key_prefix}_{comp}_{act_key}_cal'):
     save_exclusive_to_calendar(comp,act,person,notes); st.success('Saved to calendar notes.'); st.rerun()
    if act=='NXT Unfiltered' and comp=='NXT' and st.button('Open NXT Unfiltered Studio',key=f'{key_prefix}_{comp}_nxt_uf_studio'):
     d=st.session_state.setdefault('nxt_unfiltered_draft',{})
     d.update({'related_show':notes,'main_characters':person,'week':st.session_state.week+1})
     st.session_state.nav_page='NXT Unfiltered'; st.rerun()

MUSIC_EVENT_DETAILS={
 'Grammys Appearance':{'performer':'Featured star','category':'Best Crossover Moment','winner':'TBD','song':'Brand anthem clip'},
 'Grammy Winner Announcement':{'performer':'GM / star duo','category':'Album of the Year (presenter)','winner':'Guest artist','song':'—'},
 'Grammys Red Carpet Invite':{'performer':'Champion or celebrity','category':'Red Carpet','winner':'—','song':'Walk-in theme'},
 'Grammy Presenter Offer':{'performer':'Top SmackDown face/heel','category':'Presenter slot','winner':'—','song':'—'},
 'BET Awards Appearance':{'performer':'Culture star','category':'Best Hip-Hop Crossover','winner':'TBD','song':'Featured single'},
 'MTV VMA Segment':{'performer':'Trending wrestler','category':'VMA Moment','winner':'—','song':'Music video cameo track'},
 'Billboard Music Awards Invite':{'performer':'Mainstream crossover','category':'Top Collab','winner':'TBD','song':'Charting feature'},
 'Music Video Cameo Offer':{'performer':'Star talent','category':'Video cameo','winner':'Director pick','song':'Lead single'},
 'Concert Appearance':{'performer':'Live guest','category':'Surprise guest','winner':'—','song':'Encore appearance'},
 'Album Release Party Invite':{'performer':'Celebrity ally','category':'Release party','winner':'—','song':'Album launch track'},
 'Red Carpet Music Event':{'performer':'Fashion-forward star','category':'Red carpet','winner':'—','song':'—'},
}

def _brand_appearance_history(comp):
 return [normalize_appearance_record(a) for a in st.session_state.get('appearance_history',[]) if a.get('company')==comp]

def smackdown_culture_scores(comp='SmackDown'):
 ensure_extended_state()
 hist=_brand_appearance_history(comp)
 music_kw=('Grammy','Music','Concert','VMA','BET','Billboard','Album','Red Carpet','Paramount','Celebrity Music')
 music_apps=[a for a in hist if any(k in (a.get('appearance') or '') for k in music_kw)]
 celeb_pool=[w for w in roster(comp) if w['popularity']>=80]
 buzz=min(100,38+len(music_apps)*5+len(celeb_pool)*2+sum(int(a.get('revenue',0)) for a in music_apps)//800000)
 culture=min(100,32+len(music_apps)*6+int(st.session_state.company_profiles.get(comp,{}).get('prestige',85)*.15))
 return {'celebrity_buzz':buzz,'culture_score':culture,'music_crossovers':len(music_apps),'celeb_roster':len(celeb_pool)}

def wcw_sports_scores(comp='WCW'):
 ensure_extended_state()
 hist=_brand_appearance_history(comp)
 sport_kw=('NBA','NFL','ESPN','CBS','Draft','Halftime','Sports','Super Bowl','College Football','Amazon Prime')
 sport_apps=[a for a in hist if any(k in (a.get('appearance') or '') for k in sport_kw)]
 stadium_shows=len([e for e in st.session_state.get('schedule_calendar',[]) if e.get('company')==comp and 'Stadium' in (e.get('show_type') or '')])
 hometown_links=0
 sched=get_scheduled_show(comp,next_bookable_week()) or {}
 city=(sched.get('city') or '')
 for w in roster(comp):
  ht=w.get('from_location') or ''
  if ht and city and any(p in ht for p in city.split(',')[0].split()): hometown_links+=1
 legitimacy=min(100,42+len(sport_apps)*5+stadium_shows*3+hometown_links*4)
 stadium_cred=min(100,35+stadium_shows*8+len([e for e in st.session_state.get('schedule_calendar',[]) if e.get('company')==comp and int(e.get('capacity',0))>=40000])*2)
 prestige=min(100,40+len([v for v in st.session_state.champions.get(comp,{}).values() if v and v not in ('Vacant','Place Holder')])*8+len(sport_apps)*3)
 return {'sports_legitimacy':legitimacy,'stadium_credibility':stadium_cred,'championship_sports_prestige':prestige,'sports_crossovers':len(sport_apps),'hometown_links':hometown_links}

def render_smackdown_culture_pulse_page():
 comp='SmackDown'
 set_active_brand(comp)
 inject_brand_theme(comp)
 render_brand_badge(comp)
 section_header('SmackDown Culture Pulse', comp)
 st.markdown(f'<div class="brand-hub-banner"><h3>SmackDown Culture Pulse</h3><span class="small-text">Grammys · BET · VMAs · Billboard · music videos · concerts · celebrity TV · red carpet — black / blue / red UI.</span></div>',unsafe_allow_html=True)
 render_brand_permission_banner(comp)
 render_money_meter(comp,compact=False,show_ticker=True,show_sponsor=True)
 sc=smackdown_culture_scores(comp)
 render_kpi_row([('Celebrity Buzz',f"{sc['celebrity_buzz']}/100",'Twitter + crossover momentum'),('Culture Score',f"{sc['culture_score']}/100",'Music & TV brand heat'),('Music Crossovers',sc['music_crossovers'],'Logged appearances'),('Star Roster (80+ Pop)',sc['celeb_roster'],'Mainstream-ready talent')])
 with bfg_card('Award & music event details'):
  for act,details in list(MUSIC_EVENT_DETAILS.items())[:8]:
   with st.expander(act,expanded=False):
    st.write(f"**Performer:** {details['performer']} · **Category:** {details['category']} · **Winner:** {details['winner']} · **Song/segment:** {details['song']}")
    meta=exclusive_activity_meta(act,comp)
    st.caption(f"Revenue {money(meta['revenue_lo'])}–{money(meta['revenue_hi'])} · Risk {meta['risk']} · Best for: {', '.join(meta['best_for'][:4])}")
 render_brand_exclusives_section(comp,'sdp_culture',compact=False)

def render_wcw_sports_desk_page():
 comp='WCW'
 set_active_brand(comp)
 inject_brand_theme(comp)
 render_brand_badge(comp)
 section_header('WCW Sports Desk', comp)
 st.markdown(f'<div class="brand-hub-banner"><h3>WCW Sports Desk</h3><span class="small-text">NBA · NFL · ESPN · CBS SportsCenter · halftime · draft announcements · hometown connections — black / red / gold / steel.</span></div>',unsafe_allow_html=True)
 render_brand_permission_banner(comp)
 render_money_meter(comp,compact=False,show_ticker=True,show_sponsor=True)
 sc=wcw_sports_scores(comp)
 render_kpi_row([('Sports Legitimacy',f"{sc['sports_legitimacy']}/100",'ESPN/CBS crossover weight'),('Stadium Credibility',f"{sc['stadium_credibility']}/100",'Large venues & stadium cards'),('Championship Sports Prestige',f"{sc['championship_sports_prestige']}/100",'Title + sports synergy'),('Sports Crossovers',sc['sports_crossovers'],'Logged this season')])
 sched=get_scheduled_show(comp,next_bookable_week()) or {}
 with bfg_card('Desk board'):
  st.write(f"**Next show:** {sched.get('show_name','TBD')} · **{sched.get('city','TBD')}** · {sched.get('show_type','Weekly')}")
  if sc['hometown_links']: st.success(f"Hometown sports connection available near **{sched.get('city','')}** — consider NBA/NFL appearance.")
  teams_hint=[]
  if 'Dallas' in (sched.get('city') or '') or 'Arlington' in (sched.get('city') or ''): teams_hint.append('Cowboys / Mavericks market')
  if 'Miami' in (sched.get('city') or ''): teams_hint.append('Heat / Dolphins market')
  if 'Los Angeles' in (sched.get('city') or ''): teams_hint.append('Lakers / Rams market')
  if teams_hint: st.caption('**Teams playing / market angle:** '+', '.join(teams_hint))
  else: st.caption('**Teams playing:** set city in Schedule Calendar — desk suggests NBA/NFL/ESPN angles from market.')
 with bfg_card('Sports crossover history'):
  hist=[a for a in _brand_appearance_history(comp) if any(k in (a.get('appearance') or '') for k in ('NBA','NFL','ESPN','CBS','Draft','Halftime'))][:8]
  if hist:
   for a in hist: st.write(f"• Week {a.get('week')} — {a.get('person')} — {a.get('appearance')} — {money(a.get('revenue',0))}")
  else: st.caption('No sports desk appearances logged yet — run exclusives below.')
 render_brand_exclusives_section(comp,'wcw_desk',compact=False)

NXT_SPOTLIGHT_HOLLYWOOD_KW=('Netflix','Hollywood','Oscars','SNL','Good Morning','GMA','Academy','Red Carpet','Movie','Trailer','Documentary','Press','Olympic','Comic-Con','Unfiltered','Marvel','DC','Mattel','Barbie','Toy','Comic')
NXT_SPOTLIGHT_MERCH_KW=('Mattel','Barbie','DC','Toy','Comic','Merch','Action')

def _nxt_spotlight_appearances(comp='NXT'):
 hist=_brand_appearance_history(comp)
 cameo=[c for c in st.session_state.get('cameo_library',[]) if c.get('company')==comp]
 return hist,cameo

def nxt_spotlight_scores(comp='NXT'):
 ensure_extended_state(); ensure_finance_state()
 hist,cameo=_nxt_spotlight_appearances(comp)
 hollywood=[a for a in hist+cameo if any(k in (a.get('appearance') or a.get('project_type') or a.get('partner') or '') for k in NXT_SPOTLIGHT_HOLLYWOOD_KW)]
 merch=[a for a in hist+cameo if any(k in (a.get('appearance') or a.get('project_type') or a.get('partner') or '') for k in NXT_SPOTLIGHT_MERCH_KW)]
 fin=st.session_state.company_finance.get(comp,{})
 prof=st.session_state.company_profiles.get(comp,{})
 viol=len([v for v in st.session_state.get('exclusive_violations',[]) if v.get('company')==comp])
 nxt_shows=[h for h in st.session_state.get('weekly_history',[]) if h.get('company')==comp][-6:]
 grade_pts=[]
 for h in nxt_shows:
  perf=h.get('performance') or {}
  g=perf.get('grades') or h.get('grade_breakdown') or {}
  if g:
   grade_pts.append((float(g.get('story_continuity',6))+float(g.get('emotion_fan',6)))/2)
  elif h.get('episode_rating') or h.get('final_rating'):
   try: grade_pts.append(float(h.get('episode_rating',h.get('final_rating',6))))
   except (TypeError,ValueError): pass
 cinematic=sum(grade_pts)/len(grade_pts) if grade_pts else 6.0
 uf_boost=min(12,len(st.session_state.get('nxt_unfiltered_episodes',[]))*2)
 if st.session_state.get('last_nxt_unfiltered'): uf_boost+=3
 cinematic_score=min(100,max(0,int(28+cinematic*7+uf_boost)))
 rev_sum=sum(int(a.get('revenue',0)) for a in hollywood)
 hollywood_score=min(100,max(0,int(32+len(hollywood)*6+rev_sum//900000+int(prof.get('prestige',88))*.18-viol*6)))
 buzz_pool=[w for w in roster(comp) if w.get('twitter_buzz',0)>=40]
 buzz_avg=sum(w.get('twitter_buzz',0) for w in roster(comp))/max(1,len(roster(comp)))
 media_rev=int(fin.get('media_revenue_total',0))+int(fin.get('appearance_revenue_total',0))
 buzz_score=min(100,max(0,int(30+len(hollywood)*4+buzz_avg*.35+media_rev//1200000)))
 hot=[w for w in roster(comp) if w['popularity']>=85 and w['momentum']>=70]
 merch_rev=int(fin.get('merch_revenue_total',0))
 merch_score=min(100,max(0,int(26+len(merch)*7+len(hot)*6+merch_rev//1000000)))
 crossovers=len(hollywood)
 return {
  'hollywood_prestige':hollywood_score,'cinematic_story_power':cinematic_score,'mainstream_media_buzz':buzz_score,
  'merch_toy_power':merch_score,'spotlight_crossovers':crossovers,
  'media_revenue':media_rev,'merch_revenue':merch_rev,'violations':viol,
 }

def nxt_spotlight_ai_recommendations(sc):
 lines=[]
 def add(person,activity,reason):
  w=find(person); meta=exclusive_activity_meta(activity,'NXT') if activity else None
  lines.append({'person':person,'activity':activity,'reason':reason,'w':w,'meta':meta})
 presets=[
  ('Christian Rose','Netflix Show Cameo',"Christian Rose is perfect for a Netflix villain cameo because his current story is built around fame, ego, and control."),
  ('Lani Rose','Good Morning America Feature',"Lani Rose should be used for a Good Morning America or Olympics-style feature because her story has emotional and inspirational value."),
  ('Raven','DC Movie Cameo Offer',"Raven fits a dark DC-style teaser or horror-thriller cameo because his character is cryptic and psychological."),
  ('CM Punk','Netflix Documentary Offer',"CM Punk should be used in a Netflix documentary segment because his story feels real, emotional, and anti-corporate."),
  ('Jade Cargill','Mattel Toy Campaign',"Jade Cargill can drive Mattel/Barbie/DC merchandise if her popularity is high."),
  ('Bianca Belair','Mattel Toy Campaign',"Bianca Belair can drive Mattel/Barbie/DC merchandise when popularity and momentum are hot."),
  ('Roman Reigns','Hollywood Movie Role',"Roman Reigns fits blockbuster Hollywood or Netflix prestige when the title picture needs global reach."),
  ('Seth Rollins','Oscars Red Carpet Invite',"Seth Rollins fits Oscars red carpet and fashion-forward Hollywood press when you want flash over warmth."),
 ]
 for person,activity,reason in presets:
  w=find(person)
  if w and w.get('company')=='NXT':
   if activity=='Mattel Toy Campaign' and not (w['popularity']>=85 and w['momentum']>=70): continue
   add(person,activity,reason)
 for r in recommend_brand_exclusives('NXT',4):
  act=r['activity']; meta=exclusive_activity_meta(act,'NXT'); person=meta['best_for'][0] if meta.get('best_for') else 'Top NXT star'
  lines.append({'person':person,'activity':act,'reason':r['reason'],'w':find(person),'meta':meta})
 seen=set(); out=[]
 for x in lines:
  k=(x.get('person'),x.get('activity'))
  if k in seen: continue
  seen.add(k); out.append(x)
 return out[:8]

def build_nxt_spotlight_board(sc):
 board=[]
 rec_map={
  'Netflix Show Cameo':'recommended Netflix cameo',
  'Hollywood Press Tour':'recommended Hollywood press moment',
  'SNL Sketch Invitation':'recommended SNL appearance',
  'Good Morning America Feature':'recommended GMA interview',
  'Oscars Red Carpet Invite':'recommended Oscars red carpet',
  'Olympic Games Media Appearance':'recommended Olympics appearance',
  'Mattel Toy Campaign':'recommended Mattel/Barbie/DC merch opportunity',
  'DC Comic Cover Reveal':'recommended Mattel/Barbie/DC merch opportunity',
  'Barbie Crossover Campaign':'recommended Mattel/Barbie/DC merch opportunity',
 }
 for item in nxt_spotlight_ai_recommendations(sc)[:5]:
  act=item.get('activity') or 'Hollywood Press Tour'
  meta=item.get('meta') or exclusive_activity_meta(act,'NXT')
  person=item.get('person') or (meta['best_for'][0] if meta.get('best_for') else '—')
  w=item.get('w') or find(person)
  pop_hi=meta['pop'][1] if isinstance(meta.get('pop'),tuple) else 6
  board.append({
   'label':rec_map.get(act,'Spotlight opportunity'),
   'activity':act,'person':person,'revenue_lo':meta['revenue_lo'],'revenue_hi':meta['revenue_hi'],
   'pop_boost':f"+{meta['pop'][0]}-{pop_hi}",'sponsor':f"+{meta['sponsor'][0]}-{meta['sponsor'][1]}",
   'risk':meta.get('risk','Low'),'reason':item.get('reason',''),
   'fit':w['name'] if w else person,
  })
 return board

def render_nxt_spotlight_kpis(sc):
 r1,r2=st.columns([3,2])
 with r1:
  render_kpi_row([
   ('Hollywood Prestige',f"{sc['hollywood_prestige']}/100",'Netflix, Oscars, SNL, GMA, movie/TV crossover'),
   ('Cinematic Story Power',f"{sc['cinematic_story_power']}/100",'Premium drama · PLE · NXT Unfiltered reads'),
   ('Mainstream Media Buzz',f"{sc['mainstream_media_buzz']}/100",'Press, red carpet, viral media attention'),
  ])
 with r2:
  render_kpi_row([
   ('Merch / Toy Power',f"{sc['merch_toy_power']}/100",'Mattel, Barbie, DC, comics, action figures'),
   ('Spotlight Crossovers',sc['spotlight_crossovers'],'Logged this season'),
  ])

def last_show_quality_caption(comp):
 lh=next((h for h in reversed(st.session_state.get('weekly_history',[])) if h.get('company')==comp),None)
 if not lh: return None
 sq=(lh.get('logistics') or {}).get('show_quality',{})
 if sq.get('show_descriptor'):
  return f"Last show ({sq.get('sellout_status','gate')}): {sq['show_descriptor'][:95]}"
 return None

def render_nxt_spotlight_studio(comp='NXT',compact=False,key_prefix='nxt_sp'):
 if comp!='NXT': return
 ensure_extended_state(); ensure_finance_state()
 sc=nxt_spotlight_scores(comp)
 st.markdown(
  '<div class="brand-hub-banner"><h3>NXT Spotlight Studio</h3>'
  '<span class="small-text">Hollywood · Netflix · Marvel/DC-style · Oscars · SNL · GMA · Olympics · Comic-Con · cameo scripts · merch — separate from <b>NXT Unfiltered</b> podcast.</span></div>',
  unsafe_allow_html=True,
 )
 render_nxt_spotlight_kpis(sc)
 fin=st.session_state.company_finance.get('NXT',{})
 st.caption(f"**Money tie-in:** Media/appearance {money(sc['media_revenue'])} · Merch {money(sc['merch_revenue'])} · Bank {money(fin.get('current_budget',0))}")
 lsq=last_show_quality_caption(comp)
 if lsq: st.caption(lsq)
 with bfg_card('Spotlight Board'):
  for row in build_nxt_spotlight_board(sc):
   st.markdown(
    f"<div class='gm-card'><b>{html_escape(row['label'])}</b> — <b>{html_escape(row['activity'])}</b><br>"
    f"<span class='small-text'>Best fit: <b>{html_escape(row['fit'])}</b> · Revenue {money(row['revenue_lo'])}–{money(row['revenue_hi'])} · "
    f"Pop {row['pop_boost']} · Sponsor {row['sponsor']} · Risk <b>{html_escape(row['risk'])}</b></span><br>"
    f"<span style='color:#ddd;margin-top:6px;display:block'>{html_escape(row['reason'])}</span></div>",
    unsafe_allow_html=True,
   )
 with bfg_card('AI Recommendations'):
  for item in nxt_spotlight_ai_recommendations(sc):
   st.write(f"• **{item['person']}** — {item['reason']}")
 hist,cameo=_nxt_spotlight_appearances(comp)
 recent=(hist[:5]+[{'week':c.get('week'),'person':c.get('person'),'appearance':c.get('title'),'revenue':c.get('revenue')} for c in cameo[:3]])
 if recent:
  with st.expander('Recent spotlight crossovers',expanded=not compact):
   for a in recent[:8]:
    st.write(f"• Week {a.get('week')} — {fmt_display(a.get('person'))} — {fmt_display(a.get('appearance'))} — {money(a.get('revenue',0))}")
 if compact:
  if st.button('Open NXT Spotlight Studio',key=f'{key_prefix}_open_full'):
   st.session_state.nav_page='NXT Spotlight Studio'; set_active_brand('NXT'); st.rerun()
 else:
  render_brand_exclusives_section(comp,f'{key_prefix}_ex',compact=False)

def render_nxt_spotlight_studio_page():
 set_active_brand('NXT')
 inject_brand_theme('NXT')
 render_brand_badge('NXT')
 section_header('NXT Spotlight Studio','NXT')
 render_brand_permission_banner('NXT')
 render_money_meter('NXT',compact=False,show_ticker=True,show_sponsor=True)
 render_nxt_spotlight_studio('NXT',compact=False,key_prefix='nxt_sp_page')

def render_smackdown_culture_pulse_embed(comp='SmackDown',compact=True,key_prefix='sd_hub'):
 if comp!='SmackDown': return
 sc=smackdown_culture_scores(comp)
 st.markdown('<div class="brand-hub-banner"><h3>SmackDown Culture Pulse</h3><span class="small-text">Grammys · music TV · celebrity culture</span></div>',unsafe_allow_html=True)
 render_kpi_row([('Celebrity Buzz',f"{sc['celebrity_buzz']}/100",''),('Culture Score',f"{sc['culture_score']}/100",''),('Music Crossovers',sc['music_crossovers'],'')])
 lsq=last_show_quality_caption(comp)
 if lsq: st.caption(lsq)
 if compact and st.button('Open SmackDown Culture Pulse',key=f'{key_prefix}_open'): st.session_state.nav_page='SmackDown Culture Pulse'; set_active_brand('SmackDown'); st.rerun()

def render_wcw_sports_desk_embed(comp='WCW',compact=True,key_prefix='wcw_hub'):
 if comp!='WCW': return
 sc=wcw_sports_scores(comp)
 st.markdown('<div class="brand-hub-banner"><h3>WCW Sports Desk</h3><span class="small-text">NBA · NFL · ESPN · CBS · stadium credibility</span></div>',unsafe_allow_html=True)
 render_kpi_row([('Sports Legitimacy',f"{sc['sports_legitimacy']}/100",''),('Stadium Credibility',f"{sc['stadium_credibility']}/100",''),('Sports Crossovers',sc['sports_crossovers'],'')])
 lsq=last_show_quality_caption(comp)
 if lsq: st.caption(lsq)
 if compact and st.button('Open WCW Sports Desk',key=f'{key_prefix}_open'): st.session_state.nav_page='WCW Sports Desk'; set_active_brand('WCW'); st.rerun()

def render_brand_hub_embed(comp,compact=True,key_prefix='hub'):
 if comp=='NXT': render_nxt_spotlight_studio(comp,compact=compact,key_prefix=key_prefix)
 elif comp=='SmackDown': render_smackdown_culture_pulse_embed(comp,compact=compact,key_prefix=key_prefix)
 elif comp=='WCW': render_wcw_sports_desk_embed(comp,compact=compact,key_prefix=key_prefix)

def appearance_effect(company,person,appearance):
 revenue=appearance_revenue_for(company,appearance)
 prestige=random.randint(1,5)
 owner=activity_owner_brand(appearance)
 risk='Low' if owner==company else 'Medium'
 return {'revenue':revenue,'prestige_gain':prestige,'buzz':random.randint(5,15),'risk':risk,'viewership':random.randint(2,10),'sponsor':random.randint(1,5)}

def partner_nxt_exclusive(partner):
 return partner in NXT_EXCLUSIVE_PARTNERS or partner in NXT_CAMEO_PARTNERS

def cameo_allowed(company,partner,force=False):
 if company=='NXT': return True,None
 if partner_nxt_exclusive(partner): return force,'This partner is NXT-exclusive unless you force cross-brand.'
 return True,None

def cameo_fit_warnings(name,partner,project_type,w):
 warns=[]; fit=NXT_CHARACTER_FIT.get(name)
 if fit:
  if partner not in fit.get('partners',[]) and partner_nxt_exclusive(partner): warns.append(f'{name} is not an ideal fit for {partner} — better partners: {", ".join(fit["partners"][:4])}.')
  if project_type not in fit.get('projects',[]) and fit.get('projects'): warns.append(f'Consider project types like: {", ".join(fit["projects"][:3])}.')
  for av in fit.get('avoid',[]):
   if av.lower() in (project_type+' '+partner).lower(): warns.append(f'Character warning: {av}')
 if w:
  if w['popularity']<72 and project_type in ('Hollywood movie role','superhero movie cameo','movie cameo'): warns.append('Popularity may be too low for a major movie cameo.')
  if w['popularity']>=88 and w['momentum']>=70: warns.append('Star is hot — Mattel/Barbie/DC toy or comic merch push is viable.')
  if w['popularity']>=85 and w['momentum']>=75: warns.append('Merch boom window: suggest Mattel action figure, Barbie crossover, or DC comic cover.')
  if w['stamina']<40: warns.append('Low stamina — filming will hurt availability; use pre-taped promo.')
  recent=[a for a in st.session_state.get('appearance_history',[])[:6]+st.session_state.get('cameo_library',[])[:6] if a.get('person')==name or a.get('wrestler')==name]
  if len(recent)>=3: warns.append('Wrestler may be overexposed — consider a week off or pre-taped segment.')
  if w.get('status')=='Part-Time': warns.append('Already part-time — high missed-show risk.')
  if project_type=='SNL sketch' and name=='Raven': warns.append('Raven on SNL should not be goofy unless the joke protects his darkness.')
 return warns

def calc_cameo_effects(w,partner,project_type,tone,risk_level,length):
 pop=w['popularity'] if w else 75; mom=w['momentum'] if w else 55
 ranges={
  'Netflix':(1500000,3000000),'Marvel':(3000000,7000000),'DC':(3000000,7000000),
  'Hollywood':(5000000,12000000),'SNL':(500000,1500000),'Good Morning America':(300000,900000),
  'Olympics':(600000,1500000),'Oscars':(800000,2000000),'Comic-Con':(400000,1200000),
  'Mattel':(1000000,5000000),'Barbie':(1000000,5000000),'FOX':(500000,1400000),'NBC Sports':(500000,1300000),
 }
 lo,hi=900000,2200000
 for k,v in ranges.items():
  if k.lower() in partner.lower() or k.lower() in project_type.lower(): lo,hi=v; break
 if 'documentary' in project_type: lo,hi=1500000,3500000
 if 'toy' in project_type or 'comic' in project_type or 'commercial' in project_type: lo,hi=1000000,5000000
 if 'trailer' in project_type: lo,hi=400000,1200000
 rev=random.randint(lo,hi)
 if pop>=85: rev=int(rev*1.2)
 if pop>=85 and mom>=75: rev+=random.randint(200000,800000)
 pop_gain=random.randint(2,6)
 if 'Olympics' in partner: pop_gain+=2
 if tone in ('heroic','inspirational'): pop_gain+=1
 if tone in ('villainous','dark','arrogant') and w and w['alignment']=='H': pop_gain+=1
 stamina_cost=-random.randint(3,12)
 if 'month' in length: stamina_cost-=6
 elif 'week' in length and '2' in length: stamina_cost-=4
 miss_risk={'Low':0.08,'Medium':0.18,'High':0.32}.get(risk_level,0.15)
 if 'month' in length or '2 weeks' in length: miss_risk+=0.12
 morale_gain=random.randint(0,5)
 if risk_level=='High': morale_gain-=3
 sponsor_conf=random.randint(2,8)
 if partner in ('Mattel','Barbie','DC','Marvel','Netflix'): sponsor_conf+=3
 merch_boost=0
 if pop>=85 and mom>=75: merch_boost=random.randint(500000,2000000)
 twitter_buzz=random.randint(4,18)
 tension=0.12 if risk_level=='High' else 0.06
 if w and w['popularity']>=90: tension+=0.08
 return {'revenue':rev,'popularity':pop_gain,'morale':morale_gain,'stamina':stamina_cost,'miss_show_risk':round(miss_risk,2),'sponsor_confidence':sponsor_conf,'merchandise_boost':merch_boost,'twitter_buzz':twitter_buzz,'locker_room_tension':tension,'filming_length':length,'prestige_gain':random.randint(2,6)}

def build_cameo_prompt(fields,mode):
 w=fields.get('wrestler_obj'); name=fields['person']; prof=char_profile(name) if w else fields.get('staff_profile','')
 fit=NXT_CHARACTER_FIT.get(name,{}); warns='\n'.join(fields.get('warnings',[]))
 sections='TITLE:\nPLATFORM:\nWRESTLER:\nSCENE SETUP:\nCHARACTER ROLE:\nSCRIPT / DIALOGUE:\nSTAGE DIRECTIONS:\nCAMERA DIRECTIONS:\nSTORYLINE TIE-IN:\nRIVAL REACTION:\nTWITTER REACTION IDEAS:\nSPONSOR/MEDIA EFFECT:\nGAME EFFECTS:\nCONTINUITY WARNING:\n' if mode=='full' else 'IDEA TITLE:\nPLATFORM:\nLOGLINE:\nCHARACTER FIT:\nSTORYLINE HOOK:\nRIVAL ANGLE:\nTWITTER ANGLE:\nGAME EFFECT SUMMARY:\nWARNINGS:\n'
 return f"""You are writing for Bound For Glory GM Mode — an original wrestling universe (not WWE canon).
Create ORIGINAL dialogue and scenes. Do NOT copy copyrighted scripts word-for-word. You may reference real platforms (Netflix, SNL, Marvel-style, DC-style, Oscars, Olympics, Comic-Con).
Company: {fields['company']} | Person: {name} | Type: {fields['person_type']}
Profile: {prof}
Partner: {fields['partner']} | Project: {fields['project_type']} | Tone: {fields['tone']} | Length: {fields['length']}
Week: {fields['week']} | Storyline: {fields['storyline']} | Rival: {fields['rival']} | Sponsor: {fields['sponsor']} | Risk: {fields['risk']}
Character fit notes: {fit.get('role','Use Character Editor voice.')} | Avoid: {', '.join(fit.get('avoid',[])) or 'none'}
Local warnings: {warns or 'none'}
Mode: {'short creative cameo IDEA' if mode=='idea' else 'FULL cameo script package'}
Use these section headers exactly:
{sections}
Keep dialogue in-character. Connect to NXT storyline if provided. Suggest rival Twitter line if rival named."""

def rule_based_cameo(fields,mode):
 name=fields['person']; partner=fields['partner']; proj=fields['project_type']; rival=fields.get('rival') or 'a rival'
 tone=fields['tone']; fit=NXT_CHARACTER_FIT.get(name,{}); role=fit.get('role','guest star with star power')
 title=f"{name} — {partner} {proj.replace('_',' ').title()}"
 if mode=='idea':
  return f"""IDEA TITLE:
{title}

PLATFORM:
{partner}

LOGLINE:
{name} appears in a {tone} {proj} for {partner}, playing a {role}.

CHARACTER FIT:
{fit.get('role', name + ' should sound authentic to their Character Editor voice.')}

STORYLINE HOOK:
{fields.get('storyline') or 'Tie-in to current NXT title picture and weekly tension.'}

RIVAL ANGLE:
{rival} reacts on social media and may demand a response on NXT TV.

TWITTER ANGLE:
Sample: "{rival} tweets about {name}'s {partner} appearance crossing the line between entertainment and wrestling."

GAME EFFECT SUMMARY:
See calculated effects panel — revenue, popularity, stamina, merch window.

WARNINGS:
{chr(10).join(fields.get('warnings',[])) or 'Review popularity and filming length before applying.'}"""
 if proj=='SNL sketch':
  script_body=f"""[Studio. Cold open energy.]

HOST:
"Ladies and gentlemen — tonight we go Hollywood with {name}!"

{name.upper()} (entrance — {tone} energy):
"Relax. I did not come here to make friends. I came here to make headlines."

[Beat — crowd reacts]

{name.upper()}:
"You think your office politics are brutal? Try a locker room where everybody wants your spot and your soul."

PUNCHLINE:
"So yeah — I'm the villain. But at least I'm honest. Your boss still pretends the bonus structure is fair."

CHARACTER PROTECTION:
Keep {name} sharp — not randomly goofy unless the sketch frames arrogance as the joke."""
 elif proj=='Good Morning America interview':
  script_body=f"""[GMA studio — morning lights.]

HOST:
"Joining us live — NXT star {name}, fresh off major buzz around {partner}."

{name.upper()}:
"Thank you. The ring taught me discipline. Television taught me the rest of the world is watching."

HOST:
"Any message for fans before your next title defense?"

{name.upper()}:
"Show up. Or watch someone else write history without you."
"""
 elif 'Olympics' in proj or partner=='Olympics':
  script_body=f"""[Olympic training facility — international broadcast tone.]

NARRATOR:
"Tonight — NXT's {name} joins the Olympic spirit for a special media segment."

{name.upper()}:
"Gold is not given. It is earned when nobody is watching."

[Medal presentation beat — inspirational crowd]

{name.upper()}:
"To every kid training at 5 AM — your country is not behind you. You are ahead of them."
"""
 else:
  script_body=f"""[Scene opens — cinematic {tone} tone for {partner}.]

{name.upper()}:
"Power is not performed in a ring alone. It is packaged, sold, and remembered long after the lights die."

[Camera pushes in — blockbuster framing]

{name.upper()}:
"You wanted a star? You got one. Now decide if you can afford what comes next."
"""
 return f"""TITLE:
{title}

PLATFORM:
{partner}

WRESTLER:
{name}

SCENE SETUP:
A {tone} {proj} segment for {partner}. {name} appears as {role}.

CHARACTER ROLE:
{role}

SCRIPT / DIALOGUE:
{script_body}

STAGE DIRECTIONS:
Play {tone}. Protect character brand. No parody that makes a dominant heel look weak unless intentional comedy.

CAMERA DIRECTIONS:
Open wide on environment → push-in on {name} for money line → cut to reaction shot for rival/sponsor mention.

STORYLINE TIE-IN:
{fields.get('storyline') or 'Feeds directly into next NXT weekly — mention title, PLE, or faction tension.'}

RIVAL REACTION:
{rival} should respond on Twitter and possibly demand an in-ring answer next week.

TWITTER REACTION IDEAS:
- {rival}: "Hollywood really gave {name} a camera and called it storytelling."
- NXT Desk: "{name}'s {partner} segment is trending — tune in this week."
- Fan account: "Merch drop when?"

SPONSOR/MEDIA EFFECT:
{fields.get('sponsor') or partner} gains trust; mainstream press boosts NXT prestige.

GAME EFFECTS:
(See Apply panel — revenue, popularity, stamina, sponsor confidence, merch boost.)

CONTINUITY WARNING:
{chr(10).join(fields.get('warnings',[])) or 'If filming length is long, use a pre-taped promo on the weekly show.'}"""

def generate_cameo_content(mode,fields):
 prompt=build_cameo_prompt(fields,mode)
 out=ai(prompt)
 if out and not str(out).startswith('AI error'): return out.strip(),True
 return rule_based_cameo(fields,mode),False

def save_cameo_record(fields,script_text,ai_flag,mode):
 eff=calc_cameo_effects(fields.get('wrestler_obj'),fields['partner'],fields['project_type'],fields['tone'],fields['risk'],fields['length'])
 rec={
  'id':len(st.session_state.get('cameo_library',[]))+1,'company':fields['company'],'person':fields['person'],'person_type':fields['person_type'],
  'partner':fields['partner'],'project_type':fields['project_type'],'tone':fields['tone'],'length':fields['length'],'week':fields['week'],
  'storyline_tie_in':fields.get('storyline',''),'rival':fields.get('rival',''),'sponsor':fields.get('sponsor',''),'risk_level':fields['risk'],
  'title':fields['person']+' — '+fields['partner']+' '+fields['project_type'],'script':script_text,'platform':fields['partner'],
  'effects':eff,'warnings':fields.get('warnings',[]),'continuity_warning':'; '.join(fields.get('warnings',[])[:3]),
  'revenue':eff['revenue'],'popularity_effect':eff['popularity'],'morale_effect':eff['morale'],'stamina_effect':eff['stamina'],
  'sponsor_effect':eff['sponsor_confidence'],'missed_show_risk':eff['miss_show_risk'],'filming_length':eff['filming_length'],
  'merchandise_boost':eff['merchandise_boost'],'twitter_buzz':eff['twitter_buzz'],'locker_room_tension':eff['locker_room_tension'],
  'ai_generated':ai_flag,'generator_mode':mode,'label':'AI' if ai_flag else 'Rule-based',
 }
 rec=normalize_cameo_record(rec)
 st.session_state.cameo_library.insert(0,rec)
 st.session_state.last_cameo=rec
 return rec

def apply_cameo_record(rec,post_twitter=True):
 w=find(rec['person']); eff=rec.get('effects',{})
 if w:
  apply_wrestler_deltas(w,pop=eff.get('popularity',0),morale=eff.get('morale',0),stamina=eff.get('stamina',0),buzz=eff.get('twitter_buzz',0))
  w['morale']=max(0,min(100,w['morale']+eff.get('morale',0)))
  w['stamina']=max(0,w['stamina']+eff.get('stamina',0))
  w['twitter_buzz']=min(100,w.get('twitter_buzz',0)+eff.get('twitter_buzz',0))
  if random.random()<eff.get('miss_show_risk',0.1): w['status']='Part-Time'
  if eff.get('locker_room_tension',0)>0.15:
   for ow in random.sample(payroll_wrestlers(rec['company']),min(2,len(payroll_wrestlers(rec['company'])))):
    if ow['name']!=rec['person']: ow['morale']=max(0,ow['morale']-2)
 comp=rec['company']
 add_transaction(comp,'Cameo Revenue',f"{rec['person']} — {rec['partner']} {rec['project_type']}",int(eff.get('revenue',0)))
 if eff.get('merchandise_boost',0): add_transaction(comp,'Merchandise Revenue',f"Merch boost from {rec['person']} cameo",int(eff['merchandise_boost']))
 finance_flash(comp,int(eff.get('revenue',0)),f"cameo revenue for {rec['person']}")
 hist=normalize_appearance_record({**rec,'appearance':rec['project_type'],'notes':rec.get('storyline_tie_in') or '','controversy_risk':rec['risk_level'],'type':'cameo'})
 st.session_state.appearance_history.insert(0,hist)
 st.session_state.news_feed.insert(0,f"{rec['company']} cameo: {rec['person']} — {rec['title']} — {money(rec['revenue'])}")
 if post_twitter and rec.get('rival'):
  rival=rec['rival']; rw=find(rival)
  txt=tweet(rw,'Movie/Show Promotion Tweet',rec['person']) if rw else f"{rival} reacts to {rec['person']}'s {rec['partner']} appearance."
  st.session_state.twitter_posts.insert(0,{'id':len(st.session_state.twitter_posts)+1,'week':st.session_state.week,'company':rec['company'],'wrestler':rival,'role':'Wrestler','handle':'@'+slug(rival).replace('_',''),'post_type':'Movie/Show Promotion Tweet','text':txt,'likes':random.randint(2000,50000),'reposts':random.randint(200,12000),'replies':random.randint(100,4000),'views':random.randint(30000,600000),'mentions':rec['person'],'effects':{},'viral':True,'ai_generated':rec.get('ai_generated',False)})
 update_rank({rec['person']:f"Cameo appearance ({rec['partner']}) boosted profile."})

def brand_exclusive_ai_snippet(company,featured=None,ctx=None):
 lines=[]
 for r in recommend_brand_exclusives(company,2):
  lines.append(f"{r['activity']}: {r['reason']}")
 if company=='NXT':
  pool=[(n,f) for n,f in NXT_CHARACTER_FIT.items() if find(n) and find(n)['company']=='NXT']
  if featured and featured in NXT_CHARACTER_FIT:
   f=NXT_CHARACTER_FIT[featured]
   lines.append(f'{featured} fits {f["partners"][0]} / {f["projects"][0]} on NXT Hollywood lane.')
  for n,f in random.sample(pool,min(1,len(pool))):
   lines.append(f'{n}: {f["role"]} — {random.choice(f["partners"])}.')
 elif company=='SmackDown':
  lines.append('SmackDown exclusives: Grammys, BET/VMAs, music videos, concerts, Paramount/USA/TNT celebrity TV.')
  if featured in ('Logan Paul','Bad Bunny','KSI'): lines.append(f'{featured} is ideal for music-video or awards-show crossover.')
 elif company=='WCW':
  lines.append('WCW exclusives: NBA/NFL, halftime shows, draft announcements, ESPN/CBS, sports documentaries.')
  if ctx and ctx.get('venue',{}).get('capacity',0)>40000: lines.append('Stadium market — push NFL halftime or ESPN SportsCenter.')
 if ctx and ctx.get('sched',{}).get('hometown'):
  lines.append(f"Hometown talent on calendar: {', '.join(ctx['sched']['hometown'][:3])} — tie to city-exclusive angle.")
 return ' Brand exclusives: '+' '.join(lines[:5])

NXT_UNFILTERED_EXCLUSIVE_MSG="NXT Unfiltered is exclusive to NXT's cinematic media ecosystem."
NXT_UNFILTERED_TONES=['emotional deep dive','serious analyst','debate show','fan reaction','business/media breakdown','PLE fallout special','controversial tweet breakdown','Hollywood documentary style','locker room psychology','funny but smart']
NXT_UNFILTERED_LENGTHS=['Full Episode (~10 min)','Long (~10 min)','Medium (~7 min)','Short (~4 min)','Deep Dive (~12 min)']
NXT_UNFILTERED_LENGTH_SPECS={
 'Short (~4 min)':{'target_minutes':4,'min_dialogue_chars':2800,'min_lines':28,'lines_per_section':2},
 'Medium (~7 min)':{'target_minutes':7,'min_dialogue_chars':5000,'min_lines':48,'lines_per_section':3},
 'Long (~10 min)':{'target_minutes':10,'min_dialogue_chars':7200,'min_lines':72,'lines_per_section':5},
 'Full Episode (~10 min)':{'target_minutes':10,'min_dialogue_chars':9000,'min_lines':95,'lines_per_section':5},
 'Deep Dive (~12 min)':{'target_minutes':12,'min_dialogue_chars':11000,'min_lines':115,'lines_per_section':6},
 'Short':{'target_minutes':4,'min_dialogue_chars':2800,'min_lines':28,'lines_per_section':2},
 'Medium':{'target_minutes':7,'min_dialogue_chars':5000,'min_lines':48,'lines_per_section':3},
 'Long':{'target_minutes':10,'min_dialogue_chars':7200,'min_lines':72,'lines_per_section':5},
 'Deep Dive':{'target_minutes':12,'min_dialogue_chars':9000,'min_lines':95,'lines_per_section':6},
}
PODCAST_TTS_PAUSE_MS=720
PODCAST_TTS_SENTENCE_PAUSE_MS=280
OPENAI_TTS_MODEL='tts-1-hd'
PODCAST_TTS_VOICES=['neutral','warm','deep','bright','energetic','smooth','broadcast','fan-debate']

REAL_LIFE_THEMES=['fame','ego','insecurity','celebrity culture','Hollywood pressure','sports pressure','media scrutiny','public image vs private emotion','locker room politics','contract pressure','social media backlash','sponsor pressure','fan tribalism','power struggles','leadership','betrayal','loyalty','family pressure','legacy','burnout','public criticism','champion pressure','overpush backlash','post-debut neglect','popularity struggles','fear of being replaced']
HOST_REAL_LIFE_LENS={
 'maya':{'themes':['insecurity','betrayal','loyalty','public image vs private emotion','grief','fan sympathy'],'phrases':['This feels like a real-world fame problem.','The deeper issue is that this character feels disrespected.','This is what happens when public image becomes more important than personal truth.','In real sports or entertainment, this kind of pressure can break someone if the company keeps pushing without listening.']},
 'tasha':{'themes':['celebrity culture','Hollywood pressure','media scrutiny','public image','sponsor pressure'],'phrases':['This reminds me of how actors deal with fame when the brand needs them more than they need the brand.','A real-life comparison would be the pressure celebrities face when every clip becomes a headline.','NXT built a world where fame is currency — this story is spending it.']},
 'serena':{'themes':['locker room politics','contract pressure','burnout','sports pressure','respect'],'phrases':['In a real locker room, this is not about the spot — it is about whether anyone listened.','This feels similar to athlete pressure when the office keeps teasing opportunity without payoff.','Respect is not storyline decoration — it is daily life for talent.']},
 'marcus':{'themes':['legacy','power struggles','leadership','long-term storytelling'],'phrases':['In wrestling history, stories like this work because the thread remembers why the feud started.','The emotional pattern here is control — who owns the narrative week to week.']},
 'dante':{'themes':['sponsor pressure','fan tribalism','popularity','company value','media scrutiny'],'phrases':['Business-wise, controversy is inventory — but sponsors need a story they can defend.','This is not just heat — it is quarterly narrative risk.']},
 'rico':{'themes':['social media backlash','fan tribalism','public criticism','viral moments'],'phrases':['Fans will argue all week — that split reaction is what sells the rematch.','The timeline is not wrong — it is just early, and early is loud.']},
}
HOST_SLOT_MIX={
 'maya':['emotion','character psychology','fan investment','betrayal and redemption','real-life emotional patterns','hidden motivation'],
 'tasha':['press','Hollywood crossover','media buzz','popularity','sponsor reactions','celebrity culture','public image'],
 'serena':['morale','locker room','contracts','disrespect','burnout','athlete pressure','real-world locker room politics'],
 'marcus':['continuity','booking logic','title prestige','what made sense','wrestling history parallels'],
 'dante':['viewership','money','attendance','popularity movement','company value','sponsor and media economics'],
 'rico':['Twitter','fan reaction','hot takes','viral clips','how fans interpret stories'],
}
NXT_UF_SCRIPT_SECTIONS=[
 'Story Recap','Deep Story Analysis','Real-Life Connection','Character Thought Process','World-Building Meaning',
 'Hidden Motivation','What This Says About The Company','Character Psychology','How Fans Might Interpret It',
 'What The Locker Room Might Think','What Sponsors Might Worry About','What This Sets Up Emotionally',
 'Controversial Tweet Breakdown','Morale Watch','Popularity Movement','Episode / PLE Fallout',
 'What Made Sense','What Did Not Make Sense','Business / Viewership / Attendance Impact',
 'Twitter Reaction Prediction','Locker Room Reaction','Sponsor / Media Reaction','What Needs Follow-Up',
 'Next Week Predictions','Closing Thoughts',
]
HOST_SLOT_INTROS={
 'maya':'Welcome to NXT Unfiltered. Tonight we are not just talking about who won and who lost — we are talking about who left damaged.',
 'marcus':'I will say it right now — this episode works or fails on whether it remembered last week. We are judging the thread, not just the spot.',
 'tasha':'From a Hollywood lens, NXT sells cinematic emotion — press, prestige, and buzz ride on whether fans believe the story.',
 'serena':'Locker room morale matters. Public disrespect does not stay online — it walks into the building.',
 'dante':'From a business standpoint, emotion sells tickets when it is coherent. Viewership and sponsor confidence follow clarity.',
 'rico':'The timeline is already cooking. Fans are screenshotting everything before we even finish this episode.',
}

def _default_nxt_unfiltered_hosts():
 return {
  'Maya Cruz':{'name':'Maya Cruz','host_slot':'maya','gender':'Female','character_type':'Podcast Host','company':'NXT','identity':'Emotional story analyst','personality':'thoughtful, sharp, empathetic, serious when needed','podcast_role':'breaks down emotion, character pain, betrayal, redemption, and fan investment','speaking_style':'calm, deep, emotionally intelligent','strengths':['emotional intelligence','empathy','fan investment reads','character psychology'],'weaknesses':['can underweight business optics','sometimes too serious for light weeks'],'focuses_on':['character emotions','relationship drama','betrayal','morale','fan sympathy','why the audience cares'],'should_not':['talk like a generic recap host','ignore emotional consequences'],'bias':'leans toward emotional truth and fan sympathy','catchphrase':'Let us sit with what that moment actually cost them.','image_path':'','tts_voice':'warm','tts_speed':0.94,'tts_energy':0.85,'bookable':False},
  'Tasha Monroe':{'name':'Tasha Monroe','host_slot':'tasha','gender':'Female','character_type':'Podcast Host','company':'NXT','identity':'Pop culture and media analyst','personality':'stylish, confident, witty, entertainment-focused','podcast_role':'connects NXT stories to Hollywood, Netflix, Marvel/DC, Oscars, SNL, GMA, Olympics, and media buzz','speaking_style':'fast, smart, celebrity/media aware','strengths':['pop culture framing','press and trend reads','Hollywood crossover angles'],'weaknesses':['can rush in-ring logic','sometimes favors buzz over payoff'],'focuses_on':['media appearances','press','popularity','Twitter trends','Hollywood crossover','sponsor reactions'],'should_not':['ignore business/media impact'],'bias':'frames everything through mainstream entertainment optics','catchphrase':'If it is not trending, it is not finished.','image_path':'','tts_voice':'bright','tts_speed':0.96,'tts_energy':0.95,'bookable':False},
  'Serena Vale':{'name':'Serena Vale','host_slot':'serena','gender':'Female','character_type':'Podcast Host','company':'NXT','identity':'Former athlete / locker room psychology voice','personality':'direct, competitive, no-nonsense, protective of wrestlers','podcast_role':'analyzes morale, backstage tension, contracts, creative frustration, and whether wrestlers feel respected','speaking_style':'blunt, honest, athletic, locker-room focused','strengths':['locker room truth','morale and contract reads','protects talent'],'weaknesses':['can sound harsh to casual fans','less patient with comedy beats'],'focuses_on':['morale','contracts','locker room tension','disrespect','stamina','burnout','refusing to perform'],'should_not':['sugarcoat bad booking'],'bias':'protects talent and calls out disrespect','catchphrase':'Respect is not a storyline — it is a contract with the locker room.','image_path':'','tts_voice':'deep','tts_speed':0.95,'tts_energy':0.9,'bookable':False},
  'Marcus King':{'name':'Marcus King','host_slot':'marcus','gender':'Male','character_type':'Podcast Host','company':'NXT','identity':'Wrestling historian and storyline critic','personality':'analytical, intense, traditional wrestling mind','podcast_role':'judges whether the story makes sense week to week','speaking_style':'serious, detailed, sometimes harsh','strengths':['continuity tracking','booking logic','long-term storytelling'],'weaknesses':['can over-criticize','slow on pop culture tangents'],'focuses_on':['continuity','booking logic','title prestige','long-term storytelling','PLE build','dropped storylines'],'should_not':['overpraise random booking'],'bias':'continuity hawk — rewards earned stories','catchphrase':'Show me the thread, not just the spot.','image_path':'','tts_voice':'broadcast','tts_speed':0.93,'tts_energy':0.8,'bookable':False},
  'Dante Brooks':{'name':'Dante Brooks','host_slot':'dante','gender':'Male','character_type':'Podcast Host','company':'NXT','identity':'Business and ratings analyst','personality':'smooth, strategic, numbers-focused, media-business minded','podcast_role':'explains viewership, attendance, money, sponsorships, popularity movement, and company prestige','speaking_style':'polished, confident, business-like','strengths':['ratings and revenue reads','sponsor trust','popularity economics'],'weaknesses':['can cold-read raw emotion','risks spreadsheet tone'],'focuses_on':['viewership','attendance','profit/loss','popularity','sponsor trust','press reaction','company value'],'should_not':['ignore story quality when discussing business'],'bias':'numbers-first but respects emotional payoffs that sell','catchphrase':'Emotion is a line item when it is real.','image_path':'','tts_voice':'smooth','tts_speed':0.94,'tts_energy':0.75,'bookable':False},
  'Rico Blaze':{'name':'Rico Blaze','host_slot':'rico','gender':'Male','character_type':'Podcast Host','company':'NXT','identity':'Fan voice / hot-take debate host','personality':'loud, funny, passionate, unpredictable, emotional fan energy','podcast_role':'says what fans online are probably thinking','speaking_style':'energetic, funny, dramatic, debate-style','strengths':['fan reaction','viral moment reads','debate energy'],'weaknesses':['can get too silly on serious emotional stories','hot takes need fact-checking'],'focuses_on':['Twitter reaction','fan outrage','hype moments','viral clips','controversial tweets','who fans love/hate'],'should_not':['become too silly during serious emotional stories'],'bias':'fan-first hot takes — loud but not clueless','catchphrase':'The timeline is not wrong — it is just early.','image_path':'','tts_voice':'fan-debate','tts_speed':0.98,'tts_energy':1.0,'bookable':False},
 }

def ensure_nxt_unfiltered_hosts():
 defaults=_default_nxt_unfiltered_hosts()
 if 'nxt_unfiltered_hosts' not in st.session_state:
  st.session_state.nxt_unfiltered_hosts=json.loads(json.dumps(defaults))
 else:
  for k,v in defaults.items():
   cur=st.session_state.nxt_unfiltered_hosts.setdefault(k,dict(v))
   for fk,fv in v.items():
    if fk not in cur or cur[fk] in (None,''): cur[fk]=fv
 if 'nxt_unfiltered_episodes' not in st.session_state: st.session_state.nxt_unfiltered_episodes=[]
 if 'nxt_unfiltered_draft' not in st.session_state: st.session_state.nxt_unfiltered_draft={}
 if 'last_nxt_unfiltered' not in st.session_state: st.session_state.last_nxt_unfiltered=None
 if 'podcast_hosts_booking_enabled' not in st.session_state: st.session_state.podcast_hosts_booking_enabled=False
 if 'nxt_uf_tts_speed' not in st.session_state: st.session_state.nxt_uf_tts_speed=0.95
 if 'nxt_uf_last_ai_error' not in st.session_state: st.session_state.nxt_uf_last_ai_error=None
 if 'nxt_uf_tts_energy' not in st.session_state: st.session_state.nxt_uf_tts_energy=0.9

def get_nxt_unfiltered_host(name):
 ensure_nxt_unfiltered_hosts()
 h=dict(st.session_state.nxt_unfiltered_hosts.get(name,{}) or {'name':name})
 h['name']=name
 return h

def check_nxt_unfiltered_exclusive(comp,force=False):
 if comp=='NXT' or force: return True,None
 return False,NXT_UNFILTERED_EXCLUSIVE_MSG

def host_mix_focus(host_names):
 focus=[]
 slots=set()
 for n in host_names:
  h=get_nxt_unfiltered_host(n)
  slots.add(h.get('host_slot',''))
  focus+=HOST_SLOT_MIX.get(h.get('host_slot',''),[])
 return list(dict.fromkeys(focus))

def host_mix_guidance(host_names):
 slots={get_nxt_unfiltered_host(n).get('host_slot','') for n in host_names}
 lines=[]
 if slots=={'maya','marcus'}: lines.append('Maya + Marcus lineup: emphasize emotion, story logic, continuity, what made sense vs what did not.')
 if slots=={'tasha','dante'}: lines.append('Tasha + Dante lineup: emphasize press, popularity, sponsor reaction, Hollywood crossover, viewership, money.')
 if slots=={'serena','rico'}: lines.append('Serena + Rico lineup: emphasize locker room morale, fan reaction, Twitter heat, backstage tension.')
 if len(slots)>=5: lines.append('Full roundtable: emotional analysis, media analysis, locker room morale, booking critique, business impact, and fan reaction — debate-style.')
 elif len(slots)==2: lines.append('Two-host episode: keep it focused — fewer voices, deeper takes on their specialties.')
 return '\n'.join(lines)

def host_profile_prompt_block(h):
 return f"""{h['name']} ({h.get('gender','')}) — {h.get('identity','')}
Role: {h.get('podcast_role','')}
Personality: {h.get('personality','')}
Speaking style: {h.get('speaking_style','')}
Strengths: {', '.join(h.get('strengths',[]))}
Weaknesses: {', '.join(h.get('weaknesses',[]))}
Focus: {', '.join(h.get('focuses_on',[]))}
Should NOT: {', '.join(h.get('should_not',[]))}
Bias: {h.get('bias','')}
Catchphrase (optional): {h.get('catchphrase','')}"""

def get_nxt_unfiltered_length_spec(length):
 return NXT_UNFILTERED_LENGTH_SPECS.get(length) or NXT_UNFILTERED_LENGTH_SPECS['Full Episode (~10 min)']

def count_podcast_dialogue_chars(script):
 total=0
 for m in re.finditer(r'"([^"]{3,})"', script or ''):
  total+=len(m.group(1))
 return total

def estimate_podcast_runtime_minutes(script):
 chars=count_podcast_dialogue_chars(script)
 return round(chars/750.0,1)

def humanize_dialogue_for_tts(text):
 if not text: return text
 t=str(text).strip()
 subs=(
  (' do not ',' don\'t '),(' cannot ',' can\'t '),(' will not ',' won\'t '),(' did not ',' didn\'t '),
  (' is not ',' isn\'t '),(' are not ',' aren\'t '),(' was not ',' wasn\'t '),(' have not ',' haven\'t '),
  (' has not ',' hasn\'t '),(' would not ',' wouldn\'t '),(' should not ',' shouldn\'t '),
  (' could not ',' couldn\'t '),(' it is ',' it\'s '),(' that is ',' that\'s '),(' we are ',' we\'re '),
  (' they are ',' they\'re '),(' I am ',' I\'m '),(' let us ',' let\'s '),(' going to ',' gonna '),
 )
 for a,b in subs:
  t=re.sub(re.escape(a),b,t,flags=re.I)
 t=re.sub(r'\bHost Name\b','',t,flags=re.I)
 t=re.sub(r'\s{2,}',' ',t).strip()
 return t

def _hosts_by_slot(hosts):
 return {h.get('host_slot',''):h for h in hosts if h.get('host_slot')}

def _cycle_hosts(hosts,start=0):
 if not hosts: return []
 i=start%len(hosts)
 while True:
  yield hosts[i%len(hosts)]
  i+=1

def expand_script_to_target_length(script,fields,hosts):
 spec=get_nxt_unfiltered_length_spec(fields.get('length','Full Episode (~10 min)'))
 min_chars=int(spec.get('min_dialogue_chars',7500))
 min_lines=int(spec.get('min_lines',80))
 if count_podcast_dialogue_chars(script)>=min_chars and len(parse_podcast_dialogue(script,hosts))>=min_lines:
  return script
 story=fields.get('story_text','')[:600] or fields.get('main_story','') or 'this week on NXT'
 chars=fields.get('main_characters','') or 'the roster'
 tweets=fields.get('controversial_tweets','') or 'fan accounts are already clipping the finish'
 extra=[]
 fillers=[
  ('maya',_host_real_life_line('maya',fields)),
  ('tasha',_host_real_life_line('tasha',fields)),
  ('serena',_host_real_life_line('serena',fields)),
  ('marcus',f"World-building check: NXT sells cinema — this story is about image versus truth, not just the pin."),
  ('dante',f"Business lens — attention is inventory; sponsors need a sentence they can defend."),
  ('rico',f"Fan tribalism is coming — defend your side in replies, but know why you feel it."),
  ('maya',f"Sit with what {chars} might be hiding backstage — fear of replacement is real on this roster."),
  ('marcus',f"Continuity: {story[:100]}… must pay off or the emotional investment was a tax on fans."),
  ('tasha',f"Hollywood parallel — third-act turn only works if the motive was visible on camera."),
  ('serena',f"Locker room: respect beats pyro. Who walked out feeling heard?"),
  ('dante',f"Popularity and affection can diverge — office has to aim both."),
  ('rico',f"The timeline is drafting arguments — that is free marketing if the rematch delivers."),
 ]
 slot_map=_hosts_by_slot(hosts)
 host_list=[h for h in hosts if h.get('name')]
 gen=_cycle_hosts(host_list,len(script)%max(1,len(host_list)))
 idx=0
 while count_podcast_dialogue_chars(script)+sum(len(x) for x in extra)<min_chars and idx<120:
  slot,txt=fillers[idx%len(fillers)]
  h=slot_map.get(slot) or next(gen)
  extra.append(_host_line(h,humanize_dialogue_for_tts(txt)))
  idx+=1
 if extra:
  script=script.rstrip()+'\n\nExtended Roundtable\n\n'+'\n\n'.join(extra)
 return script

def _char_names_from_fields(fields):
 return [n.strip() for n in (fields.get('main_characters','') or '').split(',') if n.strip()]

def _story_beats_from_fields(fields,max_beats=16):
 text=(fields.get('story_text','') or fields.get('main_story','') or '').strip()
 if not text: return []
 parts=re.split(r'[\n.!?]+',text)
 beats=[p.strip() for p in parts if len(p.strip())>28]
 random.shuffle(beats)
 return beats[:max_beats]

def nxt_world_building_context():
 nxt_lore=BRAND_THEMES.get('NXT',{}).get('lore','')
 sd_lore=BRAND_THEMES.get('SmackDown',{}).get('lore','')[:120]
 wcw_lore=BRAND_THEMES.get('WCW',{}).get('lore','')[:120]
 prof=st.session_state.company_profiles.get('NXT',{})
 gm=prof.get('gm') or COMPANIES.get('NXT',{}).get('gm','the office')
 return {
  'nxt':nxt_lore,
  'gm':gm,
  'contrast':f"NXT is a media machine — not just wrestling. SmackDown runs on {sd_lore[:80]}… WCW runs on {wcw_lore[:80]}… Same story hits different in each world.",
  'culture':'Hollywood press, exclusive lanes, and cinematic storytelling shape how talent eat, sleep, and negotiate.',
 }

def _character_psych_read(name,story_hint=''):
 w=find(name)
 bible=st.session_state.character_bible.get(name,{})
 archetype=bible.get('archetype','') or (f"{name} on NXT" if w else name)
 promo=bible.get('promo','') or ''
 pop=w.get('popularity',50) if w else 50
 morale=w.get('morale',50) if w else 50
 champ=is_champ(name)
 reads={
  'Christian Rose':f"{name} acts like he owns the room, but the deeper read is insecurity — he needs people to see him as untouchable because authenticity threatens the brand he sells.",
  'CM Punk':f"{name}'s anger feels personal — he is not just fighting a rival, he is fighting the idea that truth can be replaced by branding.",
  'Raven':f"{name} does not speak in riddles to sound dark — mystery is control. If people are confused, he controls the pace.",
  'Lani Rose':f"{name} fights like someone proving she belongs — fear of being overlooked can look like fire until it burns out.",
  'Roman Reigns':f"{name} carries legacy pressure — every decision is about family, dominance, and never looking replaceable.",
 }
 if name in reads: return reads[name]
 wants='stay relevant and keep control of the narrative'
 fears='being exposed or replaced'
 drive='pride'
 if w:
  if morale<40: fears='being disrespected or discarded'; drive='resentment'
  elif pop<45: wants='win the crowd back'; fears='being forgotten after debut'
  elif pop>80: wants='protect top status'; drive='ego' if w.get('alignment')=='Heel' else 'loyalty'
  if champ: fears='losing the belt and the identity that comes with it'; wants='define the division'
 if 'betray' in (story_hint or '').lower(): drive='revenge or grief'
 return f"For {name}: wants {wants}; fears {fears}; driven by {drive}. Archetype: {archetype}. Voice: {promo[:100]}."

def _host_real_life_line(slot,fields):
 lens=HOST_REAL_LIFE_LENS.get(slot,{})
 phrase=random.choice(lens.get('phrases',['This reminds me of real-world pressure in sports entertainment.']))
 theme=random.choice(lens.get('themes',REAL_LIFE_THEMES[:6]))
 story=fields.get('main_story','')[:60]
 return f"{phrase} The emotional pattern here is {theme} — and it connects to {story or 'this week'} because the conflict is about control, not just wins."

def _section_lines_character_thought(hosts,fields):
 names=_char_names_from_fields(fields) or [n.strip() for n in (fields.get('main_story','') or '').split() if len(n.strip())>3][:3]
 if not names: names=['the featured talent']
 story=(fields.get('story_text','') or fields.get('main_story',''))[:400]
 slot_order=['maya','serena','marcus','tasha','dante','rico']
 slot_map=_hosts_by_slot(hosts)
 out=[]
 for i,nm in enumerate(names[:4]):
  slot=slot_order[i%len(slot_order)]
  h=slot_map.get(slot) or hosts[i%len(hosts)]
  read=_character_psych_read(nm,story)
  q=['What do they want?','What are they afraid of?','Are they performing for the audience or being honest?']
  out.append(_host_line(h,humanize_dialogue_for_tts(f"{read} {random.choice(q)} Do their actions make sense for who they are?")))
 return out or [_host_line(hosts[0],humanize_dialogue_for_tts('Pick main characters to unlock deeper thought-process reads.'))]

def build_nxt_unfiltered_prompt(fields,hosts):
 host_blocks='\n'.join(host_profile_prompt_block(h) for h in hosts)
 names=[h['name'] for h in hosts]
 mix=host_mix_focus(names)
 guide=host_mix_guidance(names)
 spec=get_nxt_unfiltered_length_spec(fields.get('length','Full Episode (~10 min)'))
 tgt=spec.get('target_minutes',10)
 min_chars=spec.get('min_dialogue_chars',7500)
 min_lines=spec.get('min_lines',80)
 lps=spec.get('lines_per_section',5)
 return f"""You are writing a NotebookLM-style podcast script for **NXT Unfiltered** — exclusive to NXT's cinematic Hollywood storytelling brand.

ONLY these hosts may speak (each must sound distinct — do NOT make them sound the same):
{host_blocks}

Episode focus mix for this lineup: {', '.join(mix)}
{guide}
Host count: {len(hosts)} — {"focused two-host conversation" if len(hosts)==2 else "roundtable debate" if len(hosts)>=5 else "panel discussion"}

USER INPUTS:
Episode title: {fields.get('episode_title','')}
Week: {fields.get('week','')}
Related NXT show: {fields.get('related_show','')}
Related PLE: {fields.get('related_ple','')}
Main story/rivalry: {fields.get('main_story','')}
Main characters: {fields.get('main_characters','')}
Controversial tweets: {fields.get('controversial_tweets','')}
Morale notes: {fields.get('morale_notes','')}
Popularity changes: {fields.get('popularity_changes','')}
PLE fallout: {fields.get('ple_fallout','')}
User notes: {fields.get('user_notes','')}
Tone: {fields.get('tone','')}
Length: {fields.get('length','')}

FULL STORY TEXT (use details from this — do not invent unrelated plots):
{(fields.get('story_text','') or '')[:14000]}

MAIN CHARACTERS TO ANALYZE (internal thought process — required if listed):
{fields.get('main_characters','') or 'Infer from story text'}

NXT WORLD (how this universe is built — reference when relevant):
{nxt_world_building_context()['nxt']}
{nxt_world_building_context()['contrast']}

FORMAT — actual podcast script. Each line MUST be:
Host Name:
"dialogue in quotes"

DO NOT only summarize what happened. Explain WHY it matters beneath the surface.

Include these sections with clear headers:
1. Episode Title
2. Host Lineup
3. Opening Intro
4. Story Recap
5. Deep Story Analysis
6. Real-Life Connection
7. Character Thought Process
8. World-Building Meaning
9. Hidden Motivation
10. What This Says About The Company
11. Character Psychology
12. How Fans Might Interpret It
13. What The Locker Room Might Think
14. What Sponsors Might Worry About
15. What This Sets Up Emotionally
16. Controversial Tweet Breakdown (if tweets provided; else brief note)
17. Morale Watch
18. Popularity Movement
19. Episode / PLE Fallout
20. What Made Sense
21. What Did Not Make Sense
22. Business / Viewership / Attendance Impact
23. Twitter Reaction Prediction
24. Locker Room Reaction
25. Sponsor / Media Reaction
26. What Needs Follow-Up
27. Next Week Predictions
28. Closing Thoughts

REAL-LIFE & DEPTH RULES:
- Connect to real-life themes when useful: {', '.join(REAL_LIFE_THEMES[:12])}… (and more). Use careful wording: "This reminds me of…", "This feels similar to…", "In real sports entertainment…", "The emotional pattern here is…"
- NEVER claim fake real-world facts, real allegations, or copy copyrighted scenes.
- For each major character: what do they want, fear, hide? What emotion drives them (pride, fear, jealousy, loyalty, revenge, ambition, love, guilt, insecurity)? Growing or falling apart? Honest or performing?
- World-building: what NXT feels like as a company, how it differs from SmackDown/WCW, owner/GM culture, media deals, sponsors, Twitter tension, contracts, popularity as power, champions as identity, exclusive media lanes.
- Host lenses: Maya = emotional psychology & fan sympathy; Tasha = Hollywood/celebrity/public image; Serena = locker room/athlete/burnout/contracts; Marcus = history/booking/continuity; Dante = money/ratings/sponsors; Rico = fans/Twitter/interpretation.
- Example depth (adapt to actual characters): Punk vs corporate image; Christian vs authenticity; Raven and control — use ONLY if those characters are in the story.

Rules:
- Use ONLY selected hosts for dialogue.
- NXT Unfiltered is EXCLUSIVE to NXT — do not treat as SmackDown/WCW programming.
- Discuss controversial tweets, morale, popularity, PLE fallout when relevant.
- TARGET RUNTIME: ~{tgt} minutes of spoken dialogue (~{min_chars}+ characters inside quotes, at least {min_lines} quoted host lines).
- Each numbered section needs at least {lps} back-and-forth exchanges (hosts interrupt, disagree, push back — like a real podcast).
- Sound human: contractions, reactions by name, not lecture notes.
- NO bullet lists in dialogue. Hosts must reference specific details from the story text.
- Length preset "{fields.get('length','Full Episode (~10 min)')}": hit the minute target — do not stop early.
"""

def _host_line(h,text):
 return f"{h['name']}:\n\"{text}\""

def _section_lines(hosts,fields,section_key,lines_per_section=5):
 if section_key=='Character Thought Process':
  return _section_lines_character_thought(hosts,fields)
 slot_map=_hosts_by_slot(hosts)
 wb=nxt_world_building_context()
 story=(fields.get('story_text','') or fields.get('main_story','') or 'the latest NXT chapter')[:500]
 chars=fields.get('main_characters','') or 'the main players'
 ple=fields.get('related_ple','') or 'the premium live event'
 tweets=(fields.get('controversial_tweets','') or '')[:300]
 morale=fields.get('morale_notes','') or 'backstage energy is mixed'
 pop=fields.get('popularity_changes','') or 'momentum shifted for a few names'
 banks={
  'Story Recap':[
   ('maya',f"Alright — here's the emotional spine of the week: {story[:220]}…"),
   ('marcus',f"And here's the booking spine — what they told us on-screen versus what they owed from last week."),
   ('rico',f"Fans didn't watch this like a spreadsheet — they watched it like a breakup or a coronation."),
   ('tasha',f"Media-wise, the clip that leaves the building is the clip that defines the week — not the match time."),
   ('dante',f"From a numbers standpoint, clarity at the end matters more than chaos in the middle."),
  ],
  'Deep Story Analysis':[
   ('maya',"When motives are visible, pain lands. When motives are fuzzy, fans feel manipulated."),
   ('marcus',"Show me the thread — not just the spot. Did this remember last week?"),
   ('serena',"Talent will give you everything if they trust the finish. If they don't, you hear it in the locker room first."),
   ('rico',"The timeline isn't wrong — it's early. But early still hurts if the payoff is late."),
   ('tasha',"Think third-act turn, not random shock — NXT sells cinematic, not disposable."),
  ],
  'Real-Life Connection':[
   ('maya',_host_real_life_line('maya',fields)),
   ('tasha',_host_real_life_line('tasha',fields)),
   ('serena',_host_real_life_line('serena',fields)),
   ('marcus',"This is not just about winning a match — this is about control of the narrative."),
   ('dante',_host_real_life_line('dante',fields)),
   ('rico',_host_real_life_line('rico',fields)),
  ],
  'World-Building Meaning':[
   ('tasha',f"NXT is not just a wrestling company here — it is a media machine. {wb['nxt'][:100]}…"),
   ('marcus',f"If WCW told this story it would feel like a fight. If SmackDown told it, celebrity heat. On NXT it feels like a movie."),
   ('dante',f"Popularity changes power — {wb['gm']} and the office know attention is leverage."),
   ('serena',f"Locker room culture on NXT: {wb['culture']}"),
   ('maya',"Champions here do not just hold belts — they carry company identity into press and fan imagination."),
  ],
  'Hidden Motivation':[
   ('maya',f"Under the surface of {chars}: someone is protecting ego, someone is chasing relevance."),
   ('serena',"Hidden motivation is often respect — talent will accept pain before they accept being ignored."),
   ('marcus',"Booking motivation and character motivation must align or fans smell a reset."),
   ('tasha',"Sometimes the hidden play is brand — who looks like the face of NXT on Monday."),
   ('rico',"Fans will psychoanalyze motives in replies — give them a story worth analyzing."),
  ],
  'What This Says About The Company':[
   ('dante',f"NXT is betting that emotional conflict sells longer than a clean finish — that is a business choice."),
   ('tasha',"The company message to partners: we can package chaos into prestige if the press sentence is clear."),
   ('serena',f"What it says to talent: {wb['gm']}'s office sets tone — respect flows downhill."),
   ('marcus',"It says NXT wants a long thread, not a one-week spike."),
   ('maya',"It says this brand believes feelings are as marketable as championships."),
  ],
  'How Fans Might Interpret It':[
   ('rico',"Half the audience will call it genius — half will call it bait. Both are engagement."),
   ('maya',"Sympathy fans vs justice fans — same moment, two interpretations."),
   ('tasha',"Clip culture will flatten the story — fans only see ten seconds of a twenty-minute emotion."),
   ('marcus',"Smart fans track continuity — casual fans track vibes."),
   ('dante',"Interpretation drives tickets when the argument is real."),
  ],
  'What The Locker Room Might Think':[
   ('serena',"Veterans ask if the finish protected workers or protected the office."),
   ('maya',"Younger talent watch who got the emotional close-up — that is currency backstage."),
   ('marcus',"If the room is quiet after, the story landed. If it is loud, someone feels disrespected."),
   ('rico',"Fans mimic locker room energy online within the hour."),
   ('tasha',"Press asks talent smiling questions while the room still feels the sting."),
  ],
  'What Sponsors Might Worry About':[
   ('tasha',"Partners love buzz until the headline needs explaining in one clean line."),
   ('dante',"Sponsor confidence drops when controversy looks toxic, not theatrical."),
   ('marcus',"If the story cannot be summarized, media buyers get nervous."),
   ('maya',"Humanize talent in press — sponsors fear chaos without empathy."),
   ('rico',"Fan outrage is inventory — sponsor panic is a liability."),
  ],
  'What This Sets Up Emotionally':[
   ('maya',f"This sets up grief, pride, or a snap — someone should apologize or explode next week."),
   ('marcus',"Emotional setup only works if next week remembers the trigger."),
   ('rico',"Fans will tune in to see if sympathy was earned or assigned."),
   ('serena',"Morale next week: who gets the respect bump on the card?"),
   ('tasha',"Press will want a redemption image or a villain portrait — plan both."),
  ],
  'Character Psychology':[
   ('maya',f"Who gained sympathy, who lost trust — and did {chars} earn either?"),
   ('marcus',"Psychology has to match booking history. A heel turn without seeds reads like a reset."),
   ('maya',"Let us sit with what that moment actually cost them — not just the bump."),
   ('rico',"Fan investment is emotional stock — you can't rug-pull every other week."),
   ('serena',"Respect isn't a storyline — but disrespect without purpose kills morale."),
  ],
  'Controversial Tweet Breakdown':[
   ('rico',tweets or "No major tweets flagged yet — but fan accounts clip within minutes."),
   ('tasha',"If it's trending, partners notice. If it's trending for the wrong reason, partners panic."),
   ('marcus',"Screenshots aren't proof of truth — but they are proof of narrative confusion."),
   ('rico',"Quote tweets are the real referendum — likes are cheap."),
   ('maya',"Cruelty online still reflects real feelings in the building — don't dismiss it."),
  ],
  'Morale Watch':[
   ('serena',morale),
   ('maya',"Morale and story quality are married — bad finishes leak into the next promo."),
   ('marcus',"If creative keeps teasing without paying, you get silence, not noise."),
   ('serena',"Athletes will perform hurt — they won't perform disrespected forever."),
   ('rico',"Fans can smell when the locker room isn't all-in — it shows in the eyes."),
  ],
  'Popularity Movement':[
   ('dante',pop),
   ('tasha',"Buzz and affection diverge all the time — especially for effective heels."),
   ('rico',"Popularity online isn't the same as being loved — sometimes it's being hated correctly."),
   ('dante',"Attention is inventory — spend it on coherent stories."),
   ('marcus',"Heat without direction is just noise — booking has to aim it."),
  ],
  'Episode / PLE Fallout':[
   ('marcus',fields.get('ple_fallout','') or f"After {ple}, someone should look stronger and someone should look cornered."),
   ('maya',"Fallout isn't recap — it's consequence. Who's damaged walking out?"),
   ('dante',"PLE bumps can lift quarterly narratives if the office commits on TV the next week."),
   ('rico',"If fallout answers nothing, fans treat the PLE like a standalone movie — bad for weekly TV."),
   ('tasha',"Press cycles love a clean image after chaos — give them a sentence, not a shrug."),
  ],
  'What Made Sense':[
   ('marcus',"Threads that remembered last week — earned nearfalls, logical interference."),
   ('maya',"Emotional beats that paid off — sympathy earned, not assigned."),
   ('dante',"Business logic when the story was clear enough to sell tickets."),
   ('serena',"Talent looked protected in the finish — not embarrassed for cheap heat."),
   ('rico',"Fans defended the angle in replies — that's rare and valuable."),
  ],
  'What Did Not Make Sense':[
   ('marcus',"Dropped threads, rushed turns, interference without setup."),
   ('rico',"If the live crowd went quiet, that's data — not 'haters.'"),
   ('maya',"Disrespect without story purpose reads like cruelty, not drama."),
   ('serena',"When the locker room doesn't buy it, the audience won't for long either."),
   ('tasha',"If press can't explain the finish in one line, the bit isn't ready for mainstream."),
  ],
  'Business / Viewership / Attendance Impact':[
   ('dante',"Emotion is a line item when it's real — projected buzz helps NXT prestige if the ending was clear."),
   ('tasha',"Sponsor confidence tracks narrative clarity — controversy helps until it doesn't."),
   ('marcus',"Attendance follows investment — not just match quality."),
   ('rico',"Clips drive discovery — but discovery without payoff churns viewers."),
   ('maya',"Fans return for unresolved feelings — not just moves."),
  ],
  'Twitter Reaction Prediction':[
   ('rico',"Within the hour: hot takes, clip farming, debate posts, and at least one viral wrong take."),
   ('tasha',"Press-friendly accounts will frame it as 'shocking' — fan editors will frame it as 'predictable.'"),
   ('marcus',"Continuity cops will post side-by-side receipts — fair or not."),
   ('maya',"Sympathy posts for whoever looked betrayed — cruelty posts for whoever caused it."),
   ('dante',"Engagement spikes — the office has to convert spikes into next-week viewership."),
  ],
  'Locker Room Reaction':[
   ('serena',"Talent reacts to whether the finish felt earned — not whether Twitter liked it."),
   ('marcus',"If veterans aren't talking about it backstage, it didn't move the needle."),
   ('rico',"Younger talent watch social — but they still take cues from the room."),
   ('maya',"Emotional honesty in promos next week will tell you how they felt."),
   ('serena',"Protect the worker — critique the booking."),
  ],
  'Sponsor / Media Reaction':[
   ('tasha',"Controversy is useful until partners ask questions — then you need a clean sentence."),
   ('dante',"Brand-safe doesn't mean boring — it means intentional."),
   ('marcus',"If media can't summarize the story, sponsors get nervous."),
   ('rico',"Fan outrage can be an asset — sponsor panic is a liability."),
   ('maya',"Humanize the talent in press — don't let the internet narrate them."),
  ],
  'What Needs Follow-Up':[
   ('marcus',"Promises on-screen must be paid or explained — otherwise it's a dropped thread."),
   ('maya',"Emotional questions left open — answer them or fans feel played."),
   ('rico',"If fans are asking 'why' in replies, that's your follow-up list."),
   ('serena',"Morale follow-up: who needs respect on the next show?"),
   ('dante',"Business follow-up: convert heat into a next-week hook."),
  ],
  'Next Week Predictions':[
   ('rico',"Fans tune in if something feels unresolved — emotionally, not just statistically."),
   ('marcus',"Predictable isn't bad if the payoff is satisfying — unpredictable without logic is."),
   ('maya',"Who's most likely to snap — and who should apologize on-screen?"),
   ('tasha',"Press will want a soundbite — give them a story, not a shrug."),
   ('dante',"If they advertise conflict honestly, numbers should hold."),
  ],
  'Closing Thoughts':[
   ('maya',"NXT Unfiltered signs off — story first, headlines second."),
   ('marcus',"Show me the thread next week — we'll be watching."),
   ('rico',"The timeline isn't wrong — it's just early."),
   ('tasha',"If it's not trending by tomorrow, the story isn't finished."),
   ('dante',"Emotion is a line item — spend it wisely."),
  ],
 }
 bank=banks.get(section_key,[('maya',section_key)])
 spec=get_nxt_unfiltered_length_spec(fields.get('length','Full Episode (~10 min)'))
 n=max(2,int(spec.get('lines_per_section',5)))
 out=[]
 gen=_cycle_hosts(hosts)
 for i in range(n):
  slot,txt=bank[i%len(bank)]
  h=slot_map.get(slot) or next(gen)
  out.append(_host_line(h,humanize_dialogue_for_tts(txt)))
 return out

def rule_based_nxt_unfiltered(fields,hosts):
 title=fields.get('episode_title') or f"NXT Unfiltered: {fields.get('main_story','NXT Story Breakdown')[:60]}"
 lineup=', '.join(h['name'] for h in hosts)
 beats=_story_beats_from_fields(fields)
 lines=[f'Episode Title:\n"{title}"',f'Host Lineup:\n{lineup}','','Opening Intro','']
 order=['maya','marcus','tasha','serena','dante','rico']
 for slot in order:
  h=next((x for x in hosts if x.get('host_slot')==slot),None)
  if not h: continue
  intro=HOST_SLOT_INTROS.get(slot,'')
  if slot=='maya' and fields.get('main_story'): intro=f"Welcome to NXT Unfiltered. Tonight we're unpacking who left damaged in {fields.get('main_story')} — not just who won."
  if intro and h in hosts: lines.append(_host_line(h,humanize_dialogue_for_tts(intro)))
 for slot in order:
  h=next((x for x in hosts if x.get('host_slot')==slot),None)
  if h and h in hosts:
   lines.append(_host_line(h,humanize_dialogue_for_tts(f"Honestly — I'm looking at {fields.get('main_story','this week')[:80]} and we've got a lot to say.")))
 beat_i=0
 for sec in NXT_UF_SCRIPT_SECTIONS:
  lines.append(''); lines.append(sec); lines.append('')
  sec_lines=_section_lines(hosts,fields,sec)
  if beats and sec in ('Story Recap','Deep Story Analysis','Real-Life Connection','Character Thought Process'):
   slot_map=_hosts_by_slot(hosts)
   for slot in ('maya','marcus','rico','tasha'):
    if beat_i>=len(beats): break
    h=slot_map.get(slot) or hosts[beat_i%len(hosts)]
    b=beats[beat_i]; beat_i+=1
    sec_lines.insert(min(1,len(sec_lines)),_host_line(h,humanize_dialogue_for_tts(f"From the actual week: {b[:240]}…")))
  lines.extend(sec_lines)
 return expand_script_to_target_length('\n'.join(lines),fields,hosts)

def generate_nxt_unfiltered_episode(fields,host_names):
 hosts=[get_nxt_unfiltered_host(n) for n in host_names]
 ensure_ai_mode_prefs()
 if not should_use_openai_ai():
  st.session_state.nxt_uf_last_ai_error=None
  note='Built-in script engine (no OpenAI charge).'
  if st.session_state.get('openai_quota_exceeded'):
   note='Built-in script — OpenAI quota exceeded; add billing to use AI again.'
  elif not get_openai_api_key():
   note='Built-in script — add an API key and disable built-in mode for AI scripts.'
  return rule_based_nxt_unfiltered(fields,hosts),False,note
 prompt=build_nxt_unfiltered_prompt(fields,hosts)
 out=ai(prompt,max_output=20000,temperature=0.72)
 if out and not str(out).startswith('AI error'):
  st.session_state.nxt_uf_last_ai_error=None
  script=expand_script_to_target_length(out.strip(),fields,hosts)
  return script,True,''
 err=str(out or 'AI returned empty response.')
 if err.startswith('AI error: '): err=err[10:]
 script=rule_based_nxt_unfiltered(fields,hosts)
 if st.session_state.get('openai_quota_exceeded'):
  st.session_state.bfg_force_builtin_ai=True
  st.session_state.nxt_uf_last_ai_error=None
  return script,False,'Built-in script — OpenAI billing limit hit; toggle restored built-in mode.'
 st.session_state.nxt_uf_last_ai_error=err
 return script,False,f'Built-in script — {err}'

def save_nxt_unfiltered_episode(fields,script,ai_flag,host_names):
 hc=fields.get('host_count_label') or f"{len(host_names)} Hosts"
 rec={
  'id':len(st.session_state.get('nxt_unfiltered_episodes',[]))+1,'week':fields.get('week',st.session_state.week),'company':'NXT',
  'episode_title':fields.get('episode_title',''),'host_lineup':host_names,'host_count':len(host_names),'host_count_label':hc,
  'tone':fields.get('tone',''),'length':fields.get('length',''),'related_show':fields.get('related_show',''),
  'related_ple':fields.get('related_ple',''),'related_rivalry':fields.get('main_story',''),'main_story':fields.get('main_story',''),
  'main_characters':fields.get('main_characters',''),
  'controversial_tweets':fields.get('controversial_tweets',''),'morale_analysis':fields.get('morale_notes',''),
  'popularity_analysis':fields.get('popularity_changes',''),'ple_fallout':fields.get('ple_fallout',''),
  'user_notes':fields.get('user_notes',''),'story_text':fields.get('story_text',''),'script':script,
  'ai_generated':ai_flag,'label':'AI' if ai_flag else 'Built-in','audio_path':fields.get('audio_path',''),'effects_applied':False,
  'buzz_preview':calc_nxt_unfiltered_buzz(fields,host_names),
 }
 st.session_state.nxt_unfiltered_episodes.insert(0,rec)
 st.session_state.last_nxt_unfiltered=rec
 return rec

def calc_nxt_unfiltered_buzz(fields,host_names):
 heat=5+len(host_names)
 if fields.get('controversial_tweets','').strip(): heat+=8
 if fields.get('ple_fallout','').strip(): heat+=6
 if fields.get('length')=='Deep Dive': heat+=4
 return {'rivalry_heat':min(15,heat),'twitter_buzz':min(20,6+heat),'fan_investment':min(12,4+heat//2),'viewership':min(15,5+heat//2),'nxt_prestige':min(8,2+heat//3),'sponsor_confidence':min(10,2+heat//4)}

def apply_nxt_unfiltered_buzz(rec):
 eff=rec.get('buzz_preview') or calc_nxt_unfiltered_buzz(rec,rec.get('host_lineup',[]))
 story=rec.get('main_story','') or rec.get('related_rivalry','')
 for r in st.session_state.rivalries:
  if r.get('company')=='NXT' and (story and story in r.get('name','') or any(n.strip() in r.get('wrestlers',[]) for n in (rec.get('main_characters','') or '').split(',') if n.strip())):
   r['heat']=min(100,int(r.get('heat',50))+eff['rivalry_heat'])
 for n in (rec.get('main_characters','') or '').split(','):
  n=n.strip()
  if not n: continue
  w=find(n)
  if w and w.get('company')=='NXT':
   w['fan_investment']=min(100,w.get('fan_investment',50)+eff['fan_investment'])
   w['twitter_buzz']=min(100,w.get('twitter_buzz',0)+eff['twitter_buzz'])
   w['sponsor_trust']=min(100,w.get('sponsor_trust',60)+eff['sponsor_confidence'])
   w['momentum']=min(100,w.get('momentum',50)+eff.get('viewership',0)//3)
 prof=st.session_state.company_profiles.setdefault('NXT',{})
 prof['prestige']=min(100,int(prof.get('prestige',85))+eff['nxt_prestige'])
 prof['media_confidence']=min(100,int(prof.get('media_confidence',70))+eff['sponsor_confidence'])
 st.session_state.news_feed.insert(0,f"NXT Unfiltered: {rec.get('episode_title','Episode')} — buzz applied (rivalry heat, Twitter, fan investment, viewership, NXT prestige, sponsor/media confidence).")
 rec['effects_applied']=True
 st.session_state.last_nxt_unfiltered=rec

def ensure_nxt_uf_voice_prefs():
 if 'nxt_uf_voice_mode' not in st.session_state:
  st.session_state.nxt_uf_voice_mode='free_edge'
 if 'nxt_uf_premium_cost_ok' not in st.session_state:
  st.session_state.nxt_uf_premium_cost_ok=False

def get_nxt_uf_voice_mode():
 ensure_nxt_uf_voice_prefs()
 return st.session_state.get('nxt_uf_voice_mode','free_edge')

def get_user_premium_openai_key():
 return (st.session_state.get('nxt_uf_user_openai_key') or '').strip()

def get_user_premium_elevenlabs_key():
 return (st.session_state.get('nxt_uf_user_elevenlabs_key') or '').strip()

def premium_voice_ready():
 mode=get_nxt_uf_voice_mode()
 if mode=='premium_openai':
  return bool(get_user_premium_openai_key())
 if mode=='premium_elevenlabs':
  return bool(get_user_premium_elevenlabs_key())
 return False

def render_browser_tts_player(script,element_id='bfg_browser_tts'):
 """Free in-browser speech (no API) — user clicks play in their browser."""
 segs=parse_podcast_dialogue(script,[])
 if not segs:
  st.caption('Generate a script first for browser voice.')
  return
 lines=json.dumps([{'speaker':a,'text':b} for a,b in segs[:80]])
 html=f"""<div id="{element_id}"><button onclick="bfgSpeak()" style="padding:10px 18px;border-radius:10px;background:#b026ff;color:#fff;font-weight:700;border:none;cursor:pointer">Play free browser voice</button>
 <span id="{element_id}_status" style="margin-left:12px;color:#ccc"></span></div>
 <script>
 const bfgLines={lines};
 let bfgIdx=0;
 function bfgSpeak(){{
  if(!window.speechSynthesis){{document.getElementById('{element_id}_status').textContent='Browser TTS not supported';return;}}
  if(bfgIdx>=bfgLines.length){{bfgIdx=0;document.getElementById('{element_id}_status').textContent='Done';return;}}
  const u=new SpeechSynthesisUtterance(bfgLines[bfgIdx].text);
  u.rate=0.95; u.onend=()=>{{bfgIdx++; setTimeout(bfgSpeak,400);}};
  document.getElementById('{element_id}_status').textContent='Speaking: '+bfgLines[bfgIdx].speaker;
  speechSynthesis.speak(u);
 }}
 </script>"""
 st.components.v1.html(html,height=80)

def synthesize_line_elevenlabs(text,voice_id,path,api_key):
 try:
  import urllib.request
  payload=json.dumps({'text':humanize_dialogue_for_tts(text)[:2500],'model_id':'eleven_multilingual_v2','voice_settings':{'stability':0.45,'similarity_boost':0.75}}).encode('utf-8')
  req=urllib.request.Request(f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',data=payload,headers={'xi-api-key':api_key,'Content-Type':'application/json'},method='POST')
  with urllib.request.urlopen(req,timeout=120) as resp:
   Path(path).write_bytes(resp.read())
  return Path(path).exists() and Path(path).stat().st_size>200
 except Exception:
  return False

def get_tts_settings():
 ensure_nxt_uf_voice_prefs()
 cfg={}
 try:
  raw=st.secrets.get('tts',{})
  if isinstance(raw,dict): cfg=raw
 except Exception: pass
 enabled=cfg.get('enabled',True)
 mode=get_nxt_uf_voice_mode()
 if mode=='free_edge' or mode=='free_browser':
  return {'enabled':enabled,'provider':'edge','prefer_openai':False,'mode':mode}
 if mode=='premium_openai' and premium_voice_ready() and st.session_state.get('nxt_uf_premium_cost_ok'):
  return {'enabled':enabled,'provider':'openai','prefer_openai':True,'mode':mode,'user_key':get_user_premium_openai_key()}
 if mode=='premium_elevenlabs' and premium_voice_ready() and st.session_state.get('nxt_uf_premium_cost_ok'):
  return {'enabled':enabled,'provider':'elevenlabs','prefer_openai':False,'mode':mode,'user_key':get_user_premium_elevenlabs_key()}
 return {'enabled':enabled,'provider':'edge','prefer_openai':False,'mode':'free_edge'}

def speed_to_edge_rate(speed):
 pct=int((float(speed or 1.0)-1.0)*100)
 pct=max(-35,min(45,pct))
 return f'{pct:+d}%'

def parse_podcast_dialogue(script,hosts):
 host_map={h['name'].strip().lower(): h for h in (hosts or []) if h.get('name')}
 segs=[]
 if not (script or '').strip(): return segs
 for m in re.finditer(r'^([A-Za-z][^\n:]{1,42}):\s*\n?"([^"]{3,2000})"', script,re.M):
  segs.append((m.group(1).strip(),humanize_dialogue_for_tts(m.group(2).strip())))
 for m in re.finditer(r'^([A-Za-z][^\n:]{1,42}):\s*"([^"]{3,2000})"', script,re.M):
  t=(m.group(1).strip(),humanize_dialogue_for_tts(m.group(2).strip()))
  if t not in segs: segs.append(t)
 if segs: return segs[:120]
 hs=[h['name'] for h in (hosts or []) if h.get('name')]
 clean=re.sub(r'^(Episode Title|Host Lineup|Opening Intro|Story Recap|Deep Story Analysis|Real-Life Connection|Character Thought Process|World-Building Meaning|Hidden Motivation|What This Says About The Company|Character Psychology|How Fans Might Interpret It|What The Locker Room Might Think|What Sponsors Might Worry About|What This Sets Up Emotionally|Controversial Tweet Breakdown|Morale Watch|Popularity Movement|Episode / PLE Fallout|What Made Sense|What Did Not Make Sense|Business / Viewership / Attendance Impact|Twitter Reaction Prediction|Locker Room Reaction|Sponsor / Media Reaction|What Needs Follow-Up|Next Week Predictions|Closing Thoughts|Extended Roundtable)\s*$','',script,flags=re.M|re.I)
 chunks=[p.strip() for p in re.split(r'\n\n+',clean) if len(p.strip())>45 and not p.strip().endswith(':')]
 for i,ch in enumerate(chunks[:90]):
  nm=hs[i%len(hs)] if hs else 'Host'
  segs.append((nm,humanize_dialogue_for_tts(ch[:1200])))
 return segs[:120]

def _voice_for_host(host_name,host_obj=None):
 if host_name in HOST_EDGE_VOICE: return HOST_EDGE_VOICE[host_name]
 style=(host_obj or {}).get('tts_voice','neutral')
 return EDGE_TTS_VOICE_MAP.get(style,EDGE_TTS_VOICE_MAP['neutral'])

def _openai_voice_for_host(host_obj):
 style=(host_obj or {}).get('tts_voice','neutral')
 return OPENAI_TTS_VOICE_MAP.get(style,OPENAI_TTS_VOICE_MAP['neutral'])

async def _edge_save_mp3(text,voice,path,rate='+0%'):
 import edge_tts
 comm=edge_tts.Communicate(text[:2000],voice,rate=rate)
 await comm.save(str(path))

def resolve_audio_path(path):
 if not path: return ''
 p=Path(path)
 if not p.is_absolute():
  p=(PROJECT_ROOT/p).resolve()
 return str(p) if p.exists() else str(p)

def synthesize_line_edge(text,voice,path,speed=1.0):
 try:
  asyncio.run(_edge_save_mp3(text,voice,path,speed_to_edge_rate(speed)))
  return Path(path).exists() and Path(path).stat().st_size>200
 except Exception as e:
  st.session_state.nxt_uf_last_tts_error=str(e)
  return False

def synthesize_line_openai(text,voice,path,api_key,speed=1.0):
 try:
  from openai import OpenAI
  sp=max(0.82,min(1.08,float(speed or 1.0)))
  model=OPENAI_TTS_MODEL if 'OPENAI_TTS_MODEL' in globals() else 'tts-1-hd'
  resp=OpenAI(api_key=api_key).audio.speech.create(model=model,voice=voice,input=humanize_dialogue_for_tts(text)[:4096],speed=sp)
  resp.stream_to_file(str(path))
  return Path(path).exists() and Path(path).stat().st_size>200
 except Exception: return False

def merge_audio_mp3(paths,out_path):
 paths=[p for p in paths if p and Path(p).exists()]
 if not paths: return None
 out_path=Path(out_path)
 out_path.parent.mkdir(parents=True,exist_ok=True)
 if len(paths)==1:
  shutil.copy2(paths[0],out_path)
  return str(out_path)
 ffmpeg=find_ffmpeg()
 if ffmpeg:
  try:
   lst=out_path.parent/'concat_list.txt'
   lst.write_text(''.join(f"file '{Path(p).resolve()}'\n" for p in paths),encoding='utf-8')
   subprocess.run([ffmpeg,'-y','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(out_path)],check=True,capture_output=True,timeout=600)
   if out_path.exists() and out_path.stat().st_size>500: return str(out_path)
  except Exception: pass
 try:
  from pydub import AudioSegment
  mix=AudioSegment.empty()
  gap_ms=int(globals().get('PODCAST_TTS_PAUSE_MS',720))
  gap=AudioSegment.silent(duration=gap_ms)
  for p in paths:
   mix+=AudioSegment.from_file(p)+gap
  mix.export(out_path,format='mp3')
  if out_path.exists() and out_path.stat().st_size>500: return str(out_path)
 except Exception: pass
 return None

def synthesize_episode_single_file(segments,hosts,out_path,api_key=None):
 lines=[]
 for speaker,text in segments:
  lines.append(f"{speaker}:\n{humanize_dialogue_for_tts(text)}")
 full='\n\n'.join(lines)[:14000]
 h=(hosts or [{}])[0]
 out_path=Path(out_path)
 out_path.parent.mkdir(parents=True,exist_ok=True)
 if api_key:
  if synthesize_line_openai(full,_openai_voice_for_host(h),out_path,api_key,h.get('tts_speed',1.0)):
   return str(out_path),'openai'
 if synthesize_line_edge(full,_voice_for_host(h.get('name','Host'),h),out_path,h.get('tts_speed',1.0)):
  return str(out_path),'edge'
 return None,''

def try_nxt_unfiltered_tts(script,hosts,max_segments=None):
 """Build MP3 from script. max_segments caps lines for a quick preview (~2–3 min)."""
 st.session_state.nxt_uf_last_tts_error=None
 settings=get_tts_settings()
 if not settings.get('enabled',True):
  return None,'TTS is disabled in Streamlit secrets [tts] (set enabled = true).'
 if settings.get('mode')=='free_browser':
  return None,'Browser voice mode: use **Play free browser voice** below (no MP3 file). Switch voice mode to **Edge TTS** to get a player here.'
 segments=parse_podcast_dialogue(script,hosts)
 if not segments:
  return None,'No dialogue found in script — generate the episode first. Host lines must look like: Host Name: then quoted dialogue.'
 total=len(segments)
 if max_segments:
  segments=segments[:int(max_segments)]
 host_map={h['name'].strip().lower(): h for h in (hosts or []) if h.get('name')}
 api_key=settings.get('user_key') or get_openai_api_key()
 use_openai=settings.get('prefer_openai') and bool(api_key)
 use_eleven=settings.get('provider')=='elevenlabs' and bool(settings.get('user_key'))
 ep_id=st.session_state.get('last_nxt_unfiltered',{}).get('id',st.session_state.week)
 out_dir=NXT_UNFILTERED_AUDIO_DIR/f'ep_{ep_id}_{random.randint(1000,99999)}'
 out_dir.mkdir(parents=True,exist_ok=True)
 if len(segments)>1 and not find_ffmpeg():
  single,prov=synthesize_episode_single_file(segments,hosts,out_dir/'episode.mp3',api_key if use_openai else None)
  if single:
   return single,f'Podcast audio ready ({prov}). For per-host voices: brew install ffmpeg, then regenerate.'
  return None,'Audio failed. Run: pip install edge-tts'
 part_paths=[]
 provider='openai' if use_openai else 'edge'
 cap_note=f' (preview: first {len(segments)} of {total} lines)' if max_segments and len(segments)<total else ''
 prog=st.progress(0.0) if len(segments)>8 else None
 for idx,(speaker,text) in enumerate(segments):
  if prog: prog.progress(min(1.0,(idx+1)/max(1,len(segments))))
  h=host_map.get(speaker.lower()) or (hosts[idx%len(hosts)] if hosts else {})
  part=out_dir/f'{idx:03d}.mp3'
  ok=False
  line_text=humanize_dialogue_for_tts(text)
  if use_eleven:
   vid=str(h.get('elevenlabs_voice_id') or '21m00Tcm4TlvDq8ikWAM')
   ok=synthesize_line_elevenlabs(line_text,vid,part,settings.get('user_key'))
   provider='elevenlabs'
  if use_openai:
   ok=synthesize_line_openai(line_text,_openai_voice_for_host(h),part,api_key,h.get('tts_speed',1.0))
   provider='openai'
  if not ok:
   provider='edge'
   ok=synthesize_line_edge(line_text,_voice_for_host(speaker,h),part,h.get('tts_speed',1.0))
  if ok: part_paths.append(str(part))
 if not part_paths:
  single,prov=synthesize_episode_single_file(segments,hosts,out_dir/'episode_single.mp3',api_key if use_openai else None)
  if single: return single,f'Podcast audio ready ({prov}). Press play below.'
  return None,'Audio generation failed. Run: pip install edge-tts — optional OPENAI_API_KEY for higher quality.'
 merged=merge_audio_mp3(part_paths,out_dir/'episode.mp3')
 if not merged:
  single,prov=synthesize_episode_single_file(segments,hosts,out_dir/'episode_single.mp3',api_key if use_openai else None)
  if single:
   hint='' if find_ffmpeg() else ' (Install ffmpeg for separate host voices: brew install ffmpeg)'
   return single,f'Podcast audio ready ({prov} full episode){hint}. Press play below.'
  if part_paths: return part_paths[0],f'Playing first segment only — install ffmpeg to merge all {len(part_paths)} parts.'
  return None,'Could not build audio file.'
 est_min=estimate_podcast_runtime_minutes(script)
 merged=resolve_audio_path(merged)
 err=st.session_state.get('nxt_uf_last_tts_error')
 if err:
  return merged,f'Podcast audio ready ({provider}){cap_note}. Press **Play** on the player below. (Note: {err[:120]})'
 return merged,f'Podcast audio ready ({provider}, {len(part_paths)} lines){cap_note}. Press **Play** on the player below — volume up on your device.'

def ensure_data_dirs():
 UNIVERSE_DATA_DIR.mkdir(parents=True,exist_ok=True)
 Path('data/sessions').mkdir(parents=True,exist_ok=True)
 Path('data/audio/nxt_unfiltered').mkdir(parents=True,exist_ok=True)
 for folder in picture_folder_map().values():
  Path(folder).mkdir(parents=True,exist_ok=True)
 purge_invalid_asset_files()

def init():
 ensure_data_dirs()
 if 'roster' not in st.session_state:
  st.session_state.roster=[dict(w) for w in ROSTER if w['name'] not in REMOVED_WRESTLERS|REMOVED_TAG_TEAMS]
 defaults={'champions':json.loads(json.dumps(CHAMPIONS)),'title_prestige':{},'champion_meta':{},'champion_history':[],'title_defense_history':[],'bank':STARTING_BUDGET*3,'week':0,'month':1,'year':1,'weekly_history':[],'twitter_posts':[],'schedule_calendar':[],'calendar_locked':False,'calendar_ai_notes':[],'cal_lock_confirm':False,'cal_reset_confirm':False,'random_event_history':[],'news_feed':[],'power_rankings':[],'previous_power_rankings':[],'power_ranking_history':[],'character_bible':json.loads(json.dumps(CHARACTER_BIBLE)),'yearly_attractions':json.loads(json.dumps(ATTRACTIONS))[:6],'attractions_locked':False,'attraction_year':1,'attraction_history':[],'last_profit_loss':0,'last_money_generated':0,'last_money_lost':0,'last_transportation_cost':0,'last_medical_cost':0,'last_ad_money':0,'last_pledge_money':0,'last_hotel_cost':0,'last_hotel_savings':0,'last_transport_savings':0,'saved_show':None,'booking_mode':'Match Card Mode','ai_booked_show':False,'show_user_edited':False,'long_story_draft':'','book_show_drafts':{},'book_show_archive':{},'last_story_analysis':None,'departed':[],'rivalries':[],'test_event_preview':None,'company_budgets':{c:STARTING_BUDGET for c in PLAYABLE},'company_finance':{},'finance_ledger':[],'show_finance_reports':[],'factions':{'NXT':[],'SmackDown':[],'WCW':WCW_FACTIONS},'custom_tag_teams':{},'breakup_history':[],'former_tag_teams':{c:[] for c in PLAYABLE},'film_projects':[],'logistics_reports':[],'cameo_library':[],'last_cameo':None,'team_profiles':{},'debut_history':[],'debut_warnings':[],'rankings_include_not_debuted':False,'confirmed_story_debuts':[],'free_agency_pool':[],'negotiation_history':[],'contract_warnings':[],'exclusive_activity_history':[],'exclusive_generated_ideas':[],'exclusive_violations':[],'nxt_unfiltered_hosts':json.loads(json.dumps(_default_nxt_unfiltered_hosts())),'nxt_unfiltered_episodes':[],'nxt_unfiltered_draft':{},'last_nxt_unfiltered':None,'podcast_hosts_booking_enabled':False,'week_progress':default_week_progress(),'player_assignments':{c:'' for c in PLAYABLE}, 'pending_trades':[],'logged_in':False,'session_id':'','game_name':'','invite_code':'','nxt_uf_voice_mode':'free_edge','nxt_uf_premium_cost_ok':False,'money_meter_flash':[],'finance_opening_applied':False,'weekly_performance_index':{},'company_crisis':{c:crisis.default_crisis_rec() for c in PLAYABLE},'bidding_wars':[],'brand_loyalty_history':[],'descriptor_recent':[], 'twitter_recruitment_history':[],'twitter_manual_gm_response':False,'storylines':[],'sponsor_objectives':[],'gate_screen':'intro'}
 for k,v in defaults.items():
  if k not in st.session_state: st.session_state[k]=v
 if not st.session_state.power_rankings: update_rank()

def main():
 register_ui_page_helpers()
 init()
 ensure_ai_mode_prefs()
 ensure_extended_state()
 ensure_multiplayer_state()
 if st.session_state.get('logged_in') and not st.session_state.get('_universe_loaded'):
  try:
   load_universe_from_disk()
  except Exception as ex:
   st.error(f'Could not load saved universe: {ex}')
   st.session_state._universe_loaded=True
 storylines.ensure_storyline_state()
 sponsor_obj.ensure_sponsor_objectives(COMPANIES)
 autosave.ensure_autosave_state()
 if not st.session_state.get('logged_in'):
  gate=st.session_state.get('gate_screen','intro')
  if gate=='tutorial':
   ui_pages.render_tutorial_page()
   st.stop()
  if gate=='continue':
   ui_pages.render_continue_saved()
   st.stop()
  if gate=='login':
   render_login_screen()
   st.stop()
  ui_pages.render_game_intro()
  st.stop()
 render_title_bar()
 render_finance_bar()
 nav=render_sidebar()
 inject_brand_theme()
 return nav

def register_ui_page_helpers():
 ui_pages.register_helpers(
  database_url_configured=database_configured,
  supabase_cloud_active=supabase_cloud_active,
  render_storage_status_banner=render_storage_status_banner,
  bfg_card=bfg_card,
  UNIVERSE_DATA_DIR=UNIVERSE_DATA_DIR,
  sync_session_from_storage=sync_session_from_storage,
  render_page_shell=render_page_shell,
  can_edit_company=can_edit_company,
  touch_universe_meta=touch_universe_meta,
  save_universe=save_universe,
  COMPANIES=COMPANIES,
  money=money,
  render_money_meter_multi=render_money_meter_multi,
  get_session_id=get_session_id,
  next_bookable_week=next_bookable_week,
  all_companies_week_completed=all_companies_week_completed,
  get_assigned_gm_display=get_assigned_gm_display,
  is_admin=is_admin,
  try_advance_shared_week_after_show=try_advance_shared_week_after_show,
  force_advance_shared_week=force_advance_shared_week,
  admin_unlock_company_week=admin_unlock_company_week,
 )

register_ui_page_helpers()
page=main()
# Theme already applied in main() after sidebar; refresh if page brand tabs change active_brand later
if st.session_state.get('active_brand') in PLAYABLE:
 inject_brand_theme()

if page=='Dashboard':
 render_page_shell('Dashboard',subtitle='Universe overview — NXT · SmackDown · WCW share one week and separate $150M banks.',show_meter=True)
 col_left,col_right=st.columns(2)
 with col_left:
  with bfg_card('Company Overview'):
   st.write('Main companies: **NXT**, **SmackDown**, **WCW**')
   st.write(f'**Shared universe week:** {st.session_state.week} · Next bookable: **Week {next_bookable_week()}**')
   st.write('All three GMs must complete their weekly show before the universe advances (Admin can force advance).')
   st.write(f'NXT payroll: **{money(sum(w["salary"] for w in roster("NXT")))}**')
  with bfg_card('Last Show Viewership (by brand)'):
   for co in PLAYABLE:
    lh=next((h for h in reversed(st.session_state.weekly_history) if h.get('company')==co),None)
    if lh: st.write(f"**{co}:** {lh.get('show_name','')} — **{lh.get('episode_rating',lh.get('final_rating','—'))}/10** · **{int(lh.get('viewership',0)):,}** viewers")
    else: st.write(f"**{co}:** No completed show yet · baseline {COMPANY_VIEWERSHIP_BASELINE.get(co,0):,}")
  with bfg_card('PPV Schedule'):
   for m,e,ppv_br in PPVS: st.write(f'**{m}** — {e} ({ppv_br})')
 with col_right:
  with bfg_card('News Feed'):
   if st.session_state.news_feed[:12]:
    for n in st.session_state.news_feed[:12]: st.write('• '+n)
   else: st.info('No news yet.')
  with bfg_card('Top 10 Power Rankings'):
   for r in st.session_state.power_rankings[:10]: st.write(f"**#{r['rank']} {r['name']}** — {r['score']} ({r['movement']})")
  dw=get_debut_followup_warnings()
  if dw:
   with bfg_card('Debut Follow-Up Warnings'):
    for x in dw[:6]: st.write('• '+x)
  cw=get_contract_warnings()
  if cw:
   with bfg_card('Contract Warnings'):
    for x in cw[:8]: st.write('• '+x)
  with bfg_card('Financial Crisis (all brands)'):
   for co in PLAYABLE:
    crisis.refresh_crisis_status_from_budget(co,get_company_budget(co))
    cr=st.session_state.company_crisis.get(co,{})
    st.write(f"**{co}:** {cr.get('status','Healthy')} · bank {money(get_company_budget(co))} · weeks below $0: **{cr.get('weeks_below_zero',0)}**")
 ab_comp=st.session_state.get('active_brand','NXT')
 render_brand_hub_embed(ab_comp,compact=True,key_prefix='dash_hub')
 render_brand_exclusives_section(ab_comp,'dash_ex',compact=True)
 with bfg_card('Multiplayer snapshot'):
  for co in PLAYABLE:
   wp=st.session_state.week_progress.get(co,{})
   st.write(f"**{co}:** {wp.get('status','Not Started')} · GM {get_assigned_gm_display(co)}")
  st.caption('Open **Multiplayer Dashboard** for full status. Admin: **Commissioner Control Center**.')
elif page in ('Weekly Control Center','Multiplayer Dashboard'):
 render_weekly_control_center()
elif page=='Commissioner Control Center':
 ui_pages.render_commissioner_control_center()
elif page=='Storyline Tracker':
 ui_pages.render_storyline_tracker_page()
elif page=='Sponsor Objectives':
 ui_pages.render_sponsor_objectives_page()
elif page=='Season Awards':
 ui_pages.render_season_awards_page()
elif page=='Free Agency':
 render_page_shell('Free Agency',subtitle='Sign free agents to your brand — offers and bidding.',show_meter=False)
 ensure_contract_fields(); ensure_finance_state()
 st.subheader('Free Agency Pool')
 fa=[find(x['name']) for x in st.session_state.free_agency_pool if find(x['name'])]
 fa+=[w for w in st.session_state.roster if w.get('company')=='Free Agency' and w not in fa]
 if not fa: st.info('No free agents. Expired contracts appear here — also under Contracts → Free Agency.')
 for w in fa:
  sync_wrestler_from(w); recompute_contract_counters(w)
  c1,c2=st.columns([.18,.82])
  with c1: show_img(w['name'],90)
  with c2:
   st.markdown(f"**{w['name']}** · OVR {w['overall']} · Pop {w['popularity']}")
   sign_co=st.selectbox('Sign to',PLAYABLE,key=f'fap_co_{w["name"]}')
   yrs=st.number_input('Years',1,7,3,key=f'fap_y_{w["name"]}')
   sal=st.number_input('Salary',100000,20000000,int(w.get('salary_demand',w['salary'])),step=50000,key=f'fap_s_{w["name"]}')
   if st.button('Sign',key=f'fap_sign_{w["name"]}'):
    ok,msg=sign_free_agent_to_company(w,sign_co,int(yrs),int(sal),250000)
    if ok: touch_universe_meta(sign_co); save_universe(); st.success(msg); st.rerun()
    else: st.error(msg)
elif page=='Weekly Performance':
 render_weekly_performance_page()
elif page=='Company Home':
 comp=render_page_shell('Company Home',subtitle='Brand profile, lore, champions snapshot, and exclusive lanes.',use_brand_tabs=True,tabs_label='Company',show_meter=True)
 can_edit=can_edit_company(comp)
 data=COMPANIES[comp]; prof=st.session_state.company_profiles.setdefault(comp,dict(COMPANY_PROFILES[comp]))
 prof['owner']=st.text_input('Owner name',prof.get('owner',data['owner']),key=f'own_{comp}',disabled=not can_edit)
 prof['gm']=st.text_input('GM name',prof.get('gm',data['gm']),key=f'gm_{comp}',disabled=not can_edit)
 prof['commentary']=st.text_input('Commentary team',prof.get('commentary',''),key=f'com_{comp}',disabled=not can_edit)
 prof['ring_announcer']=st.text_input('Ring announcer',prof.get('ring_announcer',''),key=f'ra_{comp}',disabled=not can_edit)
 prof['theme_song']=st.text_input('Theme song',prof.get('theme_song',''),key=f'ts_{comp}',disabled=not can_edit)
 st.session_state.company_lore[comp]=st.text_area('Company lore / description',st.session_state.company_lore.get(comp,BRAND_THEMES[comp]['lore']),height=120,key=f'lore_{comp}',disabled=not can_edit)
 prof['prestige']=st.slider('Prestige score',1,100,int(prof.get('prestige',85)),key=f'prest_{comp}',disabled=not can_edit)
 prof['notes']=st.text_area('Company notes',prof.get('notes',''),key=f'notes_{comp}',disabled=not can_edit)
 if can_edit and st.button('Save company profile',key=f'save_co_{comp}'): touch_universe_meta(comp); save_universe(); st.toast(f'{comp} profile saved.')
 c1,c2,c3=st.columns([.28,.36,.36])
 with c1:
   with bfg_card('Logo / Owner'):
    show_entity_img(comp,'logo',110)
    show_company_owner_imgs(comp,100)
    st.markdown('<div class="helper-note">Use <b>Manage photos</b> below for uploads · <b>Picture Manager</b> for belts & wrestlers.</div>',unsafe_allow_html=True)
 with c2:
   with bfg_card('Brand Identity'):
    st.write(f"**Colors:** {BRAND_THEMES[comp]['primary']} / {BRAND_THEMES[comp]['accent']}")
    st.write(f"**Commentary:** {prof['commentary']}"); st.write(f"**Ring Announcer:** {prof['ring_announcer']}")
    st.write(f"**Theme:** {prof['theme_song']}")
    upcoming=get_scheduled_show(comp,next_bookable_week())
    st.write(f"**Upcoming show:** {upcoming.get('venue','TBD') if upcoming else 'Book in Schedule Calendar'}")
 with c3:
   with bfg_card('Business Snapshot'):
    sync_company_payroll_stats()
    ensure_finance_state()
    fin=st.session_state.company_finance[comp]
    st.metric('Roster',len(roster(comp))); st.metric('Current Budget',money(fin['current_budget'])); st.metric('Payroll',money(fin['payroll'])); st.metric('Prestige',prof['prestige'])
    st.write('**Platforms:** '+', '.join(data['platforms'])); st.write('**Sponsors:** '+', '.join(data['sponsors']))
 with bfg_card('Champions'):
  for t,v in st.session_state.champions.get(comp,{}).items(): st.write(f"**{display_title(t)}:** {v}")
 render_brand_hub_embed(comp,compact=True,key_prefix='home_hub')
 render_company_home_photo_panel(comp,can_edit)
 render_brand_exclusives_section(comp,'home_ex',compact=False)
elif page=='Book Show':
 _bh=book_show_helpers()
 _bh.render_book_show_page(_bh)
elif page=='Twitter':
 ensure_twitter_unique_registry()
 tw_comp=render_page_shell('Twitter',subtitle='Universe-linked social — no repeated tweets; engagement up to billions of views on mega-viral posts.',use_brand_tabs=True,tabs_label='Active brand',show_meter=True)
 render_brand_exclusives_section(tw_comp,'tw_ex',compact=True)
 ensure_team_profiles()
 tw_edit=can_edit_company(tw_comp)
 allowed_cos=PLAYABLE if is_admin() else ([st.session_state.assigned_company] if st.session_state.assigned_company in PLAYABLE else [])
 comp=tw_comp
 apply_pending_tw_compose_opts()
 live_preview=twitter_live_context(comp)
 tw_stats=twitter_page_stats(comp)
 has_ai=get_openai_api_key()
 nav_col,ai_col,uniq_col=st.columns([2.2,1.2,1.2])
 with nav_col:
  st.markdown('**Where to go:** **Timeline** = read feed · **Create Post** = one tweet · **Threads** = replies · **Buzz** = heat · **Auto Waves** = bulk')
 with ai_col:
  tw_ai_on=should_use_openai_ai()
  st.session_state.twitter_force_ai=st.toggle('AI generation',value=st.session_state.get('twitter_force_ai',True) and tw_ai_on,key='tw_ai_toggle',disabled=not tw_ai_on,help='Free mode uses procedural tweets only')
 with uniq_col:
  st.metric('Unique lines saved',len(st.session_state.get('twitter_text_hashes',set())))
 st.markdown('<div class="tw-stat-row">',unsafe_allow_html=True)
 s1,s2,s3,s4,s5,s6=st.columns(6)
 s1.metric('Brand posts',tw_stats['brand'])
 s2.metric('This week',tw_stats['week'])
 s3.metric('Viral',tw_stats['viral'])
 s4.metric('Hot takes',tw_stats['hot'])
 s5.metric('Drama flags',tw_stats['drama'])
 s6.metric('AI',('On' if twitter_ai_enabled() else 'Off'))
 st.markdown('</div>',unsafe_allow_html=True)
 if builtin_ai_env_on() or not should_use_openai_ai():
  st.success('**Free mode** — procedural tweets (unique, no OpenAI).')
 elif not has_ai:
  st.warning('Add `OPENAI_API_KEY` in `.env` for AI tweets — procedural tweets still work and never repeat.')
  render_openai_key_helper()
 elif not st.session_state.get('twitter_force_ai',True):
  st.caption('AI toggle is off — using procedural variety only.')
 with st.expander('Universe context',expanded=False):
  st.write(f"**Last show:** {live_preview['last_show']}")
  st.write(f"**Upcoming:** {live_preview['upcoming']}")
  st.write('**Champions:** '+(', '.join(live_preview['champions']) or '—'))
  st.write('**Rivalries:** '+(', '.join(live_preview['rivalries']) or '—'))
  st.write('**Unresolved:** '+(', '.join(live_preview['unresolved']) or '—'))
 st.caption('Quick presets — tap then go to **Create Post**')
 pr_cols=st.columns(min(6,len(TWEET_PRESETS)))
 for i,pr in enumerate(TWEET_PRESETS[:6]):
  if pr_cols[i].button(pr[0][:24],key=f'tw_pre_{i}',use_container_width=True):
   queue_tw_compose_opts(pr[1],pr[2],pr[3]); st.rerun()
 tab_timeline,tab_create,tab_recruit,tab_threads,tab_buzz,tab_waves=st.tabs(['Timeline','Create Post','Recruit / Tamper','Threads & Replies','Buzz & Heat','Auto Waves'])
 tw_mode_map={'generate original tweet':'original','generate reply':'reply','generate quote tweet':'quote','generate owner/GM response':'original','generate commentator reaction':'reply'}
 with tab_timeline:
  st.caption('Live feed — filter, search, and read the timeline without scrolling past compose controls.')
  fc1,fc2,fc3,fc4,fc5,fc6=st.columns([1.1,1.1,1,1,1,1.2])
  feed_co=fc1.selectbox('Brand',['All']+PLAYABLE,index=([c for c in ['All']+PLAYABLE].index(comp) if comp in PLAYABLE else 0),key='tw_feed_co')
  feed_typ=fc2.selectbox('Type',['All','Replies only']+sorted(set(TWEET_TYPES+['Reply Tweet','Quote Tweet'])),key='tw_feed_typ')
  feed_week=fc3.checkbox('This week',value=False,key='tw_feed_week')
  viral_only=fc4.checkbox('Viral',value=False,key='tw_feed_viral')
  contro_only=fc5.checkbox('Hot',value=False,key='tw_feed_contro')
  filt=fc6.text_input('Search',key='tw_feed_f',placeholder='Search posts…')
  posts=filter_twitter_posts(st.session_state.twitter_posts,feed_co,feed_typ,feed_week,viral_only,contro_only,filt)
  fp=st.select_slider('Posts per page',options=[5,8,12,20],value=8,key='tw_feed_pp')
  fpages=max(1,(len(posts)+fp-1)//fp)
  fpg=st.number_input('Page',1,fpages,1,key='tw_feed_pg')
  st.caption(f'**{len(posts)}** post(s) · page **{fpg}/{fpages}**')
  if not posts:
   st.info('No posts match — use **Create Post** or **Auto Waves** to fill the timeline.')
  else:
   for p in posts[(fpg-1)*fp:fpg*fp]: render_tweet_card(p,compact=True)
 with tab_create:
  st.caption('Step 1: who is posting · Step 2: topic & tone · Step 3: generate or save.')
  c1,c2=st.columns(2)
  with c1:
   poster_opts=(['All']+PLAYABLE) if is_admin() else (allowed_cos or [comp])
   poster_co=st.selectbox('Poster company',poster_opts,index=0,key='tw_pco')
   poster_type=st.selectbox('Poster type',['Wrestler','Staff','Company Account'],key='poster_type')
   p_co=poster_co if poster_co!='All' else comp
   typ_choices=TWEET_TYPES+['Reply Tweet','Quote Tweet','Tag Partner Reply','Breakup Tease Tweet','Tag Title Hype Tweet']
   typ=st.selectbox('Tweet type',typ_choices,key='tweet_type')
   dt,tn=sync_options_from_type(typ,None)
   if st.button('Sync topic/tone from tweet type',key='tw_sync_type'):
    queue_tw_compose_opts(dt,tn,typ); st.rerun()
   def_topic,def_tone=tw_select_defaults(dt,tn)
   st.caption(f"Type suggests: **{dt}** · **{tn}**")
   tw_topic=st.selectbox('Topic',TWITTER_TOPICS,index=TWITTER_TOPICS.index(def_topic),key='tw_topic')
   tw_tone=st.selectbox('Tone',TWITTER_TONES,index=TWITTER_TONES.index(def_tone),key='tw_tone')
  with c2:
   tw_mode=st.selectbox('Generation mode',['generate original tweet','generate reply','generate quote tweet','generate owner/GM response','generate commentator reaction'],key='tw_mode')
   reply_parents=[p for p in st.session_state.twitter_posts if p_co=='All' or p.get('company') in (p_co,comp)][:40]
   if tw_mode in ('generate reply','generate quote tweet','generate commentator reaction'):
    if reply_parents:
     rlabels=[f"#{p['id']} @{slug(p.get('wrestler','')).replace('_','')} — {p.get('text','')[:50]}…" for p in reply_parents]
     rix=st.selectbox('Reply to post',range(len(rlabels)),format_func=lambda i:rlabels[i],key='tw_compose_reply_ix')
     st.session_state.tw_reply_parent_id=reply_parents[rix]['id']
     with st.container(border=True):
      par=reply_parents[rix]
      st.caption(f"@{slug(par.get('wrestler','')).replace('_','')} · {par.get('post_type')}")
      st.markdown(f"*\"{par.get('text','')[:220]}\"*")
     st.selectbox('Reply style',REPLY_STYLES,index=REPLY_STYLES.index(st.session_state.get('tw_reply_style','Clap back')) if st.session_state.get('tw_reply_style') in REPLY_STYLES else 0,key='tw_reply_style')
    else:
     st.warning('No posts to reply to — post on **Timeline** first or use **Threads & Replies**.')
     st.session_state.tw_reply_parent_id=None
   mention_pool=opts_twitter_wrestlers(p_co)+[x.split(' — ')[0] for x in opts_staff_people(p_co)]+opts_company_accounts(p_co)
   mention_pick=clean_name_selector('Mention / target','tw_mention',options=sorted(set(mention_pool),key=str.lower),extra_options=[''],current='',label_search='Search mention',show_search=True)
   mention=st.text_input('Extra mention text','',key='tw_mention_txt') or mention_pick
   manual=st.text_area('Manual tweet (optional — overrides AI)',height=100,key='tw_manual')
  n=''; w=None; staff=None; handle=''; role=''
  if poster_type=='Wrestler':
   n=clean_name_selector('Poster','twn',options=opts_twitter_wrestlers(p_co),company=p_co,entity_type='Wrestler',default_company=p_co,label_search='Search wrestler')
   w=find(n); handle='@'+slug(n).replace('_',''); role='Wrestler'
  elif poster_type=='Company Account':
   n=clean_name_selector('Poster','twn',options=opts_company_accounts(p_co),company=p_co,entity_type='Company Account',default_company=p_co,label_search='Search account')
   staff=next((s for s in st.session_state.staff.get(p_co,[]) if s['name']==n),None)
   handle=staff['handle'] if staff else '@'+slug(p_co); role='Company Account'
  else:
   sl=clean_name_selector('Poster','twn',options=opts_staff_people(p_co),company=p_co,entity_type='Staff',default_company=p_co,label_search='Search staff')
   staff=get_staff(p_co,sl); n=staff['name'] if staff else (sl.split(' — ')[0] if sl else ''); handle=staff['handle'] if staff else ''; role=staff['role'] if staff else 'Staff'
  if w:
   st.caption(f"Tag team: **{tag_team_for_wrestler(n,comp) or 'solo'}** · Record **{rec(w)}** · Pop **{w['popularity']}** · Controversy risk **{w.get('controversy_risk',0)}**")
  eff_preview=compute_tweet_effects(tw_topic,tw_tone,w,comp,mention) if w else {'buzz':random.randint(2,8)}
  eng_preview=compute_tweet_engagement(w,comp,tw_topic,tw_tone,typ,eff_preview)
  pe1,pe2,pe3,pe4=st.columns(4)
  pe1.metric('Est. views',format_social_num(eng_preview['views']))
  pe2.metric('Est. likes',format_social_num(eng_preview['likes']))
  pe3.metric('Hot take',eng_preview['controversy_score'])
  pe4.metric('Viral chance','Mega' if eng_preview.get('mega') else ('High' if eng_preview['viral'] else 'Normal'))
  st.caption('Engagement scales with heat — mega posts can reach **billions** of views. Every line is unique (no repeats).')
  if not tw_edit: render_edit_only_notice(comp)
  g1,g2,g3=st.columns(3)
  if g1.button('Generate tweet',type='primary',key='tw_gen',disabled=not tw_edit or (not is_admin() and p_co not in allowed_cos)):
   if not can_tweet_as_company(p_co): st.error(f'You can only tweet as {st.session_state.assigned_company}.'); st.stop()
   mode=tw_mode_map.get(tw_mode,'original')
   parent=None
   if mode in ('reply','quote'):
    pid=st.session_state.get('tw_reply_parent_id')
    parent=next((p for p in st.session_state.twitter_posts if p.get('id')==pid),None) if pid else None
    if not parent and st.session_state.twitter_posts:
     parent=st.session_state.twitter_posts[0]
    if not parent: st.error('Pick a post to reply to in the dropdown above.'); st.stop()
    typ='Quote Tweet' if mode=='quote' else 'Reply Tweet'
   reply_style=st.session_state.get('tw_reply_style','Clap back') if mode in ('reply','quote') else ''
   eff=compute_tweet_effects(tw_topic,tw_tone,w,comp,mention) if w else {'buzz':random.randint(2,8)}
   if poster_type=='Wrestler' and w:
    if parent and mode in ('reply','quote'):
     post=twitter_post_reply(comp,n,w,None,parent,reply_style,tw_topic,tw_tone,as_quote=(mode=='quote'))
     if not post: st.error('Reply failed.'); st.stop()
    else:
     text=generate_poster_tweet(w,None,comp,typ,tw_topic,tw_tone,mode,mention,'',force_options=False,parent_post=parent,reply_style=reply_style)
     extra=build_tweet_extra(n,comp,w,eff,tw_topic,tw_tone,mode,ai_generated=bool(get_openai_api_key()))
     post=make_twitter_post(comp,'wrestler',n,handle,role,typ,text,mention,extra)
   elif staff:
    if parent and mode in ('reply','quote'):
     post=twitter_post_reply(comp,n,None,staff,parent,reply_style,tw_topic,tw_tone,as_quote=(mode=='quote'))
     if not post: st.error('Reply failed.'); st.stop()
    else:
     text=generate_poster_tweet(None,staff,comp,typ,tw_topic,tw_tone,mode,mention,'',force_options=False,parent_post=parent,reply_style=reply_style) if mode!='original' or tw_topic!='Wrestling Story' else staff_tweet(staff,comp,typ,mention=mention)
     post=make_twitter_post(comp,'staff',n,handle,role,typ,text,mention,{'ai_generated':bool(get_openai_api_key()),'effects':eff,'topic':tw_topic,'tone':tw_tone,'tweet_mode':mode,'wrestler_obj':None,'reply_to_id':parent['id'] if parent else None})
   else: st.error('Select a valid poster.'); st.stop()
   st.session_state.twitter_posts.insert(0,post); update_rank({n:'Twitter activity.'}); st.toast('Tweet posted — check Timeline.'); st.rerun()
  if g2.button('Save manual',key='tw_man',disabled=not tw_edit or (not is_admin() and p_co not in allowed_cos)):
   if not can_tweet_as_company(p_co): st.error(f'You can only tweet as {st.session_state.assigned_company}.'); st.stop()
   eff=compute_tweet_effects(tw_topic,tw_tone,w,comp,mention) if w else {'buzz':2}
   text=manual or (generate_poster_tweet(w,staff,comp,typ,tw_topic,tw_tone,tw_mode_map.get(tw_mode,'original'),mention) if w or staff else '')
   if poster_type=='Wrestler' and w:
    post=make_twitter_post(comp,'wrestler',n,handle,role,typ,text,mention,build_tweet_extra(n,comp,w,eff,tw_topic,tw_tone,tw_mode_map.get(tw_mode,'original'),ai_generated=False))
   elif staff:
    post=make_twitter_post(comp,'staff',n,handle,role,typ,text,mention,{'ai_generated':False,'effects':eff,'topic':tw_topic,'tone':tw_tone})
   else: st.error('Select poster.'); st.stop()
   st.session_state.twitter_posts.insert(0,post); st.rerun()
  if g3.button('Preview line only',key='tw_prev',disabled=not(w or staff)):
   mode_p=tw_mode_map.get(tw_mode,'original')
   parent_p=next((p for p in st.session_state.twitter_posts if p.get('id')==st.session_state.get('tw_reply_parent_id')),None) if mode_p in ('reply','quote') else None
   prev=generate_poster_tweet(w,staff,comp,typ,tw_topic,tw_tone,mode_p,mention,'',force_options=False,parent_post=parent_p,reply_style=st.session_state.get('tw_reply_style',''))
   st.info(prev)
  with st.expander('Tag partners, threads & rivalries'):
   tab_reply,tab_thread,tab_rival=st.tabs(['Partner reply','2-tweet thread','Rivalry callout'])
   mem_posts=[p for p in st.session_state.twitter_posts if p.get('poster_kind')=='wrestler' and p.get('company')==comp][:25]
   with tab_reply:
    if not mem_posts: st.caption('Post a wrestler tweet first.')
    else:
     labels=[f"#{p['id']} {p.get('wrestler')} — {p.get('text','')[:56]}…" for p in mem_posts]
     pick_post=st.selectbox('Reply to',labels,key='tw_reply_pick')
     pid=int(pick_post.split()[0].replace('#',''))
     parent=next((p for p in mem_posts if p['id']==pid),mem_posts[0])
     tname=parent.get('team_name') or tag_team_for_wrestler(parent.get('wrestler',''),comp)
     tw2=find(tname) if tname else None
     mems=[m['name'] for m in team_members_for(tw2,comp)] if tw2 else []
     mem=clean_name_selector('Reply as','tw_reply_mem',options=mems if mems else opts_twitter_wrestlers(comp),current=next((x for x in mems if x!=parent.get('wrestler')),mems[0] if mems else ''),show_search=True)
     rtyp=st.selectbox('Interaction',['Partner defends teammate','Breakup tease','Quote tweet partner','Call out partner','Subtweet partner'],key='tw_rtyp')
     if st.button('Generate partner reply',key='tw_memrep',disabled=not tw_edit) and mem:
      style='Defend / co-sign' if 'defend' in rtyp.lower() else 'Subtweet (no @)' if 'Breakup' in rtyp or 'Subtweet' in rtyp else 'Quote tweet dunk' if 'Quote' in rtyp else 'Clap back'
      mw=find(mem)
      if mw:
       post=twitter_post_reply(comp,mem,mw,None,parent,style,'Tag Team Drama','emotional')
       if post: st.session_state.twitter_posts.insert(0,post); st.rerun()
   with tab_thread:
    m1=clean_name_selector('Wrestler A','tw_th1',options=opts_twitter_wrestlers(p_co),company=p_co,entity_type='Wrestler',show_search=True)
    t1=tag_team_for_wrestler(m1,comp)
    mems=[m['name'] for m in team_members_for(find(t1),comp)] if t1 and find(t1) else []
    m2=clean_name_selector('Wrestler B replies','tw_th2',options=[x for x in mems if x!=m1] if mems else opts_twitter_wrestlers(p_co),show_search=True)
    if st.button('Generate thread (2 posts)',key='tw_thread',disabled=not tw_edit) and m1 and m2:
     w1=find(m1); tpc,tn=infer_topic_tone_from_type(typ,w1)
     text1=generate_poster_tweet(w1,None,comp,typ,tpc,tn,'original',mention)
     ex1=twitter_wrestler_extra(m1,comp,ai_generated=bool(get_openai_api_key()),topic=tpc,tone=tn)
     p1=make_twitter_post(comp,'wrestler',m1,'@'+slug(m1).replace('_',''),'Wrestler',typ,text1,mention,ex1)
     st.session_state.twitter_posts.insert(0,p1)
     p2=twitter_post_reply(comp,m2,find(m2),None,p1,'Defend / co-sign','Tag Team Drama','emotional')
     if p2: st.session_state.twitter_posts.insert(0,p2)
     st.rerun()
   with tab_rival:
    caller=clean_name_selector('Your wrestler','tw_riv_me',options=opts_twitter_wrestlers(p_co),company=p_co,entity_type='Wrestler',show_search=True)
    rival=clean_name_selector('Rival','tw_riv_them',options=opts_twitter_wrestlers('All'),company='All',entity_type='Wrestler',label_search='Search rival')
    if st.button('Generate rivalry tweet',key='tw_riv_go',disabled=not tw_edit) and caller:
     ww=find(caller); tname=tag_team_for_wrestler(caller,comp)
     text=member_team_tweet(caller,tname,comp,'Rivalry Tweet',rival,'rival_callout',reply_context='') if tname else generate_poster_tweet(ww,None,comp,'Rivalry Tweet','Rivalry','savage','original',rival)
     extra=twitter_wrestler_extra(caller,comp,interaction='rival_callout',ai_generated=bool(get_openai_api_key()),topic='Rivalry',tone='savage')
     st.session_state.twitter_posts.insert(0,make_twitter_post(comp,'wrestler',caller,'@'+slug(caller).replace('_',''),'Wrestler','Rivalry Tweet',text,rival,extra)); st.rerun()
 with tab_recruit:
  render_twitter_recruitment_tab(comp,allowed_cos,tw_edit)
 with tab_threads:
  st.caption('Build reply threads — parent quote shows on the timeline. Use **Timeline** to read the full feed.')
  rp_brand=st.selectbox('Posts from brand',['All']+PLAYABLE,index=([c for c in ['All']+PLAYABLE].index(comp)),key='tw_rep_brand')
  rp_posts=[p for p in st.session_state.twitter_posts if rp_brand=='All' or p.get('company')==rp_brand][:50]
  if not rp_posts:
   st.info('No tweets yet — use **Create Post** or **Auto Waves** first.')
  else:
   rlabels=[f"#{p['id']} {p.get('wrestler')} ({p.get('company')}) — {p.get('text','')[:58]}…" for p in rp_posts]
   rp_ix=st.selectbox('Post to reply to',range(len(rlabels)),format_func=lambda i:rlabels[i],key='tw_rep_parent_ix')
   parent_post=rp_posts[rp_ix]
   st.session_state.tw_reply_parent_id=parent_post['id']
   with bfg_card(parent_post.get('wrestler','')):
    st.markdown(f"**{parent_post.get('wrestler')}** {parent_post.get('handle','')} · Week {parent_post.get('week')} · {parent_post.get('post_type')}")
    st.markdown(parent_post.get('text',''))
    m1,m2,m3,m4=st.columns(4)
    m1.metric('Views',format_social_num(parent_post.get('views',0)))
    m2.metric('Likes',format_social_num(parent_post.get('likes',0)))
    m3.metric('Replies',format_social_num(parent_post.get('replies',0)))
    m4.metric('Score',parent_post.get('controversy_score',0))
   rc1,rc2=st.columns(2)
   with rc1:
    rep_as=clean_name_selector('Reply as wrestler','tw_rep_as',options=opts_twitter_wrestlers(parent_post.get('company',comp)),company=parent_post.get('company',comp),entity_type='Wrestler',default_company=parent_post.get('company',comp),label_search='Search wrestler')
    rep_style=st.selectbox('Reply style',REPLY_STYLES,key='tw_rep_style')
   with rc2:
    rep_mode=st.radio('Post as',['Reply','Quote tweet'],horizontal=True,key='tw_rep_mode')
    rep_count=st.slider('Pile-on replies (different wrestlers)',1,8,3,key='tw_rep_pile_n')
   thread_replies=[p for p in st.session_state.twitter_posts if p.get('reply_to_id')==parent_post['id']]
   if thread_replies:
    st.subheader(f'Thread ({len(thread_replies)} replies)')
    for tr in thread_replies[:8]: render_tweet_card(tr,compact=True)
   br1,br2,br3,br4=st.columns(4)
   rw=find(rep_as)
   if br1.button('Generate reply',type='primary',key='tw_rep_one',disabled=not tw_edit or not rw):
    post=twitter_post_reply(parent_post.get('company',comp),rep_as,rw,None,parent_post,rep_style,as_quote=(rep_mode=='Quote tweet'))
    if post: st.session_state.twitter_posts.insert(0,post); update_rank({rep_as:'Twitter reply.'}); st.rerun()
   if br2.button(f'Pile-on ({rep_count})',key='tw_rep_pile',disabled=not tw_edit):
    for p in generate_reply_pile_on(parent_post,parent_post.get('company',comp),rep_count): st.session_state.twitter_posts.insert(0,p)
    update_rank(); st.rerun()
   if br3.button('Rival replies only',key='tw_rep_rival',disabled=not tw_edit):
    author=parent_post.get('wrestler','')
    riv=[r for r in st.session_state.rivalries if author in r.get('wrestlers',[])]
    targets=set()
    for r in riv:
     for x in r.get('wrestlers',[]):
      if x!=author: targets.add(x)
    for tname in list(targets)[:4]:
     tw=find(tname)
     if not tw: continue
     post=twitter_post_reply(tw['company'],tname,tw,None,parent_post,'Clap back')
     if post: st.session_state.twitter_posts.insert(0,post)
    update_rank(); st.rerun()
   if br4.button('GM / office reply',key='tw_rep_gm',disabled=not tw_edit):
    prof=st.session_state.company_profiles.get(parent_post.get('company',comp),{})
    gm=prof.get('gm') or COMPANIES[parent_post.get('company',comp)]['gm']
    staff=next((s for s in st.session_state.staff.get(parent_post.get('company',comp),[]) if s['name']==gm),{'name':gm,'handle':'@'+slug(gm).replace('_',''),'role':'GM','style':'corporate'})
    post=twitter_post_reply(parent_post.get('company',comp),gm,None,staff,parent_post,'GM / office shutdown')
    if post: st.session_state.twitter_posts.insert(0,post); st.rerun()
 with tab_buzz:
  buzz_l,buzz_r=st.columns(2)
  with buzz_l:
   st.subheader('Drama & storyline flags')
   drama=st.session_state.get('twitter_drama',[])
   if not drama: st.caption('Controversial tweets create drama flags automatically.')
   for d in drama[:8]:
    with st.container(border=True):
     st.markdown(f"**{d.get('wrestler')}** · W{d.get('week')} · {d.get('topic')}")
     st.caption((d.get('text','') or '')[:180])
   for f in st.session_state.get('storyline_flags',[])[:6]:
    st.write(f"• W{f.get('week')} **{f.get('flag')}** — {f.get('target')}")
   st.subheader('Buzz leaders')
   for w in sorted([x for x in st.session_state.roster if x.get('twitter_buzz',0)>0],key=lambda x:-x.get('twitter_buzz',0))[:6]:
    st.write(f"**{w['name']}** — buzz {w.get('twitter_buzz',0)}")
    st.progress(min(1.0,w.get('twitter_buzz',0)/100.0))
  with buzz_r:
   st.subheader('Controversy lab')
   st.caption('High-risk posts — up to **2M** views when heat is right.')
   cpre=[p[0] for p in CONTROVERSY_SCENARIOS]
   cix=st.selectbox('Scenario',range(len(cpre)),format_func=lambda i:cpre[i],key='tw_contro_preset')
   if st.button('Load scenario into Create Post',key='tw_contro_apply'):
    sc=CONTROVERSY_SCENARIOS[cix]
    queue_tw_compose_opts(sc[1],sc[2],sc[3]); st.rerun()
   cname=clean_name_selector('Post as','tw_contro_who',options=opts_twitter_wrestlers(comp),company=comp,entity_type='Wrestler',default_company=comp,label_search='Search wrestler')
   cw=find(cname)
   ctopic=st.selectbox('Topic',['Controversy','Card Complaint','Creative Complaint','Political/Controversy'],key='tw_contro_topic')
   ctone=st.selectbox('Tone',['angry','savage','cryptic','petty','political','emotional'],key='tw_contro_tone')
   ctyp=st.selectbox('Type',['Angry Tweet','Cryptic Tweet','Locker Room Drama Tweet','Creative Complaint Tweet'],key='tw_contro_typ')
   cmention=clean_name_selector('Call out','tw_contro_mention',options=['']+opts_twitter_wrestlers(comp),current='',show_search=True)
   bw1,bw2=st.columns(2)
   if bw1.button('One hot tweet',type='primary',key='tw_contro_one',disabled=not tw_edit or not cw):
    eff=compute_tweet_effects(ctopic,ctone,cw,comp,cmention)
    text=generate_poster_tweet(cw,None,comp,ctyp,ctopic,ctone,'original',cmention,force_options=False)
    extra=build_tweet_extra(cname,comp,cw,eff,ctopic,ctone,'original',ai_generated=bool(get_openai_api_key()))
    st.session_state.twitter_posts.insert(0,make_twitter_post(comp,'wrestler',cname,'@'+slug(cname).replace('_',''),'Wrestler',ctyp,text,cmention,extra)); st.rerun()
   if bw2.button(f'{comp} wave (10)',key='tw_contro_wave',disabled=not tw_edit):
    for p in simulate_controversy_wave(comp,10): st.session_state.twitter_posts.insert(0,p)
    update_rank(); st.rerun()
   if is_admin() and st.button('All brands wave',key='tw_contro_world',disabled=not tw_edit):
    for c2 in PLAYABLE:
     for p in simulate_controversy_wave(c2,4): st.session_state.twitter_posts.insert(0,p)
    update_rank(); st.rerun()
   st.caption('Hottest on brand')
   for hp in sorted([p for p in st.session_state.twitter_posts if p.get('company')==comp],key=lambda x:-int(x.get('controversy_score',0) or 0))[:4]:
    render_tweet_card(hp,compact=True)
 with tab_waves:
  st.caption('One-click timeline fillers — tied to your universe state.')
  if st.session_state.twitter_posts:
   hot_target=max(st.session_state.twitter_posts[:12],key=lambda p:int(p.get('views',0) or 0))
   with st.container(border=True):
    st.markdown(f"**Trending on your feed** — #{hot_target.get('id')} {hot_target.get('wrestler')}")
    st.caption(hot_target.get('text','')[:120])
    if st.button(f'Pile-on replies (5 wrestlers)',key='tw_quick_reply',disabled=not tw_edit,type='primary'):
     for p in generate_reply_pile_on(hot_target,hot_target.get('company',comp),5): st.session_state.twitter_posts.insert(0,p)
     update_rank(); st.toast('Reply wave posted.'); st.rerun()
  mw1,mw2=st.columns(2)
  mega_n=mw1.slider('Mega wave size',10,60,30,key='tw_mega_n')
  if mw1.button(f'Mega wave ({mega_n} unique tweets)',type='primary',key='tw_mega_wave',disabled=not tw_edit):
   for p in simulate_mega_twitter_wave(comp,mega_n): st.session_state.twitter_posts.insert(0,p)
   update_rank(); st.toast(f'{mega_n} unique tweets posted.'); st.rerun()
  if mw2.button('World mega wave (15 per brand)',key='tw_mega_world',disabled=not tw_edit or not is_admin()):
   for c2 in PLAYABLE:
    for p in simulate_mega_twitter_wave(c2,15): st.session_state.twitter_posts.insert(0,p)
   update_rank(); st.toast('World timeline flooded with unique posts.'); st.rerun()
  with bfg_card('Fill the timeline'):
   q1,q2,q3=st.columns(3)
   if q1.button('World feed (all brands)',key='tw_world',disabled=not tw_edit):
    for p in simulate_world_twitter_wave(2): st.session_state.twitter_posts.insert(0,p)
    update_rank(); st.toast('World feed updated.'); st.rerun()
   if q2.button(f'{comp} fan wave (6)',key='tw_brand_wave',disabled=not tw_edit):
    for _ in range(6):
     name=random.choice(opts_twitter_wrestlers(comp))
     ww=find(name)
     if not ww: continue
     if random.random()<.5:
      pr=random.choice(TWEET_PRESETS); topic,tone,typ=pr[1],pr[2],pr[3]
     else:
      typ=random.choice(list(TWEET_TYPE_HINTS.keys())); topic,tone=TWEET_TYPE_HINTS[typ]
     text=generate_poster_tweet(ww,None,comp,typ,topic,tone,'original','')
     st.session_state.twitter_posts.insert(0,make_twitter_post(comp,'wrestler',name,'@'+slug(name).replace('_',''),'Wrestler',typ,text,'',twitter_wrestler_extra(name,comp,ai_generated=bool(get_openai_api_key()),topic=topic,tone=tone)))
    st.toast(f'{comp} fan wave posted.'); st.rerun()
   if q3.button('Champions & GMs',key='tw_champs',disabled=not tw_edit):
    for c in PLAYABLE if is_admin() else [comp]:
     for t,v in st.session_state.champions.get(c,{}).items():
      if not v or v in ('Vacant','Place Holder'): continue
      w=find(v)
      if w:
       text=generate_poster_tweet(w,None,c,'Champion Tweet','Champion Pride','cocky','original','')
       st.session_state.twitter_posts.insert(0,make_twitter_post(c,'wrestler',v,'@'+slug(v).replace('_',''),'Wrestler','Champion Tweet',text,t,extra=twitter_wrestler_extra(v,c,ai_generated=bool(get_openai_api_key()),topic='Champion Pride',tone='cocky')))
     prof=st.session_state.company_profiles.get(c,{})
     gm=prof.get('gm') or COMPANIES[c]['gm']
     st.session_state.twitter_posts.insert(0,make_twitter_post(c,'staff',gm,'@'+slug(gm).replace('_',''),'GM','GM Official Statement',pick_varied_fallback(gm,c,'GM Authority','corporate','GM Official Statement','',twitter_live_context(c)),'',{'ai_generated':False,'topic':'GM Authority','tone':'corporate'}))
    st.toast('Champions & GMs posted.'); st.rerun()
  with bfg_card('Universe reactions'):
   q4,q5,q6=st.columns(3)
   if q4.button('Unresolved events',key='tw_evreact',disabled=not tw_edit):
    evs=[e for e in st.session_state.random_event_history if e.get('status')=='unresolved'][:6]
    for ev in evs:
     tgt=find(ev.get('target',''))
     if not tgt: continue
     text=generate_poster_tweet(tgt,None,ev.get('company',comp),'Locker Room Drama Tweet','Random Event Reaction','angry','original','')
     st.session_state.twitter_posts.insert(0,make_twitter_post(ev.get('company',comp),'wrestler',tgt['name'],'@'+slug(tgt['name']).replace('_',''),'Wrestler','Random Event Reaction',text,'',twitter_wrestler_extra(tgt['name'],ev.get('company',comp),topic='Random Event Reaction',tone='angry')))
    st.rerun()
   if q5.button('Brand war',key='tw_brandwar',disabled=not tw_edit):
    for c in PLAYABLE:
     w=random.choice([x for x in roster(c) if not is_tag_team_entry(x)] or [None])
     if not w: continue
     other=random.choice([x for x in PLAYABLE if x!=c])
     text=generate_poster_tweet(w,None,c,'Rival Brand Shade','Other Company Comment','petty','original',other)
     st.session_state.twitter_posts.insert(0,make_twitter_post(c,'wrestler',w['name'],'@'+slug(w['name']).replace('_',''),'Wrestler','Rival Brand Shade',text,other,twitter_wrestler_extra(w['name'],c,topic='Other Company Comment',tone='petty')))
    st.rerun()
   if q6.button('Clear all posts',key='tw_clear_feed'):
    st.session_state.tw_clear_confirm=True
  if st.session_state.get('tw_clear_confirm'):
   if st.checkbox('Yes, delete all Twitter posts',key='tw_clear_yes') and st.button('Delete all posts',key='tw_clear_do'):
    st.session_state.twitter_posts=[]; st.session_state.tw_clear_confirm=False; st.rerun()
elif page=='Schedule Calendar':
 render_page_shell('Schedule Calendar',subtitle='Year schedule, PLE anchors, travel warnings, and AI schedule analysis.',use_brand_tabs=True,tabs_label='Brand',show_meter=True)
 migrate_schedule_calendar()
 locked=st.session_state.get('calendar_locked',False)
 h1,h2=st.columns([.75,.25])
 with h1:
  st.markdown('Build the full **52-week** schedule per company (weekly shows, PLEs, tours, crossovers). Lock when ready — Book Show will follow it week-by-week.')
 with h2:
  render_schedule_lock_badge(); st.caption('Status: **LOCKED**' if locked else 'Status: **UNLOCKED**')
 if locked: st.error('Full year schedule is LOCKED. Reset to edit dates, venues, cities, or show types.')
 tab_plan,tab_table,tab_ai=st.tabs(['Plan Schedule','Year Schedule Table','AI Schedule Analysis'])
 with tab_plan:
  cal_ex=brand_tabs('Calendar brand',key='cal_ex_brand')
  render_brand_exclusives_section(cal_ex,'cal_ex',compact=True)
  if not locked:
   with st.expander('Add / Edit Calendar Entry',expanded=True):
    cal_comp=cal_ex
    month=st.selectbox('Month',CALENDAR_MONTHS,key='cal_month')
    week=st.number_input('Week Number',1,52,next_bookable_week(),key='cal_week')
    show_date=st.date_input('Date',date.today(),key='cal_date')
    show_name=st.text_input('Show Name',f'{cal_comp} Week {week}',key='cal_sname')
    stype=st.selectbox('Show Type',CALENDAR_SHOW_TYPES,key='cal_stype')
    venue=venue_selector('cal')
    cap=st.number_input('Venue Capacity',1000,150000,int(venue.get('capacity',15000)),key='cal_cap')
    venue['capacity']=int(cap)
    ticket_px=st.number_input('Ticket price',15,500,65,key='cal_ticket')
    cal_status=st.selectbox('Status',CALENDAR_STATUSES,index=0,key='cal_status')
    travel_req=st.checkbox('Travel required',key='cal_travel')
    hotel_req=st.checkbox('Hotel required',key='cal_hotel')
    transport_req=st.checkbox('Transportation required',key='cal_transport')
    hometown=clean_name_multiselect('Hometown wrestler(s)','cal_ht',options=opts(cal_comp),default_company=cal_comp,default_entity='Wrestler',label_search='Search hometown talent')
    pr=st.text_input('Planned main rivalry',key='cal_rivalry'); notes=st.text_area('Notes',key='cal_notes')
    if st.button('Save Calendar Entry',key='cal_save'):
     entry={'month':month,'week':int(week),'date':str(show_date),'company':cal_comp,'show_name':show_name,'show_type':stype,
      'country':venue['country'],'region':venue['region'],'city':venue['city'],'venue':venue['venue'],'venue_data':venue,'capacity':int(cap),
      'ticket_price':int(ticket_px),'travel_required':travel_req,'hotel_required':hotel_req,'transportation_required':transport_req,
      'hometown':hometown,'planned_rivalry':pr,'notes':notes,'status':cal_status}
     entry=normalize_schedule_entry(entry)
     st.session_state.schedule_calendar=[e for e in st.session_state.schedule_calendar if int(e.get('week',-1))!=int(week) or e.get('company')!=cal_comp]
     st.session_state.schedule_calendar.append(entry)
     st.session_state.schedule_calendar.sort(key=lambda x:(int(x.get('week',0)),x.get('company',''))); st.success(f'Saved Week {week} — {cal_comp}'); st.rerun()
  else:
   st.info('Schedule inputs are disabled while locked. View the Year Schedule Table tab or reset to edit.')
  st.markdown('---')
  st.warning('Once you lock the full year schedule, you cannot edit weekly shows, PLEs, venues, cities, or dates unless you reset the schedule.')
  st.session_state.cal_lock_confirm=st.checkbox('I understand — lock the full year schedule',value=st.session_state.get('cal_lock_confirm',False),key='cal_lock_chk',disabled=locked)
  if st.button('Lock Full Year Schedule',disabled=locked or not st.session_state.get('cal_lock_confirm')):
   if not st.session_state.schedule_calendar: st.error('Add at least one calendar entry before locking.')
   else: lock_year_schedule(); st.success('Full year schedule LOCKED.'); st.rerun()
  st.markdown('---')
  st.warning('This will erase or unlock your full year schedule. You will lose locked weekly show and PLE schedule settings. Projected venue costs/revenue will be recalculated.')
  st.session_state.cal_reset_confirm=st.checkbox('I confirm reset / unlock',value=st.session_state.get('cal_reset_confirm',False),key='cal_reset_chk')
  clr=st.checkbox('Also clear all schedule entries',value=False,key='cal_reset_clear')
  if st.button('Reset Full Year Schedule',disabled=not st.session_state.get('cal_reset_confirm')):
   reset_year_schedule(clear_entries=clr); st.success('Schedule unlocked.'+( ' All entries cleared.' if clr else '')); st.rerun()
 with tab_table:
  st.markdown('##### Yearly Schedule')
  f1,f2,f3,f4,f5,f6=st.columns(6)
  with f1: cal_view=f1.radio('View',['All weeks','Single week'],horizontal=True,key='cal_view_mode')
  with f2: filt_comp=f2.selectbox('Brand',['All']+PLAYABLE,key='cal_filt_co')
  with f3: filt_month=f3.selectbox('Month',['All']+CALENDAR_MONTHS,key='cal_filt_month')
  with f4: filt_type=f4.selectbox('Show type',['All']+CALENDAR_SHOW_TYPES,key='cal_filt_type')
  with f5: filt_status=f5.selectbox('Status',['All']+CALENDAR_STATUSES+['Locked'],key='cal_filt_status')
  countries=sorted(set(e.get('country','') for e in st.session_state.schedule_calendar if e.get('country')))
  with f6: filt_country=f6.selectbox('Country',['All']+countries,key='cal_filt_country')
  cal_search=st.text_input('Search city, venue, country, or show name',key='cal_search',placeholder='e.g. New York, Madison Square Garden')
  autosave.render_autosave_indicator('cal_as')
  all_rows=[normalize_schedule_entry(dict(e)) for e in st.session_state.schedule_calendar]
  wk_pick=None
  if cal_view=='Single week':
   wk_pick=st.number_input('Focus week',1,52,next_bookable_week(),key='cal_focus_week')
  rows=filter_calendar_table_rows(all_rows,brand=filt_comp,show_type=filt_type,month=filt_month,status=filt_status,country=filt_country,search=cal_search,week_only=wk_pick)
  rows.sort(key=lambda x:(int(x.get('week',0)),x.get('company','')))
  if not rows:
   st.info('No schedule entries match your filters. Use **Plan Schedule** to add shows.')
  else:
   st.caption('**Readable view** shows every word. Use the table view for a spreadsheet-style layout (scroll sideways if needed).')
   render_calendar_readable_cards(rows)
   with st.expander('Table view (all columns)',expanded=False):
    render_calendar_year_table(rows)
   with st.expander('Event details & actions',expanded=True):
    labels=[f"Week {e.get('week')} · {e.get('company')} · {format_schedule_location(e)} · {e.get('venue','—')}" for e in rows]
    pick=st.selectbox('Select event',range(len(rows)),format_func=lambda i:labels[i],key='cal_pick_event')
    ev=rows[pick]
    loc=format_schedule_location(ev)
    st.markdown(f"**Location:** {loc}")
    st.markdown(f"**Venue:** {ev.get('venue') or '—'}")
    st.markdown(f"**Show:** {ev.get('show_name') or '—'}")
    c1,c2,c3=st.columns(3)
    c1.metric('Capacity',f"{int(ev.get('capacity',0)):,}")
    c2.metric('Est. attendance',f"{int(ev.get('projected_attendance',0)):,}")
    pl_txt,_=format_schedule_pl_display(ev)
    c3.metric('Est. P/L',pl_txt)
    st.caption(f"**Type:** {ev.get('show_type','')} · **Date:** {format_schedule_date_short(ev)} · **Status:** {schedule_entry_status(ev)}")
    if ev.get('hotel_savings') or ev.get('transport_savings'):
     st.caption(f"Hotel {money(ev.get('hotel_estimate',0))} (savings {money(ev.get('hotel_savings',0))}) · Transport {money(ev.get('transport_estimate',0))} (savings {money(ev.get('transport_savings',0))})")
    ba1,ba2,ba3,ba4=st.columns(4)
    if ba1.button('Edit in Plan Schedule',key='cal_act_edit',disabled=locked):
     load_calendar_entry_into_form(ev); set_active_brand(ev.get('company','NXT')); st.toast('Loaded — open **Plan Schedule** tab.'); st.rerun()
    if ba2.button('Duplicate',key='cal_act_dup',disabled=locked):
     dup=normalize_schedule_entry(dict(ev))
     dup['week']=min(52,int(ev.get('week',1))+1)
     dup['show_name']=str(dup.get('show_name',''))+' (copy)'
     dup['status']='Planned'
     st.session_state.schedule_calendar.append(dup)
     st.session_state.schedule_calendar.sort(key=lambda x:(int(x.get('week',0)),x.get('company','')))
     touch_universe_meta(ev.get('company')); save_universe(); st.rerun()
    if ba3.button('Delete',key='cal_act_del',disabled=locked):
     wk,co=int(ev.get('week',0)),ev.get('company')
     st.session_state.schedule_calendar=[x for x in st.session_state.schedule_calendar if not (int(x.get('week',-1))==wk and x.get('company')==co)]
     touch_universe_meta(co); save_universe(); st.rerun()
    if ba4.button('Lock entry',key='cal_act_lock',disabled=locked):
     for x in st.session_state.schedule_calendar:
      if int(x.get('week',-1))==int(ev.get('week',0)) and x.get('company')==ev.get('company'): x['status']='Locked'
     save_universe(); st.rerun()
   with st.expander('Extra notes per event',expanded=False):
    for e in rows:
     loc=format_schedule_location(e)
     sell_lbl=e.get('projected_sellout_label') or e.get('sellout_status') or f"{e.get('projected_sellout_pct',0)}%"
     notes=(e.get('notes') or '').strip()
     st.markdown(f"**Week {e['week']} — {e.get('company','')} — {e.get('show_name','')}**")
     st.write(f"Location: **{loc}** · Venue: **{e.get('venue') or '—'}**")
     st.write(f"Gate: **{sell_lbl}** · Rivalry: **{e.get('planned_rivalry') or '—'}**")
     if notes: st.write(f"Notes: {notes}")
     if e.get('status')=='Completed':
      st.write(f"Completed — Attendance {int(e.get('actual_attendance',0)):,} · P/L {money(e.get('actual_profit_loss',0))} · Rating {e.get('episode_rating',e.get('actual_rating','—'))}/10")
     st.markdown('---')
 with tab_ai:
  if st.button('Run AI Schedule Analysis',key='cal_ai_run'):
   st.session_state.calendar_ai_notes=schedule_ai_analysis(st.session_state.schedule_calendar)
   st.rerun()
  if st.session_state.get('calendar_ai_notes'):
   with bfg_card('Schedule Warnings & AI Notes'):
    for line in st.session_state.calendar_ai_notes: st.write('• '+line if not line.startswith('•') else line)
  else:
   warns=analyze_year_schedule(st.session_state.schedule_calendar)
   if warns:
    st.subheader('Quick schedule warnings')
    for w in warns: st.write('• '+w)
   else: st.caption('Lock the schedule or click Run AI Schedule Analysis for build/travel/PLE warnings.')
elif page=='Appearances':
 ensure_extended_state()
 comp=render_page_shell('Appearances',subtitle='Brand-exclusive media lanes — NXT Hollywood, SmackDown music/TV, WCW sports crossover.',use_brand_tabs=True,tabs_label='Appearance Company',show_meter=True)
 render_brand_hub_embed(comp,compact=True,key_prefix='app_hub')
 show_all_ex=st.checkbox('Show All Exclusives (other brands)',False,key='app_show_all')
 if not show_all_ex:
  render_brand_exclusives_section(comp,'app_ex',compact=False)
 else:
  for bc in PLAYABLE:
   if bc!=comp:
    st.markdown(f'### {bc} (other brand — warnings apply)')
    render_brand_exclusives_section(bc,f'app_all_{bc}',compact=True,show_suggestions=False)
  render_brand_exclusives_section(comp,'app_ex',compact=False)
 tab_run,tab_cameo=st.tabs(['Run Appearance','Creative Cameo / Script Generator'])
 with tab_run:
  st.info(f'**{comp}** lanes active. NXT = Hollywood/Netflix/Oscars/Olympics. SmackDown = Grammys/music/TV. WCW = NBA/NFL/ESPN/CBS.')
  c1,c2=st.columns(2)
  with c1:
   person_type=st.selectbox('Person Type',['Wrestler','Staff / Owner / GM / Announcer'],key='app_pt')
   if person_type=='Wrestler': person=clean_name_selector('Select wrestler','app_pw',company=comp,entity_type='Wrestler',default_company=comp,label_search='Search wrestler')
   else:
    sl=clean_name_selector('Select staff','app_ps',company=comp,entity_type='Staff',default_company=comp,label_search='Search staff')
    person=(sl.split(' — ')[0] if sl else '—')
   lane_pool=APPEARANCE_LANES[comp]+([a for bc in PLAYABLE if bc!=comp for a in APPEARANCE_LANES[bc]] if show_all_ex else [])
   app=st.selectbox('Appearance Type',lane_pool,key='app_lane')
   week=st.number_input('Week / Date Slot',1,52,st.session_state.week+1,key='app_wk')
   notes=st.text_area('Notes / storyline connection',key='app_notes')
   ok_ex,warn_ex=check_exclusive_brand(comp,app)
   if not ok_ex: st.warning(warn_ex)
   force=st.checkbox('Force cross-brand appearance',value=False,key='app_force') if not ok_ex else False
   if st.button('Run Appearance',key='app_run'):
    if not ok_ex and not force:
     st.error('Check Force to confirm cross-brand exclusive on '+comp+'.')
    else:
     success,msg=run_brand_exclusive(comp,app,person,week,notes,force=(not ok_ex and force))
     if success: st.success(msg); st.rerun()
     else: st.error(msg)
  with c2:
   with bfg_card(f'{comp} Appearance Lane'):
    [st.write('• '+x) for x in APPEARANCE_LANES[comp]]
    if comp=='NXT': st.caption('NXT owns major entertainment crossover lanes unless another brand forces them.')
 with tab_cameo:
  st.markdown('<div class="helper-note"><b>NXT Creative Cameo Generator</b> — original scripts for Netflix, Marvel, DC, Hollywood, SNL, GMA, Olympics, Oscars, Comic-Con, Mattel/Barbie. Other brands need <b>Force NXT-style crossover</b>.</div>',unsafe_allow_html=True)
  g1,g2,g3=st.columns(3)
  with g1:
   cg_pt=st.selectbox('Person type',['Wrestler','Staff / Owner / GM'],key='cg_pt')
   if cg_pt=='Wrestler':
    cg_person=clean_name_selector('Wrestler','cg_p',company=comp,entity_type='Wrestler',default_company=comp) if opts(comp) else '—'
    cg_w=find(cg_person) if cg_person!='—' else None
    cg_staff=None
   else:
    cg_sl=clean_name_selector('Staff','cg_s',company=comp,entity_type='Staff',default_company=comp)
    cg_staff=get_staff(comp,cg_sl) if cg_sl else None
    cg_person=cg_staff['name'] if cg_staff else ((cg_sl.split(' — ')[0] if cg_sl else '—'))
    cg_w=None
  with g2:
   partner_list=NXT_CAMEO_PARTNERS if comp=='NXT' else NXT_CAMEO_PARTNERS+['Grammys','ESPN','CBS','Paramount Plus']
   cg_partner=st.selectbox('Appearance partner',partner_list,key='cg_part')
   cg_project=st.selectbox('Project type',CAMEO_PROJECT_TYPES,key='cg_proj')
   cg_tone=st.selectbox('Tone',CAMEO_TONES,key='cg_tone')
  with g3:
   cg_length=st.selectbox('Length / filming',CAMEO_LENGTHS,key='cg_len')
   cg_week=st.number_input('Week / date',1,52,st.session_state.week+1,key='cg_wk')
   cg_risk=st.selectbox('Risk level',['Low','Medium','High'],key='cg_risk')
  cg_story=st.text_area('Storyline tie-in',key='cg_story')
  cga,cgb=st.columns(2)
  cg_rival=cga.text_input('Rival mentioned',key='cg_riv')
  cg_sponsor=cgb.text_input('Sponsor involved',key='cg_spon')
  cg_force=cgb.checkbox('Force NXT-style crossover on non-NXT brand',value=False,key='cg_force')
  ok,msg=cameo_allowed(comp,cg_partner,cg_force)
  if not ok: st.error(msg)
  elif msg: st.warning(msg)
  warns=cameo_fit_warnings(cg_person,cg_partner,cg_project,cg_w) if cg_w else []
  if warns:
   with bfg_card('AI Warnings'):
    for wn in warns: st.write('• '+wn)
  preview_eff=calc_cameo_effects(cg_w,cg_partner,cg_project,cg_tone,cg_risk,cg_length) if cg_w else {}
  if cg_w:
   e1,e2,e3,e4=st.columns(4)
   e1.metric('Est. revenue',money(preview_eff.get('revenue',0))); e2.metric('Popularity',f"+{preview_eff.get('popularity',0)}")
   e3.metric('Stamina',preview_eff.get('stamina',0)); e4.metric('Miss-show risk',f"{int(preview_eff.get('miss_show_risk',0)*100)}%")
  st.subheader('Generate')
  btn_cols=st.columns(4)
  btn_i=0
  for btn_label,cfg in CAMEO_GENERATOR_BUTTONS.items():
   col=btn_cols[btn_i%4]; btn_i+=1
   if col.button(btn_label,key='cgbtn_'+slug(btn_label)[:40]):
    if not ok and not cg_force: st.error(msg or 'Partner not allowed.'); st.stop()
    proj=cfg.get('project') or cg_project
    part=cfg.get('partner') or cg_partner
    fields={'company':comp,'person':cg_person,'person_type':cg_pt,'partner':part,'project_type':proj,'tone':cg_tone,'length':cg_length,'week':int(cg_week),'storyline':cg_story,'rival':cg_rival,'sponsor':cg_sponsor,'risk':cg_risk,'wrestler_obj':cg_w,'staff_profile':cg_staff.get('style','') if cg_staff else '','warnings':warns}
    with st.spinner('Generating cameo content…'):
     script,ai_flag=generate_cameo_content(cfg['mode'],fields)
    save_cameo_record(fields,script,ai_flag,cfg['mode']); st.rerun()
  lc=st.session_state.get('last_cameo')
  if lc:
   lc=normalize_cameo_record(lc)
   st.subheader(fmt_display(lc.get('title'),'Generated Cameo'))
   st.caption(f"{fmt_display(lc.get('label'),'Saved')} · {fmt_display(lc.get('partner'))} · Week {lc.get('week', st.session_state.week)} · Risk {fmt_display(lc.get('risk_level'),'Low')}")
   st.text_area('Script / output',lc.get('script') or '',height=420,key='cg_script_view')
   st.write(f"**Revenue:** {money(lc.get('revenue',0))} · **Popularity:** +{lc.get('popularity_effect',0)} · **Morale:** {lc.get('morale_effect',0)} · **Stamina:** {lc.get('stamina_effect',0)} · **Sponsor:** +{lc.get('sponsor_effect',0)} · **Merch boost:** {money(lc.get('merchandise_boost',0))}")
   if fmt_display(lc.get('continuity_warning'),''): st.warning(lc['continuity_warning'])
   b1,b2,b3=st.columns(3)
   if b1.button('Save Script Only',key='cg_save_only'): st.success('Saved to Cameo Library.'); st.rerun()
   if b2.button('Apply Cameo To Game',key='cg_apply'):
    apply_cameo_record(lc); st.success('Cameo applied — revenue, stats, Twitter, history updated.'); st.rerun()
   if b3.button('Clear Preview',key='cg_clear'): st.session_state.last_cameo=None; st.rerun()
  with st.expander('Cameo Library (saved scripts)',expanded=False):
   for c in [normalize_cameo_record(x) for x in st.session_state.cameo_library[:15]]:
    script_snip=c.get('script') or ''
    preview=(script_snip[:280]+'…') if len(script_snip)>280 else script_snip
    st.markdown(f"<div class='event-box'><b>#{fmt_display(c.get('id'),'?')} Week {c.get('week',0)} — {fmt_display(c.get('company'))} — {fmt_display(c.get('person'))}</b><br>{fmt_display(c.get('partner'))} · {fmt_display(c.get('project_type'))} · {fmt_display(c.get('tone'))} · {money(c.get('revenue',0))} · {fmt_display(c.get('label'),'Saved')}<br><span class='small-text'>{preview or '—'}</span></div>",unsafe_allow_html=True)
 st.subheader('Appearance & Cameo History')
 for a in [normalize_appearance_record(x) for x in st.session_state.appearance_history[:25]]:
  extra=' · Script saved' if (a.get('script') or '').strip() else ''
  raw_notes=(a.get('notes') or '').strip()
  notes_snip=f" · {raw_notes}" if raw_notes else ''
  st.markdown(f"<div class='event-box'><b>Week {a.get('week',0)} — {fmt_display(a.get('company'))} — {fmt_display(a.get('appearance'))}</b><br>{fmt_display(a.get('person'))} | Revenue {money(a.get('revenue',0))} | Risk {appearance_risk_label(a)}{notes_snip}{extra}</div>",unsafe_allow_html=True)
elif page=='NXT Spotlight Studio':
 render_nxt_spotlight_studio_page()
elif page=='SmackDown Culture Pulse':
 render_smackdown_culture_pulse_page()
elif page=='WCW Sports Desk':
 render_wcw_sports_desk_page()
elif page=='NXT Unfiltered':
 ensure_nxt_unfiltered_hosts()
 set_active_brand('NXT')
 render_page_shell('NXT Unfiltered',comp='NXT',subtitle='NotebookLM-style deep-story podcast — NXT exclusive. Six hosts, optional AI voice/TTS, character psychology.',show_meter=True,show_badge=True)
 st.caption('NotebookLM-style deep-story podcast — exclusive to NXT. Goes beyond recap: real-life connections, character thought process, world-building, locker room/sponsor/fan reads. Paste full episodes, rivalries, PLE fallout, tweets, morale, and popularity movement.')
 ensure_ai_mode_prefs()
 st.session_state.pop('nxt_uf_last_ai_error',None)
 if builtin_ai_env_on():
  st.success('**Free mode** — full built-in podcast scripts + **Edge TTS** voices. No OpenAI key or billing needed.')
 else:
  st.checkbox(
   'Use built-in episode scripts (free — no OpenAI charges)',
   key='bfg_force_builtin_ai',
   help='Full NXT Unfiltered with all analysis sections.',
  )
  ai_status=get_ai_status()
  if ai_status.get('mode')=='openai':
   st.success(ai_status['message'])
  elif ai_status.get('mode')=='builtin':
   st.info(f"**{ai_status['message']}** {ai_status['help']}")
  else:
   st.warning(f"**{ai_status['message']}** {ai_status['help']}")
   render_openai_key_helper()
 uf_comp=st.selectbox('Company context',['NXT','SmackDown','WCW'],index=0,key='nxt_uf_co')
 force_uf=st.checkbox('Force use on non-NXT brand (override exclusivity)',key='nxt_uf_force')
 ok_uf,msg_uf=check_nxt_unfiltered_exclusive(uf_comp,force_uf)
 if not ok_uf: st.warning(msg_uf)
 draft=st.session_state.get('nxt_unfiltered_draft',{})
 m1,m2=st.columns(2)
 with m1:
  ep_title=st.text_input('Episode title',draft.get('episode_title',''),key='nxt_uf_title')
  week_n=st.number_input('Week number',1,52,int(draft.get('week',st.session_state.week+1)),key='nxt_uf_week')
  rel_show=st.text_input('Related NXT show',draft.get('related_show',''),key='nxt_uf_show')
  rel_ple=st.text_input('Related PLE',draft.get('related_ple',''),key='nxt_uf_ple')
  main_story=st.text_input('Main story / rivalry',draft.get('main_story',''),key='nxt_uf_story')
  main_chars=st.text_input('Main characters involved (comma-separated)',draft.get('main_characters',''),key='nxt_uf_chars')
 with m2:
  tweets=st.text_area('Controversial tweets to discuss',draft.get('controversial_tweets',''),height=100,key='nxt_uf_tweets')
  morale_n=st.text_area('Morale notes',draft.get('morale_notes',''),height=80,key='nxt_uf_morale')
  pop_n=st.text_area('Popularity changes',draft.get('popularity_changes',''),height=80,key='nxt_uf_pop')
  ple_fall=st.text_area('PLE fallout',draft.get('ple_fallout',''),height=80,key='nxt_uf_fall')
  user_n=st.text_area('User notes',draft.get('user_notes',''),height=80,key='nxt_uf_notes')
 story_text=st.text_area('Story text (paste full episode / story — no word limit)',draft.get('story_text',st.session_state.get('long_story_draft','')),height=520,key='nxt_uf_body')
 hcount=st.selectbox('Host Count',['2 Hosts','3 Hosts','4 Hosts','5 Hosts','All 6 Hosts'],key='nxt_uf_hcount')
 max_h=6 if hcount=='All 6 Hosts' else int(hcount[0])
 all_hosts=opts_podcast_hosts('NXT')
 default_hosts=draft.get('host_lineup',all_hosts[:max_h])
 sel_hosts=st.multiselect('Select hosts for this episode',all_hosts,default=[h for h in default_hosts if h in all_hosts][:max_h],max_selections=max_h,key='nxt_uf_hosts')
 tone=st.selectbox('Podcast tone',NXT_UNFILTERED_TONES,key='nxt_uf_tone')
 length=st.selectbox('Podcast length',NXT_UNFILTERED_LENGTHS,index=0,key='nxt_uf_len')
 spec_len=get_nxt_unfiltered_length_spec(length)
 st.caption(f"Target ~{spec_len.get('target_minutes',10)} min spoken · {spec_len.get('min_lines',80)}+ host lines · natural back-and-forth")
 with bfg_card('Host lineup preview'):
  for hn in sel_hosts:
   h=get_nxt_unfiltered_host(hn); c1,c2=st.columns([.12,.88])
   with c1: show_entity_img(hn,'podcast_host',64)
   with c2: st.write(f"**{hn}** — {h.get('identity','')}"); st.caption(h.get('podcast_role',''))
  apply_buzz_chk=st.checkbox('Apply NXT Unfiltered Buzz To Universe (requires Apply button below)',key='nxt_uf_buzz_chk')
  fields={'episode_title':ep_title,'week':week_n,'related_show':rel_show,'related_ple':rel_ple,'main_story':main_story,'main_characters':main_chars,'controversial_tweets':tweets,'morale_notes':morale_n,'popularity_changes':pop_n,'ple_fallout':ple_fall,'user_notes':user_n,'story_text':story_text,'tone':tone,'length':length,'host_count_label':hcount}
  st.session_state.nxt_unfiltered_draft={**fields,'host_lineup':sel_hosts,'host_count':hcount}
  g1,g2,g3=st.columns(3)
  if g1.button('Generate NXT Unfiltered Episode',key='nxt_uf_gen',disabled=not ok_uf and not force_uf):
   if len(sel_hosts)<2: st.error('Select at least 2 hosts.'); st.stop()
   if len(sel_hosts)>max_h: st.error(f'Select at most {max_h} hosts for {hcount}.'); st.stop()
   script,ai_used,ai_note=generate_nxt_unfiltered_episode(fields,sel_hosts)
   rec=save_nxt_unfiltered_episode(fields,script,ai_used,sel_hosts)
   st.session_state.last_nxt_unfiltered=rec
   if ai_used:
    st.success(f"Episode generated ({rec['label']})."); st.rerun()
   else:
    st.success(f"Episode generated ({rec['label']}). {ai_note or 'Built-in script engine.'}")
    st.rerun()
  if g2.button('Save draft to episode library',key='nxt_uf_save_draft'):
   if not sel_hosts: st.error('Select hosts first.'); st.stop()
   rec=save_nxt_unfiltered_episode(fields,st.session_state.get('last_nxt_unfiltered',{}).get('script','(draft — generate script first)'),False,sel_hosts)
   st.toast('Draft saved to NXT Unfiltered library.')
 lc=st.session_state.get('last_nxt_unfiltered')
 if lc and lc.get('script'):
  st.subheader(lc.get('episode_title') or 'Latest Episode')
  est=estimate_podcast_runtime_minutes(lc.get('script',''))
  tgt=get_nxt_unfiltered_length_spec(lc.get('length','Full Episode (~10 min)')).get('target_minutes',10)
  st.caption(f"Hosts: {', '.join(lc.get('host_lineup',[]))} · {lc.get('tone','')} · {lc.get('length','')} · {lc.get('label','')} · Script ~{est} min (target ~{tgt} min)")
  st.text_area('Podcast script',lc['script'],height=480,key='nxt_uf_script_view')
  host_objs=[get_nxt_unfiltered_host(n) for n in lc.get('host_lineup',[])]
  ff=find_ffmpeg()
  ensure_nxt_uf_voice_prefs()
  vm=get_nxt_uf_voice_mode()
  vm_label={'free_edge':'Edge TTS (free)','free_browser':'Browser voice (free)','premium_openai':'Premium OpenAI (your key)','premium_elevenlabs':'Premium ElevenLabs (your key)'}.get(vm,'Free')
  st.caption(f"Voice mode: **{vm_label}** · ffmpeg: **{'ready — separate host voices' if ff else 'not found — single narrator track'}**")
  st.markdown('#### Hear the episode (host voices — not background music)')
  st.caption('Step 1: Generate script above · Step 2: Click **Generate audio** below · Step 3: Press **Play** on the player (check device volume).')
  audio_path=resolve_audio_path(lc.get('audio_path',''))
  tts_msg=''
  ac1,ac2,ac3=st.columns(3)
  gen_preview=ac1.button('Quick audio preview (~2 min)',key='nxt_uf_tts_preview')
  gen_audio=ac2.button('Generate full podcast audio',type='primary',key='nxt_uf_tts_btn')
  if ac3.button('Clear saved audio',key='nxt_uf_tts_clear'):
   lc['audio_path']=''
   st.session_state.last_nxt_unfiltered=lc
   st.rerun()
  if gen_preview or gen_audio:
   cap=18 if gen_preview else None
   label='Quick preview' if gen_preview else 'Full episode'
   with st.spinner(f'{label}: building voices (Edge TTS)…'):
    audio_path,tts_msg=try_nxt_unfiltered_tts(lc['script'],host_objs,max_segments=cap)
   if audio_path:
    audio_path=resolve_audio_path(audio_path)
    lc['audio_path']=audio_path
    st.session_state.last_nxt_unfiltered=lc
    st.session_state.nxt_uf_last_tts_msg=tts_msg
    for ep in st.session_state.get('nxt_unfiltered_episodes',[]):
     if ep.get('id')==lc.get('id'): ep['audio_path']=audio_path
    st.rerun()
   else:
    st.session_state.nxt_uf_last_tts_msg=tts_msg
    st.error(tts_msg or 'Audio generation failed.')
  elif audio_path and Path(audio_path).exists():
   tts_msg=st.session_state.get('nxt_uf_last_tts_msg','Press Play below.')
  else:
   tts_msg='No audio yet — click **Quick audio preview** or **Generate full podcast audio**. Voice mode **Edge TTS** recommended.'
  if tts_msg:
   if audio_path and Path(audio_path).exists(): st.success(tts_msg)
   else: st.info(tts_msg)
  if audio_path and Path(audio_path).exists():
   try: st.audio(audio_path,format='audio/mp3',autoplay=True)
   except TypeError: st.audio(audio_path,format='audio/mp3')
   with open(audio_path,'rb') as af:
    st.download_button('Download MP3',af.read(),file_name=Path(audio_path).name,mime='audio/mpeg',key='nxt_uf_dl')
  elif get_nxt_uf_voice_mode()=='free_browser':
   st.info('**Browser voice mode** — MP3 player is hidden. Click the purple button below to hear hosts in your browser.')
   render_browser_tts_player(lc['script'],f'bfg_tts_{lc.get("id",0)}')
  with st.expander('Voice mode & premium API (optional)',expanded=False):
   st.caption('Scripts are always free. Premium voice uses **your** API key — the app owner does not pay for your usage.')
   _voice_opts=['free_edge','free_browser','premium_openai','premium_elevenlabs']
   _voice_labels={'free_edge':'Free — Edge TTS (recommended)','free_browser':'Free — Browser voice (play in tab)','premium_openai':'Premium — OpenAI natural voice','premium_elevenlabs':'Premium — ElevenLabs voice'}
   _vi=_voice_opts.index(get_nxt_uf_voice_mode()) if get_nxt_uf_voice_mode() in _voice_opts else 0
   st.session_state.nxt_uf_voice_mode=st.selectbox('Voice mode',_voice_opts,format_func=lambda x:_voice_labels[x],index=_vi,key='nxt_uf_voice_sel')
   if get_nxt_uf_voice_mode().startswith('premium'):
    st.warning('Premium AI voice may cost money through your API provider. You are responsible for your own API usage.')
    st.session_state.nxt_uf_premium_cost_ok=st.checkbox('I understand premium voice may cost money.',value=st.session_state.get('nxt_uf_premium_cost_ok',False),key='nxt_uf_cost_ok')
    if get_nxt_uf_voice_mode()=='premium_openai':
     st.session_state.nxt_uf_user_openai_key=st.text_input('Your OpenAI API key (session only)',type='password',key='nxt_uf_user_oai_key',placeholder='sk-...')
    if get_nxt_uf_voice_mode()=='premium_elevenlabs':
     st.session_state.nxt_uf_user_elevenlabs_key=st.text_input('Your ElevenLabs API key (session only)',type='password',key='nxt_uf_user_el_key')
     st.caption('Optional: set `elevenlabs_voice_id` on hosts in code for custom voices.')
   else:
    st.session_state.nxt_uf_premium_cost_ok=False
   tts_sp=st.slider('Default speaking speed',0.85,1.25,float(st.session_state.get('nxt_uf_tts_speed',1.0)),0.01,key='nxt_uf_tts_spd')
   tts_en=st.slider('Default energy',0.5,1.0,float(st.session_state.get('nxt_uf_tts_energy',0.9)),0.05,key='nxt_uf_tts_nrg')
   st.session_state.nxt_uf_tts_speed=tts_sp; st.session_state.nxt_uf_tts_energy=tts_en
   for hn in lc.get('host_lineup',[]):
    h=get_nxt_unfiltered_host(hn)
    c1,c2,c3=st.columns(3)
    with c1: h['tts_voice']=st.selectbox(f'{hn} voice',PODCAST_TTS_VOICES,index=PODCAST_TTS_VOICES.index(h.get('tts_voice','neutral')) if h.get('tts_voice') in PODCAST_TTS_VOICES else 0,key=f'nxt_tts_{hn}_{lc.get("id")}')
    with c2: h['tts_speed']=st.slider(f'{hn} speed',0.85,1.25,float(h.get('tts_speed',tts_sp)),0.01,key=f'nxt_spd_{hn}_{lc.get("id")}')
    with c3: h['tts_energy']=st.slider(f'{hn} energy',0.5,1.0,float(h.get('tts_energy',tts_en)),0.05,key=f'nxt_nrg_{hn}_{lc.get("id")}')
    st.session_state.nxt_unfiltered_hosts[hn]=h
  b1,b2,b3=st.columns(3)
  if b1.button('Save script to library',key='nxt_uf_save_script'): st.success('Already in episode library.'); st.rerun()
  if b2.button('Apply Buzz To Universe',key='nxt_uf_apply',disabled=not apply_buzz_chk):
   apply_nxt_unfiltered_buzz(lc); st.success('Buzz applied — rivalry heat, fan investment, Twitter buzz, NXT prestige.'); st.rerun()
  if b3.button('Clear preview',key='nxt_uf_clear'): st.session_state.last_nxt_unfiltered=None; st.rerun()
 with st.expander('NXT Unfiltered episode library',expanded=False):
  for ep in st.session_state.get('nxt_unfiltered_episodes',[])[:20]:
   st.markdown(f"<div class='event-box'><b>#{ep.get('id')} Week {ep.get('week')} — {ep.get('episode_title','Untitled')}</b><br>Hosts: {', '.join(ep.get('host_lineup',[]))} · {ep.get('tone','')} · {ep.get('length','')} · {ep.get('label','')} · Buzz applied: {ep.get('effects_applied',False)}<br><span class='small-text'>{(ep.get('script','')[:240]+'…') if len(ep.get('script',''))>240 else ep.get('script','')}</span></div>",unsafe_allow_html=True)
elif page=='Trade Center':
 render_page_shell('Trade Center',subtitle='Multiplayer trades — proposal, acceptance, optional Admin approval.',use_brand_tabs=True,tabs_label='Brand',show_meter=True)
 st.caption('Multiplayer trades require proposal → acceptance → optional Admin approval before wrestlers move.')
 tc_co=st.session_state.get('assigned_company') if st.session_state.get('assigned_company') in PLAYABLE else st.session_state.get('active_brand','NXT')
 render_money_meter(tc_co,compact=False,show_ticker=True,show_sponsor=False)
 for co in PLAYABLE:
  if crisis.is_financial_crisis(co): render_financial_crisis_panel(co,show_tools=False,key_prefix=f'tc_{co}')
 ac=st.session_state.get('assigned_company')
 if ac in PLAYABLE:
  from_comp=ac; to_choices=[c for c in PLAYABLE if c!=ac]
 else:
  from_comp=None; to_choices=PLAYABLE
 a,b=st.columns(2)
 with a:
  if ac not in PLAYABLE: from_comp=st.selectbox('Offering Company',PLAYABLE,key='tc1')
  else: st.write(f'**Offering company:** {from_comp}')
  offer=clean_name_multiselect('Offer wrestlers','tc_offer',options=opts(from_comp),default_company=from_comp,default_entity='Wrestler')
  cash=st.number_input('Cash Offered',0,50000000,0,step=100000)
 with b:
  to_comp=st.selectbox('Receiving Company',to_choices or PLAYABLE,key='tc2')
  request=clean_name_multiselect('Request wrestlers','tc_req',options=opts(to_comp),default_company=to_comp,default_entity='Wrestler')
  loan=st.checkbox('Loan Trade 1-3 months')
 can_propose=can_edit_company(from_comp)
 def trade_value(names,cash=0):
  return cash/100000 + sum((find(n) or {'overall':75,'popularity':50,'momentum':50})['overall']*2+(find(n) or {'popularity':50})['popularity'] for n in names)
 fair=trade_value(offer,cash)-trade_value(request,0)
 st.metric('Trade Fairness Score',round(fair,1))
 traded_champs=[n for n in offer+request if is_champ(n)]
 if traded_champs: st.warning(f"Champion(s) in trade: {', '.join(traded_champs)}. Vacate titles manually if needed.")
 if not can_propose: render_edit_only_notice(from_comp)
 if st.button('Propose Trade',disabled=not can_propose,key='tc_propose'):
  if cash>0 and get_company_budget(from_comp)<cash: st.error(f'{from_comp} lacks {money(cash)}.')
  else:
   prop={'id':len(st.session_state.pending_trades)+1,'week':st.session_state.week,'from':from_comp,'to':to_comp,'offer':offer,'request':request,'cash':cash,'loan':loan,'fairness':fair,'champions':traded_champs,'status':'Proposed','proposed_by':st.session_state.player_name,'proposed_at':date.today().isoformat()}
   st.session_state.pending_trades.insert(0,prop); save_pending_trades()
   st.success(f'Trade proposed to {to_comp} GM.'); st.rerun()
 st.subheader('Pending trade proposals')
 for i,tr in enumerate(list(st.session_state.pending_trades)):
  st.markdown(f"<div class='event-box'><b>#{tr.get('id')} Week {tr.get('week')} — {tr.get('status')}</b><br>{tr['from']} offers {', '.join(tr.get('offer',[])) or '—'} + {money(tr.get('cash',0))} for {', '.join(tr.get('request',[]))} · Fairness {tr.get('fairness')}</div>",unsafe_allow_html=True)
  c1,c2,c3,c4=st.columns(4)
  if tr.get('status')=='Proposed':
   if c1.button('Accept',key=f'tc_acc_{i}',disabled=not (can_edit_company(tr['to']) or is_admin())):
    tr['status']='Accepted'; tr['accepted_by']=st.session_state.player_name; save_pending_trades(); st.rerun()
   if c2.button('Reject',key=f'tc_rej_{i}',disabled=not (can_edit_company(tr['to']) or is_admin())):
    tr['status']='Rejected'; save_pending_trades(); st.rerun()
  if tr.get('status') in ('Accepted','Proposed') and c3.button('Admin Approve',key=f'tc_adm_{i}',disabled=not is_admin()):
   tr['status']='Admin Approved'; save_pending_trades(); st.rerun()
  if tr.get('status') in ('Accepted','Admin Approved') and c4.button('Complete Trade',key=f'tc_done_{i}',disabled=not (is_admin() or (can_edit_company(tr['from']) and tr.get('status')=='Accepted'))):
   execute_trade_transfer(tr); st.session_state.pending_trades=[x for x in st.session_state.pending_trades if x.get('id')!=tr.get('id')]
   save_pending_trades()
   tw=f"TRADE ALERT: {tr['from']} ↔ {tr['to']} — {', '.join(tr.get('offer',[]))} for {', '.join(tr.get('request',[]))}"
   if can_tweet_as_company(tr['from']):
    st.session_state.twitter_posts.insert(0,{'id':len(st.session_state.twitter_posts)+1,'week':st.session_state.week,'company':tr['from'],'wrestler':'Trade Desk','role':'Company','handle':'@BFGTrades','post_type':'Trade Rumor Reaction','text':tw,'likes':random.randint(2000,40000),'reposts':random.randint(200,8000),'replies':random.randint(100,3000),'views':random.randint(50000,500000),'mentions':'','effects':{},'viral':True,'ai_generated':False})
   st.success('Trade completed.'); st.rerun()
 st.subheader('Completed trade history')
 for tr in st.session_state.trade_history[:20]:
  st.markdown(f"<div class='event-box'><b>Week {tr.get('week')} — {tr.get('status','Completed')}</b><br>{tr.get('from')} ↔ {tr.get('to')} · {', '.join(tr.get('offer',[]))} for {', '.join(tr.get('request',[]))} · {money(tr.get('cash',0))}</div>",unsafe_allow_html=True)
elif page=='Sponsors':
 ui_pages.render_sponsor_objectives_page()
elif page=='Roster':
 render_page_shell('Roster',subtitle='Roster management for NXT, SmackDown, and WCW. Power Rankings are on a separate page.',show_meter=True)
 comp=roster_brand_tabs(key='rostbrand')
 ensure_wrestler_debut_fields(); ensure_contract_fields()
 if calendar_year_locked(): st.info('**Year Locked — Contracts Active.** Renew and sign talent on the **Contracts** page.')
 else: st.success('**Pre-Season Contract Editing Enabled** — edit salary and contract years on roster cards or Contracts page.')
 ensure_finance_state()
 fin=st.session_state.company_finance[comp]
 pay=fin['payroll']; rem=fin['current_budget']
 pb1,pb2,pb3,pb4=st.columns(4)
 pb1.metric('Starting Budget',money(fin['starting_budget'])); pb2.metric('Total Payroll',money(pay)); pb3.metric('Current Budget',money(rem)); pb4.metric('Singles on Payroll',len(payroll_wrestlers(comp)))
 st.caption('Payroll counts individual wrestlers only (tag team unit salaries are sums of member contracts).')
 div_opts=sorted(set(['Guest Star','Roster']+COMPANIES[comp]['titles']+[w['division'] for w in roster(comp)]))
 st.session_state.roster_show_staff=st.checkbox('Show staff section',st.session_state.get('roster_show_staff',True),key='rost_staff_toggle')
 with st.spinner(f'Loading {comp} roster…'):
  all_w=roster(comp)
  singles_all=[w for w in all_w if is_singles_entry(w)]
  tags_all=[w for w in all_w if is_tag_team_entry(w) and is_team_active(comp,w['name'])]
  inactive_tags=[w for w in all_w if is_tag_team_entry(w) and not is_team_active(comp,w['name'])]
  women_all=[w for w in all_w if is_women_entry(w)]
 fc1,fc2,fc3,fc4,fc5=st.columns(5)
 with fc1: search=st.text_input('Search by name','',key=f'rost_search_{comp}')
 with fc2: div_f=st.selectbox('Division',['All']+sorted(set(w['division'] for w in all_w)),key=f'rost_div_{comp}')
 with fc3: align_f=st.selectbox('Alignment',['All','F','H','N'],key=f'rost_align_{comp}')
 with fc4: status_f=st.selectbox('Status',['All','Active','Injured','Suspended','Part-Time'],key=f'rost_stat_{comp}')
 with fc5: sort_by=st.selectbox('Sort',['Alphabetical','Overall high to low','Popularity high to low','Momentum high to low','Record best to worst','Salary high to low','Division'],key=f'rost_sort_{comp}')
 debut_f=st.selectbox('Debut filter',['All','Not Debuted','Debuted','Ignored After Debut','Returning Soon','On Hiatus'],key=f'rost_debut_{comp}')
 ff1,ff2,ff3,ff4,ff5,ff6=st.columns(6)
 with ff1: show_singles=ff1.checkbox('Singles only',False,key=f'f_sing_{comp}')
 with ff2: show_tags=ff2.checkbox('Tag teams only',False,key=f'f_tag_{comp}')
 with ff3: show_women=ff3.checkbox('Women only',False,key=f'f_wom_{comp}')
 with ff4: show_champs=ff4.checkbox('Champions only',False,key=f'f_champ_{comp}')
 with ff5: show_staff_f=ff5.checkbox('Staff only',False,key=f'f_staff_{comp}')
 with ff6: per=st.selectbox('Per page',[4,6,8,10],index=1,key=f'rost_per_{comp}')
 def apply_view_pool(pool):
  pool=filter_roster_list(pool,search,div_f,align_f,status_f,show_champs,comp,debut_f)
  return sort_roster_list(pool,sort_by)
 if show_staff_f:
  st.info('Staff-only filter active — see Staff section below.')
  singles_v,tags_v,women_v=[],[],[]
 else:
  singles_v=apply_view_pool(singles_all) if not show_tags and not show_women else []
  tags_v=apply_view_pool(tags_all) if not show_singles and not show_women else []
  women_v=apply_view_pool(women_all) if not show_singles and not show_tags else []
  if show_singles: singles_v=apply_view_pool(singles_all); tags_v=[]; women_v=[]
  if show_tags: tags_v=apply_view_pool(tags_all); singles_v=[]; women_v=[]
  if show_women: women_v=apply_view_pool(women_all); singles_v=[]; tags_v=[]
 m1,m2,m3,m4=st.columns(4)
 m1.metric('Singles',len(singles_v)); m2.metric('Tag Teams',len(tags_v)); m3.metric("Women's",len(women_v)); m4.metric('Total',len(all_w))
 tab_singles,tab_tags,tab_women,tab_staff,tab_factions=st.tabs(['Singles Roster',f'Tag Teams / Factions ({len(tags_v)})',f"Women's Roster ({len(women_v)})",'Staff','Factions'])
 with tab_singles:
  if show_tags or show_women: st.info('Clear Tag teams only / Women only filters to view singles.')
  elif not singles_v: st.info('No singles match your filters.')
  else:
   pages=max(1,(len(singles_v)+per-1)//per); pg=st.number_input('Singles page',1,pages,1,key=f'pg_sing_{comp}')
   st.caption(f'Page {pg} of {pages}')
   for w in singles_v[(pg-1)*per:pg*per]: render_wrestler_card(w,comp,div_opts,f'sing_{comp}_')
 with tab_tags:
  can_edit=can_edit_company(comp)
  with st.expander('Create new tag team',expanded=False):
   st.caption('Form a new team from singles on this brand (2–4 wrestlers). They stay on the roster as individuals and link to the team for booking & Twitter.')
   tname=st.text_input('Team name',placeholder='e.g. Iron Syndicate',key=f'mk_team_name_{comp}')
   pool=opts_available_tag_members(comp)
   if len(pool)<2:
    st.warning(f'Need at least 2 available wrestlers on {comp} (not already on an active tag team).')
   else:
    mc1,mc2=st.columns(2)
    with mc1:
     mem1=clean_name_selector('Wrestler 1',f'mk_m1_{comp}',options=pool,company=comp,entity_type='Wrestler',label_select='Member 1',show_search=True)
     mem2=clean_name_selector('Wrestler 2',f'mk_m2_{comp}',options=pool,company=comp,entity_type='Wrestler',label_select='Member 2',show_search=True)
    with mc2:
     mem3=clean_name_selector('Wrestler 3 (optional)',f'mk_m3_{comp}',options=['']+pool,current='',company=comp,entity_type='Wrestler',label_select='Member 3',show_search=True)
     mem4=clean_name_selector('Wrestler 4 (optional)',f'mk_m4_{comp}',options=['']+pool,current='',company=comp,entity_type='Wrestler',label_select='Member 4',show_search=True)
    oc1,oc2,oc3=st.columns(3)
    mk_align=oc1.selectbox('Team alignment',['F','H','N'],key=f'mk_align_{comp}')
    mk_sal=oc2.number_input('Team salary (unit)',300000,5000000,int(900000),step=50000,key=f'mk_sal_{comp}')
    mk_ovr=oc3.number_input('Team overall (0 = auto from members)',0,100,0,key=f'mk_ovr_{comp}')
    members_pick=[m for m in [mem1,mem2,mem3,mem4] if m and m.strip()]
    if st.button('Create tag team',type='primary',key=f'mk_team_go_{comp}',disabled=not can_edit or len(pool)<2):
     ok,msg=create_tag_team(comp,tname,members_pick,mk_align,mk_ovr if mk_ovr>0 else None,mk_sal)
     if ok:
      touch_universe_meta(comp); save_universe(); st.success(msg); st.rerun()
     else: st.error(msg)
   if not can_edit: render_edit_only_notice(comp)
  if show_singles or show_women: st.info('Clear Singles only / Women only filters to view tag teams.')
  elif not tags_v: st.info('No tag teams match your filters — create one above or clear filters.')
  else:
   pages=max(1,(len(tags_v)+per-1)//per); pg=st.number_input('Tag teams page',1,pages,1,key=f'pg_tag_{comp}')
   for tw in tags_v[(pg-1)*per:pg*per]: render_tag_team_card(tw,comp)
  if inactive_tags:
   with st.expander(f'Inactive / broken-up teams ({len(inactive_tags)})'):
    for tw in inactive_tags:
     st.markdown(f"<div class='small-text'><b>{tw['name']}</b> — inactive tag team slot (members remain on singles roster)</div>",unsafe_allow_html=True)
 with tab_women:
  if not women_all: st.info(f"No women's division wrestlers listed for {comp} yet. Add wrestlers with a Women's division.")
  elif show_singles or show_tags: st.info('Clear other filters to view women\'s roster.')
  elif not women_v: st.info('No women\'s roster entries match filters.')
  else:
   pages=max(1,(len(women_v)+per-1)//per); pg=st.number_input('Women page',1,pages,1,key=f'pg_wom_{comp}')
   for w in women_v[(pg-1)*per:pg*per]: render_wrestler_card(w,comp,div_opts,f'wom_{comp}_')
 with tab_staff:
  if not st.session_state.roster_show_staff: st.info('Enable Show staff section above.')
  else:
   for s in st.session_state.staff.get(comp,[]):
    c1,c2=st.columns([.2,.8])
    with c1: show_entity_img(s['name'],'commentator',80)
    with c2:
     st.markdown(f"<b>{s['name']}</b> · {s['role']}",unsafe_allow_html=True)
     st.markdown(f"<div class='small-text'>{s.get('handle','')} · {s.get('style','')}</div>",unsafe_allow_html=True)
 with tab_factions:
  for fac in COMPANY_FACTIONS.get(comp,[]):
   st.markdown(f"<div class='event-box'><b>{fac}</b> — {comp} faction</div>",unsafe_allow_html=True)
 with st.expander('Add roster member',expanded=False):
  n1=st.text_input('Name',key=f'add_name_{comp}'); ovr=st.number_input('Overall',50,100,80,key=f'add_ovr_{comp}')
  aln=st.selectbox('Alignment',['F','H','N'],key=f'add_aln_{comp}'); sal=st.number_input('Salary',100000,20000000,500000,step=50000,key=f'add_sal_{comp}')
  frm=st.text_input('From / hometown','',key=f'add_from_{comp}')
  div_new=st.selectbox('Division',div_opts,key=f'add_div_{comp}')
  if st.button('Add to roster',key=f'add_btn_{comp}') and n1.strip():
   if find(n1.strip()): st.error('Wrestler already exists.')
   else:
    nw=W(n1.strip(),comp,div_new,ovr,aln,sal); loc=frm or HOMETOWNS.get(n1.strip(),'Unknown'); nw['from_location']=loc; nw['hometown']=loc
    seed_default_contract(nw); st.session_state.roster.append(nw); fix_roster_divisions(); apply_default_hometowns(); sync_company_payroll_stats(); st.success(f'Added {n1}'); st.rerun()
elif page=='Champions':
 ensure_champion_state()
 comp=roster_brand_tabs(key='champbrand')
 render_brand_badge(comp)
 section_header('Champions', comp)
 render_money_meter(comp,compact=True,show_ticker=True,show_sponsor=False)
 render_brand_permission_banner(comp)
 st.markdown(f"<div class='helper-note'><b>{comp} Champion Showcase</b> — current titleholders only. Use <b>Edit Champion</b> on a card to change a champion; upload belt and portrait images in <b>Picture Manager</b>. (Separate from Roster, Power Rankings, and Book Show.)</div>",unsafe_allow_html=True)
 titles=COMPANIES[comp]['titles']
 st.caption(f'{comp} · **{len(titles)} championships** — all titleholders on this page')
 for title in titles:
  render_champion_card(comp,title)
elif page=='Power Rankings':
 st.markdown('<div class="section-header">Power Rankings</div>',unsafe_allow_html=True)
 ensure_wrestler_debut_fields()
 st.session_state.rankings_include_not_debuted=st.checkbox('Include Not Debuted wrestlers in rankings',st.session_state.get('rankings_include_not_debuted',False),key='pr_include_nd')
 update_rank()
 comp_f=brand_filter_tabs('Brand',key='prbrand',include_all=True)
 rows=rankings_for_brand(comp_f)
 pr_per=st.selectbox('Rankings per page',[10,15,20,25],index=1,key='pr_per')
 pr_pages=max(1,(len(rows)+pr_per-1)//pr_per); pr_pg=st.number_input('Rankings page',1,pr_pages,1,key='pr_pg')
 page_rows=rows[(pr_pg-1)*pr_per:pr_pg*pr_per]
 tab=st.tabs(['Current Rankings','Last Week Rankings','Biggest Risers','Biggest Fallers','Why They Moved'])
 with tab[0]:
   st.caption(f'{comp_f} · Page {pr_pg}/{pr_pages}')
   for r in page_rows: render_rank_row(r)
 with tab[1]:
   prev=prev_rankings_for_brand(comp_f)
   st.caption(f'Last week snapshot · {comp_f}')
   lw_per=15; lw_pages=max(1,(len(prev)+lw_per-1)//lw_per); lw_pg=st.number_input('Last week page',1,lw_pages,1,key='lw_pg')
   for r in prev[(lw_pg-1)*lw_per:lw_pg*lw_per]:
    render_rank_row(r,compact=True)
 with tab[2]:
   risers=sorted([r for r in rows if isinstance(r.get('display_last_rank'),int) and r['display_last_rank']>r['display_rank']],key=lambda x:x['display_last_rank']-x['display_rank'],reverse=True)[:20]
   if not risers: st.write('No risers yet — run a show to record movement.')
   for r in risers: st.markdown(f"<div class='event-box'><b>{r['name']}</b> ({r['company']}) · {r['display_last_rank']} → #{r['display_rank']} · Score {r['score']}<br><span class='small-text'>{r['reason']}</span></div>",unsafe_allow_html=True)
 with tab[3]:
   fallers=sorted([r for r in rows if isinstance(r.get('display_last_rank'),int) and r['display_last_rank']<r['display_rank']],key=lambda x:x['display_rank']-x['display_last_rank'],reverse=True)[:20]
   if not fallers: st.write('No fallers yet — run a show to record movement.')
   for r in fallers: st.markdown(f"<div class='event-box'><b>{r['name']}</b> ({r['company']}) · {r['display_last_rank']} → #{r['display_rank']} · Score {r['score']}<br><span class='small-text'>{r['reason']}</span></div>",unsafe_allow_html=True)
 with tab[4]:
   why_per=12; why_pages=max(1,(len(rows)+why_per-1)//why_per); why_pg=st.number_input('Why page',1,why_pages,1,key='why_pg')
   for r in rows[(why_pg-1)*why_per:why_pg*why_per]:
    st.markdown(f"<div class='event-box'><b>{r['name']}</b> · {r['company']} · Movement {r.get('display_movement')}<br>{r['reason']}</div>",unsafe_allow_html=True)
elif page=='Attractions':
 st.markdown('<div class="section-header">Attractions</div>',unsafe_allow_html=True)
 st.caption('Exactly 6 attraction slots per in-game year.')
 if len(st.session_state.yearly_attractions)!=6: st.session_state.yearly_attractions=json.loads(json.dumps(ATTRACTIONS))[:6]
 year=max(1,st.session_state.get('year',1))
 if st.session_state.get('attraction_year')!=year: st.session_state.attractions_locked=False; st.session_state.attraction_year=year
 st.write(f"Attraction Year: **{st.session_state.attraction_year}** | Locked: **{st.session_state.attractions_locked}** | Slots: **{len(st.session_state.yearly_attractions)}/6**")
 c1,c2=st.columns(2)
 if c1.button('Lock Yearly Attractions',disabled=st.session_state.attractions_locked): st.session_state.attractions_locked=True; st.rerun()
 if c2.button('Reset Attractions'): st.session_state.yearly_attractions=json.loads(json.dumps(ATTRACTIONS)); st.session_state.attractions_locked=False; st.rerun()
 comp=brand_tabs('Company',key='attbrand')
 target_mode=st.selectbox('Target mode',['One wrestler','Multiple wrestlers','Whole roster','Men\'s division','Women\'s division','Champions only','Current rivalry talent','Hometown talent'])
 if target_mode=='One wrestler': target=[clean_name_selector('Wrestler','att_one',company=comp,entity_type='Wrestler',default_company=comp)]
 elif target_mode=='Multiple wrestlers': target=clean_name_multiselect('Wrestlers','att_multi',options=opts(comp),default_company=comp,default_entity='Wrestler')
 elif target_mode=='Whole roster': target=[w['name'] for w in roster(comp)]
 elif target_mode=='Champions only': target=[v for t,v in st.session_state.champions.get(comp,{}).items() if v!='Vacant' and v in opts(comp)]
 elif target_mode=='Current rivalry talent': target=[n for r in st.session_state.rivalries for n in r.get('wrestlers',[]) if find(n) and find(n)['company']==comp]
 else: target=clean_name_multiselect('Hometown talent','att_home',options=opts(comp),default_company=comp,default_entity='Wrestler')
 for i,a in enumerate(st.session_state.yearly_attractions):
   if not st.session_state.attractions_locked: a['name']=st.text_input('Name',a['name'],key=f'an{i}'); a['cost']=st.number_input('Cost',0,10000000,int(a['cost']),key=f'ac{i}'); a['description']=st.text_area('Description',a['description'],key=f'ad{i}')
   st.write(f"**{a['name']}** — {money(a['cost'])} — {a['description']}")
   if st.button(f"Use {a['name']}",key=f'use{i}'):
    ts=[find(x) for x in target if find(x)]
    if not ts: st.error('Select targets.')
    elif get_company_budget(comp)<a['cost']: st.error(f'{comp} does not have {money(a["cost"])} available.')
    else:
     add_transaction(comp,'Attraction Cost',f"{a['name']} attraction",-int(a['cost']))
     finance_flash(comp,-int(a['cost']),f"attraction: {a['name']}")
     for w in ts: w['morale']=min(100,w['morale']+a.get('morale_gain',0)); w['stamina']=min(100,w['stamina']+a.get('stamina_gain',0)); w['popularity']=min(100,w['popularity']+a.get('popularity_gain',0)); w['momentum']=min(100,w['momentum']+a.get('momentum_gain',0))
     st.session_state.attraction_history.insert(0,{'week':st.session_state.week,'name':a['name'],'targets':[w['name'] for w in ts],'cost':a['cost']}); update_rank({w['name']:f"{a['name']} affected them." for w in ts}); st.rerun()
elif page=='Random Event History':
 render_page_shell('Random Events',subtitle='Test, apply, and track random events — full history with stat changes and follow-ups.',use_brand_tabs=True,tabs_label='Brand',show_meter=True)
 ensure_wrestler_stats()
 evco=st.selectbox('Event company',PLAYABLE,key='rev_co')
 c1,c2,c3=st.columns(3)
 if c1.button('Generate Test Event'):
  tgt=random.choice(opts(evco))
  st.session_state.test_event_preview=build_random_event(evco,target=tgt); st.session_state.test_event_preview['status']='preview'
 if c2.button('Apply Test Event') and st.session_state.get('test_event_preview'):
  ev=dict(st.session_state.test_event_preview); ev['id']=len(st.session_state.random_event_history)+1; ev['status']='unresolved'; ev['bring_back']=True
  apply_random_event_record(ev)
  st.session_state.random_event_history.insert(0,ev)
  add_transaction(evco,'Random Event',f"{ev.get('event')} ({ev.get('target','')})",int(ev.get('money',0)))
  finance_flash(evco,int(ev.get('money',0)),f"random event applied")
  st.session_state.test_event_preview=None; st.rerun()
 if c3.button('Clear Test Preview'): st.session_state.test_event_preview=None; st.rerun()
 if st.session_state.get('test_event_preview'):
  pe=st.session_state.test_event_preview
  st.info(f"PREVIEW: {pe.get('event')} — {pe.get('target')} — {money(pe.get('money',0))} — {pe.get('description','')}")
 for ev in st.session_state.random_event_history[:30]:
  st.subheader(f"Week {ev['week']} / Month {ev.get('month','?')} — {ev['event']}")
  st.write(f"**Type:** {ev.get('event_type',ev.get('type',''))} | **Target:** {ev['target']} | **Money:** {money(ev.get('money',0))}")
  st.write(ev.get('description',ev.get('effect','')))
  if ev.get('storyline'): st.write(f"**Storyline:** {ev['storyline']}")
  if ev.get('ai_followup'): st.caption(f"AI follow-up: {ev['ai_followup']}")
  if ev.get('stat_changes'): st.write('**Stat changes:** '+', '.join(f"{k} {v:+}" for k,v in ev['stat_changes'].items()))
  ev['status']=st.selectbox('Status',['unresolved','resolved'],index=0 if ev.get('status')=='unresolved' else 1,key=f"evs{ev['id']}")
  ev['notes']=st.text_area('Notes',ev.get('notes',''),key=f"evn{ev['id']}")
  ev['bring_back']=st.checkbox('Bring This Back / Revisit Storyline',ev.get('bring_back',False),key=f"evb{ev['id']}")
elif page=='Rivalries':
 st.markdown('<div class="section-header">Rivalries</div>',unsafe_allow_html=True)
 comp=brand_tabs('Company',key='rivbrand')
 render_financial_crisis_panel(comp,show_tools=False,key_prefix=f'riv_{comp}')
 riv_edit=can_edit_company(comp)
 n1=clean_name_selector('Wrestler 1','rv1',company_filter=True,type_filter=True,default_company=comp,default_entity='All')
 n2=clean_name_selector('Wrestler 2','rv2',company_filter=True,type_filter=True,default_company=comp,default_entity='All')
 heat=st.slider('Heat',1,100,50,disabled=not riv_edit)
 if st.button('Add Rivalry',disabled=not riv_edit): st.session_state.rivalries.append({'name':f'{n1} vs {n2}','wrestlers':[n1,n2],'heat':heat,'status':'Active','company':comp}); touch_universe_meta(comp); save_universe(); st.rerun()
 for i,r in enumerate([x for x in st.session_state.rivalries if x.get('company',comp)==comp or 'company' not in x]):
   st.markdown('<div class="gm-card">',unsafe_allow_html=True); st.write(f"**{r['name']}** ({r.get('company',comp)})")
   r['heat']=st.slider('Heat',0,100,int(r.get('heat',50)),key=f'rh{i}',disabled=not riv_edit); r['status']=st.selectbox('Status',['Active','Paused','Ended'],key=f'rs{i}',disabled=not riv_edit)
   for n in r.get('wrestlers',[]): 
    w=find(n)
    if w: w['rivalry_heat']=r['heat']
elif page=='Character Editor':
 st.markdown('<div class="section-header">Character Editor</div>',unsafe_allow_html=True)
 edit_type=st.radio('Character Type',['Wrestler','Owner','GM','Commentator','Ring Announcer','Podcast Host','Company Account'],horizontal=True)
 comp=brand_tabs('Company',key='cedit')
 if edit_type=='Podcast Host':
  ensure_nxt_unfiltered_hosts()
  host_names=opts_podcast_hosts('NXT')
  hn=st.selectbox('Podcast Host',host_names,key='cedit_ph_name')
  p=get_nxt_unfiltered_host(hn)
  c1,c2=st.columns([.22,.78])
  with c1: show_entity_img(hn,'podcast_host',110)
  with c2:
   p['name']=st.text_input('Host name',p.get('name',hn),key=f'ph_name_{hn}')
   p['gender']=st.selectbox('Gender',['Female','Male','Non-binary'],index=['Female','Male','Non-binary'].index(p.get('gender','Female')) if p.get('gender') in ['Female','Male','Non-binary'] else 0,key=f'ph_g_{hn}')
   p['identity']=st.text_input('Identity',p.get('identity',''),key=f'ph_id_{hn}')
   p['personality']=st.text_area('Personality',p.get('personality',''),key=f'ph_per_{hn}')
   p['podcast_role']=st.text_area('Podcast role',p.get('podcast_role',''),key=f'ph_role_{hn}')
   p['speaking_style']=st.text_input('Speaking style',p.get('speaking_style',''),key=f'ph_spk_{hn}')
   p['strengths']=[x.strip() for x in st.text_area('Strengths (comma-separated)',', '.join(p.get('strengths',[])),key=f'ph_str_{hn}').split(',') if x.strip()]
   p['weaknesses']=[x.strip() for x in st.text_area('Weaknesses (comma-separated)',', '.join(p.get('weaknesses',[])),key=f'ph_weak_{hn}').split(',') if x.strip()]
   p['focuses_on']=[x.strip() for x in st.text_area('Focus areas (comma-separated)',', '.join(p.get('focuses_on',[])),key=f'ph_foc_{hn}').split(',') if x.strip()]
   p['should_not']=[x.strip() for x in st.text_area('Should not (comma-separated)',', '.join(p.get('should_not',[])),key=f'ph_not_{hn}').split(',') if x.strip()]
   p['bias']=st.text_input('Bias / tendency',p.get('bias',''),key=f'ph_bias_{hn}')
   p['catchphrase']=st.text_input('Catchphrase',p.get('catchphrase',''),key=f'ph_cat_{hn}')
   p['tts_voice']=st.selectbox('TTS voice style',PODCAST_TTS_VOICES,index=PODCAST_TTS_VOICES.index(p.get('tts_voice','neutral')) if p.get('tts_voice') in PODCAST_TTS_VOICES else 0,key=f'ph_tts_{hn}')
   tc1,tc2=st.columns(2)
   with tc1: p['tts_speed']=st.slider('TTS speed',0.85,1.25,float(p.get('tts_speed',1.0)),0.01,key=f'ph_spd_{hn}')
   with tc2: p['tts_energy']=st.slider('TTS energy',0.5,1.0,float(p.get('tts_energy',0.9)),0.05,key=f'ph_nrg_{hn}')
   p['bookable']=st.checkbox('Allow in match booking as performer',value=bool(p.get('bookable',False)),key=f'ph_book_{hn}')
   st.session_state.podcast_hosts_booking_enabled=st.checkbox('Enable podcast hosts globally in booking selectors',value=st.session_state.get('podcast_hosts_booking_enabled',False),key='ph_book_global')
  if p['name']!=hn:
   st.session_state.nxt_unfiltered_hosts[p['name']]=p
   st.session_state.nxt_unfiltered_hosts.pop(hn,None)
  else:
   st.session_state.nxt_unfiltered_hosts[hn]=p
  st.caption('NXT Unfiltered uses updated host personalities on the next generated episode.')
 elif edit_type in ('Owner','GM','Commentator','Ring Announcer','Company Account'):
  st.info(f'Edit **{edit_type}** profiles via **Company Home**, **Picture Manager**, or staff bible below (Staff types).')
  sl=clean_name_selector('Person','cedit_staff_mix',company=comp,entity_type='Staff' if edit_type!='Company Account' else 'Company Account',default_company=comp)
  if edit_type!='Company Account':
   staff=get_staff(comp,sl); n=staff['name'] if staff else sl.split(' — ')[0]
   st.session_state.staff_character_bible.setdefault(n,{'archetype':staff['role'],'promo':staff['style'],'should_do':[],'should_not':[],'notes':'','handle':staff['handle']})
   p=st.session_state.staff_character_bible[n]; p['archetype']=st.text_area('Archetype',p.get('archetype','')); p['promo']=st.text_area('Voice / style',p.get('promo',''))
   p['notes']=st.text_area('Notes',p.get('notes','')); show_entity_img(n,'commentator',100)
  else:
   st.caption('Company accounts post from Twitter / PR flows.')
 elif edit_type=='Wrestler':
   n=clean_name_selector('Wrestler','cedit_w',company_filter=True,type_filter=True,default_company=comp,default_entity='All')
   st.session_state.character_bible.setdefault(n,{'archetype':'Custom','promo':'','should_do':['advance story'],'should_not':['act out of character'],'notes':''})
   p=st.session_state.character_bible[n]; p['archetype']=st.text_area('Archetype',p.get('archetype','')); p['promo']=st.text_area('Promo style',p.get('promo',''))
   p['should_do']=[x.strip() for x in st.text_area('Should do (comma-separated)',', '.join(p.get('should_do',[]))).split(',') if x.strip()]
   p['should_not']=[x.strip() for x in st.text_area('Should not (comma-separated)',', '.join(p.get('should_not',[]))).split(',') if x.strip()]
   p['notes']=st.text_area('Notes',p.get('notes','')); show_img(n,100)
   with bfg_card('Character preview'):
    render_long_markdown(char_profile(n),'Profile',expanded=True)
elif page=='Picture Manager':
 render_page_shell('Picture Manager',subtitle='Upload wrestler, belt, logo, and owner images — placeholders only, no third-party logos.',show_meter=False)
 for folder in picture_folder_map().values(): Path(folder).mkdir(parents=True,exist_ok=True)
 kind=st.selectbox('Image type',['wrestler','owner','gm','commentator','podcast host','logo','banner','championship belt'],key='pic_kind')
 pic_comp=None; target=None
 if kind in ('logo','banner'):
  pic_comp=st.selectbox('Company',PLAYABLE,key='pic_co'); target=pic_comp
 elif kind=='championship belt':
  pic_comp=brand_tabs('Company',key='picbeltco'); target=st.selectbox('Championship title',COMPANIES[pic_comp]['titles'],key=f'pic_belt_title_{pic_comp}')
  st.caption(f'Saves as: assets/belts/{belt_file_slug(pic_comp,target)}.png')
 elif kind=='owner':
  pic_comp=brand_tabs('Company',key='picbrand_owner')
  choices=company_owner_photo_names(pic_comp)
  if not choices: choices=[COMPANIES[pic_comp].get('owner','Owner')]
  target=st.selectbox('Owner',choices,key=f'pic_owner_person_{pic_comp}')
  st.caption(f'Saves as: assets/owners/{slug(target)}.png')
 elif kind=='gm':
  pic_comp=brand_tabs('Company',key='picbrand_gm')
  prof=st.session_state.company_profiles.setdefault(pic_comp,dict(COMPANY_PROFILES[pic_comp]))
  target=(prof.get('gm') or COMPANIES[pic_comp]['gm'] or '').strip()
  st.text_input('GM',value=target,disabled=True,key=f'pic_gm_person_{pic_comp}')
  st.caption(f'Saves as: assets/gm/{slug(target)}.png' if target else 'Set GM name on Company Home first.')
 else:
  pic_comp=brand_tabs('Company',key='picbrand2')
  if kind=='wrestler': target=clean_name_selector('Wrestler / tag team',f'pic_wrest_{pic_comp}',company_filter=True,type_filter=True,default_company=pic_comp,default_entity='All')
  elif kind=='podcast host':
   ensure_nxt_unfiltered_hosts()
   target=st.selectbox('Podcast Host',opts_podcast_hosts('NXT'),key='pic_ph')
  else: target=clean_name_selector('Staff',f'pic_staff_{pic_comp}',company=pic_comp,entity_type='Staff',default_company=pic_comp)
 if kind=='championship belt':
  show_belt_img(pic_comp,target,150)
 elif kind in ('logo','banner'):
  show_entity_img(pic_comp,kind,140)
 else:
  img_kind='podcast_host' if kind=='podcast host' else (kind if kind!='wrestler' else 'wrestler')
  show_entity_img(target,img_kind,140)
 f=st.file_uploader('Upload image (png/jpg/jpeg/webp)',type=['png','jpg','jpeg','webp'],key=f'pic_upload_{pic_comp}_{kind}')
 url=st.text_input('Optional image URL','',key=f'pic_url_{pic_comp}_{kind}')
 if st.button('Save Picture',key=f'pic_save_{pic_comp}_{kind}'):
  if kind in ('owner','gm','wrestler','commentator','podcast host') and not (target or '').strip():
   st.error('Select a person before saving.')
  elif kind=='championship belt' and not target:
   st.error('Select a championship title before saving.')
  else:
   ok,msg=save_picture_asset(kind,pic_comp,target,f=f,url=url)
   if ok: st.success(msg); st.rerun()
   else: st.error(msg)
 with bfg_card('Belt filename reference'):
  for comp in PLAYABLE:
   st.write(f'**{comp}**')
   for t in COMPANIES[comp]['titles']: st.caption(f'{belt_file_slug(comp,t)}.png — {t}')
elif page=='Finance':
 render_page_shell('Finance',subtitle='Each brand has its own $150M starting budget, payroll, and ledger — banks never share money.',show_meter=False)
 ensure_finance_state()
 ftabs=st.tabs(['NXT','SmackDown','WCW'])
 for tab,comp in zip(ftabs,PLAYABLE):
  with tab:
   render_finance_company_panel(comp)
elif page=='Contracts':
 render_page_shell('Contracts & Negotiations',subtitle='Renewals, free agency signings, and contract warnings by brand.',show_meter=False)
 ensure_contract_fields(); ensure_finance_state()
 if calendar_year_locked(): st.info('**Year Locked — Contracts Active** — contracts count down each week. Negotiate renewals below.')
 else: st.success('**Pre-Season Contract Editing Enabled** — set length, start year, and expiration before locking the schedule.')
 cont_co=st.radio('Brand',PLAYABLE+['Free Agency'],horizontal=True,key='contract_brand_tab')
 if cont_co in PLAYABLE:
  render_money_meter(cont_co,compact=True,show_ticker=True,show_sponsor=False)
  render_financial_crisis_panel(cont_co,show_tools=True,key_prefix=f'ctr_{cont_co}')
 else:
  for bc in PLAYABLE:
   fin=st.session_state.company_finance[bc]
   st.caption(f"**{bc}** bank: {money(fin.get('current_budget',0))} — sign free agents to a brand below")
 if cont_co=='Free Agency':
  st.subheader('Free Agency Pool')
  fa=[find(x['name']) for x in st.session_state.free_agency_pool if find(x['name'])]
  fa+=[w for w in st.session_state.roster if w.get('company')=='Free Agency' and w not in fa]
  if not fa: st.info('No free agents right now. Expired or released contracts appear here.')
  for w in fa:
   sync_wrestler_from(w); recompute_contract_counters(w)
   c1,c2=st.columns([.18,.82])
   with c1: show_img(w['name'],90)
   with c2:
    st.markdown(f"**{w['name']}** · From: **{w.get('from_location','Unknown')}** · OVR {w['overall']} · Pop {w['popularity']} · Morale {w['morale']}")
    meta=next((x for x in st.session_state.free_agency_pool if x.get('name')==w['name']),{})
    st.caption(f"Previous: {meta.get('previous_company',w.get('previous_company','—'))} · Reason: {meta.get('reason',w.get('fa_reason','—'))} · Demand: {money(w.get('salary_demand',w['salary']))}")
    st.caption(f"Interested: {', '.join(meta.get('interested',PLAYABLE))} · Signing chance est. {meta.get('signing_chance',50)}%")
    sign_co=st.selectbox('Sign to',PLAYABLE,key=f'fa_co_{w["name"]}')
    yrs=st.number_input('Years',1,7,3,key=f'fa_y_{w["name"]}')
    sal=st.number_input('Salary',100000,20000000,int(w.get('salary_demand',w['salary'])),step=50000,key=f'fa_s_{w["name"]}')
    bon=st.number_input('Signing bonus',0,5000000,250000,step=50000,key=f'fa_b_{w["name"]}')
    c1b,c2b,c3b=st.columns(3)
    if c1b.button('Sign',key=f'fa_sign_{w["name"]}'):
     ok,msg=sign_free_agent_to_company(w,sign_co,int(yrs),int(sal),int(bon))
     if ok: st.success(msg); st.rerun()
     else: st.error(msg)
    if c2b.button('Make Offer',key=f'fa_offer_{w["name"]}'):
     w['renewal_status']='Offer Made'; st.toast(f'Offer sent to {w["name"]} — {sign_co}')
    if c3b.button('Pass',key=f'fa_pass_{w["name"]}'): st.toast('Passed')
 else:
  comp=cont_co
  sync_company_payroll_stats()
  fin=st.session_state.company_finance[comp]
  st.caption(f'{comp} payroll {money(fin["payroll"])} · budget {money(fin["current_budget"])}')
  warns=get_contract_warnings(comp)
  if warns:
   with bfg_card('Contract Warnings'):
    for msg in warns[:10]: st.write('• '+msg)
  pool=sorted([w for w in payroll_wrestlers(comp)],key=lambda x:(int(x.get('contract_weeks_remaining',999)),-x['popularity']))
  cfilter=st.selectbox('Filter',['All','Expiring Soon (≤8 weeks)','Negotiating','Refused / Testing FA'],key=f'ctr_f_{comp}')
  if cfilter=='Expiring Soon (≤8 weeks)': pool=[w for w in pool if int(w.get('contract_weeks_remaining',99))<=8]
  elif cfilter=='Negotiating': pool=[w for w in pool if w.get('contract_status')=='Negotiating']
  elif cfilter=='Refused / Testing FA': pool=[w for w in pool if w.get('renewal_status') in ('Rejected','Testing Free Agency','Refused Renewal','Wants More Money')]
  for w in pool:
   recompute_contract_counters(w); sync_wrestler_from(w)
   c1,c2=st.columns([.16,.84])
   with c1: show_img(w['name'],88)
   with c2:
    st.markdown(f"**{w['name']}** · From: **{w.get('from_location','Unknown')}** · OVR {w['overall']} · Pop {w['popularity']} · Morale {w['morale']}")
    st.caption(f"Salary {money(w['salary'])} · {contract_display_line(w)} · Renewal: {w.get('renewal_status')} · Chance {w.get('renewal_chance',50)}% · **Brand loyalty {w.get('brand_loyalty',50)}** ({crisis.loyalty_tier(w.get('brand_loyalty',50))})")
    if not calendar_year_locked():
     w['salary']=st.number_input('Salary',100000,20000000,int(w['salary']),step=50000,key=f'cn_sal_{comp}_{w["name"]}')
     w['contract_length_years']=st.number_input('Years given',1,10,int(w.get('contract_length_years',3)),key=f'cn_yrs_{comp}_{w["name"]}')
     w['contract_expiration_year']=st.number_input('Expiration year',2020,2055,int(w.get('contract_expiration_year',game_contract_year()+3)),key=f'cn_exp_{comp}_{w["name"]}')
     w['contract_status']=st.selectbox('Status',CONTRACT_STATUSES,index=CONTRACT_STATUSES.index(w.get('contract_status','Active')) if w.get('contract_status') in CONTRACT_STATUSES else 0,key=f'cn_cst_{comp}_{w["name"]}')
     w['renewal_status']=st.selectbox('Renewal',RENEWAL_STATUSES,index=RENEWAL_STATUSES.index(w.get('renewal_status','Not Started')) if w.get('renewal_status') in RENEWAL_STATUSES else 0,key=f'cn_rst_{comp}_{w["name"]}')
     if st.button('Save pre-season contract',key=f'cn_save_{comp}_{w["name"]}'):
      recompute_contract_counters(w); sync_company_payroll_stats(); st.rerun()
    else:
     off_sal=st.number_input('Offer salary',100000,25000000,int(w.get('negotiation_offer_salary',w.get('salary_demand',w['salary']))),step=50000,key=f'cn_off_{comp}_{w["name"]}')
     off_yrs=st.number_input('Offer years',1,7,int(w.get('negotiation_offer_years',w.get('contract_length_years',2))),key=f'cn_oy_{comp}_{w["name"]}')
     bonus=st.number_input('Signing bonus',0,5000000,0,step=50000,key=f'cn_bon_{comp}_{w["name"]}')
     creative=st.checkbox('Creative promise',key=f'cn_cr_{comp}_{w["name"]}')
     media=st.checkbox('Media opportunity',key=f'cn_med_{comp}_{w["name"]}')
     title_push=st.checkbox('Title push promise',key=f'cn_tp_{comp}_{w["name"]}')
     b1,b2,b3,b4=st.columns(4)
     if b1.button('Offer Renewal',key=f'cn_ren_{comp}_{w["name"]}'):
      if apply_contract_offer(w,comp,off_sal,off_yrs,bonus,creative,media,title_push): st.success('Accepted'); st.rerun()
      else: st.warning('Rejected or countered — adjust offer.'); st.rerun()
     if b2.button('+Salary Offer',key=f'cn_up_{comp}_{w["name"]}'):
      apply_contract_offer(w,comp,int(off_sal*1.08),off_yrs,bonus,creative,media,title_push); st.rerun()
     if b3.button('Release',key=f'cn_rel_{comp}_{w["name"]}'):
      release_wrestler_contract(w,comp); st.rerun()
     if b4.button('Let Expire',key=f'cn_expbtn_{comp}_{w["name"]}'):
      w['renewal_status']='Testing Free Agency'; w['contract_weeks_remaining']=0; recompute_contract_counters(w); st.toast('Will expire at week end if not renewed.')
    with st.expander('More negotiation actions'):
     s1,s2,s3=st.columns(3)
     if s1.button('Short-Term Deal',key=f'cn_st_{comp}_{w["name"]}'): apply_contract_offer(w,comp,off_sal,1,bonus,creative,media,title_push); st.rerun()
     if s2.button('Long-Term Deal',key=f'cn_lt_{comp}_{w["name"]}'): apply_contract_offer(w,comp,off_sal,5,bonus,creative,media,title_push); st.rerun()
     if s3.button('Offer Signing Bonus Only',key=f'cn_sb_{comp}_{w["name"]}'): apply_contract_offer(w,comp,off_sal,off_yrs,bonus+500000,creative,media,title_push); st.rerun()
  with st.expander('Negotiation history',expanded=False):
   for h in [x for x in st.session_state.negotiation_history if x.get('company')==comp][:20]:
    st.write(f"Week {h.get('week')} — **{h.get('name')}** — {h.get('action')}: {h.get('detail','')}")
elif page=='Save Center':
 render_page_shell('Save Center',subtitle='Download and load universe saves — full rosters, finances, Twitter, calendar, and GM progress.',show_meter=False)
 save_keys=_universe_save_keys()+['last_grade','last_hotel_cost','last_hotel_savings','last_transport_savings','last_profit_loss','last_money_generated','last_money_lost','nxt_uf_tts_speed','nxt_uf_tts_energy','week_progress','player_assignments']
 data={k:st.session_state[k] for k in save_keys if k in st.session_state}
 st.download_button('Download Universe Save',json.dumps(data,indent=2,default=str),'bound_for_glory_save.json','application/json')
 if is_admin() and st.button('Save universe to shared JSON (local)',key='sc_save_disk'): save_universe(); st.success('Saved to data/universe/')
 up=st.file_uploader('Load Save File',type=['json'])
 if up and st.button('Load Save',disabled=not is_admin()):
   try:
    loaded=json.loads(up.read().decode('utf-8'))
   except json.JSONDecodeError as ex:
    st.error(f'Invalid save file (not valid JSON): {ex}')
   else:
    for k,v in loaded.items(): st.session_state[k]=v
    ensure_extended_state(); ensure_week_progress_state(); storylines.ensure_storyline_state(); sponsor_obj.ensure_sponsor_objectives(COMPANIES)
    st.session_state._universe_loaded=True; save_week_state(); save_universe(); st.success('Save loaded.'); st.rerun()
 elif up and not is_admin(): st.caption('Only Admin can load a full universe save file.')
 st.info('Your full universe save file includes rosters, champions, finances, booking history, Twitter, calendar, rankings, and all GM progress.')
else:
 st.session_state.nav_page='Dashboard'
 st.rerun()

