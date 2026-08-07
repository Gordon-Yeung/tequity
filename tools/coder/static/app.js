/* Shared helpers + router + Code screen + Progress dashboard. */

const CATS = [
  ["A", "Fixed-Ability Framing"],
  ["B", "Deficit Labeling/Grouping"],
  ["C", "Problem in Student/Home/Background"],
  ["D", "Deficit Attribution (Behavior/Motivation)"],
  ["E", "Lowered Expectations"],
  ["F", "Comparative Deficit"],
  ["G", "Totalizing Negation"],
  ["Other", "Other (specify)"],
];

const el = (sel) => document.querySelector(sel);
const esc = (s) => (s == null ? "" : String(s).replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])));

async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) {
    let msg = r.statusText;
    try { msg = (await r.json()).error || msg; } catch (e) {}
    throw new Error(msg);
  }
  return r.json();
}

// Observations are keyed on OBSID; teacher and year come from observation_index.csv
// and are shown for orientation only -- never used as a key. (The NCTE source's
// "video_id" column identifies a teacher observed across years, not a video.)
// Two fixed-width glyph columns, then padded fields. The <select> is monospaced
// in CSS so this actually lines up; without that the padding is decorative.
// Option text is the only channel available -- it cannot be styled.
//   col 1  this coder's status: circle / filled / tick
//   col 2  diamond when the LLM has findings for the observation, dot when not
// The flagged count is deliberately absent: a variable-width prefix threw every
// following column out of alignment, and the filled glyph already says "started".
function coderMark(t, coderId) {
  const mine = coderId ? (t.coders || {})[coderId] : null;
  if (!mine) return "○";
  return mine.completed ? "✓" : "●";
}

const padS = (v, n) => String(v ?? "").padStart(n);
const padE = (v, n) => String(v ?? "").padEnd(n);

function obsLabel(t, coderId) {
  const cols =
    `${coderMark(t, coderId)} ${t.llm_scenes ? "✦" : "·"}  ` +
    `${padS(t.obsid, 5)}  ` +
    `teacher ${padE(t.teacher_id || "—", 8)}` +
    `yr ${padE(t.year || "—", 4)}` +
    `${padS(t.teacher_turns, 4)}/${padE(t.turn_count, 4)}`;
  // Variable-length notes go last, where they cannot disturb the columns above.
  const tail = [];
  if (t.assigned === false) tail.push("not in sample");
  if (t.error) tail.push("[MISSING FILE]");
  return cols + (tail.length ? " · " + tail.join(" · ") : "");
}

let transcriptList = [];   // last /api/transcripts payload; relabelled locally

/* ---- picker filters -------------------------------------------------------
   "Which of my assigned observations am I part-way through?" is the question
   that has to keep working as the corpus grows -- a shortcut naming one
   observation stops being useful the moment more than a handful are in flight.
   These predicates scale to any N, and the counts are rendered into the option
   labels so the distribution is visible before you filter. */
const PICKER_FILTERS = [
  ["all", "All", () => true],
  ["mine_wip", "My in progress", (t, c) => Boolean(c && (t.coders || {})[c] && !t.coders[c].completed)],
  ["mine_done", "My completed", (t, c) => Boolean(c && (t.coders || {})[c] && t.coders[c].completed)],
  ["mine_none", "Not started by me", (t, c) => !(c && (t.coders || {})[c])],
  ["any_coded", "Coded by anyone", (t) => Object.keys(t.coders || {})
    .some((k) => k !== "llm" && k !== "adjudicated")],
  ["has_llm", "Has LLM findings", (t) => Boolean(t.llm_scenes)],
];

function currentFilter(sel) {
  const node = el(sel);
  const key = node ? node.value : "all";
  return PICKER_FILTERS.find((f) => f[0] === key) || PICKER_FILTERS[0];
}

function renderFilterOptions() {
  const coderId = (el("#coder-id").value || "").trim();
  const opts = PICKER_FILTERS.map(([key, label, pred]) => {
    const n = transcriptList.filter((t) => pred(t, coderId)).length;
    return `<option value="${key}">${esc(label)} (${n})</option>`;
  }).join("");
  for (const sel of ["#picker-filter", "#cmp-filter"]) {
    const node = el(sel);
    if (!node) continue;
    const keep = node.value;
    node.innerHTML = opts;
    if (keep) node.value = keep;
  }
}

async function loadTranscriptList() {
  transcriptList = await api("/api/transcripts");
  renderTranscriptOptions();
  return transcriptList;
}

// Re-label from the cached payload. Switching coder id changes only the glyphs,
// so it must never cost a round trip.
function renderTranscriptOptions() {
  const coderId = (el("#coder-id").value || "").trim();
  renderFilterOptions();
  [["#transcript-select", "#picker-filter"], ["#cmp-transcript", "#cmp-filter"]].forEach(
    ([sel, filterSel]) => {
      const node = el(sel);
      if (!node) return;
      const keep = node.value;
      const pred = currentFilter(filterSel)[2];
      // Always keep the current selection in the list even when it fails the
      // filter -- silently dropping the loaded observation out of the picker is
      // how a coder loses their place mid-transcript.
      const shown = transcriptList.filter((t) => pred(t, coderId) || t.obsid === keep);
      node.innerHTML = shown.map((t) =>
        `<option value="${esc(t.obsid)}"${t.error ? " disabled" : ""}>${esc(obsLabel(t, coderId))}</option>`
      ).join("") || `<option value="">(none match this filter)</option>`;
      if (keep && shown.some((t) => t.obsid === keep)) node.value = keep;
    });
}

// expose for compare.js / findings.js
window.CoderApp = {
  CATS, el, esc, api,
  // Lets the Compare screen ask "does this observation have LLM findings?"
  // without a round trip -- /api/transcripts already carries the count.
  transcriptRow: (obsid) => transcriptList.find((t) => t.obsid === obsid) || null,
};

/* ------------------------------ router ------------------------------ */
function route() {
  const tab = (location.hash.replace("#", "") || "code");
  document.querySelectorAll(".view").forEach((v) => v.classList.add("hidden"));
  const view = el(`#view-${tab}`);
  if (view) view.classList.remove("hidden");
  document.querySelectorAll(".tabs a").forEach((a) =>
    a.classList.toggle("active", a.dataset.tab === tab));
  if (tab === "progress") renderProgress();
  if (tab === "findings" && window.Findings) window.Findings.onEnter();
  if (tab === "compare" && window.Compare) window.Compare.onEnter();
}
window.addEventListener("hashchange", route);

/* ------------------------------ Code screen ------------------------------ */
const Code = {
  coderId: "",
  obsid: "",
  turns: [],
  scenes: {},          // turn -> {turn, categories:[], other_label, note, confidence, verbatim_quote}
  saveTimer: null,
  lastViewed: 0,

  lsKey() { return `coding:${this.obsid}:${this.coderId}`; },

  async load() {
    this.coderId = el("#coder-id").value.trim();
    this.obsid = el("#transcript-select").value;
    if (!this.coderId) { alert("Enter a coder id first."); return; }

    const [tr, coding] = await Promise.all([
      api(`/api/transcript/${this.obsid}`),
      api(`/api/coding/${this.obsid}/${encodeURIComponent(this.coderId)}`),
    ]);
    this.turns = tr.turns;

    // Prefer newer localStorage draft if it exists (crash net).
    let scenes = coding.scenes || [];
    const draft = localStorage.getItem(this.lsKey());
    if (draft) {
      try {
        const d = JSON.parse(draft);
        if (d.updated_at && (!coding.updated_at || d.updated_at > coding.updated_at)) {
          scenes = d.scenes;
        }
      } catch (e) {}
    }
    this.scenes = {};
    scenes.forEach((s) => { this.scenes[s.turn] = s; });
    this.lastViewed = (coding.progress && coding.progress.last_turn_viewed) || 0;

    this.renderHeader(tr);
    this.render();
    if (this.lastViewed) {
      const node = el(`#turn-${this.lastViewed}`);
      if (node) node.scrollIntoView({ block: "center" });
    }
    this.updateProgressInfo();
  },

  // Identity banner: which observation, whose class, which year. Coders work one
  // observation at a time and the OBSID alone is not memorable enough to catch a
  // mis-click before an hour of coding lands in the wrong file.
  renderHeader(tr) {
    const node = el("#obs-header");
    if (!node) return;
    const bits = [`<strong>Observation ${esc(tr.obsid)}</strong>`];
    if (tr.teacher_id) bits.push(`Teacher ${esc(tr.teacher_id)}`);
    if (tr.year) bits.push(`Year ${esc(tr.year)}`);
    bits.push(`${tr.teacher_turns} teacher turns of ${tr.turn_count}`);
    const warn = tr.shared_video_id
      ? ` <span class="badge conf" title="This OBSID is claimed by more than one video_id in the source; teacher attribution is ambiguous.">shared teacher id</span>`
      : "";
    node.innerHTML = bits.join(" &middot; ") + warn;
    node.classList.remove("hidden");
  },

  render() {
    const html = this.turns.map((t) => this.renderTurn(t)).join("");
    el("#transcript").innerHTML = html;
    el("#transcript").querySelectorAll(".turn.teacher").forEach((node) => {
      node.addEventListener("click", (e) => {
        if (e.target.closest(".coder")) return; // don't re-open when editing
        this.openEditor(Number(node.dataset.turn));
      });
    });
  },

  renderTurn(t) {
    const teacher = t.is_teacher;
    const scene = this.scenes[t.turn];
    const flagged = scene && scene.categories && scene.categories.length > 0;
    const badges = flagged
      ? `<div class="badges">${scene.categories.map((c) => `<span class="badge">${esc(c)}</span>`).join("")}
         <span class="badge conf">${esc(scene.confidence || "medium")}</span></div>`
      : "";
    return `
      <div class="turn ${teacher ? "teacher" : "student"} ${flagged ? "flagged" : ""}"
           id="turn-${t.turn}" data-turn="${t.turn}">
        <div class="num">${t.turn}</div>
        <div class="spk">${esc(t.speaker)}</div>
        <div class="txt">${esc(t.text)}${badges}</div>
      </div>`;
  },

  openEditor(turn) {
    this.lastViewed = turn;
    const existing = el(`#turn-${turn}`).nextElementSibling;
    if (existing && existing.classList.contains("coder")) { existing.remove(); return; }
    document.querySelectorAll(".coder").forEach((n) => n.remove());

    const scene = this.scenes[turn] || { turn, categories: [], other_label: "", note: "", confidence: "medium", verbatim_quote: "" };
    const cats = CATS.map(([c, label]) => {
      const on = scene.categories.includes(c);
      return `<label class="${on ? "on" : ""}" data-c="${c}" title="${esc(label)}">
        <input type="checkbox" ${on ? "checked" : ""}/> ${c}${c === "Other" ? "" : ` <span class="muted">${esc(label)}</span>`}
      </label>`;
    }).join("");

    const panel = document.createElement("div");
    panel.className = "coder";
    panel.innerHTML = `
      <div class="cats">${cats}</div>
      <div class="row2">
        <input class="other" type="text" placeholder="Other: specify" value="${esc(scene.other_label)}" style="min-width:220px" />
        <label>Confidence <span class="muted" title="high = clear & explicit · medium = likely deficit, some ambiguity (default) · low = ambiguous, flag to discuss. See Codebook.">(?)</span>
          <select class="conf">
            <option value="high" ${scene.confidence === "high" ? "selected" : ""}>high — clear/explicit</option>
            <option value="medium" ${scene.confidence === "medium" ? "selected" : ""}>medium — likely (default)</option>
            <option value="low" ${scene.confidence === "low" ? "selected" : ""}>low — ambiguous</option>
          </select>
        </label>
        <button class="secondary quote-btn" type="button">Use selected text as quote</button>
      </div>
      <div class="quote-line muted">${scene.verbatim_quote ? "Quote span: " + esc(scene.verbatim_quote) : "Quote: whole turn (default)"}</div>
      <textarea class="note" placeholder="Notes / rationale">${esc(scene.note)}</textarea>
      <div class="actions">
        <button class="del" type="button">Remove flag</button>
      </div>`;
    el(`#turn-${turn}`).after(panel);

    const commit = () => {
      const categories = [...panel.querySelectorAll(".cats input:checked")]
        .map((i) => i.closest("label").dataset.c);
      panel.querySelectorAll(".cats label").forEach((l) =>
        l.classList.toggle("on", l.querySelector("input").checked));
      const s = {
        turn,
        speaker: "teacher",
        categories,
        other_label: panel.querySelector(".other").value.trim(),
        note: panel.querySelector(".note").value.trim(),
        confidence: panel.querySelector(".conf").value,
        verbatim_quote: scene.verbatim_quote || "",
        scene_id: `t${turn}`,
      };
      if (categories.length === 0 && !s.note) { delete this.scenes[turn]; }
      else { this.scenes[turn] = s; }
      this.markBadges(turn);
      this.scheduleSave();
    };

    panel.querySelectorAll(".cats input, .conf, .other, .note").forEach((n) => {
      n.addEventListener("change", commit);
      n.addEventListener("input", commit);
    });
    panel.querySelector(".quote-btn").addEventListener("click", () => {
      const sel = window.getSelection().toString().trim();
      if (sel) {
        scene.verbatim_quote = sel;
        panel.querySelector(".quote-line").textContent = "Quote span: " + sel;
        commit();
      }
    });
    panel.querySelector(".del").addEventListener("click", () => {
      delete this.scenes[turn];
      panel.remove();
      this.markBadges(turn);
      this.scheduleSave();
    });
  },

  markBadges(turn) {
    const node = el(`#turn-${turn}`);
    if (!node) return;
    const scene = this.scenes[turn];
    const flagged = scene && scene.categories.length > 0;
    node.classList.toggle("flagged", !!flagged);
    const old = node.querySelector(".badges");
    if (old) old.remove();
    if (flagged) {
      const div = document.createElement("div");
      div.className = "badges";
      div.innerHTML = scene.categories.map((c) => `<span class="badge">${esc(c)}</span>`).join("") +
        `<span class="badge conf">${esc(scene.confidence)}</span>`;
      node.querySelector(".txt").appendChild(div);
    }
    this.updateProgressInfo();
  },

  updateProgressInfo() {
    const n = Object.values(this.scenes).filter((s) => s.categories.length).length;
    el("#progress-info").textContent = `${n} flagged`;
  },

  payload() {
    return {
      scenes: Object.values(this.scenes),
      progress: { last_turn_viewed: this.lastViewed, completed: false },
    };
  },

  scheduleSave() {
    this.setStatus("saving", "Saving…");
    // localStorage mirror immediately (crash net)
    localStorage.setItem(this.lsKey(), JSON.stringify({
      updated_at: new Date().toISOString(), scenes: Object.values(this.scenes),
    }));
    clearTimeout(this.saveTimer);
    this.saveTimer = setTimeout(() => this.save(), 1200);
  },

  async save() {
    try {
      const res = await api(`/api/coding/${this.obsid}/${encodeURIComponent(this.coderId)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(this.payload()),
      });
      this.setStatus("saved", `Saved ${new Date().toLocaleTimeString()}`);
      // Keep the picker's tracker honest without another round trip. Guarded on
      // the count actually moving so the 1.2s autosave doesn't rebuild 320
      // options on every keystroke.
      const row = transcriptList.find((t) => t.obsid === this.obsid);
      if (row) {
        const n = Object.values(this.scenes).filter((s) => s.categories.length).length;
        row.coders = row.coders || {};
        const prev = row.coders[this.coderId];
        if (!prev || prev.flagged !== n) {
          row.coders[this.coderId] = { scenes: n, flagged: n, completed: false, updated_at: res.updated_at };
          renderTranscriptOptions();
        }
      }
      const warn = el("#unverified-warn");
      if (res.unverified && res.unverified.length) {
        warn.classList.remove("hidden");
        warn.textContent = `⚠ Quote not found verbatim in source for turn(s): ${res.unverified.join(", ")}. Check the highlighted span.`;
      } else {
        warn.classList.add("hidden");
      }
    } catch (e) {
      this.setStatus("", "Save failed: " + e.message);
    }
  },

  setStatus(cls, txt) {
    const s = el("#save-status");
    s.className = "save-status " + cls;
    s.textContent = txt;
  },

  // Jump straight to one turn of one observation. Used by the LLM Findings
  // screen so a model finding can be inspected in its own transcript in one
  // click instead of being hunted for in the picker.
  async openAt(obsid, turn) {
    const sel = el("#transcript-select");
    const known = [...sel.options].some((o) => o.value === obsid);
    if (!known) {
      alert(`Observation ${obsid} is not in the picker (not assigned and not yet coded), `
            + `so it cannot be opened here.`);
      return;
    }
    sel.value = obsid;
    location.hash = "#code";
    await this.load();
    const node = el(`#turn-${turn}`);
    if (node) {
      node.scrollIntoView({ block: "center" });
      // Brief highlight: after a tab switch the target turn is otherwise just
      // one row among hundreds.
      node.classList.add("jump-target");
      setTimeout(() => node.classList.remove("jump-target"), 2500);
    }
  },
};
window.CoderApp.Code = Code;

el("#load-btn").addEventListener("click", () => Code.load().catch((e) => alert(e.message)));
["#picker-filter", "#cmp-filter"].forEach((sel) => {
  const node = el(sel);
  if (node) node.addEventListener("change", renderTranscriptOptions);
});
el("#save-now-btn").addEventListener("click", () => {
  if (!Code.obsid || !Code.coderId) { alert("Load a transcript first."); return; }
  clearTimeout(Code.saveTimer);
  Code.save();
});
window.addEventListener("beforeunload", () => {
  if (Code.obsid && Code.coderId) {
    navigator.sendBeacon(
      `/api/coding/${Code.obsid}/${encodeURIComponent(Code.coderId)}`,
      new Blob([JSON.stringify(Code.payload())], { type: "application/json" })
    );
  }
});

/* ------------------------------ Progress dashboard ------------------------------ */
async function renderProgress() {
  const status = await api("/api/status");
  const rows = status.map((s) => {
    if (!s.coders.length) {
      return `<tr><td>${esc(s.obsid)}</td><td colspan="3" class="muted">—</td></tr>`;
    }
    return s.coders.map((c, i) => `
      <tr>
        ${i === 0 ? `<td rowspan="${s.coders.length}">${esc(s.obsid)}</td>` : ""}
        <td>${esc(c.coder_id)}</td>
        <td>${c.scenes} <span class="pill ${c.completed ? "done" : "wip"}">${c.completed ? "done" : "in progress"}</span></td>
        <td class="muted">${esc(c.updated_at || "")}</td>
      </tr>`).join("");
  }).join("");
  el("#status-table").innerHTML = `
    <table>
      <thead><tr><th>Transcript</th><th>Coder</th><th>Scenes flagged</th><th>Last updated</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

/* ------------------------------ boot ------------------------------ */
(async function boot() {
  const saved = localStorage.getItem("coderId");
  if (saved) el("#coder-id").value = saved;
  // "change" not "input": the glyphs are per-coder, but rebuilding 320 options
  // on every keystroke of a name is not worth the liveness.
  el("#coder-id").addEventListener("change", (e) => {
    localStorage.setItem("coderId", e.target.value.trim());
    renderTranscriptOptions();
  });
  await loadTranscriptList();
  route();
})();
