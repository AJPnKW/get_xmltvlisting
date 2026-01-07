#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_channels_overlap.py

Version: 0.1.0

Purpose:
- Analyze overlap/uniques between XMLTVListings *channels-only* XML files
  (e.g., xmltv-9329-channels.xml) OR full xmltv-9329.xml files.

Input:
- A folder containing files matching:
    - xmltv-<LINEUPID>-channels.xml  (preferred)
    - xmltv-<LINEUPID>.xml           (also supported)

Output (written to out_dir):
- summary_channels_by_lineup.csv
- overlap_counts_matrix.csv
- overlap_jaccard_matrix.csv
- unique_channels_<lineup_id>.csv   (one per lineup)

Notes:
- Uses channel_id (XML <channel id="...">) as the stable key.
- display_name is carried through for human-readable reports.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

__version__ = "0.1.0"

RE_CHANNELS = re.compile(r"^xmltv-(\d+)(?:-channels)?\.xml$", re.IGNORECASE)


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)


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


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def write_csv(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)


def write_unique_csv(path: Path, items: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["channel_id", "display_name"])
        for cid, name in items:
            w.writerow([cid, name])


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--input_dir", required=True, help="Folder containing xmltv-*-channels.xml (or xmltv-*.xml)")
    ap.add_argument("--out_dir", required=True, help="Output folder to write CSV reports")
    args = ap.parse_args(argv)

    input_dir = Path(args.input_dir).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    if not input_dir.exists():
        die(f"Missing input_dir: {input_dir}")

    files = sorted([p for p in input_dir.iterdir() if p.is_file() and RE_CHANNELS.match(p.name)])
    if not files:
        die(f"No matching files found in {input_dir} (expected xmltv-<id>-channels.xml or xmltv-<id>.xml)")

    # lineup_id -> channels map
    lineup_channels: dict[str, dict[str, str]] = {}
    for p in files:
        m = RE_CHANNELS.match(p.name)
        assert m
        lineup_id = m.group(1)
        lineup_channels[lineup_id] = parse_channels(p)

    lineup_ids = sorted(lineup_channels.keys(), key=lambda x: int(x) if x.isdigit() else x)

    # Summary
    summary_rows = [[lid, len(lineup_channels[lid])] for lid in lineup_ids]
    write_csv(out_dir / "summary_channels_by_lineup.csv", ["lineup_id", "channel_count"], summary_rows)

    # Overlap matrices
    counts_headers = ["lineup_id"] + lineup_ids
    counts_rows: list[list[object]] = []
    jac_rows: list[list[object]] = []

    sets = {lid: set(lineup_channels[lid].keys()) for lid in lineup_ids}

    for a in lineup_ids:
        row_counts: list[object] = [a]
        row_jac: list[object] = [a]
        for b in lineup_ids:
            inter = len(sets[a] & sets[b])
            row_counts.append(inter)
            row_jac.append(f"{jaccard(sets[a], sets[b]):.4f}")
        counts_rows.append(row_counts)
        jac_rows.append(row_jac)

    write_csv(out_dir / "overlap_counts_matrix.csv", counts_headers, counts_rows)
    write_csv(out_dir / "overlap_jaccard_matrix.csv", counts_headers, jac_rows)

    # Unique channels per lineup: channels in this lineup not in any others
    for lid in lineup_ids:
        others = set().union(*[sets[x] for x in lineup_ids if x != lid]) if len(lineup_ids) > 1 else set()
        unique_ids = sorted(list(sets[lid] - others))
        items = [(cid, lineup_channels[lid].get(cid, "")) for cid in unique_ids]
        write_unique_csv(out_dir / f"unique_channels_{lid}.csv", items)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
