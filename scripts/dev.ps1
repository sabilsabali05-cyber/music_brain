param(
    [Parameter(Position = 0)]
    [string]$Task,
    [Parameter(Position = 1)]
    [string]$CommitMessage = "Checkpoint"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

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
    Write-Host "  smoke-local-fake"
    Write-Host "  smoke-modal-fake"
    Write-Host "  smoke-yourmt3"
    Write-Host "  logs-modal"
    Write-Host "  preflight-yourmt3"
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
    "commit-checkpoint" {
        if (-not $script:ResolvedGitExe) { Show-ToolMissingMessage "git"; throw "Cannot run commit-checkpoint because git is unavailable in this shell." }
        Invoke-Step -Label "Git status" -Command @($script:ResolvedGitExe, "status")
        Invoke-Step -Label "Running tests before commit" -Command @("python", "-m", "pytest", "-q")
        Invoke-Step -Label "Staging all changes" -Command @($script:ResolvedGitExe, "add", ".")
        Invoke-Step -Label "Creating commit" -Command @($script:ResolvedGitExe, "commit", "-m", $CommitMessage)
    }
    default { Write-Host "Unknown task: $Task"; Show-Usage; exit 1 }
}

Write-Host ""
Write-Host "Completed task: $Task"
