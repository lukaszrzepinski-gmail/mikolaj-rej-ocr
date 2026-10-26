"""Read CoreML metadata without importing Torch, Kraken or allocating GPU memory.

This checks metadata only, not weight integrity or OCR quality.
CoreML Model.description(2).metadata(100).userDefined(100).
"""
import json
from pathlib import Path


def _varint(stream):
    value = 0
    for shift in range(0, 70, 7):
        b = stream.read(1)
        if not b:
            raise ValueError('Niekompletny plik modelu')
        value |= (b[0] & 127) << shift
        if not b[0] & 128:
            return value
    raise ValueError('Niepoprawny format modelu')


def _fields(stream, end):
    while stream.tell() < end:
        tag = _varint(stream)
        number, wire = tag >> 3, tag & 7
        if not number:
            raise ValueError('Niepoprawne pole modelu')
        if wire == 0:
            _varint(stream)
            continue
        size = _varint(stream) if wire == 2 else {1: 8, 5: 4}.get(wire)
        if size is None or stream.tell() + size > end:
            raise ValueError('Niepoprawna dlugosc pola modelu')
        start = stream.tell()
        yield number, wire, start, size
        stream.seek(start + size)


def _message(stream, end, wanted):
    for number, wire, start, size in _fields(stream, end):
        if number == wanted and wire == 2:
            return start + size
    raise ValueError('Brak metadanych modelu Kraken')


def model_metadata(path):
    import io
    path = Path(path)
    with path.open('rb') as stream:
        end = _message(stream, path.stat().st_size, 2)
        end = _message(stream, end, 100)
        metadata = {}
        for number, wire, start, size in _fields(stream, end):
            if number != 100 or wire != 2:
                continue
            if size > 4 * 1024 * 1024:
                raise ValueError('Zbyt duze metadane modelu')
            entry = io.BytesIO(stream.read(size))
            pair = {}
            for n, w, off, length in _fields(entry, size):
                if n in (1, 2) and w == 2:
                    pair[n] = entry.read(length).decode('utf-8')
            if 1 in pair and 2 in pair:
                metadata[pair[1]] = pair[2]
    return metadata


def check_model(path):
    try:
        if Path(path).suffix.lower() != '.mlmodel':
            raise ValueError('Checkpoint wymaga eksportu do .mlmodel')
        metadata = model_metadata(path)
        core = json.loads(metadata.get('kraken_meta', '{}'))
        kind = core.get('model_type')
        if kind != 'recognition' and not (isinstance(kind, list) and 'recognition' in kind):
            raise ValueError('Model ma niepoprawny typ (unknown). Wymaga poprawionego eksportu Kraken.')
        codec = metadata.get('codec', core.get('codec'))
        if isinstance(codec, str):
            codec = json.loads(codec)
        if not isinstance(codec, dict) or not codec:
            raise ValueError('Model nie ma alfabetu (codec). Wymaga poprawionego eksportu.')
        spec = metadata.get('vgsl', core.get('vgsl'))
        if not isinstance(spec, str) or not spec.startswith('['):
            raise ValueError('Brak architektury VGSL modelu')
        return {'ok': True, 'codec_len': len(codec), 'metadata_only': True}
    except Exception as exc:
        return {'ok': False, 'error': str(exc), 'metadata_only': True}
