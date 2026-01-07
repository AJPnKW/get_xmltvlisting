#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_xmltvlistings_lineups.py

Version: 0.1.0

Purpose:
- Fetch XMLTVListings data for specific lineup IDs and save to local files.

Endpoints (per XMLTVListings API docs):
- /xmltv/get_lineups/{API Key}
- /xmltv/get_channels/{API Key}/{LineupID}
- /xmltv/get/{API Key}/{LineupID}/{Days}/{Offset}

Notes on limits:
- The docs explicitly state that each successful /xmltv/get request counts toward your daily download limit.
- The docs do NOT explicitly say whether /xmltv/get_channels or /xmltv/get_lineups count toward the same limit.
  Treat them as potentially rate/limit controlled by the service.

Run from repo root (recommended):
- saves outputs under: out/downloads/<timestamp>/

Requirements:
- Python 3.8+
- requests (pip install requests)

Auth:
- API key read from environment variable: API_XMLTVLISTING_KEY
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

import requests

__version__ = "0.1.0"
BASE_URL = "https://www.xmltvlistings.com"


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)


def get_api_key() -> str:
    k = (os.getenv("API_XMLTVLISTING_KEY") or "").strip()
    if not k:
        die("Missing env var API_XMLTVLISTING_KEY")
    return k


def http_get(url: str, timeout: int = 60) -> str:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.text


def save_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def fetch_lineups(api_key: str) -> str:
    url = f"{BASE_URL}/xmltv/get_lineups/{api_key}"
    return http_get(url, timeout=60)


def fetch_channels(api_key: str, lineup_id: str) -> str:
    url = f"{BASE_URL}/xmltv/get_channels/{api_key}/{lineup_id}"
    return http_get(url, timeout=120)


def fetch_listings(api_key: str, lineup_id: str, days: int, offset: int) -> str:
    url = f"{BASE_URL}/xmltv/get/{api_key}/{lineup_id}/{days}/{offset}"
    return http_get(url, timeout=300)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--lineups", nargs="+", default=["9329", "9330", "9331"], help="Lineup IDs to fetch")
    ap.add_argument(
        "--mode",
        choices=["channels", "listings"],
        default="channels",
        help="channels=/get_channels (no listings); listings=/get (counts toward daily limit per docs)",
    )
    ap.add_argument("--days", type=int, default=5, help="Days of listings (mode=listings). Max 14 per docs.")
    ap.add_argument("--offset", type=int, default=0, help="Offset days (mode=listings).")
    ap.add_argument("--out-dir", default="", help="Optional output directory. Default: out/downloads/<timestamp>/")
    args = ap.parse_args(argv)

    api_key = get_api_key()

    repo = Path.cwd()
    stamp = now_stamp()
    out_dir = Path(args.out_dir).expanduser() if args.out_dir else (repo / "out" / "downloads" / stamp)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Always fetch lineups list once (small)
    try:
        lineups_xml = fetch_lineups(api_key)
        save_text(out_dir / f"lineups_{stamp}.xml", lineups_xml)
        print(f"Wrote: {out_dir / f'lineups_{stamp}.xml'}")
    except Exception as e:
        die(f"Failed to fetch get_lineups: {e}")

    for lid in args.lineups:
        lid = str(lid).strip()
        if not lid:
            continue
        try:
            if args.mode == "channels":
                xml = fetch_channels(api_key, lid)
                save_text(out_dir / f"xmltv-{lid}-channels.xml", xml)
                print(f"Wrote: {out_dir / f'xmltv-{lid}-channels.xml'}")
            else:
                if args.days < 1 or args.days > 14:
                    die("days must be 1..14 (per docs)")
                xml = fetch_listings(api_key, lid, args.days, args.offset)
                save_text(out_dir / f"xmltv-{lid}-listings-{args.days}d-offset{args.offset}.xml", xml)
                print(f"Wrote: {out_dir / f'xmltv-{lid}-listings-{args.days}d-offset{args.offset}.xml'}")
        except Exception as e:
            die(f"Failed for lineup {lid} in mode {args.mode}: {e}")

    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
