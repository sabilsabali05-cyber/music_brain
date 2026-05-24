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
    Write-Host "  write-agent-handoff [handoff args]"
    Write-Host "  prepare-pr-handoff"
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
    Write-Host "  run-modal-external-witnesses <performance-manifest> [providers]"
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
    Write-Host "  audit-dataset-quality-yield"
    Write-Host "  build-generative-examples <performance-manifest>"
    Write-Host "  validate-generative-examples <generative-dataset-folder>"
    Write-Host "  diagnose-generative-examples <generative-dataset-folder>"
    Write-Host "  diagnose-generative-pairing <generative-dataset-folder>"
    Write-Host "  generate-midi-from-examples <generative-dataset-folder> [task] [split]"
    Write-Host "  validate-generated-midi <output-folder>"
    Write-Host "  check-symbolic-model-backends"
    Write-Host "  check-symbolic-backends"
    Write-Host "  check-model-integrations"
    Write-Host "  check-moonbeam-setup"
    Write-Host "  run-moonbeam-smoke-test"
    Write-Host "  check-musicbert-setup"
    Write-Host "  run-musicbert-smoke-test"
    Write-Host "  evaluate-symbolic-candidates-musicbert"
    Write-Host "  check-midigpt-setup"
    Write-Host "  run-midigpt-smoke-test"
    Write-Host "  generate-midigpt-variation-scaffold"
    Write-Host "  check-text2midi-setup"
    Write-Host "  run-text2midi-smoke-test"
    Write-Host "  bootstrap-symbolic-model-local-config"
    Write-Host "  plan-symbolic-backend-install"
    Write-Host "  check-symbolic-backend-activation"
    Write-Host "  discover-symbolic-model-sources"
    Write-Host "  generate-2min-ballad [--use-symbolic-backends] [--output <folder>]"
    Write-Host "  regenerate-ballad-from-review <feedback-json>"
    Write-Host "  plan-microtonal-composition"
    Write-Host "  validate-microtonal-tuning"
    Write-Host "  export-microtonal-midi-plan"
    Write-Host "  generate-text2midi-prompt-sketch-scaffold"
    Write-Host "  check-audio-understanding-setup"
    Write-Host "  run-audio-understanding-smoke-tests"
    Write-Host "  plan-audio-texture-embedding"
    Write-Host "  check-transcription-witnesses-setup"
    Write-Host "  run-transcription-witnesses-smoke-tests"
    Write-Host "  plan-transcription-witnesses"
    Write-Host "  check-source-separation-setup"
    Write-Host "  run-source-separation-smoke-tests"
    Write-Host "  plan-source-separation-witness"
    Write-Host "  plan-full-model-activation <manifest>"
    Write-Host "  run-full-model-activation <manifest>"
    Write-Host "  build-music-evidence-fusion-plan"
    Write-Host "  write-model-integration-roadmap"
    Write-Host "  plan-symbolic-generation <generative-dataset-folder> [task]"
    Write-Host "  plan-ratio-analysis <performance-manifest>"
    Write-Host "  plan-ratio-composition [duration] [ratio] [goal]"
    Write-Host "  generate-midi-with-backend <generative-dataset-folder> [provider] [task]"
    Write-Host "  generate-symbolic-ensemble <prompt>"
    Write-Host "  generate-tangible-demo [duration] [ratio] [goal]"
    Write-Host "  validate-tangible-demo [output-folder]"
    Write-Host "  export-ableton-project-v1 <tangible-output-folder> [--copy-local-samples]"
    Write-Host "  validate-ableton-project-export [project-folder]"
    Write-Host "  batch-trusted-exports <inbox-folder> [max-performances] [max-windows]"
    Write-Host "  validate-batch-report <batch-report-json>"
    Write-Host "  classify-audio-asset <performance-manifest>"
    Write-Host "  index-sample-library <config-json> (copy local_sounds_library.example.json to local_sounds_library.json first)"
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
    Write-Host "  evaluate-mass-ingestion-readiness"
    Write-Host "  evaluate-personalized-training-readiness"
    Write-Host "  check-privacy-leaks [--strict]"
    Write-Host "  plan-historical-path-scrub [--apply-safe]"
    Write-Host "  plan-controlled-ingestion-batch <manifest>"
    Write-Host "  run-controlled-ingestion-batch <manifest> [--execute]"
    Write-Host "  compare-generation-iterations <old-output> <new-output>"
    Write-Host "  build-mass-ingestion-readiness-artifacts"
    Write-Host "  plan-texture-analysis"
    Write-Host "  create-synplant-session-plan <ableton_project_folder>"
    Write-Host "  import-synplant-session-results <session_results_json>"
    Write-Host "  validate-synplant-sessions"
    Write-Host "  build-sound-palette-context <ableton_project_folder>"
    Write-Host "  export-symbolic-ensemble-ableton [source-folder] [target-folder]"
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
    $userProfile = [Environment]::GetFolderPath("UserProfile")
    $candidates = @(
        "C:\Program Files\Git\cmd\git.exe",
        "C:\Program Files\Git\bin\git.exe",
        (Join-Path $userProfile "AppData\Local\Programs\Git\cmd\git.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) { return @{ Path = $candidate; Source = "fallback: $candidate" } }
    }
    return @{ Path = $null; Source = "missing" }
}

function Find-FfmpegPath {
    $onPath = Find-ToolPathFromCommand "ffmpeg"
    if ($onPath) { return @{ Path = $onPath; Source = "PATH" } }

    $globRoot = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
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
    "write-agent-handoff" {
        $command = @("python", "scripts/write_agent_handoff.py")
        if ($TaskArgs.Count -gt 0) { $command += $TaskArgs }
        Invoke-Step -Label "Writing latest agent handoff reports" -Command $command
    }
    "prepare-pr-handoff" {
        $command = @("python", "scripts/prepare_pr_handoff.py")
        if ($TaskArgs.Count -gt 0) { $command += $TaskArgs }
        Invoke-Step -Label "Preparing PR handoff markdown body" -Command $command
    }
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
    "run-modal-external-witnesses" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd run-modal-external-witnesses <performance-manifest> [providers]"
        $providers = Get-TaskArg -Index 1
        $providerValue = if (-not [string]::IsNullOrWhiteSpace($providers)) { $providers } else { "essentia,music21" }
        Invoke-Step -Label "Running Modal external witness analyzers" -Command @(
            "python", "scripts/run_modal_external_witnesses.py", $manifestPath, "--providers", $providerValue
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
    "audit-dataset-quality-yield" {
        Invoke-Step -Label "Auditing dataset quality and data yield" -Command @(
            "python", "scripts/audit_dataset_quality_yield.py"
        )
    }
    "build-generative-examples" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd build-generative-examples <performance-manifest>"
        Invoke-Step -Label "Building generative training examples" -Command @(
            "python", "scripts/build_generative_training_examples.py", $manifestPath
        )
    }
    "validate-generative-examples" {
        $datasetFolder = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd validate-generative-examples <generative-dataset-folder>"
        Invoke-Step -Label "Validating generative training examples" -Command @(
            "python", "scripts/validate_generative_training_examples.py", $datasetFolder
        )
    }
    "diagnose-generative-examples" {
        $datasetFolder = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd diagnose-generative-examples <generative-dataset-folder>"
        Invoke-Step -Label "Diagnosing generative training examples" -Command @(
            "python", "scripts/diagnose_generative_examples.py", $datasetFolder
        )
    }
    "diagnose-generative-pairing" {
        $datasetFolder = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd diagnose-generative-pairing <generative-dataset-folder>"
        Invoke-Step -Label "Diagnosing generative pairing quality" -Command @(
            "python", "scripts/diagnose_generative_pairing.py", $datasetFolder
        )
    }
    "generate-midi-from-examples" {
        $datasetFolder = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd generate-midi-from-examples <generative-dataset-folder> [task] [split]"
        $taskName = Get-TaskArg -Index 1
        $splitName = Get-TaskArg -Index 2
        $taskValue = if (-not [string]::IsNullOrWhiteSpace($taskName)) { $taskName } else { "continuation" }
        $splitValue = if (-not [string]::IsNullOrWhiteSpace($splitName)) { $splitName } else { "train" }
        Invoke-Step -Label "Generating prototype MIDI from examples" -Command @(
            "python", "scripts/generate_midi_from_examples.py", $datasetFolder, "--task", $taskValue, "--split", $splitValue
        )
    }
    "validate-generated-midi" {
        $outputFolder = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd validate-generated-midi <output-folder>"
        Invoke-Step -Label "Validating generated MIDI outputs" -Command @(
            "python", "scripts/validate_generated_midi_outputs.py", $outputFolder
        )
    }
    "check-symbolic-model-backends" {
        Invoke-Step -Label "Checking symbolic model backend availability" -Command @(
            "python", "scripts/check_symbolic_model_backends.py"
        )
    }
    "check-symbolic-backends" {
        Invoke-Step -Label "Checking symbolic ensemble backend availability" -Command @(
            "python", "scripts/check_symbolic_backends.py"
        )
    }
    "check-model-integrations" {
        Invoke-Step -Label "Checking broader model integration availability" -Command @(
            "python", "scripts/check_model_integrations.py"
        )
    }
    "check-moonbeam-setup" {
        Invoke-Step -Label "Checking Moonbeam local setup status" -Command @(
            "python", "scripts/check_moonbeam_setup.py"
        )
    }
    "run-moonbeam-smoke-test" {
        Invoke-Step -Label "Running Moonbeam minimal smoke test" -Command @(
            "python", "scripts/run_moonbeam_smoke_test.py"
        )
    }
    "check-musicbert-setup" {
        Invoke-Step -Label "Checking MusicBERT local setup status" -Command @(
            "python", "scripts/check_musicbert_setup.py"
        )
    }
    "run-musicbert-smoke-test" {
        Invoke-Step -Label "Running MusicBERT minimal smoke test" -Command @(
            "python", "scripts/run_musicbert_smoke_test.py"
        )
    }
    "evaluate-symbolic-candidates-musicbert" {
        Invoke-Step -Label "Evaluating symbolic candidates with MusicBERT scaffold" -Command @(
            "python", "scripts/evaluate_symbolic_candidates_musicbert.py"
        )
    }
    "check-midigpt-setup" {
        Invoke-Step -Label "Checking MIDI-GPT local setup status" -Command @(
            "python", "scripts/check_midigpt_setup.py"
        )
    }
    "run-midigpt-smoke-test" {
        Invoke-Step -Label "Running MIDI-GPT minimal smoke test" -Command @(
            "python", "scripts/run_midigpt_smoke_test.py"
        )
    }
    "generate-midigpt-variation-scaffold" {
        Invoke-Step -Label "Generating MIDI-GPT variation scaffold report" -Command @(
            "python", "scripts/generate_midigpt_variation_scaffold.py"
        )
    }
    "check-text2midi-setup" {
        Invoke-Step -Label "Checking Text2MIDI local setup status" -Command @(
            "python", "scripts/check_text2midi_setup.py"
        )
    }
    "run-text2midi-smoke-test" {
        Invoke-Step -Label "Running Text2MIDI minimal smoke test" -Command @(
            "python", "scripts/run_text2midi_smoke_test.py"
        )
    }
    "bootstrap-symbolic-model-local-config" {
        Invoke-Step -Label "Bootstrapping symbolic model local config" -Command @(
            "python", "scripts/bootstrap_symbolic_model_local_config.py"
        )
    }
    "plan-symbolic-backend-install" {
        Invoke-Step -Label "Writing symbolic backend install plan" -Command @(
            "python", "scripts/plan_symbolic_backend_install.py"
        )
    }
    "check-symbolic-backend-activation" {
        Invoke-Step -Label "Checking symbolic backend activation status" -Command @(
            "python", "scripts/check_symbolic_backend_activation.py"
        )
    }
    "discover-symbolic-model-sources" {
        Invoke-Step -Label "Discovering official symbolic model sources" -Command @(
            "python", "scripts/discover_symbolic_model_sources.py"
        )
    }
    "generate-2min-ballad" {
        $useSymbolic = $false
        $output = "outputs/ballad_2min_v2"
        for ($i = 0; $i -lt $TaskArgs.Count; $i++) {
            $arg = $TaskArgs[$i]
            if ($arg -eq "--use-symbolic-backends") {
                $useSymbolic = $true
            }
            elseif ($arg -eq "--output") {
                if (($i + 1) -ge $TaskArgs.Count) { throw "Usage: scripts\dev.cmd generate-2min-ballad [--use-symbolic-backends] [--output <folder>]" }
                $output = $TaskArgs[$i + 1]
                $i++
            }
        }
        $command = @("python", "scripts/generate_2min_ballad.py", "--output", $output)
        if ($useSymbolic) {
            $command += @("--use-symbolic-backends")
        }
        Invoke-Step -Label "Generating 2-minute ballad v2 package" -Command $command
    }
    "regenerate-ballad-from-review" {
        $feedbackPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd regenerate-ballad-from-review <feedback-json>"
        Invoke-Step -Label "Regenerating ballad stems from review feedback" -Command @(
            "python", "scripts/regenerate_ballad_from_review.py", $feedbackPath
        )
    }
    "plan-microtonal-composition" {
        Invoke-Step -Label "Planning microtonal composition layer outputs" -Command @(
            "python", "scripts/plan_microtonal_composition.py"
        )
    }
    "validate-microtonal-tuning" {
        Invoke-Step -Label "Validating microtonal tuning presets and Scala parsing" -Command @(
            "python", "scripts/validate_microtonal_tuning.py"
        )
    }
    "export-microtonal-midi-plan" {
        Invoke-Step -Label "Planning microtonal MIDI export strategies" -Command @(
            "python", "scripts/export_microtonal_midi_plan.py"
        )
    }
    "generate-text2midi-prompt-sketch-scaffold" {
        Invoke-Step -Label "Generating Text2MIDI prompt sketch scaffold report" -Command @(
            "python", "scripts/generate_text2midi_prompt_sketch_scaffold.py"
        )
    }
    "check-audio-understanding-setup" {
        Invoke-Step -Label "Checking audio understanding local setup status" -Command @(
            "python", "scripts/check_audio_understanding_setup.py"
        )
    }
    "run-audio-understanding-smoke-tests" {
        Invoke-Step -Label "Running audio understanding minimal smoke tests" -Command @(
            "python", "scripts/run_audio_understanding_smoke_tests.py"
        )
    }
    "plan-audio-texture-embedding" {
        Invoke-Step -Label "Planning audio texture embedding workflow" -Command @(
            "python", "scripts/plan_audio_texture_embedding.py"
        )
    }
    "check-transcription-witnesses-setup" {
        Invoke-Step -Label "Checking transcription witness local setup status" -Command @(
            "python", "scripts/check_transcription_witnesses_setup.py"
        )
    }
    "run-transcription-witnesses-smoke-tests" {
        Invoke-Step -Label "Running transcription witness smoke scaffolds" -Command @(
            "python", "scripts/run_transcription_witnesses_smoke_tests.py"
        )
    }
    "plan-transcription-witnesses" {
        Invoke-Step -Label "Planning transcription witness workflow" -Command @(
            "python", "scripts/plan_transcription_witnesses.py"
        )
    }
    "check-source-separation-setup" {
        Invoke-Step -Label "Checking source separation witness setup status" -Command @(
            "python", "scripts/check_source_separation_setup.py"
        )
    }
    "run-source-separation-smoke-tests" {
        Invoke-Step -Label "Running source separation witness smoke scaffolds" -Command @(
            "python", "scripts/run_source_separation_smoke_tests.py"
        )
    }
    "plan-source-separation-witness" {
        Invoke-Step -Label "Planning source separation witness workflow" -Command @(
            "python", "scripts/plan_source_separation_witness.py"
        )
    }
    "plan-full-model-activation" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd plan-full-model-activation <manifest>"
        Invoke-Step -Label "Planning full model activation scaffold" -Command @(
            "python", "scripts/plan_full_model_activation.py", $manifestPath
        )
    }
    "run-full-model-activation" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd run-full-model-activation <manifest>"
        Invoke-Step -Label "Running full model activation scaffold" -Command @(
            "python", "scripts/run_full_model_activation.py", $manifestPath
        )
    }
    "build-music-evidence-fusion-plan" {
        Invoke-Step -Label "Building music evidence fusion plan scaffold" -Command @(
            "python", "scripts/build_music_evidence_fusion_plan.py"
        )
    }
    "write-model-integration-roadmap" {
        Invoke-Step -Label "Writing model integration roadmap report" -Command @(
            "python", "scripts/write_model_integration_roadmap.py"
        )
    }
    "plan-symbolic-generation" {
        $datasetFolder = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd plan-symbolic-generation <generative-dataset-folder> [task]"
        $taskName = Get-TaskArg -Index 1
        $taskValue = if (-not [string]::IsNullOrWhiteSpace($taskName)) { $taskName } else { "continuation" }
        Invoke-Step -Label "Planning symbolic generation strategy" -Command @(
            "python", "scripts/plan_symbolic_generation.py", $datasetFolder, "--task", $taskValue
        )
    }
    "plan-ratio-analysis" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd plan-ratio-analysis <performance-manifest>"
        Invoke-Step -Label "Planning ratio analysis from existing artifacts" -Command @(
            "python", "scripts/plan_ratio_analysis.py", $manifestPath
        )
    }
    "plan-ratio-composition" {
        $durationArg = Get-TaskArg -Index 0
        $ratioArg = Get-TaskArg -Index 1
        $goalArg = Get-TaskArg -Index 2
        $duration = if (-not [string]::IsNullOrWhiteSpace($durationArg)) { $durationArg } else { "180" }
        $ratio = if (-not [string]::IsNullOrWhiteSpace($ratioArg)) { $ratioArg } else { "golden_ratio" }
        $goal = if (-not [string]::IsNullOrWhiteSpace($goalArg)) { $goalArg } else { "climax" }
        Invoke-Step -Label "Planning ratio-conditioned composition" -Command @(
            "python", "scripts/plan_ratio_conditioned_composition.py", "--duration", $duration, "--ratio", $ratio, "--goal", $goal
        )
    }
    "generate-midi-with-backend" {
        $datasetFolder = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd generate-midi-with-backend <generative-dataset-folder> [provider] [task]"
        $providerName = Get-TaskArg -Index 1
        $taskName = Get-TaskArg -Index 2
        $providerValue = if (-not [string]::IsNullOrWhiteSpace($providerName)) { $providerName } else { "example_retrieval" }
        $taskValue = if (-not [string]::IsNullOrWhiteSpace($taskName)) { $taskName } else { "continuation" }
        Invoke-Step -Label "Generating MIDI via symbolic backend wrapper" -Command @(
            "python", "scripts/generate_midi_with_backend.py", $datasetFolder, "--provider", $providerValue, "--task", $taskValue
        )
    }
    "generate-symbolic-ensemble" {
        $prompt = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd generate-symbolic-ensemble <prompt>"
        Invoke-Step -Label "Generating symbolic output via ensemble orchestrator" -Command @(
            "python", "scripts/generate_with_symbolic_ensemble.py", $prompt
        )
    }
    "generate-tangible-demo" {
        $durationArg = Get-TaskArg -Index 0
        $ratioArg = Get-TaskArg -Index 1
        $goalArg = Get-TaskArg -Index 2
        $duration = if (-not [string]::IsNullOrWhiteSpace($durationArg)) { $durationArg } else { "180" }
        $ratio = if (-not [string]::IsNullOrWhiteSpace($ratioArg)) { $ratioArg } else { "golden_ratio" }
        $goal = if (-not [string]::IsNullOrWhiteSpace($goalArg)) { $goalArg } else { "climax" }
        Invoke-Step -Label "Generating tangible MIDI demo composition" -Command @(
            "python", "scripts/generate_tangible_demo.py", $duration, $ratio, $goal
        )
    }
    "validate-tangible-demo" {
        $outputFolder = Get-TaskArg -Index 0
        $target = if (-not [string]::IsNullOrWhiteSpace($outputFolder)) { $outputFolder } else { "outputs/tangible_generation_v1" }
        Invoke-Step -Label "Validating tangible demo outputs" -Command @(
            "python", "scripts/validate_tangible_demo.py", $target
        )
    }
    "export-ableton-project-v1" {
        $tangibleFolder = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd export-ableton-project-v1 <tangible-output-folder> [--copy-local-samples]"
        $copyFlag = Get-TaskArg -Index 1
        $command = @("python", "scripts/export_ableton_project_v1.py", $tangibleFolder)
        if ($copyFlag -eq "--copy-local-samples") {
            $command += @("--copy-local-samples")
        }
        Invoke-Step -Label "Exporting Ableton project scaffold v1" -Command $command
    }
    "validate-ableton-project-export" {
        $projectFolder = Get-TaskArg -Index 0
        $target = if (-not [string]::IsNullOrWhiteSpace($projectFolder)) { $projectFolder } else { "outputs/ableton_project_v1/AI_Generated_Song_Project" }
        Invoke-Step -Label "Validating Ableton project export" -Command @(
            "python", "scripts/validate_ableton_project_export.py", $target
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
    "index-sample-library" {
        $configPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd index-sample-library <config-json>"
        Invoke-Step -Label "Indexing local sample seed library" -Command @(
            "python", "scripts/index_sample_library.py", $configPath
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
    "evaluate-mass-ingestion-readiness" {
        Invoke-Step -Label "Evaluating mass-ingestion readiness" -Command @(
            "python", "scripts/evaluate_mass_ingestion_readiness.py"
        )
    }
    "evaluate-personalized-training-readiness" {
        Invoke-Step -Label "Evaluating personalized model training readiness" -Command @(
            "python", "scripts/evaluate_personalized_training_readiness.py"
        )
    }
    "check-privacy-leaks" {
        $strictFlag = Get-TaskArg -Index 0
        $command = @("python", "scripts/check_privacy_leaks.py")
        if ($strictFlag -eq "--strict") {
            $command += @("--strict")
        }
        Invoke-Step -Label "Checking tracked files for privacy leaks" -Command $command
    }
    "plan-historical-path-scrub" {
        $applySafe = Get-TaskArg -Index 0
        $command = @("python", "scripts/plan_historical_path_scrub.py")
        if ($applySafe -eq "--apply-safe") {
            $command += @("--apply-safe")
        }
        Invoke-Step -Label "Planning historical path scrub" -Command $command
    }
    "plan-controlled-ingestion-batch" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd plan-controlled-ingestion-batch <manifest>"
        Invoke-Step -Label "Planning controlled ingestion batch" -Command @(
            "python", "scripts/plan_controlled_ingestion_batch.py", $manifestPath
        )
    }
    "run-controlled-ingestion-batch" {
        $manifestPath = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd run-controlled-ingestion-batch <manifest> [--execute]"
        $executeFlag = Get-TaskArg -Index 1
        $command = @("python", "scripts/run_controlled_ingestion_batch.py", $manifestPath)
        if ($executeFlag -eq "--execute") {
            $command += @("--execute")
        }
        Invoke-Step -Label "Running controlled ingestion batch shell" -Command $command
    }
    "compare-generation-iterations" {
        $oldOutput = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd compare-generation-iterations <old-output> <new-output>"
        $newOutput = Get-TaskArgOrThrow -Index 1 -Usage "Usage: scripts\dev.cmd compare-generation-iterations <old-output> <new-output>"
        Invoke-Step -Label "Comparing generation output iterations" -Command @(
            "python", "scripts/compare_generation_iterations.py", $oldOutput, $newOutput
        )
    }
    "build-mass-ingestion-readiness-artifacts" {
        Invoke-Step -Label "Building readiness artifacts for phases 6-14" -Command @(
            "python", "scripts/build_mass_ingestion_readiness_artifacts.py"
        )
    }
    "plan-texture-analysis" {
        Invoke-Step -Label "Planning texture intelligence analysis from sample metadata" -Command @(
            "python", "scripts/plan_texture_analysis.py"
        )
    }
    "create-synplant-session-plan" {
        $abletonProjectFolder = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd create-synplant-session-plan <ableton_project_folder>"
        Invoke-Step -Label "Creating Synplant session seed plan (manual workflow)" -Command @(
            "python", "scripts/create_synplant_session_plan.py", $abletonProjectFolder
        )
    }
    "import-synplant-session-results" {
        $sessionResultsJson = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd import-synplant-session-results <session_results_json>"
        Invoke-Step -Label "Importing Synplant manual session results" -Command @(
            "python", "scripts/import_synplant_session_results.py", $sessionResultsJson
        )
    }
    "validate-synplant-sessions" {
        Invoke-Step -Label "Validating Synplant session imports and policy constraints" -Command @(
            "python", "scripts/validate_synplant_sessions.py"
        )
    }
    "build-sound-palette-context" {
        $abletonProjectFolder = Get-TaskArgOrThrow -Index 0 -Usage "Usage: scripts\dev.cmd build-sound-palette-context <ableton_project_folder>"
        Invoke-Step -Label "Building collective sound palette context" -Command @(
            "python", "scripts/build_sound_palette_context.py", $abletonProjectFolder
        )
    }
    "export-symbolic-ensemble-ableton" {
        $sourceFolder = Get-TaskArg -Index 0
        $targetFolder = Get-TaskArg -Index 1
        $source = if (-not [string]::IsNullOrWhiteSpace($sourceFolder)) { $sourceFolder } else { "outputs/symbolic_ensemble_v1" }
        $target = if (-not [string]::IsNullOrWhiteSpace($targetFolder)) { $targetFolder } else { "outputs/ableton_project_symbolic_ensemble_v1" }
        Invoke-Step -Label "Exporting symbolic ensemble output to Ableton scaffold" -Command @(
            "python", "scripts/export_symbolic_ensemble_ableton.py", "--source-dir", $source, "--target-dir", $target
        )
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
