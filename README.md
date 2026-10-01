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

### Updates on other machines

`run.bat` checks GitHub for updates before opening the app. The desktop shortcut
created by `Create Desktop Shortcut.bat` runs this launcher minimized as well.
For an existing installation, run `git pull` once, then double-click
`Create Desktop Shortcut.bat` to replace the old shortcut that bypassed updates.

Each machine needs Git installed and a Git clone of this repository (a downloaded
ZIP cannot update through Git). GitHub access must already work on that machine.
Save your work and close the app before relaunching to load an update. Running
apps do not restart themselves when changes are pushed. If the update fails,
the launcher uses the installed version. Updates use `git pull --ff-only` and
do not reset local changes. Personal quotes and the local API key stay local.

---

## Use it

The Code Picker reads products from the live [Copy Paste Google Sheet](https://docs.google.com/spreadsheets/d/1_JJQ8S-ZwqUzmRewfjesz84QV0dEf6P52bHjd_BLdOo/edit).
It checks on startup and every minute while the app is open. Use **Refresh
products** to check immediately; the status below it shows the last successful
sync. Google's export may take a little time to reflect a just-saved edit.

Add products to the existing tabs with a unique CODE and a DESCRIPTION, keeping
the tab names and header columns. The 14 dictionary tabs are imported; calculator
and reference tabs remain excluded. The app reads the sheet without changing it
or its sharing settings. The sheet currently permits downloading without a
Google sign-in; if that access changes, sync will show a warning.

Products are validated before replacing the local offline cache. If the sheet
is unavailable or malformed, the app keeps the last successful copy (or the
bundled list on a first offline run). No GitHub update is needed for product
changes. Items already added to a quote keep their wording, including custom
edits; remove and re-add an item to use its latest description. Newly saved
quotes preserve the displayed wording when reopened. Older quotes without
saved wording still resolve their codes from the current list when loaded.

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

The **Live preview** on the right shows the actual proposal pages rendered by
**Microsoft Word**, including the logo, borders, headers, footers, spacing,
and page breaks. Desktop Microsoft Word must be installed and activated on
that machine. After updating, run **run.bat** once to install preview components.

The preview updates a few seconds after you pause editing. While it renders,
the previous pages are dimmed and marked as pending. Click **Full screen** to
expand the pages; **Close preview** or **Esc** returns to editing. Preview
copies are temporary and do not save or overwrite customer jobs. Pages show
Word's printed appearance (white paper), regardless of Word's dark display mode.

The **WE PROPOSE TO FURNISH THE FOLLOWING / AMOUNT** band appears on the first
page only. Later pages continue the quote beneath the customer header; the
customer header and footer still repeat on every page.

---

## Move an editable quote between computers

### Adjust formatting before exporting

Use **Format** beside a location item, note, or detailed-option item to edit
multiline text, set bold/underline, adjust font size and spacing, or keep the
line with the next item. **Price alignment** positions its amount at the top,
middle, or bottom of the corresponding text.

**Text position** keeps the existing label/quantity columns by default. The
text-only choices start at the left edge, quantity column, or description
column, hiding that line's label and quantity without deleting them. Choose
where wrapped lines align independently. **Reset formatting** restores the
default layout without changing the wording.

Use **Section format** on a location or detailed option to start a new page,
keep the section together when it fits, or adjust item typography and spacing
for the whole section. Individual line settings override section defaults.
All these settings appear in the live preview and survive PDF transfers and
backups. Headers, footers, and the opening band keep the standard Metro style.

### Transfer a finished quote

The easiest way is **Build PDF** in the transfer panel. It saves the Word
proposal and creates a PDF with the editable `.metroquote` data attached inside
it. Send that single PDF, then choose **Import PDF / quote…** on the other
computer. The visible PDF pages use the same Microsoft Word rendering as the
preview. Desktop Microsoft Word must be installed and activated to build PDFs.

Only PDFs made with **Build PDF** carry the editable quote. Printing to PDF,
flattening, or processing a PDF with tools that remove attachments can discard
that data. Changes made later in a PDF editor do not update the embedded quote.
If the data is missing, import explains this; it does not silently run paid AI.
Older PDFs can still use **Start from a Scan** for a draft requiring review.

You can also transfer the editable file separately:

1. On Liv's computer, open the quote (use **Load saved…** for an older quote)
   and click **Export quote**. Save the `.metroquote` file.
2. Send that file by email, shared folder, or USB.
3. On your computer, click **Import PDF / quote…** and choose the file. It is saved as
   a separate local copy and opens in the editor, ready for changes.
4. Click **Build Proposal** after editing to save the changes and create Word output.

Both computers need a version with these buttons. Export includes the current
form, even before building: customer details, displayed product wording,
quantities, options, amounts, notes, warranties, exclusions, and their order.
Import uses the same proposal builder and layout as a locally created quote.
Repeated imports create separate copies and do not overwrite existing jobs.
This transfer runs locally and needs no AI key or internet connection.

Send the `.metroquote` file for editing in Quote Builder. Edits made separately
in Word or PDF are not included; make those changes in Quote Builder before
exporting. Export any unsaved work before importing another quote.

### Automatic backups

Every **Build Proposal**, **Build PDF**, and successful quote import saves a new
dated `.metroquote` copy in **Metro Quote Backups** under your Windows user folder
(outside the app folder). Click **Backup folder** to open it in the desktop app;
the browser version displays its path. Import any backup to recover a separate
editable copy. Earlier backups are retained, including when a later Word/PDF
build fails. If a backup cannot be written, the app displays a warning while
keeping the local saved quote.

These are local recovery copies, not automatic cross-computer sync. To use an
existing shared or synced folder, set `QUOTE_BACKUP_DIR` to that folder's full
path before launching the app. Backup filenames use UTC timestamps and unique
suffixes so saves from different computers can coexist. Unsaved typing is not
backed up until you build or import a quote.

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
