# Deploying the Quote Builder to other machines

The app is a **standalone Windows desktop app** — each machine runs its own local
copy. `run.bat` sets everything up on first launch. Distribution is a **private
GitHub repo** (it contains Metro's codes and pricing wording — keep it private).

---

## Set up on a new machine (one time, ~5 min)

1. **Install Python 3** (only needed once per machine):
   - Get it from <https://www.python.org/downloads/>
   - During setup, **tick "Add python.exe to PATH."**
   - *(If you skip this, `run.bat` will tell you exactly what to do.)*
2. **Get the app folder** onto the machine:
   - `git clone <your-private-repo-url>`  — *or* download the repo as a ZIP from
     GitHub and unzip it somewhere like `Desktop\Quotes\quote-tool`.
3. **Double-click `run.bat`.** First run takes ~1 minute (it builds a private
   environment and installs dependencies — needs internet this once). After that
   it opens in its own window in seconds.
4. **Double-click `Create Desktop Shortcut.bat`** for a clickable
   *Metro Quote Builder* icon.

That's it. Close the window (or `stop.bat`) to shut it down.

---

## Scan-import key (optional, per machine)

The "Start from a Scan" feature calls the Anthropic API and needs a key. It is
**never** stored in the repo. On any machine that should use scan import:

- Put the key in a file named **`api_key.txt`** in the app folder, **or**
- Set the `ANTHROPIC_API_KEY` environment variable.

The app works fine without it — scan import just won't be available. One key
shared across machines means shared Anthropic billing.

---

## Updating a machine to a new version

From the app folder:

```
git pull          (or: re-download the ZIP and replace the files)
run.bat
```

Saved quotes, the private environment, and the API key stay put — they're local
to each machine and are never overwritten by an update.

---

## Good to know

- **WebView2** (the window engine) ships with Windows 10/11 by default — nothing
  to install.
- **Customer quotes are local.** Each machine keeps its own quotes under `jobs/`;
  they are not committed or shared. Only the blank `_template` and the Hoodland
  demo ship with the app.
- **First run needs internet** (to install dependencies). After that everything
  works offline except scan import (which calls Anthropic).
- **Port 8485** is used locally inside the app window (the submittal tool uses
  8484) — no firewall/router setup needed.
