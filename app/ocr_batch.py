#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ocr_batch.py — wsadowe OCR w JEDNEJ sesji (model + CUDA ładowane raz).

Wejście --images: każda linia to  <ścieżka_obrazu>\t<rotacja>  (rotacja opcjonalna, 0 gdy brak).
Jeśli w --preview-dir jest <stem>__seg.json, używa gotowej segmentacji (i zapisanego w niej obrotu).
Opcjonalny LM (KenLM) z alpha/beta/beam.

Postęp: PROGRESS\t<i>\t<total>\t<nazwa>\t<ok|err>\t<chars>\t<sekundy>[\t<blad>]
"""
import argparse, os, sys, json, time, unicodedata, math
from pathlib import Path
for _thread_env in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[_thread_env] = '2'
import numpy as np

SP = "\u2581"
def log(*a): print(*a, flush=True)

def lm_krok(lm, st, s, alpha, beta, LN10):
    import kenlm
    if lm is None or alpha == 0:
        return st, beta * len(s)
    sc = 0.0; cur = st
    for ch in unicodedata.normalize("NFD", s):
        tok = SP if ch == " " else ch
        nst = kenlm.State(); sc += lm.BaseScore(cur, tok, nst) * LN10; cur = nst
    return cur, alpha * sc + beta * len(s)

def beam_lm(probs, alfabet, lm, alpha, beta, beam, prog=1e-3):
    from collections import defaultdict
    import kenlm
    T = probs.shape[1]; LN10 = math.log(10)
    start = kenlm.State(); lm.BeginSentenceWrite(start)
    beams = {(): (0.0, -math.inf, start, 0.0)}
    lse = lambda a, b: a if b == -math.inf else (b if a == -math.inf else max(a, b) + math.log1p(math.exp(-abs(a - b))))
    lp = np.log(np.clip(probs.astype(np.float32), 1e-12, 1))
    for t in range(T):
        kol = lp[:, t]; kand = [c for c in np.nonzero(kol > math.log(prog))[0]]
        nowe = defaultdict(lambda: [-math.inf, -math.inf, None, 0.0])
        for pref, (pb, pnb, st, lms) in beams.items():
            ptot = lse(pb, pnb)
            for c in kand:
                p = kol[c]
                if c == 0:
                    n = nowe[pref]; n[0] = lse(n[0], ptot + p); n[2] = st; n[3] = lms; continue
                last = pref[-1] if pref else None; npref = pref + (c,)
                if c == last:
                    n = nowe[pref]; n[1] = lse(n[1], pnb + p); n[2] = st; n[3] = lms
                    n2 = nowe[npref]
                    if n2[2] is None:
                        s2, sc = lm_krok(lm, st, alfabet.get(c, ""), alpha, beta, LN10); n2[2] = s2; n2[3] = lms + sc
                    n2[1] = lse(n2[1], pb + p)
                else:
                    n2 = nowe[npref]
                    if n2[2] is None:
                        s2, sc = lm_krok(lm, st, alfabet.get(c, ""), alpha, beta, LN10); n2[2] = s2; n2[3] = lms + sc
                    n2[1] = lse(n2[1], ptot + p)
        beams = dict(sorted(((k, tuple(v)) for k, v in nowe.items()),
                            key=lambda kv: -(lse(kv[1][0], kv[1][1]) + kv[1][3]))[:beam])
    best = max(beams.items(), key=lambda kv: lse(kv[1][0], kv[1][1]) + kv[1][3])[0]
    return "".join(alfabet.get(c, "") for c in best)

def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--images", required=True)
    ap.add_argument("--preview-dir", default="")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--no-segmentation", action="store_true")
    ap.add_argument("--lm", default="")
    ap.add_argument("--lm-extra", default="", help="JSON: second LM path/name")
    ap.add_argument('--lm-name', default='')
    ap.add_argument("--beam", type=int, default=64)
    ap.add_argument("--alpha", type=float, default=0.5)
    ap.add_argument("--beta", type=float, default=1.0)
    ap.add_argument('--layout', choices=('auto','single','two'), default='auto')
    a = ap.parse_args()

    from ocr_history import sha256, save_result
    provenance = {'engine': 'Kraken', 'model': {'path': os.path.abspath(a.model), 'sha256': sha256(a.model)},
                  'layout': a.layout, 'lm': {'enabled': bool(a.lm)}}
    if a.lm:
        import importlib.util
        if importlib.util.find_spec('kenlm') is None:
            raise ValueError('Brak KenLM w środowisku OCR. Nie zainstalowano nic automatycznie; wyłącz LM lub przygotuj środowisko.')
        if not (1 <= a.beam <= 128 and math.isfinite(a.alpha) and 0 <= a.alpha <= 2 and
                math.isfinite(a.beta) and 0 <= a.beta <= 3):
            raise ValueError('Niepoprawne parametry LM: alpha 0–2, beta 0–3, beam 1–128.')
        if not os.path.isfile(a.lm):
            raise ValueError('Wybrany model językowy jest niedostępny.')
        provenance['lm'].update(name=a.lm_name or Path(a.lm).stem, path=os.path.abspath(a.lm), sha256=sha256(a.lm),
                                alpha=a.alpha, beta=a.beta, beam=a.beam, cutoff=1e-3)

    from gui_model_check import check_model
    validation = check_model(a.model)
    if not validation['ok']:
        raise ValueError(validation['error'])
    import torch
    torch.set_num_threads(2)
    try: torch.set_float32_matmul_precision("high")
    except Exception: pass
    from PIL import Image
    from kraken.lib import models, vgsl
    from kraken import rpred, blla
    from kraken.containers import Segmentation, BaselineLine
    import kraken

    t0 = time.time(); log(f"INIT\tladuje model na {a.device}")
    rec = models.load_any(a.model, device=a.device)
    provenance['acoustic_temperature'] = getattr(rec, 'temperature', None)
    provenance['raw_decoder'] = 'Kraken native rpred, preserved unchanged'
    alfabet = {labels[0]: c for c, labels in rec.codec.c2l.items() if len(labels) == 1}
    lm = None
    if a.lm:
        import kenlm
        from gui_lm_options import decoder, codec_alphabet, validate_probabilities
        decode = decoder(np)
        alfabet = codec_alphabet(rec.codec)
        lm = kenlm.Model(a.lm)
        provenance['lm']['decoder_AST_sha256'] = __import__('gui_lm_options').AST_SHA
    import copy
    lm_variants = [(lm, copy.deepcopy(provenance))]
    if a.lm_extra:
        if lm is None:
            raise ValueError('Drugi LM wymaga pierwszego LM.')
        extra = json.loads(a.lm_extra)
        if not os.path.isfile(extra['path']):
            raise ValueError('Drugi LM jest niedostępny.')
        other = copy.deepcopy(provenance)
        other['lm'].update(path=os.path.abspath(extra['path']), name=extra['name'], sha256=sha256(extra['path']))
        lm_variants.append((kenlm.Model(extra['path']), other))
    segmenter = None
    # Load the segmentation model only if an image lacks usable preview geometry.
    from gui_seg_cache import load_for_ocr
    from gui_reading_order import order_lines
    log(f"INIT_DONE\t{time.time()-t0:.1f}s")

    entries = []
    for l in Path(a.images).read_text(encoding="utf-8").splitlines():
        if not l.strip(): continue
        parts = l.split("\t"); img = parts[0].strip()
        rot = int(parts[1]) if len(parts) > 1 and parts[1].strip() else 0
        entries.append((img, rot))
    total = len(entries); log(f"TOTAL\t{total}")

    failures = 0
    for i, (img, rot) in enumerate(entries, 1):
        out_txt = os.path.splitext(img)[0] + ".txt"; name = os.path.basename(img); ts = time.time()
        try:
            from gui_seg_pipeline import memory
            memory()
            scan_digest = sha256(img)
            im = Image.open(img).convert("RGB")
            if rot: im = im.rotate(-rot, expand=True)
            seg = None
            if not a.no_segmentation:
                sj = os.path.join(a.preview_dir or str(Path(img).parent / "_podglad_segmentacji"), Path(img).stem + "__seg.json")
                d = load_for_ocr(sj, img, rot)
                if d is not None:
                    log(f"SEG_CACHE\t{name}\tuzywam gotowych linii")
                    w, h = im.size
                    lines = []
                    for k, ln in enumerate(order_lines(d.get("lines", []), a.layout)):
                        bl = [tuple(p) for p in ln["baseline"]]
                        bd = [tuple(p) for p in ln.get("boundary", [])] or [(1,1),(w-2,1),(w-2,h-2),(1,h-2)]
                        lines.append(BaselineLine(id=f"l{k}", baseline=bl, boundary=bd))
                    if lines:
                        seg = Segmentation(type="baselines", imagename="x", text_direction="horizontal-lr",
                                           script_detection=False, lines=lines)
            if seg is None:
                w, h = im.size
                if a.no_segmentation:
                    seg = Segmentation(type="baselines", imagename="x", text_direction="horizontal-lr",
                          script_detection=False,
                          lines=[BaselineLine(id="l", baseline=[(1,int(h*.72)),(w-2,int(h*.72))],
                                 boundary=[(1,1),(w-2,1),(w-2,h-2),(1,h-2)])])
                else:
                    if segmenter is None:
                        log('INIT_SEG\tladuje segmenter: brak aktualnego podgladu')
                        segmenter = vgsl.TorchVGSLModel.load_model(os.path.join(os.path.dirname(kraken.__file__), 'blla.mlmodel'))
                    seg = blla.segment(im, model=segmenter, device=a.device)
                    records = [{"baseline": line.baseline, "boundary": line.boundary, "line": line} for line in seg.lines]
                    seg.lines = [record["line"] for record in order_lines(records, a.layout)]

            if not a.no_segmentation:
                from gui_seg_cache import persist_for_ocr
                if sha256(img) != scan_digest:
                    raise ValueError('Skan zmienił się podczas segmentacji — geometria nie została zapisana.')
                directory = a.preview_dir or str(Path(img).parent / '_podglad_segmentacji')
                cache_path = Path(directory) / (Path(img).stem + '__seg.json')
                if load_for_ocr(cache_path, img, rot) is None:
                    persist_for_ocr(cache_path, img, rot, [
                        {'baseline': [[float(x),float(y)] for x,y in line.baseline],
                         'boundary': [[float(x),float(y)] for x,y in (line.boundary or [])]}
                        for line in seg.lines])
            variant_geometries = [[] for _ in lm_variants]
            lines_out = []
            geo = []   # geometria per-linia do interaktywnego raportu
            seg_lines = list(seg.lines)
            for idx, r in enumerate(rpred.rpred(rec, im, seg)):
                if lm is not None:
                    validate_probabilities(np, rec.outputs[0], alfabet)
                hyp = decode(rec.outputs[0], alfabet, lm, a.alpha, a.beta, a.beam) if lm is not None else r.prediction
                lines_out.append(hyp)
                # bbox z boundary tej linii (jeśli jest), inaczej z baseline
                try:
                    ln = seg_lines[idx]
                    pts = list(ln.boundary) if getattr(ln, "boundary", None) else list(ln.baseline)
                    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
                    bbox = [float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))]
                    baseline = [[float(x), float(y)] for x, y in ln.baseline]
                except Exception:
                    bbox = None; baseline = None
                geo.append({"i": idx, "text": hyp, "raw_text": r.prediction, "bbox": bbox, "baseline": baseline, "boundary": [[float(x),float(y)] for x,y in seg_lines[idx].boundary] if idx < len(seg_lines) and seg_lines[idx].boundary else None})
                for variant_index, (selected_lm, _) in enumerate(lm_variants):
                    selected_text = hyp if variant_index == 0 else decode(rec.outputs[0], alfabet, selected_lm, a.alpha, a.beta, a.beam)
                    variant_geometries[variant_index].append(dict(geo[-1], text=selected_text))
            text = "\n".join(lines_out) + "\n"
            # zapis geometrii + rozmiaru obrazu (po obrocie) do interaktywnego raportu
            ow, oh = im.size
            for variant_index, (selected_lm, selected_provenance) in enumerate(lm_variants):
                save_result({"image": img, "rot": rot, "width": ow, "height": oh,
                             "lm": selected_lm is not None, "lines": variant_geometries[variant_index]}, selected_provenance, scan_digest)
            text = "\n".join(row['text'] for row in variant_geometries[-1]) + "\n"
            Path(out_txt).write_text(text, encoding="utf-8")
            log(f"PROGRESS\t{i}\t{total}\t{name}\tok\t{len(text)}\t{time.time()-ts:.1f}")
        except Exception as e:
            failures += 1
            import traceback
            traceback.print_exc()
            log(f"PROGRESS\t{i}\t{total}\t{name}\terr\t0\t{time.time()-ts:.1f}\t{str(e)[:200]}")
    log(f"DONE\t{total}\t{time.time()-t0:.1f}s")
    if failures:
        raise SystemExit(1)

def main():
    from gui_seg_pipeline import device_lease, memory, low_priority, GIB
    device = sys.argv[sys.argv.index('--device')+1] if '--device' in sys.argv else 'cpu'
    with device_lease(device):
        low_priority()
        memory(int(3.5 * GIB))
        _main()


if __name__ == "__main__":
    main()
