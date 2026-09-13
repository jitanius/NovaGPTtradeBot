from __future__ import annotations
from statistics import mean

def ema(v,n):
    if not v:return []
    a=2/(n+1);o=[float(v[0])]
    for x in v[1:]:o.append(a*float(x)+(1-a)*o[-1])
    return o
def sma(v,n,i=None):
    if not v:return 0.0
    i=len(v)-1 if i is None else i;w=v[max(0,i-n+1):i+1];return sum(w)/len(w) if w else 0.0
def atr(c,n=14):
    if len(c)<2:return 0.0
    t=[];p=c[0]['close']
    for x in c[1:]:t.append(max(x['high']-x['low'],abs(x['high']-p),abs(x['low']-p)));p=x['close']
    return sma(t,n)
def rsi(v,n=14):
    o=[50.0]*len(v);g=[];l=[]
    for i in range(1,len(v)):
        d=v[i]-v[i-1];g.append(max(d,0));l.append(max(-d,0))
        if i>=n:
            gg=sum(g[i-n:i])/n;ll=sum(l[i-n:i])/n;o[i]=100 if ll==0 else 100-100/(1+gg/ll)
    return o
def pivots(c,L=3,R=3):
    h=[];l=[]
    for i in range(L,len(c)-R):
        if all(c[i]['high']>c[j]['high'] for j in range(i-L,i)) and all(c[i]['high']>=c[j]['high'] for j in range(i+1,i+R+1)):h.append((i,c[i]['high']))
        if all(c[i]['low']<c[j]['low'] for j in range(i-L,i)) and all(c[i]['low']<=c[j]['low'] for j in range(i+1,i+R+1)):l.append((i,c[i]['low']))
    return h,l
def lin(p):
    if len(p)<2:return 0,0,0
    xs=[x for x,_ in p];ys=[y for _,y in p];xm=mean(xs);ym=mean(ys);d=sum((x-xm)**2 for x in xs)
    if not d:return 0,ym,0
    s=sum((x-xm)*(y-ym) for x,y in p)/d;b=ym-s*xm;ss=sum((y-ym)**2 for y in ys);er=sum((y-(s*x+b))**2 for x,y in p);return s,b,0 if not ss else max(0,1-er/ss)
def pattern(c,hs,ls,a):
    if len(hs)<2 or len(ls)<2 or a<=0:return None
    hp=hs[-5:];lp=ls[-5:];sh,bh,rh=lin(hp);sl,bl,rl=lin(lp);nh=sh/a;nl=sl/a;f=.025;pa=.05;name=None;bias='NEUTRAL'
    if abs(nh)<f and nl>f:name='ASC_TRIANGLE';bias='BULLISH'
    elif nh<-f and abs(nl)<f:name='DESC_TRIANGLE';bias='BEARISH'
    elif nh<-f and nl>f:name='SYMM_TRIANGLE'
    elif nh>f and nl>f and abs(nh-nl)<pa:name='ASC_CHANNEL';bias='BULLISH'
    elif nh<-f and nl<-f and abs(nh-nl)<pa:name='DESC_CHANNEL';bias='BEARISH'
    elif nh>f and nl>f and nh<nl:name='RISING_WEDGE';bias='BEARISH'
    elif nh<-f and nl<-f and nh<nl:name='FALLING_WEDGE';bias='BULLISH'
    elif nh>f and nl<-f:name='BROADENING'
    elif abs(nh)<f*2 and abs(nl)<f*2:name='RANGE'
    if not name:return None
    q=int(max(45,min(95,45+25*rh+25*rl)));z=len(c)-1;a0=max(0,min(hp[0][0],lp[0][0]));return {'name':name,'bias':bias,'quality':q,'upper':{'t1':c[a0]['time'],'p1':sh*a0+bh,'t2':c[z]['time'],'p2':sh*z+bh},'lower':{'t1':c[a0]['time'],'p1':sl*a0+bl,'t2':c[z]['time'],'p2':sl*z+bl}}
def fvg(c):
    last=None
    for i in range(2,len(c)):
        if c[i]['low']>c[i-2]['high']:last={'type':'BULLISH_FVG','bottom':c[i-2]['high'],'top':c[i]['low'],'index':i}
        elif c[i]['high']<c[i-2]['low']:last={'type':'BEARISH_FVG','bottom':c[i]['high'],'top':c[i-2]['low'],'index':i}
    if last:
        p=c[-1]['close'];last['open']=last['bottom']<=p<=last['top'] or (last['type']=='BULLISH_FVG' and p>last['bottom']) or (last['type']=='BEARISH_FVG' and p<last['top'])
    return last
def sweep(c):
    if len(c)<12:return None
    x=c[-1];h=max(v['high'] for v in c[-11:-1]);l=min(v['low'] for v in c[-11:-1])
    if x['high']>h and x['close']<h:return {'type':'SWEEP_HIGH','level':h,'time':x['time']}
    if x['low']<l and x['close']>l:return {'type':'SWEEP_LOW','level':l,'time':x['time']}
    return None
def breakout(c,a):
    if len(c)<35 or a<=0:return {'stage':'SEARCH','direction':None,'level':None,'reaction_zone':None,'events':[]}
    base=c[-35:-12];rec=c[-12:];levels=[('LONG',max(x['high'] for x in base)),('SHORT',min(x['low'] for x in base))];cand=[]
    for d,level in levels:
        bi=ri=ci=None;ev=[]
        for k,x in enumerate(rec):
            if (x['close']>level+.15*a if d=='LONG' else x['close']<level-.15*a):bi=k;break
        if bi is None:continue
        ev.append({'kind':'BREAKOUT','direction':d,'time':rec[bi]['time'],'price':level})
        for k in range(bi+1,len(rec)):
            x=rec[k]
            if x['low']<=level+.25*a and x['high']>=level-.25*a:ri=k;break
        if ri is not None:
            ev.append({'kind':'RETEST','direction':d,'time':rec[ri]['time'],'price':level})
            for k in range(ri+1,len(rec)):
                x=rec[k]
                if (x['close']>level+.05*a if d=='LONG' else x['close']<level-.05*a):ci=k;break
        st='CONFIRM' if ci is not None else 'RETEST' if ri is not None else 'BREAKOUT';ix=ci if ci is not None else ri if ri is not None else bi
        if ci is not None:ev.append({'kind':'CONFIRM','direction':d,'time':rec[ci]['time'],'price':rec[ci]['close']})
        cand.append((ix,st,d,level,ev))
    if not cand:return {'stage':'SEARCH','direction':None,'level':None,'reaction_zone':None,'events':[]}
    _,st,d,level,ev=max(cand,key=lambda x:x[0]);return {'stage':st,'direction':d,'level':level,'reaction_zone':{'bottom':level-.25*a,'top':level+.25*a},'events':ev}
def analyze(candles,symbol='BTCUSDT',interval='15m'):
    if len(candles)<40:return {'symbol':symbol,'interval':interval,'signal':'WAIT','score':0,'error':'NOT_ENOUGH_DATA'}
    c=candles[:-1];live=candles[-1];cl=[x['close'] for x in c];vol=[x.get('volume',0) or 0 for x in c];e13=ema(cl,13);e26=ema(cl,26);a=atr(c);rs=rsi(cl);px=c[-1]['close'];rv=vol[-1]/sma(vol,20) if sma(vol,20)>0 else 0;tb=c[-1].get('taker_buy_volume');tbs=100*tb/c[-1]['volume'] if tb is not None and c[-1].get('volume',0)>0 else None
    hs,ls=pivots(c);hl='HH' if len(hs)>=2 and hs[-1][1]>hs[-2][1] else 'LH' if len(hs)>=2 else None;ll='HL' if len(ls)>=2 and ls[-1][1]>ls[-2][1] else 'LL' if len(ls)>=2 else None;st='BULLISH' if hl=='HH' and ll=='HL' else 'BEARISH' if hl=='LH' and ll=='LL' else 'MIXED';sup=max([p for _,p in ls if p<=px],default=min(x['low'] for x in c[-30:]));res=min([p for _,p in hs if p>=px],default=max(x['high'] for x in c[-30:]));sw=sweep(c);fg=fvg(c[-100:]);pat=pattern(c,hs,ls,a);br=breakout(c,a)
    x=c[-1];body=max(abs(x['close']-x['open']),1e-12);lower=min(x['open'],x['close'])-x['low'];upper=x['high']-max(x['open'],x['close']);be=(e26[-1]-px)>=1.8*a if a else False;se=(px-e26[-1])>=1.8*a if a else False;bd=sd=False
    if len(ls)>=2:aa,bb=ls[-2][0],ls[-1][0];bd=ls[-1][1]<ls[-2][1] and rs[bb]>rs[aa]
    if len(hs)>=2:aa,bb=hs[-2][0],hs[-1][0];sd=hs[-1][1]>hs[-2][1] and rs[bb]<rs[aa]
    bctx=(abs(px-sup)<=.35*a if a else False) or bool(sw and sw['type']=='SWEEP_LOW');sctx=(abs(px-res)<=.35*a if a else False) or bool(sw and sw['type']=='SWEEP_HIGH');bes=(2 if be else 0)+(1 if rs[-1]<=32 else 0)+(1 if bd else 0)+(1 if lower>1.2*body else 0)+(1 if bctx else 0);ses=(2 if se else 0)+(1 if rs[-1]>=68 else 0)+(1 if sd else 0)+(1 if upper>1.2*body else 0)+(1 if sctx else 0);pe={'direction':'UP','score':bes,'time':x['time'],'price':x['low']} if be and bes>=4 else {'direction':'DOWN','score':ses,'time':x['time'],'price':x['high']} if se and ses>=4 else None
    bull=bear=0;comp=[]
    if px>e13[-1]>e26[-1]:bull+=20;comp.append({'name':'EMA alignment','bull':20,'bear':0})
    elif px<e13[-1]<e26[-1]:bear+=20;comp.append({'name':'EMA alignment','bull':0,'bear':20})
    if st=='BULLISH':bull+=20
    elif st=='BEARISH':bear+=20
    else:bull+=5;bear+=5
    if sw:bull+=15 if sw['type']=='SWEEP_LOW' else 0;bear+=15 if sw['type']=='SWEEP_HIGH' else 0
    if rv>=1:bull+=5;bear+=5
    if tbs is not None:bull+=10 if tbs>=56 else 0;bear+=10 if tbs<=44 else 0
    if fg and fg.get('open'):bull+=5 if fg['type']=='BULLISH_FVG' else 0;bear+=5 if fg['type']=='BEARISH_FVG' else 0
    if pat:bull+=10 if pat['bias']=='BULLISH' else 3 if pat['bias']=='NEUTRAL' else 0;bear+=10 if pat['bias']=='BEARISH' else 3 if pat['bias']=='NEUTRAL' else 0
    pts={'SEARCH':0,'BREAKOUT':5,'RETEST':10,'CONFIRM':20}.get(br['stage'],0);bull+=pts if br['direction']=='LONG' else 0;bear+=pts if br['direction']=='SHORT' else 0
    if pe:bull+=5 if pe['direction']=='UP' else 0;bear+=5 if pe['direction']=='DOWN' else 0
    bull=min(100,bull);bear=min(100,bear);score=max(bull,bear);gap=abs(bull-bear);d='LONG' if bull>bear else 'SHORT' if bear>bull else None;ready=br['stage']=='CONFIRM' and br['direction']==d and score>=75 and gap>=20;sig=d+'_READY' if ready else 'WAIT' if score>=45 else 'DO_NOT_ENTER';reasons=[f'Structure: {st} ({hl or "-"}/{ll or "-"})',f'EMA13 {e13[-1]:.8g} / EMA26 {e26[-1]:.8g}',f'Breakout state: {br["stage"]} {br["direction"] or ""}'.strip()];missing=[]
    if sw:reasons.append('Liquidity: '+sw['type'])
    if pat:reasons.append(f'Pattern: {pat["name"]} quality {pat["quality"]}/100 ({pat["bias"]})')
    if pe:reasons.append(f'Point E warning: {pe["direction"]} {pe["score"]}/6')
    if br['stage']!='CONFIRM':missing.append('Need breakout → retest → closed-candle confirmation')
    if score<75:missing.append('Evidence score below 75/100 readiness threshold')
    if gap<20:missing.append('Directional evidence is not sufficiently separated')
    en=slv=tp1=tp2=None
    if ready:
        en=px
        if d=='LONG':slv=min(sup,br['level'] or sup)-.15*a;r=max(en-slv,.25*a);tp1=en+1.5*r;tp2=en+2.5*r
        else:slv=max(res,br['level'] or res)+.15*a;r=max(slv-en,.25*a);tp1=en-1.5*r;tp2=en-2.5*r
        br['events'].append({'kind':'ENTRY','direction':d,'time':x['time'],'price':en})
    marks=[]
    for i,p in hs[-8:]:marks.append({'kind':'STRUCTURE','label':'H','time':c[i]['time'],'price':p,'side':'above'})
    for i,p in ls[-8:]:marks.append({'kind':'STRUCTURE','label':'L','time':c[i]['time'],'price':p,'side':'below'})
    if pe:marks.append({'kind':'POINT_E','label':'E?','time':pe['time'],'price':pe['price'],'side':'below' if pe['direction']=='UP' else 'above'})
    for ev in br['events']:marks.append({'kind':ev['kind'],'label':ev['kind'],'time':ev['time'],'price':ev['price'],'side':'below' if ev['direction']=='LONG' else 'above'})
    return {'symbol':symbol,'interval':interval,'signal':sig,'direction':d,'score':score,'bull_score':bull,'bear_score':bear,'gate':'READY' if ready else 'BLOCKED','last':live['close'],'closed_price':px,'ema13':e13[-1],'ema26':e26[-1],'atr14':a,'rsi14':rs[-1],'rvol20':rv,'taker_buy_share':tbs,'structure':st,'high_label':hl,'low_label':ll,'support':sup,'resistance':res,'sweep':sw,'fvg':fg,'pattern':pat,'point_e':pe,'breakout':br,'entry':en,'sl':slv,'tp1':tp1,'tp2':tp2,'reasons':reasons,'missing':missing,'components':comp,'markers':marks,'data_quality':{'closed_candles':len(c),'live_candle_provisional':True}}
