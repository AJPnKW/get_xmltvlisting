#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_xmltvlistings_channels.py

Version: 0.9.0

Change
- SAFE FILENAMES: no square brackets [] or other special chars.
- Output naming:
    IPTV/<LABEL>_channels_<LINEUPID>.xml
  Example:
    IPTV/Rogers_Toronto_ON_CA_channels_10270.xml

Purpose
- Fetch channels-only XML using:
    /xmltv/get_channels/{API Key}/{LineupID}
- Save to publish folder (default repo/IPTV) and audit folder (out/downloads/<timestamp>/)

Safety
- If payload indicates limit/invalid:
  - does NOT overwrite existing publish files
  - returns exit code 2

Env
- API_XMLTVLISTING_KEY (required)

Active lineups
10270 Rogers - Toronto, ON
10269 Telus Optik TV - Vancouver, BC
10271 Xfinity - Chicago Area 1, 4 & 5, IL - Digital
10273 Verizon FIOS - New York, NY
10272 Broadcast - Los Angeles, CA
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import tempfile
from pathlib import Path
import requests

__version__ = "0.9.0"
BASE_URL = "https://www.xmltvlistings.com"
LIMIT_TEXT = "You have reached your limit of 5 downloads per day."

LINEUP_LABELS = {
    "10270": "Rogers_Toronto_ON_CA",
    "10269": "Telus_Optik_Vancouver_BC_CA",
    "10271": "Xfinity_Chicago_IL_US",
    "10273": "Verizon_FIOS_NewYork_NY_US",
    "10272": "Broadcast_LosAngeles_CA_US",
}


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def get_api_key() -> str:
    k = (os.getenv("API_XMLTVLISTING_KEY") or "").strip()
    if not k:
        die("Missing env var API_XMLTVLISTING_KEY")
    return k


def http_get(url: str, timeout: int = 600) -> str:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.text


def fetch_channels(api_key: str, lineup_id: str) -> str:
    url = f"{BASE_URL}/xmltv/get_channels/{api_key}/{lineup_id}"
    return http_get(url, timeout=600)


def looks_like_channels_xml(xml: str) -> bool:
    s = (xml or "").lstrip()
    if not s:
        return False
    if LIMIT_TEXT in xml:
        return False
    return "<tv" in s[:1000] and "<channel" in xml


def atomic_write_text(target: Path, text: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", newline="\n", dir=str(target.parent)) as tf:
        tf.write(text)
        tmp_name = tf.name
    Path(tmp_name).replace(target)


def out_name(lineup_id: str) -> str:
    label = LINEUP_LABELS.get(lineup_id, f"Lineup{lineup_id}")
    return f"{label}_channels_{lineup_id}.xml"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--lineups", nargs="+", default=list(LINEUP_LABELS.keys()))
    ap.add_argument("--publish-dir", default="IPTV", help="Relative (repo-based) or absolute publish folder")
    ap.add_argument("--out-dir", default="", help="Audit out dir (default repo/out/downloads/<timestamp>/)")
    args = ap.parse_args(argv)

    api_key = get_api_key()
    repo = repo_root_from_script()
    stamp = now_stamp()

    pub = Path(args.publish_dir).expanduser()
    if not pub.is_absolute():
        pub = repo / pub
    pub.mkdir(parents=True, exist_ok=True)

    out_dir = Path(args.out_dir).expanduser() if args.out_dir else (repo / "out" / "downloads" / stamp)
    out_dir.mkdir(parents=True, exist_ok=True)

    any_blocked = False

    for lid_raw in args.lineups:
        lid = str(lid_raw).strip()
        if not lid:
            continue
        fname = out_name(lid)

        try:
            xml = fetch_channels(api_key, lid)

            if LIMIT_TEXT in (xml or ""):
                any_blocked = True
                print(f"SKIP (limit): {fname}")
                continue

            if not looks_like_channels_xml(xml):
                any_blocked = True
                print(f"SKIP (invalid): {fname}")
                continue

            atomic_write_text(out_dir / fname, xml)
            print(f"Wrote: {out_dir / fname}")
            atomic_write_text(pub / fname, xml)
            print(f"Wrote: {pub / fname}")

        except Exception as e:
            any_blocked = True
            print(f"SKIP (error): {fname} :: {e}")

    return 2 if any_blocked else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
