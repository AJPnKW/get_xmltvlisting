#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
channels_overlap_report.py

Version: 0.7.1

Inputs (strict)
- IPTV/<LABEL>-channels-<LINEUPID>.xml for the 5 lineups.

Outputs
- out/reports/<timestamp>/channels_by_lineup.csv
- out/reports/<timestamp>/overlap_summary.csv
- out/reports/<timestamp>/remove_lists.txt

Logic (deterministic)
- Compute per lineup: count
- Split groups:
  - CA: lineups with [CA] in label
  - US: lineups with [US] in label
- For each group, choose PRIMARY = lineup with MAX channel count.
- For every other lineup in group:
  - REMOVE = channels that also exist in PRIMARY (by channel_id)
  - KEEP   = channels not in PRIMARY

Channel number
- extracted from <display-name> values that look numeric (e.g., 12 or 12.3)
"""

from __future__ import annotations

import csv
import datetime as dt
import re
from pathlib import Path
import xml.etree.ElementTree as ET

__version__ = "0.7.1"

LINEUPS = [
    ("10270", "Rogers_Toronto_ON[CA]"),
    ("10269", "Telus_Optik_Vancouver_BC[CA]"),
    ("10271", "Xfinity_Chicago_IL[US]"),
    ("10273", "Verizon_FIOS_NewYork_NY[US]"),
    ("10272", "Broadcast_LosAngeles_CA[US]"),
]

RE_CHNUM = re.compile(r"^\d{1,4}(\.\d{1,3})?$")


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_channels(xml_path: Path) -> dict[str, dict]:
    root = ET.parse(xml_path).getroot()
    out = {}
    for ch in root.findall("channel"):
        cid = (ch.attrib.get("id") or "").strip()
        if not cid:
            continue
        display_names = [(dn.text or "").strip() for dn in ch.findall("display-name") if (dn.text or "").strip()]
        full_name = display_names[0] if display_names else ""
        chnum = ""
        for dn in display_names:
            if RE_CHNUM.match(dn):
                chnum = dn
                break
        out[cid] = {"display_name": full_name, "channel_number": chnum}
    return out


def write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)


def group_key(label: str) -> str:
    if "[CA]" in label:
        return "CA"
    if "[US]" in label:
        return "US"
    return "OTHER"


def main() -> int:
    repo = repo_root_from_script()
    iptv = repo / "IPTV"

    lineup_data = {}
    missing = []
    for lid, label in LINEUPS:
        p = iptv / f"{label}-channels-{lid}.xml"
        if not p.exists():
            missing.append(str(p))
            continue
        lineup_data[(lid, label)] = parse_channels(p)

    if missing:
        print("Missing channels-only files:")
        for m in missing:
            print("  -", m)
        return 1

    stamp = now_stamp()
    out_dir = repo / "out" / "reports" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for (lid, label), d in lineup_data.items():
        for cid, meta in d.items():
            rows.append([label, lid, cid, meta.get("channel_number", ""), meta.get("display_name", "")])
    write_csv(out_dir / "channels_by_lineup.csv",
              ["lineup_label", "lineup_id", "channel_id", "channel_number", "display_name"],
              rows)

    by_group = {"CA": [], "US": [], "OTHER": []}
    for lid, label in LINEUPS:
        by_group[group_key(label)].append((lid, label))

    summary_rows = []
    remove_txt = []

    for g in ["CA", "US"]:
        members = by_group[g]
        primary = max(members, key=lambda x: len(lineup_data[(x[0], x[1])]))
        pset = set(lineup_data[primary].keys())
        summary_rows.append([g, primary[1], primary[0], str(len(pset)), "PRIMARY(max channels)"])

        remove_txt.append(f"GROUP: {g}")
        remove_txt.append(f"PRIMARY: {primary[1]} ({primary[0]}) count={len(pset)}")
        remove_txt.append("")

        for lid, label in members:
            cset = set(lineup_data[(lid, label)].keys())
            summary_rows.append([g, label, lid, str(len(cset)), ""])

            if (lid, label) == primary:
                continue

            remove_ids = sorted(list(cset & pset))
            keep_ids = sorted(list(cset - pset))

            remove_txt.append(f"LINEUP: {label} ({lid})")
            remove_txt.append(f"REMOVE (duplicates vs primary): {len(remove_ids)}")
            for cid in remove_ids:
                meta = lineup_data[(lid, label)].get(cid, {})
                remove_txt.append(f"  {meta.get('channel_number','')}	{meta.get('display_name','')}	[{cid}]")
            remove_txt.append("")
            remove_txt.append(f"KEEP (unique vs primary): {len(keep_ids)}")
            for cid in keep_ids:
                meta = lineup_data[(lid, label)].get(cid, {})
                remove_txt.append(f"  {meta.get('channel_number','')}	{meta.get('display_name','')}	[{cid}]")
            remove_txt.append("")
            remove_txt.append("-" * 72)
            remove_txt.append("")

        remove_txt.append("=" * 72)
        remove_txt.append("")

    write_csv(out_dir / "overlap_summary.csv",
              ["group", "lineup_label", "lineup_id", "channel_count", "note"],
              summary_rows)

    (out_dir / "remove_lists.txt").write_text("\n".join(remove_txt), encoding="utf-8")

    print("Wrote:", out_dir / "channels_by_lineup.csv")
    print("Wrote:", out_dir / "overlap_summary.csv")
    print("Wrote:", out_dir / "remove_lists.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
