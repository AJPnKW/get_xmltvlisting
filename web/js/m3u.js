/* m3u.js - minimal M3U parser
   Exports: parseM3u(text) -> { items: [{name, tvgId, logo, group, url}] }
*/
(function () {
  function parseAttrs(line) {
    const attrs = {};
    const re = /(\w[\w-]*)="([^"]*)"/g;
    let m;
    while ((m = re.exec(line)) !== null) attrs[m[1]] = m[2];
    return attrs;
  }

  function parseM3u(text) {
    const lines = String(text || "").split(/\r?\n/);
    const items = [];
    let cur = null;

    for (const raw of lines) {
      const line = raw.trim();
      if (!line) continue;

      if (line.startsWith("#EXTINF:")) {
        const comma = line.indexOf(",");
        const left = comma >= 0 ? line.slice(0, comma) : line;
        const name = comma >= 0 ? line.slice(comma + 1).trim() : "";
        const attrs = parseAttrs(left);
        cur = {
          name: attrs["tvg-name"] || name || "",
          tvgId: attrs["tvg-id"] || "",
          logo: attrs["tvg-logo"] || "",
          group: attrs["group-title"] || "",
          url: ""
        };
        continue;
      }

      if (!line.startsWith("#") && cur) {
        cur.url = line;
        items.push(cur);
        cur = null;
      }
    }

    return { items };
  }

  window.M3U = { parseM3u };
})();
