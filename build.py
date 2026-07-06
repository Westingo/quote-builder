"""
build.py — expand a job's shortcut codes into a finished Metro proposal .docx.

    python build.py jobs/<slug>          # reads jobs/<slug>/job.yaml

Loads codes.yaml (the dictionary), resolves every code a job references to its
canonical Metro sentence, and renders the branded document via proposal.py.

A gate scope line may be either:
    { code: "6",  qty: 1 }                       # looked up in the dictionary
    { code: "15", qty: 1, fills: ["24'","8'"] }  # fill the _ blanks in order
    { code: "3",  qty: 1, note: "With rebar ..." }  # append "— note"
    { text: "24' vertical pivot gate ...", qty: 1 } # verbatim (not in dict)
qty omitted/null renders the no-count "—" marker instead of "N)".
"""
import os
import re
import sys

import yaml

import proposal

HERE = os.path.dirname(os.path.abspath(__file__))
CODES = os.path.join(HERE, "codes.yaml")

# N/W/E sheets hold the boilerplate; everything else is scope.
NWE_SHEET = {"note": "N", "warranty": "W", "exclusion": "E"}


# ----------------------------------------------------------------------------
# dictionary
# ----------------------------------------------------------------------------
def load_codes():
    with open(CODES, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    index = {}            # code -> list of (sheet, item)
    for sheet, items in data.items():
        for it in items:
            index.setdefault(str(it["code"]), []).append((sheet, it))
    return data, index


def lookup(index, code, sheet=None):
    """Resolve a code to its item dict. Prefer an explicit sheet, then a unique
    match, then the first scope-section match. Returns (item, sheet) or raises."""
    rows = index.get(str(code))
    if not rows:
        raise KeyError(f"code {code!r} not found in codes.yaml")
    if sheet:
        for s, it in rows:
            if s == sheet:
                return it, s
        raise KeyError(f"code {code!r} not found on sheet {sheet!r}")
    if len(rows) == 1:
        return rows[0][1], rows[0][0]
    scope = [(s, it) for s, it in rows if it.get("section") == "scope"]
    pick = (scope or rows)[0]
    return pick[1], pick[0]


def _fill_blanks(text, fills):
    """Replace successive runs of underscores with the provided values."""
    if not fills:
        return text
    it = iter(fills)

    def repl(_m):
        try:
            return str(next(it))
        except StopIteration:
            return _m.group(0)
    return re.sub(r"_+", repl, text)


def _terminate(text):
    """Code-derived lines get a closing period like the sample proposal."""
    t = text.rstrip()
    if t and t[-1] not in ".!?:":
        t += "."
    return t


def _norm_label(v):
    """Normalize a row label (Install/Supply/Other) to print with a trailing colon."""
    v = str(v or "").strip()
    return v if (not v or v.endswith(":")) else v + ":"


def resolve_line(index, line):
    """A gate scope line -> {qty, text}."""
    qty = line.get("qty")
    if "text" in line and line["text"] is not None:
        text = str(line["text"])
    else:
        item, _ = lookup(index, line["code"], line.get("sheet"))
        text = item.get("description", "")
        text = _fill_blanks(text, line.get("fills"))
    if line.get("note"):
        text = _terminate(text) + " — " + str(line["note"])
    res = {"qty": qty, "text": _terminate(text)}
    if line.get("sub"):                        # indented "— text" sub-note
        res["sub"] = True
    if line.get("atqty"):                      # note starting at the qty/number column
        res["atqty"] = True
    if line.get("leftnote"):                   # note starting at the far-left label column
        res["leftnote"] = True
    if "label" in line:                        # explicit Install/Supply/Other (or "")
        res["label"] = _norm_label(line["label"])
    if line.get("amount") not in (None, ""):   # per-item price/note in AMOUNT col
        res["amount"] = line["amount"]
        if line.get("deduct"):
            res["deduct"] = True
    return res


def resolve_lines(index, lines):
    """Resolve a location/option line list: priced notes pass through; everything
    else is a coded or free-text scope line."""
    out = []
    for ln in lines or []:
        if isinstance(ln, dict) and ln.get("amount_note") is not None:
            out.append({"amount_note": ln["amount_note"],
                        "amount": ln.get("amount"), "deduct": ln.get("deduct")})
        else:
            out.append(resolve_line(index, ln))
    return out


# N/W/E code prefixes — salesmen write the bare Copy_Paste code (34, 4a, 8c);
# the dictionary stores them prefixed by section (N34, EX4A, EX8C).
NWE_PREFIX = {"note": "N", "warranty": "W", "exclusion": "EX"}


def find_nwe(index, code, section):
    """Resolve an N/W/E code tolerantly: try it as written, then add the section
    prefix (note->N, warranty->W, exclusion->EX), case-insensitively. So '34'
    finds 'N34', '4a' finds 'EX4A', 'W2'/'w2'/'2' all find 'W2'. Returns the item
    dict or None."""
    sheet, pre = NWE_SHEET[section], NWE_PREFIX[section]
    raw = str(code).strip()
    cands = [raw, raw.upper(), pre + raw, pre + raw.upper()]
    # build an upper-cased view of the index once per section is overkill; just
    # scan candidates against exact keys, then fall back to a case-insensitive pass
    for cand in cands:
        for s, it in index.get(cand, []):
            if s == sheet:
                return it
    want = {c.upper() for c in cands}
    for key, rows in index.items():
        if key.upper() in want:
            for s, it in rows:
                if s == sheet:
                    return it
    return None


def resolve_codes(index, codes, section):
    """N/W/E lists -> [description, ...]. Accepts bare strings or {code,...}."""
    out = []
    for c in codes or []:
        if isinstance(c, dict):
            code, fills = c.get("code"), c.get("fills")
            if "text" in c:
                out.append(str(c["text"]))
                continue
        else:
            code, fills = c, None
        item = find_nwe(index, code, section)
        if item is None:                       # unknown code: keep it, don't crash
            out.append(str(code))
        else:
            out.append(_fill_blanks(item.get("description", ""), fills))
    return out


# ----------------------------------------------------------------------------
# assemble normalized doc
# ----------------------------------------------------------------------------
def process_options(index, options):
    """Resolve coded scope lines inside detailed option blocks; pass simple/block
    options through unchanged."""
    out = []
    for opt in options or []:
        if isinstance(opt, dict) and opt.get("lines") is not None and "kind" not in opt:
            lines = []
            for orig in opt["lines"]:
                if orig.get("amount_note") is not None:
                    lines.append({"amount_note": orig["amount_note"],
                                  "amount": orig.get("amount"), "deduct": orig.get("deduct")})
                    continue
                res = resolve_line(index, orig)
                if orig.get("label"):
                    res["label"] = _norm_label(orig["label"])
                if orig.get("bold"):
                    res["bold"] = True
                lines.append(res)
            if (lines and not lines[0].get("label")
                    and lines[0].get("qty") not in (None, 0, "")):
                lines[0]["label"] = "Install:"
            out.append({"title": opt.get("title", ""), "lines": lines,
                        "amount": opt.get("amount"), "deduct": opt.get("deduct"),
                        "note": opt.get("note")})
        else:
            out.append(opt)
    return out


def build_doc(job, data, index):
    p = job.get("proposal", {})

    def desc(code, sheet=None):
        return lookup(index, code, sheet)[0].get("description", "")

    # tariff notes default to N38/N39 unless the job overrides
    tariff = p.get("tariff_notes")
    if tariff is None:
        tariff = [desc("N38", "N"), desc("N39", "N")]

    intro = p.get("intro") or desc("INTRO1", "Other")

    gates = []
    for g in job.get("gates", []):
        gates.append({
            "title": g["title"],
            "lines": resolve_lines(index, g.get("lines", [])),
        })

    doc = {
        "header": {
            "for": p.get("for", ""),
            "address": p.get("address", ""),
            "phone": p.get("phone", ""),
            "email": p.get("email", ""),
            "date": p.get("date", ""),
            "terms": p.get("terms", ""),
            "job_address": p.get("job_address", ""),
            "attention": p.get("attention", ""),
            "bid_number": p.get("bid_number", ""),
            "submitted_by": p.get("submitted_by", ""),
            # Metro's fixed license numbers — never change, not overridable
            "ccb": "46091",
            "cc": "METROOD121MJ",
            "job_footer": p.get("job_footer", ""),
        },
        "tariff_notes": tariff,
        "intro": intro,
        "gate_summary": job.get("gate_summary", []),
        "gates": gates,
        "options_title": job.get("options_title", proposal.DEFAULT_OPTIONS_TITLE),
        "options": process_options(index, job.get("options")),
        "notes": resolve_codes(index, job.get("notes"), "note"),
        "warranties": resolve_codes(index, job.get("warranties"), "warranty"),
        "exclusions": resolve_codes(index, job.get("exclusions"), "exclusion"),
        "total": job.get("total"),
    }
    return doc


def _slug_outfile(jobdir, job):
    """Consistent output name every time: '<customer> <bid #> <date>.docx'
    (job name = the 'For' customer field). Empty parts are skipped; characters
    illegal in Windows filenames are replaced with '-'."""
    p = job.get("proposal", {})

    def safe(v):
        v = str(v or "").strip()
        for ch in '\\/:*?"<>|':
            v = v.replace(ch, "-")
        return v.strip()

    name = safe(p.get("for")) or "Proposal"
    bid = safe(p.get("bid_number"))
    date = safe(str(p.get("date") or "").replace("/", "."))
    parts = [name] + [x for x in (bid, date) if x]
    return os.path.join(jobdir, " ".join(parts) + ".docx")


def main(jobdir):
    jobdir = os.path.abspath(jobdir)
    with open(os.path.join(jobdir, "job.yaml"), encoding="utf-8") as f:
        job = yaml.safe_load(f)
    data, index = load_codes()
    doc = build_doc(job, data, index)
    out = _slug_outfile(jobdir, job)

    # If the proposal is open in Word (the usual cause of a save failure), the
    # file is locked — write to a numbered name instead so the build still works.
    base, ext = os.path.splitext(out)
    candidates = [out] + [f"{base} ({i}){ext}" for i in range(2, 50)]
    for i, cand in enumerate(candidates):
        try:
            proposal.build_proposal(doc, cand)
            if i:
                print(f"note: '{os.path.basename(out)}' was open in Word, "
                      f"so this was saved as '{os.path.basename(cand)}'. "
                      f"Close the old one to reuse the main name.")
            print(f"wrote {cand}")
            return cand
        except PermissionError:
            continue
    raise PermissionError(
        f"Could not save the proposal — '{os.path.basename(out)}' (and its "
        f"numbered copies) are open in Word. Close them and build again.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python build.py jobs/<slug>")
        sys.exit(1)
    main(sys.argv[1])
