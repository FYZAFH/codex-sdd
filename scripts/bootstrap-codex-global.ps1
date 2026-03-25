param(
    [string]$SourceRepo,
    [string]$RepoUrl = 'https://github.com/FYZAFH/codex-sdd.git',
    [string]$RepoRef = 'main',
    [string]$CheckoutDir,
    [string]$CodexHome,
    [switch]$Uninstall
)

$ErrorActionPreference = 'Stop'

function Resolve-FullPath([string]$Path) {
    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }

    return [System.IO.Path]::GetFullPath((Join-Path (Get-Location).Path $Path))
}

function Default-CheckoutDir() {
    if ($env:LOCALAPPDATA) {
        return Join-Path $env:LOCALAPPDATA 'double-sdd\repo'
    }
    return Join-Path $HOME 'AppData\Local\double-sdd\repo'
}

if (-not $CheckoutDir) {
    $CheckoutDir = Default-CheckoutDir
}

if ($SourceRepo) {
    $SourceRoot = Resolve-FullPath $SourceRepo
} else {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw 'git is required unless -SourceRepo is provided.'
    }

    $CheckoutDir = Resolve-FullPath $CheckoutDir
    $CheckoutParent = Split-Path -Parent $CheckoutDir
    if ($CheckoutParent) {
        New-Item -ItemType Directory -Force -Path $CheckoutParent | Out-Null
    }

    $GitDir = Join-Path $CheckoutDir '.git'
    if (Test-Path -LiteralPath $GitDir) {
        $CurrentOrigin = (& git -C $CheckoutDir config --get remote.origin.url 2>$null | Select-Object -First 1)
        if ($CurrentOrigin -and $CurrentOrigin.Trim() -ne $RepoUrl) {
            throw "checkout dir already points to a different origin: $CurrentOrigin"
        }

        & git -C $CheckoutDir remote set-url origin $RepoUrl
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
        & git -C $CheckoutDir fetch --depth 1 origin $RepoRef
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
        & git -C $CheckoutDir checkout --force FETCH_HEAD
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    } elseif (Test-Path -LiteralPath $CheckoutDir) {
        throw "checkout path exists and is not a git repo: $CheckoutDir"
    } else {
        & git clone --depth 1 --branch $RepoRef $RepoUrl $CheckoutDir
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }

    $SourceRoot = $CheckoutDir
}

if ($Uninstall) {
    $Installer = Join-Path $SourceRoot 'scripts\uninstall-codex.ps1'
} else {
    $Installer = Join-Path $SourceRoot 'scripts\install-codex.ps1'
}

if ($CodexHome) {
    & $Installer -CodexHome $CodexHome
} else {
    & $Installer
}
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
