"""Human line corrections as immutable PNG/GT pairs, never auto-added to training."""
import json,math,os,shutil,tempfile,uuid
from datetime import datetime,timezone
from pathlib import Path
from ocr_history import sha256,atomic_json,variants_for


def correction_root(image):
    return Path(image).parent / '_probki_poprawkowe'


def saved_corrections(image,digest,variant):
    if sha256(image)!=digest:
        raise ValueError('Skan zmienił się od otwarcia raportu. Otwórz aktualny raport.')
    found=[]
    for path in sorted((correction_root(image)/digest).glob('*/*/sample.json')):
        try:
            value=json.loads(path.read_text(encoding='utf-8'))
            if value['source_variant_id']==variant:found.append(value)
        except (OSError,ValueError,KeyError):continue
    return sorted(found,key=lambda row:row['created_utc'])


def save_correction(data):
    image=Path(data['image']).resolve()
    digest=data['scan_sha256'];variant=data['variant_id'];index=data['line_id'];text=data['text']
    if not isinstance(text,str) or not text.strip() or len(text)>20000 or any(c in text for c in ('\r','\n','\0')):
        raise ValueError('Podaj pełny zapis jednego wiersza (bez pustych i dodatkowych wierszy).')
    if not isinstance(index,int) or isinstance(index,bool):raise ValueError('Niepoprawny numer wiersza.')
    if sha256(image)!=digest:raise ValueError('Skan zmienił się od otwarcia raportu. Otwórz aktualny raport.')
    sidecar=image.with_name(image.stem+'__ocr.json')
    current=json.loads(sidecar.read_text(encoding='utf-8'))
    docs=variants_for(dict(current,image=str(image),scan_sha256=digest))
    document=next((d for d in docs if d.get('variant_id')==variant and d.get('scan_sha256')==digest),None)
    if document is None:raise ValueError('Nie znaleziono źródłowego wyniku OCR. Odśwież raport.')
    line=next((row for row in document['lines'] if row.get('i')==index),None)
    if line is None or not line.get('bbox'):raise ValueError('Wiersz nie ma zapisanej geometrii.')
    rotation=int(document.get('rot',0))%360
    if rotation not in (0,90,180,270):raise ValueError('Nieobsługiwany obrót.')
    bbox=line['bbox']
    if len(bbox)!=4 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in bbox):raise ValueError('Niepoprawna geometria.')
    from PIL import Image
    with Image.open(image) as source:
        source=source.convert('RGB')
        if rotation:source=source.rotate(-rotation,expand=True)
        if source.size!=(document.get('width'),document.get('height')):raise ValueError('Wymiary skanu nie zgadzają się z segmentacją.')
        w,h=source.size
        box=(max(0,math.floor(bbox[0])),max(0,math.floor(bbox[1])),min(w,math.ceil(bbox[2])),min(h,math.ceil(bbox[3])))
        if box[2]<=box[0] or box[3]<=box[1]:raise ValueError('Wiersz leży poza obrazem.')
        crop=source.crop(box)
    parent=correction_root(image)/digest/('line-'+str(index))
    parent.mkdir(parents=True,exist_ok=True)
    ident=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex[:10]
    staging=Path(tempfile.mkdtemp(prefix='.saving-',dir=parent));destination=parent/ident
    try:
        crop.save(staging/'line.png')
        with (staging/'line.png').open('r+b') as f:os.fsync(f.fileno())
        with (staging/'line.gt.txt').open('w',encoding='utf-8',newline='\n') as f:
            f.write(text+'\n');f.flush();os.fsync(f.fileno())
        metadata={'schema':'human-corrected-line-v1','sample_id':ident,'created_utc':datetime.now(timezone.utc).isoformat(),
                  'status':'ready_for_training_review','human_corrected':True,'source_image':str(image),'scan_sha256':digest,
                  'source_variant_id':variant,'source_provenance':document.get('provenance',{}),'line_id':index,
                  'original_text':line.get('text',''),'original_raw_text':line.get('raw_text',''),
                  'corrected_text':text,'rotation':rotation,'source_dimensions':[w,h],
                  'bbox':bbox,'baseline':line.get('baseline'),'boundary':line.get('boundary'),
                  'crop_box':box,'crop_size':list(crop.size),'image':'line.png','ground_truth':'line.gt.txt',
                  'image_sha256':sha256(staging/'line.png'),'ground_truth_sha256':sha256(staging/'line.gt.txt'),
                  'training_included':False}
        atomic_json(staging/'sample.json',metadata)
        assert sha256(staging/'line.png')==metadata['image_sha256']
        assert sha256(staging/'line.gt.txt')==metadata['ground_truth_sha256']
        if sha256(image)!=digest:raise ValueError('Skan zmienił się podczas zapisu próbki.')
        os.rename(staging,destination)
    finally:
        crop.close()
        if staging.exists():shutil.rmtree(staging)
    return {'saved':True,'sample_id':ident,'sample_path':str(destination),'line_id':index,'text':text}
