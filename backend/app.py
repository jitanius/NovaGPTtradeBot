from __future__ import annotations
import time,threading
import httpx
from fastapi import FastAPI,HTTPException,Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .engine import analyze
from .paper import PaperEngine
from .knowledge import search as ksearch,ask as kask,add_note,sources as ksources
from .storage import read_json
app=FastAPI(title='ENOS NOVA API',version='0.16.0');app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_credentials=False,allow_methods=['*'],allow_headers=['*']);CLIENT=httpx.Client(timeout=12,headers={'User-Agent':'Mozilla/5.0 ENOS-NOVA/0.16'});CACHE={};LOCK=threading.RLock();INT={'1m':'1m','5m':'5m','15m':'15m','1h':'1h','4h':'4h','1d':'1d'};YINT={'1m':'1m','5m':'5m','15m':'15m','1h':'60m','4h':'60m','1d':'1d'};IDX={'NASDAQ':'^IXIC','NDX':'^NDX','NASDAQ100':'^NDX','SPX':'^GSPC','S&P500':'^GSPC'}
FALLBACK=['BTCUSDT','ETHUSDT','BNBUSDT','XRPUSDT','SOLUSDT','DOGEUSDT','ADAUSDT','TRXUSDT','AVAXUSDT','LINKUSDT','DOTUSDT','LTCUSDT','BCHUSDT','ATOMUSDT','UNIUSDT','ETCUSDT','XLMUSDT','FILUSDT','APTUSDT','ARBUSDT','OPUSDT','NEARUSDT','ICPUSDT','INJUSDT','AAVEUSDT','SUIUSDT','SEIUSDT','TIAUSDT','RUNEUSDT','FETUSDT','RENDERUSDT','GRTUSDT','ALGOUSDT','VETUSDT','HBARUSDT','EGLDUSDT','THETAUSDT','SANDUSDT','MANAUSDT','AXSUSDT','GALAUSDT','FLOWUSDT','KAVAUSDT','KSMUSDT','SNXUSDT','CRVUSDT','MKRUSDT','COMPUSDT','LDOUSDT','STXUSDT','IMXUSDT','QNTUSDT','WLDUSDT','PEPEUSDT','SHIBUSDT','BONKUSDT','FLOKIUSDT','WIFUSDT','JUPUSDT','ENAUSDT','ONDOUSDT','PYTHUSDT','ORDIUSDT','DYDXUSDT','GMXUSDT','MINAUSDT','ZECUSDT','DASHUSDT','IOTAUSDT','NEOUSDT','XTZUSDT','EOSUSDT','CHZUSDT','ENJUSDT','1INCHUSDT','ZILUSDT','CELOUSDT','ANKRUSDT','BATUSDT','QTUMUSDT','ICXUSDT','RVNUSDT','KNCUSDT','LRCUSDT','MASKUSDT','ENSUSDT','BLURUSDT','CFXUSDT','ROSEUSDT','SKLUSDT','BANDUSDT','API3USDT','SSVUSDT','YFIUSDT','ZRXUSDT','KASUSDT','JASMYUSDT','NOTUSDT','TONUSDT']
def cached(k,ttl,fn):
 with LOCK:
  v=CACHE.get(k)
  if v and time.time()-v[0]<ttl:return v[1]
 x=fn()
 with LOCK:CACHE[k]=(time.time(),x)
 return x
def crypto():
 def f():
  try:
   rows=CLIENT.get('https://api.binance.com/api/v3/ticker/24hr').json();x=[]
   for r in rows:
    s=r.get('symbol','');q=float(r.get('quoteVolume') or 0)
    if s.endswith('USDT') and not any(k in s for k in ('UPUSDT','DOWNUSDT','BULLUSDT','BEARUSDT')) and q>0:x.append((q,s))
   x.sort(reverse=True);return [s for _,s in x[:100]] or FALLBACK[:100]
  except Exception:return FALLBACK[:100]
 return cached('c100',300,f)
def snap(n):return read_json(f'data/universe/{n}.json',[])
def universe(g='all'):
 if g=='crypto':return [{'symbol':x,'name':x.replace('USDT',' / USDT'),'group':'CRYPTO'} for x in crypto()]
 if g=='nasdaq100':return snap('nasdaq100')
 if g=='sp500':return snap('sp500')
 if g=='indices':return [{'symbol':'NASDAQ','name':'NASDAQ Composite','group':'INDEX'},{'symbol':'NDX','name':'NASDAQ-100 Index','group':'INDEX'},{'symbol':'SPX','name':'S&P 500 Index','group':'INDEX'}]
 return universe('indices')+universe('crypto')+universe('nasdaq100')+universe('sp500')
def binance(symbol,interval,limit):
 r=CLIENT.get('https://api.binance.com/api/v3/klines',params={'symbol':symbol,'interval':INT[interval],'limit':limit});r.raise_for_status();return [{'time':int(x[0]/1000),'open':float(x[1]),'high':float(x[2]),'low':float(x[3]),'close':float(x[4]),'volume':float(x[5]),'close_time':int(x[6]/1000),'taker_buy_volume':float(x[9])} for x in r.json()]
def yahoo(symbol,interval,limit):
 y=IDX.get(symbol.upper(),symbol.upper().replace('.','-'));rng='5d' if interval in ('1m','5m','15m') else '1mo' if interval in ('1h','4h') else '1y';r=CLIENT.get(f'https://query1.finance.yahoo.com/v8/finance/chart/{y}',params={'interval':YINT[interval],'range':rng,'includePrePost':'false'});r.raise_for_status();z=r.json()['chart']['result'][0];ts=z['timestamp'];q=z['indicators']['quote'][0];out=[];sec={'1m':60,'5m':300,'15m':900,'1h':3600,'4h':14400,'1d':86400}[interval]
 for i,t in enumerate(ts):
  v=[q[k][i] for k in ('open','high','low','close','volume')]
  if any(x is None for x in v):continue
  out.append({'time':int(t),'open':float(v[0]),'high':float(v[1]),'low':float(v[2]),'close':float(v[3]),'volume':float(v[4] or 0),'close_time':int(t)+sec,'taker_buy_volume':None})
 return out[-limit:]
def candles(symbol,interval='15m',limit=320):
 symbol=symbol.upper();interval=interval if interval in INT else '15m';return cached(('k',symbol,interval,limit),3,lambda:binance(symbol,interval,limit) if symbol.endswith('USDT') else yahoo(symbol,interval,limit))
def price(symbol):
 if symbol.upper().endswith('USDT'):
  r=CLIENT.get('https://api.binance.com/api/v3/ticker/price',params={'symbol':symbol.upper()});r.raise_for_status();return float(r.json()['price'])
 return yahoo(symbol,'5m',3)[-1]['close']
paper=PaperEngine(price)
class Ticket(BaseModel):symbol:str;interval:str='15m';direction:str;margin:float=10;leverage:int=10;sl:float|None=None;tp1:float|None=None;tp2:float|None=None;auto_manage:bool=True
class Levels(BaseModel):sl:float|None=None;tp1:float|None=None;tp2:float|None=None
class Note(BaseModel):title:str;body:str;source:str='USER_NOTE';tags:list[str]=[]
@app.get('/health')
def health():return {'ok':True,'version':'0.16.0','paper_only':True,'live_execution_enabled':False}
@app.get('/api/universe')
def au(group:str='all'):return {'items':universe(group),'group':group}
@app.get('/api/candles')
def ac(symbol:str='BTCUSDT',interval:str='15m',limit:int=320):
 try:return {'symbol':symbol.upper(),'interval':interval,'candles':candles(symbol,interval,max(80,min(limit,1000)))}
 except Exception as e:raise HTTPException(502,f'market data unavailable: {e}')
@app.get('/api/analysis')
def aa(symbol:str='BTCUSDT',interval:str='15m'):
 try:return analyze(candles(symbol,interval,420),symbol.upper(),interval)
 except Exception as e:raise HTTPException(502,f'analysis unavailable: {e}')
@app.get('/api/ticker')
def at(symbol:str='BTCUSDT'):
 try:return {'symbol':symbol.upper(),'price':price(symbol)}
 except Exception as e:raise HTTPException(502,str(e))
@app.get('/api/paper/status')
def ps():return paper.status(True)
@app.post('/api/paper/open')
def po(t:Ticket):
 try:
  cs=candles(t.symbol,t.interval,420);s=analyze(cs,t.symbol.upper(),t.interval);return paper.open(t.symbol.upper(),t.interval,t.direction,t.margin,t.leverage,float(cs[-1]['close']),t.sl,t.tp1,t.tp2,s,t.auto_manage)
 except ValueError as e:raise HTTPException(400,str(e))
 except Exception as e:raise HTTPException(502,str(e))
@app.post('/api/paper/{pid}/levels')
def pl(pid:str,x:Levels):
 try:return paper.update_levels(pid,x.sl,x.tp1,x.tp2)
 except ValueError as e:raise HTTPException(404,str(e))
@app.post('/api/paper/{pid}/close')
def pc(pid:str):
 try:return paper.close(pid)
 except ValueError as e:raise HTTPException(404,str(e))
@app.get('/api/journal')
def j():return {'items':paper.journal()[-1000:]}
@app.get('/api/performance')
def pf():return paper.performance()
@app.get('/api/knowledge/search')
def ks(q:str=Query(...,min_length=2),limit:int=8):return {'items':ksearch(q,max(1,min(limit,20)))}
@app.get('/api/knowledge/ask')
def ka(q:str=Query(...,min_length=2),lang:str='ru'):return kask(q,lang)
@app.post('/api/knowledge/note')
def kn(n:Note):return add_note(n.title,n.body,n.source,n.tags)
@app.get('/api/knowledge/sources')
def kso():return {'items':ksources()}
@app.get('/api/system')
def sy():return {'version':'0.16.0','paper_only':True,'live_execution_enabled':False,'market_providers':['Binance Public','Yahoo Public Chart'],'knowledge_entries':len(read_json('data/knowledge/encyclopedia.json',[])),'sources':len(ksources()),'crypto_universe':len(crypto()),'nasdaq100':len(snap('nasdaq100')),'sp500':len(snap('sp500'))}
