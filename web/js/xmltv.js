/* xmltv.js - parse minimal XMLTV
   Exports: parseXmltv(xmlText) -> { channelsById, programmesByChannel, days }
*/
(function () {
  function text(el, tag) {
    const n = el.getElementsByTagName(tag)[0];
    return n ? (n.textContent || "").trim() : "";
  }

  function parseStamp(s) {
    // "YYYYMMDDHHmmss +0000" or without tz
    const m = String(s || "").match(/^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})/);
    if (!m) return null;
    const [_, Y, M, D, h, min] = m;
    // treat as UTC if "+0000" present; otherwise parse as local-ish
    const isUtc = /\+\d{4}$/.test(s);
    const dt = isUtc
      ? new Date(Date.UTC(+Y, +M - 1, +D, +h, +min, 0))
      : new Date(+Y, +M - 1, +D, +h, +min, 0);
    return dt;
  }

  function dayKey(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const da = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${da}`;
  }

  function fmtTime(d) {
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function fmtDayLabel(d) {
    return d.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
  }

  function parseXmltv(xmlText) {
    const doc = new DOMParser().parseFromString(xmlText, "application/xml");
    const err = doc.getElementsByTagName("parsererror")[0];
    if (err) throw new Error("XML parse error");

    const channels = Array.from(doc.getElementsByTagName("channel"));
    const programmes = Array.from(doc.getElementsByTagName("programme"));

    const channelsById = {};
    for (const ch of channels) {
      const id = ch.getAttribute("id");
      if (!id) continue;
      const dn = Array.from(ch.getElementsByTagName("display-name"))
        .map(n => (n.textContent || "").trim())
        .filter(Boolean)[0] || id;
      const icon = ch.getElementsByTagName("icon")[0];
      const iconSrc = icon ? (icon.getAttribute("src") || "") : "";
      channelsById[id] = { id, name: dn, icon: iconSrc };
    }

    const programmesByChannel = {};
    const daysSet = new Set();

    for (const p of programmes) {
      const chId = (p.getAttribute("channel") || "").trim();
      const start = parseStamp(p.getAttribute("start"));
      const stop = parseStamp(p.getAttribute("stop"));
      if (!chId || !start || !stop) continue;

      const title = text(p, "title") || "(no title)";
      const desc = text(p, "desc");
      const item = {
        channelId: chId,
        start,
        stop,
        startKey: dayKey(start),
        title,
        desc
      };

      daysSet.add(item.startKey);
      (programmesByChannel[chId] ||= []).push(item);
    }

    for (const k of Object.keys(programmesByChannel)) {
      programmesByChannel[k].sort((a, b) => a.start - b.start);
    }

    const days = Array.from(daysSet).sort().map(k => {
      const d = new Date(k + "T00:00:00");
      return { key: k, label: fmtDayLabel(d) };
    });

    return { channelsById, programmesByChannel, days, fmtTime };
  }

  window.XMLTV = { parseXmltv };
})();
