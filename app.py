#!/usr/bin/env python3
"""
Metro Access Control — Quote / Proposal Builder (web UI)

    python app.py            ->  open http://localhost:8485

Wraps build.py: the form posts a job, we write jobs/<slug>/job.yaml, run the
builder, and hand back the finished .docx. Runs standalone via desktop.py
(pywebview window) or headless here for a browser.
"""
import os
import re
import io
import glob
import json
import contextlib

import yaml
from fastapi import FastAPI, Body
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse

import build as builder

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")
JOBS = os.path.join(HERE, "jobs")
CODES = os.path.join(HERE, "codes.yaml")

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

app = FastAPI(title="Metro Quote Builder")


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-") or "job"


@app.get("/", response_class=HTMLResponse)
def index():
    return open(os.path.join(STATIC, "index.html"), encoding="utf-8").read()


@app.get("/api/codes")
def api_codes():
    """The dictionary, grouped sheet -> category -> items, for the picker UI."""
    data = yaml.safe_load(open(CODES, encoding="utf-8"))
    sheets = []
    for sheet, items in data.items():
        cats = {}
        for it in items:
            cat = it.get("category") or sheet
            desc = it.get("description") or ""
            cats.setdefault(cat, []).append({
                "code": str(it["code"]),
                "description": desc,
                "section": it.get("section", "scope"),
                "blanks": "_" in desc,          # has fill-in placeholders
                "model": it.get("model", ""),
            })
        sheets.append({
            "sheet": sheet,
            "section": items[0].get("section", "scope") if items else "scope",
            "categories": [{"name": k, "items": v} for k, v in cats.items()],
        })
    return {"sheets": sheets}


@app.get("/api/jobs")
def api_jobs():
    out = []
    if os.path.isdir(JOBS):
        for d in sorted(os.listdir(JOBS)):
            jd = os.path.join(JOBS, d)
            if d.startswith("_") or not os.path.isdir(jd):
                continue
            docs = sorted(glob.glob(os.path.join(jd, "*.docx")),
                          key=os.path.getmtime, reverse=True)
            out.append({"slug": d,
                        "docx": os.path.basename(docs[0]) if docs else None})
    return out


@app.get("/api/job/{slug}")
def api_job(slug: str):
    """Load a saved job back into the form (for revisions / addenda)."""
    path = os.path.join(JOBS, os.path.basename(slug), "job.yaml")
    if not os.path.isfile(path):
        return JSONResponse({"error": "not found"}, status_code=404)
    return yaml.safe_load(open(path, encoding="utf-8"))


@app.post("/api/build")
def api_build(job: dict = Body(...)):
    customer = (job.get("proposal", {}) or {}).get("for", "").strip()
    if not customer:
        return JSONResponse({"ok": False, "log": "Customer (For:) is required."},
                            status_code=400)

    slug = slugify(job.get("slug") or customer)
    job_dir = os.path.join(JOBS, slug)
    os.makedirs(job_dir, exist_ok=True)
    job.pop("slug", None)
    with open(os.path.join(job_dir, "job.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(job, f, sort_keys=False, allow_unicode=True)

    buf = io.StringIO()
    ok, out = True, None
    try:
        with contextlib.redirect_stdout(buf):
            out = builder.main(job_dir)
    except KeyError as e:                 # unknown code -> friendly message
        buf.write(f"\nERROR: code {e} is not in codes.yaml. "
                  f"Use a free-text line instead, or check the code.")
        ok = False
    except Exception as e:
        buf.write(f"\nERROR: {e}")
        ok = False

    if not ok:
        return JSONResponse({"ok": False, "log": buf.getvalue()}, status_code=500)
    return {"ok": True, "log": buf.getvalue(), "slug": slug,
            "docx": os.path.basename(out)}


@app.get("/download/{slug}/{fname}")
def download(slug: str, fname: str):
    path = os.path.join(JOBS, os.path.basename(slug), os.path.basename(fname))
    if not os.path.isfile(path):
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(path, media_type=DOCX_MIME, filename=fname)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8485, log_level="warning")
