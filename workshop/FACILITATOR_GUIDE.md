# Noticing and Reframing Deficit Language — Teacher Workshop

**Duration:** 120 min (90- and 60-min cuts at the end)
**Group size:** 8–24, at tables of 3–4
**Source:** `data/deficit_scenes_obsid/run_2026-07-19_153121/`
**Scenes:** `workshop/scene_bank.json` · `scene_bank.csv` — rebuild with `py -3 workshop/build_scene_bank.py`

Every quote in this packet was re-verified against `data/transcripts/by_obsid/<obsid>.csv`
at build time. The builder refuses to write output if any fragment fails to land on its
expected turn.

---

## 1. What this session is for

It has two jobs and they pull in slightly different directions. Say so out loud in the room.

**For the teachers.** Build the noticing. Deficit framing is hard to catch in yourself because
it is usually fast, usually under frustration, and usually sits next to something you did well.
The session gives structured practice on other people's transcripts, which is the only low-cost
way to rehearse it.

**For the research.** Three things this project currently cannot get any other way:

1. **An unprimed human threshold.** The A–G rubric was written by researchers. Nobody knows what
   practising teachers flag when you hand them a turn and no categories at all. Round 1 measures it.
2. **A teacher-authored reframe corpus.** There is none in the repo. Without it there is nothing to
   evaluate a reframing tool against.
3. **Acceptability, separately from accuracy.** Whether teachers agree that a flag is correct and
   whether they would tolerate a tool showing it to them are different questions with different
   answers. Round 3 asks both.

The tension: good PD wants a safe, generous room; good measurement wants people's real first
instincts before the room has converged. The design handles this by taking every measurement
**before** the discussion that would contaminate it — solo card first, table talk second, always.
Hold that order even when a table is impatient.

---

## 2. Ground rules — say these before any scene goes up

Put them on a slide and leave them up.

> **1. We code turns, not teachers.** A flagged utterance is a moment, not a verdict about a person.
> Nobody in this room gets to conclude anything about the teacher in the transcript.
>
> **2. These are real classrooms.** The corpus is anonymised elementary maths lessons. The teachers
> consented to research, not to being an example of what not to do.
>
> **3. The machine has the same failure mode we do.** It also turns episodes into traits. Part of
> what we want from you is help catching it doing that.
>
> **4. Nothing here is about your own classroom** unless you choose to bring it.

Rule 3 is not a nicety. This project's own analysis found that in its cheapest configuration the
model converts episodes into *teacher* traits by exactly the grammar it was built to detect in
teachers — habitual adverb, personal subject, no time interval (`drafts/RQ2_temporal_language_findings.md`,
"Trait attribution, and a reflexive problem for deficit research"). Leading with that levels the room
fast: they are not being asked to judge colleagues, they are being asked to audit an instrument.

---

## 3. What the corpus actually shows — the honest numbers

Put these up early. They prevent the room concluding that teaching is a swamp.

| | |
|---|---|
| Transcripts scanned | 50 |
| **Transcripts with nothing flagged** | **23 (46%)** |
| Verified scenes | 37 |
| High confidence | **2** |
| Medium | 16 |
| Low | **19** |

Two framings to deliver with it:

- **Almost half the classrooms came back clean.** That is a finding, not a gap. The scan ran on
  every transcript and found nothing to flag in 23 of them.
- **The machine is mostly saying "maybe."** Nineteen of 37 are low confidence — the run's own
  spec defines that as *ambiguous between deficit and neutral, requires a charitable reading to
  count as deficit*. This is the honest hook for the room: **we are not here to check the machine's
  homework, we are here because the machine mostly shrugs and we need practitioners to say what the
  shrug means.**

### Category distribution, and a real hole

| Code | Category | Verified scenes |
|---|---|---|
| A | Fixed-ability framing | **0** |
| B | Deficit labeling / grouping | 4 |
| C | Problem located in student / home / background | 2 |
| D | Deficit attribution for behavior / motivation | 28 |
| E | Lowered expectations | 4 |
| F | Comparative deficit | 3 |
| G | Totalizing negation | 2 |

**Category A returned zero, and you should not paper over it.** Two A-tagged scenes exist in the
earlier `run_2026-07-12_170210`, but both fail verification against the current transcripts — one is
attributed to turn 536 of a 308-turn file, the other to turn 1551 of a 215-turn file. Those quotes do
not exist. They are excluded from this packet and should never be shown.

The packet covers A through the one *verified* utterance that reaches fixed-ability framing:
**S01**'s longer span, `"you gotta practice then maybe when you get smarter you can do this stuff on
your own."` The 2026-07-19 run trimmed the quote to the shorter `"you're just getting lazy"` and
dropped the A tag with it.

That trim is worth ninety seconds of the room's time, because it is the whole methodological problem
in miniature: **where you draw the span changes the code.** Same turn, same teacher, same moment —
one boundary produces a motivation complaint, another produces a claim about who is capable of being
smart. Ask the room where they would have cut it. Their answer is a design requirement for the tool.

Two honest disclosures to make when you show these numbers, if asked:

- Prevalence here is *not* an estimate of how much deficit language is in these classrooms. The
  detector is deliberately conservative — the spec says in as many words that a false positive is
  worse than a miss — so 37 is a floor, not a measurement.
- The earlier run flagged 68 scenes on the same corpus. Two passes, different totals. That
  instability is one more reason the human threshold in Round 1 matters.

---

## 4. The scenes, and why these ones

Thirteen scenes, one to two per category, all quote-verified. Full text, ±3 turns of context, LLM
categories, confidence and rationale are in `scene_bank.json`; `scene_bank.csv` is the same thing
flat for printing or sorting.

| ID | OBSID · turn | Cat | LLM conf | Role | The line |
|---|---|---|---|---|---|
| S01 | 2253 · 155 | D (+A) | high | Round 1 anchor | "you re just getting lazy and not pushing yourself" |
| S02 | 2199 · 168 | E | low | Round 1 split | "if… too difficult you don t have to do it" |
| S03 | 2204 · 227 | D, E | high | Round 1 benchmark | "those people that are not paying attention are the ones that won t be able to do it" |
| S04 | 2765 · 186 | D | medium | Reframe lab | "it is okay to be confused what s not okay is to be confused because you weren t paying attention" |
| S05 | 2571 · 124 | F, D | medium | Reframe lab | "there s 19 other kids aren t having a problem they re ready to learn math" |
| S06 | 2761 · 110 | C, G | medium | Reframe lab (hard) | "it s fascinating to me that my english speakers are not understanding me" |
| S07 | 2789 · 5 | C | low | Pairs with S06 | "i know some of you guys don t speak english that much but just stay with me" |
| S08 | 2561 · 163 | B | low | Reframe lab | "move next to student a so you can move off your weak side" |
| S09 | 2561 · 165 | B | low | Pairs with S08 | "you re still in the weak side and i don t want to put anybody else there" |
| S10 | 2592 · 616 | B, F | medium | Reserve | "some students who really can follow directions and others are not able to" |
| S11 | 2592 · 403 | D, F | medium | Reserve | "now you re acting like kindergarteners instead of fifth graders" |
| S12 | 1085 · 181 | D | medium | Reserve | "you guys are quitting on me you guys are quitting on me" |
| S13 | 47 · 61 | D, G | medium | Take-home | "without you having a breakdown cause that s what happens sometimes" |

### Justifications that matter

**S01 — 2253 t155 · the anchor.** One of only two high-confidence scenes in the corpus, and the only
verified utterance reaching fixed-ability framing. Put it first so the room calibrates on something
they will nearly all flag. It also carries the span problem in §3.

**S02 — 2199 t168 · the split.** The most valuable scene in the packet and the least dramatic. The
teacher is warm, mid-conference, praising a student's thinking two clauses earlier — and offers to
let children skip the hard part of the task. Expect a real split, and expect a substantial minority
not to flag it at all. **The disagreement is the measurement.** If the room flags this unanimously,
you have learned something surprising; if it splits, you have located exactly where the rubric's
category E outruns practitioner intuition.

**S03 — 2204 t227 · the benchmark.** The only scene in the corpus already coded by two trained
researchers *and* the LLM (`data/adjudication/obsid2204_1v2_llm_worksheet.csv`). All three flagged
it; all three disagreed about what it was:

| | categories | confidence |
|---|---|---|
| Coder 1 | B, D, E, F | medium |
| Coder 2 | A, E, F | high |
| LLM | D, E | high |

This lets you place workshop teachers on the same scale as your existing coders, and it gives you a
disarming reveal: three careful readers, three different answers, on the scene *everyone* agreed was
a flag. Use it to make the point that the hard part is not detection, it is description.

**S04 — 2765 t186 · the best reframe in the bank.** The teacher normalises confusion and then
takes it back inside the same sentence. Only one clause needs to change, so every table produces
something usable. Two facilitation details, both verified in the transcript:

- The surrounding turns are *good teaching*. At t188 the teacher explains why the harder visual
  method comes first — a genuinely strong answer to a student's "why can we not just do it the
  normal way."
- **Two turns after the flagged line, the teacher self-corrects**: at t188, "many of us aren't
  there yet, part of it was too fast." They relocate the problem into their own pacing without
  any prompting. Hold this back until after the tables have written their reframes, then reveal it.
  The move you are teaching is already in the room's repertoire; the transcript proves it.

**S05 — 2571 t124 · comparison as management.** "There's 19 other kids aren't having a problem,
they're ready to learn math." The compliant majority is made the measure of the rest, in public.
Reframes cleanly into a private redirect, so it is a fast win for a table that has stalled.

**S06 + S07 — the language pair.** Deliberately adjacent, same category C, opposite tone.

- S06 (2761 t110) is the hardest scene here. **In the same turn**, the teacher says
  *"that's what learning is all about, we love making mistakes in here because it means we're
  trying to learn"* — a textbook asset-based move — and, a few hundred words later,
  *"it's fascinating to me that my english speakers are not understanding me."* One breath,
  one turn, both moves.
- S07 (2789 t5) is the kind version of the same frame: an opening reassurance that names what some
  children lack.

Run them together and the question writes itself: does warmth rescue a deficit frame, or make it
harder to see? Note that S06 is the corpus's only scene where the teacher names a student
*population* while locating the failure inside it — handle the room carefully.

**S08 + S09 — 2561 t163/165 · the label.** "Your weak side," used twice in three turns, to mean a
*seat*. Not an insult, not said in anger — a classification that has hardened into furniture. Show
both turns or the scene does not work; a single use reads as a slip. This is the packet's test of
whether teachers notice categorisation as distinct from criticism, which is the distinction
category B turns on.

**S10–S12 — reserve.** For fast tables or a second session. S11 is the easy one if a group needs a
win before the hard scenes.

**S13 — take-home.** A whole-class prediction of failure stated as a recurring trait, spoken while
setting up a perfectly good task. Send it home with the coding card; collecting it later gives you
unhurried data to compare against the in-room rushed data.

---

## 5. The reframe protocol

Teach it once, in three minutes, before the lab. Keep it to three moves and one test.

### Notice — one question

> **"Would this sentence still be true tomorrow morning?"**

If yes, you have made a trait. "You're not listening" is about now. "You're lazy" is about always.
This single test operationalises the definition the whole project runs on — deficit framing locates
the problem inside the student as a *stable property* rather than in the task, the moment, or the
instruction.

### Reframe — three moves

1. **RELOCATE.** Move the problem out of the child and into something you control: the task, the
   pacing, the explanation, the moment.
2. **SPECIFY.** Replace the trait word with the thing you actually saw or heard.
3. **HOLD.** Keep the cognitive demand where it was. Support goes up; the maths does not come down.

Move 3 is the one teachers skip, and it is why S02 is in the packet. Category E is the trap where
kindness does the damage: the warmest thing in the room can be the sentence that takes the
mathematics away.

### Worked example — S04

| | |
|---|---|
| **Original** | "it is okay to be confused / what s not okay is to be confused because you weren t paying attention" |
| **Diagnose** | Clause 1 relocates — good. Clause 2 puts it back in the child and adds a moral term. Passes the tomorrow test: "not paying attention" is offered as the kind of person you are. |
| **Reframe** | "It is okay to be confused. This is a hard switch and I moved fast. Tell me where I lost you and I'll take that part again." |
| **Which moves** | RELOCATE (my pacing) + HOLD (we're going back to it, not around it) |
| **The reveal** | The teacher gets there themselves two turns later: "part of it was too fast." |

Print the protocol on the table tents. It is the one thing you want teachers to leave with.

---

## 6. Rundown — 120 minutes

| Time | Min | Block | Data collected |
|---|---|---|---|
| 0:00 | 8 | **Open** — consent, purpose, ground rules | consent forms |
| 0:08 | 10 | **Warm-up: one turn, two moves** (S06, facilitator-led) | — |
| 0:18 | 20 | **Round 1 — blind noticing** (S01, S02, S03) | Card A |
| 0:38 | 14 | **Round 2 — the rubric arrives** (same 3 scenes) | Card B |
| 0:52 | 8 | **Break** | — |
| 1:00 | 18 | **Round 3 — the machine speaks** (+ the two coders on S03) | Card C |
| 1:18 | 25 | **Reframe lab** (S04, S05, S08+S09, S06+S07) | Reframe cards |
| 1:43 | 14 | **Designing the tool** — three models, critique, vote | Design sheet + dots |
| 1:57 | 3 | **Close** | Exit slip |

### 0:00 · Open (8)

Consent first, before any transcript is visible. Ground rules slide. Name both purposes (§1) —
teachers give better data when they know what the data is for. Show the numbers in §3, including
the 23 clean transcripts and the two-high-confidence-out-of-37.

### 0:08 · Warm-up — one turn, two moves (10)

Facilitator-led, nobody codes anything. Put up S06's turn with both moves highlighted: the
mistakes-are-how-we-learn line and the english-speakers line, from the same turn.

Ask only: *"What do we do with a turn that contains both?"*

This block earns the rest of the session. It establishes that the unit is the turn, that good
teachers produce deficit language, and that the interesting question is never "is this teacher bad."
Do not let it run long — six minutes of talk, then move.

### 0:18 · Round 1 — blind noticing (20)

Hand out **Card A** and the three participant scene cards (S01, S02, S03). The cards show the
turn and its context. **No categories. No LLM verdict. No confidence.**

- **Solo, 8 min.** For each scene: flag or not · one line on why · how sure, 1–5.
  Silence. Collect nothing yet, but make clear the card is not to be changed later.
- **Table, 8 min.** Compare. Where did you differ? Table records its split — "3 of 4 flagged S02."
- **Whip-round, 4 min.** One sentence per table, on S02 only. Do not resolve it.

> **Facilitator discipline:** do not offer an opinion in this block. The moment you signal what you
> think is a flag, the measurement is gone.

### 0:38 · Round 2 — the rubric arrives (14)

Hand out A–G with the spec's definitions and its examples. Read the "what is NOT deficit-based"
list aloud too — neutral error description, factual formative assessment, productive struggle,
encouragement. It is as important as the categories.

**Card B, 6 min.** Re-code the same three scenes, now with categories available.

**Discussion, 8 min.** One question:

> *"Did the categories change whether you flagged, or only what you called it?"*

This is the project's own diagnostic — the adjudication worksheet asks exactly this ("Threshold or
definition?") when two coders disagree. If the rubric moves people's threshold, that is a finding
about the rubric. If it only supplies vocabulary, that is a finding too, and a more comfortable one.

### 0:52 · Break (8)

### 1:00 · Round 3 — the machine speaks (18)

Reveal the LLM's flag, categories, confidence and rationale for S01, S02, S03. Then reveal the two
researchers' codes for S03 (table in §4).

**Card C, 5 min**, per scene, two questions kept deliberately separate:

- Do you agree with the flag? (yes / no / partly, plus one line)
- **Would you want a tool to show you this one?** (yes / no)

**Discussion, 13 min.** In this order:

1. **S02 first**, because it will be the widest gap. If the room did not flag what the model flagged
   — or the reverse — sit in it.
2. **S03**: three careful readers, three different category sets, on a scene all three flagged.
   *Detection is easy; description is hard.*
3. **The confidence question**, with the real numbers: 19 of 37 flags are low confidence. *Should the
   tool show you the low-confidence ones at all?* Two live positions worth surfacing — showing them
   trains noticing but floods you; hiding them makes the tool look confident about things it isn't.

### 1:18 · Reframe lab (25)

Teach the protocol (§5) in 3 minutes with the S04 worked example — but stop before the reveal.

**Rounds, 18 min.** Each table takes scenes in this order, writing a reframe on a card for each:

1. S04 (warm-up, one clause)
2. S05 (public → private)
3. S08 + S09 (the label — harder, because there is nothing to soften; the word has to go)
4. S06 + S07 (the pair — only if time; assign to fast tables)

Rules for the reframe: it has to be a sentence you could actually say, in that moment, at that pace.
No paragraph-long reframes. No reframes that require having planned differently a week earlier.

**Reveal + close, 4 min.** Show that the S04 teacher self-corrects at t188. Then the closing question:

> *"What would have had to be true, in that thirty seconds, for the better sentence to be the one
> that came out?"*

Answers to that question are the actual design brief for the tool. Capture them on chart paper.

### 1:43 · Designing the tool (14)

Present three interaction models on one slide. Do not ask "what features do you want" — teachers
will politely invent a feature list. Make them react to concrete alternatives with a forced choice.

| | **A · The Detector** | **B · The Second Reader** | **C · The Rehearsal Room** |
|---|---|---|---|
| **What it does** | You give it a lesson recording or transcript; it returns flagged moments with categories and confidence | You bring one moment you're unsure about; it asks you questions and offers alternatives; you decide | It generates a plausible classroom moment; you respond; it reflects back where your response put the problem |
| **This is** | the current pipeline | a coaching conversation | flight simulation |
| **Buys you** | coverage — catches what you'd never notice | agency — it never looks unbidden | fluency — reps without a real child |
| **Costs you** | feels like evaluation | only catches what you already suspect | synthetic material |

**5 min table critique**, then **dot vote** — but vote on two axes separately, because they come apart:
*most useful to me* and *safest to have in my building*.

Then the three probes that actually determine adoption. Ask them explicitly; do not let the room
skip to features:

1. **Who is allowed to see the output?** Just you? Your coach? Your principal? Your evaluator?
   This single question usually decides whether a tool gets used at all.
2. **When would you want it — during planning, same-day, or the next morning?**
3. **What would make you stop using it after a week?**

Record answers verbatim on chart paper. Question 1 is the one to protect time for.

### 1:57 · Close (3)

Hand out S13 as a take-home with a spare Card A. Exit slip. Say what happens to the data and when
they will hear back.

---

## 7. Shorter cuts

**90 minutes** — drop Round 2 entirely (it is the most research-facing, least PD-facing block) and
fold "did the categories change anything" into Round 3 as a spoken question.

> Open 8 · Warm-up 8 · Round 1 blind 18 · Break 6 · Round 3 reveal 16 · Reframe lab 20 · Design 12 · Close 2

**60 minutes** — two scenes only, S02 and S04. Keep blind → reveal → reframe intact; it is the spine
and it does not survive being broken.

> Open 6 · Warm-up 6 · Blind code S02 + S04 12 · Reveal 12 · Reframe lab 14 · Design vote 8 · Close 2

At 60 minutes you get one clean measurement (S02 blind vs. LLM) and one reframe corpus entry per
table. That is still worth doing. What you lose is the rubric-effect data and the S03 benchmark
against your existing coders.

---

## 8. Data collection plan

### Instruments

| # | Instrument | Block | What it yields |
|---|---|---|---|
| A | Blind coding card | Round 1 | **Unprimed teacher threshold.** Flag rate per scene with no rubric, plus free-text reasons. The reasons are the prize: they show which criteria teachers actually use, which the A–G rubric may not name. |
| B | Rubric re-code card | Round 2 | **Rubric effect.** Threshold shift vs. vocabulary shift, on a fresh population — the worksheet's "threshold or definition?" question. |
| C | Reveal reaction card | Round 3 | **Agreement and acceptability, measured separately.** Human–LLM agreement per scene, plus whether teachers would tolerate seeing that flag. |
| D | Reframe cards | Reframe lab | **A teacher-authored reframe corpus.** The repo has none. This is the eval set for the reframing half of the tool. |
| E | Design sheet + dot votes | Design block | Model preference on two axes, plus the disclosure red lines. |
| F | Table audio | Throughout | Reasoning-in-progress. Native data for a discourse project; the card captures the verdict, the audio captures the argument. |
| G | Exit slip | Close | Four questions, no more. |

### Field structure — keep it compatible with the existing pipeline

The repo already has the machinery: `tools/coder/` writes
`data/human_coding/<obsid>/<coder>.json`, and `tools/coder/irr.py` computes the agreement stats.
Workshop teachers are just additional coders. Use fields that map onto it:

```
participant_id, scene_id, obsid, turn, round (A|B|C),
flagged (y/n), categories (A-G, round B onward), confidence (1-5),
reason_text, would_show_in_tool (y/n, round C only)
```

Reframes:

```
participant_id | table_id | scene_id | reframe_text | moves_used (relocate/specify/hold)
```

Two notes on reading the results, both already documented in `tools/coder/README.md` and worth
repeating here because workshop data will tempt you into the same error:

- **Do not report Cohen's κ alone.** Flagging is rare relative to teacher turns, so raw agreement is
  inflated and κ is pessimistic. Positive agreement (Dice on the flags themselves) is the honest
  headline; report κ, PABAK and category Jaccard alongside it.
- Workshop coding is on **pre-selected scenes**, not whole transcripts. The base rate is completely
  different from the coders' task. **Do not pool workshop cards with `data/human_coding/` runs into
  one agreement figure.** Compare per-scene rates instead.

### Consent and ethics

- Consent before the first transcript appears. Separate ticks for: written cards, audio, quotation
  in publication.
- **Slot in your own IRB-approved language.** I don't know this project's approval status; do not
  ship the packet without checking whether teacher-participant data collection is covered by the
  existing protocol or needs an amendment.
- Participants code anonymously (`P01`…). Table audio should be labelled by table, not by name.
- Say explicitly that nothing collected is about the participants' own teaching, and that no one's
  employer sees anything.
- The corpus teachers consented to research use, not to being teaching examples. Do not put OBSIDs
  on participant-facing cards beyond what identification requires, and do not photograph slides.

### A study this makes possible

The reframe corpus (Instrument D) sets up a natural third study in the same shape as Study 1:
generate LLM reframes for the same scenes, mix them with the teacher-authored ones, and have a
separate panel rate all of them blind for *usability in the moment*. Study 1 asked whether prompt
framing changes an LLM's analysis; this would ask whether an LLM's repair is one a teacher could
actually say at speed. Worth collecting the reframes carefully with that in mind — table
attribution, and legible handwriting.

---

## 9. Materials

**Print two separate sets, and keep them apart.** Generated by `py -3 workshop/make_cards.py`:

- `cards_participant.md` — turn + context only. No categories, no verdict, no confidence.
  **Round 1 is worthless if a participant sees the answer key.**
- `cards_facilitator.md` — same scenes plus LLM categories, confidence, rationale, and the
  facilitation notes.

Also needed:

- A–G rubric handout — copy the definitions *and* the "what is NOT deficit-based" list verbatim
  from `prompts/deficit_language_analysis_spec.txt`
- Cards A / B / C, reframe cards, design sheet, exit slip
- Table tent with the reframe protocol (§5)
- Chart paper for the design block; dot stickers in two colours
- Slides: ground rules, the §3 numbers, the S03 three-coder table, the three tool models
- Recorders, one per table

**If you want to run the coding tool live.** `tools/coder/app.py` binds to `127.0.0.1:5000`, so it
serves the facilitator's machine only. Serving a room means changing the bind to `0.0.0.0` — do
that only on a private network, since the app has no authentication and the corpus is
consent-restricted. **Paper is the recommended default**: it is faster for three scenes, it
guarantees the blind condition, and it removes the single point of failure. Transcribe into the
tool afterwards.

---

## 10. Risks

| Risk | Handling |
|---|---|
| Room converges on "this teacher is bad" | Ground rule 1, plus the S06 warm-up — an asset move and a deficit move in one turn. Redirect any person-level claim to the turn. |
| Teachers over-flag to please the researchers | Round 1 is solo and silent, before any signal from you. Say plainly that "not a flag" is a real and useful answer. |
| Teachers under-flag to protect colleagues | The §3 numbers help — 23 clean transcripts shows the instrument is not out for blood. So does naming the machine's own trait-talk problem. |
| A participant discloses something raw about their own classroom | Ground rule 4 makes it opt-in. Have a plan; do not put it on chart paper. |
| The room concludes AI should not do this at all | A legitimate finding, not a failure. Capture it. The design block's question 1 usually reveals it as a disclosure objection rather than a capability objection. |
| Reframe lab produces essays | State the constraint up front: one sentence, sayable at that moment, at that pace. |
| Time collapses in the design block | It always does. Protect question 1 ("who sees the output") — cut questions 2 and 3 first. |

---

## 11. Rebuilding

```
py -3 workshop/build_scene_bank.py    # verify + emit scene_bank.json / .csv
py -3 workshop/make_cards.py          # emit participant + facilitator card sets
```

The builder re-verifies every quote against `data/transcripts/by_obsid/<obsid>.csv` and writes
nothing if any fragment fails to land on its expected turn. To swap a scene, edit `PICKS` and
`VERIFY` in `build_scene_bank.py` and re-run — it will refuse the change rather than emit an
unverified quote.
