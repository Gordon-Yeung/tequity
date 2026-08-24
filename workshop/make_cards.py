"""Emit the two printable card sets from scene_bank.json.

They are generated separately on purpose. Round 1 of the workshop measures what
teachers flag with no rubric and no machine verdict in front of them, so the
participant set must not contain categories, confidence, or rationale. Building
both from one source keeps them in sync without ever putting the answer key on
the page a participant reads.
"""

import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
BANK = OUT / "scene_bank.json"

# Keys that must never reach the participant page.
WITHHELD = ("llm_categories", "llm_confidence", "llm_rationale", "packet_slot", "why_this_scene")


def context_block(scene, mark_span):
    """Render the +/-3 turn window, flagged turn arrowed."""
    lines = []
    for c in scene["context_excerpt"]:
        is_target = c["turn"] == scene["turn"]
        arrow = "**->**" if is_target else "   "
        speaker = c["speaker"] or "unknown"
        text = c["text"]
        if is_target and mark_span:
            quote = scene["deficit_quote"]
            if quote in text:
                text = text.replace(quote, f"**{quote}**", 1)
        lines.append(f"- {arrow} `t{c['turn']}` **{speaker}**: {text}")
    return "\n".join(lines)


def participant_cards(bank):
    out = [
        "# Scene cards — participant set",
        "",
        "One classroom moment per card. The arrow marks the turn to consider; the turns around",
        "it are there so you can see what was happening. These are anonymised elementary",
        "mathematics lessons, transcribed verbatim — punctuation and contractions are lost in",
        "transcription, so `you re` is *you're*.",
        "",
        "**We code turns, not teachers.** You are judging an utterance in a moment, not the",
        "person who said it.",
        "",
        "---",
        "",
    ]
    for s in bank:
        out += [
            f"## {s['scene_id']}",
            "",
            f"*Observation {s['obsid']}, turn {s['turn']}. Year {s['year']} of the study.*",
            "",
            context_block(s, mark_span=False),
            "",
            "> **Flag it?**  yes / no    **How sure?**  1 2 3 4 5",
            ">",
            "> In one line, what decided it for you:",
            ">",
            "> ______________________________________________",
            "",
            "---",
            "",
        ]
    return "\n".join(out)


def facilitator_cards(bank):
    out = [
        "# Scene cards — facilitator set",
        "",
        "**Do not print this for participants.** Contains the machine's verdict and the",
        "selection rationale; Round 1 is invalid if a participant sees either.",
        "",
        "The flagged span is bolded inside the turn. Every quote was verified against the",
        "source transcript at build time.",
        "",
        "---",
        "",
    ]
    for s in bank:
        cats = ", ".join(s["llm_categories"])
        out += [
            f"## {s['scene_id']} — OBSID {s['obsid']}, turn {s['turn']}",
            "",
            f"| | |",
            f"|---|---|",
            f"| Packet slot | {s['packet_slot']} |",
            f"| Role | {s['workshop_role']} |",
            f"| LLM categories | **{cats}** |",
            f"| LLM confidence | **{s['llm_confidence']}** |",
            f"| Teacher / year | {s['teacher_video_id']} / {s['year']} |",
            f"| Verified against | `{s['quote_verified_against']}` |",
            "",
            f"**Flagged span:** {s['deficit_quote']}",
            "",
            f"**LLM rationale:** {s['llm_rationale']}",
            "",
            f"**Why this scene:** {s['why_this_scene']}",
            "",
            "**Context:**",
            "",
            context_block(s, mark_span=True),
            "",
            "---",
            "",
        ]
    return "\n".join(out)


def main():
    if not BANK.exists():
        print("scene_bank.json missing - run build_scene_bank.py first", file=sys.stderr)
        return 1
    bank = json.loads(BANK.read_text(encoding="utf-8"))

    participant = participant_cards(bank)
    facilitator = facilitator_cards(bank)

    # Guard the blind condition: no withheld value may appear in the participant set.
    leaks = []
    for s in bank:
        for key in WITHHELD:
            val = s[key]
            for token in (val if isinstance(val, list) else [val]):
                token = str(token)
                if len(token) > 12 and token in participant:
                    leaks.append(f"{s['scene_id']}: {key} leaked into participant cards")
    if leaks:
        print("BLIND-CONDITION CHECK FAILED - nothing written:", file=sys.stderr)
        for leak in leaks:
            print("  " + leak, file=sys.stderr)
        return 1

    (OUT / "cards_participant.md").write_text(participant, encoding="utf-8")
    (OUT / "cards_facilitator.md").write_text(facilitator, encoding="utf-8")
    print(f"Wrote cards_participant.md and cards_facilitator.md ({len(bank)} scenes).")
    print("Blind-condition check passed: no categories, confidence, or rationale in the "
          "participant set.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
