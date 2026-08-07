/* LLM Findings browser. Relies on helpers from app.js (window.CoderApp).

   Reads the OBSID-keyed relabelled runs only. The raw data/deficit_scenes/run_*
   folders are named by the old NCTE video_id, so browsing them by name would
   attribute findings to the wrong observation -- the same defect this screen
   exists to make visible. */
(function () {
  const { CATS, el, esc, api, Code } = window.CoderApp;

  let rows = [];        // last /api/llm-findings payload
  let runs = [];

  function filtered() {
    const conf = el("#fnd-conf").value;
    const cat = el("#fnd-cat").value;
    const onlyAssigned = el("#fnd-assigned").checked;
    return rows.filter((r) =>
      (!conf || r.confidence === conf) &&
      (!cat || (r.categories || []).includes(cat)) &&
      (!onlyAssigned || r.assigned));
  }

  function render() {
    const shown = filtered();
    el("#fnd-count").textContent =
      `${shown.length} of ${rows.length} scenes · ${new Set(shown.map((r) => r.obsid)).size} observations`;

    if (!shown.length) {
      el("#fnd-rows").innerHTML = `<p class="muted">No scenes match these filters.</p>`;
      return;
    }

    el("#fnd-rows").innerHTML = shown.map((r) => {
      const cats = (r.categories || []).map((c) => `<span class="badge">${esc(c)}</span>`).join("") || "—";
      // "not in sample" matters: only 4 of the 52 scanned observations are in
      // the coding assignment, so most findings here are exploratory.
      const tags = [
        r.assigned ? `<span class="pill done">assigned</span>`
                   : `<span class="pill wip">not in sample</span>`,
        r.coders.length ? `<span class="muted">coded by ${esc(r.coders.join(", "))}</span>` : "",
      ].filter(Boolean).join(" ");
      return `<div class="fnd-row" data-obsid="${esc(r.obsid)}" data-turn="${esc(r.turns)}">
        <div class="head">
          <b>Obs ${esc(r.obsid)}</b>
          ${r.teacher_id ? `<span class="muted">teacher ${esc(r.teacher_id)} · yr ${esc(r.year)}</span>` : ""}
          <span class="muted">turn ${esc(r.turns)}</span>
          <span class="badge conf">${esc(r.confidence)}</span>
          <span class="badges">${cats}</span>
          ${tags}
          <button class="secondary fnd-open" type="button">Open in Code</button>
        </div>
        <div class="quote">${esc(r.verbatim_quote)}</div>
        ${r.rationale ? `<div class="muted rationale">${esc(r.rationale)}</div>` : ""}
      </div>`;
    }).join("");

    el("#fnd-rows").querySelectorAll(".fnd-open").forEach((btn) => {
      btn.addEventListener("click", () => {
        const node = btn.closest(".fnd-row");
        // turn_range can read like "12-14"; the first number is where to land.
        const turn = parseInt(String(node.dataset.turn).match(/\d+/)?.[0], 10);
        Code.openAt(node.dataset.obsid, turn).catch((e) => alert(e.message));
      });
    });
  }

  async function loadRun() {
    const run = el("#fnd-run").value;
    const d = await api(`/api/llm-findings${run ? `?run=${encodeURIComponent(run)}` : ""}`);
    if (d.error) {
      rows = [];
      el("#fnd-provenance").textContent = d.error;
      render();
      return;
    }
    rows = d.rows;
    const meta = runs.find((r) => r.run === d.run) || {};
    const dropped = [];
    if (meta.dropped_unverified) dropped.push(`${meta.dropped_unverified} dropped as unverifiable against today's transcripts`);
    if (meta.dropped_unresolved_legacy) dropped.push(`${meta.dropped_unresolved_legacy} from files the crosswalk could not resolve to an OBSID`);
    el("#fnd-provenance").innerHTML =
      `Relabelled from <code>data/deficit_scenes/${esc(d.run)}</code> via <code>data/obsid_crosswalk.csv</code>; `
      + `every quote re-verified against <code>by_obsid/&lt;obsid&gt;.csv</code>.`
      + (dropped.length ? ` ${esc(dropped.join("; "))}. See that run's <code>MANIFEST.json</code>.` : "");
    render();
  }

  async function onEnter() {
    if (!runs.length) {
      runs = await api("/api/llm-runs");
      el("#fnd-run").innerHTML = runs.map((r) =>
        `<option value="${esc(r.run)}">${esc(r.run)} — ${r.scenes} scenes, ${r.observations_with_scenes} observations</option>`
      ).join("") || `<option value="">(no relabelled runs)</option>`;
      el("#fnd-cat").innerHTML = `<option value="">all</option>` +
        CATS.map(([c, label]) => `<option value="${c}">${c} — ${esc(label)}</option>`).join("");
    }
    await loadRun();
  }

  window.Findings = { onEnter };

  el("#fnd-run").addEventListener("change", () => loadRun().catch((e) => alert(e.message)));
  ["#fnd-conf", "#fnd-cat", "#fnd-assigned"].forEach((sel) =>
    el(sel).addEventListener("change", render));
})();
