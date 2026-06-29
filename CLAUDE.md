# CLAUDE.md — Metro Access Control Quote / Proposal Builder

Build handoff for **Claude Code**. Owner: Westin, lead technician / access
control integrator at Metro Access Control (Portland, OR). June 2026.

> **BUILD MODE — write the application code, move fast, build it.** The
> salesperson who produced every Metro quote left with no notice; this tool
> replaces them and is needed now. (This supersedes any earlier *teacher-mode*
> handoff for the quote project.) Westin's working style still applies: a
> sentence or two of architecture before each chunk, incremental checkpoints he
> can verify, and blunt, direct pushback when his direction is wrong — but you
> are the implementer here, not a tutor.

---

## 0. What's in this package

Drop all of these into the repo root (`quote-tool/`):

| file | what it is | state |
|------|------------|-------|
| `CLAUDE.md` | this handoff | — |
| `codes.yaml` | the shortcut dictionary — 493 codes | **DONE, generated** |
| `build_codes.py` | regenerates `codes.yaml` from the workbook | **DONE** |
| `Copy_Paste.xlsx` | Metro master workbook (source of the dictionary) | provided by Westin |
| a finished Metro proposal | the visual target for the `.docx` template | provided by Westin |

### Status at a glance

- **Done:** the dictionary (`codes.yaml`) and its generator (`build_codes.py`).
  The hard data problem is already solved — do **not** rebuild it from Publisher.
- **To build:** (1) the Metro proposal **`.docx` template**, (2) `build.py`
  (codes -> filled proposal), (3) the `app.py` + `static/index.html` web UI.
  The template is the biggest remaining task — start there.

---

## 1. What this is

A **proposal/quote generator** that replaces a manual workflow built on
**Microsoft Publisher + a "Copy_Paste" spreadsheet of shortcut codes**:

1. A salesman submits a sheet of **shortcut codes** — e.g. `6 23 15B`, grouped
   under gate-location headers, with quantities.
2. The old owner looked each code up in the workbook and pasted the matching
   **DESCRIPTION** into Publisher (`6` -> "Sawcut vehicle presence loop - Keeps
   gate from closing if vehicle is present").
3. Out came a formatted, branded **Metro PROPOSAL** document.

This tool does steps 2-3 automatically: **codes in -> finished proposal out.**

### What this tool does NOT do

**It does not price anything.** Pricing is figured by the salesmen — no markup
math, no cost rollup, no margins. The `COST`/`LABOR` columns in the source are
salesman *reference* only and are frequently freeform text
(`"175 plus verizon charge of $30 per month"`, `"Charge $56"`), so never assume
they are clean numbers. The only money on the page is a salesman-entered TOTAL
plus a few option adders/deducts. **Do not build a pricing engine.**

---

## 2. The dictionary: `codes.yaml` (already built)

Generated from `Copy_Paste.xlsx`: **493 codes across 14 sheets**, each mapping a
shortcut code to its canonical Metro sentence plus model/cost/labor/category.

| sheet | section | items |  | sheet | section | items |
|-------|---------|-------|--|-------|---------|-------|
| Operators | scope | 21 |  | Storage | scope | 10 |
| Gate Accessories | scope | 64 |  | Brivo | scope | 29 |
| Ironwork | scope | 16 |  | Access | scope | 75 |
| Readers | scope | 34 |  | Other | scope | 23 |
| CCTV | scope | 61 |  | **N** (Notes) | note | 45 |
| Remotes | scope | 13 |  | **W** (Warranties) | warranty | 20 |
| Door Hardware | scope | 58 |  | **E** (Exclusions) | exclusion | 24 |

**Key structural fact:** the proposal's **Notes / Warranties / Exclusions are
not static boilerplate** — they are coded too (`N1`, `W1`, `EX1`...) and selected
per job from the `N`/`W`/`E` sheets. The `.docx` template holds only the branded
chrome; even the boilerplate body is assembled from `codes.yaml`. Expect a
default set of N/W/E codes on essentially every proposal (Westin to confirm).

**Reference sheets excluded from the dictionary:** `MyQ Price Tool`,
`Labor Rates`, `Do not change` are salesman calculators / backing data. Leave
them alone for v1.

Regenerate any time the workbook changes: `python build_codes.py Copy_Paste.xlsx`.

---

## 3. Relationship to the existing `submittal-tool`

Direct **sister project**, same machine, same patterns — study it first and copy
its conventions: `app.py` = FastAPI web UI; `static/index.html` = single-page
vanilla-JS form (no build step); a YAML library + per-job YAML; Metro title-block
styling; PM2 deploy. Difference: submittal assembles **PDFs**; this one expands
**text codes** into a **`.docx` proposal**. Keep the two libraries separate.

---

## 4. Architecture decisions (made — flip with Westin if he disagrees)

- **Output = editable `.docx`.** Quotes get revised constantly (the sample has an
  "Addendum #1 / Revised 6.30"); a flat PDF would be a downgrade from Publisher.
  Generate from a **Metro proposal template `.docx`** that holds every static
  element, filling only variable regions. Library: **`python-docx`**. Optional
  PDF export later via Word / `docx2pdf`; not required for v1.
- **Stack:** FastAPI + uvicorn + `python-docx` + `pyyaml` + `openpyxl` +
  `static/index.html`. Port **8485** (submittal uses 8484).
- **Template approach is the heart of it.** All branded chrome (header box, the
  "WE PROPOSE TO FURNISH" band, tariff notes, signature block, CCB/CC numbers,
  Metro address, "valid for 30 days" fine print) lives in the template `.docx`.
  Everything else — header fields, per-gate scope, options, and the N/W/E
  boilerplate — is assembled from `codes.yaml`.

---

## 5. File layout

```
quote-tool/
  app.py                  FastAPI web UI (port 8485)
  build.py                Core builder. CLI: python build.py jobs/<slug>
  new_job.py              Scaffolds jobs/<slug>/ from jobs/_template/
  codes.yaml              THE DICTIONARY (493 codes — already generated)
  build_codes.py          Regenerates codes.yaml from Copy_Paste.xlsx
  Copy_Paste.xlsx         Master workbook (source of truth for codes)
  templates/
    proposal-template.docx  Branded Metro proposal w/ placeholder tokens
  static/index.html       Single-page UI (vanilla JS)
  jobs/
    _template/job.yaml
    <slug>/job.yaml
  requirements.txt        fastapi uvicorn python-docx pyyaml python-multipart openpyxl
  .gitignore
  README.md
```

---

## 6. `codes.yaml` schema (real, as generated)

Top level is keyed by source sheet; each value is a list of items:

```yaml
Gate Accessories:
  - code: "6"
    description: "Sawcut vehicle presence loop – Keeps gate from closing if vehicle is present"
    category: "LOOPS AND DETECTORS"   # ALL-CAPS separator the code sat under
    section: scope                    # scope | note | warranty | exclusion
    sheet: "Gate Accessories"
  - code: "6A"
    description: "Preformed vehicle presence loop to be set at time of asphalt pour"
    cost: 165                         # reference only; may be a freeform string
    category: "LOOPS AND DETECTORS"
    section: scope
    sheet: "Gate Accessories"
```

Builder notes:
- **`code`** is the lookup key (string). Numeric codes were coerced from Excel
  floats: `6.0 -> "6"`, `15.0 -> "15"`. Letter variants (`6A`, `15B`, `N2A`,
  `EX4A`) are distinct keys. Codes are unique *within* a sheet; if you build one
  global lookup, namespace by sheet or verify cross-sheet uniqueness first.
- **`description`** renders verbatim and contains en-dashes (`–`), smart quotes,
  `×`, etc. — **UTF-8 everywhere** (see §10).
- **Parameterized lines:** many descriptions have fill-in blanks (`"_ × _"`,
  `"___ finish"`, gate size/model/voltage). Support simple field substitution
  from the gate definition. Not yet tokenized — agree a `{field}` convention with
  Westin (see §12) and apply it in `build_codes.py`.
- **`variants`** = sub-rows that hung under a code with no code of their own
  (e.g. Operators `LA500` -> `{model: DBL, cost: 2596, labor: 12}`).
- **`cost` / `labor`** are reference only — do not compute with them.
- **`notes`** = ad-hoc trailing-column text from the sheet.

**Rendering a scope line:** `<qty>) <description>` for counted items;
`— <description>` for no-count items (e.g. reflective tape). Qty comes from the
job file.

---

## 7. `job.yaml` — per-job input

```yaml
proposal:
  for: "Town & Country Fence of Oregon"
  address: "PO Box 443; Clackamas, OR 97015"
  phone: "503.655.2055"
  email: "Troy@tcfence.us"
  attention: "Troy Deming"
  job_address: "Hoodland Fire District Station #74\n25400 E Salmon River Rd; Welches, OR 97067"
  date: "06/26/2026"
  bid_number: "G20260319"
  submitted_by: ""                  # current salesperson

gate_summary:                        # centered "Install:" list at the top
  - "(1) 24' x 8' Vertical Pivot Gate"
  - "(1) 30' x 8' Double Vertical Pivot Gate"

gates:
  - title: "Work to be Done at 24' Gate Location:"
    fields: { size: "24", model: "VPG2490", voltage: "120V 1PH" }
    lines:
      - { code: "6",  qty: 1 }       # qty overrides the item default
      - { code: "23", qty: 1 }

options: [ ]                          # selected option codes (+ optional amount)
notes:    [ "N1", "N2" ]             # codes from the N sheet
warranties: [ "W2", "W6" ]           # codes from the W sheet
exclusions: [ "EX1", "EX4" ]         # codes from the E sheet
total: null                          # salesman fills; tool leaves blank
```

---

## 8. Proposal document structure (order on the page)

Template holds the static chrome; tool fills the rest.

1. **Header box** — PROPOSAL title, "Pg X of Y", Metro logo; For/Address/Phone/
   Date/Terms/Email/Job Address/Attention. *(tool fills fields)*
2. **"WE PROPOSE TO FURNISH THE FOLLOWING" | "AMOUNT"** band + tariff notes. *(static)*
3. **"Metro Access will provide all labor, materials, equipment, and
   supervision for the following work:"** + centered `Install:` `gate_summary`. *(tool)*
4. **Per-gate section(s):** `Work to be Done at <X> Gate Location:` + expanded
   scope lines (`<qty>) <text>` / `— <text>`). One block per gate. *(tool)*
5. **OPTIONS** — "Circle options chosen to be added to totals:" + selected option
   lines with amounts; deducts shown as `<$1,071.00>`. *(tool)*
6. **Notes (Cont.) / Warranties / Exclusions** — assembled from the job's
   `notes`/`warranties`/`exclusions` codes via the N/W/E sheets. *(tool)*
7. **Footer + signature + Metro address block + fine print.** *(static)*
8. **TOTAL** — blank unless `total` set. *(tool)*

---

## 9. FIRST TASKS

1. **`git init` immediately**, initial commit, `.gitignore` (ignore `jobs/*/`
   output `.docx`, `__pycache__`). The submittal project lost hours to version
   mixups for lack of this — do it first.
2. **Review `codes.yaml`** (already generated). Two judgment calls are reserved
   for Westin — do not guess them:
   - **Option flagging:** which scope codes are OPTION adders/deducts vs. base
     install (the `Other` sheet has an `O2` "OPTIONS" marker; some lines are
     deducts). Add an `is_option` / `is_deduct` flag where he confirms.
   - **Parameter tokens:** agree the `{field}` convention for fill-in blanks and
     the default-on N/W/E code set, then bake it into `build_codes.py`.
3. **Build `templates/proposal-template.docx`** from a finished Metro proposal:
   open it in Word, strip the variable text, keep the static chrome + styling,
   drop placeholder tokens (`{{for}}`, `{{gate_sections}}`, `{{options}}`,
   `{{notes}}`, `{{warranties}}`, `{{exclusions}}`, `{{total}}`). Confirm fonts and
   the boxed/table layout survive.
4. Render one gate from a hand-written `job.yaml` -> eyeball the `.docx` against
   the sample -> only then build the UI.

---

## 10. Hard-won constraints carried from `submittal-tool` (don't re-break)

- **Windows 11.** Use `python`, not `python3`.
- **UTF-8 everywhere.** Every `open()` needs `encoding="utf-8"` — the cp1252
  default crashes on `–`, `—`, `×`, and smart quotes, which are all over the
  descriptions.
- **OneDrive-synced Desktop path** causes file locks; prefer a repo path outside
  OneDrive, and if a `.docx` write fails it's usually Word/OneDrive holding it open.
- **PM2 deploy:** `pm2 start app.py --name quote-builder --interpreter python`.
- Keep the UI dependency-free (vanilla JS in `static/index.html`).

---

## 11. Build checkpoints (ordered)

1. Skeleton + `git init` + `requirements.txt` + `.gitignore`.
2. `codes.yaml` reviewed; `build_codes.py` re-runs clean from `Copy_Paste.xlsx`.
3. `templates/proposal-template.docx` with placeholder tokens.
4. `build.py`: load `job.yaml` + `codes.yaml`, expand one gate, fill template,
   write `jobs/<slug>/Proposal - <customer> - <date>.docx`.
5. Multi-gate + options + N/W/E + centered `Install:` summary + parameter fields.
6. `app.py` + `static/index.html`: enter header fields, add gates, tick codes per
   gate (check/uncheck + qty, like submittal's preset UI), pick options/N/W/E,
   Build -> download `.docx`.
7. `new_job.py`; README; PM2 notes.
8. **Later:** load a prior `job.yaml` to emit an "Addendum #N / Revised <date>";
   optional PDF export.

---

## 12. Open questions for Westin

- Which N/W/E codes are default-on for every proposal vs. picked per job?
- Within the scope sheets, which codes are OPTION adders / deducts (§8 step 5)?
- Standard option prices stored as defaults in `codes.yaml`, or entered fresh?
- One proposal per customer, or batch the same job to multiple fence-contractor
  customers at once (the sample shows Hoodland sent to both Town & Country and
  McDermott)?

---

## 13. Verification loop

```
python build.py jobs/<test-slug>      # must produce a .docx
# open it in Word, compare side-by-side with a real Metro proposal
python app.py                         # UI on http://localhost:8485
```
After any `codes.yaml` change: confirm it parses, every job-referenced code
exists, and a test job using the new/changed codes builds clean and reads
correctly against the sample.
