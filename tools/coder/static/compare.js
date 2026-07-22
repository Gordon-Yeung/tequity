/* Compare + Adjudicate screen. Relies on helpers from app.js (window.CoderApp). */
(function () {
  const { CATS, el, esc, api } = window.CoderApp;

  const pct = (x) => (x == null ? "—" : (x * 100).toFixed(0) + "%");
  const num2 = (x) => (x == null ? "—" : x.toFixed(2));

  let current = null;   // last compare response
  const adj = {};       // turn -> {categories:[], other_label, note, confidence, include, resolution, source}
  let availableCoders = [];  // last fetched coder-id list for the selected transcript

  async function populateCoders() {
    const vid = el("#cmp-transcript").value;
    if (!vid) return;
    let coders = [];
    try { coders = await api(`/api/coders/${vid}`); } catch (e) {}
    availableCoders = coders;
    // "llm" and "adjudicated" are derived/system codings, not human coders — keep
    // them out of the A/B selectors (LLM is included via the checkbox instead).
    const human = coders.filter((c) => c !== "adjudicated" && c !== "llm");
    const opts = human.map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
    el("#cmp-a").innerHTML = opts;
    el("#cmp-b").innerHTML = opts;
    if (human.length > 1) el("#cmp-b").selectedIndex = 1;
    el("#cmp-llm").checked = coders.includes("llm");
  }

  // Build the 8 stat cards for one pairwise comparison. `labels` overrides the
  // "Only A"/"Only B" wording (e.g. LLM-only / coder-only) and the per-category tags.
  function statCards(b, c, labels) {
    const L = labels || { aOnly: "Only A", bOnly: "Only B", aTag: "A", bTag: "B" };
    return [
      ["Both flagged", b.both],
      [L.aOnly, b.a_only],
      [L.bOnly, b.b_only],
      ["Raw agreement", pct(b.raw_agreement)],
      ["Cohen's κ", num2(b.cohen_kappa)],
      ["PABAK", num2(b.pabak)],
      ["Positive agreement", pct(b.positive_agreement)],
      ["Category Jaccard", c.mean_jaccard == null ? "—" : num2(c.mean_jaccard)],
    ].map(([k, v]) => `<div class="stat"><div class="k">${k}</div><div class="v">${v}</div></div>`).join("");
  }

  function perCatLine(c, aTag, bTag) {
    return Object.entries(c.per_category || {}).map(([cat, v]) =>
      `${cat}: ${v.both}✓ / ${v.a_only}${aTag} / ${v.b_only}${bTag}`).join(" &nbsp;·&nbsp; ") || "—";
  }

  // One LLM-vs-human panel. `sub` = {coder, binary, category}; LLM is rater "a".
  function llmPanel(sub) {
    const b = sub.binary, c = sub.category;
    const name = esc(sub.coder);
    const cards = statCards(b, c, { aOnly: "LLM only", bOnly: `${name} only`, aTag: "L", bTag: name });
    return `<div class="llm-panel">
      <h3>LLM vs Coder ${name}</h3>
      <div class="stats">${cards}
        <div class="caveat">
          Of ${b.n} teacher turns, LLM and ${name} both flagged ${b.both}
          (LLM-only ${b.a_only}, ${name}-only ${b.b_only}).
          Expect this κ to trail human–human agreement — the LLM flags a different set.
          Read <b>positive agreement</b> (${pct(b.positive_agreement)}) and
          <b>PABAK</b> (${num2(b.pabak)}) alongside κ.
          <br/>Per-category (both✓ / LLM-only / ${name}-only): ${perCatLine(c, "L", name)}
        </div>
      </div></div>`;
  }

  function renderStats(stats) {
    const b = stats.binary, c = stats.category;
    const cards = statCards(b, c);

    let html = `<div class="hh-panel"><h3>Coder A vs Coder B (human–human)</h3>
      <div class="stats">${cards}
      <div class="caveat">
        Over ${b.n} teacher turns, coders both flagged ${b.both}.
        Cohen's κ is deflated when flags are rare — read <b>positive agreement</b>
        (${pct(b.positive_agreement)}) and <b>PABAK</b> (${num2(b.pabak)}) alongside it,
        not in isolation.
        <br/>Per-category (both✓ / A-only / B-only): ${perCatLine(c, "A", "B")}
      </div></div></div>`;

    if (stats.llm) {
      html += llmPanel(stats.llm.vs_a) + llmPanel(stats.llm.vs_b);
    }

    el("#cmp-stats").innerHTML = html;
  }

  function codeCol(title, s) {
    if (!s) return `<div class="col empty"><h4>${title}</h4>not flagged</div>`;
    const cats = (s.categories || []).join(", ") + (s.other_label ? ` (${esc(s.other_label)})` : "");
    return `<div class="col"><h4>${title}</h4>
      <div><b>${esc(cats) || "—"}</b> <span class="muted">[${esc(s.confidence || "")}]</span></div>
      ${s.note ? `<div class="muted">${esc(s.note)}</div>` : ""}
      ${s.verbatim_quote ? `<div class="quote">${esc(s.verbatim_quote)}</div>` : ""}
    </div>`;
  }

  function prefillAdj(row) {
    const a = row.a, b = row.b;
    let categories = [];
    if (a && b) categories = [...new Set([...(a.categories || []), ...(b.categories || [])])];
    else if (a) categories = [...(a.categories || [])];
    else if (b) categories = [...(b.categories || [])];
    const note = (a && a.note) || (b && b.note) || "";
    const confidence = (a && a.confidence) || (b && b.confidence) || "medium";
    adj[row.turn] = {
      turn: row.turn, speaker: row.speaker, categories, other_label: "",
      note, confidence, verbatim_quote: (a && a.verbatim_quote) || (b && b.verbatim_quote) || row.text,
      include: true, resolution: row.status, source: [row.a && "a", row.b && "b"].filter(Boolean),
      scene_id: `t${row.turn}`,
    };
  }

  function renderAdj(row) {
    const s = adj[row.turn];
    const cats = CATS.map(([c]) =>
      `<label class="${s.categories.includes(c) ? "on" : ""}" data-c="${c}">
        <input type="checkbox" ${s.categories.includes(c) ? "checked" : ""}/> ${c}</label>`).join("");
    return `<div class="adj" data-turn="${row.turn}">
      <label class="check"><input type="checkbox" class="adj-include" ${s.include ? "checked" : ""}/>
        include in adjudicated.json</label>
      <div class="cats">${cats}</div>
      <textarea class="adj-note" placeholder="Adjudicated note">${esc(s.note)}</textarea>
    </div>`;
  }

  function renderRows(resp) {
    const html = resp.rows.map((row) => {
      prefillAdj(row);
      const statusLabel = { agree: "agree", category_mismatch: "category mismatch", a_only: "only A", b_only: "only B" }[row.status];
      const cols = codeCol("Coder A", row.a) + codeCol("Coder B", row.b) +
        (resp.has_llm ? codeCol("LLM", row.llm) : `<div class="col empty"><h4>LLM</h4>not loaded</div>`);
      const ctx = row.context.map((c) =>
        `<div class="t ${c.turn === row.turn ? "center" : ""}"><b>${c.turn} ${esc(c.speaker)}:</b> ${esc(c.text)}</div>`).join("");
      return `<div class="cmp-row ${row.status}" data-turn="${row.turn}">
        <div class="head">
          <span class="status">${statusLabel}</span>
          <span class="muted">turn ${row.turn} · ${esc(row.speaker)}</span>
          <button class="context-toggle" type="button">show context ±3</button>
        </div>
        <div class="context hidden">${ctx}</div>
        <div class="cols">${cols}</div>
        ${renderAdj(row)}
      </div>`;
    }).join("");
    el("#cmp-rows").innerHTML = html || `<p class="muted">No flagged turns from either coder.</p>`;
    el("#adj-bar").classList.toggle("hidden", resp.rows.length === 0);

    // wire per-row controls
    el("#cmp-rows").querySelectorAll(".cmp-row").forEach((node) => {
      const turn = Number(node.dataset.turn);
      node.querySelector(".context-toggle").addEventListener("click", (e) => {
        const c = node.querySelector(".context");
        c.classList.toggle("hidden");
        e.target.textContent = c.classList.contains("hidden") ? "show context ±3" : "hide context";
      });
      node.querySelector(".adj-include").addEventListener("change", (e) => { adj[turn].include = e.target.checked; });
      node.querySelector(".adj-note").addEventListener("input", (e) => { adj[turn].note = e.target.value; });
      node.querySelectorAll(".adj .cats label").forEach((l) => {
        l.addEventListener("click", () => {
          const cb = l.querySelector("input");
          // click bubbles from the input too; normalize after event settles
          setTimeout(() => {
            const on = cb.checked;
            l.classList.toggle("on", on);
            const c = l.dataset.c;
            const set = new Set(adj[turn].categories);
            if (on) set.add(c); else set.delete(c);
            adj[turn].categories = [...set];
            adj[turn].resolution = "modified";
          }, 0);
        });
      });
    });
  }

  async function runCompare() {
    const vid = el("#cmp-transcript").value;
    const a = el("#cmp-a").value, b = el("#cmp-b").value;
    if (!a || !b) { alert("Need two coders. Code a transcript first (or import LLM)."); return; }
    if (a === b) { alert("Pick two different coders."); return; }
    const wantLlm = el("#cmp-llm").checked;
    // "include LLM" is self-sufficient: if the LLM coding hasn't been imported yet,
    // pull it from the latest deficit run now instead of silently showing "not loaded".
    if (wantLlm && !availableCoders.includes("llm")) {
      const ok = await ensureLlmImported(vid);
      if (!ok) { el("#cmp-llm").checked = false; return; }
    }
    const llm = el("#cmp-llm").checked ? "1" : "0";
    try {
      const resp = await api(`/api/compare/${vid}?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}&llm=${llm}`);
      current = resp;
      Object.keys(adj).forEach((k) => delete adj[k]);
      renderStats(resp.stats);
      renderRows(resp);
    } catch (e) { alert(e.message); }
  }

  // Import LLM scenes for `vid` from the latest deficit run. Returns true on success.
  // `silent` suppresses the confirmation alert (used by the auto-import path).
  async function ensureLlmImported(vid, silent) {
    try {
      const r = await api(`/api/import-llm/${vid}`, { method: "POST" });
      if (!silent) alert(`Imported ${r.scenes} LLM scenes from ${r.source_run}.`);
      await populateCoders();
      el("#cmp-llm").checked = true;
      return true;
    } catch (e) {
      alert("Could not import LLM scenes: " + e.message +
            "\n\nRun scripts/deficit_analysis.py for this transcript first.");
      return false;
    }
  }

  async function importLlm() {
    await ensureLlmImported(el("#cmp-transcript").value, false);
  }

  async function saveAdjudicated() {
    const vid = el("#cmp-transcript").value;
    const scenes = Object.values(adj).filter((s) => s.include && s.categories.length);
    try {
      const r = await api(`/api/adjudicated/${vid}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenes }),
      });
      el("#adj-status").textContent = `Saved adjudicated.json (${r.scenes} scenes) ${new Date().toLocaleTimeString()}`;
    } catch (e) { el("#adj-status").textContent = "Save failed: " + e.message; }
  }

  window.Compare = {
    onEnter() { populateCoders(); },
  };

  el("#cmp-transcript").addEventListener("change", populateCoders);
  el("#cmp-run").addEventListener("click", runCompare);
  el("#cmp-import-llm").addEventListener("click", importLlm);
  el("#adj-save").addEventListener("click", saveAdjudicated);
})();
