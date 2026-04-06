# get_xmltvlisting — Fetch + CBC Canada EPG build

## What this does
- Fetches source lineup XMLTV files into `IPTV/`.
- Builds a standalone CBC-only XMLTV file from these two fetched sources:
  - `IPTV/Rogers_Toronto_ON_CA_xmltv_10270.xml`
  - `IPTV/Telus_Optik_Vancouver_BC_CA_xmltv_10269.xml`
- Produces:
  - `IPTV/CBC_Canada.xml`

## CBC allow-list used by the builder
- `CBLT-DT`
- `CBUT-DT`
- `CBHT-DT`
- `CBWT-DT`
- `CBRT-DT`

## Run locally
1. Fetch source lineup XMLTV files:
   - `tools/run_fetch_listings.ps1`

2. Build CBC-only EPG (EPG-only; no M3U dependency):
   - `python tools/build_cbc_canada_epg.py`

### Output
- `IPTV/CBC_Canada.xml`

### Notes
- Allow-list: CBLT-DT, CBUT-DT, CBHT-DT, CBWT-DT, CBRT-DT
- If any allow-list callsign is missing from both source XML files, the build fails fast and prints the missing callsigns.

## Files produced
- Fetched source files in `IPTV/` (including the two CBC source inputs above).
- Derived CBC output:
  - `IPTV/CBC_Canada.xml`

## GitHub Actions
- Workflow: `.github/workflows/fetch_xmltv_listings.yml`
- Sequence:
  1. fetch channels
  2. fetch listings
  3. run `tools/build_cbc_canada_epg.py`

## Multi-target publish

Use this when you want the repo synced to:
- local working copy
- GitHub
- HP920 local git clone
- HP920 LAN-hosted static XMLTV folder at `http://192.168.1.73:8011/iptv-epg/`

Run:

```powershell
Set-Location "C:\Users\andrew\PROJECTS\GitHub\get_xmltvlisting"
powershell -ExecutionPolicy Bypass -File .\tools\publish_sync_targets.ps1
```

What it does:
- installs the HP920 GitHub-sync helper
- pushes the current `main` branch to GitHub
- tells HP920 to clone/pull the repo from GitHub into `~/sites/iptv-sync/get_xmltvlisting`
- HP920 then publishes the repo `IPTV/` folder into `/srv/my_tv_movie/app/iptv-epg`

Notes:
- HP920 currently has an active Python static web server on port `8011`
- `Gitea` was not found running on HP920 during setup, so HP920 sync uses a local clone refreshed from GitHub instead
- large files over GitHub's single-file limit should be published as `.gz` assets for GitHub compatibility
