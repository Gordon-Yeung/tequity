# Extract transcripts from NCTE CSV and save as individual files
$inputCsv = "c:\Users\Gordon Yeung\Downloads\ncte_single_utterances.csv"
$outputDir = "C:\Users\Gordon Yeung\Documents\GitHub\temporal-prompting\data\transcripts"

# Ensure output directory exists
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
}

# Import the CSV
Write-Host "Reading input CSV..." -ForegroundColor Green
$data = Import-Csv $inputCsv

# Get unique video IDs in sorted order
$uniqueIds = $data | Select-Object -ExpandProperty video_id -Unique | Sort-Object
Write-Host "Found $($uniqueIds.Count) unique video IDs" -ForegroundColor Green

# Limit to 50
$idsToProcess = $uniqueIds | Select-Object -First 50
Write-Host "Processing first $($idsToProcess.Count) videos..." -ForegroundColor Green
Write-Host ""

$count = 0
foreach ($videoId in $idsToProcess) {
    $count++

    # Filter data for this video
    $videoData = $data | Where-Object { $_.video_id -eq $videoId }

    # Create output with only speaker and cleaned_text
    $transcript = $videoData | Select-Object @{Name='speaker';Expression={$_.speaker}}, @{Name='cleaned_text';Expression={$_.cleaned_text}}

    # Save to CSV
    $outputFile = Join-Path $outputDir "$($videoId)_original.csv"
    $transcript | Export-Csv -Path $outputFile -NoTypeInformation -Encoding UTF8

    Write-Host ("{0:D2}. Saved {1} ({2} turns) → {3}" -f $count, $videoId, $transcript.Count, (Split-Path -Leaf $outputFile))
}

Write-Host ""
Write-Host "Done! Saved $count transcript files." -ForegroundColor Green
