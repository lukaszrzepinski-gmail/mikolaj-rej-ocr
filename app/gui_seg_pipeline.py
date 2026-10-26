"""Bounded CPU geometry workers; one parent owns the neural segmenter."""
import contextlib
import ctypes
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace

GIB = 1024 ** 3
GPU_LOCK = Path(os.environ['REJ_GPU_LOCK']) if os.environ.get('REJ_GPU_LOCK') else None


def memory(required=2 * GIB):
    if os.name != 'nt':
        raise RuntimeError('Ta wersja pełnej aplikacji wymaga Windows; wrapper PAGE działa osobno.')
    class Status(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [(name, ctypes.c_ulonglong) for name in ('total_phys','avail_phys','total_page','avail_page','total_virtual','avail_virtual','extended')]
    info = Status(); info.length = ctypes.sizeof(info)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(info)):
        raise OSError('Nie można sprawdzić dostępnej pamięci')
    if min(info.avail_phys, info.avail_page) < required:
        raise RuntimeError('Za mało wolnej pamięci RAM lub commit do bezpiecznej segmentacji')
    return min(info.avail_phys, info.avail_page)


def low_priority():
    kernel = ctypes.windll.kernel32
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    if not kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x4000):
        raise OSError('Nie można ustawić bezpiecznego priorytetu segmentacji')


@contextlib.contextmanager
def device_lease(device):
    stream = None
    if device.startswith('cuda'):
        import msvcrt
        if GPU_LOCK is None or not GPU_LOCK.is_file() or GPU_LOCK.is_symlink():
            raise RuntimeError('Brak oryginalnej blokady GPU; segmentacja nie została uruchomiona')
        stream = GPU_LOCK.open('r+b')
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            stream.close()
            raise RuntimeError('GPU jest zajęte przez trening. Wybierz CPU albo wykonaj segmentację po zwolnieniu GPU.')
    try:
        yield
    finally:
        if stream is not None:
            stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1); stream.close()


def cpu_init():
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    for name in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        os.environ[name] = '1'
    low_priority(); memory(int(3.5 * GIB))
    import torch
    torch.set_num_threads(1)


def dump_map(folder, rets, model, size):
    import numpy as np
    folder = Path(folder); folder.mkdir()
    # Keep all original float32 values; never use the old float16 shortcut.
    np.save(folder/'heatmap.npy', rets['heatmap'], allow_pickle=False)
    np.save(folder/'scal_im.npy', rets['scal_im'], allow_pickle=False)
    metadata = {'cls_map':rets['cls_map'], 'bounding_regions':rets['bounding_regions'],
                'scale':rets['scale'].tolist(), 'size':list(size),
                'topline':model.user_metadata.get('topline', False)}
    (folder/'metadata.json').write_text(json.dumps(metadata), encoding='utf-8')


def vectorize(folder):
    memory(); started = time.perf_counter()
    import numpy as np
    from PIL import Image
    from kraken import blla
    folder = Path(folder); meta = json.loads((folder/'metadata.json').read_text())
    rets = {key:meta[key] for key in ('cls_map','bounding_regions')}
    rets.update(scale=np.asarray(meta['scale']),
                heatmap=np.load(folder/'heatmap.npy', mmap_mode='c', allow_pickle=False),
                scal_im=np.load(folder/'scal_im.npy', mmap_mode='c', allow_pickle=False))
    descriptor = SimpleNamespace(model_type='segmentation',
        user_metadata={'class_mapping':meta['cls_map'],'topline':meta['topline']}, aux_layers={})
    original = blla.compute_segmentation_map
    blla.compute_segmentation_map = lambda *args, **kwargs: rets
    try:
        segmentation = blla.segment(Image.new('L', tuple(meta['size'])), model=[descriptor], device='cpu')
    finally:
        blla.compute_segmentation_map = original
    lines = [{'baseline':[[float(x),float(y)] for x,y in line.baseline],
              'boundary':[[float(x),float(y)] for x,y in (line.boundary or [])]} for line in segmentation.lines]
    memory()
    return {'lines':lines,'cpu_geometry_seconds':time.perf_counter()-started,'CPU_only_worker':True}
