"""Financial crisis, brand loyalty, and AI bidding war system for Bound For Glory."""
import random
import streamlit as st

PLAYABLE=['NXT','SmackDown','WCW']

BRAND_FIT_TAGS={
 'NXT':['cinematic','hollywood','netflix','marvel','dc','oscars','snl','gma','olympic','comic','story','spotlight','unfiltered','drama','press'],
 'SmackDown':['music','celebrity','grammy','paramount','prime','sony','culture','viral','mainstream','concert','red carpet','hasbro'],
 'WCW':['sports','nba','nfl','espn','cbs','legitimacy','stadium','championship','desk','draft','halftime','funko','topps'],
}

BID_WEIGHTS={'money':0.25,'creative':0.25,'brand_fit':0.20,'morale_loyalty':0.15,'title':0.10,'sponsor':0.05}

def _money(x):
 try:
  return '${:,.0f}'.format(float(0 if x is None else x))
 except (TypeError, ValueError):
  return '—'

def loyalty_tier(score):
 s=int(score or 0)
 if s>=70: return 'High'
 if s>=40: return 'Medium'
 return 'Low'

def default_crisis_rec():
 return {'weeks_below_zero':0,'status':'Healthy','bank_at_last_check':0,'crisis_since_week':None}

def ensure_crisis_state():
 if 'company_crisis' not in st.session_state:
  st.session_state.company_crisis={c:default_crisis_rec() for c in PLAYABLE}
 if 'bidding_wars' not in st.session_state:
  st.session_state.bidding_wars=[]
 if 'brand_loyalty_history' not in st.session_state:
  st.session_state.brand_loyalty_history=[]
 for c in PLAYABLE:
  st.session_state.company_crisis.setdefault(c,default_crisis_rec())

def seed_wrestler_loyalty(w):
 base=50
 if w.get('popularity',0)>=88: base+=8
 if w.get('morale',0)>=75: base+=6
 w.setdefault('brand_loyalty',clamp_loyalty(base+random.randint(-5,8)))
 w.setdefault('booking_satisfaction',60)
 w.setdefault('rejected_pay_cut',False)
 w.setdefault('requested_release',False)
 w.setdefault('pay_cut_week',None)
 w.setdefault('deferred_bidding',False)

def clamp_loyalty(v):
 return max(0,min(100,int(v)))

def adjust_brand_loyalty(w,delta,reason=''):
 if not w or w.get('company') not in PLAYABLE: return
 old=int(w.get('brand_loyalty',50))
 w['brand_loyalty']=clamp_loyalty(old+delta)
 if reason:
  st.session_state.brand_loyalty_history.insert(0,{'week':st.session_state.get('week',0),'name':w['name'],'company':w.get('company'),'delta':delta,'loyalty':w['brand_loyalty'],'reason':reason})

def get_financial_status(comp):
 ensure_crisis_state()
 return st.session_state.company_crisis.get(comp,default_crisis_rec()).get('status','Healthy')

def is_financial_crisis(comp):
 return get_financial_status(comp)=='Financial Crisis'

def refresh_crisis_status_from_budget(comp,budget=None):
 ensure_crisis_state()
 if budget is None:
  fin=st.session_state.get('company_finance',{}).get(comp,{})
  budget=int(fin.get('current_budget',0))
 cr=st.session_state.company_crisis[comp]
 cr['bank_at_last_check']=budget
 wkz=int(cr.get('weeks_below_zero',0))
 if budget<0:
  if wkz==0: cr['crisis_since_week']=st.session_state.get('week',0)
  cr['weeks_below_zero']=wkz
 else:
  cr['weeks_below_zero']=0
  cr['crisis_since_week']=None
 if cr['weeks_below_zero']>=3:
  cr['status']='Financial Crisis'
 elif cr['weeks_below_zero']==2:
  cr['status']='Serious Financial Warning'
 elif cr['weeks_below_zero']==1:
  cr['status']='Financial Warning'
 else:
  cr['status']='Healthy'

def advance_financial_crisis_week(roster_fn,payroll_fn):
 """Call once per universe week advance — uses end-of-week bank balance."""
 ensure_crisis_state()
 for c in PLAYABLE:
  fin=st.session_state.get('company_finance',{}).get(c,{})
  budget=int(fin.get('current_budget',0))
  cr=st.session_state.company_crisis[c]
  if budget<0:
   cr['weeks_below_zero']=int(cr.get('weeks_below_zero',0))+1
   if cr['weeks_below_zero']==1:
    cr['crisis_since_week']=st.session_state.get('week',0)
   for w in payroll_fn(c):
    adjust_brand_loyalty(w,-random.randint(1,4),f'{c} bank below $0 (week {cr["weeks_below_zero"]})')
    if cr['weeks_below_zero']>=2:
     w['morale']=max(0,int(w.get('morale',50))-random.randint(0,2))
  else:
   cr['weeks_below_zero']=0
   cr['crisis_since_week']=None
  refresh_crisis_status_from_budget(c,budget)
  if cr['status']=='Financial Crisis':
   st.session_state.news_feed.insert(0,f"**{c} FINANCIAL CRISIS** — bank { _money(budget) }. Bidding wars may begin for vulnerable talent.")

def wrestler_storyline_importance(w,company,rivalries_fn,is_champ_fn,weekly_hist):
 score=0; notes=[]
 if is_champ_fn(w['name']):
  score+=45; notes.append('Current champion')
 for r in rivalries_fn():
  if r.get('company')!=company: continue
  if w['name'] in (r.get('wrestlers') or []):
   heat=int(r.get('heat',0))
   if heat>=55:
    score+=min(35,heat//2); notes.append(f"Active rivalry ({r.get('name')}) heat {heat}")
 lh=next((h for h in reversed(weekly_hist) if h.get('company')==company),None)
 if lh:
  feat=(lh.get('featured_star') or '').lower()
  if w['name'].lower() in feat or any(p in feat for p in w['name'].lower().split()):
   score+=25; notes.append('Featured on last show')
  if 'ple' in (lh.get('show_type') or '').lower() or 'ple' in (lh.get('show_name') or '').lower():
   score+=15; notes.append('PLE cycle active')
 return min(100,score),notes

def brand_fit_score(w,target_comp):
 w=w or {}
 pop=w.get('popularity',75); mom=w.get('momentum',55)
 score=42+pop*.2+mom*.15
 name_l=(w.get('name') or '').lower()
 if target_comp=='NXT' and any(x in name_l for x in ('rose','punk','raven','cena','rollins')): score+=12
 if target_comp=='SmackDown' and any(x in name_l for x in ('logan','paul','bunny','liv','becky')): score+=12
 if target_comp=='WCW' and any(x in name_l for x in ('rock','rhodes','mysterio','goldberg')): score+=10
 if w.get('company')==target_comp: score+=8
 return min(100,int(score))

def score_offer_component(w,offer,from_comp,find_fn,is_champ_fn,story_fn):
 sal=int(offer.get('salary',0) or w.get('salary',0))
 cur=int(w.get('salary',1))
 money_s=min(100,int(50*sal/max(1,cur)))
 if sal<cur*0.95: money_s*=0.85
 creative_s=88 if offer.get('creative_promise') else 42
 if offer.get('creative_promise') and not offer.get('title_opportunity'): creative_s+=4
 fit_s=brand_fit_score(w,offer.get('company'))
 loyalty=int(w.get('brand_loyalty',50))
 morale=int(w.get('morale',50))
 ml=loyalty*.55+morale*.45
 if loyalty>=70: ml=loyalty*.7+morale*.3
 elif morale<40: ml=morale*.65+loyalty*.35
 title_s=82 if offer.get('title_opportunity') else 38
 if is_champ_fn(w['name']) and offer.get('company')!=from_comp: title_s-=25
 sponsor_s=78 if offer.get('sponsor_media') else 40
 debt_pen=0
 cr=st.session_state.company_crisis.get(from_comp,{})
 if int(cr.get('weeks_below_zero',0))>=3: debt_pen=8
 total=(
  money_s*BID_WEIGHTS['money']+creative_s*BID_WEIGHTS['creative']+fit_s*BID_WEIGHTS['brand_fit']+
  ml*BID_WEIGHTS['morale_loyalty']+title_s*BID_WEIGHTS['title']+sponsor_s*BID_WEIGHTS['sponsor']-debt_pen
 )
 return {'total':total,'money':money_s,'creative':creative_s,'brand_fit':fit_s,'morale_loyalty':ml,'title':title_s,'sponsor':sponsor_s}

def identify_vulnerable_wrestlers(comp,payroll_fn,is_champ_fn,story_fn):
 out=[]
 wk=st.session_state.get('week',0)
 for w in payroll_fn(comp):
  reasons=[]; vuln=0
  if int(w.get('salary',0))>=1500000: vuln+=2; reasons.append('High salary')
  if w.get('morale',50)<45: vuln+=2; reasons.append('Low morale')
  if int(w.get('brand_loyalty',50))<40: vuln+=3; reasons.append('Low brand loyalty')
  if int(w.get('contract_weeks_remaining',99))<=12: vuln+=2; reasons.append('Expiring contract')
  if w.get('rejected_pay_cut'): vuln+=3; reasons.append('Rejected pay cut')
  if w.get('requested_release'): vuln+=3; reasons.append('Requested release')
  if w.get('renewal_status') in ('Rejected','Testing Free Agency','Wants More Money','Refused Renewal'): vuln+=2; reasons.append(w.get('renewal_status'))
  lb=w.get('last_booked_week')
  if lb is not None and wk-int(lb)>=4: vuln+=2; reasons.append('Not booked recently')
  if int(w.get('booking_satisfaction',60))<45: vuln+=1; reasons.append('Poor booking satisfaction')
  st_score,st_notes=story_fn(w,comp)
  if vuln>=3 or (vuln>=2 and int(w.get('brand_loyalty',50))<55):
   out.append({'wrestler':w,'reasons':reasons,'story_score':st_score,'story_notes':st_notes,'vuln_score':vuln})
 out.sort(key=lambda x:(-x['vuln_score'],-x['wrestler']['salary']))
 return out[:12]

def ai_bidding_decision(w,offers,from_comp,find_fn,is_champ_fn,story_fn):
 w=w or {}
 loyalty=int(w.get('brand_loyalty',50))
 morale=int(w.get('morale',50))
 st_score,st_notes=story_fn(w,from_comp)
 champion=is_champ_fn(w['name'])
 scored=[]
 for o in offers:
  sc=score_offer_component(w,o,from_comp,find_fn,is_champ_fn,story_fn)
  scored.append({**o,'score':sc['total'],'breakdown':sc})
 scored.sort(key=lambda x:-x['score'])
 best=scored[0] if scored else None
 outcome='stay_loyal'; target=None; delay=False
 reasons=[]
 if champion and morale>=42 and st_score>=40:
  outcome='delay'; delay=True
  reasons.append(f"{w['name']} is champion with storyline heat ({st_score}/100) — decision delayed until after PLE payoff.")
 elif st_score>=55 and loyalty>=62 and morale>=48:
  outcome='stay_loyal'
  reasons.append(f"High brand loyalty ({loyalty}) and central storyline ({st_score}/100) outweigh outside money for now.")
 elif w.get('requested_release') and morale<35:
  outcome='request_release'
  reasons.append(f"{w['name']} already requested release — morale is too low to stay.")
 elif not scored:
  outcome='reject_all'
  reasons.append('No rival offers on the table.')
 elif best and loyalty>=72 and best['company']!=from_comp and best['score']<loyalty*0.95:
  outcome='stay_loyal'
  reasons.append(f"Loyalty ({loyalty}) beats best offer score ({best['score']:.0f}) — staying with {from_comp}.")
 elif best and best['company']==from_comp:
  outcome='renegotiate'
  target=from_comp
  reasons.append(f"Best fit is staying, but wants renegotiation — creative/money still short vs morale ({morale}).")
 elif best:
  outcome='accept'
  target=best['company']
  parts=[f"{target} wins on brand fit ({best['breakdown']['brand_fit']:.0f})"]
  if best['breakdown']['creative']>=75: parts.append('strong creative promise')
  if best['breakdown']['money']>=60: parts.append('solid money')
  else: parts.append('money was not the top factor')
  reasons.append(f"{w['name']} accepts {target}. "+'; '.join(parts)+f". Loyalty {loyalty}, morale {morale}.")
 elif morale<38 and loyalty<45:
  outcome='reject_all'
  reasons.append('Morale and loyalty collapsed — wrestler rejects all offers and wants clarity.')
 else:
  outcome='stay_loyal'
  reasons.append(f"Stays with {from_comp} after weighing offers — continuity and loyalty held.")
 if w.get('rejected_pay_cut') and outcome=='stay_loyal':
  reasons.append('Previously rejected a pay cut — trust is damaged but storyline keeps them for now.')
 return {
  'outcome':outcome,'target_company':target,'delay':delay,'best_offer':best,'all_offers':scored,
  'reason':' '.join(reasons),'loyalty':loyalty,'morale':morale,'story_score':st_score,'story_notes':st_notes,
  'champion':champion,'breakdown':best['breakdown'] if best else {},
 }

def next_bidding_id():
 return len(st.session_state.get('bidding_wars',[]))+1

def get_open_bidding_for_wrestler(name,from_comp):
 for bw in st.session_state.get('bidding_wars',[]):
  if bw.get('wrestler')==name and bw.get('from_company')==from_comp and bw.get('status') in ('open','ai_decided','delayed'):
   return bw
 return None

def create_bidding_war(w,from_comp):
 bw={'id':next_bidding_id(),'week':st.session_state.get('week',0),'wrestler':w['name'],'from_company':from_comp,
     'status':'open','offers':[],'ai_decision':None,'admin_override':None,'history':[]}
 st.session_state.bidding_wars.insert(0,bw)
 return bw

def render_ai_decision_card(dec,w,from_comp):
 st.markdown(f"**Wrestler:** {w['name']}")
 st.markdown(f"**Current Brand:** {from_comp}")
 st.markdown(f"**Current Morale:** {w.get('morale')} · **Brand Loyalty:** {dec.get('loyalty')} ({loyalty_tier(dec.get('loyalty'))})")
 st.markdown(f"**Current Salary:** {_money(w.get('salary',0))} · **Contract Remaining:** {w.get('contract_weeks_remaining',0)} weeks")
 st.markdown(f"**Champion Status:** {'Yes' if dec.get('champion') else 'No'} · **Storyline Importance:** {dec.get('story_score')}/100")
 if dec.get('story_notes'):
  st.caption(' · '.join(dec['story_notes']))
 if dec.get('all_offers'):
  st.markdown('**Offers Received:**')
  for o in dec['all_offers']:
   st.write(f"- **{o.get('company')}** — {_money(o.get('salary'))} / {o.get('years',2)}yr · bonus {_money(o.get('bonus',0))} · score **{o.get('score',0):.1f}**")
 bo=dec.get('best_offer')
 if bo:
  st.markdown(f"**Best Offer:** {bo.get('company')} ({bo.get('score',0):.1f} weighted score)")
 labels={'stay_loyal':f"Stay loyal to {from_comp}",'accept':f"Accept {dec.get('target_company')}",'reject_all':'Reject all offers',
         'renegotiate':'Ask for contract renegotiation','request_release':'Request release','delay':'Delay until after PLE'}
 st.markdown(f"**AI Decision:** {labels.get(dec.get('outcome'),dec.get('outcome'))}")
 st.markdown(f"**Reason:** {dec.get('reason','')}")
 if dec.get('delay'):
  st.warning('Decision delayed — champion/major storyline protection.')
 eff=dec.get('outcome')
 if eff=='accept' and dec.get('target_company'):
  st.markdown(f"**Effect on Current Brand:** {from_comp} loses {w['name']} — payroll drops, morale shock in locker room.")
  st.markdown(f"**Effect on New Brand:** {dec['target_company']} gains star power and buzz.")
 elif eff=='stay_loyal':
  st.markdown(f"**Effect on Current Brand:** {w['name']} stays — loyalty reinforced, crisis continues.")
 elif eff=='renegotiate':
  st.markdown('**Effect:** Negotiation required — use Contracts crisis tools.')
 elif eff=='request_release':
  st.markdown(f'**Effect:** {w["name"]} pushes toward exit / free agency.')

def financial_status_color(status):
 return {'Healthy':'#2ecc71','Financial Warning':'#f1c40f','Serious Financial Warning':'#e67e22','Financial Crisis':'#e74c3c'}.get(status,'#aaa')

def render_financial_crisis_banner(comp,budget_fn):
 ensure_crisis_state()
 refresh_crisis_status_from_budget(comp,budget_fn())
 cr=st.session_state.company_crisis[comp]
 status=cr.get('status','Healthy')
 col=financial_status_color(status)
 bud=budget_fn()
 st.markdown(
  f"<div class='money-meter-flash {'loss' if bud<0 else 'gain'}' style='border-color:{col}'>"
  f"<b>{comp} — {status}</b> · Bank {_money(bud)} · Weeks below $0: <b>{cr.get('weeks_below_zero',0)}</b>"
  f"{' · Bidding wars active' if status=='Financial Crisis' else ''}</div>",
  unsafe_allow_html=True,
 )
 if status=='Financial Warning':
  st.warning('Week 1 below $0 — Financial Warning. The game continues.')
 elif status=='Serious Financial Warning':
  st.warning('Week 2 below $0 — Serious Financial Warning.')
 elif status=='Financial Crisis':
  st.error('Week 3+ below $0 — Financial Crisis. Rival GMs may bid on vulnerable talent; AI decides where wrestlers want to go.')
