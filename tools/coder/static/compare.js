/* Compare + Adjudicate screen. Relies on helpers from app.js (window.CoderApp). */
(function () {
  const { CATS, el, esc, api, transcriptRow } = window.CoderApp;

  const pct = (x) => (x == null ? "—" : (x * 100).toFixed(0) + "%");
  const num2 = (x) => (x == null ? "—" : x.toFixed(2));

  let current = null;   // last compare response
  const adj = {};       // turn -> {categories:[], other_label, note, confidence, include, resolution, source}
  let availableCoders = [];  // last fetched coder-id list for the selected transcript

  async function populateCoders() {
    const vid = el("#cmp-transcript").value;
    if (!vid) return;

    const fetchCoders = async () => {
      try { return await api(`/api/coders/${vid}`); } catch (e) { return []; }
    };

    let coders = await fetchCoders();
    // Auto-import, but only where there is something to import: the picker
    // payload already carries the scene count, so this never fires a POST that
    // would 404, and never writes a file for an observation with no findings.
    const row = transcriptRow(vid);
    if (row && row.llm_scenes && !coders.includes("llm")) {
      if (await ensureLlmImported(vid, true)) coders = await fetchCoders();
    }
    availableCoders = coders;
    // "llm" is selectable as a rater: an observation the model has coded but no
    // human has should still be readable here, and LLM-vs-one-human is a real
    // comparison. "adjudicated" stays out -- it is an output of this screen, so
    // rating against it would be circular.
    const raters = coders.filter((c) => c !== "adjudicated");
    const opts = raters.map((c) =>
      `<option value="${esc(c)}">${esc(c)}${c === "llm" ? " (model)" : ""}</option>`).join("");
    el("#cmp-a").innerHTML = opts;
    el("#cmp-b").innerHTML = opts;
    // Prefer a human-vs-human default when two humans exist; otherwise fall back
    // to whatever is available rather than leaving the selectors empty.
    const humans = raters.filter((c) => c !== "llm");
    if (humans.length > 1) {
      el("#cmp-a").value = humans[0];
      el("#cmp-b").value = humans[1];
    } else if (raters.length > 1) {
      el("#cmp-b").selectedIndex = 1;
    }
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

  function renderStats(stats, resp) {
    // One rater on both sides: reading mode, not agreement. The server omits the
    // statistics rather than sending 1.0s that would be mistaken for a result.
    if (resp && resp.single_rater) {
      const who = esc(resp.a_id);
      el("#cmp-stats").innerHTML = `<div class="hh-panel">
        <h3>Single-rater view — ${who}${resp.a_id === "llm" ? " (model)" : ""}</h3>
        <div class="caveat">
          Showing every turn <b>${who}</b> flagged, in transcript context, across
          ${stats.universe_teacher_turns} teacher turns. No agreement statistics:
          with one rater there is nothing to agree with, and &kappa; against itself
          is 1.0 by construction. Pick two different raters to get IRR.
        </div></div>`;
      return;
    }
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

  function codeCol(title, s, extraClass) {
    const cls = extraClass ? ` ${extraClass}` : "";
    if (!s) return `<div class="col empty${cls}"><h4>${title}</h4>not flagged</div>`;
    const cats = (s.categories || []).join(", ") + (s.other_label ? ` (${esc(s.other_label)})` : "");
    return `<div class="col${cls}"><h4>${title}</h4>
      <div><b>${esc(cats) || "—"}</b> <span class="muted">[${esc(s.confidence || "")}]</span></div>
      ${s.note ? `<div class="muted">${esc(s.note)}</div>` : ""}
      ${s.verbatim_quote ? `<div class="quote">${esc(s.verbatim_quote)}</div>` : ""}
    </div>`;
  }

  function prefillAdj(row, resp) {
    const a = row.a, b = row.b;
    // Whether a *human* flagged this turn. The LLM can now occupy the A or B
    // slot, so "row.a exists" no longer implies a person put it there — check
    // which rater each slot actually is.
    const aHuman = a && resp && resp.a_id !== "llm";
    const bHuman = b && resp && resp.b_id !== "llm";
    const humanFlagged = Boolean(aHuman || bHuman);
    // Fall back to the third-column LLM only when neither slot flagged the turn
    // — i.e. the row exists solely because the LLM did. Where a rater flagged
    // it, that rater's codes are the prefill and the LLM stays advisory.
    const llm = (!a && !b) ? row.llm : null;
    let categories = [];
    if (a && b) categories = [...new Set([...(a.categories || []), ...(b.categories || [])])];
    else if (a) categories = [...(a.categories || [])];
    else if (b) categories = [...(b.categories || [])];
    else if (llm) categories = [...(llm.categories || [])];
    const note = (a && a.note) || (b && b.note) || (llm && llm.note) || "";
    const confidence = (a && a.confidence) || (b && b.confidence) || (llm && llm.confidence) || "medium";
    adj[row.turn] = {
      turn: row.turn, speaker: row.speaker, categories, other_label: "",
      note, confidence,
      verbatim_quote: (a && a.verbatim_quote) || (b && b.verbatim_quote) ||
                      (llm && llm.verbatim_quote) || row.text,
      // Machine-only turns start unchecked: an unreviewed model flag must never
      // reach adjudicated.json without a human affirmatively including it. This
      // covers both the third-column LLM and the LLM selected as a rater.
      include: humanFlagged,
      resolution: row.status,
      source: [a && "a", b && "b", llm && "llm"].filter(Boolean),
      scene_id: `t${row.turn}`,
    };

    // Overlay a previously saved adjudication for this turn -- this is what makes
    // the screen RESUME rather than start over. The saved note / category edits /
    // include flag win over the freshly computed prefill; `restored` marks the
    // row so the UI can say so.
    const saved = row.adj;
    if (saved) {
      Object.assign(adj[row.turn], {
        categories: [...(saved.categories || [])],
        other_label: saved.other_label || "",
        note: saved.note != null ? saved.note : adj[row.turn].note,
        confidence: saved.confidence || adj[row.turn].confidence,
        verbatim_quote: saved.verbatim_quote || adj[row.turn].verbatim_quote,
        include: saved.include != null ? saved.include : true,
        resolution: saved.resolution || "restored",
        restored: true,
      });
    }
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
      prefillAdj(row, resp);
      // One rater selected on both sides is a reading view, not a comparison.
      // Rendering it as "Coder A agrees with Coder B" would be one coding shown
      // twice and read as corroboration, so collapse to a single column.
      const single = resp.single_rater;
      const statusLabel = single ? "flagged" : { agree: "agree",
                            category_mismatch: "category mismatch",
                            a_only: "only A", b_only: "only B", llm_only: "only LLM",
                            adjudicated_only: "from saved adjudication" }[row.status];
      const savedCol = resp.has_adjudicated
        ? codeCol("Saved adjudication", row.adj, "saved-adj")
        : "";
      const cols = single
        ? codeCol(resp.a_id === "llm" ? "LLM (model)" : `Coder ${resp.a_id}`, row.a) + savedCol
        : codeCol("Coder A", row.a) + codeCol("Coder B", row.b) +
          (resp.has_llm ? codeCol("LLM", row.llm) : `<div class="col empty"><h4>LLM</h4>not loaded</div>`) +
          savedCol;
      const ctx = row.context.map((c) =>
        `<div class="t ${c.turn === row.turn ? "center" : ""}"><b>${c.turn} ${esc(c.speaker)}:</b> ${esc(c.text)}</div>`).join("");
      return `<div class="cmp-row ${single ? "single" : row.status}" data-turn="${row.turn}">
        <div class="head">
          <span class="status">${statusLabel}</span>
          <span class="muted">turn ${row.turn} · ${esc(row.speaker)}</span>
          ${row.adj ? `<span class="restored-tag" title="restored from adjudicated.json">↺ saved</span>` : ""}
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
    if (!a || !b) { alert("No coding found for this transcript yet."); return; }
    // Same rater on both sides is allowed: it is the single-rater reading view,
    // and the only way to read an observation the model has coded but no human has.
    // The server omits agreement statistics for that case.
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
      renderStats(resp.stats, resp);
      renderRows(resp);
      el("#adj-status").textContent = resp.has_adjudicated
        ? `Resumed adjudicated.json — rev ${resp.adjudicated_revision ?? "?"}, saved ${resp.adjudicated_updated_at || "?"}. Rows marked “↺ saved” carry your earlier decision.`
        : "";
      refreshAdjHistory(vid);
    } catch (e) { alert(e.message); }
  }

  // Import LLM scenes for `vid` from the latest deficit run. Returns true on success.
  // `silent` suppresses the confirmation alert (used by the auto-import path).
  // Single-purpose on purpose: it must NOT refresh the coder list itself, because
  // populateCoders() now calls this on transcript change and the two would recurse.
  // Callers refresh.
  async function ensureLlmImported(vid, silent) {
    try {
      const r = await api(`/api/import-llm/${vid}`, { method: "POST" });
      if (!silent) alert(`Imported ${r.scenes} LLM scenes from ${r.source_run}.`);
      return true;
    } catch (e) {
      if (!silent) {
        alert("Could not import LLM scenes: " + e.message +
              "\n\nRun scripts/deficit_analysis.py for this transcript first.");
      }
      return false;
    }
  }

  async function importLlm() {
    if (await ensureLlmImported(el("#cmp-transcript").value, false)) await populateCoders();
  }

  async function saveAdjudicated() {
    const vid = el("#cmp-transcript").value;
    const scenes = Object.values(adj).filter((s) => s.include && s.categories.length);
    // Also send the full working set -- included, excluded and modified rows with
    // their notes -- so the server's history keeps a record of everything argued
    // over this pass, not just the rows that made the cut.
    const deliberation = Object.values(adj);
    const compared = current
      ? { a: current.a_id, b: current.b_id, llm: Boolean(current.has_llm) }
      : {};
    try {
      const r = await api(`/api/adjudicated/${vid}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenes, deliberation, compared }),
      });
      const kept = r.prior_versions
        ? ` · ${r.prior_versions} prior version${r.prior_versions === 1 ? "" : "s"} kept`
        : "";
      el("#adj-status").textContent =
        `Saved adjudicated.json — rev ${r.revision}, ${r.scenes} scene${r.scenes === 1 ? "" : "s"}${kept} · ${new Date().toLocaleTimeString()}`;
      refreshAdjHistory(vid);
    } catch (e) { el("#adj-status").textContent = "Save failed: " + e.message; }
  }

  // Advisory line under the Save button: shows that prior adjudicated versions
  // exist and where to find them. Failure is silent -- history is not load-bearing.
  async function refreshAdjHistory(vid) {
    const box = el("#adj-history");
    if (!box || !vid) return;
    try {
      const hist = await api(`/api/adjudicated/${vid}/history`);
      if (hist.length < 2) { box.textContent = ""; return; }
      box.textContent =
        "Saved versions: " +
        hist.map((h) => `rev${h.revision ?? "?"} (${h.scenes} sc)${h.current ? " ←current" : ""}`).join("  ·  ") +
        `  —  data/human_coding/${vid}/history/adjudicated/`;
    } catch (e) { box.textContent = ""; }
  }

  window.Compare = {
    onEnter() { populateCoders(); },
  };

  el("#cmp-transcript").addEventListener("change", populateCoders);
  el("#cmp-run").addEventListener("click", runCompare);
  el("#cmp-import-llm").addEventListener("click", importLlm);
  el("#adj-save").addEventListener("click", saveAdjudicated);
})();
