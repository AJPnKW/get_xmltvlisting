#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
channels_inventory.py

Version: 0.6.0

Purpose
- Read channels-only XML files from repo/IPTV:
    DirecTV[US]-channels-9329.xml
    Spectrum_NY[US]-channels-9330.xml
    Bell_Fibe[CA]-channels-9331.xml
- Produce one *human-friendly* table (CSV) that shows:
    channel_id, display_name, and included flags per lineup.

Outputs
- out/reports/<timestamp>/channels_inventory.csv
- out/reports/<timestamp>/channels_inventory.txt  (same data, readable)
"""

from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path
import xml.etree.ElementTree as ET

__version__ = "0.6.0"

LINEUPS = [
    ("9329", "DirecTV[US]"),
    ("9330", "Spectrum_NY[US]"),
    ("9331", "Bell_Fibe[CA]"),
]


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_channels(xml_path: Path) -> dict[str, str]:
    # returns {channel_id: display_name}
    d: dict[str, str] = {}
    root = ET.parse(xml_path).getroot()
    for ch in root.findall("channel"):
        cid = ch.attrib.get("id", "").strip()
        if not cid:
            continue
        dn = ""
        dn_el = ch.find("display-name")
        if dn_el is not None and (dn_el.text or "").strip():
            dn = (dn_el.text or "").strip()
        d[cid] = dn
    return d


def write_txt(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    colw = [len(h) for h in headers]
    for r in rows:
        for i, v in enumerate(r):
            colw[i] = max(colw[i], len(v))
    def fmt_row(r):
        return " | ".join((r[i].ljust(colw[i]) for i in range(len(headers))))
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(fmt_row(headers) + "\n")
        f.write("-+-".join(("-" * w for w in colw)) + "\n")
        for r in rows:
            f.write(fmt_row(r) + "\n")


def main() -> int:
    repo = repo_root_from_script()
    iptv = repo / "IPTV"

    # load per lineup
    per = {}
    missing = []
    for lid, label in LINEUPS:
        p = iptv / f"{label}-channels-{lid}.xml"
        if not p.exists():
            missing.append(str(p))
            continue
        per[(lid, label)] = parse_channels(p)

    if missing:
        print("Missing channels files:")
        for m in missing:
            print("  -", m)
        return 1

    # union set
    all_ids = sorted({cid for d in per.values() for cid in d.keys()})

    rows: list[list[str]] = []
    for cid in all_ids:
        # pick a display name from the first lineup that has it
        dn = ""
        for (lid, label), d in per.items():
            if cid in d and d[cid]:
                dn = d[cid]
                break
        flags = []
        for lid, label in LINEUPS:
            flags.append("Y" if cid in per[(lid, label)] else "")
        rows.append([cid, dn, *flags])

    stamp = now_stamp()
    out_dir = repo / "out" / "reports" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / "channels_inventory.csv"
    txt_path = out_dir / "channels_inventory.txt"

    headers = ["channel_id", "display_name"] + [label for _lid, label in LINEUPS]

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)

    write_txt(txt_path, headers, rows)

    print("Wrote:", csv_path)
    print("Wrote:", txt_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
