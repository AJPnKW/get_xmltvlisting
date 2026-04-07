#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[CAPABILITY] cbc_canada_epg=YES

Build a standalone CBC-only XMLTV file from fetched lineup XMLTV sources.
"""
from __future__ import annotations

import copy
import re
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

XML_SOURCES = (
    "Rogers_Toronto_ON_CA_xmltv_10270.xml",
    "Telus_Optik_Vancouver_BC_CA_xmltv_10269.xml",
)

ALLOWLIST = (
    ("CBLT-DT", "Toronto"),
    ("CBUT-DT", "Vancouver"),
    ("CBHT-DT", "Halifax"),
    ("CBWT-DT", "Winnipeg"),
    ("CBRT-DT", "Calgary"),
)


def die(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def canonical_channel_id(callsign: str) -> str:
    return f"cbc.canada.{callsign.lower()}"


def canonical_display_name(callsign: str, city: str) -> str:
    return f"CBC {city} ({callsign})"


def compile_callsign_pattern(callsign: str) -> re.Pattern[str]:
    base = callsign.split("-", 1)[0]
    # Deterministic guard: CBC + callsign token family (base, -DT, -HD).
    return re.compile(rf"\b{re.escape(base)}(?:-DT|-HD)?\b", re.IGNORECASE)


def parse_sources(iptv_dir: Path) -> tuple[dict[str, dict[str, str | None]], list[ET.Element], dict[str, list[str]], dict[str, str]]:
    callsign_meta: dict[str, dict[str, str | None]] = {}
    found_per_source: dict[str, list[str]] = {name: [] for name in XML_SOURCES}
    source_channel_to_callsign: dict[str, str] = {}
    merged_programmes: list[ET.Element] = []
    root_attrs: dict[str, str] = {}

    allow_patterns = {callsign: compile_callsign_pattern(callsign) for callsign, _city in ALLOWLIST}
    city_map = dict(ALLOWLIST)

    for source_name in XML_SOURCES:
        source_path = iptv_dir / source_name
        if not source_path.exists():
            die(f"Missing XML source: {source_path}")

        tree = ET.parse(source_path)
        root = tree.getroot()
        if not root_attrs:
            root_attrs = dict(root.attrib)

        local_channel_map: dict[str, str] = {}

        for channel in root.findall("channel"):
            source_channel_id = (channel.get("id") or "").strip()
            if not source_channel_id:
                continue

            display_names = [((d.text or "").strip()) for d in channel.findall("display-name")]
            callsign_match: str | None = None

            for callsign, _city in ALLOWLIST:
                patt = allow_patterns[callsign]
                matched = any(("CBC" in dn.upper()) and patt.search(dn) for dn in display_names)
                if matched:
                    callsign_match = callsign
                    break

            if not callsign_match:
                continue

            local_channel_map[source_channel_id] = callsign_match
            if callsign_match not in found_per_source[source_name]:
                found_per_source[source_name].append(callsign_match)

            if callsign_match not in callsign_meta:
                icon = channel.find("icon")
                icon_src = None
                if icon is not None:
                    icon_src = (icon.get("src") or "").strip() or None
                callsign_meta[callsign_match] = {
                    "channel_id": canonical_channel_id(callsign_match),
                    "display_name": canonical_display_name(callsign_match, city_map[callsign_match]),
                    "icon_src": icon_src,
                }

        for source_channel_id, callsign in local_channel_map.items():
            source_channel_to_callsign[source_channel_id] = callsign

        for programme in root.findall("programme"):
            source_channel_id = (programme.get("channel") or "").strip()
            callsign = source_channel_to_callsign.get(source_channel_id)
            if not callsign:
                continue
            clone = copy.deepcopy(programme)
            clone.set("channel", canonical_channel_id(callsign))
            merged_programmes.append(clone)

    missing_callsigns = [callsign for callsign, _city in ALLOWLIST if callsign not in callsign_meta]
    if missing_callsigns:
        die("Missing callsigns in XML sources: " + ", ".join(missing_callsigns))

    for source_name in found_per_source:
        found_per_source[source_name].sort()

    return callsign_meta, merged_programmes, found_per_source, root_attrs


def build_output_xml(
    callsign_meta: dict[str, dict[str, str | None]],
    merged_programmes: list[ET.Element],
    root_attrs: dict[str, str],
) -> tuple[ET.ElementTree, dict[str, int], str, str, list[str]]:
    tv = ET.Element("tv", root_attrs)

    channel_ids: list[str] = []
    callsign_to_channel_id = {callsign: meta["channel_id"] for callsign, meta in callsign_meta.items()}
    channel_id_to_callsign = {channel_id: callsign for callsign, channel_id in callsign_to_channel_id.items()}

    for callsign, city in ALLOWLIST:
        meta = callsign_meta[callsign]
        channel_id = str(meta["channel_id"])
        display_name = str(meta["display_name"])
        channel_ids.append(channel_id)

        channel_el = ET.SubElement(tv, "channel", {"id": channel_id})
        dn_el = ET.SubElement(channel_el, "display-name")
        dn_el.text = display_name
        icon_src = meta.get("icon_src")
        if icon_src:
            ET.SubElement(channel_el, "icon", {"src": str(icon_src)})

    seen = set()
    deduped: list[ET.Element] = []
    for programme in merged_programmes:
        key = ET.tostring(programme, encoding="unicode")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(programme)

    deduped.sort(key=lambda p: (p.get("channel", ""), p.get("start", ""), p.get("stop", "")))
    for programme in deduped:
        tv.append(programme)

    programme_counts = {callsign: 0 for callsign, _city in ALLOWLIST}
    starts: list[str] = []
    stops: list[str] = []
    for programme in deduped:
        channel_id = programme.get("channel", "")
        callsign = channel_id_to_callsign.get(channel_id)
        if callsign:
            programme_counts[callsign] += 1
        start = (programme.get("start") or "").strip()
        stop = (programme.get("stop") or "").strip()
        if start:
            starts.append(start)
        if stop:
            stops.append(stop)

    earliest_start = min(starts) if starts else ""
    latest_stop = max(stops) if stops else ""

    tree = ET.ElementTree(tv)
    ET.indent(tree, space="  ")
    return tree, programme_counts, earliest_start, latest_stop, channel_ids


def write_xml(tree: ET.ElementTree, out_path: Path) -> None:
    body = ET.tostring(tree.getroot(), encoding="unicode")
    text = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE tv SYSTEM "xmltv.dtd">\n' + body + "\n"
    out_path.write_text(text, encoding="utf-8", newline="\n")


def main(argv: list[str]) -> int:
    if argv:
        die("This script does not accept arguments; it uses fixed inputs/outputs.")

    repo = Path(__file__).resolve().parents[1]
    iptv_dir = repo / "IPTV"
    out_path = iptv_dir / "CBC_Canada.xml"

    callsign_meta, merged_programmes, found_per_source, root_attrs = parse_sources(iptv_dir)
    tree, programme_counts, earliest_start, latest_stop, output_channel_ids = build_output_xml(
        callsign_meta, merged_programmes, root_attrs
    )
    write_xml(tree, out_path)

    print(f"Wrote: {out_path}")
    print("Callsigns found per source:")
    for source_name in XML_SOURCES:
        found = found_per_source[source_name]
        print(f"- {source_name}: {', '.join(found) if found else '(none)'}")
    print("Programme count per callsign:")
    for callsign, _city in ALLOWLIST:
        print(f"- {callsign}: {programme_counts[callsign]}")
    print(f"Earliest start: {earliest_start or '(none)'}")
    print(f"Latest stop: {latest_stop or '(none)'}")
    print("Output channel ids:")
    for channel_id in output_channel_ids:
        print(f"- {channel_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

