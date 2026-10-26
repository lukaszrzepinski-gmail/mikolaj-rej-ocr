"""Fingerprint preview geometry and images; no ML imports or GPU allocations."""
import hashlib
import json
import os
from pathlib import Path

PIPELINE = 'kraken-blla-preview-v2-original-geometry'


def sha(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def image_key(image, rotation):
    return {'path': os.path.normcase(os.path.realpath(image)),
            'sha256': sha(image), 'rotation': int(rotation) % 360}


def cache_key(image, rotation, model_sha, maxdim, kraken_version):
    return {'pipeline': PIPELINE, 'image': image_key(image, rotation),
            'segmenter_sha256': model_sha, 'maxdim': int(maxdim),
            'kraken_version': kraken_version}


def load_preview(path, expected, preview=None):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8'))
        if value.get('cache_key') != expected or not isinstance(value.get('lines'), list):
            return None
        if preview is not None and not Path(preview).is_file():
            return None
        return value
    except (OSError, ValueError, TypeError):
        return None


def load_for_ocr(path, image, rotation):
    """Accept new fingerprinted previews; preserve compatible legacy user previews.

    Legacy lacks hashes: require matching path, rotation and image not newer than
    geometry. New previews check content hashes and don't override user rotation.
    """
    try:
        path = Path(path)
        value = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(value.get('lines'), list):
            return None
        if int(value.get('rot', 0)) % 360 != int(rotation) % 360:
            return None
        expected = image_key(image, rotation)
        if 'cache_key' in value:
            return value if value['cache_key'].get('image') == expected else None
        if os.path.normcase(os.path.realpath(value.get('image', ''))) != expected['path']:
            return None
        return value if Path(image).stat().st_mtime_ns <= path.stat().st_mtime_ns else None
    except (OSError, ValueError, TypeError):
        return None


def persist_for_ocr(path, image, rotation, lines):
    value = {'image': str(image), 'rot': int(rotation) % 360,
             'lines': lines, 'cache_key': {'image': image_key(image, rotation)},
             'source': 'OCR saved segmentation, original rotated coordinates'}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    save_json(path, value)
    return value


def save_json(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + '.tmp-' + str(os.getpid()))
    try:
        with temp.open('w', encoding='utf-8') as target:
            json.dump(value, target, ensure_ascii=False)
            target.flush(); os.fsync(target.fileno())
        temp.replace(path)
    finally:
        if temp.exists():
            temp.unlink()
