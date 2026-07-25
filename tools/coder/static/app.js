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
function obsLabel(t) {
  const bits = [`Obs ${t.obsid}`];
  if (t.teacher_id) bits.push(`teacher ${t.teacher_id}`);
  if (t.year) bits.push(`yr ${t.year}`);
  bits.push(`${t.teacher_turns} teacher / ${t.turn_count} turns`);
  return bits.join(" · ") + (t.error ? "  [MISSING FILE]" : "");
}

async function loadTranscriptList() {
  const list = await api("/api/transcripts");
  const opts = list.map((t) =>
    `<option value="${esc(t.obsid)}"${t.error ? " disabled" : ""}>${esc(obsLabel(t))}</option>`
  ).join("");
  ["#transcript-select", "#cmp-transcript"].forEach((sel) => {
    const node = el(sel);
    if (node) node.innerHTML = opts;
  });
  return list;
}

// expose for compare.js
window.CoderApp = { CATS, el, esc, api };

/* ------------------------------ router ------------------------------ */
function route() {
  const tab = (location.hash.replace("#", "") || "code");
  document.querySelectorAll(".view").forEach((v) => v.classList.add("hidden"));
  const view = el(`#view-${tab}`);
  if (view) view.classList.remove("hidden");
  document.querySelectorAll(".tabs a").forEach((a) =>
    a.classList.toggle("active", a.dataset.tab === tab));
  if (tab === "progress") renderProgress();
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
};

el("#load-btn").addEventListener("click", () => Code.load().catch((e) => alert(e.message)));
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
  el("#coder-id").addEventListener("change", (e) => localStorage.setItem("coderId", e.target.value.trim()));
  await loadTranscriptList();
  route();
})();
