#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


TARGET_COUNTRIES = ("UK", "AU")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def default_decision_for(row: dict) -> dict:
    country = row.get("country", "")
    scope_hint = row.get("scope_hint", "optional")
    if country in TARGET_COUNTRIES:
        if scope_hint == "core":
            decision = "include"
        elif scope_hint == "regional":
            decision = "maybe"
        else:
            decision = "maybe"
    else:
        decision = "exclude"
    return {
        "decision": decision,
        "target_group": f"{country} • Seeded" if country in TARGET_COUNTRIES else "",
        "notes": "Auto-seeded from country and scope hint.",
    }


def build_seed_decisions(data: list[dict]) -> dict:
    decisions = {}
    selected_ids = []
    for row in data:
        key = row.get("tvg_id") or row.get("name")
        review = default_decision_for(row)
        decisions[key] = review
        if review["decision"] in {"include", "maybe"}:
            selected_ids.append(key)
    return {
        "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "selected_ids": selected_ids,
        "decisions": decisions,
        "seeded": True,
    }


def normalize_decisions(raw: dict) -> dict:
    if isinstance(raw, dict) and isinstance(raw.get("decisions"), dict):
        return raw
    if isinstance(raw, dict):
        return {"decisions": raw, "selected_ids": [], "seeded": False}
    raise ValueError("Decision payload must be a JSON object.")


def render_m3u(country: str, rows: list[dict], xml_filename: str) -> str:
    lines = [f'#EXTM3U x-tvg-url="{xml_filename}"']
    for row in rows:
        group = row["review"].get("target_group") or f"{country} • {row.get('network') or 'Channels'}"
        logo = row.get("logo_urls", [""])[0] if row.get("logo_urls") else ""
        lines.append(
            f'#EXTINF:-1 tvg-id="{row.get("tvg_id","")}" tvg-name="{row.get("name","")}" '
            f'tvg-logo="{logo}" group-title="{group}",{row.get("name","")}'
        )
        lines.append(f'http://your-stream-source/{country.lower()}/{row.get("tvg_id","").replace(".","-")}.m3u8')
    return "\n".join(lines) + "\n"


def render_xmltv(country: str, rows: list[dict]) -> str:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<tv generator-info-name="get_xmltvlisting scope builder">']
    for row in rows:
        lines.append(f'  <channel id="{row.get("tvg_id","")}">')
        lines.append(f'    <display-name>{html.escape(row.get("name",""))}</display-name>')
        if row.get("network"):
            lines.append(f'    <display-name>{html.escape(row.get("network",""))}</display-name>')
        if row.get("logo_urls"):
            lines.append(f'    <icon src="{html.escape(row["logo_urls"][0])}"/>')
        lines.append("  </channel>")
    lines.append("</tv>")
    return "\n".join(lines) + "\n"


def render_index(output_dir: Path, summaries: list[dict], source_map: dict, decision_file: str) -> str:
    cards = []
    rows = []
    for summary in summaries:
        country = summary["country"]
        allowlist = summary["allowlist_name"]
        m3u = summary["m3u_name"]
        xml = summary["xml_name"]
        cards.append(
            f'<div class="card"><div class="label">{country}</div><div class="value">{summary["included_count"]}</div><div class="small">included channels</div></div>'
        )
        rows.append(
            f"<tr><td>{country}</td><td>{summary['included_count']}</td><td>{summary['maybe_count']}</td>"
            f"<td><a href=\"./{allowlist}\">{allowlist}</a></td><td><a href=\"./{m3u}\">{m3u}</a></td><td><a href=\"./{xml}\">{xml}</a></td></tr>"
        )
    source_file = html.escape(source_map.get("source_file", ""))
    source_uri = html.escape(source_map.get("source_uri", ""))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Scope Outputs Index</title>
  <style>
    body {{ margin: 0; font-family: "Segoe UI", Tahoma, sans-serif; background: #f5f1ea; color: #1a2328; }}
    .wrap {{ max-width: 1240px; margin: 0 auto; padding: 24px 18px 40px; }}
    .panel {{ background: #fffdfa; border: 1px solid #d9d1c4; border-radius: 18px; box-shadow: 0 16px 34px rgba(26,35,40,0.08); padding: 20px; margin-bottom: 18px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }}
    .card {{ background: linear-gradient(135deg, #0c627f, #2389ab); color: #fff; border-radius: 16px; padding: 14px; }}
    .label {{ font-size: 0.76rem; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.88; }}
    .value {{ margin-top: 8px; font-size: 1.8rem; font-weight: 700; }}
    .small {{ margin-top: 6px; color: rgba(255,255,255,0.88); font-size: 0.85rem; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid #d9d1c4; }}
    th {{ background: #ece4d8; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; }}
    a {{ color: #0c627f; }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="panel">
      <h1>Scope Outputs Index</h1>
      <p>Generated from <a href="{source_uri}">{source_file}</a>.</p>
      <p>Decisions source: {html.escape(decision_file)}</p>
    </section>
    <section class="panel">
      <div class="grid">
        {''.join(cards)}
      </div>
    </section>
    <section class="panel">
      <h2>Outputs</h2>
      <table>
        <thead><tr><th>Country</th><th>Include</th><th>Maybe</th><th>Allowlist</th><th>M3U Template</th><th>XMLTV Channels</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </section>
  </div>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build country scope outputs from review decisions.")
    parser.add_argument("--iptv-dir", type=Path, default=repo_root() / "IPTV")
    parser.add_argument("--decisions", type=Path, help="Optional exported review decisions JSON.")
    args = parser.parse_args()

    iptv_dir = args.iptv_dir
    data = load_json(iptv_dir / "INPUT_SCOPE_CHANNEL_DATA.json")
    source_map = load_json(iptv_dir / "INPUT_SCOPE_SOURCE_MAP.json")
    outputs_dir = iptv_dir / "scope_outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    if args.decisions and args.decisions.exists():
        decision_payload = normalize_decisions(load_json(args.decisions))
        decision_source = str(args.decisions)
    else:
        decision_payload = build_seed_decisions(data)
        seed_path = outputs_dir / "INPUT_SCOPE_DECISIONS.seed.json"
        seed_path.write_text(json.dumps(decision_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        decision_source = str(seed_path)

    decisions = decision_payload["decisions"]
    summaries = []

    for country in TARGET_COUNTRIES:
        country_rows = [row for row in data if row.get("country") == country]
        included = []
        maybe_count = 0
        for row in country_rows:
            key = row.get("tvg_id") or row.get("name")
            review = decisions.get(key, default_decision_for(row))
            merged = dict(row)
            merged["review"] = review
            if review.get("decision") == "include":
                included.append(merged)
            elif review.get("decision") == "maybe":
                maybe_count += 1

        allowlist_name = f"{country}_allowlist.json"
        m3u_name = f"{country}_playlist_template.m3u"
        xml_name = f"{country}_channels.xml"

        allowlist_payload = {
            "country": country,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "decision_source": decision_source,
            "included_channels": included,
        }
        (outputs_dir / allowlist_name).write_text(json.dumps(allowlist_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        (outputs_dir / m3u_name).write_text(render_m3u(country, included, xml_name), encoding="utf-8")
        (outputs_dir / xml_name).write_text(render_xmltv(country, included), encoding="utf-8")

        summaries.append({
            "country": country,
            "included_count": len(included),
            "maybe_count": maybe_count,
            "allowlist_name": allowlist_name,
            "m3u_name": m3u_name,
            "xml_name": xml_name,
        })

    (outputs_dir / "SCOPE_OUTPUTS_INDEX.html").write_text(
        render_index(outputs_dir, summaries, source_map, decision_source),
        encoding="utf-8",
    )

    print(f"Built scope outputs in {outputs_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
