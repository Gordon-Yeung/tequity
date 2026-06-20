# Temporal Prompting in Educational Transcripts

A research project investigating how adding a **temporal dimension** to LLM prompts changes the quality and character of thematic analyses of classroom discourse.

## Research Question

Does prompting an LLM to track how teacher orientations *shift over time* — rather than treating the transcript as a static document — produce qualitatively different thematic analyses? How does this interact with the type of input provided (raw transcript vs. human-coded turn-level orientations)?

## Background

Each turn in a classroom transcript can be coded for the teacher's implicit orientation across three dimensions:

- **Orientation about Mathematics** — what the teacher's talk implies about the nature of math (e.g., procedural, problem-solving, multimodal)
- **Orientation about Students** — how the teacher positions students (e.g., as agents, as holders of prior knowledge, as a collective)
- **Orientation about Interaction** — the interactional structure the teacher constructs (e.g., collaborative, directive, time-structured)

Human coders applied these labels turn-by-turn. This project tests four conditions for automating or augmenting that thematic analysis using LLMs.

## Experimental Conditions

| ID | Name | Input | Prompt Style |
|----|------|-------|--------------|
| 01 | Static Codes | Human-coded orientations | Generic thematic analysis |
| 02 | Temporal Codes | Human-coded orientations | Temporal shift framing |
| 03 | Static Transcript | Raw classroom transcript | Generic thematic analysis |
| 04 | Temporal Transcript | Raw classroom transcript | Temporal shift framing |

**Temporal prompting** (conditions 02 and 04) explicitly asks the model to attend to how orientations evolve across the lesson rather than treating all turns as equivalent.

## Data

Two elementary classroom video transcripts serve as the primary cases:

| Video ID | Lesson Topic | Notes |
|----------|-------------|-------|
| 706 | Fractions / word problems | Grades 3–5, structured launch–work–share |
| 543 | Multiplication / scriptwriting | Grades 3–5, creative math storytelling |

## Folder Structure

```
temporal-prompting/
├── data/
│   ├── transcripts/          # Raw speaker-turn CSVs
│   │   ├── 706_original.csv
│   │   └── 543_original.csv
│   ├── coded/                # Human-coded turn-level orientations
│   │   ├── 706_coded.csv
│   │   └── 543_coded.csv
│   └── analysis/             # LLM outputs, one column per condition
│       ├── 706_analysis.csv
│       └── 543_analysis.csv
├── prompts/
│   ├── conditions.json                     # Condition registry
│   ├── condition_01_static_codes.txt
│   ├── condition_02_temporal_codes.txt
│   ├── condition_03_static_transcript.txt
│   └── condition_04_temporal_transcript.txt
├── scripts/
│   └── run_condition.py      # Pipeline script (Anthropic API)
├── CLAUDE.md                 # Technical guide for Claude Code
└── README.md
```

## Running a New Condition

### Prerequisites

```bash
pip install anthropic
export ANTHROPIC_API_KEY="your-key-here"
```

### Basic Usage

```bash
python scripts/run_condition.py --video_id 706 --condition 01
```

Arguments:

| Flag | Required | Description |
|------|----------|-------------|
| `--video_id` | Yes | `706` or `543` |
| `--condition` | Yes | `01`, `02`, `03`, or `04` |
| `--output_dir` | No | Where to save output (default: `data/analysis/`) |
| `--save` | No | Save output to a timestamped file |

### Adding a New Condition

1. Write your prompt to `prompts/condition_XX_<slug>.txt`
2. Add an entry to `prompts/conditions.json`:

```json
"05": {
  "name": "Your Condition Name",
  "description": "What distinguishes this condition.",
  "input_type": "coded",
  "prompt_file": "prompts/condition_05_your_slug.txt"
}
```

3. Run: `python scripts/run_condition.py --video_id 706 --condition 05`

`input_type` must be either `"coded"` (uses `data/coded/<video_id>_coded.csv`) or `"transcript"` (uses `data/transcripts/<video_id>_original.csv`).

## Analysis Files

The `data/analysis/` CSVs use a wide format where each condition occupies one column. Rows are thematic observations; the first few rows contain metadata (condition name, prompt used, researcher comments).

## Requirements

- Python 3.9+
- `anthropic` Python SDK (`pip install anthropic`)
- `ANTHROPIC_API_KEY` environment variable
