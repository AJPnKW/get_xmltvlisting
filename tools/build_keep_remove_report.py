#!/usr/bin/env python3
"""
build_keep_remove_report.py

Reads:
- sample_download_XML.TV.Listings/xmltv-*.xml
- out/analysis/<latest>/unique_channels_<lineup>.csv

Produces:
- out/reports/<timestamp>/keep_remove_report_<timestamp>.txt
"""

import csv
import sys
import re
import datetime as dt
from pathlib import Path
import xml.etree.ElementTree as ET

BASE_LINEUP_ID = "9330"  # Spectrum – Manhattan, NY


def die(msg: str):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def find_latest_analysis(repo: Path) -> Path:
    root = repo / "out" / "analysis"
    if not root.exists():
        die("out/analysis folder not found")

    for d in sorted(root.iterdir(), reverse=True):
        if d.is_dir() and any(d.glob("unique_channels_*.csv")):
            return d

    die("No analysis folder containing unique_channels_*.csv found")


def load_unique_ids(analysis_dir: Path, lineup_id: str) -> set[str]:
    p = analysis_dir / f"unique_channels_{lineup_id}.csv"
    if not p.exists():
        return set()

    ids = set()
    with p.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cid = (row.get("channel_id") or "").strip()
            if cid:
                ids.add(cid)
    return ids


def parse_channels(xml_path: Path) -> dict[str, str]:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    channels = {}
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


def main():
    repo = Path.cwd()

    sample_dir = repo / "sample_download_XML.TV.Listings"
    if not sample_dir.exists():
        die(f"Missing folder: {sample_dir}")

    xml_files = sorted(sample_dir.glob("xmltv-*.xml"))
    if not xml_files:
        die("No xmltv-*.xml files found")

    analysis_dir = find_latest_analysis(repo)

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = repo / "out" / "reports" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    report_path = out_dir / f"keep_remove_report_{stamp}.txt"

    with report_path.open("w", encoding="utf-8") as out:
        out.write("KEEP / REMOVE REPORT\n")
        out.write(f"Generated: {dt.datetime.now():%Y-%m-%d %H:%M:%S}\n")
        out.write(f"Base lineup (KEEP ALL): {BASE_LINEUP_ID}\n\n")

        for xml in xml_files:
            m = re.search(r"xmltv-(\d+)\.xml$", xml.name, re.I)
            lineup_id = m.group(1) if m else xml.stem

            channels = parse_channels(xml)
            all_ids = set(channels.keys())

            out.write("=" * 60 + "\n")
            out.write(f"FILE: {xml.name}\n")
            out.write(f"LINEUP ID: {lineup_id}\n")
            out.write(f"TOTAL CHANNELS: {len(all_ids)}\n\n")

            if lineup_id == BASE_LINEUP_ID:
                out.write(f"KEEP (BASE LINEUP): ALL ({len(all_ids)})\n")
                out.write("REMOVE: NONE\n\n")
                continue

            keep_ids = load_unique_ids(analysis_dir, lineup_id)
            remove_ids = sorted(all_ids - keep_ids, key=lambda x: channels.get(x, x))
            keep_ids = sorted(keep_ids, key=lambda x: channels.get(x, x))

            out.write(f"KEEP (UNIQUE ONLY): {len(keep_ids)}\n")
            out.write("-" * 60 + "\n")
            if keep_ids:
                for cid in keep_ids:
                    name = channels.get(cid, "")
                    out.write(f"  - {name} [{cid}]\n")
            else:
                out.write("  (none)\n")

            out.write("\n")
            out.write(f"REMOVE (DUPLICATES): {len(remove_ids)}\n")
            out.write("-" * 60 + "\n")
            if remove_ids:
                for cid in remove_ids:
                    name = channels.get(cid, "")
                    out.write(f"  - {name} [{cid}]\n")
            else:
                out.write("  (none)\n")

            out.write("\n")

    print("DONE")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
