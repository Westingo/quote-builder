#!/usr/bin/env python3
"""
Metro Access Control — Quote Builder (desktop app)

Runs the web server quietly in a background thread and shows the UI in a native
OS window via pywebview — no browser, no tabs, no address bar.

    python desktop.py              # open the native window
    python desktop.py --selftest   # boot server, build a test job, exit (no GUI)

app.py is still usable headless (python app.py) for a browser.
"""
import os
import sys
import threading
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))

# pythonw.exe (used by the desktop shortcut) provides NO console, so
# sys.stdout / sys.stderr are None. uvicorn's logging would crash writing to
# them — redirect to a log file BEFORE importing uvicorn.
LOGFILE = os.path.join(HERE, "desktop.log")
if sys.stdout is None or sys.stderr is None:
    _logf = open(LOGFILE, "a", encoding="utf-8", buffering=1)
    sys.stdout = _logf
    sys.stderr = _logf

import uvicorn
from app import app, JOBS

HOST, PORT = "127.0.0.1", 8485
URL = f"http://{HOST}:{PORT}"


class Api:
    """Bridge the JS UI calls (window.pywebview.api.*) to open the finished
    proposal or its folder in the OS default app — the desktop equivalent of a
    browser download."""

    def open_docx(self, slug, fname):
        p = os.path.join(JOBS, os.path.basename(slug), os.path.basename(fname))
        if os.path.isfile(p):
            os.startfile(p)            # opens in Word (Windows)
            return True
        return False

    def open_folder(self, slug):
        p = os.path.join(JOBS, os.path.basename(slug))
        if os.path.isdir(p):
            os.startfile(p)
            return True
        return False


def _serve():
    # uvicorn skips signal-handler install off the main thread, so this is safe
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


def _wait_until_up(timeout=40):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(URL + "/api/codes", timeout=1)
            return True
        except Exception:
            time.sleep(0.2)
    return False


def main(headless=False):
    threading.Thread(target=_serve, daemon=True).start()
    if not _wait_until_up():
        print("ERROR: server did not start", file=sys.stderr)
        sys.exit(1)
    print(f"server up at {URL}")

    if headless:
        import json
        body = urllib.request.urlopen(URL + "/").read()
        codes = urllib.request.urlopen(URL + "/api/codes").read()
        print(f"selftest: index {len(body)} bytes, codes {len(codes)} bytes")
        job = {"proposal": {"for": "SELFTEST", "date": "01/01/2026"},
               "gate_summary": ["(1) Test Gate"],
               "gates": [{"title": "Work to be Done at Test Gate Location:",
                          "lines": [{"code": "6", "sheet": "Gate Accessories", "qty": 1},
                                    {"text": "Free-text line", "qty": 2}]}],
               "options": [], "notes": ["N38"], "warranties": [], "exclusions": ["EX1"]}
        req = urllib.request.Request(URL + "/api/build", data=json.dumps(job).encode(),
                                     headers={"Content-Type": "application/json"})
        res = json.loads(urllib.request.urlopen(req).read())
        print(f"selftest build: {res}")
        return

    # Native window. If WebView2 is unavailable, log it and fall back to the
    # default browser rather than dying silently (no console under pythonw).
    try:
        import webview
        webview.create_window("Metro Quote Builder", URL,
                              width=1240, height=940, js_api=Api())
        webview.start()
    except Exception:
        import traceback
        import webbrowser
        try:
            with open(os.path.join(HERE, "desktop-error.log"), "w", encoding="utf-8") as f:
                f.write(traceback.format_exc())
        except Exception:
            pass
        webbrowser.open(URL)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main(headless="--selftest" in sys.argv)
