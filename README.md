# Metro Access Control — Quote / Proposal Builder

Turns a salesman's **shortcut codes** into a finished, branded Metro **PROPOSAL
`.docx`** — the replacement for the old Publisher + Copy_Paste workflow.

Codes in → finished proposal out. It does **not** price anything; the salesman
fills the TOTAL and option amounts.

---

## Run it (standalone — any Windows machine)

1. Download / clone this folder from GitHub.
2. Double-click **`run.bat`**. The first run builds a private environment
   (~1 min); after that it opens in seconds in its own window.
   - Needs **Python 3** — if it's missing, `run.bat` tells you how to install it
     (tick *“Add python.exe to PATH”*).
3. (Optional) Double-click **`Create Desktop Shortcut.bat`** for a clickable
   *Metro Quote Builder* icon.
4. Close the window — or double-click **`stop.bat`** — to shut it down.

No server, no PM2. It runs locally on `127.0.0.1:8485` inside the app window.

---

## Use it

In the window:
1. Fill the **proposal header** (customer, address, date, job address, bid #, …).
2. Add the **Install summary** lines (the centered list up top).
3. Add **gate locations**; for each, add scope lines two ways:
   - **+ code** — type a code (or pick from the **Code Picker** on the right);
     it's looked up in the dictionary and expanded to the full Metro sentence.
   - **+ text** — type a line that isn't in the dictionary (verbatim).
   - Lines flagged with blanks (`_`) get a fill-in box (e.g. gate size/finish).
4. Add **Options** (priced add/deduct lines, plus the Low-Voltage block).
5. Tick **Notes / Warranties / Exclusions** (N / W / EX codes) or add free text.
6. **Build Proposal** → opens the finished `.docx` (saved under `jobs/<slug>/`).

Quotes get revised, so the output is an **editable Word doc**, not a flat PDF.
*Load saved…* re-opens a prior job to revise it.

---

## Import from a scan (AI)

In the window, **Start from a Scan** lets you upload a scanned sales sheet,
quote, or email (image or PDF). It sends the scan to Claude's vision API, which
reads it — including handwriting — and pre-fills a **draft** quote you then
review and fix before building. Great for typed docs/emails; messy handwriting
will need corrections.

This needs an **Anthropic API key** and internet. Each scan costs roughly
$0.05–0.15. Set the key one of two ways:
- environment variable `ANTHROPIC_API_KEY`, or
- put the key in a file named **`api_key.txt`** next to the app (gitignored).

Model defaults to `claude-opus-4-8`; override with `QUOTE_IMPORT_MODEL`
(e.g. `claude-haiku-4-5` for lower cost). The scan is sent to Anthropic to be read.

---

## Command line (optional)

```
python new_job.py "Town & Country Fence"   # scaffold jobs/town-country-fence/job.yaml
python build.py jobs/town-country-fence    # build the .docx
python app.py                              # browser UI at http://localhost:8485
```

A worked example lives in [`jobs/hoodland-tc/job.yaml`](jobs/hoodland-tc/job.yaml)
— it reproduces a real Metro proposal and shows every line shape (code lookup,
fills, note, free text, options block, deduct, N/W/E).

---

## The dictionary

`codes.yaml` is the shortcut dictionary (493 codes across 14 sheets),
generated from the master workbook:

```
python build_codes.py Copy_Paste.xlsx
```

Regenerate it whenever the workbook changes. Cost/labor columns are salesman
reference only — the tool never does pricing math.

> **Note:** the current workbook is missing some everyday gate items (ground
> rod, cold weather package, mat heater, photo eye, gate yoke, reflective tape,
> Group 24 batteries) and the AutoGate vertical-pivot gate. Type those as
> free-text lines until they're added to the workbook.

---

## Files

| file | what |
|------|------|
| `run.bat` / `stop.bat` / `Create Desktop Shortcut.bat` | launchers |
| `desktop.py` | native-window app (pywebview) — the shortcut target |
| `app.py` | FastAPI web UI (also runs headless in a browser) |
| `build.py` | core builder: `job.yaml` + `codes.yaml` → `.docx` |
| `proposal.py` / `docx_utils.py` | the branded document layout |
| `codes.yaml` / `build_codes.py` | the dictionary and its generator |
| `static/index.html` | the single-page UI (vanilla JS) |
| `jobs/<slug>/job.yaml` | per-job input; built `.docx` lands beside it |
