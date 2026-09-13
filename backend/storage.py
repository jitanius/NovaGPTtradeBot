from __future__ import annotations
import json, os, threading
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; LOCK=threading.RLock()
def ensure_dirs():
    for p in [DATA,DATA/'knowledge',DATA/'universe',DATA/'imports']: p.mkdir(parents=True,exist_ok=True)
def read_json(path,default):
    ensure_dirs(); p=Path(path); p=p if p.is_absolute() else ROOT/p
    with LOCK:
        if not p.exists(): return default
        try: return json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            try:
                bad=p.with_suffix(p.suffix+'.corrupt')
                if not bad.exists(): bad.write_bytes(p.read_bytes())
            except Exception: pass
            return default
def write_json(path,value):
    ensure_dirs(); p=Path(path); p=p if p.is_absolute() else ROOT/p; p.parent.mkdir(parents=True,exist_ok=True); tmp=p.with_suffix(p.suffix+'.tmp')
    with LOCK: tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8'); os.replace(tmp,p)
def append_json_list(path,item,max_items=20000):
    with LOCK:
        rows=read_json(path,[]); rows=rows if isinstance(rows,list) else []; rows.append(item); write_json(path,rows[-max_items:])
