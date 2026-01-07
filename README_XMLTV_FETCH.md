# get_xmltvlisting — XMLTVListings fetch + publish

## What this does
- Fetches XMLTV listings for 3 lineups: 9329, 9330, 9331
- Writes 3 copies (atomic writes; existing files preserved if limit/error occurs):
  - Audit (timestamped): out/downloads/<timestamp>/...
  - Local device folder: C:\X1_Share\Tivimate\iptv_lineup\...
  - Repo publish folder: IPTV/iptv_lineup/... (push to GitHub for web access)

## Human-friendly filenames (stable)
- DirecTV[US]-xmltv-9329.xml
- Spectrum_NY[US]-xmltv-9330.xml
- Bell_Fibe[CA]-xmltv-9331.xml

## Run locally
PowerShell:
- tools/run_fetch_listings.ps1

Environment:
- API_XMLTVLISTING_KEY (required)
- IPTV_LINEUP_DIR (optional override of local device folder)

## GitHub Actions
- .github/workflows/fetch_xmltv_listings.yml
- Runs daily at 12:00 UTC (~07:00 Toronto winter)
- Requires repo secret: API_XMLTVLISTING_KEY

## What happens if the daily limit is reached?
- The script detects the provider message and SKIPS overwriting files.
- Your previously published XML files remain intact, so clients can still load yesterday’s data.
