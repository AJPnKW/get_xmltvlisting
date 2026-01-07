#!/usr/bin/env python3
"""
build_keep_remove_report_v0_2_0.py

Versioned utility to generate ONE human-readable KEEP/REMOVE report per lineup XML.

Reads (from repo root):
- sample_download_XML.TV.Listings/xmltv-*.xml
- out/analysis/<latest>/unique_channels_<lineup>.csv

Writes:
- out/reports/<timestamp>/keep_remove_report_<timestamp>.txt
"""

from __future__ import annotations

import csv
import datetime as dt
import re
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

__app__ = "build_keep_remove_report"
__version__ = "0.2.0"

# Base lineup: KEEP ALL, REMOVE NONE (your current choice)
BASE_LINEUP_ID = "9330"


def die(msg: str, code: int = 2) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def channel_num(cid: str) -> int:
    """Extract leading integer from channel_id; if none, push to bottom."""
    m = re.match(r"^(\d+)", cid.strip())
    return int(m.group(1)) if m else 999_999_999


def find_latest_analysis(repo: Path) -> Path:
    root = repo / "out" / "analysis"
    if not root.exists():
        die("out/analysis folder not found (run the analyzer first)")

    for d in sorted(root.iterdir(), reverse=True):
        if d.is_dir() and any(d.glob("unique_channels_*.csv")):
            return d

    die("No analysis folder containing unique_channels_*.csv found")


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


def parse_channels(xml_path: Path) -> dict[str, str]:
    """Return dict: channel_id -> display_name (first display-name if present)."""
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError as e:
        die(f"XML parse failed: {xml_path}: {e}")

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


def sort_key(cid: str, channels: dict[str, str]) -> tuple[int, str, str]:
    name = (channels.get(cid) or "").strip()
    return (channel_num(cid), name.lower(), cid)


def main() -> int:
    repo = Path.cwd()

    sample_dir = repo / "sample_download_XML.TV.Listings"
    if not sample_dir.exists():
        die(f"Missing folder: {sample_dir}")

    xml_files = sorted(sample_dir.glob("xmltv-*.xml"))
    if not xml_files:
        die(f"No xmltv-*.xml files found in: {sample_dir}")

    analysis_dir = find_latest_analysis(repo)

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = repo / "out" / "reports" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    report_path = out_dir / f"keep_remove_report_{stamp}.txt"

    with report_path.open("w", encoding="utf-8", newline="\n") as out:
        out.write("KEEP / REMOVE REPORT\n")
        out.write(f"Tool: {__app__} v{__version__}\n")
        out.write(f"Generated: {dt.datetime.now():%Y-%m-%d %H:%M:%S}\n")
        out.write(f"Base lineup (KEEP ALL): {BASE_LINEUP_ID}\n")
        out.write(f"Analysis folder: {analysis_dir}\n\n")

        for xml in xml_files:
            m = re.search(r"xmltv-(\d+)\.xml$", xml.name, re.I)
            lineup_id = m.group(1) if m else xml.stem

            channels = parse_channels(xml)
            all_ids = set(channels.keys())

            out.write("=" * 68 + "\n")
            out.write(f"FILE: {xml.name}\n")
            out.write(f"LINEUP ID: {lineup_id}\n")
            out.write(f"TOTAL CHANNELS: {len(all_ids)}\n\n")

            if lineup_id == BASE_LINEUP_ID:
                out.write(f"KEEP (BASE LINEUP): ALL ({len(all_ids)})\n")
                out.write("REMOVE: NONE\n\n")
                continue

            keep_set = load_unique_ids(analysis_dir, lineup_id)

            keep_ids = sorted(keep_set, key=lambda cid: sort_key(cid, channels))
            remove_ids = sorted((all_ids - keep_set), key=lambda cid: sort_key(cid, channels))

            out.write(f"KEEP (UNIQUE ONLY): {len(keep_ids)}\n")
            out.write("-" * 68 + "\n")
            if keep_ids:
                for cid in keep_ids:
                    num = channel_num(cid)
                    name = (channels.get(cid) or "").strip()
                    out.write(f"{num:<6} - {name} [{cid}]\n")
            else:
                out.write("(none)\n")

            out.write("\n")
            out.write(f"REMOVE (DUPLICATES): {len(remove_ids)}\n")
            out.write("-" * 68 + "\n")
            if remove_ids:
                for cid in remove_ids:
                    num = channel_num(cid)
                    name = (channels.get(cid) or "").strip()
                    out.write(f"{num:<6} - {name} [{cid}]\n")
            else:
                out.write("(none)\n")

            out.write("\n")

    print("DONE")
    print(f"Script: {__app__} v{__version__}")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
