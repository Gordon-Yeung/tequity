# DEPRECATED (2026-07-17)
#
# This PowerShell version grouped rows by `video_id`, which concatenated multiple
# distinct lessons (OBSIDs) into a single transcript file. Use the corrected
# Python extractor instead, which keys by OBSID:
#
#     py -3 scripts/extract_transcripts.py
#
# See scripts/extract_transcripts.py for the full explanation.

Write-Host "Deprecated. Run: py -3 scripts/extract_transcripts.py" -ForegroundColor Yellow
exit 1
