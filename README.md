# get_xmltvlisting

Purpose: pull + normalize + analyze XMLTVListings lineups (XMLTV) so **your IPTV devices don't each consume the daily download quota**.

This patch includes **local analysis first** (no API calls required) so you can work with the sample XML files you already downloaded.

## Folder map (expected)

- `sample_download_XML.TV.Listings/` (your sample XML files)
- `config/lineups.json` (lineup registry for later API pulls)
- `tools/` (PowerShell launchers)
- `src/get_xmltvlisting/` (Python code)
- `out/` (generated reports; gitignored)

## Step 1 (local overlap analysis)

Run:

```powershell
Set-Location "C:\Users\andrew\PROJECTS\GitHub\get_xmltvlisting"
powershell -ExecutionPolicy Bypass -File .\tools\run_local_analysis.ps1
```

Outputs will be written under `out\analysis\<timestamp>\`.
