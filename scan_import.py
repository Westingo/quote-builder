"""
scan_import.py — turn a scanned sheet / quote / email into a draft job.

Sends the uploaded image or PDF to Claude's vision API along with the code
dictionary, gets back a structured extraction, and maps it into our job.yaml
shape (resolving each shortcut code to its sheet). The result is a DRAFT for the
salesman to review in the form — handwriting especially will need corrections.

API key: ANTHROPIC_API_KEY env var, or an `api_key.txt` file next to this script.
Model: claude-fable-5 by default (override with QUOTE_IMPORT_MODEL).
"""
import os
import re
import json
import base64

import build

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.environ.get("QUOTE_IMPORT_MODEL", "claude-fable-5")
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
      "lines":[
        {{"code":"6","qty":1}},
        {{"text":"Ground rod","qty":1}},
        {{"text":"Reflective tape on both sides","qty":null}},
        {{"text":"HID proximity cards","qty":300,"amount":"$1,050.00"}},
        {{"text":"New enclosure","qty":1,"amount":"by others"}},
        {{"text":"Gooseneck pedestal","qty":1,"amount":"$1,071.00","deduct":true}},
        {{"amount_note":"Total to Install all Options (minus monthly fees)","amount":"$29,729.00"}}
      ]}}
  ],
  "notes": ["N4","N6"], "warranties": ["W2"], "exclusions": ["EX1","EX6"],
  "total": "29,729.00"
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
- PRICES GO IN THE RIGHT COLUMN. Put every dollar amount, price, or percent on a \
line into that line's "amount" field — it prints in the right-hand AMOUNT column. \
NEVER write a price inside "text"; "text" is only the description for the left \
column. "amount" may be a dollar value ("$1,050.00"), a percent ("15%"), or a \
short note ("by others", "included", "TBD").
- A deduct or credit (shown in <angle brackets>, or labeled "Deduct"/"Credit"/ \
"<...>") -> set "deduct": true and put the number in "amount".
- A line that is ONLY a priced label or running total with no scope item (e.g. \
"Total to Install all Options ... $29,729.00", "Not-To-Exceed Total: $540", \
"Cost Per Gate $390") -> use {{"amount_note":"<the label text>","amount":"<the price>"}}.
- notes / warranties / exclusions are usually listed as codes after "N:", "W:", \
"E:" or "Ex:". Map to code keys from the N, W, E sheets. If written out in full, \
return the text instead of a code.
- "total" is the single grand TOTAL for the whole proposal, if shown.
- Leave a field "" or null when it is not present. Do not invent values.

DICTIONARY (code | sheet | description):
{dictionary}
"""


def _extract_json(text):
    m = re.search(r"\{.*\}", text.strip(), re.S)
    return json.loads(m.group(0) if m else text)


def _nwe_items(values, index, section):
    """Pass valid codes through as strings (bare or prefixed); wrap free text as
    {text: ...}."""
    out = []
    for v in values or []:
        s = str(v).strip()
        if not s:
            continue
        if build.find_nwe(index, s, section) is not None:
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
            amount = ln.get("amount")
            deduct = bool(ln.get("deduct"))
            code = str(ln.get("code") or "").strip()
            text = str(ln.get("text") or "").strip()
            # a priced label / running total: right-aligned label + price in the
            # AMOUNT column (no scope item of its own)
            if ln.get("amount_note") is not None or (
                    amount not in (None, "") and not code and not text):
                lines.append({"amount_note": str(ln.get("amount_note") or "").strip(),
                              "amount": amount, "deduct": deduct})
                continue
            rows = index.get(code) if code else None
            if rows:
                row = {"code": code, "sheet": rows[0][0], "qty": ln.get("qty")}
            else:
                txt = text or code
                if not txt:
                    continue
                row = {"text": txt, "qty": ln.get("qty")}
            if amount not in (None, ""):   # price/percent/note -> right-hand column
                row["amount"] = amount
                if deduct:
                    row["deduct"] = True
            lines.append(row)
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

    # Fable 5's always-on thinking accepts {"type": "adaptive"}; it also helps
    # interpret messy handwriting. Fable 5's safety classifiers can occasionally
    # decline a benign request — this is access-control / gate-security work,
    # adjacent to the "cyber" category — so opt into a server-side fallback:
    # a false-positive refusal is transparently re-served by Opus 4.8 inside the
    # same call instead of failing the scan. (Skipped if MODEL is already 4.8.)
    kwargs = dict(
        model=MODEL,
        max_tokens=8000,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": [media, {"type": "text", "text": prompt}]}],
    )
    if MODEL != "claude-opus-4-8":
        msg = client.beta.messages.create(
            betas=["server-side-fallback-2026-06-01"],
            fallbacks=[{"model": "claude-opus-4-8"}],
            **kwargs,
        )
    else:
        msg = client.messages.create(**kwargs)

    if msg.stop_reason == "refusal":
        raise RuntimeError(
            "Claude declined to read this document (a safety refusal). This is "
            "usually a false positive on access-control content — try a cleaner "
            "scan, or enter the codes by hand.")

    text = "".join(b.text for b in msg.content if b.type == "text")
    parsed = _extract_json(text)
    return _to_job(parsed, index), text
