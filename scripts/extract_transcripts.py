#!/usr/bin/env python3
"""
Extract transcripts from the NCTE CSV file and save as individual CSVs.
Keeps only speaker and cleaned_text columns.
"""
import pandas as pd
from pathlib import Path

# File paths
input_csv = Path(r"c:\Users\Gordon Yeung\Downloads\ncte_single_utterances.csv")
output_dir = Path(r"C:\Users\Gordon Yeung\Documents\GitHub\temporal-prompting\data\transcripts")

# Ensure output directory exists
output_dir.mkdir(parents=True, exist_ok=True)

# Read the input CSV
print("Reading input CSV...")
df = pd.read_csv(input_csv)

# Get unique video IDs in order
unique_ids = sorted(df['video_id'].unique())
print(f"Found {len(unique_ids)} unique video IDs")

# Limit to 50 videos
videos_to_process = unique_ids[:50]
print(f"Processing first {len(videos_to_process)} videos...")

# Process each video
for i, video_id in enumerate(videos_to_process, 1):
    video_data = df[df['video_id'] == video_id]

    # Keep only speaker and cleaned_text columns
    transcript = video_data[['speaker', 'cleaned_text']].copy()
    transcript.columns = ['speaker', 'cleaned_text']

    # Save to file
    output_file = output_dir / f"{video_id}_original.csv"
    transcript.to_csv(output_file, index=False)

    print(f"{i:2d}. Saved {video_id} ({len(transcript)} turns) → {output_file.name}")

print(f"\nDone! Saved {len(videos_to_process)} transcript files.")
