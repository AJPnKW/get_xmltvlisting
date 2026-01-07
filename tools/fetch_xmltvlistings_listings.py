#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_xmltvlistings_listings.py

Version: 0.4.1

Key behaviors
- NEVER deletes/empties your existing published files.
- Writes are atomic:
  - download -> validate -> write to temp -> replace target
- If provider returns the daily-limit message (or any non-XMLTV payload):
  - script logs the reason
  - script does NOT overwrite existing lineup XML files
  - script exits with code 2 (so automation can detect it)

Files written (3 copies, same filenames)
1) Audit (timestamped): out/downloads/<timestamp>/...
2) Local device folder:  C:\\X1_Share\\Tivimate\\iptv_lineup\\...
3) Repo publish folder:  IPTV/iptv_lineup/...   (push to GitHub for web access)

Human-friendly filenames
- DirecTV[US]-xmltv-9329.xml
- Spectrum_NY[US]-xmltv-9330.xml
- Bell_Fibe[CA]-xmltv-9331.xml

Auth
- API key from env: API_XMLTVLISTING_KEY

Daily limit note
- Each successful /xmltv/get request counts toward the provider's daily download limit.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import tempfile
from pathlib import Path

import requests

__version__ = "0.4.1"
BASE_URL = "https://www.xmltvlistings.com"
DEFAULT_DEVICE_DIR = r"C:\X1_Share\Tivimate\iptv_lineup"
DEFAULT_REPO_PUBLISH_REL = r"IPTV\iptv_lineup"

LINEUP_LABELS = {
    "9329": "DirecTV[US]",
    "9330": "Spectrum_NY[US]",
    "9331": "Bell_Fibe[CA]",
}

LIMIT_TEXT = "You have reached your limit of 5 downloads per day."


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


def log_line(log_path: Path, msg: str) -> None:
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(f"[{ts}] {msg}\n")


def http_get(url: str, timeout: int = 600) -> str:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.text


def fetch_listings(api_key: str, lineup_id: str, days: int, offset: int) -> str:
    url = f"{BASE_URL}/xmltv/get/{api_key}/{lineup_id}/{days}/{offset}"
    return http_get(url, timeout=900)


def pick_device_dir(cli_device_dir: str | None) -> Path:
    if cli_device_dir:
        return Path(cli_device_dir).expanduser()
    env_dir = (os.getenv("IPTV_LINEUP_DIR") or "").strip()
    if env_dir:
        return Path(env_dir).expanduser()
    return Path(DEFAULT_DEVICE_DIR)


def lineup_output_name(lineup_id: str) -> str:
    label = LINEUP_LABELS.get(lineup_id, f"Lineup{lineup_id}")
    return f"{label}-xmltv-{lineup_id}.xml"


def looks_like_xmltv(xml: str) -> bool:
    s = (xml or "").lstrip()
    if not s:
        return False
    if LIMIT_TEXT in xml:
        return False
    return "<tv" in s[:1000]


def atomic_write_text(target: Path, text: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", newline="\n", dir=str(target.parent)) as tf:
        tf.write(text)
        tmp_name = tf.name
    Path(tmp_name).replace(target)


def write_all_copies(out_audit: Path, out_device: Path, out_publish: Path, filename: str, xml: str) -> None:
    atomic_write_text(out_audit / filename, xml)
    atomic_write_text(out_device / filename, xml)
    atomic_write_text(out_publish / filename, xml)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--lineups", nargs="+", default=["9329", "9330", "9331"], help="Lineup IDs to fetch")
    ap.add_argument("--days", type=int, default=7, help="Days of listings to pull (1..14)")
    ap.add_argument("--offset", type=int, default=0, help="Offset days")
    ap.add_argument("--out-dir", default="", help="Optional audit output dir (default: repo/out/downloads/<timestamp>/)")
    ap.add_argument("--device-dir", default="", help="Optional device folder (stable filenames)")
    ap.add_argument("--repo-publish-dir", default="", help="Optional repo publish folder (relative or absolute)")
    args = ap.parse_args(argv)

    if args.days < 1 or args.days > 14:
        die("days must be 1..14")

    api_key = get_api_key()
    repo = repo_root_from_script()
    stamp = now_stamp()

    out_dir = Path(args.out_dir).expanduser() if args.out_dir else (repo / "out" / "downloads" / stamp)
    out_dir.mkdir(parents=True, exist_ok=True)

    device_dir = pick_device_dir(args.device_dir.strip() or None)
    device_dir.mkdir(parents=True, exist_ok=True)

    publish_arg = (args.repo_publish_dir or "").strip()
    if publish_arg:
        publish_dir = Path(publish_arg).expanduser()
        if not publish_dir.is_absolute():
            publish_dir = (repo / publish_dir)
    else:
        publish_dir = repo / DEFAULT_REPO_PUBLISH_REL
    publish_dir.mkdir(parents=True, exist_ok=True)

    log_path = out_dir / f"fetch_listings_{stamp}.log.txt"
    log_line(log_path, f"START fetch listings v{__version__}")
    log_line(log_path, f"Repo        = {repo}")
    log_line(log_path, f"OutDir       = {out_dir}")
    log_line(log_path, f"DeviceDir    = {device_dir}")
    log_line(log_path, f"PublishDir   = {publish_dir}")
    log_line(log_path, f"Lineups      = {args.lineups}")
    log_line(log_path, f"Days/Offset  = {args.days}/{args.offset}")

    any_blocked = False

    for lid_raw in args.lineups:
        lid = str(lid_raw).strip()
        if not lid:
            continue

        fname = lineup_output_name(lid)

        try:
            log_line(log_path, f"Fetching lineup {lid} -> {fname}")
            xml = fetch_listings(api_key, lid, args.days, args.offset)

            if LIMIT_TEXT in (xml or ""):
                any_blocked = True
                log_line(log_path, f"LIMIT HIT for lineup {lid}. Keeping existing files (no overwrite).")
                print(f"SKIP (limit): {fname}")
                continue

            if not looks_like_xmltv(xml):
                any_blocked = True
                snippet = (xml or "").strip().replace("\r", " ").replace("\n", " ")
                snippet = snippet[:240]
                log_line(log_path, f"INVALID PAYLOAD for lineup {lid}. Keeping existing files. Snippet: {snippet}")
                print(f"SKIP (invalid): {fname}")
                continue

            write_all_copies(out_dir, device_dir, publish_dir, fname, xml)

            print(f"Wrote: {out_dir / fname}")
            print(f"Wrote: {device_dir / fname}")
            print(f"Wrote: {publish_dir / fname}")
            log_line(log_path, f"WROTE OK: {fname}")

        except Exception as e:
            any_blocked = True
            log_line(log_path, f"ERROR lineup {lid}: {e}. Keeping existing files.")
            print(f"SKIP (error): {fname}")

    log_line(log_path, "DONE")
    print("DONE")
    print(f"Log: {log_path}")

    return 2 if any_blocked else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
