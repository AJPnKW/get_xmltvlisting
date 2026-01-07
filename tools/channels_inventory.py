#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
channels_inventory.py

Version: 0.6.4

Inputs (strict)
- Uses ONLY channels-only files in repo/IPTV:
    DirecTV[US]-channels-9329.xml
    Spectrum_NY[US]-channels-9330.xml
    Bell_Fibe[CA]-channels-9331.xml

Outputs (two locations)
1) Timestamped reports:
   - out/reports/<timestamp>/channels_inventory.csv
   - out/reports/<timestamp>/channels_inventory.txt
   - out/reports/<timestamp>/channels.json
2) Publish (stable, current collection):
   - IPTV/channels.json

channels.json schema (per channel_id)
{
  "channel_id": "...",
  "display_names": ["...", "...", "..."],
  "full_name": "...",
  "call_sign": "...",
  "channel_number": "...",
  "url": "...",
  "icon_src": "...",
  "present_in": ["DirecTV[US]", "Spectrum_NY[US]"]
}
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET

__version__ = "0.6.4"

LINEUPS = [
    ("9329", "DirecTV[US]"),
    ("9330", "Spectrum_NY[US]"),
    ("9331", "Bell_Fibe[CA]"),
]

RE_CALLSIGN = re.compile(r"^[A-Z0-9]{2,8}([\-\.][A-Z0-9]{1,6})?$")
RE_CHNUM = re.compile(r"^\d{1,4}(\.\d{1,3})?$")


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_channels(xml_path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    root = ET.parse(xml_path).getroot()
    for ch in root.findall("channel"):
        cid = (ch.attrib.get("id") or "").strip()
        if not cid:
            continue

        dns = []
        for dn_el in ch.findall("display-name"):
            t = (dn_el.text or "").strip()
            if t and t not in dns:
                dns.append(t)

        url = ""
        url_el = ch.find("url")
        if url_el is not None and (url_el.text or "").strip():
            url = (url_el.text or "").strip()

        icon_src = ""
        icon_el = ch.find("icon")
        if icon_el is not None:
            icon_src = (icon_el.attrib.get("src") or "").strip()

        out[cid] = {
            "display_names": dns,
            "url": url,
            "icon_src": icon_src,
        }
    return out


def choose_full_name(display_names: list[str]) -> str:
    return display_names[0] if display_names else ""


def choose_call_sign(display_names: list[str]) -> str:
    for s in display_names:
        if RE_CHNUM.match(s):
            continue
        if RE_CALLSIGN.match(s) and s.upper() == s:
            return s
    return ""


def choose_channel_number(display_names: list[str]) -> str:
    for s in display_names:
        if RE_CHNUM.match(s):
            return s
    return ""


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

    per: dict[tuple[str, str], dict[str, dict]] = {}
    missing = []

    for lid, label in LINEUPS:
        p = iptv / f"{label}-channels-{lid}.xml"
        if not p.exists():
            missing.append(str(p))
            continue
        per[(lid, label)] = parse_channels(p)

    if missing:
        print("Missing channels-only files (create them first with fetch_xmltvlistings_channels.py):")
        for m in missing:
            print("  -", m)
        return 1

    all_ids = sorted({cid for d in per.values() for cid in d.keys()})

    rows: list[list[str]] = []
    channels_json = []

    for cid in all_ids:
        display_names: list[str] = []
        url = ""
        icon_src = ""
        present_in: list[str] = []

        for (_lid, label), d in per.items():
            if cid in d:
                present_in.append(label)
                for dn in d[cid]["display_names"]:
                    if dn and dn not in display_names:
                        display_names.append(dn)
                if not url and d[cid]["url"]:
                    url = d[cid]["url"]
                if not icon_src and d[cid]["icon_src"]:
                    icon_src = d[cid]["icon_src"]

        full_name = choose_full_name(display_names)
        call_sign = choose_call_sign(display_names)
        chnum = choose_channel_number(display_names)

        flags = []
        for lid, label in LINEUPS:
            flags.append("Y" if cid in per[(lid, label)] else "")
        rows.append([cid, full_name, *flags])

        channels_json.append({
            "channel_id": cid,
            "display_names": display_names,
            "full_name": full_name,
            "call_sign": call_sign,
            "channel_number": chnum,
            "url": url,
            "icon_src": icon_src,
            "present_in": present_in,
        })

    stamp = now_stamp()
    out_dir = repo / "out" / "reports" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / "channels_inventory.csv"
    txt_path = out_dir / "channels_inventory.txt"
    json_path = out_dir / "channels.json"
    publish_json_path = iptv / "channels.json"

    headers = ["channel_id", "display_name"] + [label for _lid, label in LINEUPS]

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)

    write_txt(txt_path, headers, rows)

    # timestamped JSON
    with json_path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(channels_json, f, ensure_ascii=False, indent=2)

    # publish JSON (stable)
    iptv.mkdir(parents=True, exist_ok=True)
    with publish_json_path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(channels_json, f, ensure_ascii=False, indent=2)

    print("Wrote:", csv_path)
    print("Wrote:", txt_path)
    print("Wrote:", json_path)
    print("Wrote:", publish_json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
