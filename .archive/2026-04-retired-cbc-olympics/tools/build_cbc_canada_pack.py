#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FILE: tools/build_cbc_canada_pack.py
VERSION: 1.1.0
UPDATED: 2026-02-12T00:00:00Z
CHANGE NOTES:
- Fixes M3U matching: no longer requires "CBC <City> (CALLSIGN)" formatting.
- Callsign detection now checks tvg-id, tvg-name, display text, group-title for:
  - base token (cblt/cbut/cbht/cbwt/cbrt) and optional -DT/-HD
  - city fallback when "CBC" appears (Toronto/Vancouver/Halifax/Winnipeg/Calgary)
- Preserves deterministic allow-list + per-callsign ALT handling (distinct URLs only).
- Outputs remain:
  - IPTV/CBC_Canada.m3u
  - IPTV/CBC_Canada.xml

[CAPABILITY] cbc_canada_pack=YES
"""
from __future__ import annotations

import argparse
import copy
import re
import sys
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET

XML_SOURCES = (
    "Rogers_Toronto_ON_CA_xmltv_10270.xml",
    "Telus_Optik_Vancouver_BC_CA_xmltv_10269.xml",
)

# Explicit allow-list requested: Toronto + backup CBC stations.
ALLOWLIST = (
    ("CBLT-DT", "Toronto"),
    ("CBUT-DT", "Vancouver"),
    ("CBHT-DT", "Halifax"),
    ("CBWT-DT", "Winnipeg"),
    ("CBRT-DT", "Calgary"),
)

CALLSIGN_TO_CITY = {callsign: city for callsign, city in ALLOWLIST}
BASE_NAME_BY_CALLSIGN = {callsign: f"CBC {city} ({callsign})" for callsign, city in ALLOWLIST}
CITY_BY_CALLSIGN = {callsign: city for callsign, city in ALLOWLIST}


@dataclass(frozen=True)
class ChannelDef:
    callsign: str
    source_channel_id: str
    xml_channel_id: str
    display_name: str
    icon_src: str | None


@dataclass
class M3UEntry:
    extinf: str
    url: str
    attrs: dict[str, str]
    tvg_name: str
    tvg_id: str
    group_title: str
    display_text: str


def die(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iptv-dir", default="IPTV", help="Directory containing XML inputs and output artifacts.")
    parser.add_argument("--source-m3u", default="IPTV/provider.m3u", help="Source provider M3U path.")
    return parser.parse_args(argv)


def canonical_name(callsign: str) -> str:
    return BASE_NAME_BY_CALLSIGN[callsign]


def xml_channel_id_from_callsign(callsign: str) -> str:
    return f"cbc.canada.{callsign.lower()}"


def compile_callsign_pattern(callsign: str) -> re.Pattern[str]:
    # Callsign family token: base, -DT, -HD. Match as word boundary where possible.
    base = callsign.split("-", 1)[0]  # CBLT
    # Accept: CBLT, CBLT-DT, CBLT-HD, cblt_dt etc (some playlists are messy)
    return re.compile(rf"\b{re.escape(base)}(?:[-_ ]?(?:DT|HD))?\b", re.IGNORECASE)


def compile_city_pattern(city: str) -> re.Pattern[str]:
    return re.compile(rf"\b{re.escape(city)}\b", re.IGNORECASE)


ALLOW_CALLSIGN_PATTERNS = {callsign: compile_callsign_pattern(callsign) for callsign, _ in ALLOWLIST}
ALLOW_CITY_PATTERNS = {callsign: compile_city_pattern(city) for callsign, city in ALLOWLIST}


def parse_callsign_from_text(text: str) -> str | None:
    """
    Determine which allow-listed callsign the text refers to.

    Rule:
    - Prefer explicit callsign token hits (CBLT/CBLT-DT/etc) anywhere.
    - If no callsign token, allow city fallback only when 'CBC' appears.
    """
    t = (text or "").strip()
    if not t:
        return None

    # 1) Callsign token hit (does NOT require 'CBC' word)
    for callsign, _city in ALLOWLIST:
        if ALLOW_CALLSIGN_PATTERNS[callsign].search(t):
            return callsign

    # 2) City fallback only if CBC appears
    if "CBC" in t.upper():
        for callsign, _city in ALLOWLIST:
            if ALLOW_CITY_PATTERNS[callsign].search(t):
                return callsign

    return None


def extract_cbc_channels_from_xml(xml_path: Path) -> tuple[dict[str, ChannelDef], set[str]]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    result: dict[str, ChannelDef] = {}
    found_callsigns: set[str] = set()

    for channel in root.findall("channel"):
        source_id = (channel.get("id") or "").strip()
        if not source_id:
            continue

        display_names = [((dn.text or "").strip()) for dn in channel.findall("display-name")]
        matched_callsign: str | None = None

        for dn in display_names:
            cs = parse_callsign_from_text(dn)
            if cs:
                matched_callsign = cs
                break

        if not matched_callsign:
            continue

        found_callsigns.add(matched_callsign)

        icon = channel.find("icon")
        icon_src = (icon.get("src") or "").strip() if icon is not None else ""
        if matched_callsign not in result:
            result[matched_callsign] = ChannelDef(
                callsign=matched_callsign,
                source_channel_id=source_id,
                xml_channel_id=xml_channel_id_from_callsign(matched_callsign),
                display_name=canonical_name(matched_callsign),
                icon_src=icon_src or None,
            )

    return result, found_callsigns


def collect_channels(iptv_dir: Path) -> tuple[dict[str, ChannelDef], dict[str, list[str]]]:
    collected: dict[str, ChannelDef] = {}
    found_per_source: dict[str, list[str]] = {}
    for source_name in XML_SOURCES:
        source_path = iptv_dir / source_name
        if not source_path.exists():
            die(f"Missing XML source: {source_path}")
        extracted, found_callsigns = extract_cbc_channels_from_xml(source_path)
        found_per_source[source_name] = sorted(found_callsigns)
        for callsign, channel_def in extracted.items():
            if callsign not in collected:
                collected[callsign] = channel_def

    missing = [cs for cs, _city in ALLOWLIST if cs not in collected]
    if missing:
        die("Missing callsigns in XML inputs (allow-list not found): " + ", ".join(missing))
    return collected, found_per_source


def parse_extinf(line: str) -> tuple[dict[str, str], str]:
    content = line.strip()
    if not content.startswith("#EXTINF:"):
        return {}, ""
    body = content.split(":", 1)[1]
    if "," in body:
        attrs_part, display = body.split(",", 1)
    else:
        attrs_part, display = body, ""
    attrs: dict[str, str] = {}
    for key, value in re.findall(r'([A-Za-z0-9_-]+)="([^"]*)"', attrs_part):
        attrs[key] = value
    return attrs, display.strip()


def build_extinf(attrs: dict[str, str], display_text: str) -> str:
    ordered = []
    for key in ("tvg-id", "tvg-name", "tvg-logo", "group-title"):
        if key in attrs and attrs[key] != "":
            ordered.append(f'{key}="{attrs[key]}"')
    remaining = [k for k in attrs.keys() if k not in {"tvg-id", "tvg-name", "tvg-logo", "group-title"}]
    for key in sorted(remaining):
        if attrs[key] != "":
            ordered.append(f'{key}="{attrs[key]}"')
    attrs_blob = " ".join(ordered)
    if attrs_blob:
        return f"#EXTINF:-1 {attrs_blob},{display_text}"
    return f"#EXTINF:-1,{display_text}"


def parse_m3u_entries(source_m3u: Path) -> list[M3UEntry]:
    if not source_m3u.exists():
        die(f"Missing source M3U: {source_m3u}")
    lines = source_m3u.read_text(encoding="utf-8", errors="replace").splitlines()
    entries: list[M3UEntry] = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF:"):
            attrs, display_text = parse_extinf(line)
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or lines[j].strip().startswith("#")):
                j += 1
            if j >= len(lines):
                die(f"Malformed M3U: missing stream URL after EXTINF at line {i + 1}")
            url = lines[j].strip()
            entries.append(
                M3UEntry(
                    extinf=line,
                    url=url,
                    attrs=attrs,
                    tvg_name=(attrs.get("tvg-name") or "").strip(),
                    tvg_id=(attrs.get("tvg-id") or "").strip(),
                    group_title=(attrs.get("group-title") or "").strip(),
                    display_text=display_text,
                )
            )
            i = j + 1
            continue
        i += 1
    return entries


def entry_callsign(entry: M3UEntry) -> str | None:
    # Check multiple fields; provider playlists vary wildly.
    fields = [
        entry.tvg_id,
        entry.tvg_name,
        entry.display_text,
        entry.group_title,
    ]
    for f in fields:
        cs = parse_callsign_from_text(f)
        if cs:
            return cs
    # Combined fallback (covers cases where parts are split across fields)
    combo = " | ".join([x for x in fields if x])
    return parse_callsign_from_text(combo)


def select_cbc_m3u_entries(entries: list[M3UEntry], channels: dict[str, ChannelDef]) -> tuple[list[M3UEntry], dict[str, int]]:
    # Preserve encounter order per callsign, then dedupe by URL.
    by_callsign: dict[str, list[M3UEntry]] = {cs: [] for cs in channels.keys()}
    for entry in entries:
        callsign = entry_callsign(entry)
        if not callsign:
            continue
        if callsign in by_callsign:
            by_callsign[callsign].append(entry)

    distinct_by_callsign: dict[str, list[M3UEntry]] = {}
    for callsign, channel_entries in by_callsign.items():
        seen_urls: set[str] = set()
        distinct_entries: list[M3UEntry] = []
        for entry in channel_entries:
            url = entry.url.strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            distinct_entries.append(entry)
        distinct_by_callsign[callsign] = distinct_entries

    missing = [callsign for callsign, channel_entries in distinct_by_callsign.items() if not channel_entries]
    if missing:
        die("Missing channels in source M3U for allow-list callsigns: " + ", ".join(sorted(missing)))

    selected: list[M3UEntry] = []
    stream_url_counts: dict[str, int] = {}

    for callsign, _city in ALLOWLIST:
        channel_entries = distinct_by_callsign[callsign]
        stream_url_counts[callsign] = len(channel_entries)
        canonical_logo = channels[callsign].icon_src
        if not canonical_logo:
            first_entry_logo = (channel_entries[0].attrs.get("tvg-logo") or "").strip()
            canonical_logo = first_entry_logo or None

        base_name = BASE_NAME_BY_CALLSIGN[callsign]
        for idx, entry in enumerate(channel_entries, start=1):
            attrs = dict(entry.attrs)
            attrs["tvg-id"] = channels[callsign].xml_channel_id
            display_name = base_name if idx == 1 else f"{base_name} ALT-{idx - 1}"
            attrs["tvg-name"] = display_name
            attrs["group-title"] = "CBC Canada"
            if canonical_logo:
                attrs["tvg-logo"] = canonical_logo
            elif "tvg-logo" in attrs:
                del attrs["tvg-logo"]

            selected.append(
                M3UEntry(
                    extinf=build_extinf(attrs, display_name),
                    url=entry.url,
                    attrs=attrs,
                    tvg_name=display_name,
                    tvg_id=channels[callsign].xml_channel_id,
                    group_title=attrs["group-title"],
                    display_text=display_name,
                )
            )

    return selected, stream_url_counts


def write_cbc_m3u(m3u_entries: list[M3UEntry], output_path: Path) -> None:
    lines = ['#EXTM3U x-tvg-url="CBC_Canada.xml"']
    for entry in m3u_entries:
        lines.append(entry.extinf)
        lines.append(entry.url)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def build_cbc_xml(iptv_dir: Path, channels: dict[str, ChannelDef], selected_ids: set[str], output_path: Path) -> dict[str, int]:
    combined_attrs: dict[str, str] = {}
    combined_programmes: list[ET.Element] = []

    source_id_to_callsign = {ch.source_channel_id: ch.callsign for ch in channels.values()}

    for source_name in XML_SOURCES:
        source_path = iptv_dir / source_name
        tree = ET.parse(source_path)
        root = tree.getroot()
        if not combined_attrs:
            combined_attrs = dict(root.attrib)

        for programme in root.findall("programme"):
            source_channel_id = (programme.get("channel") or "").strip()
            callsign = source_id_to_callsign.get(source_channel_id)
            if not callsign:
                continue
            target_channel_id = channels[callsign].xml_channel_id
            if target_channel_id not in selected_ids:
                continue
            clone = copy.deepcopy(programme)
            clone.set("channel", target_channel_id)
            combined_programmes.append(clone)

    tv = ET.Element("tv", combined_attrs)

    channel_defs_for_output = sorted(
        [ch for ch in channels.values() if ch.xml_channel_id in selected_ids],
        key=lambda c: c.display_name,
    )
    for ch in channel_defs_for_output:
        channel_el = ET.SubElement(tv, "channel", {"id": ch.xml_channel_id})
        display_name = ET.SubElement(channel_el, "display-name")
        display_name.text = ch.display_name
        if ch.icon_src:
            ET.SubElement(channel_el, "icon", {"src": ch.icon_src})

    seen: set[str] = set()
    deduped: list[ET.Element] = []
    for programme in combined_programmes:
        key = ET.tostring(programme, encoding="unicode")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(programme)

    deduped.sort(key=lambda p: (p.get("channel", ""), p.get("start", ""), p.get("stop", "")))
    for programme in deduped:
        tv.append(programme)

    programme_counts: dict[str, int] = {callsign: 0 for callsign in channels.keys()}
    xml_id_to_callsign = {ch.xml_channel_id: ch.callsign for ch in channels.values()}
    for programme in deduped:
        ch_id = programme.get("channel", "")
        callsign = xml_id_to_callsign.get(ch_id)
        if callsign:
            programme_counts[callsign] += 1

    tree = ET.ElementTree(tv)
    ET.indent(tree, space="  ")
    body = ET.tostring(tv, encoding="unicode")
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE tv SYSTEM "xmltv.dtd">\n' + body + "\n"
    output_path.write_text(xml, encoding="utf-8", newline="\n")
    return programme_counts


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    iptv_dir = Path(args.iptv_dir).resolve()
    source_m3u = Path(args.source_m3u).resolve()

    channels, found_per_source = collect_channels(iptv_dir)
    source_entries = parse_m3u_entries(source_m3u)
    selected_entries, stream_url_counts = select_cbc_m3u_entries(source_entries, channels)

    m3u_output = iptv_dir / "CBC_Canada.m3u"
    xml_output = iptv_dir / "CBC_Canada.xml"

    write_cbc_m3u(selected_entries, m3u_output)
    selected_ids = {entry.tvg_id for entry in selected_entries}
    programme_counts = build_cbc_xml(iptv_dir, channels, selected_ids, xml_output)

    print(f"Wrote: {m3u_output}")
    print(f"Wrote: {xml_output}")
    print(f"CBC entries: {len(selected_entries)}")
    print(f"CBC channels: {len(selected_ids)}")
    print("")
    print("Report: callsigns found per XML source")
    for source_name in XML_SOURCES:
        found = found_per_source.get(source_name, [])
        print(f"- {source_name}: {', '.join(found) if found else '(none)'}")
    print("Report: programmes per callsign")
    for callsign, _city in ALLOWLIST:
        print(f"- {callsign}: {programme_counts.get(callsign, 0)}")
    print("Report: stream URLs per callsign (primary + ALTs)")
    for callsign, _city in ALLOWLIST:
        print(f"- {callsign}: {stream_url_counts.get(callsign, 0)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
