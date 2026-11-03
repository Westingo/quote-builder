# QB mobile PWA

Target address: https://quotebuilder.westin-co.com (published behind Cloudflare Access).

The mobile layout, manifest, icons, install prompt, and offline notice are implemented.
Word previews, scans, saving, imports, and document generation require an online
connection to the Windows QB host. This is an online PWA, not an offline quote editor.
The service worker caches only the offline notice, never quotes or API responses.
Desktop editing retains its existing layout and launch process.

## Protected domain setup

1. In Cloudflare Zero Trust, create a self-hosted Access application named
   **Quote Builder**, covering **quotebuilder.westin-co.com** and all paths.
   Add an Allow policy for explicitly approved email addresses. Use email one-time
   PIN or an existing identity provider. Do not use Everyone or a Bypass policy.
   The initial approved user is **westing@metrogates.com** only (confirmed 2026-10-29).
2. Create a separate remotely managed tunnel named **quote-builder**. Run its
   Windows connector on the QB Windows host, using the connector credential
   privately. Do not paste the credential into this repository or chat.
3. Run `run-mobile-host.bat` in the logged-in Windows session where Word works.
   It listens only on **http://127.0.0.1:8487** and uses the same saved jobs as desktop QB.
   Keep the PC awake, the host running, and the tunnel connected. Do not configure
   this Word-dependent process as a Windows service without testing Word automation
   in that execution context.
4. Only after the Access application exists, add the tunnel's published route:
   hostname **quotebuilder.westin-co.com**, service **http://127.0.0.1:8487**.
   Enable **Protect with Access** and select the Quote Builder application's audience.
   This validates Access tokens at the connector. Leave the inventory tunnel unchanged.
5. Verify from an anonymous browser that both `/` and `/api/jobs` require sign-in;
   test an unapproved account is denied. Then sign in with an approved account and
   test editing, saving, reopening, preview, Word/PDF download, and installation
   over cellular data. These remote checks have not yet been performed.

Cloudflare documentation:
https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/

## Install on a phone

After the protected address is live, sign in there first.
On iPhone, use Safari's Share menu and **Add to Home Screen**.
On Android, use the browser's **Install app** action or **Files > Install QB**
when the browser makes the install prompt available.
Opening the installed app still requires a valid sign-in session.

If the connection drops while editing, keep the editor open and reconnect before
saving or building. Closing or refreshing an unsaved quote can lose changes.
The offline screen does not restore an unsaved quote.

This first version shares the host's saved quote list among approved users;
it has no per-user quote ownership or conflict resolution for simultaneous edits
to the same saved quote. Use one editor at a time for a given quote.

## Deployment record — 2026-10-29

- Background Chrome connection and signed-in Cloudflare account verified.
- Access application **Quote Builder**, ID `0de8425e-4267-496c-a66c-c4fb38503a26`,
  protects `quotebuilder.westin-co.com` with no path restriction.
- Allow policy **QB owner**, ID `640a3da1-029a-4613-84a3-de03e558cd8c`,
  includes exactly `westing@metrogates.com`. Application session duration: 24 hours.
- Separate tunnel **quote-builder**, ID `93331127-9232-439e-84b2-cccbc50af7f6`,
  connected from ITDesktop and showed Healthy.
- Published route points to `http://127.0.0.1:8487`; Cloudflare confirmed creation
  of its CNAME pointing to that tunnel. Access existed before route publication.
- **Protect with Access** is enabled. The connector's received configuration was
  checked for `access.required: true`, team `shrill-dust-1e7e`, and the QB audience
  `ab0251bb00f3ad46a7939da51ae816146a134be478a431df0c34c18d529495a6`.
  This audience identifier is public configuration, not a connector credential.
- The connector credential is stored outside the repository in
  `%LOCALAPPDATA%\QuoteBuilder\cloudflared\token`, in a directory restricted
  to the current Windows user and SYSTEM. Never print or commit its contents.
  Connector logs are in that directory as `connector.log` and `connector-error.log`.
- The connector currently runs as a hidden user process, not an installed service.
  Automatic restart after logout/reboot is not configured. The QB host likewise
  must be running in the logged-in Word-capable Windows session.
- Local host returned HTTP 200; three PWA tests and `git diff --check` passed.
- Anonymous Chrome displayed **Log in to Quote Builder** over HTTPS. Anonymous
  scripted requests to `/`, `/api/jobs`, `/sw.js`, and the manifest returned 403
  without the editor. The script's 403 alone does not distinguish Access from
  other Cloudflare protection; the browser login and received connector settings
  provide the separate Access evidence.
- Authorized session, save/reopen, preview, downloads, and phone installation:
  pending verification. Email-code sign-in was initiated for the approved user.
- No changes were made to the inventory deployment. Its tunnel showed Healthy
  during setup. No source changes have been committed or pushed by this setup.

## Restart the connector after a reboot

First start `run-mobile-host.bat` in your normal logged-in Windows session.
Then run the following in PowerShell once, only if the QB connector is not already
running. This uses the existing private token file and does not install or replace
any Windows service:

```powershell
$qbPrivate = Join-Path $env:LOCALAPPDATA 'QuoteBuilder\cloudflared'
Start-Process -FilePath 'C:\Program Files (x86)\cloudflared\cloudflared.exe' `
  -ArgumentList @('tunnel', '--no-autoupdate', 'run', '--token-file',
    ('"' + (Join-Path $qbPrivate 'token') + '"')) `
  -WindowStyle Hidden `
  -RedirectStandardOutput (Join-Path $qbPrivate 'connector.log') `
  -RedirectStandardError (Join-Path $qbPrivate 'connector-error.log')
```

## Phone / cellular acceptance check (pending)

1. Turn off phone Wi-Fi and open https://quotebuilder.westin-co.com using cellular.
2. Sign in as `westing@metrogates.com`; enter the emailed code on Cloudflare's page.
3. Create a clearly named test quote, change a line and price, save it, then reopen
   it and verify the changed values. Do not overwrite a real customer quote.
4. Open Preview, build Word and PDF, and open both downloads to check the layout.
5. Install QB using Safari **Share > Add to Home Screen** on iPhone, or Chrome
   **Install app / Add to Home screen** on Android. Launch the new icon and verify
   the editor and saved quote work. Installation through Access still needs this
   real-device check.
6. With a disposable test quote open, disable cellular briefly and check the offline
   notice. Reconnect before saving. Do not close an unsaved real quote during this test.
7. Confirm a fresh signed-out browser requires sign-in. An unapproved-account denial
   test has not yet been completed; do not add another email simply to run that test.
