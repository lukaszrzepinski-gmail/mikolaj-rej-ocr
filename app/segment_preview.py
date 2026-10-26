"""Cached previews or one network process with bounded CPU geometry workers."""
import argparse
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
import importlib.metadata
import importlib.util
import json
import multiprocessing
from pathlib import Path
import shutil
import tempfile
import time
import traceback
from gui_seg_cache import cache_key, load_preview, save_json, sha
from gui_reading_order import order_lines, redraw_preview, POLICY
from gui_seg_pipeline import GIB, memory, low_priority, device_lease, cpu_init, dump_map, vectorize


def log(*args):
    print(*args, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--images', required=True); ap.add_argument('--preview-dir', required=True)
    ap.add_argument('--device', default='cpu'); ap.add_argument('--seg-maxdim', type=int, default=1500)
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--layout', choices=('auto','single','two'), default='auto')
    ap.add_argument('--cpu-workers', type=int, choices=(1,2,4), default=1)
    args = ap.parse_args(); started = time.perf_counter(); failures = 0
    directory = Path(args.preview_dir); directory.mkdir(parents=True, exist_ok=True)
    entries = []
    for row in Path(args.images).read_text(encoding='utf-8').splitlines():
        if row.strip():
            fields=row.split('\t'); entries.append((fields[0].strip(),int(fields[1]) if len(fields)>1 and fields[1].strip() else 0))
    spec = importlib.util.find_spec('kraken')
    if spec is None or not spec.submodule_search_locations:raise RuntimeError('Brak Krakena')
    model_path = Path(next(iter(spec.submodule_search_locations)))/'blla.mlmodel'
    model_sha = sha(model_path); version = importlib.metadata.version('kraken')
    log(f'TOTAL\t{len(entries)}'); jobs=[]
    for index,(image,rotation) in enumerate(entries,1):
        try:
            t=time.perf_counter(); preview=directory/(Path(image).stem+'__seg.png'); geometry=preview.with_suffix('.json')
            key=cache_key(image,rotation,model_sha,args.seg_maxdim,version)
            cached=None if args.force else load_preview(geometry,key,preview)
            if cached is not None:
                lines=order_lines(cached['lines'],args.layout)
                if lines!=cached['lines']:redraw_preview(image,rotation,lines,preview)
                if lines!=cached['lines'] or cached.get('reading_order_version')!=POLICY or cached.get('layout')!=args.layout:
                    cached.update(lines=lines,reading_order_version=POLICY,layout=args.layout);save_json(geometry,cached)
                log(f'CACHE_HIT\t{Path(image).name}\t{time.perf_counter()-t:.3f}s')
                log(f'SEG\t{index}\t{len(entries)}\t{Path(image).name}\t{len(lines)}\t{preview}\t{time.perf_counter()-t:.1f}')
            else:jobs.append({'index':index,'image':image,'rotation':rotation,'preview':preview,'geometry':geometry,'key':key})
        except Exception:
            failures+=1;traceback.print_exc()
    if jobs:
        available=memory(int(3.5*GIB)); low_priority()
        workers=min(args.cpu_workers,len(jobs))
        # Budget one GiB per CPU worker plus parent reserve; lower concurrency, never guards.
        while workers>1 and available < int(3.5*GIB)+workers*GIB:workers-=1
        memory(int(3.5*GIB)+workers*GIB)
        with device_lease(args.device):
            log(f'INIT\tladuje segmenter na {args.device}; procesy CPU: {workers}')
            t=time.perf_counter()
            import torch
            from PIL import Image
            from kraken import blla
            from kraken.lib import vgsl
            torch.set_num_threads(2);torch.set_float32_matmul_precision('high')
            segmenter=vgsl.TorchVGSLModel.load_model(model_path)
            if segmenter.aux_layers:raise RuntimeError('Ten segmenter wymaga osobnej obsługi modelu kolejności')
            available=memory(int(3.5*GIB))
            while workers>1 and available < int(3.5*GIB)+workers*GIB:workers-=1
            memory(int(3.5*GIB)+workers*GIB)
            log(f'INIT_DONE\t{time.perf_counter()-t:.3f}s')
            log(f'PIPELINE\t1 proces sieci + {workers} procesy geometrii CPU; float32, bez zmiany rozdzielczości')
            with tempfile.TemporaryDirectory(prefix='.seg-map-',dir=directory) as scratch:
                with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn'),initializer=cpu_init) as pool:
                    pending={}
                    def collect(block):
                        nonlocal failures
                        done,_=wait(pending,timeout=0.25 if block else 0,return_when=FIRST_COMPLETED)
                        memory()
                        for future in done:
                            job=pending.pop(future)
                            try:
                                result=future.result()
                                if cache_key(job['image'],job['rotation'],model_sha,args.seg_maxdim,version)!=job['key']:
                                    raise RuntimeError('Obraz zmienił się podczas przetwarzania; wynik nie został zapisany')
                                scale=job['scale']
                                lines=[{key:[[x/scale,y/scale] for x,y in row[key]] for key in ('baseline','boundary')} for row in result['lines']]
                                lines=order_lines(lines,args.layout)
                                redraw_preview(job['image'],job['rotation'],lines,job['preview'])
                                timing={'compute_segmentation_map':job['map_seconds'],'cpu_geometry_seconds':result['cpu_geometry_seconds'],'pipeline_seconds':time.perf_counter()-job['start']}
                                save_json(job['geometry'],{'image':job['image'],'rot':job['rotation'],'lines':lines,'cache_key':job['key'],'reading_order_version':POLICY,'layout':args.layout,'timings':timing,'device':args.device,'cpu_workers':workers})
                                log('TIMING\t'+Path(job['image']).name+'\t'+json.dumps(timing))
                                log(f'SEG\t{job["index"]}\t{len(entries)}\t{Path(job["image"]).name}\t{len(lines)}\t{job["preview"]}\t{timing["pipeline_seconds"]:.1f}')
                            except Exception:
                                failures+=1;traceback.print_exc()
                            finally:shutil.rmtree(job['spool'])
                    for job in jobs:
                        while len(pending)>=workers:collect(True)
                        memory();job['start']=time.perf_counter()
                        log(f'STAGE\t{Path(job["image"]).name}\twykrywanie linii; geometria równolegle na CPU')
                        try:
                            with Image.open(job['image']) as source:im=source.convert('RGB')
                            if job['rotation']:im=im.rotate(-job['rotation'],expand=True)
                            scale=min(1.0,args.seg_maxdim/max(im.size)) if args.seg_maxdim else 1.0
                            if scale!=1:im=im.resize((max(1,int(im.width*scale)),max(1,int(im.height*scale))))
                            t=time.perf_counter();rets=blla.compute_segmentation_map(im,None,segmenter,args.device)
                            job.update(map_seconds=time.perf_counter()-t,scale=scale,spool=Path(scratch)/str(job['index']))
                            dump_map(job['spool'],rets,segmenter,im.size);del rets;im.close()
                            pending[pool.submit(vectorize,str(job['spool']))]=job
                            collect(False)
                        except Exception:
                            failures+=1;traceback.print_exc()
                    while pending:collect(True)
    log(f'DONE\t{time.perf_counter()-started:.3f}s')
    if failures:raise SystemExit(1)


if __name__=='__main__':main()
