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
