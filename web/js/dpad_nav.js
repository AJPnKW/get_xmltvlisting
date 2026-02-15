/* dpad_nav.js - simple deterministic D-pad navigation for buttons/inputs/selects/links
   Mark focusable targets with: data-dpad="item"
   Wrap regions with: data-nav
*/
(function () {
  function focusables(root) {
    return Array.from(root.querySelectorAll('[data-dpad="item"]'))
      .filter(el => !el.disabled && el.offsetParent !== null);
  }

  function rect(el) {
    const r = el.getBoundingClientRect();
    return { el, x: r.left + r.width / 2, y: r.top + r.height / 2, r };
  }

  function bestCandidate(from, dir, list) {
    const f = rect(from);
    const cands = list.map(rect).filter(o => o.el !== from);

    function score(o) {
      const dx = o.x - f.x;
      const dy = o.y - f.y;

      if (dir === "left" && dx >= 0) return null;
      if (dir === "right" && dx <= 0) return null;
      if (dir === "up" && dy >= 0) return null;
      if (dir === "down" && dy <= 0) return null;

      const primary = (dir === "left" || dir === "right") ? Math.abs(dx) : Math.abs(dy);
      const secondary = (dir === "left" || dir === "right") ? Math.abs(dy) : Math.abs(dx);
      return primary * 10 + secondary;
    }

    let best = null;
    let bestScore = Infinity;
    for (const o of cands) {
      const s = score(o);
      if (s === null) continue;
      if (s < bestScore) { best = o.el; bestScore = s; }
    }
    return best;
  }

  function handleKey(e) {
    const k = e.key;
    const dir =
      k === "ArrowLeft" ? "left" :
      k === "ArrowRight" ? "right" :
      k === "ArrowUp" ? "up" :
      k === "ArrowDown" ? "down" : null;

    if (!dir) return;

    const active = document.activeElement;
    if (!active || !active.matches('[data-dpad="item"]')) return;

    const navRoot = active.closest("[data-nav]") || document.body;
    const items = focusables(navRoot);
    const next = bestCandidate(active, dir, items);
    if (next) {
      e.preventDefault();
      next.focus();
    }
  }

  window.addEventListener("keydown", handleKey, { passive: false });
})();
