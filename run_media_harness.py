"""EXECUTES the real media/processing.py and media/signing.py with real Pillow,
against stubs for Django/DRF (not installed here). Verifies the image-pipeline
security properties at the Pillow level. It does NOT test views, auth, storage
backends or the database."""
import hashlib, hmac, importlib.util, io, sys, time, types
from pathlib import Path

import os
ROOT = Path(os.environ.get('VEYA_BACKEND', str(Path(__file__).resolve().parents[2] / 'backend')))

# ---- stubs --------------------------------------------------------------
class VErr(Exception):
    def __init__(self, detail): self.detail = detail
settings = types.SimpleNamespace(MEDIA_MAX_BYTES=5*1024*1024, MEDIA_MAX_PIXELS=40_000_000,
                                 MEDIA_URL_BUCKET_SECONDS=6*3600, SECRET_KEY='test-secret')
STORE = {}
class _Storage:
    def save(self, name, content):
        n = name
        while n in STORE: n = n.replace('.jpg', '_x.jpg')
        STORE[n] = content.read() if hasattr(content, 'read') else content
        return n
class ContentFile:
    def __init__(self, b): self._b = b
    def read(self): return self._b
def mod(name, **attrs):
    m = types.ModuleType(name); m.__dict__.update(attrs); sys.modules[name] = m; return m
for n in ['django', 'django.conf', 'django.core', 'django.core.files', 'django.core.files.base',
          'django.core.files.storage', 'django.utils', 'django.utils.crypto',
          'rest_framework', 'rest_framework.exceptions']: mod(n)
sys.modules['django.conf'].settings = settings
sys.modules['django.core.files.base'].ContentFile = ContentFile
sys.modules['django.core.files.storage'].default_storage = _Storage()
sys.modules['rest_framework.exceptions'].ValidationError = VErr
class _Mac:
    def __init__(self, k): self.k = k
    def hexdigest(self): return self.k
sys.modules['django.utils.crypto'].salted_hmac = lambda salt, value: _Mac(
    hmac.new((salt + settings.SECRET_KEY).encode(), value.encode(), hashlib.sha256).hexdigest())
sys.modules['django.utils.crypto'].constant_time_compare = hmac.compare_digest

def load(relpath, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relpath)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
processing = load('media/processing.py', 'processing')
signing = load('media/signing.py', 'signing')

from PIL import Image, ExifTags
class Upload(io.BytesIO):
    def __init__(self, b): super().__init__(b); self.size = len(b)
def img_bytes(fmt, size=(800, 600), mode='RGB', color=(200, 30, 30), **kw):
    b = io.BytesIO(); Image.new(mode, size, color).save(b, fmt, **kw); return b.getvalue()

results = []
def check(name, fn):
    try: fn(); results.append((name, True, ''))
    except AssertionError as e: results.append((name, False, str(e) or 'assertion failed'))
    except Exception as e: results.append((name, False, f'{type(e).__name__}: {e}'))
def rejects(b, kind='post', why=None):
    try: processing.process_upload(Upload(b), kind, 'owner')
    except VErr: return
    raise AssertionError('accepted but should have been rejected')
def accepts(b, kind='post'):
    return processing.process_upload(Upload(b), kind, 'owner')
def stored(info, which='path'): return STORE[info[which]]

# ---- cases --------------------------------------------------------------
for fmt in ['JPEG', 'PNG', 'WEBP']:
    check(f'accepts valid {fmt}', lambda f=fmt: accepts(img_bytes(f)))
check('output is a decodable JPEG', lambda: (lambda i: (Image.open(io.BytesIO(stored(i))).format == 'JPEG') or (_ for _ in ()).throw(AssertionError('not JPEG')))(accepts(img_bytes('PNG'))))
check('RGBA PNG with alpha flattened (no crash, RGB out)', lambda: Image.open(io.BytesIO(stored(accepts(img_bytes('PNG', mode='RGBA', color=(200, 30, 30, 90)))))).mode == 'RGB' or (_ for _ in ()).throw(AssertionError('not RGB')))
check('palette PNG with transparency accepted', lambda: accepts((lambda b: (Image.new('P', (50, 50)).save(b, 'PNG', transparency=0), b.getvalue())[1])(io.BytesIO())))
check('CMYK JPEG accepted', lambda: accepts(img_bytes('JPEG', mode='CMYK', color=(0, 0, 0, 0))))
check('16-bit grayscale PNG accepted', lambda: accepts(img_bytes('PNG', mode='I;16', color=1000)))
check('post full image capped at 1600px, thumb at 400px', lambda: (lambda i: (max(Image.open(io.BytesIO(stored(i))).size) <= 1600 and max(Image.open(io.BytesIO(stored(i, 'thumb_path'))).size) <= 400) or (_ for _ in ()).throw(AssertionError('size cap')))(accepts(img_bytes('JPEG', size=(3200, 2400)))))
check('avatar capped at 512px / thumb 128px', lambda: (lambda i: (max(Image.open(io.BytesIO(stored(i))).size) <= 512 and max(Image.open(io.BytesIO(stored(i, 'thumb_path'))).size) <= 128) or (_ for _ in ()).throw(AssertionError('size cap')))(accepts(img_bytes('JPEG', size=(2000, 2000)), 'avatar')))

def exif_case():
    e = Image.Exif(); e[0x010F] = 'SecretCameraMaker'; e[0x0110] = 'Model-X'
    e.get_ifd(0x8825)[1] = 'N'; e.get_ifd(0x8825)[2] = (33.0, 0.0, 0.0)   # GPS IFD
    raw = img_bytes('JPEG', exif=e.tobytes())
    assert b'SecretCameraMaker' in raw, 'test setup: EXIF not embedded'
    out = stored(accepts(raw))
    assert b'SecretCameraMaker' not in out and b'Model-X' not in out, 'EXIF text survived'
    assert not dict(Image.open(io.BytesIO(out)).getexif()), 'EXIF tags survived'
check('EXIF/GPS metadata is stripped', exif_case)

def orientation_case():
    e = Image.Exif(); e[0x0112] = 6   # rotate 90 CW on display
    out = Image.open(io.BytesIO(stored(accepts(img_bytes('JPEG', size=(800, 400), exif=e.tobytes())))))
    assert out.size[1] > out.size[0], f'orientation not applied, got {out.size}'
check('EXIF orientation applied before stripping', orientation_case)

def polyglot():
    payload = b'<?php system($_GET["c"]); ?>PAYLOAD_MARKER_123'
    raw = img_bytes('JPEG') + payload
    out = stored(accepts(raw))
    assert b'PAYLOAD_MARKER_123' not in out, 'appended payload survived re-encode'
check('data appended to a JPEG does not survive', polyglot)
def png_chunk_payload():
    raw = bytearray(img_bytes('PNG')); iend = raw.rfind(b'IEND')
    raw[iend - 4:iend - 4] = b'\x00\x00\x00\x0ctEXtcomment\x00EVIL_TEXT_CHUNK\x00\x00\x00\x00'
    try: out = stored(accepts(bytes(raw)))
    except VErr: return          # rejecting corrupt chunk CRC is also safe
    assert b'EVIL_TEXT_CHUNK' not in out
check('PNG text-chunk payload does not survive', png_chunk_payload)

check('rejects plain text named .jpg', lambda: rejects(b'<?php echo 1; ?>'))
check('rejects empty upload', lambda: rejects(b''))
check('rejects GIF', lambda: rejects(img_bytes('GIF')))
check('rejects BMP', lambda: rejects(img_bytes('BMP')))
check('rejects TIFF', lambda: rejects(img_bytes('TIFF')))
check('rejects SVG with script', lambda: rejects(b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'))
check('rejects HTML disguised as image', lambda: rejects(b'<html><script>alert(1)</script></html>'))
check('rejects truncated JPEG', lambda: rejects(img_bytes('JPEG', size=(1200, 900))[:700]))
check('rejects corrupt random bytes', lambda: rejects(bytes(range(256)) * 40))
check('rejects invalid kind', lambda: processing.process_upload(Upload(img_bytes('JPEG')), 'video', 'o'))  if False else None
def bad_kind():
    try: processing.process_upload(Upload(img_bytes('JPEG')), 'video', 'o')
    except VErr: return
    raise AssertionError('invalid kind accepted')
check('rejects invalid kind', bad_kind)

def too_large():
    old = settings.MEDIA_MAX_BYTES; settings.MEDIA_MAX_BYTES = 500
    try: rejects(img_bytes('JPEG', size=(900, 900), color=(1, 2, 3)))
    finally: settings.MEDIA_MAX_BYTES = old
check('rejects over MEDIA_MAX_BYTES', too_large)
def pixel_limit():
    old = settings.MEDIA_MAX_PIXELS; settings.MEDIA_MAX_PIXELS = 1000
    try: rejects(img_bytes('JPEG', size=(100, 100)))
    finally: settings.MEDIA_MAX_PIXELS = old
check('rejects over MEDIA_MAX_PIXELS', pixel_limit)
def decompression_bomb():
    # a real "bomb": 30000x30000 1-bit PNG compresses to a few KB but is 900 MP
    b = io.BytesIO(); Image.new('1', (30000, 30000), 0).save(b, 'PNG', optimize=False)
    raw = b.getvalue(); assert len(raw) < settings.MEDIA_MAX_BYTES, f'setup: {len(raw)} bytes'
    rejects(raw)
check('rejects a real 900-megapixel decompression bomb (small file)', decompression_bomb)

def no_original_stored():
    STORE.clear(); raw = img_bytes('PNG'); accepts(raw)
    assert all(v != raw for v in STORE.values()), 'original bytes were stored'
    assert all(k.endswith('.jpg') for k in STORE), list(STORE)
check('original upload bytes are never stored; only .jpg outputs', no_original_stored)
def names_random():
    a = accepts(img_bytes('JPEG')); b = accepts(img_bytes('JPEG'))
    assert a['path'] != b['path'] and 'owner' in a['path']
check('storage names are unique per upload', names_random)

# ---- signing ------------------------------------------------------------
import uuid
iid = uuid.uuid4()
check('sig roundtrip valid', lambda: signing.check_sig(iid, signing.make_sig(iid)) or (_ for _ in ()).throw(AssertionError('invalid')))
check('sig tamper rejected', lambda: (not signing.check_sig(iid, signing.make_sig(iid)[:-1] + ('0' if signing.make_sig(iid)[-1] != '0' else '1'))) or (_ for _ in ()).throw(AssertionError('tampered accepted')))
check('sig for another id rejected', lambda: (not signing.check_sig(uuid.uuid4(), signing.make_sig(iid))) or (_ for _ in ()).throw(AssertionError('cross-id accepted')))
check('garbage / empty / None sigs rejected', lambda: all(not signing.check_sig(iid, s) for s in ['garbage', '', '1.2.3', 'x.y', None]) or (_ for _ in ()).throw(AssertionError('garbage accepted')))
def expiry():
    sig = signing.make_sig(iid); real = time.time
    try:
        time.time = lambda: real() + 1 * settings.MEDIA_URL_BUCKET_SECONDS
        assert signing.check_sig(iid, sig), 'previous bucket should still be valid'
        time.time = lambda: real() + 3 * settings.MEDIA_URL_BUCKET_SECONDS
        assert not signing.check_sig(iid, sig), 'expired bucket accepted'
    finally: time.time = real
check('sig valid in previous bucket, rejected after 2 buckets', expiry)
check('sig is deterministic within a bucket (image-cache friendly)', lambda: signing.make_sig(iid) == signing.make_sig(iid) or (_ for _ in ()).throw(AssertionError('not deterministic')))

# ---- report -------------------------------------------------------------
import PIL
p = sum(1 for _, ok, _ in results if ok); f = len(results) - p
for n, ok, msg in results: print(('PASS ' if ok else 'FAIL ') + n + ('' if ok else f'  ← {msg}'))
print(f'\nPillow {PIL.__version__} (project pins 11.0.0). TOTAL: {p} passed, {f} failed')
sys.exit(1 if f else 0)
