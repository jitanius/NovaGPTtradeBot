from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from .storage import read_json, write_json, append_json_list, LOCK
STATE='data/paper_state.json'; JOURNAL='data/journal.json'
def now():return datetime.now(timezone.utc).isoformat()
def default_state():return {'wallet_balance':10000.0,'used_margin':0.0,'realized_pnl':0.0,'fees':0.0,'positions':[],'daily_pnl':0.0,'daily_key':datetime.now(timezone.utc).date().isoformat()}
class PaperEngine:
 def __init__(self,price_provider):self.price_provider=price_provider
 def state(self):
  s=read_json(STATE,default_state());d=datetime.now(timezone.utc).date().isoformat()
  if s.get('daily_key')!=d:s['daily_key']=d;s['daily_pnl']=0.0
  return s
 def status(self,refresh=True):
  with LOCK:
   s=self.state()
   if refresh:self._refresh(s)
   u=0.0
   for p in s['positions']:u+=(p.get('mark',p['entry'])-p['entry'])*p['remaining_qty']*(1 if p['direction']=='LONG' else -1)
   s['unrealized_pnl']=u;s['equity']=s['wallet_balance']+u;s['available_margin']=s['wallet_balance']-s['used_margin'];write_json(STATE,s);return s
 def open(self,symbol,interval,direction,margin,leverage,entry,sl,tp1,tp2,snapshot,auto_manage=True):
  d=direction.upper();lev=int(leverage);margin=float(margin)
  if d not in ('LONG','SHORT'):raise ValueError('direction must be LONG or SHORT')
  if lev not in (1,2,3,5,10,20):raise ValueError('leverage must be 1/2/3/5/10/20')
  with LOCK:
   s=self.state()
   if margin<=0 or margin>s['wallet_balance']-s['used_margin']:raise ValueError('insufficient paper margin')
   exp=margin*lev;qty=exp/entry;fee=exp*.0004;a=float(snapshot.get('atr14') or entry*.005)
   if sl is None:sl=entry-1.2*a if d=='LONG' else entry+1.2*a
   risk=abs(entry-sl)
   if risk<=0 or (d=='LONG' and sl>=entry) or (d=='SHORT' and sl<=entry):raise ValueError('invalid stop')
   if tp1 is None:tp1=entry+1.5*risk if d=='LONG' else entry-1.5*risk
   if tp2 is None:tp2=entry+2.5*risk if d=='LONG' else entry-2.5*risk
   liq=entry*(1-.90/lev) if d=='LONG' else entry*(1+.90/lev);pid=str(uuid4())[:10]
   p={'id':pid,'symbol':symbol,'interval':interval,'direction':d,'margin':margin,'margin_remaining':margin,'leverage':lev,'exposure':exp,'entry':entry,'mark':entry,'qty':qty,'remaining_qty':qty,'sl':sl,'tp1':tp1,'tp2':tp2,'liq':liq,'tp1_hit':False,'auto_manage':bool(auto_manage),'opened_at':now(),'setup_type':(snapshot.get('pattern') or {}).get('name') or snapshot.get('breakout',{}).get('stage') or 'MANUAL','enos_signal':snapshot.get('signal'),'enos_score':snapshot.get('score'),'enos_direction':snapshot.get('direction'),'snapshot':snapshot,'open_fee':fee,'realized_partial':0.0}
   s['wallet_balance']-=fee;s['fees']+=fee;s['used_margin']+=margin;s['positions'].append(p);write_json(STATE,s);append_json_list(JOURNAL,{'event':'OPEN','time':now(),'position':p,'aligned_with_enos':snapshot.get('gate')=='READY' and snapshot.get('direction')==d});return p
 def update_levels(self,pid,sl=None,tp1=None,tp2=None):
  with LOCK:
   s=self.state();p=next((x for x in s['positions'] if x['id']==pid),None)
   if not p:raise ValueError('position not found')
   if sl is not None:p['sl']=float(sl)
   if tp1 is not None:p['tp1']=float(tp1)
   if tp2 is not None:p['tp2']=float(tp2)
   write_json(STATE,s);append_json_list(JOURNAL,{'event':'LEVEL_UPDATE','time':now(),'position_id':pid,'sl':p['sl'],'tp1':p['tp1'],'tp2':p['tp2']});return p
 def close(self,pid,reason='MANUAL',price=None):
  with LOCK:
   s=self.state();p=next((x for x in s['positions'] if x['id']==pid),None)
   if not p:raise ValueError('position not found')
   px=float(price if price is not None else self.price_provider(p['symbol']));self._close(s,p,px,reason);write_json(STATE,s);return {'closed':pid,'price':px,'reason':reason}
 def _partial(self,s,p,px):
  q=p['remaining_qty']*.5;sign=1 if p['direction']=='LONG' else -1;gross=(px-p['entry'])*q*sign;fee=px*q*.0004;net=gross-fee;release=p['margin_remaining']*.5;p['remaining_qty']-=q;p['margin_remaining']-=release;p['realized_partial']+=net;p['tp1_hit']=True;p['sl']=p['entry'];s['used_margin']-=release;s['wallet_balance']+=net;s['realized_pnl']+=net;s['daily_pnl']+=net;s['fees']+=fee;append_json_list(JOURNAL,{'event':'PARTIAL_TP1','time':now(),'position_id':p['id'],'price':px,'net_pnl':net,'new_sl':p['sl']})
 def _close(self,s,p,px,reason):
  sign=1 if p['direction']=='LONG' else -1;gross=(px-p['entry'])*p['remaining_qty']*sign;fee=px*p['remaining_qty']*.0004;net=gross-fee;s['wallet_balance']+=net;s['realized_pnl']+=net;s['daily_pnl']+=net;s['fees']+=fee;s['used_margin']=max(0,s['used_margin']-p['margin_remaining']);s['positions']=[x for x in s['positions'] if x['id']!=p['id']];ir=abs(p['entry']-p['snapshot'].get('sl',p['sl']))*p['qty'] if p.get('sl') else 0;tot=net+p.get('realized_partial',0);append_json_list(JOURNAL,{'event':'CLOSE','time':now(),'position_id':p['id'],'symbol':p['symbol'],'interval':p['interval'],'direction':p['direction'],'entry':p['entry'],'exit':px,'margin':p['margin'],'leverage':p['leverage'],'setup_type':p.get('setup_type'),'enos_signal':p.get('enos_signal'),'enos_score':p.get('enos_score'),'net_pnl':tot,'r_multiple':tot/ir if ir else None,'reason':reason,'opened_at':p['opened_at']})
 def _refresh(self,s):
  for p in list(s['positions']):
   try:m=float(self.price_provider(p['symbol']))
   except Exception:continue
   p['mark']=m;d=p['direction'];liq=m<=p['liq'] if d=='LONG' else m>=p['liq'];st=m<=p['sl'] if d=='LONG' else m>=p['sl'];t2=m>=p['tp2'] if d=='LONG' else m<=p['tp2'];t1=m>=p['tp1'] if d=='LONG' else m<=p['tp1']
   if liq:self._close(s,p,m,'LIQUIDATION')
   elif st:self._close(s,p,m,'STOP')
   elif t2:self._close(s,p,m,'TP2')
   elif p.get('auto_manage') and not p.get('tp1_hit') and t1:self._partial(s,p,m)
 def journal(self):return read_json(JOURNAL,[])
 def performance(self):
  c=[x for x in self.journal() if x.get('event')=='CLOSE'];p=[float(x.get('net_pnl') or 0) for x in c];w=[x for x in p if x>0];l=[x for x in p if x<0];gp=sum(w);gl=abs(sum(l));rs=[x.get('r_multiple') for x in c if isinstance(x.get('r_multiple'),(int,float))];by={}
  for x in c:
   k=x.get('setup_type') or 'UNKNOWN';z=by.setdefault(k,{'trades':0,'wins':0,'pnl':0.0});z['trades']+=1;z['wins']+=1 if x.get('net_pnl',0)>0 else 0;z['pnl']+=float(x.get('net_pnl') or 0)
  for z in by.values():z['win_rate']=100*z['wins']/z['trades'] if z['trades'] else 0
  return {'trades':len(c),'wins':len(w),'losses':len(l),'win_rate':100*len(w)/len(c) if c else 0,'gross_profit':gp,'gross_loss':gl,'profit_factor':gp/gl if gl else (999 if gp else 0),'net_pnl':sum(p),'expectancy_r':sum(rs)/len(rs) if rs else 0,'by_setup':by}
