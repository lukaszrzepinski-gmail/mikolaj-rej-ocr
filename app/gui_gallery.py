"""Read-only scan history summaries, independent of inference runtime."""
import json
from pathlib import Path
import threading
from ocr_history import sha256, variants_for

_CACHE = {}
_LOCK = threading.Lock()


def scan_sha(path):
    path=Path(path)
    stamp=(str(path.resolve()),path.stat().st_size,path.stat().st_mtime_ns)
    with _LOCK:
        known=_CACHE.get(stamp)
    if known:
        return known
    digest=sha256(path)
    if stamp[1:]!=(path.stat().st_size,path.stat().st_mtime_ns):
        raise ValueError('Skan zmienił się podczas odczytu historii.')
    with _LOCK:
        if len(_CACHE)>=128:
            _CACHE.clear()
        _CACHE[stamp]=digest
    return digest


def image_info(image):
    image=Path(image)
    result={'path':str(image),'processed':False,'model':'Nieprzetworzony','models':[],
            'variant_count':0,'model_count':0,'rotation':0,'lm':'','status':'none'}
    sidecar=image.with_name(image.stem+'__ocr.json')
    if not sidecar.is_file():
        return result
    try:
        current=json.loads(sidecar.read_text(encoding='utf-8'))
        digest=current.get('scan_sha256')
        if digest and scan_sha(image)!=digest:
            result.update(status='changed',model='Skan zmieniony — brak wyniku dla tej wersji')
            return result
        # A renamed scan may still use a copied sidecar: bind the current path only
        # after its byte identity was checked, never invent a historical model.
        current=dict(current,image=str(image))
        variants=variants_for(current)
        models={}
        for variant in variants:
            model=variant.get('provenance',{}).get('model',{})
            name=Path(model['path']).name if model.get('path') else 'Model nieznany (starszy wynik)'
            key=model.get('sha256') or model.get('path') or 'unknown'
            models[key]={'name':name,'path':model.get('path'),'sha256':model.get('sha256')}
        latest_model=current.get('provenance',{}).get('model',{})
        lm=current.get('provenance',{}).get('lm',{})
        result.update(processed=True,status='verified' if digest else 'legacy',
                      model=Path(latest_model['path']).name if latest_model.get('path') else 'Model nieznany (starszy wynik)',
                      model_path=latest_model.get('path'),model_sha256=latest_model.get('sha256'),
                      lm=(lm.get('name') or 'LM nieznany') if current.get('lm') else 'bez LM',
                      models=list(models.values()),model_count=len(models),variant_count=len(variants),
                      rotation=int(current.get('rot',0))%360,created_utc=current.get('created_utc'),
                      uncertain=not bool(digest))
    except (OSError,ValueError,KeyError,TypeError,AttributeError) as error:
        result.update(status='error',model='Nie można odczytać historii',error=str(error))
    return result
