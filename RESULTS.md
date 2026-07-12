# Results Organization Guide

This document explains how to generate and view analysis results using the structured pipeline.

## Quick Start

### 1. Generate Results for a Video

Run all 4 conditions for a video:

```bash
python scripts/run_all_conditions.py --video_id 706
```

This will:
- Run conditions 01, 02, 03, 04 sequentially
- Save outputs to `data/results/706/` 
- Create a manifest file: `data/results/706/manifest.json`

### 2. View Results

View a summary of all conditions run for a video:
```bash
python scripts/view_results.py --video_id 706
```

View output from a specific condition:
```bash
python scripts/view_results.py --video_id 706 --condition 01
```

## Directory Structure

```
data/
├── results/
│   ├── 706/
│   │   ├── manifest.json
│   │   ├── 706_condition01_20260624_143022.txt
│   │   ├── 706_condition02_20260624_143145.txt
│   │   ├── 706_condition03_20260624_143301.txt
│   │   └── 706_condition04_20260624_143402.txt
│   └── 543/
│       ├── manifest.json
│       ├── 543_condition01_*.txt
│       └── ...
├── transcripts/
│   ├── 706_original.csv
│   └── 543_original.csv
├── coded/
│   ├── 706_coded.csv
│   └── 543_coded.csv
└── analysis/
    ├── 706_analysis.csv  (original web-based results)
    └── 543_analysis.csv
```

## Understanding Conditions

The 4 conditions form a 2×2 matrix:

| Condition | Data Type | Prompt Type | File | Purpose |
|-----------|-----------|-------------|------|---------|
| **01** | Coded | Static | `condition_01_static_codes.txt` | Baseline: human codes, generic prompt |
| **02** | Coded | Temporal | `condition_02_temporal_codes.txt` | Test temporal framing with human codes |
| **03** | Transcript | Static | `condition_03_static_transcript.txt` | Raw transcript, generic prompt |
| **04** | Transcript | Temporal | `condition_04_temporal_transcript.txt` | Raw transcript, temporal framing |

## Comparing Results

The manifest file (`data/results/706/manifest.json`) tracks:
- Condition ID and name
- Data source (coded vs transcript)
- Prompt file used
- Output file location
- Run timestamp
- Status (success/failed)

Use this to cross-reference outputs and identify differences between:
- **Static vs Temporal**: Compare conditions 01↔02 (same data, different prompt)
- **Coded vs Transcript**: Compare conditions 01↔03 (different data, static prompt)
- **Full matrix**: Compare all 4 to isolate effects

## Example Workflow

```bash
# Generate results for video 706
python scripts/run_all_conditions.py --video_id 706

# View summary of what was generated
python scripts/view_results.py --video_id 706

# Look at a specific condition's output
python scripts/view_results.py --video_id 706 --condition 02

# Do the same for video 543
python scripts/run_all_conditions.py --video_id 543
```

Then you can compare the raw outputs side-by-side to see how the model's analysis changes based on:
1. **Input data type** (human-coded orientations vs raw transcript)
2. **Prompt framing** (static analysis vs temporal shift tracking)

## Environment Setup

Before running, ensure:
1. Python 3.8+ is installed
2. Dependencies are installed: `pip install anthropic`
3. `ANTHROPIC_API_KEY` environment variable is set:
   ```bash
   # Windows PowerShell
   $env:ANTHROPIC_API_KEY = "your-key-here"
   
   # macOS/Linux
   export ANTHROPIC_API_KEY="your-key-here"
   ```

## Reproducibility

Each run is timestamped and logged in the manifest. If you want to archive and compare multiple runs:
- Different timestamps = different API calls
- Same condition + video = may have slight variation due to model sampling
- The manifest tracks which files correspond to which experimental parameters
