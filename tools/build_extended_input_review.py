#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import quote

from bs4 import BeautifulSoup


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def text_of(node) -> str:
    if node is None:
        return ""
    return " ".join(node.stripped_strings)


def infer_country(section_id: str, section_title: str) -> str:
    text = f"{section_id} {section_title}".lower()
    if "uk" in text or "freeview" in text or "freesat" in text:
        return "UK"
    if "au" in text or "australia" in text:
        return "AU"
    if "us" in text or "usa" in text:
        return "US"
    if "ca" in text or "canada" in text:
        return "CA"
    return "GLOBAL"


def infer_scope_hint(name: str, notes: str, section_title: str, article_title: str) -> str:
    text = f"{name} {notes} {section_title} {article_title}".lower()
    if any(token in text for token in ["london", "scotland", "wales", "northern ireland", "granada", "regional", "stv", "s4c", "utv", "ni"]):
        return "regional"
    if any(token in text for token in ["main ", "flagship", "core", "national"]):
        return "core"
    return "optional"


def infer_call_sign(name: str, tvg_id: str) -> str:
    if tvg_id:
        return re.split(r"[._-]+", tvg_id)[0].upper()
    return re.sub(r"[^A-Za-z0-9]+", "", name).upper()


def infer_type(scope_hint: str, platforms: list[str], section_title: str) -> str:
    text = " ".join(platforms + [section_title]).lower()
    if scope_hint == "regional":
        return "Regional"
    if "freesat" in text:
        return "FTA Satellite"
    if "freeview" in text:
        return "FTA Terrestrial"
    if "fast" in text:
        return "FAST"
    return "National"


def classify_code(code_text: str) -> str:
    stripped = code_text.lstrip()
    if stripped.startswith("#EXTM3U"):
        return "m3u"
    if stripped.startswith("{"):
        return "json"
    if stripped.startswith("<") or stripped.startswith("&lt;"):
        return "xmltv"
    return "text"


def parse_source(source_path: Path) -> dict:
    soup = BeautifulSoup(source_path.read_text(encoding="utf-8"), "html.parser")
    source_uri = source_path.resolve().as_uri()
    channels_by_id: dict[str, dict] = {}
    sections_summary: list[dict] = []
    code_blocks: list[dict] = []

    nav_links = []
    for anchor in soup.select("a[href^='#']"):
        href = (anchor.get("href") or "").strip()
        if href:
            nav_links.append({
                "label": text_of(anchor),
                "href": href,
                "absolute_href": f"{source_uri}{href}",
            })

    for section in soup.select("section.section[id]"):
        section_id = (section.get("id") or "").strip()
        section_title = text_of(section.find("h2")) or section_id
        section_href = f"{source_uri}#{quote(section_id)}"
        country = infer_country(section_id, section_title)
        section_channel_ids: set[str] = set()
        article_count = 0
        table_count = 0

        for article in section.select("article.panel"):
            article_count += 1
            article_title = text_of(article.select_one(".panel-title")) or section_title
            article_subtitle = text_of(article.select_one(".panel-subtitle"))

            for table in article.select("table"):
                table_count += 1
                headers = [text_of(th) for th in table.select("thead th")]
                if "Channel" not in headers or "tvg-id" not in headers:
                    continue

                for tr in table.select("tbody tr"):
                    tds = tr.find_all("td")
                    if not tds:
                        continue
                    row = {}
                    logo_url = ""
                    for idx, td in enumerate(tds):
                        key = headers[idx] if idx < len(headers) else f"column_{idx + 1}"
                        row[key] = text_of(td)
                        img = td.find("img")
                        if img and not logo_url:
                            logo_url = (img.get("src") or "").strip()

                    name = (row.get("Channel") or "").strip()
                    tvg_id = (row.get("tvg-id") or "").strip()
                    notes = (row.get("Notes") or row.get("Category") or row.get("Region") or "").strip()
                    if not name and not tvg_id:
                        continue

                    channel_key = tvg_id or name
                    section_channel_ids.add(channel_key)
                    item = channels_by_id.setdefault(channel_key, {
                        "channel_name": name,
                        "name": name,
                        "tvg_id": tvg_id,
                        "call_sign": infer_call_sign(name, tvg_id),
                        "channel_number": "",
                        "country": country,
                        "network": "",
                        "broadcaster": "",
                        "channel_type": "",
                        "platforms": [],
                        "lineups": [],
                        "sections": [],
                        "article_titles": [],
                        "source_links": [],
                        "logo_urls": [],
                        "source_notes": [],
                        "scope_hint": "optional",
                    })

                    network = article_title.split("(")[0].replace("Channels", "").replace("Full Set", "").strip()
                    network = network or country
                    section_platform = section_title.split("(")[0].strip()
                    scope_hint = infer_scope_hint(name, notes, section_title, article_title)

                    item["country"] = item["country"] or country
                    item["network"] = item["network"] or network
                    item["broadcaster"] = item["broadcaster"] or network
                    item["scope_hint"] = scope_hint if item["scope_hint"] != "regional" else item["scope_hint"]
                    if section_platform and section_platform not in item["platforms"]:
                        item["platforms"].append(section_platform)
                    if article_title and article_title not in item["lineups"]:
                        item["lineups"].append(article_title)
                    if section_title and section_title not in item["sections"]:
                        item["sections"].append(section_title)
                    if article_title and article_title not in item["article_titles"]:
                        item["article_titles"].append(article_title)
                    if notes and notes not in item["source_notes"]:
                        item["source_notes"].append(notes)
                    if logo_url and logo_url not in item["logo_urls"]:
                        item["logo_urls"].append(logo_url)

                    source_link = {
                        "section_id": section_id,
                        "section_title": section_title,
                        "article_title": article_title,
                        "href": section_href,
                    }
                    if source_link not in item["source_links"]:
                        item["source_links"].append(source_link)

            for code in article.select("pre > code"):
                code_text = code.get_text("\n", strip=False)
                code_blocks.append({
                    "section_id": section_id,
                    "section_title": section_title,
                    "article_title": article_title,
                    "article_subtitle": article_subtitle,
                    "href": section_href,
                    "kind": classify_code(code_text),
                    "preview": code_text[:280].strip(),
                    "length": len(code_text),
                })

        sections_summary.append({
            "section_id": section_id,
            "section_title": section_title,
            "country": country,
            "href": section_href,
            "channel_count": len(section_channel_ids),
            "article_count": article_count,
            "table_count": table_count,
        })

    channels = list(channels_by_id.values())
    for item in channels:
        item["channel_type"] = infer_type(item["scope_hint"], item["platforms"], " ".join(item["sections"]))
        item["notes"] = " | ".join(item["source_notes"])

    channels.sort(key=lambda row: (
        row["country"],
        row["network"].lower(),
        row["name"].lower(),
        row["tvg_id"].lower(),
    ))

    kind_counts = dict(Counter(block["kind"] for block in code_blocks))
    return {
        "source_file": str(source_path),
        "source_uri": source_uri,
        "nav_links": nav_links,
        "sections": sections_summary,
        "channels": channels,
        "code_blocks": code_blocks,
        "code_kind_counts": kind_counts,
    }


def replace_embedded_json(html_text: str, channels: list[dict], source_file: str, source_uri: str) -> str:
    replacement = (
        f'<script type="application/json" id="channelData">{html.escape(json.dumps(channels, ensure_ascii=False))}</script>'
    )
    html_text = re.sub(
        r'<script type="application/json" id="channelData">.*?</script>',
        lambda _: replacement,
        html_text,
        count=1,
        flags=re.S,
    )
    source_line = (
        f'<p class="small" style="margin-top: 10px;">'
        f'Use this page for UK and AU from the input HTML. '
        f'Source file: <a href="{html.escape(source_uri)}">{html.escape(source_file)}</a>. '
        f'The separate repo validator reflects existing repo inventory, which is why UK and AU are not showing there.'
        f'</p>'
    )
    html_text = re.sub(
        r'<p class="small" style="margin-top: 10px;">.*?</p>',
        lambda _: source_line,
        html_text,
        count=1,
        flags=re.S,
    )
    return html_text


def render_report(payload: dict) -> str:
    section_rows = "\n".join(
        f"<tr><td><a href=\"{html.escape(row['href'])}\">{html.escape(row['section_title'])}</a></td><td>{html.escape(row['country'])}</td><td>{row['channel_count']}</td><td>{row['article_count']}</td><td>{row['table_count']}</td></tr>"
        for row in payload["sections"]
    )
    code_rows = "\n".join(
        f"<tr><td><a href=\"{html.escape(row['href'])}\">{html.escape(row['section_title'])}</a></td><td>{html.escape(row['article_title'])}</td><td>{html.escape(row['kind'])}</td><td>{row['length']}</td><td><pre>{html.escape(row['preview'])}</pre></td></tr>"
        for row in payload["code_blocks"][:80]
    )
    cards = "\n".join(
        f"<div class=\"card\"><div class=\"label\">{html.escape(kind.upper())}</div><div class=\"value\">{count}</div></div>"
        for kind, count in sorted(payload["code_kind_counts"].items())
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Extended Input Parse Report</title>
  <style>
    body {{ margin: 0; font-family: "Segoe UI", Tahoma, sans-serif; background: #f5f1ea; color: #1a2328; }}
    .wrap {{ max-width: 1400px; margin: 0 auto; padding: 24px 18px 40px; }}
    .panel {{ background: #fffdfa; border: 1px solid #d9d1c4; border-radius: 18px; box-shadow: 0 16px 34px rgba(26, 35, 40, 0.08); padding: 20px; margin-bottom: 18px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }}
    .card {{ background: linear-gradient(135deg, #0c627f, #2389ab); color: #fff; border-radius: 16px; padding: 14px; }}
    .label {{ font-size: 0.76rem; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.88; }}
    .value {{ margin-top: 8px; font-size: 1.8rem; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid #d9d1c4; vertical-align: top; }}
    th {{ background: #ece4d8; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; }}
    pre {{ margin: 0; white-space: pre-wrap; word-break: break-word; font-family: Consolas, monospace; font-size: 0.8rem; }}
    a {{ color: #0c627f; }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="panel">
      <h1>Extended Input Parse Report</h1>
      <p>Generated from <a href="{html.escape(payload['source_uri'])}">{html.escape(payload['source_file'])}</a>.</p>
      <div class="grid" style="margin-top: 16px;">
        <div class="card"><div class="label">Channels</div><div class="value">{len(payload['channels'])}</div></div>
        <div class="card"><div class="label">Sections</div><div class="value">{len(payload['sections'])}</div></div>
        <div class="card"><div class="label">Nav Links</div><div class="value">{len(payload['nav_links'])}</div></div>
        <div class="card"><div class="label">Code Blocks</div><div class="value">{len(payload['code_blocks'])}</div></div>
      </div>
    </section>
    <section class="panel">
      <h2>Template And Manifest Mix</h2>
      <div class="grid">{cards}</div>
    </section>
    <section class="panel">
      <h2>Sections</h2>
      <table>
        <thead><tr><th>Section</th><th>Country</th><th>Channels</th><th>Articles</th><th>Tables</th></tr></thead>
        <tbody>{section_rows}</tbody>
      </table>
    </section>
    <section class="panel">
      <h2>Embedded Code Blocks</h2>
      <table>
        <thead><tr><th>Section</th><th>Article</th><th>Kind</th><th>Length</th><th>Preview</th></tr></thead>
        <tbody>{code_rows}</tbody>
      </table>
    </section>
  </div>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build review outputs from the extended IPTV source HTML.")
    parser.add_argument("source_html", type=Path)
    parser.add_argument("--iptv-dir", type=Path, default=repo_root() / "IPTV")
    args = parser.parse_args()

    payload = parse_source(args.source_html)
    iptv_dir = args.iptv_dir
    review_html_path = iptv_dir / "INPUT_SCOPE_CHANNEL_REVIEW.html"
    template_html = review_html_path.read_text(encoding="utf-8")

    (iptv_dir / "INPUT_SCOPE_CHANNEL_DATA.json").write_text(
        json.dumps(payload["channels"], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (iptv_dir / "INPUT_SCOPE_SOURCE_MAP.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    review_html_path.write_text(
        replace_embedded_json(template_html, payload["channels"], payload["source_file"], payload["source_uri"]),
        encoding="utf-8",
    )
    (iptv_dir / "EXTENDED_INPUT_PARSE_REPORT.html").write_text(
        render_report(payload),
        encoding="utf-8",
    )

    print(f"Built {len(payload['channels'])} extracted channels from {args.source_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
