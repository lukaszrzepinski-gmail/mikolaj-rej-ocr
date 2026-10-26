"""Static, offline history comparison; no OCR runtime imports."""
import html
import json
from ocr_history import variants_for


def block(document):
    variants = variants_for(document)
    payload = json.dumps(variants, ensure_ascii=False).replace('<', '\\u003c').replace('&', '\\u0026')
    geometry = json.dumps([document.get('rot',0),document.get('width'),document.get('height'),
                           [[line.get('bbox'),line.get('baseline')] for line in document.get('lines',[])]],separators=(',',':'))
    return ('<div class="comparison" data-geometry="'+html.escape(geometry,quote=True)+'"><h3>Historia i porównanie wyników</h3>'
            '<p>Wybierz dwa wyniki tego skanu. Czerwony: tekst wersji A; zielony: tekst wersji B. '
            'Różnica nie oznacza automatycznie błędu.</p>'
            '<label>Wersja A <select class="choose-a"></select></label> '
            '<label>Wersja B <select class="choose-b"></select></label> '
            '<label><input type="checkbox" class="only-changes" checked> Tylko różnice</label>'
            '<p class="compare-info"></p><div class="compare-output"></div>'
            '<script type="application/json" class="variants">' + payload + '</script></div>')


CSS = '''
.comparison{border-top:1px solid #ddd;padding:16px}.comparison h3{margin:0 0 8px}
.comparison p{font-size:12px;color:#555}.comparison select{max-width:100%;padding:7px;margin:5px}
.compare-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;border-top:1px solid #ddd;padding:9px 0}
.compare-text{white-space:pre-wrap;overflow-wrap:anywhere;font-size:14px;line-height:1.7}
.compare-text del{background:#ffe1e1;color:#8b1616;text-decoration:none;border-bottom:2px solid #b42318}
.compare-text ins{background:#d9f6df;color:#14532d;text-decoration:none;border-bottom:2px solid #15803d}
.compare-info{white-space:pre-wrap}.comparison .unchanged{display:none}
.comparison.show-all .unchanged{display:grid}
@media(max-width:650px){.compare-grid{grid-template-columns:1fr}}
'''

JS = r'''
// Compare Unicode code points, preserving original text and escaping through text nodes.
function marked(a,b){
  const A=Array.from(a), B=Array.from(b), left=document.createElement('span'),right=document.createElement('span');
  function add(parent,text,tag){if(!text)return;const e=tag?document.createElement(tag):document.createTextNode(text);if(tag)e.textContent=text;parent.appendChild(e);}
  let lo=0,ea=A.length,eb=B.length;
  while(lo<ea&&lo<eb&&A[lo]===B[lo])lo++;
  while(ea>lo&&eb>lo&&A[ea-1]===B[eb-1]){ea--;eb--;}
  const x=A.slice(lo,ea),y=B.slice(lo,eb);
  add(left,A.slice(0,lo).join(''));add(right,B.slice(0,lo).join(''));
  if(x.length*y.length>250000){add(left,x.join(''),'del');add(right,y.join(''),'ins');}
  else {
    const dp=Array.from({length:x.length+1},()=>new Uint32Array(y.length+1));
    for(let i=x.length-1;i>=0;i--)for(let j=y.length-1;j>=0;j--)dp[i][j]=x[i]===y[j]?1+dp[i+1][j+1]:Math.max(dp[i+1][j],dp[i][j+1]);
    let i=0,j=0,minus='',plus='',same='';
    function flush(){add(left,minus,'del');add(right,plus,'ins');minus='';plus='';}
    function flushSame(){add(left,same);add(right,same);same='';}
    while(i<x.length||j<y.length){
      if(i<x.length&&j<y.length&&x[i]===y[j]){flush();same+=x[i];i++;j++;}
      else {flushSame();if(j>=y.length||(i<x.length&&dp[i+1][j]>=dp[i][j+1]))minus+=x[i++];else plus+=y[j++];}
    }flush();flushSame();
  }
  add(left,A.slice(ea).join(''));add(right,B.slice(eb).join(''));return [left,right];
}
document.querySelectorAll('.comparison').forEach(box=>{
  const variants=JSON.parse(box.querySelector('.variants').textContent),a=box.querySelector('.choose-a'),b=box.querySelector('.choose-b');
  for(const [i,v] of variants.entries())for(const select of [a,b]){const option=document.createElement('option');option.value=i;option.textContent=(v.label||'Model nieznany')+' · '+(v.created_utc||'data nieznana');select.appendChild(option);}
  b.value=Math.max(0,variants.length-1);
  const newest=variants[+b.value];const raw=variants.findIndex(v=>v.run_id&&v.run_id===newest.run_id&&!v.lm);
  a.value=raw>=0&&raw!==+b.value?raw:Math.max(0,+b.value-1);
  function info(v){const p=v.provenance||{},m=p.model||{},lm=p.lm||{};return (v.label||'Model nieznany')+'\nModel SHA256: '+(m.sha256||'brak w starszym wyniku')+'\nLM: '+(v.lm?(lm.name||'nieznany'):'wyłączony')+(v.lm?' · SHA256 '+(lm.sha256||'?')+' · α '+lm.alpha+' · β '+lm.beta+' · beam '+lm.beam:'')+'\nUkład: '+(p.layout||'?')+' · obrót '+(v.rot||0)+'°';}
  function render(){
    const A=variants[+a.value],B=variants[+b.value],out=box.querySelector('.compare-output');out.replaceChildren();
    const ga=v=>JSON.stringify([v.rot||0,v.width,v.height,(v.lines||[]).map(l=>[l.bbox,l.baseline])]);
    const aligned=ga(A)===ga(B)&&(A.lines||[]).every(l=>l.bbox||l.baseline);
    const legacy=[A,B].some(v=>v.scan_identity!=='sha256-verified');
    let rows=aligned?A.lines.map((l,i)=>[l.text||'',B.lines[i].text||'',i]):[[(A.lines||[]).map(l=>l.text||'').join('\n'),(B.lines||[]).map(l=>l.text||'').join('\n'),null]];
    let changes=0;
    for(const [x,y,index] of rows){const row=document.createElement('div');row.className='compare-grid'+(x===y?' unchanged':'');if(x!==y)changes++;
      for(const [k,content] of marked(x,y).entries()){const cell=document.createElement('div');cell.className='compare-text';const label=document.createElement('small');label.textContent=(k?'B':'A')+(index===null?' · cały tekst':' · wiersz '+(index+1))+': ';cell.append(label,content);row.appendChild(cell);}
      if(index!==null&&ga(A)===box.dataset.geometry){row.dataset.k=index;row.onmouseenter=()=>{box.closest('.report').querySelectorAll('.zone[data-k="'+index+'"]').forEach(z=>z.classList.add('hl'));};row.onmouseleave=()=>{box.closest('.report').querySelectorAll('.zone.hl').forEach(z=>z.classList.remove('hl'));};}
      out.appendChild(row);
    }
    box.querySelector('.compare-info').textContent='A: '+info(A)+'\n\nB: '+info(B)+'\n\n'+(aligned?changes+' z '+rows.length+' wierszy różni się.':'Różna lub nieznana segmentacja: porównanie całych tekstów, bez przypisywania wierszy do tych samych miejsc skanu.')+(legacy?'\nUwaga: dla starszego wyniku nie można potwierdzić zgodności skanu na podstawie historycznej sumy kontrolnej.':'');
    if(!changes){const p=document.createElement('p');p.textContent='Teksty są identyczne.';out.prepend(p);}
  }
  a.onchange=b.onchange=render;box.querySelector('.only-changes').onchange=e=>box.classList.toggle('show-all',!e.target.checked);render();
});
'''
