"""Read the Copy Paste Google Sheet, keeping a validated offline snapshot."""
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen

import yaml
from build_codes import read_workbook, DICT_SHEETS

HERE = Path(__file__).resolve().parent
SHEET_ID = '1_JJQ8S-ZwqUzmRewfjesz84QV0dEf6P52bHjd_BLdOo'
SHEET_URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit'
EXPORT_URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx'
CACHE = HERE / '.product-cache.json'
INTERVAL = 60
MAX_BYTES = 20 * 1024 * 1024
_lock = threading.RLock()
_data = None
_last_attempt = None
_synced_at = None
_error = None


def _load_local():
    global _data, _synced_at
    if _data is not None:
        return
    try:
        cached = json.loads(CACHE.read_text(encoding='utf-8'))
        data = cached['data']
        if cached['sheet_id'] != SHEET_ID or not all(
            isinstance(data.get(name), list) and data[name] for name in DICT_SHEETS
        ):
            raise ValueError('Invalid product cache')
        _data, _synced_at = data, cached['synced_at']
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        _data = yaml.safe_load((HERE / 'codes.yaml').read_text(encoding='utf-8'))


def cached_codes():
    """The builder and scan importer use the same dictionary as the picker."""
    with _lock:
        _load_local()
        return _data


def _download():
    request = Request(EXPORT_URL, headers={'User-Agent': 'MetroQuoteBuilder/1.0',
                                          'Cache-Control': 'no-cache'})
    with urlopen(request, timeout=15) as response:
        content = response.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise ValueError('Google Sheet export exceeds 20 MB')
    if not content.startswith(b'PK'):
        raise ValueError('Google Sheet export is unavailable; check sheet access')
    return content


def _save(data, synced_at):
    # Replace only after the entire workbook has downloaded and validated.
    payload = {'sheet_id': SHEET_ID, 'synced_at': synced_at, 'data': data}
    filename = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=HERE,
                                         prefix='.product-cache-', suffix='.tmp',
                                         delete=False) as stream:
            filename = stream.name
            json.dump(payload, stream, ensure_ascii=False)
        os.replace(filename, CACHE)
    finally:
        if filename and os.path.exists(filename):
            os.unlink(filename)


def get_products(force=False):
    global _data, _last_attempt, _synced_at, _error
    with _lock:
        _load_local()
        if force or _last_attempt is None or time.monotonic() - _last_attempt >= INTERVAL:
            try:
                data = read_workbook(io.BytesIO(_download()), strict=True)
                synced_at = datetime.now(timezone.utc).isoformat()
                _save(data, synced_at)
                _data, _synced_at, _error = data, synced_at, None
            except Exception as exc:
                _error = str(exc)
            finally:
                _last_attempt = time.monotonic()
        version = hashlib.sha256(json.dumps(_data, sort_keys=True,
                                            ensure_ascii=False).encode('utf-8')).hexdigest()
        return _data, {'state': 'cached' if _error else 'live',
                       'last_synced': _synced_at, 'error': _error,
                       'sheet_url': SHEET_URL, 'version': version}
