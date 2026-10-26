"""Verify released model bytes with the standard library only."""
import argparse
import hashlib
from pathlib import Path

EXPECTED = {
    'MikolajRej-KRA-K11-E26-step345005.mlmodel':
        ('871092c802375e0100c1b2efefb2dcf687b87022f2305723dfffb9aeef5e243d', 16437242),
    'lm6B.bin':
        ('7545861f8b82a5b4d8ecce74e057c720fadc7683c7aa2302bc63fd500b666bff', 61757330),
}


def check(directory, require_lm=False):
    for name, (expected, size) in EXPECTED.items():
        path = directory / name
        if not path.is_file():
            if name == 'lm6B.bin' and not require_lm:
                print('Optional Diariusz LM absent: RAW remains available.')
                continue
            raise ValueError('Missing model: ' + name)
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        if path.stat().st_size != size or digest.hexdigest() != expected:
            raise ValueError('Model size/SHA256 mismatch: ' + name)
        print('OK ' + name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--require-lm', action='store_true')
    args = parser.parse_args()
    try:
        check(args.directory, args.require_lm)
    except (OSError, ValueError) as error:
        parser.exit(1, str(error) + '\n')
