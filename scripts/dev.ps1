param(
    [Parameter(Position = 0)]
    [string]$Task,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$TaskArgs = @()
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
try {
    [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
    $OutputEncoding = [System.Text.UTF8Encoding]::new()
}
catch {
    Write-Host "Warning: Could not set PowerShell UTF-8 output encoding."
}
try {
    chcp.com 65001 > $null
}
catch {
    Write-Host "Warning: Could not switch terminal code page to UTF-8."
}

$script:ResolvedGitExe = $null
$script:ResolvedGitSource = "missing"
$script:ResolvedFfmpegExe = $null
$script:ResolvedFfmpegSource = "missing"

function Show-Usage {
    Write-Host "Usage: ./scripts/dev.ps1 <task> [args]"
    Write-Host ""
    Write-Host "Tasks:"
    Write-Host "  doctor"
    Write-Host "  test"
    Write-Host "  deploy-modal"
    Write-Host "  deploy-modal-utf8"
    Write-Host "  smoke-local-fake"
    Write-Host "  smoke-modal-fake"
    Write-Host "  smoke-yourmt3"
    Write-Host "  logs-modal"
    Write-Host "  preflight-yourmt3"
    Write-Host "  make-clip <audio-path> [seconds]"
    Write-Host "  analyze-structure <audio-path> (legacy alias for analyze-structure-local)"
    Write-Host "  analyze-structure-local <audio-path>"
    Write-Host "  analyze-structure-modal <audio-path>"
    Write-Host "  analyze-structure-modal-dense <audio-path>"
    Write-Host "  audio-analysis-diagnostics"
    Write-Host "  segment-audio <audio-path> [target-window-seconds] [strategy]"
    Write-Host "  segment-audio-structure <audio-path> [target-window-seconds]"
    Write-Host "  segment-audio-structure-dense <audio-path> [target-window-seconds]"
    Write-Host "  segment-audio-structure-tuned <audio-path> <target-window-seconds> <boundary-threshold>"
    Write-Host "  sweep-audio-structure-dense <audio-path> [target-window-seconds]"
    Write-Host "  inspect-segments <manifest-path>"
    Write-Host "  diagnose-boundaries <manifest-path>"
    Write-Host "  review-segments <manifest-path>"
    Write-Host "  inspect-latest-segments [source-folder]"
    Write-Host "  inspect-analysis <analysis-json-path>"
    Write-Host "  compare-analyses <analysis-source-folder>"
    Write-Host "  compare-segmentations <segments-source-folder>"
    Write-Host "  transcribe-windows <manifest-path> [max-windows]"
    Write-Host "  benchmark-segments <manifest-path>"
    Write-Host "  stitch-midi-dry-run <manifest-path>"
    Write-Host "  stitch-midi <manifest-path>"
    Write-Host "  validate-merged-midi <merged-midi-path>"
    Write-Host "  ingest-performance <audio-path>"
    Write-Host "  process-performance <performance-manifest> [max-windows] [--allow-partial-stitch]"
    Write-Host "  batch-performances <inbox-folder> [max-performances] [max-windows]"
    Write-Host "  list-performance-runs <performance-manifest>"
    Write-Host "  set-active-performance-run <performance-manifest> <segments-manifest>"
    Write-Host "  extract-rhythm-features <performance-manifest>"
    Write-Host "  extract-meter-time-features <performance-manifest>"
    Write-Host "  extract-harmony-features <performance-manifest>"
    Write-Host "  extract-pitch-harmony-features <performance-manifest>"
    Write-Host "  validate-pitch-harmony-features <performance-manifest>"
    Write-Host "  tag-performance-features <performance-manifest>"
    Write-Host "  build-ai-training-records <performance-manifest>"
    Write-Host "  extract-feature-pack <performance-manifest>"
    Write-Host "  validate-feature-pack <performance-manifest>"
    Write-Host "  validate-meter-time-features <performance-manifest>"
    Write-Host "  check-model-sources"
    Write-Host "  check-external-analyzers"
    Write-Host "  run-external-witnesses <performance-manifest> [providers]"
    Write-Host "  compare-model-witnesses <performance-manifest>"
    Write-Host "  build-model-consensus <performance-manifest>"
    Write-Host "  run-external-analyzers <performance-manifest> [providers]"
    Write-Host "  compare-external-features <performance-manifest>"
    Write-Host "  build-feature-consensus <performance-manifest>"
    Write-Host "  evaluate-rhythm-lexicon"
    Write-Host "  compute-transcription-reliability <performance-manifest>"
    Write-Host "  evaluate-training-quality-gates <performance-manifest>"
    Write-Host "  audit-training-data <performance-manifest>"
    Write-Host "  export-training-dataset-splits <performance-manifest>"
    Write-Host "  validate-training-export <export-folder>"
    Write-Host "  summarize-training-exports [exports-root]"
    Write-Host "  batch-trusted-exports <inbox-folder> [max-performances] [max-windows]"
    Write-Host "  validate-batch-report <batch-report-json>"
    Write-Host "  classify-audio-asset <performance-manifest>"
    Write-Host "  classify-content-regions <performance-manifest>"
    Write-Host "  apply-analysis-routing <performance-manifest>"
    Write-Host "  evaluate-label-upgrades <performance-manifest>"
    Write-Host "  diagnose-content-routing <performance-manifest>"
    Write-Host "  route-performance-analysis <performance-manifest>"
    Write-Host "  transcribe-yourmt3 <audio-path>"
    Write-Host "  clip-and-transcribe-yourmt3 <audio-path> [seconds]"
    Write-Host "  debug-args [any args]"
    Write-Host "  benchmark-track <track-folder>"
    Write-Host "  validate-latest"
    Write-Host "  validate-track <track-folder>"
    Write-Host "  commit-checkpoint [commit message]"
}

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string[]]$Command
    )
    $commandText = $Command -join " "
    Write-Host ""
    Write-Host "==> $Label"
    Write-Host "    $commandText"
    if ($Command.Length -eq 1) { & $Command[0] } else { & $Command[0] $Command[1..($Command.Length - 1)] }
    if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $commandText" }
}

function Invoke-CommandCapture {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string[]]$Command
    )
    $commandText = $Command -join " "
    Write-Host ""
    Write-Host "==> $Label"
    Write-Host "    $commandText"
    $previousErrorPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $output = if ($Command.Length -eq 1) { & $Command[0] 2>&1 } else { & $Command[0] $Command[1..($Command.Length - 1)] 2>&1 }
    $ErrorActionPreference = $previousErrorPreference
    $exitCode = $LASTEXITCODE
    foreach ($line in $output) { Write-Host $line }
    if ($exitCode -ne 0) { throw "Command failed ($exitCode): $commandText" }
    return @($output | ForEach-Object { "$_" })
}

function Invoke-YourMt3TranscriptionWorkflow {
    param([Parameter(Mandatory = $true)][string]$AudioPath)

    Ensure-FfmpegPath
    $env:MUSIC_BRAIN_PROVIDER = "yourmt3"
    $env:MUSIC_BRAIN_BACKEND = "modal"
    $env:MUSIC_BRAIN_MT3_MODEL = "yourmt3"
    $env:MUSIC_BRAIN_MODAL_GPU = "T4"
    Show-MusicBrainEnv

    $submissionOutput = Invoke-CommandCapture -Label "Running yourmt3/modal transcription" -Command @(
        "python", "submit_track.py", $AudioPath, "--print-track-dir"
    )
    $trackDirLine = $submissionOutput | Where-Object { $_ -like "TRACK_DIR=*" } | Select-Object -Last 1
    $jobReportLine = $submissionOutput | Where-Object { $_ -like "JOB_REPORT=*" } | Select-Object -Last 1
    $midiPathLine = $submissionOutput | Where-Object { $_ -like "MIDI_PATH=*" } | Select-Object -Last 1
    if (-not $trackDirLine) { throw "Could not find TRACK_DIR in submit output." }

    $trackDir = $trackDirLine.Substring("TRACK_DIR=".Length)
    $jobReportPath = if ($jobReportLine) { $jobReportLine.Substring("JOB_REPORT=".Length) } else { Join-Path $trackDir "analysis\job_report.json" }
    $midiPath = if ($midiPathLine) { $midiPathLine.Substring("MIDI_PATH=".Length) } else { Join-Path $trackDir "midi\full_mix.mid" }

    $validationOutput = Invoke-CommandCapture -Label "Validating transcribed track" -Command @(
        "python", "scripts/validate_track.py", $trackDir
    )
    $validationResultLine = $validationOutput | Where-Object { $_ -like "Validation result:*" } | Select-Object -Last 1
    $validationResult = if ($validationResultLine) { $validationResultLine } else { "Validation result: UNKNOWN" }

    $benchmarkOutput = Invoke-CommandCapture -Label "Benchmarking transcribed track" -Command @(
        "python", "scripts/benchmark_track.py", $trackDir
    )

    Write-Host ""
    Write-Host "==> Final summary"
    Write-Host "  track folder: $trackDir"
    Write-Host "  job_report path: $jobReportPath"
    Write-Host "  MIDI path: $midiPath"
    Write-Host "  validation result: $validationResult"
    Write-Host "  benchmark summary:"
    foreach ($line in $benchmarkOutput) {
        if (-not [string]::IsNullOrWhiteSpace($line)) { Write-Host "    $line" }
    }
}

function Get-TaskArg {
    param([Parameter(Mandatory = $true)][int]$Index)
    if ($TaskArgs.Count -le $Index) { return $null }
    return $TaskArgs[$Index]
}

function Get-TaskArgOrThrow {
    param(
        [Parameter(Mandatory = $true)][int]$Index,
        [Parameter(Mandatory = $true)][string]$Usage
    )
    $value = Get-TaskArg -Index $Index
    if ([string]::IsNullOrWhiteSpace($value)) { throw $Usage }
    return $value
}

function Find-ToolPathFromCommand {
    param([Parameter(Mandatory = $true)][string]$Name)
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -eq $cmd) { return $null }
    return $cmd.Path
}

function Find-GitPath {
    $onPath = Find-ToolPathFromCommand "git"
    if ($onPath) { return @{ Path = $onPath; Source = "PATH" } }
    $candidates = @(
        "C:\Program Files\Git\cmd\git.exe",
        "C:\Program Files\Git\bin\git.exe",
        "C:\Users\izzyo\AppData\Local\Programs\Git\cmd\git.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) { return @{ Path = $candidate; Source = "fallback: $candidate" } }
    }
    return @{ Path = $null; Source = "missing" }
}

function Find-FfmpegPath {
    $onPath = Find-ToolPathFromCommand "ffmpeg"
    if ($onPath) { return @{ Path = $onPath; Source = "PATH" } }

    $globRoot = "C:\Users\izzyo\AppData\Local\Microsoft\WinGet\Packages"
    if (Test-Path $globRoot) {
        $wingetMatches = @(Get-ChildItem -Path $globRoot -Filter "ffmpeg.exe" -Recurse -File -ErrorAction SilentlyContinue |
                Where-Object { $_.FullName -like "*Gyan.FFmpeg_*" -and $_.FullName -like "*\ffmpeg-*\bin\ffmpeg.exe" } |
                Sort-Object FullName -Descending)
        if ($wingetMatches.Count -gt 0) {
            return @{ Path = $wingetMatches[0].FullName; Source = "fallback: WinGet package path" }
        }
    }

    $candidates = @(
        "C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        "C:\ffmpeg\bin\ffmpeg.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) { return @{ Path = $candidate; Source = "fallback: $candidate" } }
    }
    return @{ Path = $null; Source = "missing" }
}

function Resolve-ToolPaths {
    $gitInfo = Find-GitPath
    $script:ResolvedGitExe = $gitInfo.Path
    $script:ResolvedGitSource = $gitInfo.Source

    $ffmpegInfo = Find-FfmpegPath
    $script:ResolvedFfmpegExe = $ffmpegInfo.Path
    $script:ResolvedFfmpegSource = $ffmpegInfo.Source

    if ($script:ResolvedFfmpegExe) {
        $ffmpegDir = Split-Path -Parent $script:ResolvedFfmpegExe
        if ($env:PATH -notlike "*$ffmpegDir*") { $env:PATH = "$ffmpegDir;$env:PATH" }
    }
}

function Show-ToolMissingMessage {
    param([Parameter(Mandatory = $true)][string]$ToolName)
    Write-Host "${ToolName}: Tool not found in this shell. Restart Cursor or open a new terminal after installing."
}

function Show-ShellDiagnostics {
    Write-Host "PowerShell process: $((Get-Process -Id $PID).Path)"
    Write-Host "PowerShell version: $($PSVersionTable.PSVersion)"
    Write-Host "PYTHONUTF8=$env:PYTHONUTF8"
    Write-Host "PYTHONIOENCODING=$env:PYTHONIOENCODING"
    try {
        Write-Host "Console output encoding: $([Console]::OutputEncoding.WebName)"
    }
    catch {
        Write-Host "Console output encoding: unavailable"
    }

    $pythonPath = Find-ToolPathFromCommand "python"
    if ($pythonPath) { Write-Host "python path: $pythonPath"; Invoke-Step -Label "Python version" -Command @("python", "--version") } else { Show-ToolMissingMessage "python" }
    if ($script:ResolvedGitExe) { Write-Host "git path: $script:ResolvedGitExe"; Write-Host "git source: $script:ResolvedGitSource"; Invoke-Step -Label "Git version" -Command @($script:ResolvedGitExe, "--version") } else { Show-ToolMissingMessage "git" }
    if ($script:ResolvedFfmpegExe) { Write-Host "ffmpeg path: $script:ResolvedFfmpegExe"; Write-Host "ffmpeg source: $script:ResolvedFfmpegSource"; Invoke-Step -Label "ffmpeg version" -Command @($script:ResolvedFfmpegExe, "-version") } else { Show-ToolMissingMessage "ffmpeg" }
}

function Show-MusicBrainEnv {
    Write-Host "MUSIC_BRAIN_PROVIDER=$env:MUSIC_BRAIN_PROVIDER"
    Write-Host "MUSIC_BRAIN_BACKEND=$env:MUSIC_BRAIN_BACKEND"
    Write-Host "MUSIC_BRAIN_MT3_MODEL=$env:MUSIC_BRAIN_MT3_MODEL"
    Write-Host "MUSIC_BRAIN_MODAL_GPU=$env:MUSIC_BRAIN_MODAL_GPU"
}

function Ensure-FfmpegPath {
    if ($script:ResolvedFfmpegExe) {
        $ffmpegDir = Split-Path -Parent $script:ResolvedFfmpegExe
        if ($env:PATH -notlike "*$ffmpegDir*") { $env:PATH = "$ffmpegDir;$env:PATH" }
    }
}

function Run-Doctor {
    $failedChecks = @()
    Write-Host ""
    Write-Host "==> Doctor checks"
    Write-Host "Project root: $(Get-Location)"

    $pythonPath = Find-ToolPathFromCommand "python"
    if (-not $pythonPath) { Show-ToolMissingMessage "python"; $failedChecks += "python" }
    else {
        Write-Host "python path: $pythonPath"
        Invoke-Step -Label "Python version" -Command @("python", "--version")
        Invoke-Step -Label "Pytest import check" -Command @("python", "-c", "import pytest; print('pytest import ok')")
        Invoke-Step -Label "Modal module check" -Command @("python", "-m", "modal", "--help")
    }

    if (-not $script:ResolvedGitExe) { Show-ToolMissingMessage "git"; $failedChecks += "git" }
    else {
        Write-Host "git path: $script:ResolvedGitExe"
        Write-Host "git source: $script:ResolvedGitSource"
        Invoke-Step -Label "Git version" -Command @($script:ResolvedGitExe, "--version")
    }

    if (-not $script:ResolvedFfmpegExe) { Show-ToolMissingMessage "ffmpeg"; $failedChecks += "ffmpeg" }
    else {
        Write-Host "ffmpeg path: $script:ResolvedFfmpegExe"
        Write-Host "ffmpeg source: $script:ResolvedFfmpegSource"
        Invoke-Step -Label "ffmpeg version" -Command @($script:ResolvedFfmpegExe, "-version")
    }

    $hasEnvAuth = -not [string]::IsNullOrWhiteSpace($env:MODAL_TOKEN_ID) -and -not [string]::IsNullOrWhiteSpace($env:MODAL_TOKEN_SECRET)
    $modalConfigPath = Join-Path $HOME ".modal.toml"
    $hasFileAuth = Test-Path $modalConfigPath
    if ($hasEnvAuth -or $hasFileAuth) {
        Write-Host "Modal auth config: detected"
        if ($hasFileAuth) { Write-Host "Modal auth file: $modalConfigPath" }
    }
    else {
        Write-Host "Modal auth config: missing. Run 'python -m modal setup'."
        $failedChecks += "modal-auth"
    }

    if ($failedChecks.Count -gt 0) { throw "Doctor failed checks: $($failedChecks -join ', ')" }
}

if ([string]::IsNullOrWhiteSpace($Task)) { Show-Usage; exit 1 }

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptPath "..")
Set-Location $projectRoot
Write-Host "Project root: $projectRoot"

Resolve-ToolPaths
Show-ShellDiagnostics

switch ($Task) {
    "doctor" { Run-Doctor }
    "test" { Invoke-Step -Label "Running tests" -Command @("python", "-m", "pytest", "-q") }
    "deploy-modal" { Invoke-Step -Label "Deploying Modal app" -Command @("python", "-m", "modal", "deploy", "modal_app.py") }
    "deploy-modal-utf8" { Invoke-Step -Label "Deploying Modal app (UTF-8 mode)" -Command @("python", "-m", "modal", "deploy", "modal_app.py") }
    "smoke-local-fake" {
        Ensure-FfmpegPath
        $env:MUSIC_BRAIN_PROVIDER = "fake"
        $env:MUSIC_BRAIN_BACKEND = "local_fake"
        Show-MusicBrainEnv
        Invoke-Step -Label "Preflight (local fake)" -Command @("python", "submit_track.py", "--preflight")
        Invoke-Step -Label "Generating test audio" -Command @("python", "scripts/create_test_audio.py")
        Invoke-Step -Label "Running local fake smoke transcription" -Command @("python", "submit_track.py", "samples/test_tone.wav")
    }
    "smoke-modal-fake" {
        Ensure-FfmpegPath
        $env:MUSIC_BRAIN_PROVIDER = "fake"
        $env:MUSIC_BRAIN_BACKEND = "modal_fake"
        Show-MusicBrainEnv
        Invoke-Step -Label "Preflight (modal fake)" -Command @("python", "submit_track.py", "--preflight")
        Invoke-Step -Label "Generating test audio" -Command @("python", "scripts/create_test_audio.py")
        Invoke-Step -Label "Running modal fake smoke transcription" -Command @("python", "submit_track.py", "samples/test_tone.wav")
    }
    "smoke-yourmt3" {
        Ensure-FfmpegPath
        $env:MUSIC_BRAIN_PROVIDER = "yourmt3"
        $env:MUSIC_BRAIN_BACKEND = "modal"
        $env:MUSIC_BRAIN_MT3_MODEL = "yourmt3"
        $env:MUSIC_BRAIN_MODAL_GPU = "T4"
        Show-MusicBrainEnv
        Invoke-Step -Label "Preflight (yourmt3/modal)" -Command @("python", "submit_track.py", "--preflight")
        Invoke-Step -Label "Generating test audio" -Command @("python", "scripts/create_test_audio.py")
        Invoke-Step -Label "Running yourmt3/modal smoke transcription" -Command @("python", "submit_track.py", "samples/test_tone.wav")
    }
    "logs-modal" { Invoke-Step -Label "Streaming Modal logs" -Command @("python", "-m", "modal", "app", "logs", "music-brain-v2", "-f") }
    "preflight-yourmt3" {
        Ensure-FfmpegPath
        $env:MUSIC_BRAIN_PROVIDER = "yourmt3"
        $env:MUSIC_BRAIN_BACKEND = "modal"
        $env:MUSIC_BRAIN_MT3_MODEL = "yourmt3"
        $env:MUSIC_BRAIN_MODAL_GPU = "T4"
        Show-MusicBrainEnv
        Invoke-Step -Label "Running preflight for yourmt3/modal" -Command @("python", "submit_track.py", "--preflight")
    }
    "make-clip" {
        Ensure-FfmpegPath
        $audioPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd make-clip <audio-path> [seconds]"
        $seconds = Get-TaskArg -Index 1
        $clipCommand = @("python", "scripts/make_clip.py", $audioPath)
        if (-not [string]::IsNullOrWhiteSpace($seconds)) {
            $clipCommand += @("--seconds", $seconds)
        }
        Invoke-Step -Label "Creating short clip" -Command $clipCommand
    }
    "analyze-structure" {
        Ensure-FfmpegPath
        $audioPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd analyze-structure <audio-path>"
        $analysisOutput = Invoke-CommandCapture -Label "Analyzing pre-MIDI audio structure" -Command @(
            "python", "scripts/analyze_audio_structure.py", $audioPath, "--backend", "local_light"
        )
        $analysisLine = $analysisOutput | Where-Object { $_ -like "ANALYSIS_PATH=*" } | Select-Object -Last 1
        if ($analysisLine) {
            Write-Host "ANALYSIS_PATH=$($analysisLine.Substring('ANALYSIS_PATH='.Length))"
        }
    }
    "analyze-structure-local" {
        Ensure-FfmpegPath
        $audioPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd analyze-structure-local <audio-path>"
        $analysisOutput = Invoke-CommandCapture -Label "Analyzing pre-MIDI audio structure (local_light)" -Command @(
            "python", "scripts/analyze_audio_structure.py", $audioPath, "--backend", "local_light"
        )
        $analysisLine = $analysisOutput | Where-Object { $_ -like "ANALYSIS_PATH=*" } | Select-Object -Last 1
        if ($analysisLine) {
            Write-Host "ANALYSIS_PATH=$($analysisLine.Substring('ANALYSIS_PATH='.Length))"
        }
    }
    "analyze-structure-modal" {
        Ensure-FfmpegPath
        $audioPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd analyze-structure-modal <audio-path>"
        $analysisOutput = Invoke-CommandCapture -Label "Analyzing pre-MIDI audio structure (modal_librosa)" -Command @(
            "python", "scripts/analyze_audio_structure.py", $audioPath, "--backend", "modal_librosa"
        )
        $analysisLine = $analysisOutput | Where-Object { $_ -like "ANALYSIS_PATH=*" } | Select-Object -Last 1
        if ($analysisLine) {
            Write-Host "ANALYSIS_PATH=$($analysisLine.Substring('ANALYSIS_PATH='.Length))"
        }
    }
    "analyze-structure-modal-dense" {
        Ensure-FfmpegPath
        $audioPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd analyze-structure-modal-dense <audio-path>"
        $analysisOutput = Invoke-CommandCapture -Label "Analyzing pre-MIDI audio structure (modal_librosa dense)" -Command @(
            "python", "scripts/analyze_audio_structure.py", $audioPath, "--backend", "modal_librosa",
            "--candidate-density", "dense",
            "--peak-pick-threshold", "0.40",
            "--min-boundary-distance-seconds", "8.0",
            "--max-candidates", "24"
        )
        $analysisLine = $analysisOutput | Where-Object { $_ -like "ANALYSIS_PATH=*" } | Select-Object -Last 1
        if ($analysisLine) {
            Write-Host "ANALYSIS_PATH=$($analysisLine.Substring('ANALYSIS_PATH='.Length))"
        }
    }
    "audio-analysis-diagnostics" {
        Ensure-FfmpegPath
        Invoke-Step -Label "Audio analysis diagnostics (local + Modal lookup)" -Command @(
            "python", "scripts/analyze_audio_structure.py", "--diagnostics"
        )
    }
    "segment-audio" {
        Ensure-FfmpegPath
        $audioPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd segment-audio <audio-path> [target-window-seconds] [strategy]"
        $targetWindow = Get-TaskArg -Index 1
        $strategy = Get-TaskArg -Index 2
        $segmentCommand = @(
            "python",
            "scripts/segment_audio.py",
            $audioPath,
            "--strategy",
            $(if (-not [string]::IsNullOrWhiteSpace($strategy)) { $strategy } else { "hybrid" }),
            "--target-window-seconds"
        )
        if (-not [string]::IsNullOrWhiteSpace($targetWindow)) {
            $segmentCommand += $targetWindow
        }
        else {
            $segmentCommand += "60"
        }
        $segmentCommand += @("--max-window-seconds", "90", "--context-seconds", "5")
        $segmentOutput = Invoke-CommandCapture -Label "Creating segment manifest and windows" -Command $segmentCommand
        $manifestLine = $segmentOutput | Where-Object { $_ -like "MANIFEST_PATH=*" } | Select-Object -Last 1
        if ($manifestLine) {
            Write-Host "MANIFEST_PATH=$($manifestLine.Substring('MANIFEST_PATH='.Length))"
        }
    }
    "segment-audio-structure" {
        Ensure-FfmpegPath
        $audioPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd segment-audio-structure <audio-path> [target-window-seconds]"
        $targetWindow = Get-TaskArg -Index 1

        $segmentCommand = @(
            "python",
            "scripts/segment_audio.py",
            $audioPath,
            "--strategy",
            "audio_structure",
            "--target-window-seconds",
            $(if (-not [string]::IsNullOrWhiteSpace($targetWindow)) { $targetWindow } else { "60" }),
            "--max-window-seconds",
            "90",
            "--context-seconds",
            "5"
        )
        $segmentOutput = Invoke-CommandCapture -Label "Creating audio-structure segment manifest and windows" -Command $segmentCommand
        $manifestLine = $segmentOutput | Where-Object { $_ -like "MANIFEST_PATH=*" } | Select-Object -Last 1
        if ($manifestLine) {
            Write-Host "MANIFEST_PATH=$($manifestLine.Substring('MANIFEST_PATH='.Length))"
        }
    }
    "segment-audio-structure-dense" {
        Ensure-FfmpegPath
        $audioPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd segment-audio-structure-dense <audio-path> [target-window-seconds]"
        $targetWindow = Get-TaskArg -Index 1
        $targetValue = if (-not [string]::IsNullOrWhiteSpace($targetWindow)) { $targetWindow } else { "60" }
        $sourceStem = [System.IO.Path]::GetFileNameWithoutExtension($audioPath)
        $safeSource = (($sourceStem -replace "[^a-zA-Z0-9._-]+", "_").Trim("_"))
        if ([string]::IsNullOrWhiteSpace($safeSource)) { $safeSource = "performance" }
        $latestAnalysisPointer = Join-Path (Join-Path "samples\analysis" $safeSource) "latest_analysis.txt"
        $reuseDense = $false
        if (Test-Path $latestAnalysisPointer) {
            $latestPath = (Get-Content -Path $latestAnalysisPointer -Raw).Trim()
            if (-not [string]::IsNullOrWhiteSpace($latestPath) -and (Test-Path $latestPath)) {
                try {
                    $analysisJson = Get-Content -Path $latestPath -Raw | ConvertFrom-Json
                    if ($analysisJson -and $analysisJson.diagnostics -and $analysisJson.diagnostics.candidate_density -eq "dense") {
                        Write-Host "Reusing latest dense analysis: $latestPath"
                        Write-Host "ANALYSIS_PATH=$latestPath"
                        $reuseDense = $true
                    }
                }
                catch {
                    $reuseDense = $false
                }
            }
        }
        if (-not $reuseDense) {
            $analysisOutput = Invoke-CommandCapture -Label "Analyzing pre-MIDI audio structure (modal_librosa dense)" -Command @(
                "python", "scripts/analyze_audio_structure.py", $audioPath, "--backend", "modal_librosa",
                "--candidate-density", "dense",
                "--peak-pick-threshold", "0.40",
                "--min-boundary-distance-seconds", "8.0",
                "--max-candidates", "24"
            )
            $analysisLine = $analysisOutput | Where-Object { $_ -like "ANALYSIS_PATH=*" } | Select-Object -Last 1
            if ($analysisLine) {
                Write-Host "ANALYSIS_PATH=$($analysisLine.Substring('ANALYSIS_PATH='.Length))"
            }
        }
        $segmentOutput = Invoke-CommandCapture -Label "Creating audio-structure segment manifest/windows from dense analysis" -Command @(
            "python", "scripts/segment_audio.py", $audioPath, "--strategy", "audio_structure",
            "--target-window-seconds", $targetValue, "--max-window-seconds", "90", "--context-seconds", "5"
        )
        $manifestLine = $segmentOutput | Where-Object { $_ -like "MANIFEST_PATH=*" } | Select-Object -Last 1
        if ($manifestLine) {
            Write-Host "MANIFEST_PATH=$($manifestLine.Substring('MANIFEST_PATH='.Length))"
        }
    }
    "segment-audio-structure-tuned" {
        Ensure-FfmpegPath
        $audioPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd segment-audio-structure-tuned <audio-path> <target-window-seconds> <boundary-threshold>"
        $targetWindow = Get-TaskArgOrThrow -Index 1 -Usage "Usage: scripts\dev.cmd segment-audio-structure-tuned <audio-path> <target-window-seconds> <boundary-threshold>"
        $boundaryThreshold = Get-TaskArgOrThrow -Index 2 -Usage "Usage: scripts\dev.cmd segment-audio-structure-tuned <audio-path> <target-window-seconds> <boundary-threshold>"

        $sourceStem = [System.IO.Path]::GetFileNameWithoutExtension($audioPath)
        $safeSource = (($sourceStem -replace "[^a-zA-Z0-9._-]+", "_").Trim("_"))
        if ([string]::IsNullOrWhiteSpace($safeSource)) { $safeSource = "performance" }
        $latestAnalysisPointer = Join-Path (Join-Path "samples\analysis" $safeSource) "latest_analysis.txt"
        $analysisPath = $null
        if (Test-Path $latestAnalysisPointer) {
            $candidatePath = (Get-Content -Path $latestAnalysisPointer -Raw).Trim()
            if (-not [string]::IsNullOrWhiteSpace($candidatePath) -and (Test-Path $candidatePath)) {
                $analysisPath = $candidatePath
            }
        }
        if (-not [string]::IsNullOrWhiteSpace($analysisPath)) {
            Write-Host "Reusing existing modal_librosa analysis: $analysisPath"
        }
        else {
            $analysisOutput = Invoke-CommandCapture -Label "Analyzing pre-MIDI audio structure (modal_librosa)" -Command @(
                "python", "scripts/analyze_audio_structure.py", $audioPath, "--backend", "modal_librosa"
            )
            $analysisLine = $analysisOutput | Where-Object { $_ -like "ANALYSIS_PATH=*" } | Select-Object -Last 1
            if ($analysisLine) {
                Write-Host "ANALYSIS_PATH=$($analysisLine.Substring('ANALYSIS_PATH='.Length))"
            }
        }

        $segmentCommand = @(
            "python",
            "scripts/segment_audio.py",
            $audioPath,
            "--strategy",
            "audio_structure",
            "--target-window-seconds",
            $targetWindow,
            "--max-window-seconds",
            "90",
            "--context-seconds",
            "5",
            "--boundary-threshold",
            $boundaryThreshold
        )
        $segmentOutput = Invoke-CommandCapture -Label "Creating tuned audio-structure segment manifest and windows" -Command $segmentCommand
        $manifestLine = $segmentOutput | Where-Object { $_ -like "MANIFEST_PATH=*" } | Select-Object -Last 1
        if ($manifestLine) {
            Write-Host "MANIFEST_PATH=$($manifestLine.Substring('MANIFEST_PATH='.Length))"
        }
    }
    "sweep-audio-structure-dense" {
        Ensure-FfmpegPath
        $audioPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd sweep-audio-structure-dense <audio-path> [target-window-seconds]"
        $targetWindow = Get-TaskArg -Index 1
        $targetValue = if (-not [string]::IsNullOrWhiteSpace($targetWindow)) { $targetWindow } else { "60" }
        $densities = @("normal", "dense")
        $distances = @("6", "8")
        $maxCandidatesSet = @("16", "24")
        foreach ($density in $densities) {
            foreach ($distance in $distances) {
                foreach ($maxCandidatesValue in $maxCandidatesSet) {
                    Invoke-Step -Label "Sweeping analysis density=$density distance=$distance max_candidates=$maxCandidatesValue" -Command @(
                        "python", "scripts/analyze_audio_structure.py", $audioPath, "--backend", "modal_librosa",
                        "--candidate-density", $density,
                        "--peak-pick-threshold", "0.40",
                        "--min-boundary-distance-seconds", $distance,
                        "--max-candidates", $maxCandidatesValue
                    )
                    Invoke-Step -Label "Sweeping segmentation density=$density distance=$distance max_candidates=$maxCandidatesValue" -Command @(
                        "python", "scripts/segment_audio.py", $audioPath, "--strategy", "audio_structure",
                        "--target-window-seconds", $targetValue, "--max-window-seconds", "90", "--context-seconds", "5"
                    )
                }
            }
        }
    }
    "inspect-segments" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd inspect-segments <manifest-path>"
        Invoke-Step -Label "Inspecting segment manifest" -Command @("python", "scripts/inspect_segments.py", $manifestPath)
    }
    "diagnose-boundaries" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd diagnose-boundaries <manifest-path>"
        Invoke-Step -Label "Diagnosing boundary candidates" -Command @("python", "scripts/diagnose_boundaries.py", $manifestPath)
    }
    "review-segments" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd review-segments <manifest-path>"
        $reviewOutput = Invoke-CommandCapture -Label "Generating segmentation review report" -Command @(
            "python", "scripts/review_segments.py", $manifestPath
        )
        $reportLine = $reviewOutput | Where-Object { $_ -like "REVIEW_REPORT_PATH=*" } | Select-Object -Last 1
        if ($reportLine) {
            Write-Host "REVIEW_REPORT_PATH=$($reportLine.Substring('REVIEW_REPORT_PATH='.Length))"
        }
    }
    "inspect-latest-segments" {
        $sourceFolder = Get-TaskArg -Index 0
        $latestFile = $null
        if (-not [string]::IsNullOrWhiteSpace($sourceFolder)) {
            $candidate = Join-Path $sourceFolder "latest_manifest.txt"
            if (-not (Test-Path $candidate)) {
                $candidate = Join-Path (Join-Path "samples\segments" $sourceFolder) "latest_manifest.txt"
            }
            if (Test-Path $candidate) { $latestFile = Get-Item $candidate }
        }
        if ($null -eq $latestFile) {
            $latestFile = Get-ChildItem -Path "samples\segments" -Filter "latest_manifest.txt" -Recurse -File |
                Sort-Object LastWriteTime -Descending |
                Select-Object -First 1
        }
        if ($null -eq $latestFile) { throw "No latest_manifest.txt found under samples/segments." }
        $manifestPath = (Get-Content -Path $latestFile.FullName -Raw).Trim()
        if ([string]::IsNullOrWhiteSpace($manifestPath)) { throw "latest_manifest.txt is empty: $($latestFile.FullName)" }
        Write-Host "Using latest manifest pointer: $($latestFile.FullName)"
        Invoke-Step -Label "Inspecting latest segment manifest" -Command @("python", "scripts/inspect_segments.py", $manifestPath)
    }
    "inspect-analysis" {
        $analysisPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd inspect-analysis <analysis-json-path>"
        Invoke-Step -Label "Inspecting analysis report" -Command @("python", "scripts/inspect_analysis.py", $analysisPath)
    }
    "compare-analyses" {
        $analysisRoot = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd compare-analyses <analysis-source-folder>"
        Invoke-Step -Label "Comparing analysis runs" -Command @("python", "scripts/compare_analyses.py", $analysisRoot)
    }
    "compare-segmentations" {
        $segmentsRoot = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd compare-segmentations <segments-source-folder>"
        Invoke-Step -Label "Comparing segmentation runs" -Command @("python", "scripts/compare_segmentations.py", $segmentsRoot)
    }
    "transcribe-windows" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd transcribe-windows <manifest-path> [max-windows]"
        $maxWindows = Get-TaskArg -Index 1
        $command = @("python", "scripts/transcribe_windows.py", $manifestPath)
        if (-not [string]::IsNullOrWhiteSpace($maxWindows)) {
            $command += @("--max-windows", $maxWindows)
        }
        Invoke-Step -Label "Transcribing windows from manifest" -Command $command
    }
    "benchmark-segments" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd benchmark-segments <manifest-path>"
        Invoke-Step -Label "Benchmarking segment manifest" -Command @("python", "scripts/benchmark_segments.py", $manifestPath)
    }
    "stitch-midi-dry-run" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd stitch-midi-dry-run <manifest-path>"
        Invoke-Step -Label "MIDI stitching dry-run" -Command @("python", "scripts/stitch_midi.py", $manifestPath, "--dry-run")
    }
    "stitch-midi" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd stitch-midi <manifest-path>"
        Invoke-Step -Label "MIDI stitching (core-trim merge)" -Command @("python", "scripts/stitch_midi.py", $manifestPath)
    }
    "validate-merged-midi" {
        $midiPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd validate-merged-midi <merged-midi-path>"
        Invoke-Step -Label "Validating merged MIDI" -Command @("python", "scripts/validate_merged_midi.py", $midiPath)
    }
    "ingest-performance" {
        Ensure-FfmpegPath
        $audioPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd ingest-performance <audio-path>"
        Invoke-Step -Label "Ingesting performance into library manifest" -Command @("python", "scripts/ingest_performance.py", $audioPath)
    }
    "process-performance" {
        Ensure-FfmpegPath
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd process-performance <performance-manifest> [max-windows] [--allow-partial-stitch]"
        $maxWindows = Get-TaskArg -Index 1
        $allowPartial = Get-TaskArg -Index 2
        $command = @("python", "scripts/process_performance.py", $manifestPath)
        if (-not [string]::IsNullOrWhiteSpace($maxWindows)) {
            $command += @("--max-windows", $maxWindows)
        }
        if ($allowPartial -eq "--allow-partial-stitch") {
            $command += @("--allow-partial-stitch")
        }
        Invoke-Step -Label "Processing performance through staged pipeline" -Command $command
    }
    "batch-performances" {
        Ensure-FfmpegPath
        $inboxFolder = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd batch-performances <inbox-folder> [max-performances] [max-windows]"
        $maxPerformances = Get-TaskArg -Index 1
        $maxWindows = Get-TaskArg -Index 2
        $command = @("python", "scripts/batch_performances.py", $inboxFolder)
        if (-not [string]::IsNullOrWhiteSpace($maxPerformances)) {
            $command += @("--max-performances", $maxPerformances)
        }
        if (-not [string]::IsNullOrWhiteSpace($maxWindows)) {
            $command += @("--max-windows", $maxWindows)
        }
        Invoke-Step -Label "Batch ingest/process performances" -Command $command
    }
    "list-performance-runs" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd list-performance-runs <performance-manifest>"
        Invoke-Step -Label "Listing canonical and historical performance runs" -Command @(
            "python", "scripts/list_performance_runs.py", $manifestPath
        )
    }
    "set-active-performance-run" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd set-active-performance-run <performance-manifest> <segments-manifest>"
        $segmentsManifest = Get-TaskArgOrThrow -Index 1 -Usage "Usage: scripts\dev.cmd set-active-performance-run <performance-manifest> <segments-manifest>"
        Invoke-Step -Label "Setting canonical active performance run" -Command @(
            "python", "scripts/set_active_performance_run.py", $manifestPath, $segmentsManifest
        )
    }
    "extract-rhythm-features" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd extract-rhythm-features <performance-manifest>"
        Invoke-Step -Label "Extracting rhythm feature records" -Command @(
            "python", "scripts/extract_rhythm_features.py", $manifestPath
        )
    }
    "extract-meter-time-features" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd extract-meter-time-features <performance-manifest>"
        Invoke-Step -Label "Extracting hierarchical meter/time features" -Command @(
            "python", "scripts/extract_meter_time_features.py", $manifestPath
        )
    }
    "extract-harmony-features" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd extract-harmony-features <performance-manifest>"
        Invoke-Step -Label "Extracting harmony feature records" -Command @(
            "python", "scripts/extract_harmony_features.py", $manifestPath
        )
    }
    "extract-pitch-harmony-features" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd extract-pitch-harmony-features <performance-manifest>"
        Invoke-Step -Label "Extracting pitch/harmony intelligence records" -Command @(
            "python", "scripts/extract_pitch_harmony_features.py", $manifestPath
        )
    }
    "validate-pitch-harmony-features" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd validate-pitch-harmony-features <performance-manifest>"
        Invoke-Step -Label "Validating pitch/harmony intelligence outputs" -Command @(
            "python", "scripts/validate_pitch_harmony_features.py", $manifestPath
        )
    }
    "tag-performance-features" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd tag-performance-features <performance-manifest>"
        Invoke-Step -Label "Tagging performance feature records" -Command @(
            "python", "scripts/tag_performance_features.py", $manifestPath
        )
    }
    "build-ai-training-records" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd build-ai-training-records <performance-manifest>"
        Invoke-Step -Label "Building AI training records" -Command @(
            "python", "scripts/build_ai_training_records.py", $manifestPath
        )
    }
    "extract-feature-pack" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd extract-feature-pack <performance-manifest>"
        Invoke-Step -Label "Extracting full feature pack" -Command @(
            "python", "scripts/extract_feature_pack.py", $manifestPath
        )
    }
    "validate-feature-pack" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd validate-feature-pack <performance-manifest>"
        Invoke-Step -Label "Validating feature pack outputs" -Command @(
            "python", "scripts/validate_feature_pack.py", $manifestPath
        )
    }
    "validate-meter-time-features" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd validate-meter-time-features <performance-manifest>"
        Invoke-Step -Label "Validating meter/time feature outputs" -Command @(
            "python", "scripts/validate_meter_time_features.py", $manifestPath
        )
    }
    "check-external-analyzers" {
        Invoke-Step -Label "Checking external analyzer availability" -Command @(
            "python", "scripts/check_external_analyzers.py"
        )
    }
    "check-model-sources" {
        Invoke-Step -Label "Checking configured model source registry" -Command @(
            "python", "scripts/check_model_sources.py"
        )
    }
    "run-external-witnesses" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd run-external-witnesses <performance-manifest> [providers]"
        $providers = Get-TaskArg -Index 1
        $providerValue = if (-not [string]::IsNullOrWhiteSpace($providers)) { $providers } else { "essentia,musicnn,beat_tracker,music21,omnizart" }
        Invoke-Step -Label "Running external witness analyzers" -Command @(
            "python", "scripts/run_external_witnesses.py", $manifestPath, $providerValue
        )
    }
    "compare-model-witnesses" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd compare-model-witnesses <performance-manifest>"
        Invoke-Step -Label "Comparing internal and witness model outputs" -Command @(
            "python", "scripts/compare_model_witnesses.py", $manifestPath
        )
    }
    "build-model-consensus" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd build-model-consensus <performance-manifest>"
        Invoke-Step -Label "Building model witness consensus" -Command @(
            "python", "scripts/build_model_consensus.py", $manifestPath
        )
    }
    "run-external-analyzers" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd run-external-analyzers <performance-manifest> [providers]"
        $providers = Get-TaskArg -Index 1
        $providerValue = if (-not [string]::IsNullOrWhiteSpace($providers)) { $providers } else { "essentia,musicnn" }
        Invoke-Step -Label "Running optional external analyzers" -Command @(
            "python", "scripts/run_external_analyzers.py", $manifestPath, "--providers", $providerValue
        )
    }
    "compare-external-features" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd compare-external-features <performance-manifest>"
        Invoke-Step -Label "Comparing internal and external features" -Command @(
            "python", "scripts/compare_external_features.py", $manifestPath
        )
    }
    "build-feature-consensus" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd build-feature-consensus <performance-manifest>"
        Invoke-Step -Label "Building feature consensus summary" -Command @(
            "python", "scripts/build_feature_consensus.py", $manifestPath
        )
    }
    "evaluate-rhythm-lexicon" {
        Invoke-Step -Label "Evaluating rhythm lexicon against standard fixtures" -Command @(
            "python", "scripts/evaluate_rhythm_lexicon.py"
        )
    }
    "compute-transcription-reliability" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd compute-transcription-reliability <performance-manifest>"
        Invoke-Step -Label "Computing per-window transcription reliability" -Command @(
            "python", "scripts/compute_transcription_reliability.py", $manifestPath
        )
    }
    "evaluate-training-quality-gates" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd evaluate-training-quality-gates <performance-manifest>"
        Invoke-Step -Label "Evaluating training quality gates" -Command @(
            "python", "scripts/evaluate_training_quality_gates.py", $manifestPath
        )
    }
    "audit-training-data" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd audit-training-data <performance-manifest>"
        Invoke-Step -Label "Auditing training dataset readiness" -Command @(
            "python", "scripts/audit_training_dataset_record.py", $manifestPath
        )
    }
    "export-training-dataset-splits" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd export-training-dataset-splits <performance-manifest>"
        Invoke-Step -Label "Exporting trusted training dataset splits" -Command @(
            "python", "scripts/export_training_dataset_splits.py", $manifestPath
        )
    }
    "validate-training-export" {
        $exportFolder = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd validate-training-export <export-folder>"
        Invoke-Step -Label "Validating exported training dataset splits" -Command @(
            "python", "scripts/validate_training_export.py", $exportFolder
        )
    }
    "summarize-training-exports" {
        $exportsRoot = Get-TaskArg -Index 0
        $target = if (-not [string]::IsNullOrWhiteSpace($exportsRoot)) { $exportsRoot } else { "datasets/training_exports" }
        Invoke-Step -Label "Summarizing training export manifests" -Command @(
            "python", "scripts/summarize_training_exports.py", $target
        )
    }
    "batch-trusted-exports" {
        $inboxFolder = Get-TaskArg -Index 0
        $maxPerformances = Get-TaskArg -Index 1
        $maxWindows = Get-TaskArg -Index 2
        $inbox = if (-not [string]::IsNullOrWhiteSpace($inboxFolder)) { $inboxFolder } else { "performances/inbox" }
        $perfCap = if (-not [string]::IsNullOrWhiteSpace($maxPerformances)) { $maxPerformances } else { "1" }
        $winCap = if (-not [string]::IsNullOrWhiteSpace($maxWindows)) { $maxWindows } else { "3" }
        Invoke-Step -Label "Running batch trusted exports workflow" -Command @(
            "python", "scripts/batch_trusted_exports.py", $inbox, "--max-performances", $perfCap, "--max-windows", $winCap
        )
    }
    "validate-batch-report" {
        $reportPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd validate-batch-report <batch-report-json>"
        Invoke-Step -Label "Validating batch trusted export report" -Command @(
            "python", "scripts/validate_batch_report.py", $reportPath
        )
    }
    "classify-audio-asset" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd classify-audio-asset <performance-manifest>"
        Invoke-Step -Label "Classifying file-level audio asset type" -Command @(
            "python", "scripts/classify_audio_asset.py", $manifestPath
        )
    }
    "classify-content-regions" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd classify-content-regions <performance-manifest>"
        Invoke-Step -Label "Classifying segment/window/region content states" -Command @(
            "python", "scripts/classify_content_regions.py", $manifestPath
        )
    }
    "apply-analysis-routing" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd apply-analysis-routing <performance-manifest>"
        Invoke-Step -Label "Applying analysis routing decisions" -Command @(
            "python", "scripts/apply_analysis_routing.py", $manifestPath
        )
    }
    "evaluate-label-upgrades" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd evaluate-label-upgrades <performance-manifest>"
        Invoke-Step -Label "Evaluating weak-label upgrade candidates" -Command @(
            "python", "scripts/evaluate_label_upgrade_candidates.py", $manifestPath
        )
    }
    "diagnose-content-routing" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd diagnose-content-routing <performance-manifest>"
        Invoke-Step -Label "Diagnosing content routing calibration quality" -Command @(
            "python", "scripts/diagnose_content_routing.py", $manifestPath
        )
    }
    "route-performance-analysis" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd route-performance-analysis <performance-manifest>"
        Invoke-Step -Label "Running full content-state routing workflow" -Command @(
            "python", "scripts/route_performance_analysis.py", $manifestPath
        )
    }
    "transcribe-yourmt3" {
        $audioPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd transcribe-yourmt3 <audio-path>"
        Invoke-YourMt3TranscriptionWorkflow -AudioPath $audioPath
    }
    "clip-and-transcribe-yourmt3" {
        Ensure-FfmpegPath
        $audioPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd clip-and-transcribe-yourmt3 <audio-path> [seconds]"
        $seconds = Get-TaskArg -Index 1

        $clipCommand = @("python", "scripts/make_clip.py", $audioPath)
        if (-not [string]::IsNullOrWhiteSpace($seconds)) {
            $clipCommand += @("--seconds", $seconds)
        }
        $clipOutput = Invoke-CommandCapture -Label "Creating short clip" -Command $clipCommand
        $clipPath = $clipOutput | Select-Object -Last 1
        if ([string]::IsNullOrWhiteSpace($clipPath)) { throw "Could not determine clip output path." }
        Invoke-YourMt3TranscriptionWorkflow -AudioPath $clipPath
    }
    "debug-args" {
        Write-Host "TASK=$Task"
        Write-Host "TASK_ARG_COUNT=$($TaskArgs.Count)"
        for ($i = 0; $i -lt $TaskArgs.Count; $i++) {
            Write-Host "TASK_ARG_$i=$($TaskArgs[$i])"
        }
    }
    "benchmark-track" {
        $trackFolder = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd benchmark-track <track-folder>"
        Invoke-Step -Label "Benchmarking track" -Command @("python", "scripts/benchmark_track.py", $trackFolder)
    }
    "validate-latest" {
        $libraryRoot = Join-Path (Get-Location) "library"
        if (-not (Test-Path $libraryRoot)) { throw "Library path not found: $libraryRoot" }
        $latestTrack = Get-ChildItem -Path $libraryRoot -Directory -Filter "trk_*" |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
        if ($null -eq $latestTrack) { throw "No track folders found under $libraryRoot" }
        Write-Host "Selected latest track: $($latestTrack.FullName)"
        Invoke-Step -Label "Validating latest track" -Command @("python", "scripts/validate_track.py", $latestTrack.FullName)
    }
    "validate-track" {
        $trackFolder = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd validate-track <track-folder>"
        Invoke-Step -Label "Validating track" -Command @("python", "scripts/validate_track.py", $trackFolder)
    }
    "commit-checkpoint" {
        $commitMessage = if ($TaskArgs.Count -gt 0) { ($TaskArgs -join " ") } else { "Checkpoint" }
        if (-not $script:ResolvedGitExe) { Show-ToolMissingMessage "git"; throw "Cannot run commit-checkpoint because git is unavailable in this shell." }
        Invoke-Step -Label "Git status" -Command @($script:ResolvedGitExe, "status")
        Invoke-Step -Label "Running tests before commit" -Command @("python", "-m", "pytest", "-q")
        Invoke-Step -Label "Staging all changes" -Command @($script:ResolvedGitExe, "add", ".")
        Invoke-Step -Label "Creating commit" -Command @($script:ResolvedGitExe, "commit", "-m", $commitMessage)
    }
    default { Write-Host "Unknown task: $Task"; Show-Usage; exit 1 }
}

Write-Host ""
Write-Host "Completed task: $Task"
