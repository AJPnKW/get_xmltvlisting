#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_channel_mapping_to_channels_json.py

Version: 0.1.0

Inputs
- IPTV/channels.json
- IPTV/channel_name_map.csv

Output
- IPTV/channels.enriched.json   (does NOT overwrite channels.json)
- out/reports/<timestamp>/channels.enriched.json

Behavior
- For each channel record in channels.json:
  - tries to match any display_name to channel_name_map.variant_name (case-insensitive)
  - if matched, adds:
      canonical_name
      mapping_type
      mapping_country
      mapping_feed
"""

from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path

__version__ = "0.1.0"


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def load_map(map_path: Path) -> dict[str, dict]:
    m = {}
    with map_path.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            v = (row.get("variant_name") or "").strip()
            if not v:
                continue
            m[v.casefold()] = {
                "canonical_name": (row.get("canonical_name") or "").strip(),
                "type": (row.get("type") or "").strip(),
                "country": (row.get("country") or "").strip(),
                "feed": (row.get("feed") or "").strip(),
            }
    return m


def main() -> int:
    repo = repo_root_from_script()
    iptv = repo / "IPTV"
    channels_path = iptv / "channels.json"
    map_path = iptv / "channel_name_map.csv"

    if not channels_path.exists():
        print("ERROR: missing IPTV/channels.json")
        return 1
    if not map_path.exists():
        print("ERROR: missing IPTV/channel_name_map.csv (run build_channel_mapping_from_manual_review.py first)")
        return 1

    mapping = load_map(map_path)

    channels = json.loads(channels_path.read_text(encoding="utf-8"))
    for ch in channels:
        dns = ch.get("display_names") or []
        found = None
        for dn in dns:
            key = (dn or "").strip().casefold()
            if key in mapping:
                found = mapping[key]
                break
        if found:
            ch["canonical_name"] = found["canonical_name"] or ch.get("full_name") or ""
            ch["mapping_type"] = found["type"]
            ch["mapping_country"] = found["country"]
            ch["mapping_feed"] = found["feed"]

    enriched_name = "channels.enriched.json"
    iptv_out = iptv / enriched_name
    iptv_out.write_text(json.dumps(channels, ensure_ascii=False, indent=2), encoding="utf-8")

    stamp = now_stamp()
    rep_out_dir = repo / "out" / "reports" / stamp
    rep_out_dir.mkdir(parents=True, exist_ok=True)
    rep_out = rep_out_dir / enriched_name
    rep_out.write_text(json.dumps(channels, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Wrote:", iptv_out)
    print("Wrote:", rep_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
