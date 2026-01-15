#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_channels_overlap.py

Version: 0.9.0

Accepts input filenames:
- <LABEL>_channels_<id>.xml              (safe names)
- <LABEL>-channels-<id>.xml              (older labelled names)
- xmltv-<id>-channels.xml                (legacy)
- xmltv-<id>.xml                         (legacy)

Outputs
- summary_channels_by_lineup.csv
- overlap_counts_matrix.csv
- overlap_jaccard_matrix.csv
- unique_channels_<id>.csv
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
import xml.etree.ElementTree as ET

__version__ = "0.9.0"

RE_LEGACY_CH = re.compile(r"^xmltv-(\d+)-channels\.xml$", re.IGNORECASE)
RE_LEGACY_XML = re.compile(r"^xmltv-(\d+)\.xml$", re.IGNORECASE)
RE_LABELLED_CH_DASH = re.compile(r"^.+-channels-(\d+)\.xml$", re.IGNORECASE)
RE_LABELLED_CH_SAFE = re.compile(r"^.+_channels_(\d+)\.xml$", re.IGNORECASE)


def die(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")


def parse_channel_ids(xml_path: Path) -> set[str]:
    root = ET.parse(xml_path).getroot()
    ids = set()
    for ch in root.findall(".//channel"):
        cid = (ch.get("id") or "").strip()
        if cid:
            ids.add(cid)
    return ids


def find_lineup_files(input_dir: Path) -> dict[str, Path]:
    files = {}
    for p in input_dir.iterdir():
        if not p.is_file():
            continue
        m = (
            RE_LEGACY_CH.match(p.name)
            or RE_LEGACY_XML.match(p.name)
            or RE_LABELLED_CH_DASH.match(p.name)
            or RE_LABELLED_CH_SAFE.match(p.name)
        )
        if not m:
            continue
        lid = m.group(1)
        files[lid] = p
    return files


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def write_csv(path: Path, headers: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--input_dir", required=True)
    ap.add_argument("--out_dir", required=True)
    args = ap.parse_args(argv)

    input_dir = Path(args.input_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    lineup_files = find_lineup_files(input_dir)
    if not lineup_files:
        die(f"No matching files found in {input_dir} (expected *_channels_<id>.xml or *-channels-<id>.xml or xmltv-<id>-channels.xml or xmltv-<id>.xml)")

    lineup_ids = sorted(lineup_files.keys(), key=lambda x: int(x) if x.isdigit() else x)
    channels_by_lineup = {lid: parse_channel_ids(lineup_files[lid]) for lid in lineup_ids}

    write_csv(out_dir / "summary_channels_by_lineup.csv",
              ["lineup_id", "channel_count", "source_file"],
              [[lid, len(channels_by_lineup[lid]), lineup_files[lid].name] for lid in lineup_ids])

    headers = ["lineup_id"] + lineup_ids
    counts_rows = []
    jacc_rows = []
    for a in lineup_ids:
        row_c = [a]
        row_j = [a]
        for b in lineup_ids:
            row_c.append(len(channels_by_lineup[a] & channels_by_lineup[b]))
            row_j.append(round(jaccard(channels_by_lineup[a], channels_by_lineup[b]), 6))
        counts_rows.append(row_c)
        jacc_rows.append(row_j)

    write_csv(out_dir / "overlap_counts_matrix.csv", headers, counts_rows)
    write_csv(out_dir / "overlap_jaccard_matrix.csv", headers, jacc_rows)

    for lid in lineup_ids:
        others = set().union(*[channels_by_lineup[x] for x in lineup_ids if x != lid])
        uniq = sorted(list(channels_by_lineup[lid] - others))
        write_csv(out_dir / f"unique_channels_{lid}.csv", ["channel_id"], [[x] for x in uniq])

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
