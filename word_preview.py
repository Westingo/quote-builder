"""Render the real proposal with Microsoft Word, never an HTML approximation."""
import base64
import atexit
from collections import OrderedDict
import hashlib
import json
import queue
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

import proposal

_lock = threading.Lock()
_cache = OrderedDict()
_worker = None
_replies = None


def close_worker():
    global _worker, _replies
    worker, _worker = _worker, None
    _replies = None
    if worker is None:
        return
    try:
        worker.stdin.close()
        worker.wait(timeout=3)
    except (OSError, subprocess.TimeoutExpired):
        worker.terminate()
        worker.wait()
    finally:
        worker.stdout.close()


atexit.register(close_worker)


def _export(source):
    """Keep COM on one isolated process/thread and reuse its private Word instance."""
    global _worker, _replies
    if _worker is None or _worker.poll() is not None:
        close_worker()
        python = Path(sys.executable)
        if python.name.lower() == "pythonw.exe":
            python = python.with_name("python.exe")
        _worker = subprocess.Popen(
            [str(python), str(Path(__file__).resolve()), "--worker"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW,
        )
        _replies = queue.Queue()
        def read_replies(process, replies):
            try:
                for line in process.stdout:
                    replies.put(line)
            finally:
                replies.put(None)
        threading.Thread(target=read_replies, args=(_worker, _replies), daemon=True).start()
    try:
        _worker.stdin.write(json.dumps(str(source)) + "\n")
        _worker.stdin.flush()
        reply = _replies.get(timeout=60)
        if reply is None or not json.loads(reply).get("ok"):
            raise RuntimeError("Word could not render the preview. Make sure desktop Microsoft Word is installed and activated, then click Retry.")
    except queue.Empty as exc:
        close_worker()
        raise RuntimeError("Word took too long to render. Close any Word setup or sign-in prompts and click Retry.") from exc
    except Exception:
        close_worker()
        raise


def render(doc):
    key = hashlib.sha256(json.dumps(doc, sort_keys=True).encode()).hexdigest()
    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
        if sys.platform != "win32":
            raise RuntimeError("Exact preview requires Microsoft Word on Windows.")
        try:
            import pymupdf
        except ImportError as exc:
            raise RuntimeError("Preview components are missing. Close the app and run run.bat to install them.") from exc
        with tempfile.TemporaryDirectory(prefix="metro-preview-") as folder:
            root = Path(folder)
            source = root / "proposal.docx"
            proposal.build_proposal(doc, str(source))
            _export(source)
            pages = []
            with pymupdf.open(root / "proposal.pdf") as pdf:
                for page in pdf:
                    pix = page.get_pixmap(dpi=144, alpha=False)
                    pages.append({"image": "data:image/png;base64," + base64.b64encode(pix.tobytes("png")).decode("ascii"),
                                  "width": pix.width, "height": pix.height})
        result = {"ok": True, "pages": pages, "renderer": "Microsoft Word"}
        _cache[key] = result
        while len(_cache) > 8:
            _cache.popitem(last=False)
        return result


def export_pdf(source):
    """Export a saved proposal without colliding with preview or user PDFs."""
    with _lock:
        if sys.platform != "win32":
            raise RuntimeError("PDF export requires Microsoft Word on Windows.")
        with tempfile.TemporaryDirectory(prefix="metro-pdf-") as folder:
            staged = Path(folder) / "proposal.docx"
            shutil.copyfile(source, staged)
            _export(staged)
            return staged.with_suffix(".pdf").read_bytes()


def export_with_word(source, word):
    document = None
    try:
        document = word.Documents.Open(str(source), ReadOnly=True, AddToRecentFiles=False,
                                       ConfirmConversions=False)
        document.Repaginate()
        document.Fields.Update()
        document.ExportAsFixedFormat(str(source.with_suffix(".pdf")), 17,
                                    OpenAfterExport=False)
    finally:
        if document is not None:
            document.Close(False)


def run_worker(sources):
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    word = None
    try:
        # A private instance: never close or edit the user's open documents.
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        word.AutomationSecurity = 3
        # Windows may reuse this instance when opening a finished quote.
        # Keep painting enabled so that first user-visible document is not blank.
        word.ScreenUpdating = True
        for source in sources:
            try:
                export_with_word(Path(source).resolve(), word)
                print(json.dumps({"ok": True}), flush=True)
            except Exception:
                print(json.dumps({"ok": False}), flush=True)
                break
    finally:
        try:
            if word is not None:
                word.Quit()
        finally:
            pythoncom.CoUninitialize()


if __name__ == "__main__":
    sources = (json.loads(line) for line in sys.stdin) if sys.argv[1] == "--worker" else [sys.argv[1]]
    run_worker(sources)
