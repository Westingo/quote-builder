"""Render the real proposal with Microsoft Word, never an HTML approximation."""
import base64
from collections import OrderedDict
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

import proposal

_lock = threading.Lock()
_cache = OrderedDict()


def render(doc):
    key = hashlib.sha256(json.dumps(doc, sort_keys=True).encode()).hexdigest()
    with _lock:
        if key in _cache:
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
            python = Path(sys.executable)
            if python.name.lower() == "pythonw.exe":
                python = python.with_name("python.exe")
            try:
                result = subprocess.run(
                    [str(python), str(Path(__file__).resolve()), str(source)],
                    capture_output=True, timeout=60,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError("Word took too long to render. Close any Word setup or sign-in prompts and click Retry.") from exc
            if result.returncode:
                raise RuntimeError("Word could not render the preview. Make sure desktop Microsoft Word is installed and activated, then click Retry.")
            pages = []
            with pymupdf.open(root / "proposal.pdf") as pdf:
                for page in pdf:
                    pix = page.get_pixmap(dpi=144, alpha=False)
                    pages.append({"image": "data:image/png;base64," + base64.b64encode(pix.tobytes("png")).decode("ascii"),
                                  "width": pix.width, "height": pix.height})
        result = {"ok": True, "pages": pages, "renderer": "Microsoft Word"}
        _cache[key] = result
        while len(_cache) > 2:
            _cache.popitem(last=False)
        return result


def export_with_word(source):
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    word = document = None
    try:
        # A private instance: never close or edit the user's open documents.
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        word.AutomationSecurity = 3
        document = word.Documents.Open(str(source), ReadOnly=True, AddToRecentFiles=False,
                                       ConfirmConversions=False)
        document.Repaginate()
        document.Fields.Update()
        document.ExportAsFixedFormat(str(source.with_suffix(".pdf")), 17,
                                    OpenAfterExport=False)
    finally:
        try:
            if document is not None:
                document.Close(False)
        finally:
            try:
                if word is not None:
                    word.Quit()
            finally:
                pythoncom.CoUninitialize()


if __name__ == "__main__":
    export_with_word(Path(sys.argv[1]).resolve())
