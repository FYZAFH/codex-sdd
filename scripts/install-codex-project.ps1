param(
    [string]$ProjectRoot,
    [string]$ArtifactRoot
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = (Get-Location).Path
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$Installer = Join-Path $ScriptDir 'codex_installer.py'

if (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCommand = @('py', '-3')
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCommand = @('python')
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PythonCommand = @('python3')
} else {
    throw 'Python 3 is required to install double-SDD for Codex on Windows.'
}

$Arguments = @(
    $Installer,
    'install-project',
    "--repo-root=$RepoRoot",
    "--project-root=$ProjectRoot"
)

if ($ArtifactRoot) {
    $Arguments += "--artifact-root=$ArtifactRoot"
}

$PythonArgs = @()
if ($PythonCommand.Count -gt 1) {
    $PythonArgs = $PythonCommand[1..($PythonCommand.Count - 1)]
}

& $PythonCommand[0] @PythonArgs @Arguments
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
