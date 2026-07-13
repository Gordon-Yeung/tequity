# CLAUDE.md — Technical Guide for Claude Code

This file tells Claude Code how the project is structured so it can assist accurately.

## What This Project Does

Tests four prompting conditions for LLM-based thematic analysis of classroom transcripts. The core variable is whether the prompt asks the model to treat turn-level data as temporally ordered (tracking how teacher orientations *shift*) versus as a static document. See README.md for the research framing.

## Data Schemas

### `data/transcripts/<video_id>_original.csv`

Raw speaker-turn transcripts. Column names differ between the two cases:

| Video | Columns |
|-------|---------|
| 706 | `speaker`, `text`, `video_id` |
| 543 | `speaker`, `cleaned_text` |

The text column contains the verbatim (or lightly cleaned) teacher/student speech. `speaker` values include `teacher`, `student`, `multiple students`.

### `data/coded/<video_id>_coded.csv`

Human-coded turn-level orientations. Both files share this schema:

```
speaker, Utterance, Orientation about Mathematics, Orientation about Students, Orientation about Interaction
```

Episode headers appear as inline rows (e.g., `Episode 1: The launch,,,,`). Rows where the speaker is blank are researcher commentary inserted between episodes — treat them as metadata, not turns. Orientation columns are free-text; they may be empty for student turns.

### `data/analysis/<video_id>_analysis.csv`

Wide-format outputs. Each condition occupies one column. The first few rows are:
- Row 1: video/dataset label
- Row 2: condition names (`Static Codes`, `Temporal Codes`, etc.)
- Row 3: prompt text used
- Row 4: researcher comment field
- Row 5+: thematic content (themes and elaborations)

Do not treat this as a standard row-indexed table. When appending a new condition result, add a column to the right.

## Conditions Registry

`prompts/conditions.json` is the single source of truth for all conditions:

```json
{
  "01": {
    "name": "Static Codes",
    "description": "...",
    "input_type": "coded",       // "coded" | "transcript"
    "prompt_file": "prompts/condition_01_static_codes.txt"
  },
  ...
}
```

`input_type` controls which data file the pipeline script loads:
- `"coded"` → `data/coded/<video_id>_coded.csv`
- `"transcript"` → `data/transcripts/<video_id>_original.csv`

## Pipeline Script

`scripts/run_condition.py` handles the full condition run:

```
python scripts/run_condition.py --video_id 706 --condition 01 [--save] [--output_dir data/analysis/]
```

It reads `conditions.json`, loads the right input file, appends the prompt, calls `claude-opus-4-8` with adaptive thinking and streaming, and prints the response. Pass `--save` to write the output to a timestamped `.txt` file.

## Adding a New Condition

1. Write the prompt to `prompts/condition_XX_<slug>.txt`
2. Register it in `prompts/conditions.json` (see schema above)
3. Run the pipeline script — no code changes needed

## Naming Conventions

| Artifact | Pattern | Example |
|----------|---------|---------|
| Prompt file | `condition_NN_<slug>.txt` | `condition_05_temporal_coded_v2.txt` |
| Condition key | Two-digit zero-padded string | `"05"` |
| Transcript | `<video_id>_original.csv` | `706_original.csv` |
| Coded file | `<video_id>_coded.csv` | `543_coded.csv` |
| Analysis | `<video_id>_analysis.csv` | `706_analysis.csv` |

## API Usage

The pipeline uses the Anthropic Python SDK with:
- Model: `claude-opus-4-8`
- Thinking: `{"type": "adaptive"}` (model decides depth)
- Streaming: yes — transcripts can be large; streaming prevents timeout

The `ANTHROPIC_API_KEY` environment variable must be set. The script does not hard-code the key.

## What NOT to Change Without Researcher Sign-Off

- Column names in coded CSVs (downstream analysis depends on exact headers)
- The `input_type` values in `conditions.json` (must stay `"coded"` or `"transcript"`)
- The episode/commentary row structure in coded CSVs

## How to Work with Claude Code

### Collaboration Style

- **Be direct.** Tell me what you need; I'll figure out the best path.
- **Ask for cleanup explicitly.** Don't assume I'll remove test files or failed runs—ask and I will.
- **Prefer outputs in multiple formats.** If a report is useful, offer it as `.md`, `.txt`, `.csv`, or `.json` depending on the use case.
- **Verify rigorously.** For data processing tasks, I should always verify outputs (e.g., quote matching against source), not just trust the analysis.
- **Use Python for data processing.** I write deterministic scripts when handling files, transcripts, or structured data—not ad-hoc one-off commands.

### Technical Preferences

- **Handle CSV parsing robustly.** Expect UTF-8 BOM, quoted column names, multiple schema variants—normalize them.
- **Use Claude Opus for heavy lifting.** Complex language analysis (deficit framing, semantic understanding) uses Opus; I (Haiku) orchestrate.
- **Python 3.13+.** Use the stable Python 3.13 release; avoid alpha versions (3.14-alpha has SDK incompatibilities).
- **Environment variables via `.env`.** Store secrets in `.env` (already in .gitignore); I'll read them at runtime.
- **Timestamp output directories.** When a process can be re-run, use timestamped folders to avoid overwriting prior runs.

### Reporting & Cleanup

- **Generate reader-friendly reports.** Complex JSON outputs should have a human-readable summary (Markdown preferred).
- **Remove temporary files.** Test scripts, failed runs, and cache directories should be cleaned up after debugging.
- **Preserve the audit trail in code.** Comments in scripts should explain *why*, not *what*; good variable names handle the latter.

### Scope & Boundaries

- **Research-grade work.** This project is academic research—prioritize correctness and transparency over speed.
- **No destructive shortcuts.** Don't use `--no-verify` or similar flags to bypass safety checks; fix the underlying issue instead.
- **Check with you on big decisions.** Before deleting large datasets, changing schemas, or refactoring pipelines, ask first.
