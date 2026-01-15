#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_channel_overlap_remove_lists.py

Version: 0.1.0

Goal
- Produce "what to disable in XMLTVListings UI" per lineup based on channels-only files.
- NO downloads. Reads existing files under repo/IPTV.

Inputs (expected safe filenames)
- IPTV/Rogers_Toronto_ON_CA_channels_10270.xml
- IPTV/Telus_Optik_Vancouver_BC_CA_channels_10269.xml
- IPTV/Xfinity_Chicago_IL_US_channels_10271.xml
- IPTV/Verizon_FIOS_NewYork_NY_US_channels_10273.xml
- IPTV/Broadcast_LosAngeles_CA_US_channels_10272.xml

Outputs
1) Timestamped:
   out/reports/<timestamp>/remove_lists_CA.txt
   out/reports/<timestamp>/remove_lists_US.txt
   out/reports/<timestamp>/remove_summary.csv
2) Publish (stable, current):
   IPTV/remove_lists_CA.txt
   IPTV/remove_lists_US.txt
   IPTV/remove_summary.csv

Logic (deterministic)
- Split into two groups by filename:
  - CA: *_CA_channels_*
  - US: *_US_channels_*
- Primary per group = lineup with MAX channel count.
- For every other lineup in group:
  - REMOVE = channels whose channel_id exists in primary (duplicates)
  - KEEP   = channels not in primary (unique)

Channel number / display name
- Extracted from <display-name> entries:
  - number = first numeric display-name
  - name   = first display-name
"""

from __future__ import annotations

import csv
import datetime as dt
import re
from pathlib import Path
import xml.etree.ElementTree as ET

__version__ = "0.1.0"

FILES = [
    ("10270", "Rogers_Toronto_ON_CA", "CA"),
    ("10269", "Telus_Optik_Vancouver_BC_CA", "CA"),
    ("10271", "Xfinity_Chicago_IL_US", "US"),
    ("10273", "Verizon_FIOS_NewYork_NY_US", "US"),
    ("10272", "Broadcast_LosAngeles_CA_US", "US"),
]

RE_CHNUM = re.compile(r"^\d{1,4}(\.\d{1,3})?$")


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_channels(path: Path) -> dict[str, dict]:
    root = ET.parse(path).getroot()
    out: dict[str, dict] = {}
    for ch in root.findall(".//channel"):
        cid = (ch.attrib.get("id") or "").strip()
        if not cid:
            continue
        dns = [(dn.text or "").strip() for dn in ch.findall("display-name") if (dn.text or "").strip()]
        name = dns[0] if dns else ""
        num = ""
        for dn in dns:
            if RE_CHNUM.match(dn):
                num = dn
                break
        out[cid] = {"channel_number": num, "display_name": name}
    return out


def write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)


def build_group(members: list[tuple[str, str]]) -> tuple[tuple[str, str], dict[tuple[str, str], dict[str, dict]]]:
    repo = repo_root_from_script()
    iptv = repo / "IPTV"
    data: dict[tuple[str, str], dict[str, dict]] = {}
    missing = []
    for lid, label in members:
        p = iptv / f"{label}_channels_{lid}.xml"
        if not p.exists():
            missing.append(str(p))
            continue
        data[(lid, label)] = parse_channels(p)
    if missing:
        raise FileNotFoundError("Missing channels files:\n  - " + "\n  - ".join(missing))
    primary = max(data.keys(), key=lambda k: len(data[k]))
    return primary, data


def main() -> int:
    repo = repo_root_from_script()
    iptv = repo / "IPTV"
    stamp = now_stamp()
    out_dir = repo / "out" / "reports" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    ca_members = [(lid, label) for (lid, label, g) in FILES if g == "CA"]
    us_members = [(lid, label) for (lid, label, g) in FILES if g == "US"]

    summary_rows: list[list[str]] = []

    def render(group: str, members: list[tuple[str, str]]) -> list[str]:
        primary, data = build_group(members)
        p_ids = set(data[primary].keys())

        lines: list[str] = []
        lines.append(f"GROUP: {group}")
        lines.append(f"PRIMARY (keep as-is): {primary[1]} ({primary[0]})  channels={len(p_ids)}")
        lines.append("")

        for lid, label in members:
            ids = set(data[(lid, label)].keys())
            summary_rows.append([group, label, lid, str(len(ids)), "PRIMARY" if (lid, label) == primary else ""])

            if (lid, label) == primary:
                continue

            remove_ids = sorted(list(ids & p_ids))
            keep_ids = sorted(list(ids - p_ids))

            lines.append(f"LINEUP: {label} ({lid})")
            lines.append(f"REMOVE in XMLTVListings UI (duplicates vs primary): {len(remove_ids)}")
            for cid in remove_ids:
                meta = data[(lid, label)].get(cid, {})
                num = meta.get("channel_number", "")
                name = meta.get("display_name", "")
                lines.append(f"  {num}\t{name}\t[{cid}]")
            lines.append("")
            lines.append(f"KEEP (unique vs primary): {len(keep_ids)}")
            for cid in keep_ids:
                meta = data[(lid, label)].get(cid, {})
                num = meta.get("channel_number", "")
                name = meta.get("display_name", "")
                lines.append(f"  {num}\t{name}\t[{cid}]")
            lines.append("")
            lines.append("-" * 72)
            lines.append("")

        return lines

    ca_lines = render("CA", ca_members)
    us_lines = render("US", us_members)

    # Timestamped outputs
    write_text(out_dir / "remove_lists_CA.txt", ca_lines)
    write_text(out_dir / "remove_lists_US.txt", us_lines)
    write_csv(out_dir / "remove_summary.csv",
              ["group", "lineup_label", "lineup_id", "channel_count", "role"],
              summary_rows)

    # Publish outputs (stable)
    write_text(iptv / "remove_lists_CA.txt", ca_lines)
    write_text(iptv / "remove_lists_US.txt", us_lines)
    write_csv(iptv / "remove_summary.csv",
              ["group", "lineup_label", "lineup_id", "channel_count", "role"],
              summary_rows)

    print("Wrote:", out_dir / "remove_lists_CA.txt")
    print("Wrote:", out_dir / "remove_lists_US.txt")
    print("Wrote:", out_dir / "remove_summary.csv")
    print("Wrote:", iptv / "remove_lists_CA.txt")
    print("Wrote:", iptv / "remove_lists_US.txt")
    print("Wrote:", iptv / "remove_summary.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
