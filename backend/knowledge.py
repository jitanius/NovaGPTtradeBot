from __future__ import annotations
import re
from datetime import datetime, timezone
from .storage import read_json,append_json_list
ENC='data/knowledge/encyclopedia.json';SOURCES='data/knowledge/sources.json';NOTES='data/knowledge/notes.json'
def tok(s):return set(re.findall(r'[a-zA-Zа-яА-ЯёЁא-ת0-9_+-]{2,}',(s or '').lower()))
def entries():
 r=read_json(ENC,[]);r.extend(read_json(NOTES,[]));return r
def search(q,limit=8):
 qt=tok(q);rank=[]
 for r in entries():
  text=' '.join(str(r.get(k,'')) for k in ('title','title_en','keywords','body','body_en','tags'));tt=tok(text);sc=len(qt&tt)*2+(3 if q.lower() in text.lower() else 0)
  if sc:rank.append((sc,r))
 rank.sort(key=lambda x:x[0],reverse=True);return [dict(r,relevance=s) for s,r in rank[:limit]]
def ask(q,lang='ru'):
 h=search(q,6)
 if not h:return {'answer':'В локальной базе пока нет достаточного материала. Добавьте источник или уточните запрос.','evidence':[],'mode':'LOCAL_GROUNDED'}
 bk='body_en' if lang=='en' else 'body_he' if lang=='he' else 'body';tk='title_en' if lang=='en' else 'title_he' if lang=='he' else 'title';intro={'ru':'ENOS нашёл в локальной базе следующие релевантные правила:','en':'ENOS found these relevant rules in the local knowledge base:','he':'ENOS מצא את הכללים הרלוונטיים הבאים במאגר המקומי:'}.get(lang,'ENOS:');chunks=[f"{x.get(tk) or x.get('title')}: {x.get(bk) or x.get('body')}" for x in h[:4]];return {'answer':intro+'\n\n'+'\n\n'.join(chunks),'evidence':[{'id':x.get('id'),'title':x.get(tk) or x.get('title'),'source':x.get('source'),'verification':x.get('verification','CURATED')} for x in h],'mode':'LOCAL_GROUNDED'}
def add_note(title,body,source='USER_NOTE',tags=None):
 x={'id':'note-'+datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f'),'title':title,'body':body,'source':source,'tags':tags or [],'verification':'UNVERIFIED','created_at':datetime.now(timezone.utc).isoformat()};append_json_list(NOTES,x);return x
def sources():return read_json(SOURCES,[])
