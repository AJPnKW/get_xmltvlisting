from __future__ import annotations

import argparse
import csv
import datetime as _dt
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple


@dataclass(frozen=True)
class Channel:
    channel_id: str
    names: Tuple[str, ...]


def _safe_mkdir(p: str) -> None:
    os.makedirs(p, exist_ok=True)


def _read_xmltv_channels(path: str) -> Dict[str, Channel]:
    # XMLTV format: <tv> ... <channel id="..."><display-name>...</display-name>...</channel> ...
    # Use iterparse to keep memory stable.
    channels: Dict[str, Channel] = {}

    try:
        context = ET.iterparse(path, events=("end",))
    except ET.ParseError as e:
        raise RuntimeError(f"XML parse failed: {path}: {e}") from e

    for event, elem in context:
        if elem.tag != "channel":
            continue

        channel_id = (elem.get("id") or "").strip()
        if not channel_id:
            elem.clear()
            continue

        names: List[str] = []
        for dn in elem.findall("display-name"):
            if dn.text:
                t = " ".join(dn.text.split()).strip()
                if t and t not in names:
                    names.append(t)

        channels[channel_id] = Channel(channel_id=channel_id, names=tuple(names))
        elem.clear()

    return channels


def _short_label(filename: str) -> str:
    # xmltv-9328.xml -> 9328
    m = re.search(r"xmltv-(\d+)\.xml$", filename, flags=re.IGNORECASE)
    return m.group(1) if m else os.path.basename(filename)


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _write_csv(path: str, header: List[str], rows: Iterable[List[str]]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


def analyze(files: List[str], out_dir: str) -> int:
    _safe_mkdir(out_dir)

    parsed: Dict[str, Dict[str, Channel]] = {}
    for fp in files:
        key = _short_label(os.path.basename(fp))
        parsed[key] = _read_xmltv_channels(fp)

    keys = sorted(parsed.keys(), key=lambda x: (len(x), x))
    sets: Dict[str, Set[str]] = {k: set(parsed[k].keys()) for k in keys}

    # Summary
    summary_rows: List[List[str]] = []
    for k in keys:
        summary_rows.append([k, str(len(sets[k]))])

    _write_csv(
        os.path.join(out_dir, "summary_channels_by_lineup.csv"),
        ["lineup_id", "channel_count"],
        summary_rows,
    )

    # Overlap matrix (counts + jaccard)
    matrix_counts: List[List[str]] = []
    matrix_jacc: List[List[str]] = []

    header = ["lineup_id"] + keys
    for a in keys:
        row_c = [a]
        row_j = [a]
        for b in keys:
            inter = len(sets[a] & sets[b])
            row_c.append(str(inter))
            row_j.append(f"{_jaccard(sets[a], sets[b]):.4f}")
        matrix_counts.append(row_c)
        matrix_jacc.append(row_j)

    _write_csv(os.path.join(out_dir, "overlap_counts_matrix.csv"), header, matrix_counts)
    _write_csv(os.path.join(out_dir, "overlap_jaccard_matrix.csv"), header, matrix_jacc)

    # Unique channels per lineup (ids + best name)
    for k in keys:
        others = set().union(*(sets[o] for o in keys if o != k))
        uniq = sorted(sets[k] - others)
        rows: List[List[str]] = []
        for cid in uniq:
            ch = parsed[k].get(cid)
            best_name = ch.names[0] if ch and ch.names else ""
            rows.append([cid, best_name])
        _write_csv(
            os.path.join(out_dir, f"unique_channels_{k}.csv"),
            ["channel_id", "display_name"],
            rows,
        )

    # Print compact console report
    print("")
    print("XMLTV overlap analysis")
    print(f"OutDir: {out_dir}")
    print("")
    print("Channel counts:")
    for k in keys:
        print(f"  {k}: {len(sets[k])}")

    print("")
    print("Top overlaps (by intersection count):")
    pairs: List[Tuple[int, str, str]] = []
    for i, a in enumerate(keys):
        for b in keys[i + 1 :]:
            pairs.append((len(sets[a] & sets[b]), a, b))
    pairs.sort(reverse=True)
    for n, a, b in pairs[:10]:
        print(f"  {a} ∩ {b}: {n}")

    print("")
    print("Files written:")
    print("  summary_channels_by_lineup.csv")
    print("  overlap_counts_matrix.csv")
    print("  overlap_jaccard_matrix.csv")
    for k in keys:
        print(f"  unique_channels_{k}.csv")

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="xmltv_analyze", add_help=True)
    ap.add_argument("--input_dir", required=True, help="Folder containing xmltv-*.xml files")
    ap.add_argument("--out_dir", required=True, help="Output folder for CSV reports")

    args = ap.parse_args(argv)

    in_dir = os.path.abspath(args.input_dir)
    out_dir = os.path.abspath(args.out_dir)

    if not os.path.isdir(in_dir):
        print(f"ERROR: input_dir not found: {in_dir}", file=sys.stderr)
        return 2

    files = [
        os.path.join(in_dir, f)
        for f in os.listdir(in_dir)
        if re.match(r"(?i)^xmltv-\d+\.xml$", f)
    ]
    files.sort()

    if not files:
        print(f"ERROR: no xmltv-*.xml files found in: {in_dir}", file=sys.stderr)
        return 2

    return analyze(files, out_dir)


if __name__ == "__main__":
    raise SystemExit(main())
