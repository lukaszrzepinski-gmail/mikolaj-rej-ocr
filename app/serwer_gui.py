#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
serwer_gui.py — nowoczesny webowy interfejs MikolajRej OCR (lokalny serwer + przeglądarka).

Zastępuje okno tkinter interfejsem webowym w stylu makiety: galeria skanów (lazy-load,
zaznaczanie jak Google Photos, obrót), wybór modelu z datą, segmentacja i OCR przez
istniejący silnik (segment_preview.py / ocr_batch.py / report_gen.py), interaktywny raport.

Uruchom przez env htr-env:
  & "C:\\...\\htr-env\\Scripts\\python.exe" serwer_gui.py
Otwiera http://127.0.0.1:5057 i startuje przeglądarkę.

Biblioteka standardowa (http.server) — bez instalacji. Silnik wołany jako podprocesy.
"""
import os, sys, json, glob, threading, subprocess, time, html, webbrowser, urllib.parse, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from gui_model_check import check_model
import gui_lm_options
import traceback
from gui_gallery import image_info

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
SEG_PREVIEW = os.path.join(HERE, "segment_preview.py")
OCR_BATCH = os.path.join(HERE, "ocr_batch.py")
REPORT_GEN = os.path.join(HERE, "report_gen.py")
PORT = int(os.environ.get('REJ_PORT', '5057'))
MODEL_DIR = os.path.abspath(os.environ.get('REJ_MODEL_DIR', os.path.join(HERE, '..', 'models')))
MODEL_ROOTS = [MODEL_DIR]
CKPT_ROOTS = []
RECOMMENDED = [
    ('Rej K11 E26 — pseudo DEV RAW110 7,19%', 'MikolajRej-KRA-K11-E26-step345005.mlmodel'),
]
LM_CANDIDATES = [os.path.join(MODEL_DIR, 'lm6B.bin')]
EXTS = (".png", ".jpg", ".jpeg", ".tif", ".tiff")

def find_lm():
    for p in LM_CANDIDATES:
        if os.path.isfile(p): return p
    return ""

def mtime_str(p):
    try: return datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M")
    except Exception: return "?"

def scan_models(include_archive=False):
    found = {}
    for root in MODEL_ROOTS:
        if os.path.isdir(root):
            for p in glob.glob(os.path.join(root, "**", "*.mlmodel"), recursive=True):
                low = p.lower()
                if "site-packages" in low or "uv-cache" in low: continue
                found[os.path.normpath(p)] = True
    ckpts = {}
    for root in CKPT_ROOTS:
        if os.path.isdir(root):
            for p in glob.glob(os.path.join(root, "**", "epoch-*.ckpt"), recursive=True):
                low = p.lower()
                if "inert" in low or "corrupt" in low or "torn" in low: continue
                try:
                    if os.path.getsize(p) < 1_000_000: continue
                except Exception: continue
                ckpts[os.path.normpath(p)] = True
    out, seen = [], set()
    for label, tail in RECOMMENDED:
        for full in found:
            if full.lower().endswith(tail.lower().replace("/", "\\")):
                out.append({"label": f"{label} — {os.path.basename(full)} ({mtime_str(full)})", "path": full, "kind": "mlmodel"}); seen.add(full); break
    rest = sorted([f for f in found if f not in seen], key=lambda f: os.path.getmtime(f), reverse=True)
    for full in rest:
        out.append({"label": f"{os.path.basename(full)} [{os.path.basename(os.path.dirname(full))}] ({mtime_str(full)})", "path": full, "kind": "mlmodel"})
    for full in sorted(ckpts, key=lambda f: os.path.getmtime(f), reverse=True):
        par = os.path.basename(os.path.dirname(os.path.dirname(full)))
        out.append({"label": f"⚠ .ckpt (wymaga eksportu) — {os.path.basename(full)} [{par}] ({mtime_str(full)})", "path": full, "kind": "ckpt"})
    if not include_archive:
        out = [item for item in out if item['path'] in seen]
    for item in out:
        if item['kind'] == 'mlmodel':
            validation = check_model(item['path'])
            item['usable'] = validation['ok']
            item['validation_error'] = validation.get('error')
            if not validation['ok']:
                item['label'] = '⚠ Niesprawny eksport — ' + item['label']
        else:
            item['usable'] = False
    if not include_archive:
        out = [item for item in out if item['usable']]
    return out

# stan serwera (jedna sesja — lokalne użycie)
STATE = {"folder": None, "images": [], "jobs": {}}

def list_images(folder):
    return [os.path.join(folder, f) for f in sorted(os.listdir(folder))
            if f.lower().endswith(EXTS) and not f.startswith("_")]

def list_drives():
    import string, ctypes
    drives = []
    try:
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for i, letter in enumerate(string.ascii_uppercase):
            if bitmask & (1 << i): drives.append(letter + ":\\\\")
    except Exception:
        drives = ["C:\\\\"]
    return drives

def browse_dir(path):
    """Zwraca podkatalogi + liczbę obrazów w danym katalogu. Pusta ścieżka => lista dysków."""
    if not path:
        return {"path": "", "parent": None, "dirs": list_drives(), "img_count": 0, "is_root": True}
    path = os.path.normpath(path)
    if not os.path.isdir(path):
        return {"error": "Nie ma takiego folderu."}
    dirs = []
    try:
        for name in sorted(os.listdir(path)):
            full = os.path.join(path, name)
            if os.path.isdir(full) and not name.startswith((".", "$")):
                dirs.append(full)
    except PermissionError:
        return {"error": "Brak dostępu do tego folderu."}
    try:
        img_count = len([f for f in os.listdir(path) if f.lower().endswith(EXTS) and not f.startswith("_")])
    except Exception:
        img_count = 0
    parent = os.path.dirname(path.rstrip("\\\\")) if len(os.path.splitdrive(path)[1].strip("\\\\")) else ""
    return {"path": path, "parent": parent, "dirs": dirs, "img_count": img_count, "is_root": False}

def env_for(device):
    env = dict(os.environ)
    env["PYTHONWARNINGS"]="ignore"; env["KRAKEN_TELEMETRY"]="0"
    env["PYTHONUTF8"]="1"; env["PYTHONIOENCODING"]="utf-8"
    if device=="cpu": env["CUDA_VISIBLE_DEVICES"]=""
    return env

# --- rejestr wcześniejszych raportów (trwały między restartami) ---
REGISTRY = os.path.join(HERE, "_mikolajrej_raporty.json")
def load_registry():
    try: return json.load(open(REGISTRY, encoding="utf-8"))
    except Exception: return []
def save_report_entry(folder, model, n_pages):
    reg = load_registry()
    rep = os.path.join(folder, "_RAPORT_OCR.html")
    reg = [e for e in reg if e.get("folder") != folder]   # bez duplikatu
    reg.insert(0, {"folder": folder, "report": rep, "model": model, "pages": n_pages,
                   "when": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")})
    reg = reg[:50]
    try: json.dump(reg, open(REGISTRY, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    except Exception: pass
def known_reports():
    """Rejestr + autodetekcja: foldery z istniejącym _RAPORT_OCR.html, których nie ma w rejestrze."""
    reg = load_registry()
    known = {e["folder"] for e in reg}
    out = []
    for e in reg:
        if os.path.isfile(e.get("report","")):
            e = dict(e); e["exists"] = True; out.append(e)
    return out

def run_job(job_id, cmd, env, complete=True):
    logdir = os.path.join(HERE, 'logs'); os.makedirs(logdir, exist_ok=True)
    logfile = os.path.join(logdir, 'job-' + job_id + '.log')
    job = {"lines": [], "done": False, "exit_code": None, "error": None, "log_path": logfile}
    STATE["jobs"][job_id] = job
    code = 1
    with open(logfile, 'w', encoding='utf-8') as saved:
        def append(line):
            job['lines'].append(line); saved.write(line + '\n'); saved.flush()
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, encoding="utf-8", errors="replace", env=env, bufsize=1)
            for raw in proc.stdout:
                append(raw.rstrip("\n"))
            code = proc.wait()
            if code:
                job['error'] = 'OCR nie powiodl sie (kod ' + str(code) + '). Pelny blad: ' + logfile
                append('ERROR\t' + job['error'])
        except Exception as exc:
            job['error'] = str(exc) + '. Pelny blad: ' + logfile
            append(traceback.format_exc())
        job['exit_code'] = code
        job['done'] = complete or code != 0
    return code

PAGE = """<!doctype html><html lang="pl"><head><meta charset="utf-8"><title>MikolajRej OCR</title>
<style>
:root{--bg:#faf9fc;--card:#fff;--ink:#1a1a1a;--mut:#9ca3af;--sec:#5e5e5e;--line:rgba(0,0,0,.08);
 --pri:#9333ea;--pri2:#a855f7;--prib:#f3e8ff;--ok:#16a34a;--okb:rgba(34,197,94,.12);--rad:12px;--sh:0 4px 12px rgba(0,0,0,.08);}
*{box-sizing:border-box}body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--ink);margin:0;padding:20px}
.app{max-width:1060px;margin:0 auto}
.topbar{display:flex;align-items:center;gap:13px;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px 18px;box-shadow:var(--sh);margin-bottom:16px}
.logo{width:38px;height:38px;border-radius:10px;background:linear-gradient(135deg,var(--pri),var(--pri2));display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700}
.topbar h1{font-size:16px;margin:0}.topbar .sub{font-size:12px;color:var(--mut);margin-top:2px}.spacer{flex:1}
.btn{border:none;border-radius:17px;padding:9px 18px;font-size:13.5px;font-weight:600;cursor:pointer;transition:all .15s;font-family:inherit}
.btn-primary{background:var(--pri);color:#fff}.btn-primary:hover{background:var(--pri2);transform:translateY(-1px);box-shadow:var(--sh)}
.btn-ghost{background:var(--surface,#f9fafb);color:var(--sec);border:1px solid var(--line)}.btn-ghost:hover{background:#f3f4f6}
.controls{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:14px}
.select{background:var(--card);border:1px solid var(--line);border-radius:var(--rad);padding:9px 12px;font-size:13px;min-width:340px;font-family:inherit}
.chip{display:inline-flex;align-items:center;gap:6px;background:#f9fafb;border:1px solid var(--line);border-radius:17px;padding:6px 13px;font-size:12.5px;cursor:pointer}
.chip.on{background:var(--prib);border-color:var(--pri);color:var(--pri);font-weight:600}
.count{font-size:12.5px;color:var(--mut)}
.browser{background:var(--card);border:1px solid var(--line);border-radius:var(--rad);padding:12px;margin-bottom:14px;box-shadow:var(--sh)}
.crumb{font-size:12.5px;color:var(--sec);margin-bottom:8px;word-break:break-all}
.dirlist{max-height:220px;overflow:auto;border:1px solid var(--line);border-radius:8px}
.diritem{padding:7px 12px;font-size:13px;cursor:pointer;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:8px}
.diritem:hover{background:#f3f4f6}.diritem:last-child{border-bottom:none}
.diritem .ic{color:var(--pri)}
.browser .bar{display:flex;gap:8px;margin-top:10px;align-items:center}
.row{display:flex;gap:8px;align-items:center;margin-bottom:12px;flex-wrap:wrap}
.gallery{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
.scan{position:relative;background:var(--card);border:1px solid var(--line);border-radius:var(--rad);overflow:hidden;box-shadow:var(--sh);transition:all .18s}
.scan:hover{transform:translateY(-2px)}.scan.sel{border:2px solid var(--pri)}
.scan img{width:100%;height:150px;object-fit:cover;display:block;background:#eee}
.scan .cap{padding:7px 9px;font-size:11px;color:var(--sec);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.scan .modelmeta{padding:0 9px 8px;font-size:11px;line-height:1.5;overflow-wrap:anywhere;color:#444;min-height:48px}
.scan .actions{display:flex;flex-wrap:wrap;gap:5px;padding:0 8px 10px}.scan .actions button{font-size:11px;padding:6px;border:1px solid #ddd;border-radius:6px;background:white;cursor:pointer}
.scan .check{position:absolute;top:7px;left:7px;width:22px;height:22px;border-radius:6px;background:rgba(255,255,255,.92);border:1px solid var(--line);display:flex;align-items:center;justify-content:center;color:var(--pri);font-size:13px}
.scan.sel .check{background:var(--pri);color:#fff}
.scan .rot{position:absolute;top:7px;right:7px;display:flex;gap:3px}
.scan .rot button{width:24px;height:24px;border-radius:6px;border:none;background:rgba(255,255,255,.92);cursor:pointer}
.slider{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--sec)}
#log{font-family:var(--font-mono,monospace);font-size:11.5px;background:#0f1117;color:#cdd3de;border-radius:10px;padding:10px;height:120px;overflow:auto;white-space:pre-wrap;margin-top:12px;display:none}
.prog{height:6px;background:#eee;border-radius:3px;overflow:hidden;margin-top:10px;display:none}.prog>div{height:100%;width:0;background:var(--pri);transition:width .2s}
</style></head><body><div class="app">
<div class="topbar"><div class="logo">MR</div>
 <div><h1>MikolajRej OCR</h1><div class="sub" id="folderlbl">wybierz folder ze skanami</div></div>
 <div class="spacer"></div>
 <button class="btn btn-ghost" id="segbtn" disabled>Segmentuj</button>
 <button class="btn btn-primary" id="ocrbtn" disabled>Rozpoznaj →</button>
</div>
<div class="browser">
 <div class="crumb" id="crumb">Wybierz dysk…</div>
 <div class="dirlist" id="dirlist"></div>
 <div class="bar">
   <button class="btn btn-ghost" id="up">↑ W górę</button>
   <input class="select" id="folder" placeholder="lub wklej ścieżkę ręcznie" style="min-width:260px" />
   <button class="btn btn-ghost" id="go">Idź</button>
   <button class="btn btn-primary" id="openhere">Otwórz ten folder (<span id="imgcnt">0</span> skanów)</button>
 </div>
</div>
<div class="controls">
 <select class="select" id="model"></select>
 <label style="font-size:12px"><input type="checkbox" id="model-archive"> Pokaż modele archiwalne</label>
 <label>Układ tekstu <select class="select" id="layout" style="min-width:170px"><option value="auto">Automatycznie</option><option value="single">1 kolumna</option><option value="two">2 kolumny: lewa, prawa</option></select></label>
</div>
<div class="browser" id="recentbox" style="display:none">
 <div class="crumb">🕘 Ostatnie raporty (gotowe — otwórz bez ponownego przetwarzania)</div>
 <div class="dirlist" id="recentlist"></div>
</div>
<div class="controls">
 <span class="chip" id="gpu" title="Lokalna karta; wymaga jawnego REJ_GPU_LOCK">GPU lokalne</span>
 <label>Drugi LM (opcjonalnie) <select class="select" id="lm-second"><option value="">Nie używaj drugiego LM</option></select></label>
 <label>Model językowy <select class="select" id="lm-choice"><option value="none">Bez modelu językowego</option></select></label>
 <span class="chip on" id="diff" title="RAW i wynik z LM są zawsze zachowywane w historii">Porównanie RAW / LM w raporcie</span>
 <div class="slider">α<input type="range" id="alpha" min="0" max="2" step="0.1" value="0.5"><span id="av">0.5</span></div>
 <div class="slider">β<input type="range" id="beta" min="0" max="3" step="0.1" value="1.0"><span id="bv">1.0</span></div>
 <div class="slider">beam<input type="range" id="beam" min="8" max="128" step="8" value="64"><span id="bmv">64</span></div>
</div>
<div class="row">
 <button class="btn btn-ghost" id="selall">☑ Zaznacz wszystkie</button>
 <button class="btn btn-ghost" id="selnone">☐ Odznacz wszystkie</button>
 <span class="count" id="selcount"></span>
 <button class="btn btn-ghost" id="historybtn">Historia i porównanie zaznaczonych</button>
 <a class="btn btn-ghost" id="reportlink" href="#" style="display:none" target="_blank">🌐 Otwórz raport</a>
</div>
<div class="prog" id="prog"><div></div></div>
<div id="log"></div>
<div class="gallery" id="gal"></div>
</div>
<div id="reportview" style="display:none;position:fixed;inset:0;background:var(--bg);z-index:50;flex-direction:column">
  <div style="display:flex;flex-wrap:wrap;align-items:center;gap:12px;padding:12px 18px;background:var(--card);border-bottom:1px solid var(--line);box-shadow:var(--sh)">
    <button class="btn btn-ghost" id="backbtn">← Wróć do galerii</button>
    <strong id="reporttitle" style="font-size:14px">Raport</strong>
    <span id="scan-actions" style="display:none">
      <label>Inny model <select id="scan-model" class="select" style="max-width:350px"></select></label>
      <label>LM <select id="scan-lm" class="select" style="max-width:250px"></select></label>
      <button id="scan-run" class="btn btn-primary">Przetwórz tym modelem</button>
      <span id="scan-status" role="status"></span>
    </span>
    <span class="spacer"></span>
    <a class="btn btn-ghost" id="reportnewtab" href="#" target="_blank">Otwórz w nowej karcie ↗</a>
  </div>
  <iframe id="reportframe" style="flex:1;border:0;width:100%;height:100%"></iframe>
</div>
<script>
let MODELS=[], ITEMS=[], LM_AVAIL=false;
let ACTIVE_SCAN=null, GALLERY_GENERATION=0;
const $=id=>document.getElementById(id);
function showReport(url,title){
  $('reportframe').src=url;
  $('reporttitle').textContent=title||'Raport';
  $('reportnewtab').href=url;
  $('reportview').style.display='flex';
}
function hideReport(){ $('reportview').style.display='none'; $('reportframe').src='about:blank'; ACTIVE_SCAN=null;$('scan-actions').style.display='none'; }
function opt(id,on){$(id).classList.toggle('on',on);}
['gpu'].forEach(id=>$(id).onclick=()=>$(id).classList.toggle('on'));
$('lm-choice').onchange=()=>{try{localStorage.setItem('mr-lm-choice',$('lm-choice').value);}catch(e){}if($('lm-choice').value==='korba'){$('beta').value=0;$('bv').textContent='0';}};
['alpha','beta','beam'].forEach(id=>{const v={alpha:'av',beta:'bv',beam:'bmv'}[id];$(id).oninput=()=>$(v).textContent=$(id).value;});

function setModelChoices(models){
 const prior=MODELS[+$('model').value]?.path, scanPrior=MODELS[+$('scan-model').value]?.path;MODELS=models;
 for(const id of ['model','scan-model']){const sel=$(id);sel.replaceChildren();
  MODELS.forEach((m,i)=>{const o=document.createElement('option');o.value=i;o.textContent=m.label;o.disabled=m.usable===false;sel.appendChild(o);});
  const index=MODELS.findIndex(m=>m.path===(id==='model'?prior:scanPrior));
  sel.value=index>=0?index:MODELS.findIndex(m=>m.usable!==false);
 }
}
$('model-archive').onchange=async()=>{try{const d=await(await fetch('/api/models?archive='+($('model-archive').checked?'1':'0'))).json();setModelChoices(d.models);}catch(e){alert('Nie można odczytać modeli: '+e);}};
fetch('/api/models').then(r=>r.json()).then(d=>{
  MODELS=d.models; LM_AVAIL=d.lm;
  const sel=$('model'); setModelChoices(MODELS);
  // Prefer the documented E26 publication model.
  const idx=MODELS.findIndex(m=>m.label.includes('K11 E26'));
  sel.value = idx>=0 && MODELS[idx].usable!==false ? idx : MODELS.findIndex(m=>m.usable!==false);
  const lmSelect=$('lm-choice');lmSelect.replaceChildren();
  (d.lm_choices||[]).forEach(m=>{const o=document.createElement('option');o.value=m.id;o.textContent=m.label+(m.available?'':' — niedostępny');lmSelect.appendChild(o);});
  for(const m of (d.lm_choices||[]).filter(m=>m.id!=='none')){
    const option=document.createElement('option');option.value=m.id;option.textContent=m.label;option.disabled=!m.available;$('lm-second').appendChild(option);
  }
  const settings=d.lm_settings||{};
  try{lmSelect.value=localStorage.getItem('mr-lm-choice')||settings.choice||'none';}catch(e){lmSelect.value=settings.choice||'none';}
  if(!lmSelect.value)lmSelect.value='none';
  if(lmSelect.value==='korba'){$('beta').value=0;$('bv').textContent='0';}
});

let CUR={path:"",parent:null,img_count:0};
let BROWSE_GENERATION=0, LOAD_GENERATION=0;
function browse(path){
  const generation=++BROWSE_GENERATION;
  ++LOAD_GENERATION;++GALLERY_GENERATION;
  ITEMS=[];renderGal();$('segbtn').disabled=true;$('ocrbtn').disabled=true;
  $('folderlbl').textContent='Wczytywanie katalogu…';
  fetch('/api/browse?path='+encodeURIComponent(path||'')).then(r=>r.json()).then(d=>{
    if(generation!==BROWSE_GENERATION)return;
    if(d.error){alert(d.error);return;}
    CUR=d; $('crumb').textContent=d.path||'Wybierz dysk…';
    $('imgcnt').textContent=d.img_count||0;
    $('openhere').style.opacity=(d.img_count>0)?1:.5;
    const dl=$('dirlist');dl.innerHTML='';
    (d.dirs||[]).forEach(full=>{
      const name=full.replace(/\\\\$/,'').split('\\\\').pop()||full;
      const el=document.createElement('div');el.className='diritem';
      el.innerHTML='<span class="ic">📁</span>'+name;
      el.onclick=()=>browse(full);
      dl.appendChild(el);
    });
    if(!d.dirs||!d.dirs.length){const e=document.createElement('div');e.className='diritem';e.style.color='#9ca3af';e.textContent='(brak podfolderów)';dl.appendChild(e);}
    $('folder').value=d.path||'';
    if(d.path)loadFolder(d.path);
    else $('folderlbl').textContent='Wybierz dysk lub katalog ze skanami';
  });
}
function loadFolder(f){
  const generation=++LOAD_GENERATION;
  fetch('/api/list?folder='+encodeURIComponent(f)).then(r=>r.json()).then(d=>{
    if(generation!==LOAD_GENERATION)return;
    if(d.error){alert(d.error);return;}
    ITEMS=d.images.map(p=>({path:p,name:p.split('\\\\').pop(),sel:true,rot:0}));
    $('folder').value=f;   // KLUCZOWE: payload() czyta folder z tego pola — bez tego wysyłał pusty folder
    $('folderlbl').textContent=f+' · '+ITEMS.length+' skanów';
    $('segbtn').disabled=!ITEMS.length;$('ocrbtn').disabled=!ITEMS.length;
    renderGal();
    refreshGalleryInfo();
  });
}
$('up').onclick=()=>browse(CUR.parent!==null?CUR.parent:'');
$('go').onclick=()=>browse($('folder').value.trim());
$('openhere').onclick=()=>{ if(CUR.path && CUR.img_count>0) loadFolder(CUR.path); else alert('Ten folder nie ma skanów — wejdź do folderu, który je zawiera.'); };
browse('');  // start: lista dysków
$('backbtn').onclick=hideReport;
// ostatnie raporty — gotowe, bez ponownego przetwarzania
fetch('/api/reports').then(r=>r.json()).then(d=>{
  const list=d.reports||[]; if(!list.length)return;
  $('recentbox').style.display='block';
  const rl=$('recentlist');rl.innerHTML='';
  list.forEach(e=>{
    const el=document.createElement('div');el.className='diritem';
    const folderName=e.folder.replace(/\\\\$/,'').split('\\\\').pop();
    el.innerHTML='<span class="ic">📄</span>'+folderName+' · '+(e.pages||'?')+' stron · '+(e.model||'')+' · '+(e.when||'');
    el.onclick=()=>showReport('/report?path='+encodeURIComponent(e.report), folderName);
    rl.appendChild(el);
  });
});
function renderGal(){
  const g=$('gal');g.innerHTML='';
  ITEMS.forEach((it,i)=>{
    const d=document.createElement('div');d.className='scan'+(it.sel?' sel':'');
    d.innerHTML=`<div class="check">${it.sel?'✓':''}</div>
      <div class="rot"><button data-r="-90">⟲</button><button data-r="90">⟳</button></div>
      <img loading="lazy" src="/img?path=${encodeURIComponent(it.path)}&rot=${it.rot}">
      <div class="cap"></div><div class="modelmeta"></div>
      <div class="actions"><button class="preview">Podgląd / wyniki</button><button class="another">Przetwórz innym modelem</button></div>`;
    d.dataset.path=it.path;
    d.querySelector('.cap').textContent=it.name;
    updateCardInfo(d,it);
    d.querySelector('img').onclick=()=>{it.sel=!it.sel;renderGal();};
    d.querySelector('.check').onclick=()=>{it.sel=!it.sel;renderGal();};
    d.querySelectorAll('.rot button').forEach(b=>b.onclick=ev=>{ev.stopPropagation();it.rotDirty=true;it.rot=((it.rot+(+b.dataset.r))%360+360)%360;renderGal();});
    d.querySelector('.preview').onclick=()=>openScan(it,false);
    d.querySelector('.another').onclick=()=>openScan(it,true);
    g.appendChild(d);
  });
  $('selcount').textContent='zaznaczono '+ITEMS.filter(x=>x.sel).length+' z '+ITEMS.length;
}
function updateCardInfo(card,it){
  const info=it.info,meta=card.querySelector('.modelmeta');
  meta.textContent=info?(info.processed?'Model: '+info.model+' · '+info.lm+' · '+info.model_count+' modeli / '+info.variant_count+' wyników':info.model):'Sprawdzam historię…';
  meta.title=info?(info.models||[]).map(m=>m.name+(m.sha256?' · SHA256 '+m.sha256:'')).join(' | '):'';
  if(info&&info.status==='legacy')meta.textContent+=' · starszy zapis, identyfikacja niepełna';
  if(info&&info.error)meta.title=info.error;
}
async function refreshGalleryInfo(){
  const generation=++GALLERY_GENERATION, pending=ITEMS.slice();
  async function worker(){while(pending.length&&generation===GALLERY_GENERATION){const it=pending.shift();try{
    const response=await fetch('/api/image-history?path='+encodeURIComponent(it.path));it.info=await response.json();
    if(generation!==GALLERY_GENERATION)return;
    if(!it.rotDirty&&it.info.processed)it.rot=it.info.rotation;
    for(const card of $('gal').children)if(card.dataset.path===it.path){updateCardInfo(card,it);card.querySelector('img').src='/img?path='+encodeURIComponent(it.path)+'&rot='+it.rot;}
  }catch(error){it.info={model:'Nie można odczytać historii',status:'error'};if(generation===GALLERY_GENERATION)for(const card of $('gal').children)if(card.dataset.path===it.path)updateCardInfo(card,it);}}}
  await Promise.all([worker(),worker(),worker()]);
}
async function openScan(it,chooseOther){
  ACTIVE_SCAN=it;$('scan-actions').style.display='inline-flex';
  const select=$('scan-model');select.replaceChildren();
  MODELS.forEach((model,index)=>{const option=document.createElement('option');option.value=index;option.textContent=model.label;option.disabled=model.usable===false;select.appendChild(option);});
  const other=MODELS.findIndex(m=>m.usable!==false&&m.path!==it.info?.model_path);
  select.value=chooseOther&&other>=0?other:$('model').value;
  const lm=$('scan-lm');lm.replaceChildren();
  for(const option of $('lm-choice').options)lm.appendChild(option.cloneNode(true));lm.value=$('lm-choice').value;
  showReport('/scan-preview?path='+encodeURIComponent(it.path)+'&rot='+it.rot,it.name);
  try{
    const info=await (await fetch('/api/image-history?path='+encodeURIComponent(it.path))).json();it.info=info;
    if(ACTIVE_SCAN!==it)return;
    if(chooseOther){const alternative=MODELS.findIndex(m=>m.usable!==false&&m.path!==info.model_path);if(alternative>=0)select.value=alternative;}
    if(info.processed){const data=payload();data.items=[{path:it.path,rot:it.rot}];
      const result=await (await fetch('/api/history-report',{method:'POST',body:JSON.stringify(data)})).json();
      if(ACTIVE_SCAN!==it)return;
      if(result.error)alert(result.error);else showReport(result.report,it.name+' — historia i różnice');
    }
    if(chooseOther)select.focus();
  }catch(error){alert('Nie można otworzyć wyników: '+error);}
}
$('scan-lm').onchange=()=>{$('lm-choice').value=$('scan-lm').value;$('lm-choice').dispatchEvent(new Event('change'));};
$('scan-run').onclick=async()=>{
  const it=ACTIVE_SCAN;if(!it)return;
  const data=payload(),index=+$('scan-model').value;
  if(!MODELS[index]||MODELS[index].usable===false){alert('Wybierz dostępny model rozpoznawania.');return;}
  data.model_idx=index;data.model_path=MODELS[index].path;data.items=[{path:it.path,rot:it.rot}];
  $('scan-run').disabled=true;
  $('scan-status').textContent='Rozpoznawanie tego skanu…';
  try{const result=await (await fetch('/api/ocr',{method:'POST',body:JSON.stringify(data)})).json();
    if(result.error){alert(result.error);$('scan-run').disabled=false;$('scan-status').textContent='';return;}poll(result.job);
  }catch(error){alert('Błąd: '+error);$('scan-run').disabled=false;$('scan-status').textContent='';}
};
$('selall').onclick=()=>{ITEMS.forEach(x=>x.sel=true);renderGal();};
$('selnone').onclick=()=>{ITEMS.forEach(x=>x.sel=false);renderGal();};

function payload(){return{folder:$('folder').value.trim(),
  layout:$('layout').value, model_idx:+$('model').value, model_path:MODELS[+$('model').value]?.path, device:$('gpu').classList.contains('on')?'cuda:0':'cpu',
  lm:$('lm-choice').value!=='none', lm_choice:$('lm-choice').value, lm_second:$('lm-second').value, diff:true,
  alpha:+$('alpha').value, beta:+$('beta').value, beam:+$('beam').value,
  items:ITEMS.filter(x=>x.sel).map(x=>({path:x.path,rot:x.rot}))};}

function poll(job){
  $('log').style.display='block';$('prog').style.display='block';
  const t=setInterval(()=>{fetch('/api/job?id='+job).then(r=>r.json()).then(d=>{
    $('log').textContent=d.lines.slice(-40).join('\\n');$('log').scrollTop=1e9;
    const done=d.lines.filter(l=>l.startsWith('PROGRESS')||l.startsWith('SEG')).length;
    const tot=ITEMS.filter(x=>x.sel).length||1;$('prog').firstChild.style.width=Math.min(100,100*done/tot)+'%';
    if(d.done){clearInterval(t);
      $('scan-run').disabled=false;refreshGalleryInfo();
      $('scan-status').textContent='';
      if(d.error){$('log').textContent+='\\n'+d.error;alert(d.error);return;}
      if(d.report){
        showReport(d.report, 'Raport OCR');   // w tej samej karcie — bez blokady okien
      }
    }
  });},800);
}
$('segbtn').onclick=()=>fetch('/api/segment',{method:'POST',body:JSON.stringify(payload())}).then(r=>r.json()).then(d=>{if(d.error){alert(d.error);return;}poll(d.job);}).catch(e=>alert('Błąd: '+e));
$('ocrbtn').onclick=()=>fetch('/api/ocr',{method:'POST',body:JSON.stringify(payload())}).then(r=>r.json()).then(d=>{if(d.error){alert(d.error);return;}poll(d.job);}).catch(e=>alert('Błąd: '+e));
$('historybtn').onclick=()=>fetch('/api/history-report',{method:'POST',body:JSON.stringify(payload())}).then(r=>r.json()).then(d=>{if(d.error){alert(d.error);return;}showReport(d.report,'Historia i porównanie');}).catch(e=>alert('Błąd: '+e));
</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def _send(self, code, ctype, body):
        self.send_response(code); self.send_header("Content-Type", ctype); self.end_headers()
        if isinstance(body, str): body = body.encode("utf-8")
        self.wfile.write(body)
    def log_message(self, *a): pass

    def _local_request(self):
        expected = {f'127.0.0.1:{PORT}', f'localhost:{PORT}'}
        origin = self.headers.get('Origin')
        host = self.headers.get('Host', '')
        if host not in expected or (origin and origin not in {f'http://{item}' for item in expected}):
            self._send(403, 'text/plain', 'Tylko lokalne, zgodne źródło żądania.')
            return False
        if self.headers.get('Sec-Fetch-Site') == 'cross-site':
            self._send(403, 'text/plain', 'Żądanie z innej strony zostało odrzucone.')
            return False
        return True

    def do_GET(self):
        if not self._local_request(): return
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        if u.path == "/" : return self._send(200, "text/html; charset=utf-8", PAGE)
        if u.path == '/api/line-corrections':
            try:
                from gui_line_corrections import saved_corrections
                result=saved_corrections(q.get('path',[''])[0],q.get('sha',[''])[0],q.get('variant',[''])[0])
                return self._send(200,'application/json',json.dumps({'samples':result},ensure_ascii=False))
            except (OSError,ValueError,KeyError,TypeError) as error:
                return self._send(400,'application/json',json.dumps({'error':str(error)},ensure_ascii=False))
        if u.path == '/api/image-history':
            image=q.get('path',[''])[0]
            if not os.path.isfile(image) or not image.lower().endswith(EXTS):
                return self._send(400,'application/json',json.dumps({'error':'Nie ma takiego skanu.'}))
            return self._send(200,'application/json',json.dumps(image_info(image),ensure_ascii=False))
        if u.path == '/scan-preview':
            image=q.get('path',[''])[0]
            rotation=int(q.get('rot',['0'])[0])%360
            if not os.path.isfile(image) or not image.lower().endswith(EXTS):
                return self._send(404,'text/plain','Brak skanu')
            src='/img?path='+urllib.parse.quote(image)+'&rot='+str(rotation)+'&full=1'
            page='<html lang="pl"><meta charset="utf-8"><body style="margin:0;background:#eee;text-align:center"><p>Podgląd skanu. Po rozpoznaniu pojawi się historia wyników i porównanie różnic.</p><img style="max-width:100%;height:auto" alt="'+html.escape(os.path.basename(image),quote=True)+'" src="'+html.escape(src,quote=True)+'"></body></html>'
            return self._send(200,'text/html; charset=utf-8',page)
        if u.path == "/api/models":
            return self._send(200, "application/json", json.dumps({"models": scan_models(q.get("archive",["0"])[0]=="1"), "lm": bool(find_lm()), "lm_choices": gui_lm_options.choices(find_lm()), 'lm_settings':gui_lm_options.load_settings()}))
        if u.path == "/api/list":
            folder = q.get("folder",[""])[0]
            if not os.path.isdir(folder): return self._send(200,"application/json",json.dumps({"error":"Nie ma takiego folderu."}))
            STATE["folder"]=folder
            return self._send(200,"application/json",json.dumps({"images": list_images(folder)}))
        if u.path == "/api/browse":
            return self._send(200,"application/json",json.dumps(browse_dir(q.get("path",[""])[0])))
        if u.path == "/img":
            path = q.get("path",[""])[0]; rot = int(q.get("rot",["0"])[0])
            try:
                from PIL import Image; import io
                im = Image.open(path).convert("RGB")
                if rot: im = im.rotate(-rot, expand=True)
                full = q.get("full",["0"])[0] == "1"
                if not full:
                    im.thumbnail((360,360))
                else:
                    # raport: ogranicz do 1600 px dłuższego boku (ostrość + rozsądny rozmiar)
                    if max(im.size) > 1600:
                        s = 1600/max(im.size); im = im.resize((int(im.width*s), int(im.height*s)))
                buf=io.BytesIO(); im.save(buf,"JPEG",quality=85)
                return self._send(200,"image/jpeg",buf.getvalue())
            except Exception as e:
                return self._send(404,"text/plain",str(e))
        if u.path == "/api/job":
            j = STATE["jobs"].get(q.get("id",[""])[0], {"lines":[],"done":True})
            rep = j.get("report")
            return self._send(200,"application/json",json.dumps({"lines":j["lines"],"done":j["done"],"report":rep,"error":j.get("error"),"exit_code":j.get("exit_code"),"log_path":j.get("log_path")}))
        if u.path == "/report":
            path = q.get("path",[""])[0]
            if os.path.isfile(path):
                htmlc = open(path,encoding="utf-8").read()
                if 'class="rr-archive"' not in htmlc:
                    import re, report_gen
                    saved_images = [html.unescape(value) for value in re.findall(r'src="file:///([^"\n]+)"', htmlc)]
                    saved_paths = list(dict.fromkeys(os.path.splitext(value)[0]+'__ocr.json' for value in saved_images))
                    if saved_paths and all(os.path.isfile(value) for value in saved_paths):
                        report_gen.build_report(os.path.dirname(path), path, 'Historia modeli i LM', saved_paths)
                        htmlc = open(path,encoding="utf-8").read()
                # Przepisz obrazy file:///... na endpoint /img?path=... — inaczej przeglądarka
                # blokuje file:// wewnątrz strony serwowanej po HTTP (puste skany w raporcie).
                import re as _re
                def _rw(m):
                    fp = m.group(1).replace("/", os.sep)
                    return 'src="/img?path=' + urllib.parse.quote(fp) + '&full=1"'
                htmlc = _re.sub(r'src="file:///([^"]+)"', _rw, htmlc)
                return self._send(200,"text/html; charset=utf-8",htmlc)
            return self._send(404,"text/plain","brak raportu")
        if u.path == "/api/reports":
            rep = []
            try:
                if os.path.isfile(REGISTRY):
                    raw = json.load(open(REGISTRY, encoding="utf-8"))
                    for e in raw:
                        if e.get("folder") and e.get("report") and os.path.isfile(e.get("report","")):
                            rep.append(e)
            except Exception as ex:
                return self._send(200,"application/json",json.dumps({"reports":[],"error":str(ex)}))
            return self._send(200,"application/json",json.dumps({"reports":rep}))
        return self._send(404,"text/plain","not found")

    def do_POST(self):
        if not self._local_request(): return
        n=int(self.headers.get("Content-Length",0)); data=json.loads(self.rfile.read(n).decode("utf-8"))
        if urllib.parse.urlparse(self.path).path == '/api/line-correction':
            try:
                from gui_line_corrections import save_correction
                result=save_correction(data)
                return self._send(200,'application/json',json.dumps(result,ensure_ascii=False))
            except (OSError,ValueError,KeyError,TypeError) as error:
                return self._send(400,'application/json',json.dumps({'error':str(error)},ensure_ascii=False))
        folder=data.get("folder","")
        layout=data.get("layout","auto")
        if layout not in ("auto","single","two"):
            return self._send(400,"application/json",json.dumps({"error":"Nieznany układ tekstu."},ensure_ascii=False))
        # WALIDACJA: pusty / nieistniejący folder albo brak zaznaczonych skanów -> błąd, bez tworzenia śmieci
        if not folder or not os.path.isdir(folder):
            return self._send(400,"application/json",json.dumps({"error":"Nie wybrano folderu ze skanami (albo folder nie istnieje)."}))
        if not data.get("items"):
            return self._send(400,"application/json",json.dumps({"error":"Nie zaznaczono żadnych skanów do przetworzenia."}))
        if urllib.parse.urlparse(self.path).path == '/api/history-report':
            import report_gen
            paths = [os.path.splitext(it['path'])[0] + '__ocr.json' for it in data['items']]
            paths = [p for p in paths if os.path.isfile(p)]
            if not paths:
                return self._send(400, 'application/json', json.dumps({'error': 'Brak zapisanych wyników OCR dla zaznaczonych skanów.'}))
            out = os.path.join(folder, '_POROWNANIE_OCR.html')
            report_gen.build_report(folder, out, 'Historia modeli i LM', paths)
            return self._send(200, 'application/json', json.dumps({'report': '/report?path=' + urllib.parse.quote(out)}))
        pdir=os.path.join(folder,"_podglad_segmentacji"); os.makedirs(pdir,exist_ok=True)
        device=data.get("device","cpu"); env=env_for(device)
        job_id=str(int(time.time()*1000))
        u=urllib.parse.urlparse(self.path)
        if u.path=="/api/segment":
            lst=os.path.join(pdir,"_do_segmentacji.txt")
            open(lst,"w",encoding="utf-8").write("\n".join(f"{it['path']}\t{it['rot']}" for it in data["items"]))
            cmd=[PY,SEG_PREVIEW,"--images",lst,"--preview-dir",pdir,"--device",device,"--layout",layout]
            threading.Thread(target=run_job,args=(job_id,cmd,env),daemon=True).start()
            return self._send(200,"application/json",json.dumps({"job":job_id}))
        if u.path=="/api/ocr":
            models = scan_models(include_archive=True)
            requested = data.get('model_path')
            if requested:
                selected = next((item for item in models if item['path'] == requested), None)
            else:
                index = data.get('model_idx')
                selected = models[index] if isinstance(index, int) and 0 <= index < len(models) else None
            if selected is None:
                return self._send(400, 'application/json', json.dumps({'error': 'Wybierz model z aktualnej listy.'}))
            model = selected['path']
            validation = check_model(model)
            if not validation['ok']:
                return self._send(400, 'application/json', json.dumps({'error': validation['error']}, ensure_ascii=False))
            lst=os.path.join(pdir,"_do_ocr_"+job_id+".txt")
            open(lst,"w",encoding="utf-8").write("\n".join(f"{it['path']}\t{it['rot']}" for it in data["items"]))
            choice = data.get('lm_choice', 'legacy' if data.get('lm') else 'none')
            try:
                lm_path=gui_lm_options.resolve(choice, find_lm())
                second_choice=data.get('lm_second','')
                if second_choice and (choice=='none' or second_choice==choice or second_choice=='none'):
                    raise ValueError('Wybierz dwa różne LM lub wyłącz drugi LM.')
                second_path=gui_lm_options.resolve(second_choice, find_lm()) if second_choice else '' 
            except ValueError as error:
                return self._send(400, 'application/json', json.dumps({'error':str(error)},ensure_ascii=False))
            if data.get('lm') and not lm_path:
                return self._send(400, 'application/json', json.dumps({'error': 'Wybrany model językowy jest niedostępny. Wyłącz LM albo udostępnij jego plik.'}))
            gui_lm_options.save_settings(choice, data['alpha'], data['beta'], data['beam'])
            def worker():
                # jeśli różnice: licz RAW, potem (jeśli LM dostępny) wariant z LM; raport pokaże oba
                cmd=[PY,OCR_BATCH,"--model",model,"--images",lst,"--preview-dir",pdir,"--device",device,"--layout",layout]
                if lm_path:
                    lm_label=next(item['label'] for item in gui_lm_options.choices(find_lm()) if item['id']==choice)
                    cmd+=["--lm",lm_path,"--lm-name",lm_label,"--beam",str(data["beam"]),"--alpha",str(data["alpha"]),"--beta",str(data["beta"])]
                if second_path:
                    second_label=next(item['label'] for item in gui_lm_options.choices(find_lm()) if item['id']==second_choice)
                    cmd += ['--lm-extra',json.dumps({'path':second_path,'name':second_label},ensure_ascii=False)]
                if run_job(job_id,cmd,env,complete=False) != 0:
                    return  # Never report old OCR outputs as success for this failed run.
                # zbuduj interaktywny raport
                out=os.path.join(folder,"_RAPORT_OCR.html")
                try:
                    # buduj raport bezpośrednio (import), nie jako podproces — pewniejsze
                    import importlib, report_gen as _rg
                    importlib.reload(_rg)
                    selected_jsons = [os.path.splitext(item['path'])[0] + '__ocr.json' for item in data['items']]
                    _rg.build_report(folder, out, os.path.basename(model), selected_jsons)
                    STATE["jobs"][job_id]["report"]="/report?path="+urllib.parse.quote(out)
                    STATE["jobs"][job_id]["lines"].append("REPORT_OK\t"+out)
                    # zapisz do rejestru, żeby był dostępny po restarcie serwera
                    try:
                        n_pages = len(selected_jsons)
                        # zapisz TYLKO gdy realnie powstały dane OCR (inaczej śmieciowy, pusty wpis)
                        if n_pages > 0:
                            save_report_entry(folder, os.path.basename(model), n_pages)
                        else:
                            STATE["jobs"][job_id]["lines"].append("REPORT_SKIP\tbrak __ocr.json — raport pusty, nie zapisuję do rejestru")
                    except Exception: pass
                except Exception as e:
                    import traceback
                    message = f"REPORT_ERROR\t{e}\t{traceback.format_exc()}"
                    STATE["jobs"][job_id]["lines"].append(message)
                    STATE["jobs"][job_id]['error'] = str(e)
                    with open(STATE['jobs'][job_id]['log_path'], 'a', encoding='utf-8') as saved:
                        saved.write(message + '\n')
                STATE['jobs'][job_id]['done'] = True
            threading.Thread(target=worker,daemon=True).start()
            return self._send(200,"application/json",json.dumps({"job":job_id}))
        return self._send(404,"application/json",json.dumps({"error":"not found"}))

def main():
    srv=ThreadingHTTPServer(("127.0.0.1",PORT),H)
    print(f"MikolajRej OCR — serwer na http://127.0.0.1:{PORT}  (Ctrl+C aby zatrzymać)")
    if '--open-browser' in sys.argv:
        webbrowser.open(f"http://127.0.0.1:{PORT}")
    srv.serve_forever()

if __name__ == "__main__":
    main()
