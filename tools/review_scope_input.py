from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path


SECTION_HEADING_RX = re.compile(r"^\[\d+/\d+\]\s+(.+?)\s*$", re.MULTILINE)
HTML_H2_RX = re.compile(r"<h2>(.*?)</h2>", re.IGNORECASE | re.DOTALL)
TAG_RX = re.compile(r"<[^>]+>")
SPACE_RX = re.compile(r"\s+")


@dataclass
class SectionResult:
    title: str
    decision: str
    score: int
    reasons: list[str]


def normalize(text: str) -> str:
    text = TAG_RX.sub(" ", text)
    text = SPACE_RX.sub(" ", text)
    return text.strip()


def load_profile(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_titles(text: str) -> list[str]:
    titles: list[str] = []
    seen: set[str] = set()
    for title in SECTION_HEADING_RX.findall(text):
        clean = normalize(title)
        if clean and clean not in seen:
            titles.append(clean)
            seen.add(clean)
    for title in HTML_H2_RX.findall(text):
        clean = normalize(title)
        if clean and clean not in seen:
            titles.append(clean)
            seen.add(clean)
    return titles


def score_title(title: str, profile: dict) -> SectionResult:
    low = title.lower()
    score = 0
    reasons: list[str] = []

    for word in profile["keep_keywords"]:
        if word in low:
            score += 3
            reasons.append(f"keep:{word}")

    for word in profile["reference_only_keywords"]:
        if word in low:
            score += 1
            reasons.append(f"reference:{word}")

    for word in profile["scope_out_keywords"]:
        if word in low:
            score -= 4
            reasons.append(f"scope_out:{word}")

    if "template" in low:
        score -= 1
        reasons.append("template_penalty")

    if "expanded" in low:
        score -= 1
        reasons.append("expanded_penalty")

    if score >= 4:
        decision = "KEEP"
    elif score >= 1:
        decision = "REFERENCE_ONLY"
    else:
        decision = "SCOPE_OUT"

    return SectionResult(title=title, decision=decision, score=score, reasons=reasons)


def build_report(results: list[SectionResult], source_name: str) -> str:
    counts = {"KEEP": 0, "REFERENCE_ONLY": 0, "SCOPE_OUT": 0}
    rows: list[str] = []
    for row in results:
        counts[row.decision] += 1
        reason_text = ", ".join(row.reasons) if row.reasons else "none"
        rows.append(
            f"""
            <tr data-decision="{html.escape(row.decision)}">
              <td>{html.escape(row.title)}</td>
              <td><span class="pill {html.escape(row.decision.lower())}">{html.escape(row.decision)}</span></td>
              <td>{row.score}</td>
              <td>{html.escape(reason_text)}</td>
            </tr>
            """.strip()
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Scope Review - {html.escape(source_name)}</title>
  <style>
    :root {{
      --bg: #f4efe7;
      --paper: #fffdfa;
      --ink: #182126;
      --muted: #657177;
      --line: #d7d0c3;
      --keep: #0e7a5f;
      --ref: #9a6c00;
      --out: #9a2f2f;
      --accent: #0b5f86;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Tahoma, sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #dcecf0 0, transparent 24rem),
        linear-gradient(180deg, #f8f5ee 0, var(--bg) 100%);
    }}
    .wrap {{ max-width: 1280px; margin: 0 auto; padding: 28px 20px 48px; }}
    .hero, .panel {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: 0 16px 36px rgba(24, 33, 38, 0.08);
    }}
    .hero {{ padding: 24px; margin-bottom: 18px; }}
    h1, h2 {{ margin: 0 0 10px; line-height: 1.1; }}
    p {{ margin: 0; }}
    .lede {{ color: var(--muted); max-width: 72rem; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
      margin: 18px 0;
    }}
    .stat {{
      padding: 16px;
      border-radius: 16px;
      color: #fff;
      min-height: 110px;
    }}
    .stat.keep {{ background: linear-gradient(135deg, #0e7a5f, #20a17c); }}
    .stat.reference_only {{ background: linear-gradient(135deg, #8e6600, #c69314); }}
    .stat.scope_out {{ background: linear-gradient(135deg, #8a2e2e, #bc5555); }}
    .stat .k {{ font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.88; }}
    .stat .v {{ font-size: 2rem; font-weight: 700; margin-top: 8px; }}
    .controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      margin-bottom: 14px;
    }}
    .panel {{ padding: 20px; }}
    .btn, input {{
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 999px;
      padding: 10px 14px;
      font: inherit;
    }}
    .btn {{
      cursor: pointer;
      color: var(--accent);
      font-weight: 600;
    }}
    .btn.active {{
      background: var(--accent);
      color: #fff;
      border-color: var(--accent);
    }}
    input {{ min-width: 260px; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      overflow: hidden;
      border-radius: 14px;
    }}
    th, td {{
      text-align: left;
      padding: 12px 10px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
    }}
    th {{
      background: #ece4d7;
      font-size: 0.82rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    tr:last-child td {{ border-bottom: 0; }}
    .pill {{
      display: inline-block;
      padding: 5px 10px;
      border-radius: 999px;
      color: #fff;
      font-size: 0.8rem;
      font-weight: 700;
      letter-spacing: 0.04em;
    }}
    .pill.keep {{ background: var(--keep); }}
    .pill.reference_only {{ background: var(--ref); }}
    .pill.scope_out {{ background: var(--out); }}
    .notes {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 14px;
      margin-top: 18px;
    }}
    .note {{
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
      background: #fffcf7;
    }}
    ul {{ margin: 0; padding-left: 18px; }}
    li {{ margin-bottom: 8px; }}
    .muted {{ color: var(--muted); }}
    @media (max-width: 720px) {{
      th:nth-child(3), td:nth-child(3), th:nth-child(4), td:nth-child(4) {{ font-size: 0.84rem; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>IPTV Scope Review</h1>
      <p class="lede">
        Reviewed source: <strong>{html.escape(source_name)}</strong>. This report is tuned for the working focus:
        <strong>CA, UK, AU, US</strong>. Use it to keep broadcaster-aligned material and cut placeholder-heavy global IPTV noise.
      </p>
      <div class="grid">
        <div class="stat keep">
          <div class="k">Keep</div>
          <div class="v">{counts["KEEP"]}</div>
        </div>
        <div class="stat reference_only">
          <div class="k">Reference Only</div>
          <div class="v">{counts["REFERENCE_ONLY"]}</div>
        </div>
        <div class="stat scope_out">
          <div class="k">Scope Out</div>
          <div class="v">{counts["SCOPE_OUT"]}</div>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="controls">
        <button class="btn active" data-filter="ALL">All</button>
        <button class="btn" data-filter="KEEP">Keep</button>
        <button class="btn" data-filter="REFERENCE_ONLY">Reference Only</button>
        <button class="btn" data-filter="SCOPE_OUT">Scope Out</button>
        <input id="searchBox" type="search" placeholder="Filter by section title or reason">
      </div>
      <table id="resultsTable">
        <thead>
          <tr>
            <th>Section</th>
            <th>Decision</th>
            <th>Score</th>
            <th>Reason Summary</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows)}
        </tbody>
      </table>
    </section>

    <section class="notes">
      <article class="note">
        <h2>Decision Meaning</h2>
        <ul>
          <li><strong>Keep</strong>: aligned to the country and broadcaster scope and useful in final deliverables.</li>
          <li><strong>Reference Only</strong>: useful for naming, manifests, mapping, or QA, but not a source of truth.</li>
          <li><strong>Scope Out</strong>: generic, placeholder-heavy, FAST-heavy, or unrelated expansion material.</li>
        </ul>
      </article>
      <article class="note">
        <h2>Working Rule Set</h2>
        <ul>
          <li>Prefer real XMLTV assets over templates.</li>
          <li>Prefer country-specific broadcaster material over global examples.</li>
          <li>Reject FAST, IPTV-Org, and fallback-chain content unless explicitly requested.</li>
          <li>Treat regional variants as optional until your real playlist needs them.</li>
        </ul>
      </article>
    </section>
  </div>
  <script>
    const buttons = [...document.querySelectorAll('.btn[data-filter]')];
    const searchBox = document.getElementById('searchBox');
    const rows = [...document.querySelectorAll('#resultsTable tbody tr')];
    let activeFilter = 'ALL';

    function applyFilters() {{
      const q = searchBox.value.trim().toLowerCase();
      rows.forEach((row) => {{
        const decision = row.dataset.decision;
        const text = row.innerText.toLowerCase();
        const matchFilter = activeFilter === 'ALL' || decision === activeFilter;
        const matchSearch = !q || text.includes(q);
        row.style.display = matchFilter && matchSearch ? '' : 'none';
      }});
    }}

    buttons.forEach((btn) => {{
      btn.addEventListener('click', () => {{
        activeFilter = btn.dataset.filter;
        buttons.forEach((b) => b.classList.toggle('active', b === btn));
        applyFilters();
      }});
    }});

    searchBox.addEventListener('input', applyFilters);
    applyFilters();
  </script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Review a pasted IPTV reference file and classify sections by scope.")
    parser.add_argument("input_file", type=Path, help="Path to the source text or HTML file")
    parser.add_argument(
        "--profile",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "config" / "iptv_scope_profile.json",
        help="Path to the scope profile JSON"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output HTML path"
    )
    args = parser.parse_args()

    text = args.input_file.read_text(encoding="utf-8")
    profile = load_profile(args.profile)
    titles = extract_titles(text)
    results = [score_title(title, profile) for title in titles]
    report = build_report(results, args.input_file.name)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
