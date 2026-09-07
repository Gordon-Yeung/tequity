# Human Deficit-Language Coding Tool

A small local web app for **two researchers to independently code** classroom
transcripts for deficit-based teacher language (categories A–G + Other), then
**compare and adjudicate** their codings against each other and against the LLM
pipeline output (Study 2).

It's the human-coding companion to `scripts/deficit_analysis.py`: same corpus,
same categories, same verbatim-quote discipline — but the judgments come from
people, so the automated findings can be validated and a gold standard built.

## Run it

```bash
pip install -r requirements.txt          # from repo root (Flask; anthropic optional)
python tools/coder/app.py                # or: py tools/coder/app.py
# open http://localhost:5000
```

Works on Python 3.13+. Flask is the only hard dependency. The tool reuses the
pipeline's `load_transcript` / quote-verification when `anthropic` is installed;
if it isn't, it falls back to identical built-in copies, so it still runs.

## Workflow

1. **Code (blind).** Each coder enters their id, picks a transcript, and clicks
   *Load / Resume*. Scroll the transcript; **click a teacher turn** to flag it,
   tick one or more categories (A–G / Other), set confidence, add a note.
   Optionally select text in the turn and *Use selected text as quote* to record
   the exact span (otherwise the whole turn is the quote). Student turns are
   context only. The LLM's flags are **not shown here** — coding is blind.
2. **Autosave.** Changes save to `data/human_coding/<video>/<coder>.json` about a
   second after you stop typing, with a `localStorage` mirror as a crash net.
   Reopen the same transcript+coder to resume where you left off.
3. **Compare.** On the *Compare & Adjudicate* tab pick the transcript and two
   coders. You get agreement stats and every flagged turn colour-coded:
   green = agree, amber = both flagged but categories differ, red = only one
   flagged. Tick *include LLM* (after *Import LLM scenes*) to add a third column.
4. **Adjudicate.** Each row has an editor pre-filled from the two codings. Adjust
   categories/notes, keep *include* ticked for the ones that belong in the gold
   standard, and click *Save adjudicated.json*.
   **Resuming:** if an `adjudicated.json` already exists, re-running the compare
   reloads it — rows that carry a prior decision are marked *↺ saved* and show a
   *Saved adjudication* column, and the editor is rehydrated with your earlier
   categories/notes/include flags rather than rebuilt from the raw codings.

## Reading the agreement stats (important)

Flagging is rare relative to the teacher turns in an observation (median 161,
max 607), so **raw agreement is misleadingly high and Cohen's κ is misleadingly
low** (the "kappa paradox"). Read them together:

| Stat | What it tells you |
|------|-------------------|
| Raw agreement | inflated — dominated by the many turns *neither* flagged |
| Cohen's κ | chance-corrected, but pessimistic when flags are rare |
| PABAK | κ adjusted for prevalence/bias |
| **Positive agreement** | Dice/F1 on the flags themselves — the honest headline |
| Category Jaccard | given both flagged a turn, how much categories overlap |

Do not report κ alone.

## The unit of analysis: OBSID, not video_id

Everything here is keyed on **OBSID** — one observed class. The NCTE source's
`video_id` column is *not* a video: 192 of its 319 values span more than one
year, so it identifies a **teacher** observed repeatedly (~5.2 observations
each, up to 11). Teacher and year are display metadata, joined in from
`data/observation_index.csv`; they are never keys.

Two ids are never encoded in one filename. Besides being ambiguous to parse,
OBSID 508 belongs to two `video_id`s, so a single filename could not express it.

| What | Where |
|---|---|
| Transcript | `data/transcripts/by_obsid/<OBSID>.csv` (`speaker,cleaned_text`, bytes frozen) |
| Identity + counts | `data/observation_index.csv` (`obsid, video_id, year, …, sha256`) |
| Coding assignment | `data/samples/one_per_teacher.csv` |
| Portable copy | `python scripts/export_observation.py <OBSID>` → `data/exports/` |

The tool lists whatever is in the sample manifest, falling back to the legacy
`*_original.csv` set if no manifest exists. Study 1's hand-prepared `706` and
`543` files keep their own column schemas and still resolve by name.

## File layout

```
data/human_coding/<OBSID>/
  <coder_id>.json      # one per coder (autosave target; the handoff artifact)
  llm.json             # LLM scenes imported as a third "coder"
  adjudicated.json     # reconciled gold standard (latest revision)
  history/
    adjudicated/       # every prior Save, rev<NNN>_<timestamp>.json, oldest-first
    <coder_id>/        # autosave snapshots, throttled to one per 10 min
```

### Versioning (nothing overwrites silently)

Every write keeps the version it replaces. `adjudicated.json` is snapshotted to
`history/adjudicated/` on **each** click of *Save adjudicated.json*; per-coder
autosaves are snapshotted at most once per 10 minutes. Files carry a `revision`
counter and a stable `created_at`. The adjudicated file also stores:

- `deliberation` — the full working set for that pass, **including rows that were
  reviewed and excluded**, with their notes. `scenes` is only what made the cut;
  `deliberation` is the audit trail of what was argued over.
- `compared` — which two codings (and whether the LLM) were on screen.

`GET /api/adjudicated/<obsid>/history` lists all revisions. To roll one back,
copy the chosen `history/adjudicated/rev*.json` over `adjudicated.json` by hand.

### Per-coder JSON

```json
{
  "obsid": "2204",
  "coder_id": "gordon",
  "created_at": "2026-07-15T12:00:00",
  "updated_at": "2026-07-15T12:34:00",
  "revision": 12,
  "progress": { "last_turn_viewed": 640, "completed": false },
  "scenes": [
    {
      "scene_id": "t227",
      "turn": 227,
      "speaker": "teacher",
      "verbatim_quote": "those people that are not paying attention ...",
      "quote_verified": true,
      "categories": ["D", "E"],
      "other_label": "",
      "note": "predicts failure before task attempted",
      "confidence": "high",
      "flagged_at": "2026-07-15T12:10:00"
    }
  ]
}
```

`turn` matches the numbering in `scripts/deficit_analysis.py` exactly (1-based over
all CSV rows, keeping only rows with both a speaker and text — so numbers can have
gaps). This is what lets human flags line up with LLM scenes turn-for-turn.

## Categories (A–G, + Other)

Defined in `prompts/deficit_language_analysis_spec.txt` — the source of truth:
A Fixed-Ability · B Deficit Labeling/Grouping · C Problem in Student/Home/Background ·
D Deficit Attribution (Behavior/Motivation) · E Lowered Expectations ·
F Comparative Deficit · G Totalizing Negation.
