"""Build the facilitator scene bank for the deficit-reframing teacher workshop.

Selection is curated (see PICKS below) but everything else is derived: quotes are
re-verified against the frozen OBSID transcripts, context comes from the run's own
scene records, and teacher/year metadata is joined from the observation index.

Re-verification is not redundant with the pipeline's own check. The 2026-07-12 run
contains scenes whose quotes do not exist in the current transcripts at all (one is
attributed to turn 536 of a 308-turn file), so anything carried into a room full of
teachers is checked again here, against the file the workshop will actually display.
"""

import csv
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUN = REPO / "data" / "deficit_scenes_obsid" / "run_2026-07-19_153121"
SCENES = RUN / "all_scenes.json"
OBSID_DIR = REPO / "data" / "transcripts" / "by_obsid"
INDEX = REPO / "data" / "observation_index.csv"
OUT = Path(__file__).resolve().parent

# (obsid, turn, packet_slot, workshop_role, why_this_scene)
# packet_slot = the A-G category this scene carries in the packet.
PICKS = [
    ("2253", "155", "D+A", "round1-anchor",
     "The one near-certain flag in the set, and the only verified utterance in the corpus that "
     "reaches fixed-ability framing: 'when you get smarter' treats intelligence as something the "
     "child does not yet have. Calibrates the room's scale before anything subtle."),
    ("2199", "168", "E", "round1-split",
     "Warm, well-meant, and it removes the mathematics. Expect the room to split, and expect a "
     "substantial minority not to flag it at all. That disagreement is the most valuable single "
     "measurement of the day."),
    ("2204", "227", "D+E", "round1-benchmark",
     "The only scene already coded by two trained researchers AND the LLM "
     "(data/adjudication/obsid2204_1v2_llm_worksheet.csv), so workshop teachers can be placed on "
     "the same scale as the existing coders. All three parties flagged it and all three disagreed "
     "on category: coder1 B,D,E,F / coder2 A,E,F / llm D,E."),
    ("2765", "186", "D", "reframe-lab",
     "A growth-mindset move the teacher undercuts inside the same sentence. The surrounding turns "
     "are strong teaching (t188 is genuinely good), which is the point: this is what deficit "
     "language looks like in a classroom nobody would call deficit-oriented. Highest-yield reframe "
     "in the bank because only one clause has to change."),
    ("2571", "124", "F+D", "reframe-lab",
     "Public comparison used as a management tool - the compliant majority is made into the measure "
     "of the rest. Reframes cleanly into a private redirect, so tables produce a usable alternative "
     "fast."),
    ("2761", "110", "C+G", "reframe-lab-hard",
     "The hardest scene in the bank and the only one where the teacher names a student population "
     "('my english speakers') while locating the failure in them. Sits inside a turn that also "
     "contains real warmth and real press. Use it to test whether the reframe protocol survives a "
     "genuinely mixed moment."),
    ("2789", "5", "C", "reframe-lab-pair",
     "Deliberate pair with 2761: same category, opposite tone. Kind, protective, and still opens the "
     "lesson by naming what some children lack. Forces the question of whether warmth rescues a "
     "deficit frame."),
    ("2561", "163", "B", "reframe-lab",
     "A label, not an insult - a seat becomes a deficit category ('your weak side'). Tests whether "
     "teachers notice classification as distinct from criticism."),
    ("2561", "165", "B", "reframe-lab-pair",
     "The second use, two turns later, is what makes it a label rather than a slip. Show both turns "
     "or the scene does not work."),
    ("2592", "616", "B+F", "reserve",
     "Grouping by a capability the teacher treats as fixed ('others are not able to follow "
     "directions'), voiced as genuine puzzlement. Good reserve scene for a fast table."),
    ("2592", "403", "D+F", "reserve",
     "Demeaning age comparison, very short, very recognisable. Useful as a quick warm-up if a group "
     "needs an easy win before the hard scenes."),
    ("1085", "181", "D", "reserve",
     "'You guys are quitting on me' - effort attribution in six words, with the teacher's own "
     "disappointment audible. Good for discussing frustration as the source of deficit talk."),
    ("47", "61", "D+G", "take-home",
     "Whole-class anticipated failure stated as a recurring trait ('that's what happens sometimes'), "
     "spoken while setting up a good task. Take-home scene for teachers to code at their own pace."),
]

# Fragments used only to re-verify each pick lands on the expected turn and nowhere else.
VERIFY = {
    ("2253", "155"): ["you re just getting lazy and not pushing yourself",
                      "then maybe when you get smarter you can do this stuff on your own"],
    ("2199", "168"): ["if splitting up the fraction you re finding might be a little too difficult "
                      "you don t have to do it"],
    ("2204", "227"): ["those people that are not paying attention are the ones that won t be able to do it"],
    ("2765", "186"): ["it is okay to be confused what s not okay is to be confused because you weren t "
                      "paying attention"],
    ("2571", "124"): ["there s 19 other kids aren t having a problem they re ready to learn math"],
    ("2761", "110"): ["it s fascinating to me that my english speakers are not understanding me"],
    ("2789", "5"): ["now i know some of you guys don t speak english that much but just stay with me"],
    ("2561", "163"): ["so you can move off your weak side"],
    ("2561", "165"): ["you re still in the weak side and i don t want to put anybody else there"],
    ("2592", "616"): ["i don t understand why i have some students who really can follow directions and "
                      "others are not able to follow directions"],
    ("2592", "403"): ["now you re acting like kindergarteners instead of fifth graders not acceptable"],
    ("1085", "181"): ["you guys are quitting on me you guys are quitting on me"],
    ("47", "61"): ["without you having a breakdown cause that s what happens sometimes"],
}


def norm(s):
    return re.sub(r"\s+", " ", s.lower()).strip()


def load_transcript(path):
    """Turn-indexed rows. Handles the UTF-8 BOM and both column schemas."""
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for i, r in enumerate(csv.DictReader(f), 1):
            text = r.get("text") or r.get("cleaned_text") or ""
            rows.append({"turn": i, "speaker": (r.get("speaker") or "").strip(), "text": text})
    return rows


def load_index():
    meta = {}
    with open(INDEX, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            meta[r["obsid"]] = {
                "teacher_video_id": r["video_id"],
                "year": r["year"],
                "n_teacher_turns": r["n_teacher_turns"],
            }
    return meta


def main():
    scenes = json.loads(SCENES.read_text(encoding="utf-8"))
    by_key = {(s["obsid"], s["deficit_span"]["turns"]): s for s in scenes}
    meta = load_index()

    bank, failures = [], []
    for obsid, turn, slot, role, why in PICKS:
        scene = by_key.get((obsid, turn))
        if scene is None:
            failures.append(f"{obsid} t{turn}: not present in {SCENES.name}")
            continue

        rows = load_transcript(OBSID_DIR / f"{obsid}.csv")
        turn_row = next((r for r in rows if r["turn"] == int(turn)), None)
        if turn_row is None:
            failures.append(f"{obsid} t{turn}: turn absent from transcript")
            continue

        for frag in VERIFY[(obsid, turn)]:
            hits = [r["turn"] for r in rows if norm(frag) in norm(r["text"])]
            if hits != [int(turn)]:
                failures.append(f"{obsid} t{turn}: fragment matched {hits or 'nothing'} - {frag[:50]!r}")

        bank.append({
            "scene_id": f"S{len(bank) + 1:02d}",
            "obsid": obsid,
            "turn": int(turn),
            "teacher_video_id": meta.get(obsid, {}).get("teacher_video_id"),
            "year": meta.get(obsid, {}).get("year"),
            "packet_slot": slot,
            "workshop_role": role,
            "why_this_scene": why,
            "llm_categories": scene["categories"],
            "llm_confidence": scene["confidence"],
            "llm_rationale": scene["rationale"],
            "deficit_quote": scene["deficit_span"]["verbatim_quote"],
            "full_turn_text": turn_row["text"],
            "context_excerpt": scene["context_excerpt"],
            "quote_verified_against": f"data/transcripts/by_obsid/{obsid}.csv",
        })

    if failures:
        print("VERIFICATION FAILED - nothing written:", file=sys.stderr)
        for f in failures:
            print("  " + f, file=sys.stderr)
        return 1

    (OUT / "scene_bank.json").write_text(
        json.dumps(bank, indent=2, ensure_ascii=False), encoding="utf-8")

    with open(OUT / "scene_bank.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scene_id", "obsid", "turn", "teacher_video_id", "year", "packet_slot",
                    "workshop_role", "llm_categories", "llm_confidence", "deficit_quote",
                    "llm_rationale", "why_this_scene"])
        for s in bank:
            w.writerow([s["scene_id"], s["obsid"], s["turn"], s["teacher_video_id"], s["year"],
                        s["packet_slot"], s["workshop_role"], ",".join(s["llm_categories"]),
                        s["llm_confidence"], s["deficit_quote"], s["llm_rationale"],
                        s["why_this_scene"]])

    print(f"{len(bank)} scenes, all quotes verified against by_obsid transcripts.")
    for s in bank:
        print(f"  {s['scene_id']}  obsid {s['obsid']:>4} t{s['turn']:<4} "
              f"{s['packet_slot']:<5} {s['llm_confidence']:<6} {s['workshop_role']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
