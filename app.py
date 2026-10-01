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
from fastapi import FastAPI, Body, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

import build as builder
import scan_import
import product_sync
import word_preview
import quote_transfer
import quote_pdf
import quote_backup

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")
JOBS = os.path.join(HERE, "jobs")
CODES = os.path.join(HERE, "codes.yaml")

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

app = FastAPI(title="Metro Quote Builder")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.post("/api/preview")
def api_preview(job: dict = Body(...)):
    """Render a temporary copy of the actual DOCX through Microsoft Word."""
    try:
        data, index = builder.load_codes()
        doc = builder.build_doc(job, data, index)
        return word_preview.render(doc)
    except (KeyError, TypeError, ValueError) as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=503)


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-") or "job"


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(open(os.path.join(STATIC, "index.html"), encoding="utf-8").read(),
                        headers={"Cache-Control": "no-store"})


@app.get("/api/codes")
def api_codes(refresh: bool = False, local: bool = False):
    """The dictionary, grouped sheet -> category -> items, for the picker UI."""
    data, sync = product_sync.get_products(force=refresh, local_only=local)
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
    return {"sheets": sheets, "sync": sync}


@app.get("/api/jobs")
def api_jobs():
    """Recent quotes, newest first — for the sidebar list and reload."""
    out = []
    if os.path.isdir(JOBS):
        for d in os.listdir(JOBS):
            jd = os.path.join(JOBS, d)
            if d.startswith("_") or not os.path.isdir(jd):
                continue
            yml = os.path.join(jd, "job.yaml")
            cust, date = d, ""
            if os.path.isfile(yml):
                try:
                    p = (yaml.safe_load(open(yml, encoding="utf-8")) or {}).get("proposal", {})
                    cust = (p.get("for") or "").strip() or d
                    date = p.get("date", "") or ""
                except Exception:
                    pass
            docs = sorted(glob.glob(os.path.join(jd, "*.docx")),
                          key=os.path.getmtime, reverse=True)
            mtime = os.path.getmtime(yml) if os.path.isfile(yml) else os.path.getmtime(jd)
            out.append({"slug": d, "for": cust, "date": date, "mtime": mtime,
                        "docx": os.path.basename(docs[0]) if docs else None})
    out.sort(key=lambda x: x["mtime"], reverse=True)
    return out


@app.get("/api/job/{slug}")
def api_job(slug: str):
    """Load a saved job back into the form (for revisions / addenda)."""
    path = os.path.join(JOBS, os.path.basename(slug), "job.yaml")
    if not os.path.isfile(path):
        return JSONResponse({"error": "not found"}, status_code=404)
    return yaml.safe_load(open(path, encoding="utf-8"))


@app.post("/api/build")
def api_build(job: dict = Body(...), pdf: bool = False):
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
    backup, warnings = backup_quote(job, slug)
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
        return JSONResponse({"ok": False, "log": buf.getvalue(), "slug": slug,
                             "backup": backup, "warnings": warnings}, status_code=500)
    pdf_name = None
    if pdf:
        try:
            content = quote_pdf.embed(word_preview.export_pdf(out), job)
            base = os.path.splitext(out)[0]
            # Keep older PDFs intact, including files already open in a viewer.
            for number in range(1, 10000):
                target = base + (f" ({number})" if number > 1 else "") + ".pdf"
                try:
                    with open(target, "xb") as f:
                        f.write(content)
                    pdf_name = os.path.basename(target)
                    break
                except FileExistsError:
                    continue
            if pdf_name is None:
                raise RuntimeError("Too many PDF copies in this quote folder.")
        except Exception as exc:
            warnings.append(f"Word quote saved, but PDF was not created: {exc}")
    return {"ok": True, "log": buf.getvalue(), "slug": slug,
            "docx": os.path.basename(out), "pdf": pdf_name,
            "backup": backup, "warnings": warnings}


def backup_quote(job, slug):
    try:
        return quote_backup.save(job, slug), []
    except Exception as exc:
        return None, [f"Quote saved locally, but automatic backup failed: {exc}"]


@app.get("/api/backup-folder")
def api_backup_folder():
    return {"path": str(quote_backup.directory())}


@app.post("/api/import")
def api_import(file: UploadFile = File(...)):
    """Read a scanned sheet/quote/email with Claude vision -> draft job dict."""
    try:
        data = file.file.read()
        job, raw = scan_import.import_scan(data, file.content_type, file.filename or "")
        return {"ok": True, "job": job}
    except Exception as e:
        return JSONResponse({"ok": False, "log": f"Import failed: {e}"},
                            status_code=500)


@app.post("/api/quote/export")
def api_export_quote(job: dict = Body(...)):
    try:
        data = quote_transfer.export_quote(job)
        filename = slugify(job["proposal"]["for"]) + ".metroquote"
        return Response(data, media_type="application/json", headers={
            "Content-Disposition": f'attachment; filename="{filename}"'})
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@app.post("/api/quote/import")
def api_import_quote(file: UploadFile = File(...)):
    try:
        is_pdf = (file.filename or "").lower().endswith(".pdf")
        limit = quote_pdf.MAX_PDF_BYTES if is_pdf else quote_transfer.MAX_BYTES
        data = file.file.read(limit + 1)
        job = quote_pdf.extract(data) if is_pdf else quote_transfer.import_quote(data)
    except (ValueError, RecursionError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    base = slugify(job["proposal"]["for"]) + "-imported"
    slug, suffix = base, 2
    os.makedirs(JOBS, exist_ok=True)
    while True:
        job_dir = os.path.join(JOBS, slug)
        try:
            os.mkdir(job_dir)
            break
        except FileExistsError:
            slug, suffix = f"{base}-{suffix}", suffix + 1
    with open(os.path.join(job_dir, "job.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(job, f, sort_keys=False, allow_unicode=True)
    backup, warnings = backup_quote(job, slug)
    return {"ok": True, "job": job, "slug": slug, "backup": backup, "warnings": warnings}


@app.get("/download/{slug}/{fname}")
def download(slug: str, fname: str):
    path = os.path.join(JOBS, os.path.basename(slug), os.path.basename(fname))
    if not os.path.isfile(path):
        return JSONResponse({"error": "not found"}, status_code=404)
    mime = "application/pdf" if fname.lower().endswith(".pdf") else DOCX_MIME
    return FileResponse(path, media_type=mime, filename=fname)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8485, log_level="warning")
