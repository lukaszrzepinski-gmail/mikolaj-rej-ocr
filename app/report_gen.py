#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
report_gen.py — generator nowoczesnego, INTERAKTYWNEGO raportu HTML "skan ↔ tekst".

Czyta <stem>__ocr.json (zapisane przez ocr_batch.py: width/height/rot + lines[{i,text,bbox,baseline}])
i składa jedną stronę: po lewej skan z nakładką klikalnych stref linii, po prawej tekst.
Najechanie na linię (na obrazie LUB w tekście) podświetla ją po obu stronach.

Użycie (z GUI):
  from report_gen import build_report
  build_report(folder, out_html, model_name, ocr_json_paths)

Samodzielnie:
  python report_gen.py --folder FOLDER --out _RAPORT_OCR.html --model "V9"
  (skanuje FOLDER w poszukiwaniu *__ocr.json)
"""
import argparse, os, json, html, glob
import ocr_comparison
from ocr_history import sha256

def _esc(s): return html.escape(s or "")

def _page_block(d):
    """Jeden skan: obraz + nakładka stref linii + kolumna tekstu."""
    img = d["image"]; W = d.get("width") or 1; H = d.get("height") or 1
    uri = html.escape("file:///" + img.replace("\\", "/"), quote=True)
    # Geometry is measured AFTER clockwise rotation in ocr_batch.py. Rotate only
    # the original image here; the overlay already uses the rotated coordinates.
    rotation = int(d.get('rot', 0)) % 360
    if rotation not in (0, 90, 180, 270):
        raise ValueError('Raport obsługuje obrót skanu o wielokrotność 90 stopni.')
    image_width = 100.0 * H / W if rotation in (90, 270) else 100.0
    image_style = (f'position:absolute;left:50%;top:50%;width:{image_width:.8f}%;'
                   f'max-width:none;height:auto;transform:translate(-50%,-50%) rotate({rotation}deg)')
    name = os.path.basename(img)
    lm = d.get("lm")
    rows = []          # tekst po prawej
    zones = []         # strefy na obrazie (procentowo, skalują się z obrazem)
    for ln in d.get("lines", []):
        i = ln["i"]; t = ln.get("text", "")
        bbox = ln.get("bbox")
        if bbox:
            x0, y0, x1, y1 = bbox
            left = 100.0 * x0 / W; top = 100.0 * y0 / H
            wpc = 100.0 * (x1 - x0) / W; hpc = 100.0 * (y1 - y0) / H
            zones.append(
                f'<span class="zone" data-k="{i}" style="left:{left:.2f}%;top:{top:.2f}%;'
                f'width:{wpc:.2f}%;height:{hpc:.2f}%" title="linia {i+1}"></span>')
        rows.append(f'<span class="tl" data-k="{i}"><span class="lnum">{i+1}</span>{_esc(t)}</span>')
    correction_payload = json.dumps({'image': img, 'scan_sha256': d.get('scan_sha256'),
                                     'variant_id': d.get('variant_id'), 'lines': d.get('lines',[])},ensure_ascii=False).replace('<','\\u003c').replace('&','\\u0026')
    badge = '<span class="pill lm">LM</span>' if lm else '<span class="pill raw">RAW</span>'
    return f"""
<section class="report">
  <div class="rhead">
    <span class="name">{_esc(name)}</span>
    {badge}<span class="pill">{len(d.get('lines',[]))} linii</span>
    <span class="spacer"></span>
    <button class="zbtn" data-act="zin">+</button><button class="zbtn" data-act="zout">−</button>
    <button class="zbtn" data-act="zreset">reset</button>
  </div>
  <div class="split">
    <div class="imgwrap"><div class="imgbox" style="aspect-ratio:{W}/{H}">
      <img src="{uri}" alt="{_esc(name)}" data-ocr-rotation="{rotation}" style="{image_style}">
      <div class="zones">{''.join(zones)}</div>
    </div></div>
    <div class="txtcol">{'<br>'.join(rows)}</div>
  </div>
<div class="rerun" data-image="{_esc(img)}" data-rot="{rotation}" data-layout="{_esc(d.get('provenance',{}).get('layout','auto'))}">
  <label>Model <select class="rr-model"></select></label>
  <label><input type="checkbox" class="rr-archive"> Pokaż modele archiwalne</label>
  <label>LM <select class="rr-lm"></select></label>
  <label>Drugi LM <select class="rr-second"><option value="">Nie używaj</option></select></label>
  <label>Urządzenie <select class="rr-device"><option value="cpu">CPU</option><option value="cuda:0">GPU</option></select></label>
  <button class="rr-run" disabled>Przetwórz ten skan i porównaj</button>
  <span class="rr-status" role="status"></span>
</div>
<div class="line-editor" hidden>
  <strong class="line-title"></strong>
  <label>Pełny poprawiony zapis wiersza<textarea class="line-text" rows="3"></textarea></label>
  <button class="line-save">Zapisz próbkę do douczenia</button> <button class="line-cancel">Anuluj</button>
  <p class="line-status" role="status"></p>
</div>
<script type="application/json" class="correction-source">{correction_payload}</script>
{ocr_comparison.block(d)}
</section>"""

CSS = """
.line-editor{padding:16px;border-top:1px solid #ddd;background:#f8f4ff}.line-editor[hidden]{display:none}.line-editor label{display:block;margin:12px 0}.line-text{display:block;width:100%;font:inherit;padding:10px}.line-status{white-space:pre-wrap}.tl.corrected{border-bottom:2px solid #16a34a}.tl{white-space:pre-wrap}

.rerun{padding:14px;display:flex;gap:10px;flex-wrap:wrap;border-top:1px solid #ddd}.rerun select{max-width:300px}.rr-status{width:100%}
:root{--bg:#faf9fc;--card:#fff;--ink:#1a1a1a;--mut:#9ca3af;--sec:#5e5e5e;--line:rgba(0,0,0,.08);
 --pri:#9333ea;--pri2:#a855f7;--prib:#f3e8ff;--ok:#16a34a;--okb:rgba(34,197,94,.12);--rad:12px;--sh:0 4px 12px rgba(0,0,0,.08);}
*{box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--ink);margin:0;padding:22px}
.wrap{max-width:1100px;margin:0 auto}
.apphead{display:flex;align-items:center;gap:13px;background:var(--card);border:1px solid var(--line);
 border-radius:16px;padding:14px 18px;box-shadow:var(--sh);margin-bottom:18px}
.logo{width:40px;height:40px;border-radius:11px;background:linear-gradient(135deg,var(--pri),var(--pri2));
 display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700}
.apphead h1{font-size:16px;margin:0}.apphead .sub{font-size:12px;color:var(--mut);margin-top:2px}
.report{background:var(--card);border:1px solid var(--line);border-radius:var(--rad);overflow:hidden;box-shadow:var(--sh);margin-bottom:20px}
.rhead{display:flex;align-items:center;gap:9px;padding:11px 15px;border-bottom:1px solid var(--line)}
.rhead .name{font-weight:600;font-size:13.5px}.spacer{flex:1}
.pill{font-size:11px;padding:3px 10px;border-radius:17px;background:#eef;color:var(--sec);font-weight:600}
.pill.lm{background:var(--prib);color:var(--pri)}.pill.raw{background:var(--okb);color:var(--ok)}
.zbtn{border:1px solid var(--line);background:var(--card);border-radius:7px;width:28px;height:26px;cursor:pointer;font-size:14px}
.zbtn:hover{background:#f3f4f6}
.split{display:grid;grid-template-columns:1fr 1fr}
.imgwrap{background:#f4ecec;padding:12px;overflow:auto;max-height:640px}
.imgbox{position:relative;width:100%;transform-origin:top left;transition:transform .12s}
.imgbox img{width:100%;display:block;border-radius:5px}
.zones{position:absolute;inset:0}
.zone{position:absolute;border-radius:3px;cursor:pointer;background:transparent;transition:background .12s,box-shadow .12s}
.zone:hover,.zone.hl{background:rgba(147,51,234,.22);box-shadow:0 0 0 2px var(--pri) inset}
.txtcol{padding:14px 16px;font-size:13.5px;line-height:1.5;max-height:640px;overflow:auto}
.tl{display:inline;padding:2px 5px;border-radius:5px;cursor:pointer;transition:background .12s}
.tl:hover,.tl.hl{background:var(--prib)}
.lnum{display:inline-block;min-width:22px;color:var(--mut);font-size:10.5px;margin-right:5px;font-variant-numeric:tabular-nums}
.hint{font-size:12px;color:var(--mut);margin:0 0 14px}
"""

JS = """
document.querySelectorAll('.rerun').forEach(async panel=>{
 const q=s=>panel.querySelector(s), status=q('.rr-status');
 if(location.protocol==='file:'){status.textContent='Aby przetworzyć skan, otwórz raport w aplikacji.';return;}
 try{
  const data=await (await fetch('/api/models')).json();
  for(const m of data.models){const o=document.createElement('option');o.value=m.path;o.textContent=m.label;o.disabled=m.usable===false;q('.rr-model').appendChild(o);}
  q('.rr-archive').onchange=async()=>{
   try{const prior=q('.rr-model').value, result=await(await fetch('/api/models?archive='+(q('.rr-archive').checked?'1':'0'))).json();q('.rr-model').replaceChildren();
    for(const m of result.models){const o=document.createElement('option');o.value=m.path;o.textContent=m.label;o.disabled=m.usable===false;q('.rr-model').appendChild(o);}
    const options=Array.from(q('.rr-model').options);q('.rr-model').value=options.find(o=>o.value===prior&&!o.disabled)?.value||options.find(o=>!o.disabled)?.value||'';q('.rr-run').disabled=!q('.rr-model').value;
   }catch(error){status.textContent=String(error);}
  };
  const usable=Array.from(q('.rr-model').options).find(o=>!o.disabled);if(usable)q('.rr-model').value=usable.value;
  for(const m of data.lm_choices){const o=document.createElement('option');o.value=m.id;o.textContent=m.label;o.disabled=!m.available;q('.rr-lm').appendChild(o);if(m.id!=='none')q('.rr-second').appendChild(o.cloneNode(true));}
  q('.rr-run').disabled=!usable;
  q('.rr-run').onclick=async()=>{
   q('.rr-run').disabled=true;status.textContent='Przetwarzanie…';
   try{
    const image=panel.dataset.image, choice=q('.rr-lm').value;
    const payload={folder:image.replace(/[\\/][^\\/]+$/, ''),items:[{path:image,rot:+panel.dataset.rot}],layout:panel.dataset.layout,model_path:q('.rr-model').value,
     lm:choice!=='none',lm_choice:choice,lm_second:q('.rr-second').value,alpha:0.5,beta:choice==='korba'?0:1,beam:64,device:q('.rr-device').value};
    const reply=await (await fetch('/api/ocr',{method:'POST',body:JSON.stringify(payload)})).json();if(reply.error)throw Error(reply.error);
    const timer=setInterval(async()=>{try{
     const job=await (await fetch('/api/job?id='+encodeURIComponent(reply.job))).json();
     status.textContent=(job.lines||[]).slice(-1)[0]||'Przetwarzanie…';
     if(job.done){clearInterval(timer);q('.rr-run').disabled=false;if(job.error)status.textContent=job.error;else if(job.report)location.href=job.report;}
    }catch(e){clearInterval(timer);q('.rr-run').disabled=false;status.textContent=String(e);}},1000);
   }catch(e){q('.rr-run').disabled=false;status.textContent=String(e);}
  };
 }catch(e){status.textContent='Nie można połączyć z aplikacją: '+e;}
});
document.querySelectorAll('.report').forEach(rep=>{
 const payload=rep.querySelector('.correction-source');if(!payload)return;
 const data=JSON.parse(payload.textContent), editor=rep.querySelector('.line-editor'),text=editor.querySelector('.line-text'), status=editor.querySelector('.line-status'),save=editor.querySelector('.line-save');
 const saved=new Map();let active=null;
 if(location.protocol!=='file:'&&data.scan_sha256&&data.variant_id){
  fetch('/api/line-corrections?path='+encodeURIComponent(data.image)+'&sha='+encodeURIComponent(data.scan_sha256)+'&variant='+encodeURIComponent(data.variant_id)).then(r=>r.json()).then(result=>{
   for(const row of result.samples||[]){saved.set(row.line_id,row.corrected_text);const el=rep.querySelector('.tl[data-k="'+row.line_id+'"]');if(el){el.classList.add('corrected');el.title='Zapisano poprawkę do douczenia';}}
  }).catch(()=>{});
 }
 rep.querySelectorAll('.zone,.tl').forEach(el=>el.addEventListener('click',()=>{
  active=data.lines.find(row=>String(row.i)===el.dataset.k);if(!active)return;
  editor.hidden=false;editor.querySelector('.line-title').textContent='Popraw zapis — wiersz '+(active.i+1);
  text.value=saved.has(active.i)?saved.get(active.i):active.text;status.textContent='Zapisz cały wiersz zgodnie ze skanem. Powstanie obraz wiersza i poprawiony tekst do douczenia.';
  save.disabled=location.protocol==='file:'||!data.variant_id||!data.scan_sha256;
  if(save.disabled)status.textContent='Otwórz aktualny raport w aplikacji, aby zapisać poprawkę.';
  editor.scrollIntoView({block:'nearest',behavior:'smooth'});text.focus();
 }));
 editor.querySelector('.line-cancel').onclick=()=>{editor.hidden=true;};
 save.onclick=async()=>{
  if(!active)return;const line=active,corrected=text.value;save.disabled=true;
  try{
   const reply=await (await fetch('/api/line-correction',{method:'POST',body:JSON.stringify({image:data.image,scan_sha256:data.scan_sha256,variant_id:data.variant_id,line_id:line.i,text:corrected})})).json();
   if(reply.error)throw Error(reply.error);saved.set(line.i,corrected);
   const el=rep.querySelector('.tl[data-k="'+line.i+'"]');if(el){el.classList.add('corrected');el.title='Zapisano poprawkę do douczenia';}
   status.textContent='Zapisano cały wiersz jako próbkę do douczenia.'+String.fromCharCode(10)+reply.sample_path;
  }catch(error){status.textContent=String(error);}finally{save.disabled=false;}
 };
});
function setHL(el,on){el.closest('.report').querySelectorAll('[data-k="'+el.dataset.k+'"]').forEach(e=>e.classList.toggle('hl',on));}
document.querySelectorAll('.zone,.tl').forEach(e=>{
  e.addEventListener('mouseenter',()=>setHL(e,true));
  e.addEventListener('mouseleave',()=>setHL(e,false));
  e.addEventListener('click',()=>{ // klik w linię na obrazie przewija tekst do niej
    const tl=e.closest('.report').querySelector('.tl[data-k="'+e.dataset.k+'"]'); if(tl) tl.scrollIntoView({block:'center',behavior:'smooth'});
  });
});
// zoom per-raport
document.querySelectorAll('.report').forEach(rep=>{
  const box=rep.querySelector('.imgbox'); let s=1;
  rep.querySelectorAll('.zbtn').forEach(b=>b.addEventListener('click',()=>{
    const a=b.dataset.act; if(a==='zin')s=Math.min(4,s+0.25); else if(a==='zout')s=Math.max(0.5,s-0.25); else s=1;
    box.style.transform='scale('+s+')';
  }));
});
"""

def build_report(folder, out_html, model_name, ocr_json_paths=None):
    if ocr_json_paths is None:
        ocr_json_paths = sorted(glob.glob(os.path.join(folder, "*__ocr.json")))
    blocks = []
    for p in ocr_json_paths:
        try:
            d = json.load(open(p, encoding="utf-8"))
            if d.get('scan_sha256') and sha256(d['image']) != d['scan_sha256']:
                raise ValueError('Plik skanu zmienił się od OCR. Przetwórz nowy skan; wcześniejsza historia pozostaje zachowana.')
            blocks.append(_page_block(d))
        except Exception as e:
            blocks.append(f'<section class="report"><div class="rhead">'
                          f'<span class="name">{_esc(os.path.basename(p))}</span>'
                          f'<span class="pill raw">błąd: {_esc(str(e)[:80])}</span></div></section>')
    doc = f"""<!doctype html><html lang="pl"><head><meta charset="utf-8">
<title>MikolajRej OCR — raport</title><style>{CSS}{ocr_comparison.CSS}</style></head><body>
<div class="wrap">
  <div class="apphead"><div class="logo">MR</div>
    <div><h1>MikolajRej OCR — raport</h1>
    <div class="sub">Model: {_esc(model_name)} · {len(blocks)} stron · najedź na linię, aby podświetlić</div></div>
  </div>
  <p class="hint">Interaktywnie: najedź na wiersz na skanie lub w tekście — podświetli się po obu stronach. Klik na skanie przewija do tekstu. +/− zmienia powiększenie.</p>
  {''.join(blocks)}
</div>
<script>{JS}\n{ocr_comparison.JS}</script>
</body></html>"""
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(doc)
    return out_html

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", required=True)
    ap.add_argument("--out", default="_RAPORT_OCR.html")
    ap.add_argument("--model", default="?")
    a = ap.parse_args()
    out = a.out if os.path.isabs(a.out) else os.path.join(a.folder, a.out)
    p = build_report(a.folder, out, a.model)
    print("OK:", p)

if __name__ == "__main__":
    main()
