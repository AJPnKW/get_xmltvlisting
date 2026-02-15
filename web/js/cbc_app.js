/* cbc_app.js - CBC Olympics Hub POC
   Loads:
     /IPTV/CBC_Canada.xml
     /IPTV/CBC_Canada.m3u
*/
(function () {
  const PATH_XML = "../../IPTV/CBC_Canada.xml";
  const PATH_M3U = "../../IPTV/CBC_Canada.m3u";

  const $ = (id) => document.getElementById(id);
  const toast = $("toast");

  function showToast(msg) {
    toast.textContent = msg;
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 1400);
  }

  async function fetchText(url) {
    const r = await fetch(url, { cache: "no-store" });
    if (!r.ok) throw new Error(`HTTP ${r.status} for ${url}`);
    return await r.text();
  }

  function setTab(name) {
    document.querySelectorAll(".tab").forEach(b => b.classList.toggle("is-active", b.dataset.tab === name));
    document.querySelectorAll(".panel").forEach(p => p.classList.toggle("is-active", p.dataset.panel === name));
    // focus first dpad item
    const panel = document.querySelector(`.panel[data-panel="${name}"]`);
    const first = panel ? panel.querySelector('[data-dpad="item"]') : null;
    if (first) first.focus();
  }

  function pickBestProgramme(list, now) {
    const cur = list.find(p => p.start <= now && p.stop > now);
    if (cur) return { now: cur, next: list.filter(p => p.start >= now).slice(0, 6) };
    return { now: null, next: list.filter(p => p.start >= now).slice(0, 6) };
  }

  function renderChannels(channels, m3uItems, filter) {
    const wrap = $("channels");
    wrap.innerHTML = "";
    const f = (filter || "").trim().toLowerCase();

    const byId = {};
    for (const it of m3uItems) {
      if (!it.tvgId) continue;
      (byId[it.tvgId] ||= []).push(it);
    }

    const ids = Object.keys(channels)
      .sort((a, b) => channels[a].name.localeCompare(channels[b].name));

    let shown = 0;
    for (const id of ids) {
      const ch = channels[id];
      const name = ch.name || id;
      const group = (byId[id]?.[0]?.group) || "CBC Canada";
      const hasStreams = (byId[id] || []).length;

      if (f && !(`${name} ${id}`.toLowerCase().includes(f))) continue;

      const div = document.createElement("button");
      div.type = "button";
      div.className = "ch";
      div.setAttribute("data-dpad", "item");
      div.dataset.channelId = id;

      const logo = document.createElement("div");
      logo.className = "ch-logo";
      const imgSrc = ch.icon || (byId[id]?.[0]?.logo) || "";
      if (imgSrc) {
        const img = document.createElement("img");
        img.loading = "lazy";
        img.alt = "";
        img.src = imgSrc;
        logo.appendChild(img);
      } else {
        logo.textContent = "CBC";
      }

      const txt = document.createElement("div");
      txt.className = "ch-txt";
      txt.innerHTML = `<div class="ch-name">${escapeHtml(name)}</div>
                       <div class="ch-sub">${escapeHtml(group)} • ${hasStreams} stream(s)</div>`;

      const badge = document.createElement("div");
      badge.className = "badge";
      badge.textContent = hasStreams ? "READY" : "NO STREAM";

      div.append(logo, txt, badge);
      wrap.appendChild(div);
      shown++;
    }

    $("channelsMeta").textContent = `${shown} channel(s)`;
  }

  function escapeHtml(s) {
    return String(s || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function renderNow(channelId, state) {
    const ch = state.channelsById[channelId];
    const pList = state.programmesByChannel[channelId] || [];
    const now = new Date();
    const pick = pickBestProgramme(pList, now);
    const m3uStreams = (state.m3uById[channelId] || []);

    $("nowTitle").textContent = ch ? ch.name : channelId;
    const nowText = pick.now ? `${state.fmtTime(pick.now.start)}–${state.fmtTime(pick.now.stop)} • ${pick.now.title}` : "No current programme found";
    $("nowMeta").textContent = nowText;

    // Buttons
    const bestUrl = (m3uStreams[0] && m3uStreams[0].url) ? m3uStreams[0].url : "";
    $("btnOpen").disabled = !bestUrl;
    $("btnCopy").disabled = !bestUrl;
    $("btnOpen").onclick = () => window.open(bestUrl, "_blank", "noopener,noreferrer");
    $("btnCopy").onclick = async () => {
      await navigator.clipboard.writeText(bestUrl);
      showToast("Copied stream URL");
    };

    // up next
    const up = $("upNext");
    up.innerHTML = "";
    for (const item of pick.next) {
      const div = document.createElement("div");
      div.className = "mini-item";
      div.innerHTML = `<div class="t">${escapeHtml(item.title)}</div>
                       <div class="m">${escapeHtml(state.fmtTime(item.start))}</div>`;
      up.appendChild(div);
    }
  }

  function buildSchedule(channelId, dayKey, state) {
    const wrap = $("schedule");
    wrap.innerHTML = "";

    const list = (state.programmesByChannel[channelId] || []).filter(p => p.startKey === dayKey);
    if (!list.length) {
      wrap.innerHTML = `<div class="hint">No programmes for this day.</div>`;
      return;
    }

    for (const p of list) {
      const row = document.createElement("div");
      row.className = "row";
      row.innerHTML = `
        <div class="row-h">
          <div class="row-title">${escapeHtml(p.title)}</div>
          <div class="row-time">${escapeHtml(state.fmtTime(p.start))}–${escapeHtml(state.fmtTime(p.stop))}</div>
        </div>
        <div class="row-desc">${escapeHtml(p.desc || "")}</div>
      `;
      wrap.appendChild(row);
    }
  }

  function setDownloads(state) {
    // these raw links are only correct once you host them; for local, keep relative
    // For GitHub Pages later, we’ll compute absolute URLs automatically.
    $("m3uUrl").textContent = PATH_M3U;
    $("epgUrl").textContent = PATH_XML;

    $("copyM3u").onclick = async () => { await navigator.clipboard.writeText(PATH_M3U); showToast("Copied M3U URL"); };
    $("copyEpg").onclick = async () => { await navigator.clipboard.writeText(PATH_XML); showToast("Copied EPG URL"); };
  }

  function wireTabs() {
    document.querySelectorAll(".tab").forEach(b => {
      b.addEventListener("click", () => setTab(b.dataset.tab));
    });
  }

  async function main() {
    wireTabs();
    setTab("watch");

    $("btnRefresh").addEventListener("click", () => location.reload());

    const [xmlText, m3uText] = await Promise.all([fetchText(PATH_XML), fetchText(PATH_M3U)]);
    const xml = window.XMLTV.parseXmltv(xmlText);
    const m3u = window.M3U.parseM3u(m3uText);

    const m3uById = {};
    for (const it of m3u.items) (m3uById[it.tvgId] ||= []).push(it);

    const state = {
      channelsById: xml.channelsById,
      programmesByChannel: xml.programmesByChannel,
      days: xml.days,
      fmtTime: xml.fmtTime,
      m3uItems: m3u.items,
      m3uById
    };

    // WATCH: channels + filter + click
    renderChannels(state.channelsById, state.m3uItems, "");
    $("q").addEventListener("input", (e) => renderChannels(state.channelsById, state.m3uItems, e.target.value));

    $("channels").addEventListener("click", (e) => {
      const btn = e.target.closest(".ch");
      if (!btn) return;
      const id = btn.dataset.channelId;
      state.activeChannelId = id;
      renderNow(id, state);

      // also sync schedule selectors
      $("channelPick").value = id;
      $("dayPick").value = $("dayPick").value || (state.days[0]?.key || "");
      buildSchedule(id, $("dayPick").value, state);
    });

    // SCHEDULE: selectors
    const channelPick = $("channelPick");
    channelPick.innerHTML = Object.keys(state.channelsById)
      .sort((a,b) => state.channelsById[a].name.localeCompare(state.channelsById[b].name))
      .map(id => `<option value="${id}">${escapeHtml(state.channelsById[id].name)}</option>`)
      .join("");

    const dayPick = $("dayPick");
    dayPick.innerHTML = state.days.map(d => `<option value="${d.key}">${escapeHtml(d.label)}</option>`).join("");

    channelPick.addEventListener("change", () => buildSchedule(channelPick.value, dayPick.value, state));
    dayPick.addEventListener("change", () => buildSchedule(channelPick.value, dayPick.value, state));

    $("btnNow").addEventListener("click", () => {
      const now = new Date();
      const key = (now.getFullYear()) + "-" + String(now.getMonth()+1).padStart(2,"0") + "-" + String(now.getDate()).padStart(2,"0");
      const opt = Array.from(dayPick.options).find(o => o.value === key);
      if (opt) dayPick.value = key;
      buildSchedule(channelPick.value, dayPick.value, state);
    });

    // Defaults
    const firstCh = channelPick.value || Object.keys(state.channelsById)[0];
    const firstDay = dayPick.value || state.days[0]?.key || "";
    if (firstCh) {
      state.activeChannelId = firstCh;
      renderNow(firstCh, state);
      buildSchedule(firstCh, firstDay, state);
    }

    setDownloads(state);
    showToast("Loaded CBC schedule + channels");
  }

  window.addEventListener("DOMContentLoaded", () => {
    main().catch(err => {
      console.error(err);
      document.body.innerHTML = `<div style="padding:16px;font-family:system-ui;color:#fff;">
        <h2>Failed to load CBC Hub</h2>
        <pre style="white-space:pre-wrap;color:#ffd54a">${String(err && err.message || err)}</pre>
        <div>Check that <code>IPTV/CBC_Canada.xml</code> and <code>IPTV/CBC_Canada.m3u</code> exist and are reachable by the web server.</div>
      </div>`;
    });
  });
})();
