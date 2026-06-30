"""
scan_import.py — turn a scanned sheet / quote / email into a draft job.

Sends the uploaded image or PDF to Claude's vision API along with the code
dictionary, gets back a structured extraction, and maps it into our job.yaml
shape (resolving each shortcut code to its sheet). The result is a DRAFT for the
salesman to review in the form — handwriting especially will need corrections.

API key: ANTHROPIC_API_KEY env var, or an `api_key.txt` file next to this script.
Model: claude-opus-4-8 by default (override with QUOTE_IMPORT_MODEL).
"""
import os
import re
import json
import base64

import build

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.environ.get("QUOTE_IMPORT_MODEL", "claude-opus-4-8")
NWE_SECTION = {"note": "notes", "warranty": "warranties", "exclusion": "exclusions"}


def api_key():
    k = os.environ.get("ANTHROPIC_API_KEY")
    if k:
        return k.strip()
    p = os.path.join(HERE, "api_key.txt")
    if os.path.isfile(p):
        return open(p, encoding="utf-8").read().strip()
    return None


def _dictionary_lines(data):
    """Compact 'code | sheet | description' list so the model maps codes exactly."""
    out = []
    for sheet, items in data.items():
        for it in items:
            desc = (it.get("description") or "").replace("\n", " ")[:90]
            out.append(f"{it['code']} | {sheet} | {desc}")
    return "\n".join(out)


PROMPT = """You are reading a scanned Metro Access Control sales sheet, quote, or \
email and extracting it into a structured quote. The input may be handwritten.

Return ONLY a JSON object (no markdown fences, no prose) with this exact shape:
{{
  "proposal": {{"for":"", "attention":"", "address":"", "phone":"", "email":"",
    "date":"", "terms":"", "job_address":"", "bid_number":"", "submitted_by":""}},
  "gate_summary": ["(1) 24' x 8' Vertical Pivot Gate"],
  "gates": [
    {{"title":"Work to be Done at 24' Gate Location:",
      "lines":[ {{"code":"6","qty":1}}, {{"text":"Ground rod","qty":1}},
                {{"text":"Reflective tape on both sides","qty":null}} ]}}
  ],
  "notes": ["N4","N6"], "warranties": ["W2"], "exclusions": ["EX1","EX6"],
  "total": null
}}

Rules:
- Each work location has a header like "Work to be Done at <X> Gate Location:". \
Group its lines under that gate. If there are no headers, use one gate with a \
sensible title.
- A scope line may reference a shortcut CODE from the dictionary below. Salesmen \
write codes like "6", "#6", "23", "N4", "W2", "EX1", "SIG40". Map each to the \
EXACT code key from the dictionary and put it in "code". If a line is plain text \
not in the dictionary (e.g. "Ground rod", "Cold weather package"), put it in \
"text" instead — never guess a code.
- qty is the number before ")" (e.g. "2) Loop detectors" -> qty 2). A "—" or no \
number -> qty null.
- notes / warranties / exclusions are usually listed as codes after "N:", "W:", \
"E:" or "Ex:". Map to code keys from the N, W, E sheets. If written out in full, \
return the text instead of a code.
- Leave a field "" or null when it is not present. Do not invent values.

DICTIONARY (code | sheet | description):
{dictionary}
"""


def _extract_json(text):
    m = re.search(r"\{.*\}", text.strip(), re.S)
    return json.loads(m.group(0) if m else text)


def _nwe_items(values, index, section):
    """Pass valid codes through as strings; wrap free text as {text: ...}."""
    out = []
    for v in values or []:
        s = str(v).strip()
        if not s:
            continue
        rows = index.get(s)
        if rows and any(it.get("section") == section for _, it in rows):
            out.append(s)
        else:
            out.append({"text": s})
    return out


def _to_job(parsed, index):
    p = parsed.get("proposal", {}) or {}
    gates = []
    for g in parsed.get("gates", []) or []:
        lines = []
        for ln in g.get("lines", []) or []:
            qty = ln.get("qty")
            code = str(ln.get("code") or "").strip()
            rows = index.get(code) if code else None
            if rows:
                lines.append({"code": code, "sheet": rows[0][0], "qty": qty})
            else:
                txt = str(ln.get("text") or code or "").strip()
                if txt:
                    lines.append({"text": txt, "qty": qty})
        gates.append({"title": (g.get("title") or "Work to be Done:").strip(),
                      "lines": lines})
    return {
        "proposal": {k: (p.get(k) or "") for k in
                     ("for", "attention", "address", "phone", "email", "date",
                      "terms", "job_address", "bid_number", "submitted_by")},
        "gate_summary": [s for s in (parsed.get("gate_summary") or []) if str(s).strip()],
        "gates": gates,
        "options": [],   # options are reviewed/added by hand after import
        "notes": _nwe_items(parsed.get("notes"), index, "note"),
        "warranties": _nwe_items(parsed.get("warranties"), index, "warranty"),
        "exclusions": _nwe_items(parsed.get("exclusions"), index, "exclusion"),
        "total": parsed.get("total"),
    }


def import_scan(file_bytes, content_type, filename=""):
    """Returns (job_dict, raw_text). Raises on API/parse errors."""
    import anthropic

    key = api_key()
    if not key:
        raise RuntimeError(
            "No Anthropic API key. Set ANTHROPIC_API_KEY, or put your key in "
            "api_key.txt next to the app, then try again.")

    data, index = build.load_codes()
    prompt = PROMPT.format(dictionary=_dictionary_lines(data))
    b64 = base64.standard_b64encode(file_bytes).decode("utf-8")

    name = (filename or "").lower()
    is_pdf = (content_type == "application/pdf") or name.endswith(".pdf")
    if is_pdf:
        media = {"type": "document",
                 "source": {"type": "base64", "media_type": "application/pdf", "data": b64}}
    else:
        mt = content_type if (content_type or "").startswith("image/") else "image/png"
        media = {"type": "image", "source": {"type": "base64", "media_type": mt, "data": b64}}

    client = anthropic.Anthropic(api_key=key)
    msg = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        thinking={"type": "adaptive"},   # helps interpret messy handwriting
        messages=[{"role": "user", "content": [media, {"type": "text", "text": prompt}]}],
    )
    text = "".join(b.text for b in msg.content if b.type == "text")
    parsed = _extract_json(text)
    return _to_job(parsed, index), text
