#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_channel_mapping_from_manual_review.py

Version: 0.1.0

Input
- Manual_Channel_Review.csv (default: repo root, or IPTV/, or out/reports/*)
  Expected column: Channel/Network

Output
- IPTV/channel_name_map.csv

Goal
- Turn your 1-column manual list into a *mapping file* you can refine.
- Pre-fills:
  - canonical_name: strips trailing "- East"/"- West"/" East"/" West"
  - feed: East/West if detected
  - type: "specialty" by default (you can change to "local" later)
"""

from __future__ import annotations

import csv
import datetime as dt
import re
from pathlib import Path

__version__ = "0.1.0"

RE_EW = re.compile(r"\s*[-–]?\s*(East|West)\s*$", re.IGNORECASE)


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def find_manual_csv(repo: Path) -> Path | None:
    # preferred locations
    candidates = [
        repo / "Manual_Channel_Review.csv",
        repo / "IPTV" / "Manual_Channel_Review.csv",
    ]
    for p in candidates:
        if p.exists():
            return p

    # fallback: most recent out/reports/*/Manual_Channel_Review.csv
    reports = repo / "out" / "reports"
    if reports.exists():
        for d in sorted([x for x in reports.iterdir() if x.is_dir()], reverse=True):
            p = d / "Manual_Channel_Review.csv"
            if p.exists():
                return p
    return None


def normalize_variant(s: str) -> str:
    return (s or "").strip()


def detect_feed(name: str) -> str:
    m = RE_EW.search(name or "")
    if not m:
        return ""
    return m.group(1).title()


def strip_feed_suffix(name: str) -> str:
    return RE_EW.sub("", (name or "").strip()).strip(" -–").strip()


def main() -> int:
    repo = repo_root_from_script()
    iptv = repo / "IPTV"
    iptv.mkdir(parents=True, exist_ok=True)

    src = find_manual_csv(repo)
    if not src:
        print("ERROR: Manual_Channel_Review.csv not found (place it in repo root or IPTV/)")
        return 1

    # read
    rows = []
    with src.open(encoding="cp1252", newline="") as f:
        r = csv.DictReader(f)
        if "Channel/Network" not in r.fieldnames:
            print(f"ERROR: Expected column 'Channel/Network' in {src}")
            return 1
        for row in r:
            v = normalize_variant(row.get("Channel/Network", ""))
            if v:
                rows.append(v)

    # unique preserve order
    seen = set()
    uniq = []
    for v in rows:
        k = v.casefold()
        if k not in seen:
            seen.add(k)
            uniq.append(v)

    out_path = iptv / "channel_name_map.csv"
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "variant_name",
            "canonical_name",
            "type",
            "country",
            "feed",
            "notes",
        ])
        for v in uniq:
            feed = detect_feed(v)
            canon = strip_feed_suffix(v)
            w.writerow([v, canon, "specialty", "", feed, ""])

    print("Wrote:", out_path)
    print("Source:", src)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
