"""Explicit LM selection; no runtime installation or ML import at GUI startup."""
import ast
import hashlib
import math
import unicodedata
import json
from collections import defaultdict
from pathlib import Path
from ocr_history import sha256

MODELS = Path(__file__).resolve().parents[1] / 'models'
KORBA = MODELS / 'public-korba-char-6gram.bin'
KORBA_SHA = 'a15c51d3d2911105965c9e273c1b6e595e542ecf1759517f26ebb5f81013f189'
HELPER = Path(__file__).with_name('lm_decoder.py')
HELPER_SHA = 'f24d3039c54ff02da6699d8a5f12a578ae9aeb47478a4536eba185764f41b1f4'
AST_SHA = '2e5ff1322e353fd79dec7478b6c226090ed279775b2f995ce3d35d61f60c2dd3'
DIARIUSZ_SHA = '7545861f8b82a5b4d8ecce74e057c720fadc7683c7aa2302bc63fd500b666bff'


def load_settings():
    try:
        return json.loads(Path(__file__).with_name('_lm_settings.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'choice':'none', 'alpha':0.5, 'beta':1.0, 'beam':64}


def save_settings(choice, alpha, beta, beam):
    from ocr_history import atomic_json
    atomic_json(Path(__file__).with_name('_lm_settings.json'),
                {'choice':choice, 'alpha':alpha, 'beta':beta, 'beam':beam})


def choices(legacy=''):
    return [{'id':'none','label':'Bez modelu językowego','available':True},
            
            {'id':'legacy','label':'Diariusz — podstawowy produkcyjny','available':bool(legacy and Path(legacy).is_file())}]


def resolve(choice, legacy=''):
    if choice == 'none':
        return ''
    if choice != 'legacy':
        raise ValueError('Nieznany model językowy.')
    path = str(KORBA) if choice == 'korba' else legacy
    if not path or not Path(path).is_file():
        raise ValueError('Wybrany model językowy jest niedostępny. Nie wykonano zamiany na inny LM.')
    if choice == 'korba' and sha256(path) != KORBA_SHA:
        raise ValueError('Plik KorBa nie zgadza się ze zweryfikowaną wersją.')
    if choice == 'legacy' and sha256(path) != DIARIUSZ_SHA:
        raise ValueError('Plik Diariusz LM nie zgadza się z opisaną wersją.')
    return path


def decoder(np):
    # Compile only the two reviewed functions, never import the framework-bearing helper.
    if sha256(HELPER) != HELPER_SHA:
        raise ValueError('Zmienił się zweryfikowany dekoder LM.')
    tree = ast.parse(HELPER.read_text(encoding='utf-8'))
    nodes = [n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('beam_lm','lm_krok')]
    module = ast.Module(body=nodes, type_ignores=[])
    if hashlib.sha256(ast.dump(module, include_attributes=False).encode()).hexdigest() != AST_SHA:
        raise ValueError('Niezgodna wersja dekodera CTC.')
    scope = dict(np=np, math=math, unicodedata=unicodedata, defaultdict=defaultdict, SP='▁')
    exec(compile(module, str(HELPER), 'exec'), scope)
    return scope['beam_lm']


def codec_alphabet(codec):
    result = {0: ''}
    for char, labels in codec.c2l.items():
        if char == '' and list(labels) == [0]:
            continue
        if len(labels) != 1 or labels[0] == 0 or len(unicodedata.normalize('NFD',char)) != 1 or char == '▁':
            raise ValueError('Ten codec nie obsługuje bezpiecznego dekodowania znakowego LM. Użyj RAW.')
        if labels[0] in result:
            raise ValueError('Niejednoznaczne etykiety codec.')
        result[labels[0]] = char
    if set(result) != set(range(len(result))):
        raise ValueError('Codec LM musi mieć ciągłe etykiety i blank 0.')
    return result


def validate_probabilities(np, probabilities, alphabet):
    if probabilities.ndim != 2 or probabilities.shape[0] != len(alphabet) or not probabilities.shape[1]:
        raise ValueError('Niezgodny układ macierzy CTC i codec.')
    if not (np.isfinite(probabilities).all() and (probabilities >= 0).all() and
            (probabilities <= 1).all() and np.allclose(probabilities.sum(axis=0,dtype=np.float64),1,atol=1e-5,rtol=0)):
        raise ValueError('Dekoder LM wymaga prawdopodobieństw CTC; nie zmienia logits ani temperatury.')
