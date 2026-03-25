param(
    [string]$CodexHome
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Installer = Join-Path $ScriptDir 'codex_installer.py'

if (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCommand = @('py', '-3')
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCommand = @('python')
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PythonCommand = @('python3')
} else {
    throw 'Python 3 is required to uninstall double-SDD for Codex on Windows.'
}

$Arguments = @($Installer, 'uninstall-global')
if ($CodexHome) {
    $Arguments += @('--codex-home', $CodexHome)
}

$PythonArgs = @()
if ($PythonCommand.Count -gt 1) {
    $PythonArgs = $PythonCommand[1..($PythonCommand.Count - 1)]
}

& $PythonCommand[0] @PythonArgs @Arguments
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
