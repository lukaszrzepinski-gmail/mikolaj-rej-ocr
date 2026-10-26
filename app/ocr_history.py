"""Immutable OCR variants, keyed by scan bytes; standard library only."""
import copy
import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.writing-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def root_for(image, digest):
    return Path(image).parent / '_historia_ocr' / digest


def variants_for(document):
    provenance = document.get('provenance', {})
    digest = document.get('scan_sha256')
    image = document['image']
    if not digest:
        digest = sha256(image)
    variants = []
    root = root_for(image, digest)
    for path in sorted(root.glob('*.json')):
        try:
            saved = json.loads(path.read_text(encoding='utf-8'))
            if saved.get('scan_sha256') == digest:
                variants.append(saved)
        except (OSError, ValueError):
            continue
    if document.get('variant_id') not in {v.get('variant_id') for v in variants}:
        current = copy.deepcopy(document)
        current.setdefault('variant_id', 'legacy-current')
        current.setdefault('label', 'Starszy wynik — model nieznany' if not provenance else 'Bieżący wynik')
        variants.append(current)
    return variants


def preserve_legacy(image):
    """Never attribute an overwritten historical sidecar to the new model."""
    sidecar = Path(image).with_name(Path(image).stem + '__ocr.json')
    if not sidecar.exists():
        return
    old = json.loads(sidecar.read_text(encoding='utf-8'))
    if old.get('variant_id'):
        return
    # Historical sidecars have no scan hash: association is explicitly uncertain.
    digest = sha256(image)
    old.update(scan_sha256=digest, scan_identity='legacy-assumed-from-current-path',
               variant_id='legacy-' + sha256(sidecar),
               label='Starszy wynik — model nieznany (zgodność skanu niepotwierdzona)')
    old['created_utc'] = datetime.fromtimestamp(sidecar.stat().st_mtime, timezone.utc).isoformat()
    dest = root_for(image, digest) / (old['variant_id'] + '.json')
    if not dest.exists():
        atomic_json(dest, old)


def save_result(document, provenance, scan_digest):
    image = document['image']
    if sha256(image) != scan_digest:
        raise ValueError('Skan zmienił się podczas OCR — wynik nie zostanie przypisany do historii.')
    preserve_legacy(image)
    run = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + uuid.uuid4().hex[:10]
    base = copy.deepcopy(document)
    base.update(schema_version=2, scan_sha256=scan_digest, scan_identity='sha256-verified',
                created_utc=datetime.now(timezone.utc).isoformat(), provenance=provenance, run_id=run)
    model_name = Path(provenance['model']['path']).name
    variants = []
    raw = copy.deepcopy(base)
    raw.update(lm=False, variant_id=run + '-raw', label=model_name + ' · bez LM')
    if document['lm']:
        raw['provenance']['lm'] = {'enabled':False, 'paired_lm':copy.deepcopy(provenance['lm'])}
    for line in raw['lines']:
        line['text'] = line['raw_text']
    variants.append(raw)
    selected = raw
    if document['lm']:
        selected = copy.deepcopy(base)
        selected.update(variant_id=run + '-lm', label=model_name + ' · ' + provenance['lm']['name'])
        variants.append(selected)
    for variant in variants:
        atomic_json(root_for(image, scan_digest) / (variant['variant_id'] + '.json'), variant)
    atomic_json(Path(image).with_name(Path(image).stem + '__ocr.json'), selected)
    return selected
