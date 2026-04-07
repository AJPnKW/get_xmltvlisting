#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_matrix(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def uniq(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        value = (value or "").strip()
        if value and value not in seen:
            out.append(value)
            seen.add(value)
    return out


def merge_review_dataset(channels: list[dict], matrix_rows: list[dict[str, str]], lineups: list[dict]) -> list[dict]:
    lineup_name_by_id = {
        (row.get("lineup_id") or "").strip(): (row.get("lineup_name") or "").strip()
        for row in lineups
    }

    matrix_by_channel: dict[str, list[dict[str, str]]] = {}
    for row in matrix_rows:
        cid = (row.get("channel_id") or "").strip()
        if not cid:
            continue
        matrix_by_channel.setdefault(cid, []).append(row)

    dataset: list[dict] = []
    for channel in channels:
        cid = channel["channel_id"]
        rows = matrix_by_channel.get(cid, [])

        lineup_ids = uniq([row.get("lineup_id", "") for row in rows])
        lineup_names = uniq([
            lineup_name_by_id.get(lineup_id, "")
            for lineup_id in lineup_ids
        ])

        countries = uniq([row.get("country", "") for row in rows])
        channel_types = uniq([row.get("channel_type", "") for row in rows])
        network_bases = uniq([row.get("network_base", "") for row in rows])
        cities = uniq([row.get("city", "") for row in rows])
        regions = uniq([row.get("region", "") for row in rows])
        brand_scopes = uniq([row.get("brand_scope", "") for row in rows])
        resolutions = uniq([row.get("resolution", "") for row in rows])
        final_names = uniq([row.get("final_display_name", "") for row in rows])

        display_names = uniq(channel.get("display_names", []))
        present_in = uniq(channel.get("present_in", []))

        dataset.append({
            "channel_id": cid,
            "full_name": channel.get("full_name", ""),
            "call_sign": channel.get("call_sign", ""),
            "channel_number": channel.get("channel_number", ""),
            "feed": channel.get("feed", ""),
            "url": channel.get("url", ""),
            "icon_src": channel.get("icon_src", ""),
            "display_names": display_names,
            "present_in": present_in,
            "present_in_count": len(present_in),
            "lineup_ids": lineup_ids,
            "lineup_names": lineup_names,
            "countries": countries,
            "channel_types": channel_types,
            "network_bases": network_bases,
            "cities": cities,
            "regions": regions,
            "brand_scopes": brand_scopes,
            "resolutions": resolutions,
            "final_display_names": final_names,
        })

    dataset.sort(key=lambda row: (
        row["countries"][0] if row["countries"] else "ZZ",
        row["network_bases"][0] if row["network_bases"] else "ZZZZ",
        row["full_name"].lower(),
        row["channel_id"].lower(),
    ))
    return dataset


def build_html(dataset: list[dict]) -> str:
    payload = json.dumps(dataset, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Channel Review Tool</title>
  <style>
    :root {{
      --bg: #f3efe8;
      --panel: #fffdfa;
      --ink: #1c2529;
      --muted: #657177;
      --line: #d9d1c4;
      --accent: #0b617e;
      --keep: #0d7a60;
      --review: #a16c00;
      --remove: #9e2f2f;
      --shadow: 0 18px 40px rgba(28, 37, 41, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Tahoma, sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #d8eaee 0, transparent 26rem),
        linear-gradient(180deg, #f9f6ef 0, var(--bg) 100%);
    }}
    .app {{
      display: grid;
      grid-template-columns: minmax(320px, 1.3fr) minmax(300px, 420px);
      gap: 18px;
      max-width: 1480px;
      margin: 0 auto;
      padding: 22px 18px 40px;
    }}
    .left-col, .right-col {{
      display: flex;
      flex-direction: column;
      gap: 18px;
      min-width: 0;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: var(--shadow);
    }}
    .hero {{ padding: 22px; }}
    h1, h2, h3 {{ margin: 0 0 10px; line-height: 1.1; }}
    p {{ margin: 0; }}
    .lede {{ color: var(--muted); max-width: 72rem; }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .stat {{
      border-radius: 16px;
      padding: 14px;
      color: #fff;
      min-height: 96px;
    }}
    .stat.total {{ background: linear-gradient(135deg, #0b617e, #2486a6); }}
    .stat.keep {{ background: linear-gradient(135deg, #0d7a60, #1ca07f); }}
    .stat.review {{ background: linear-gradient(135deg, #8d6500, #c39117); }}
    .stat.remove {{ background: linear-gradient(135deg, #8f2d2d, #c55d5d); }}
    .stat .label {{
      font-size: 0.75rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      opacity: 0.88;
    }}
    .stat .value {{
      font-size: 1.9rem;
      font-weight: 700;
      margin-top: 8px;
    }}
    .toolbar {{ padding: 18px; }}
    .filter-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
    }}
    label {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      font-size: 0.88rem;
      color: var(--muted);
    }}
    input, select, textarea, button {{
      font: inherit;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px 12px;
      background: #fff;
      color: var(--ink);
    }}
    textarea {{ min-height: 120px; resize: vertical; }}
    button {{
      cursor: pointer;
      background: #fff;
    }}
    .button-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 14px;
    }}
    .button-primary {{
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
      font-weight: 600;
    }}
    .table-wrap {{
      padding: 0 18px 18px;
      overflow: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 1060px;
    }}
    th, td {{
      text-align: left;
      padding: 11px 10px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
      font-size: 0.92rem;
    }}
    th {{
      position: sticky;
      top: 0;
      background: #ece4d8;
      z-index: 1;
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    tr {{
      cursor: pointer;
    }}
    tr:hover {{
      background: #f5f1e9;
    }}
    tr.selected {{
      background: #e8f4f8;
    }}
    .pill {{
      display: inline-block;
      border-radius: 999px;
      padding: 4px 9px;
      font-size: 0.75rem;
      font-weight: 700;
      letter-spacing: 0.03em;
      color: #fff;
    }}
    .pill.keep {{ background: var(--keep); }}
    .pill.review {{ background: var(--review); }}
    .pill.remove {{ background: var(--remove); }}
    .pill.pending {{ background: #7f8b90; }}
    .detail {{
      padding: 18px;
      position: sticky;
      top: 18px;
    }}
    .detail h2 {{ margin-bottom: 8px; }}
    .detail .subtle {{
      color: var(--muted);
      font-size: 0.92rem;
      margin-bottom: 12px;
    }}
    .meta {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px 14px;
      margin: 14px 0 16px;
    }}
    .meta .box {{
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 10px 12px;
      background: #fffdf8;
    }}
    .meta .k {{
      display: block;
      font-size: 0.73rem;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 4px;
    }}
    .chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 6px;
    }}
    .chip {{
      display: inline-block;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 8px;
      background: #faf6ef;
      font-size: 0.78rem;
    }}
    .empty {{
      color: var(--muted);
      font-style: italic;
    }}
    .small {{
      font-size: 0.84rem;
      color: var(--muted);
    }}
    @media (max-width: 1180px) {{
      .app {{ grid-template-columns: 1fr; }}
      .detail {{ position: static; }}
    }}
  </style>
</head>
<body>
  <div class="app">
    <div class="left-col">
      <section class="panel hero">
        <h1>Channel Review Tool</h1>
        <p class="lede">
          This tool is for channel review, not final playback. It uses merged metadata from <code>channels.json</code>,
          <code>channel_name_matrix.csv</code>, and <code>lineups.json</code> so you can filter, inspect, and decide
          what to keep, review, or remove before building country-specific M3U or XMLTV subsets.
        </p>
        <div class="stats">
          <div class="stat total"><div class="label">Visible</div><div class="value" id="visibleCount">0</div></div>
          <div class="stat keep"><div class="label">Keep</div><div class="value" id="keepCount">0</div></div>
          <div class="stat review"><div class="label">Review</div><div class="value" id="reviewCount">0</div></div>
          <div class="stat remove"><div class="label">Remove</div><div class="value" id="removeCount">0</div></div>
        </div>
      </section>

      <section class="panel toolbar">
        <h2>Filters</h2>
        <div class="filter-grid">
          <label>Search
            <input id="searchBox" type="search" placeholder="Name, callsign, network, lineup, notes">
          </label>
          <label>Decision
            <select id="decisionFilter">
              <option value="ALL">All</option>
              <option value="keep">Keep</option>
              <option value="review">Review</option>
              <option value="remove">Remove</option>
              <option value="pending">Pending</option>
            </select>
          </label>
          <label>Country
            <select id="countryFilter"><option value="ALL">All</option></select>
          </label>
          <label>Lineup
            <select id="lineupFilter"><option value="ALL">All</option></select>
          </label>
          <label>Channel Type
            <select id="typeFilter"><option value="ALL">All</option></select>
          </label>
          <label>Network Base
            <select id="networkFilter"><option value="ALL">All</option></select>
          </label>
          <label>Presence Count
            <select id="presenceFilter">
              <option value="ALL">All</option>
              <option value="1">1 lineup</option>
              <option value="2">2+ lineups</option>
              <option value="3">3+ lineups</option>
            </select>
          </label>
        </div>
        <div class="button-row">
          <button id="clearFilters">Clear Filters</button>
          <button id="exportJson" class="button-primary">Export Review JSON</button>
          <button id="exportCsv">Export Review CSV</button>
          <button id="importJson">Import Review JSON</button>
          <button id="clearSaved">Clear Saved Decisions</button>
          <input id="importFile" type="file" accept=".json" hidden>
        </div>
        <p class="small" style="margin-top: 12px;">
          Review decisions are saved in browser local storage on this machine. Use export/import if you want a file copy.
        </p>
      </section>

      <section class="panel table-wrap">
        <table>
          <thead>
            <tr>
              <th>Decision</th>
              <th>Name</th>
              <th>Call Sign</th>
              <th>No.</th>
              <th>Country</th>
              <th>Type</th>
              <th>Network</th>
              <th>Lineups</th>
            </tr>
          </thead>
          <tbody id="tableBody"></tbody>
        </table>
      </section>
    </div>

    <div class="right-col">
      <section class="panel detail">
        <h2 id="detailTitle">Select a channel</h2>
        <p id="detailSubtitle" class="subtle">
          Click a row to inspect its metadata, then assign a review decision and notes.
        </p>

        <div class="meta">
          <div class="box"><span class="k">Channel ID</span><div id="detailChannelId" class="empty">None selected</div></div>
          <div class="box"><span class="k">Decision</span><div id="detailDecisionText" class="empty">Pending</div></div>
          <div class="box"><span class="k">Channel Number</span><div id="detailChannelNumber" class="empty">-</div></div>
          <div class="box"><span class="k">Feed</span><div id="detailFeed" class="empty">-</div></div>
        </div>

        <label>Decision
          <select id="detailDecision">
            <option value="pending">Pending</option>
            <option value="keep">Keep</option>
            <option value="review">Review</option>
            <option value="remove">Remove</option>
          </select>
        </label>

        <label style="margin-top: 10px;">Custom Group
          <input id="detailGroup" type="text" placeholder="Example: CA • News">
        </label>

        <label style="margin-top: 10px;">Notes
          <textarea id="detailNotes" placeholder="Why keep/remove? grouping ideas? playlist comments?"></textarea>
        </label>

        <div class="button-row">
          <button id="saveDecision" class="button-primary">Save Decision</button>
          <button id="markKeep">Mark Keep</button>
          <button id="markReview">Mark Review</button>
          <button id="markRemove">Mark Remove</button>
        </div>

        <h3 style="margin-top: 18px;">Metadata</h3>
        <div><strong>Display Names</strong><div id="detailDisplayNames" class="chips"></div></div>
        <div style="margin-top: 12px;"><strong>Countries</strong><div id="detailCountries" class="chips"></div></div>
        <div style="margin-top: 12px;"><strong>Lineups</strong><div id="detailLineups" class="chips"></div></div>
        <div style="margin-top: 12px;"><strong>Channel Types</strong><div id="detailTypes" class="chips"></div></div>
        <div style="margin-top: 12px;"><strong>Networks</strong><div id="detailNetworks" class="chips"></div></div>
        <div style="margin-top: 12px;"><strong>Cities / Regions</strong><div id="detailRegions" class="chips"></div></div>
        <div style="margin-top: 12px;"><strong>Final Names</strong><div id="detailFinalNames" class="chips"></div></div>
        <div style="margin-top: 12px;"><strong>Source Presence</strong><div id="detailPresentIn" class="chips"></div></div>
        <div style="margin-top: 12px;"><strong>Source URL</strong><div id="detailUrl" class="small"></div></div>
      </section>
    </div>
  </div>

  <script>
    const DATA = {payload};
    const STORAGE_KEY = 'get_xmltvlisting.channel_review.decisions.v1';
    let selectedId = null;
    let decisions = loadDecisions();

    const els = {{
      searchBox: document.getElementById('searchBox'),
      decisionFilter: document.getElementById('decisionFilter'),
      countryFilter: document.getElementById('countryFilter'),
      lineupFilter: document.getElementById('lineupFilter'),
      typeFilter: document.getElementById('typeFilter'),
      networkFilter: document.getElementById('networkFilter'),
      presenceFilter: document.getElementById('presenceFilter'),
      tableBody: document.getElementById('tableBody'),
      visibleCount: document.getElementById('visibleCount'),
      keepCount: document.getElementById('keepCount'),
      reviewCount: document.getElementById('reviewCount'),
      removeCount: document.getElementById('removeCount'),
      detailTitle: document.getElementById('detailTitle'),
      detailSubtitle: document.getElementById('detailSubtitle'),
      detailChannelId: document.getElementById('detailChannelId'),
      detailDecisionText: document.getElementById('detailDecisionText'),
      detailChannelNumber: document.getElementById('detailChannelNumber'),
      detailFeed: document.getElementById('detailFeed'),
      detailDecision: document.getElementById('detailDecision'),
      detailGroup: document.getElementById('detailGroup'),
      detailNotes: document.getElementById('detailNotes'),
      detailDisplayNames: document.getElementById('detailDisplayNames'),
      detailCountries: document.getElementById('detailCountries'),
      detailLineups: document.getElementById('detailLineups'),
      detailTypes: document.getElementById('detailTypes'),
      detailNetworks: document.getElementById('detailNetworks'),
      detailRegions: document.getElementById('detailRegions'),
      detailFinalNames: document.getElementById('detailFinalNames'),
      detailPresentIn: document.getElementById('detailPresentIn'),
      detailUrl: document.getElementById('detailUrl'),
      importFile: document.getElementById('importFile')
    }};

    function loadDecisions() {{
      try {{
        return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{{}}');
      }} catch (err) {{
        return {{}};
      }}
    }}

    function saveDecisions() {{
      localStorage.setItem(STORAGE_KEY, JSON.stringify(decisions));
    }}

    function escapeHtml(value) {{
      return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;');
    }}

    function getDecision(channelId) {{
      return decisions[channelId]?.decision || 'pending';
    }}

    function getReview(channelId) {{
      return decisions[channelId] || {{ decision: 'pending', custom_group: '', notes: '' }};
    }}

    function uniqueSorted(values) {{
      return [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b));
    }}

    function fillSelect(select, values) {{
      const current = select.value;
      select.innerHTML = '<option value="ALL">All</option>' + values.map((value) =>
        `<option value="${{escapeHtml(value)}}">${{escapeHtml(value)}}</option>`
      ).join('');
      if ([...select.options].some((opt) => opt.value === current)) {{
        select.value = current;
      }}
    }}

    function initFilters() {{
      fillSelect(els.countryFilter, uniqueSorted(DATA.flatMap((row) => row.countries)));
      fillSelect(els.lineupFilter, uniqueSorted(DATA.flatMap((row) => row.lineup_names)));
      fillSelect(els.typeFilter, uniqueSorted(DATA.flatMap((row) => row.channel_types)));
      fillSelect(els.networkFilter, uniqueSorted(DATA.flatMap((row) => row.network_bases)));
    }}

    function renderChips(target, values) {{
      if (!values || values.length === 0) {{
        target.innerHTML = '<span class="empty">None</span>';
        return;
      }}
      target.innerHTML = values.map((value) => `<span class="chip">${{escapeHtml(value)}}</span>`).join('');
    }}

    function filteredRows() {{
      const q = els.searchBox.value.trim().toLowerCase();
      const decision = els.decisionFilter.value;
      const country = els.countryFilter.value;
      const lineup = els.lineupFilter.value;
      const type = els.typeFilter.value;
      const network = els.networkFilter.value;
      const presence = els.presenceFilter.value;

      return DATA.filter((row) => {{
        const review = getReview(row.channel_id);
        const resolvedDecision = review.decision || 'pending';
        const haystack = [
          row.channel_id,
          row.full_name,
          row.call_sign,
          row.channel_number,
          row.feed,
          row.url,
          review.custom_group,
          review.notes,
          ...row.display_names,
          ...row.countries,
          ...row.lineup_names,
          ...row.channel_types,
          ...row.network_bases,
          ...row.cities,
          ...row.regions,
          ...row.final_display_names
        ].join(' ').toLowerCase();

        if (q && !haystack.includes(q)) return false;
        if (decision !== 'ALL' && resolvedDecision !== decision) return false;
        if (country !== 'ALL' && !row.countries.includes(country)) return false;
        if (lineup !== 'ALL' && !row.lineup_names.includes(lineup)) return false;
        if (type !== 'ALL' && !row.channel_types.includes(type)) return false;
        if (network !== 'ALL' && !row.network_bases.includes(network)) return false;
        if (presence === '1' && row.present_in_count !== 1) return false;
        if (presence === '2' && row.present_in_count < 2) return false;
        if (presence === '3' && row.present_in_count < 3) return false;
        return true;
      }});
    }}

    function renderTable() {{
      const rows = filteredRows();
      els.tableBody.innerHTML = rows.map((row) => {{
        const review = getReview(row.channel_id);
        const decision = review.decision || 'pending';
        const rowClass = row.channel_id === selectedId ? 'selected' : '';
        return `
          <tr data-id="${{escapeHtml(row.channel_id)}}" class="${{rowClass}}">
            <td><span class="pill ${{escapeHtml(decision)}}">${{escapeHtml(decision.toUpperCase())}}</span></td>
            <td>${{escapeHtml(row.full_name || row.display_names[0] || row.channel_id)}}</td>
            <td>${{escapeHtml(row.call_sign || '')}}</td>
            <td>${{escapeHtml(row.channel_number || '')}}</td>
            <td>${{escapeHtml(row.countries.join(', '))}}</td>
            <td>${{escapeHtml(row.channel_types.join(', '))}}</td>
            <td>${{escapeHtml(row.network_bases.join(', '))}}</td>
            <td>${{escapeHtml(row.lineup_names.join(' | '))}}</td>
          </tr>
        `;
      }}).join('');

      els.visibleCount.textContent = String(rows.length);
      els.keepCount.textContent = String(Object.values(decisions).filter((v) => v.decision === 'keep').length);
      els.reviewCount.textContent = String(Object.values(decisions).filter((v) => v.decision === 'review').length);
      els.removeCount.textContent = String(Object.values(decisions).filter((v) => v.decision === 'remove').length);

      els.tableBody.querySelectorAll('tr').forEach((tr) => {{
        tr.addEventListener('click', () => {{
          selectedId = tr.dataset.id;
          renderTable();
          renderDetail();
        }});
      }});
    }}

    function renderDetail() {{
      const row = DATA.find((item) => item.channel_id === selectedId);
      if (!row) {{
        els.detailTitle.textContent = 'Select a channel';
        els.detailSubtitle.textContent = 'Click a row to inspect its metadata, then assign a review decision and notes.';
        els.detailChannelId.textContent = 'None selected';
        els.detailDecisionText.innerHTML = '<span class="empty">Pending</span>';
        els.detailChannelNumber.textContent = '-';
        els.detailFeed.textContent = '-';
        els.detailDecision.value = 'pending';
        els.detailGroup.value = '';
        els.detailNotes.value = '';
        renderChips(els.detailDisplayNames, []);
        renderChips(els.detailCountries, []);
        renderChips(els.detailLineups, []);
        renderChips(els.detailTypes, []);
        renderChips(els.detailNetworks, []);
        renderChips(els.detailRegions, []);
        renderChips(els.detailFinalNames, []);
        renderChips(els.detailPresentIn, []);
        els.detailUrl.innerHTML = '<span class="empty">No source URL</span>';
        return;
      }}

      const review = getReview(row.channel_id);
      const decision = review.decision || 'pending';
      els.detailTitle.textContent = row.full_name || row.display_names[0] || row.channel_id;
      els.detailSubtitle.textContent = row.call_sign ? `Call sign: ${{row.call_sign}}` : 'No call sign recorded';
      els.detailChannelId.textContent = row.channel_id;
      els.detailDecisionText.innerHTML = `<span class="pill ${{escapeHtml(decision)}}">${{escapeHtml(decision.toUpperCase())}}</span>`;
      els.detailChannelNumber.textContent = row.channel_number || '-';
      els.detailFeed.textContent = row.feed || '-';
      els.detailDecision.value = decision;
      els.detailGroup.value = review.custom_group || '';
      els.detailNotes.value = review.notes || '';
      renderChips(els.detailDisplayNames, row.display_names);
      renderChips(els.detailCountries, row.countries);
      renderChips(els.detailLineups, row.lineup_names);
      renderChips(els.detailTypes, row.channel_types);
      renderChips(els.detailNetworks, row.network_bases);
      renderChips(els.detailRegions, [...row.cities, ...row.regions]);
      renderChips(els.detailFinalNames, row.final_display_names);
      renderChips(els.detailPresentIn, row.present_in);
      els.detailUrl.innerHTML = row.url ? `<a href="${{escapeHtml(row.url)}}" target="_blank" rel="noreferrer">${{escapeHtml(row.url)}}</a>` : '<span class="empty">No source URL</span>';
    }}

    function saveCurrentDecision(forcedDecision = null) {{
      if (!selectedId) return;
      const decision = forcedDecision || els.detailDecision.value;
      decisions[selectedId] = {{
        decision,
        custom_group: els.detailGroup.value.trim(),
        notes: els.detailNotes.value.trim()
      }};
      saveDecisions();
      renderTable();
      renderDetail();
    }}

    function clearFilters() {{
      els.searchBox.value = '';
      els.decisionFilter.value = 'ALL';
      els.countryFilter.value = 'ALL';
      els.lineupFilter.value = 'ALL';
      els.typeFilter.value = 'ALL';
      els.networkFilter.value = 'ALL';
      els.presenceFilter.value = 'ALL';
      renderTable();
    }}

    function download(name, type, content) {{
      const blob = new Blob([content], {{ type }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = name;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    }}

    function exportJson() {{
      const payload = {{
        exported_at: new Date().toISOString(),
        review_count: Object.keys(decisions).length,
        decisions
      }};
      download('channel_review_decisions.json', 'application/json', JSON.stringify(payload, null, 2));
    }}

    function exportCsv() {{
      const lines = [
        ['channel_id','decision','custom_group','notes']
      ];
      Object.entries(decisions).forEach(([channelId, review]) => {{
        lines.push([
          channelId,
          review.decision || 'pending',
          review.custom_group || '',
          review.notes || ''
        ]);
      }});
      const csv = lines.map((row) => row.map((value) => {{
        const text = String(value ?? '');
        return /[",\\n]/.test(text) ? '"' + text.replaceAll('"', '""') + '"' : text;
      }}).join(',')).join('\\n');
      download('channel_review_decisions.csv', 'text/csv;charset=utf-8', csv);
    }}

    function importJsonObject(obj) {{
      const next = obj.decisions && typeof obj.decisions === 'object' ? obj.decisions : obj;
      if (!next || typeof next !== 'object') {{
        alert('Import file did not contain a valid decisions object.');
        return;
      }}
      decisions = next;
      saveDecisions();
      renderTable();
      renderDetail();
    }}

    initFilters();
    renderTable();
    renderDetail();

    [
      els.searchBox,
      els.decisionFilter,
      els.countryFilter,
      els.lineupFilter,
      els.typeFilter,
      els.networkFilter,
      els.presenceFilter
    ].forEach((el) => el.addEventListener('input', renderTable));

    document.getElementById('clearFilters').addEventListener('click', clearFilters);
    document.getElementById('saveDecision').addEventListener('click', () => saveCurrentDecision());
    document.getElementById('markKeep').addEventListener('click', () => saveCurrentDecision('keep'));
    document.getElementById('markReview').addEventListener('click', () => saveCurrentDecision('review'));
    document.getElementById('markRemove').addEventListener('click', () => saveCurrentDecision('remove'));
    document.getElementById('exportJson').addEventListener('click', exportJson);
    document.getElementById('exportCsv').addEventListener('click', exportCsv);
    document.getElementById('importJson').addEventListener('click', () => els.importFile.click());
    document.getElementById('clearSaved').addEventListener('click', () => {{
      if (!confirm('Clear all saved review decisions for this browser?')) return;
      decisions = {{}};
      saveDecisions();
      renderTable();
      renderDetail();
    }});
    els.importFile.addEventListener('change', async (event) => {{
      const file = event.target.files?.[0];
      if (!file) return;
      try {{
        const text = await file.text();
        importJsonObject(JSON.parse(text));
      }} catch (err) {{
        alert('Could not import review JSON.');
      }} finally {{
        event.target.value = '';
      }}
    }});
  </script>
</body>
</html>
"""


def main() -> int:
    repo = repo_root()
    iptv_dir = repo / "IPTV"

    channels = load_json(iptv_dir / "channels.json")
    matrix_rows = load_matrix(iptv_dir / "channel_name_matrix.csv")
    lineups = load_json(iptv_dir / "lineups.json")

    dataset = merge_review_dataset(channels, matrix_rows, lineups)
    output_path = iptv_dir / "CHANNEL_REVIEW_TOOL.html"
    output_path.write_text(build_html(dataset), encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
