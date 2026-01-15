#!/usr/bin/env python3
import os
import xml.etree.ElementTree as ET
import csv
import re

# ---------------------------------------------------------
# DETECT REPO ROOT
# ---------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

IPTV_DIR = os.path.join(REPO_ROOT, "IPTV")
OUTPUT_DIR = os.path.join(REPO_ROOT, "output")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------
# INPUT FILES (relative to IPTV folder)
# ---------------------------------------------------------
INPUT_FILES = {
    "channels_CA_Rogers.tsv": "Rogers_Toronto_ON_CA_channels_10270.xml",
    "channels_CA_Telus.tsv": "Telus_Optik_Vancouver_BC_CA_channels_10269.xml",
    "channels_US_Xfinity.tsv": "Xfinity_Chicago_IL_US_channels_10271.xml",
    "channels_US_Verizon.tsv": "Verizon_FIOS_NewYork_NY_US_channels_10273.xml",
    "channels_US_Broadcast.tsv": "Broadcast_LosAngeles_CA_US_channels_10272.xml"
}

OUTPUT_FIELDS = [
    "provider",
    "xmltv_id",
    "channel_number",
    "canonical_name",
    "alt_names",
    "country",
    "region",
    "category",
    "edge_case",
    "exclude",
    "hd_flag",
    "duplicate_flag",
    "network_group",
    "icon_url",
    "url",
    "notes"
]

# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def detect_country(name):
    if any(us in name for us in ["Seattle", "Buffalo", "Boston", "Detroit", "Los Angeles", "New York", "Tacoma", "Spokane"]):
        return "US"
    return "CA"

def detect_region(name):
    m = re.search(r"\((.*?)\)", name)
    return m.group(1) if m else ""

def detect_category(name):
    name_lower = name.lower()
    if "news" in name_lower or "cbc news" in name_lower:
        return "News"
    if "sports" in name_lower or "tsn" in name_lower or "sportsnet" in name_lower:
        return "Sports"
    if "movie" in name_lower or "hollywood" in name_lower or "starz" in name_lower:
        return "Movies"
    if "kids" in name_lower or "cartoon" in name_lower:
        return "Kids"
    if "music" in name_lower or "much" in name_lower or "mtv" in name_lower:
        return "Music"
    if "demand" in name_lower:
        return "OnDemand"
    if "relig" in name_lower:
        return "Religious"
    return "Entertainment"

def detect_network_group(name):
    if "CBC" in name: return "CBC"
    if "CTV" in name: return "CTV"
    if "Global" in name: return "Global"
    if "CITY" in name or "Citytv" in name: return "Citytv"
    if "Corus" in name or "Slice" in name or "W Network" in name: return "Corus"
    if "FX" in name or "FXX" in name: return "FX"
    if "PBS" in name: return "PBS"
    if any(x in name for x in ["ABC", "CBS", "NBC", "FOX"]):
        return "US Network"
    return "Specialty"

def is_edge_case(name):
    return any(x in name for x in ["CP24", "CBC News", "CNN", "CNBC", "PBS"])

def is_excluded(name):
    name_lower = name.lower()
    return ("demand" in name_lower) or ("relig" in name_lower)

def is_hd(name):
    return "HD" in name or "-HD" in name

# ---------------------------------------------------------
# MAIN PARSER
# ---------------------------------------------------------

def parse_xml_to_rows(provider, xmlfile):
    rows = []
    seen_ids = set()

    tree = ET.parse(xmlfile)
    root = tree.getroot()

    for ch in root.findall("channel"):
        xmltv_id = ch.attrib.get("id", "")
        display_names = [d.text for d in ch.findall("display-name") if d.text]

        if not display_names:
            continue

        canonical = display_names[0]
        alt = display_names[1:]

        # Extract channel number
        channel_number = ""
        for d in display_names:
            if d.isdigit():
                channel_number = d
                break

        country = detect_country(canonical)
        region = detect_region(canonical)
        category = detect_category(canonical)
        edge = is_edge_case(canonical)
        exclude = is_excluded(canonical)
        hd = is_hd(canonical)
        network = detect_network_group(canonical)
        duplicate = xmltv_id in seen_ids
        if not duplicate:
            seen_ids.add(xmltv_id)

        icon = ""
        icon_tag = ch.find("icon")
        if icon_tag is not None:
            icon = icon_tag.attrib.get("src", "")

        url = ""
        url_tag = ch.find("url")
        if url_tag is not None:
            url = url_tag.text or ""

        notes = ""
        if duplicate:
            notes = "Duplicate channel ID"
        if exclude:
            notes = "Excluded (OnDemand/Religious)"

        rows.append({
            "provider": provider,
            "xmltv_id": xmltv_id,
            "channel_number": channel_number,
            "canonical_name": canonical,
            "alt_names": "|".join(alt),
            "country": country,
            "region": region,
            "category": category,
            "edge_case": str(edge),
            "exclude": str(exclude),
            "hd_flag": str(hd),
            "duplicate_flag": str(duplicate),
            "network_group": network,
            "icon_url": icon,
            "url": url,
            "notes": notes
        })

    return rows

# ---------------------------------------------------------
# EXECUTION
# ---------------------------------------------------------

for outfile, infile in INPUT_FILES.items():
    provider = outfile.split("_")[1]  # CA or US

    xml_path = os.path.join(IPTV_DIR, infile)
    out_path = os.path.join(OUTPUT_DIR, outfile)

    print(f"Processing {xml_path} → {out_path}")

    rows = parse_xml_to_rows(provider, xml_path)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

print("Done. All TSV files created in /output/")
