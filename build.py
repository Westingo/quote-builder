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
    return {"qty": qty, "text": _terminate(text)}


def resolve_codes(index, codes, section):
    """N/W/E lists -> [description, ...]. Accepts bare strings or {code,...}."""
    out = []
    sheet = NWE_SHEET[section]
    for c in codes or []:
        if isinstance(c, dict):
            code, fills = c.get("code"), c.get("fills")
            if "text" in c:
                out.append(str(c["text"]))
                continue
        else:
            code, fills = c, None
        item, _ = lookup(index, code, sheet)
        out.append(_fill_blanks(item.get("description", ""), fills))
    return out


# ----------------------------------------------------------------------------
# assemble normalized doc
# ----------------------------------------------------------------------------
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
            "lines": [resolve_line(index, ln) for ln in g.get("lines", [])],
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
        "options": job.get("options", []),
        "notes": resolve_codes(index, job.get("notes"), "note"),
        "warranties": resolve_codes(index, job.get("warranties"), "warranty"),
        "exclusions": resolve_codes(index, job.get("exclusions"), "exclusion"),
        "total": job.get("total"),
    }
    return doc


def _slug_outfile(jobdir, job):
    p = job.get("proposal", {})
    cust = (p.get("for") or "proposal").replace("/", "-")
    date = (p.get("date") or "").replace("/", ".")
    name = f"Proposal - {cust}" + (f" - {date}" if date else "") + ".docx"
    return os.path.join(jobdir, name)


def main(jobdir):
    jobdir = os.path.abspath(jobdir)
    with open(os.path.join(jobdir, "job.yaml"), encoding="utf-8") as f:
        job = yaml.safe_load(f)
    data, index = load_codes()
    doc = build_doc(job, data, index)
    out = _slug_outfile(jobdir, job)
    proposal.build_proposal(doc, out)
    print(f"wrote {out}")
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python build.py jobs/<slug>")
        sys.exit(1)
    main(sys.argv[1])
