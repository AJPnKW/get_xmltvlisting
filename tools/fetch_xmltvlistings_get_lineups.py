#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_xmltvlistings_get_lineups.py

Version: 0.1.1

Fix
- The API response sometimes contains extra text/HTML after the <lineups>...</lineups> document,
  which caused:
    xml.etree.ElementTree.ParseError: junk after document element
- This version extracts the first <lineups>...</lineups> block before parsing.
- If extraction fails (no <lineups> block), it will NOT overwrite publish files and returns code 2.

Purpose
- Fetch current lineup names + IDs:
    /xmltv/get_lineups/{APIKEY}
- Write:
    IPTV/lineups.xml|json|csv (stable)
    out/downloads/<timestamp>/lineups.xml|json|csv (audit)

Env
- API_XMLTVLISTING_KEY (required)

Exit codes
- 0 = updated
- 2 = blocked/invalid; publish unchanged
- 1 = hard failure
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET

import requests

__version__ = "0.1.1"
BASE_URL = "https://www.xmltvlistings.com"
LIMIT_TEXT = "You have reached your limit of 5 downloads per day."

RE_LINEUPS_BLOCK = re.compile(r"(<lineups\b[\s\S]*?</lineups>)", re.IGNORECASE)


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


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", newline="\n", dir=str(path.parent)) as tf:
        tf.write(text)
        tmp = tf.name
    Path(tmp).replace(path)


def extract_lineups_xml(xml_text: str) -> str | None:
    if not xml_text:
        return None
    if LIMIT_TEXT in xml_text:
        return None
    m = RE_LINEUPS_BLOCK.search(xml_text)
    if not m:
        return None
    return m.group(1).strip()


def parse_lineups(lineups_xml: str) -> list[dict]:
    root = ET.fromstring(lineups_xml)
    out = []
    for el in root.findall(".//lineup"):
        lid = (el.attrib.get("id") or "").strip()
        name = (el.text or "").strip()
        if lid or name:
            out.append({"lineup_id": lid, "lineup_name": name})

    def keyfn(x):
        try:
            return int(x["lineup_id"])
        except Exception:
            return 999999999

    out.sort(key=keyfn)
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(add_help=True)
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

    url = f"{BASE_URL}/xmltv/get_lineups/{api_key}"
    raw_text = http_get(url, timeout=600)

    lineups_xml = extract_lineups_xml(raw_text)
    if not lineups_xml:
        print("SKIP (invalid): lineups.xml")
        return 2

    try:
        lineups = parse_lineups(lineups_xml)
    except Exception:
        print("SKIP (parse error): lineups.xml")
        return 2

    # CSV
    csv_lines = ["lineup_id,lineup_name"]
    for r in lineups:
        lid = (r.get("lineup_id") or "").replace('"', '""')
        name = (r.get("lineup_name") or "").replace('"', '""')
        csv_lines.append(f'"{lid}","{name}"')
    csv_text = "\n".join(csv_lines) + "\n"

    # Audit
    atomic_write_text(out_dir / "lineups.xml", lineups_xml)
    atomic_write_text(out_dir / "lineups.json", json.dumps(lineups, ensure_ascii=False, indent=2))
    atomic_write_text(out_dir / "lineups.csv", csv_text)

    # Publish (stable)
    atomic_write_text(pub / "lineups.xml", lineups_xml)
    atomic_write_text(pub / "lineups.json", json.dumps(lineups, ensure_ascii=False, indent=2))
    atomic_write_text(pub / "lineups.csv", csv_text)

    print("Wrote:", out_dir / "lineups.xml")
    print("Wrote:", out_dir / "lineups.json")
    print("Wrote:", out_dir / "lineups.csv")
    print("Wrote:", pub / "lineups.xml")
    print("Wrote:", pub / "lineups.json")
    print("Wrote:", pub / "lineups.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
