#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_keep_remove_report_from_downloads.py

Version: 0.1.0

Purpose
- Build ONE human-readable TXT report with KEEP/REMOVE lists per lineup,
  using the *channels-only* downloads you fetched:
    out/downloads/<timestamp>/xmltv-<id>-channels.xml
  and the latest analysis outputs:
    out/analysis/<timestamp>/unique_channels_<id>.csv

Why this version
- Website UI "channel numbers" often do NOT match XML <channel id="...">.
- This report is optimized for manual UI editing:
  - Sorted by display name (easy to search in UI)
  - Includes channel_id for stable reference

Inputs (auto)
- Latest out/downloads/<timestamp>/
- Latest out/analysis/<timestamp>/ (must contain unique_channels_*.csv)

Output
- out/reports/<timestamp>/keep_remove_report_<timestamp>.txt
"""

from __future__ import annotations

import csv
import datetime as dt
import re
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

__version__ = "0.1.0"

# ---- CONFIG ----
BASE_LINEUP_ID = "9330"  # keep all channels in this lineup (no REMOVE list)
# ---------------

RE_CH_FILE = re.compile(r"^xmltv-(\d+)-channels\.xml$", re.IGNORECASE)


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)


def latest_subdir(root: Path) -> Path:
    if not root.exists():
        die(f"Missing folder: {root}")
    dirs = [d for d in root.iterdir() if d.is_dir()]
    if not dirs:
        die(f"No subfolders under: {root}")
    return sorted(dirs, reverse=True)[0]


def find_latest_with_glob(root: Path, pattern: str) -> Path:
    if not root.exists():
        die(f"Missing folder: {root}")
    for d in sorted([x for x in root.iterdir() if x.is_dir()], reverse=True):
        if any(d.glob(pattern)):
            return d
    die(f"No folder under {root} contains {pattern}")


def parse_channels(xml_path: Path) -> dict[str, str]:
    """Return dict: channel_id -> display_name (first non-empty display-name)."""
    try:
        tree = ET.parse(xml_path)
    except Exception as e:
        die(f"Failed to parse XML: {xml_path} ({e})")
    root = tree.getroot()

    channels: dict[str, str] = {}
    for ch in root.findall(".//channel"):
        cid = (ch.get("id") or "").strip()
        if not cid:
            continue

        name = ""
        for dn in ch.findall("display-name"):
            if dn.text and dn.text.strip():
                name = dn.text.strip()
                break
        channels[cid] = name
    return channels


def load_unique_ids(analysis_dir: Path, lineup_id: str) -> set[str]:
    p = analysis_dir / f"unique_channels_{lineup_id}.csv"
    if not p.exists():
        return set()

    ids: set[str] = set()
    with p.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            cid = (row.get("channel_id") or "").strip()
            if cid:
                ids.add(cid)
    return ids


def sort_key_name(cid: str, name_map: dict[str, str]) -> tuple[str, str]:
    # primary: display name (casefold), fallback: channel_id
    n = (name_map.get(cid) or "").strip()
    return (n.casefold() if n else "~", cid.casefold())


def fmt_row(cid: str, name: str) -> str:
    n = (name or "").strip()
    if n:
        return f"- {n} [{cid}]"
    return f"- [{cid}]"


def main() -> int:
    repo = Path.cwd()

    downloads_root = repo / "out" / "downloads"
    analysis_root = repo / "out" / "analysis"
    reports_root = repo / "out" / "reports"

    downloads_dir = find_latest_with_glob(downloads_root, "xmltv-*-channels.xml")
    analysis_dir = find_latest_with_glob(analysis_root, "unique_channels_*.csv")

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = reports_root / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    report_path = out_dir / f"keep_remove_report_{stamp}.txt"

    # Load channel files
    channel_files = [p for p in downloads_dir.iterdir() if p.is_file() and RE_CH_FILE.match(p.name)]
    if not channel_files:
        die(f"No xmltv-*-channels.xml files found in: {downloads_dir}")

    # lineup_id -> channel_id->display_name
    lineup_channels: dict[str, dict[str, str]] = {}
    for f in sorted(channel_files):
        m = RE_CH_FILE.match(f.name)
        assert m
        lid = m.group(1)
        lineup_channels[lid] = parse_channels(f)

    lineup_ids = sorted(lineup_channels.keys(), key=lambda x: int(x) if x.isdigit() else x)

    with report_path.open("w", encoding="utf-8", newline="\n") as out:
        out.write("KEEP / REMOVE REPORT (channels-only downloads)\n")
        out.write(f"Script: build_keep_remove_report_from_downloads.py v{__version__}\n")
        out.write(f"Generated: {dt.datetime.now():%Y-%m-%d %H:%M:%S}\n")
        out.write(f"Downloads: {downloads_dir}\n")
        out.write(f"Analysis:   {analysis_dir}\n")
        out.write(f"Base lineup (KEEP ALL): {BASE_LINEUP_ID}\n\n")

        for lid in lineup_ids:
            name_map = lineup_channels[lid]
            all_ids = set(name_map.keys())

            out.write("=" * 72 + "\n")
            out.write(f"LINEUP ID: {lid}\n")
            out.write(f"TOTAL CHANNELS: {len(all_ids)}\n\n")

            if lid == BASE_LINEUP_ID:
                out.write(f"KEEP (BASE LINEUP): ALL ({len(all_ids)})\n")
                out.write("REMOVE: NONE\n\n")
                continue

            keep_set = load_unique_ids(analysis_dir, lid)

            keep_ids = sorted(keep_set, key=lambda cid: sort_key_name(cid, name_map))
            remove_ids = sorted(all_ids - keep_set, key=lambda cid: sort_key_name(cid, name_map))

            out.write(f"KEEP (UNIQUE ONLY): {len(keep_ids)}\n")
            out.write("-" * 72 + "\n")
            if keep_ids:
                for cid in keep_ids:
                    out.write(fmt_row(cid, name_map.get(cid, "")) + "\n")
            else:
                out.write("(none)\n")

            out.write("\n")
            out.write(f"REMOVE (DUPLICATES): {len(remove_ids)}\n")
            out.write("-" * 72 + "\n")
            if remove_ids:
                for cid in remove_ids:
                    out.write(fmt_row(cid, name_map.get(cid, "")) + "\n")
            else:
                out.write("(none)\n")

            out.write("\n")

    print("DONE")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
