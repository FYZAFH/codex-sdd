#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path


CONFIG_ROOT_MARKER_START = "# double-sdd:codex-config-root:start"
CONFIG_ROOT_MARKER_END = "# double-sdd:codex-config-root:end"
CONFIG_AGENTS_MARKER_START = "# double-sdd:codex-config-agents:start"
CONFIG_AGENTS_MARKER_END = "# double-sdd:codex-config-agents:end"
EXCLUDE_MARKER_START = "# double-sdd:start"
EXCLUDE_MARKER_END = "# double-sdd:end"
SKILL_OWNER_MARKER = ".double-sdd-owner"
SKILL_OWNER_VALUE = "double-sdd"
CUSTOM_AGENT_MARKER = "# double-sdd:managed"

CONFIG_ROOT_CONFLICT_PATTERNS = [
    ("developer_instructions", re.compile(r"(?m)^\s*developer_instructions\s*=")),
    ("compact_prompt", re.compile(r"(?m)^\s*compact_prompt\s*=")),
]

CONFIG_AGENT_CONFLICT_PATTERNS = [
    ("[agents.implementer]", re.compile(r"(?m)^\s*\[agents\.implementer\]\s*$")),
    ("[agents.spec-code-reviewer]", re.compile(r"(?m)^\s*\[agents\.spec-code-reviewer\]\s*$")),
    ("[agents.quality-code-reviewer]", re.compile(r"(?m)^\s*\[agents\.quality-code-reviewer\]\s*$")),
    ("[agents.spec-document-reviewer]", re.compile(r"(?m)^\s*\[agents\.spec-document-reviewer\]\s*$")),
    ("[agents.plan-document-reviewer]", re.compile(r"(?m)^\s*\[agents\.plan-document-reviewer\]\s*$")),
]


def resolve_path(path: str | Path) -> Path:
    expanded = Path(path).expanduser()
    if expanded.is_absolute():
        return expanded
    return (Path.cwd() / expanded).absolute()


def path_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def remove_path(path: Path) -> None:
    if not path_exists(path):
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    shutil.rmtree(path)


def read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def make_executable(path: Path) -> None:
    current_mode = path.stat().st_mode
    path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def default_codex_home() -> Path:
    return resolve_path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))


def default_global_skills_root() -> Path:
    return resolve_path(Path.home() / ".agents" / "skills")


def default_global_home_root() -> Path:
    return resolve_path(Path.home())


def default_global_agents_root(codex_home: Path) -> Path:
    return codex_home / "agents"


def default_global_config_file(codex_home: Path) -> Path:
    return codex_home / "config.toml"


def default_project_skills_root(project_root: Path) -> Path:
    return project_root / ".agents" / "skills"


def default_project_agents_root(project_root: Path) -> Path:
    return project_root / ".codex" / "agents"


def default_project_config_file(project_root: Path) -> Path:
    return project_root / ".codex" / "config.toml"


def strip_managed_block(text: str, start_marker: str, end_marker: str) -> str:
    result: list[str] = []
    skip = False
    for line in text.splitlines():
        if line == start_marker:
            skip = True
            continue
        if line == end_marker:
            skip = False
            continue
        if not skip:
            result.append(line)

    while result and result[-1] == "":
        result.pop()
    return "\n".join(result)


def split_toml_root_and_tables(text: str) -> tuple[str, str]:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.lstrip().startswith("["):
            return "\n".join(lines[:index]).strip(), "\n".join(lines[index:]).strip()
    return text.strip(), ""


def find_config_conflicts(existing_text: str) -> list[str]:
    root_text, tables_text = split_toml_root_and_tables(existing_text)
    conflicts: list[str] = []

    for label, pattern in CONFIG_ROOT_CONFLICT_PATTERNS:
        if pattern.search(root_text):
            conflicts.append(label)

    for label, pattern in CONFIG_AGENT_CONFLICT_PATTERNS:
        if pattern.search(tables_text):
            conflicts.append(label)

    return conflicts


def update_managed_config_file(path: Path, managed_text: str) -> None:
    existing = read_text(path)
    stripped = strip_managed_block(
        strip_managed_block(existing, CONFIG_ROOT_MARKER_START, CONFIG_ROOT_MARKER_END),
        CONFIG_AGENTS_MARKER_START,
        CONFIG_AGENTS_MARKER_END,
    ).rstrip("\n")

    conflicts = find_config_conflicts(stripped)
    if conflicts:
        joined = ", ".join(conflicts)
        raise RuntimeError(f"refusing to modify existing config with conflicting Codex keys/tables: {path} ({joined})")

    existing_root, existing_tables = split_toml_root_and_tables(stripped)
    managed_root, managed_tables = split_toml_root_and_tables(managed_text.rstrip("\n"))

    sections: list[str] = []
    if existing_root:
        sections.append(existing_root)
    if managed_root:
        sections.append("\n".join([CONFIG_ROOT_MARKER_START, managed_root, CONFIG_ROOT_MARKER_END]))
    if existing_tables:
        sections.append(existing_tables)
    if managed_tables:
        sections.append("\n".join([CONFIG_AGENTS_MARKER_START, managed_tables, CONFIG_AGENTS_MARKER_END]))

    write_text(path, "\n\n".join(sections) + ("\n" if sections else ""))


def remove_managed_config_file(path: Path) -> None:
    if not path.is_file():
        return

    cleaned = strip_managed_block(
        strip_managed_block(read_text(path), CONFIG_ROOT_MARKER_START, CONFIG_ROOT_MARKER_END),
        CONFIG_AGENTS_MARKER_START,
        CONFIG_AGENTS_MARKER_END,
    )
    if cleaned:
        write_text(path, cleaned.rstrip("\n") + "\n")
    else:
        write_text(path, "")


def render_codex_bundle(repo_root: Path, output_dir: Path, logical_root: Path) -> None:
    command = [
        sys.executable,
        str(repo_root / "scripts" / "render-platform-bundle.py"),
        "--platform",
        "codex",
        "--output",
        str(output_dir),
        "--logical-root",
        str(logical_root),
    ]
    subprocess.run(command, check=True)


def is_managed_skill_target(target: Path) -> bool:
    if not target.is_dir():
        return False
    marker_path = target / SKILL_OWNER_MARKER
    return marker_path.is_file() and marker_path.read_text(encoding="utf-8").strip() == SKILL_OWNER_VALUE


def is_managed_agent_target(target: Path) -> bool:
    if not target.is_file():
        return False
    first_line = target.read_text(encoding="utf-8").splitlines()
    return bool(first_line) and first_line[0] == CUSTOM_AGENT_MARKER


def install_skill_target(source_skill: Path, target: Path) -> None:
    remove_path(target)
    shutil.copytree(source_skill, target)
    write_text(target / SKILL_OWNER_MARKER, f"{SKILL_OWNER_VALUE}\n")


def install_agent_target(source_agent: Path, target: Path) -> None:
    remove_path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_agent, target)


def validate_skill_targets(staging_root: Path, skills_root: Path) -> None:
    staging_skills_root = staging_root / ".agents" / "skills"
    for skill_dir in sorted(staging_skills_root.iterdir()):
        if not skill_dir.is_dir():
            continue

        target = skills_root / skill_dir.name
        if path_exists(target) and not is_managed_skill_target(target):
            raise RuntimeError(f"refusing to replace existing path: {target}")


def validate_agent_targets(staging_root: Path, agents_root: Path) -> None:
    staging_agents_root = staging_root / ".codex" / "agents"
    for agent_file in sorted(staging_agents_root.glob("*.toml")):
        target = agents_root / agent_file.name
        if path_exists(target) and not is_managed_agent_target(target):
            raise RuntimeError(f"refusing to replace existing path: {target}")


def remove_managed_skill_targets(skills_root: Path) -> None:
    if not skills_root.is_dir():
        return
    for target in skills_root.iterdir():
        if is_managed_skill_target(target):
            remove_path(target)


def remove_managed_agent_targets(agents_root: Path) -> None:
    if not agents_root.is_dir():
        return
    for target in agents_root.glob("*.toml"):
        if is_managed_agent_target(target):
            remove_path(target)


def prune_empty_directories(start_path: Path, stop_path: Path) -> None:
    path = start_path
    while path != stop_path and path != path.parent:
        try:
            path.rmdir()
        except OSError:
            break
        path = path.parent


def install_rendered_bundle(
    staging_root: Path,
    skills_root: Path,
    agents_root: Path,
    config_file: Path,
) -> None:
    skills_root.mkdir(parents=True, exist_ok=True)
    agents_root.mkdir(parents=True, exist_ok=True)

    validate_skill_targets(staging_root, skills_root)
    validate_agent_targets(staging_root, agents_root)

    for skill_dir in sorted((staging_root / ".agents" / "skills").iterdir()):
        if skill_dir.is_dir():
            install_skill_target(skill_dir, skills_root / skill_dir.name)

    for agent_file in sorted((staging_root / ".codex" / "agents").glob("*.toml")):
        install_agent_target(agent_file, agents_root / agent_file.name)

    update_managed_config_file(config_file, read_text(staging_root / ".codex" / "config.toml"))


def install_global(repo_root: Path, codex_home: Path) -> None:
    codex_home = resolve_path(codex_home)
    skills_root = default_global_skills_root()
    home_root = default_global_home_root()
    agents_root = default_global_agents_root(codex_home)
    config_file = default_global_config_file(codex_home)

    with tempfile.TemporaryDirectory(prefix="double-sdd-codex-global.") as temp_dir:
        staging_root = Path(temp_dir)
        render_codex_bundle(repo_root, staging_root, home_root)
        install_rendered_bundle(staging_root, skills_root, agents_root, config_file)

    print(f"Installed Codex skills to {skills_root}")
    print(f"Installed Codex subagents to {agents_root}")
    print(f"Updated {config_file} with managed double-SDD Codex config")


def uninstall_global(codex_home: Path) -> None:
    codex_home = resolve_path(codex_home)
    skills_root = default_global_skills_root()
    home_root = default_global_home_root()
    agents_root = default_global_agents_root(codex_home)
    config_file = default_global_config_file(codex_home)

    remove_managed_skill_targets(skills_root)
    remove_managed_agent_targets(agents_root)
    remove_managed_config_file(config_file)

    prune_empty_directories(skills_root, home_root)
    prune_empty_directories(agents_root, codex_home)

    print(f"Removed Codex skills from {skills_root}")
    print(f"Removed Codex subagents from {agents_root}")
    print(f"Removed managed double-SDD Codex config from {config_file}")


def sh_quote(value: str | Path) -> str:
    return "'" + str(value).replace("'", "'\"'\"'") + "'"


def ps_quote(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def cmd_escape(value: str | Path) -> str:
    return str(value).replace("%", "%%").replace('"', '""')


def build_shell_uninstaller(
    project_root: Path,
    artifact_root: Path,
    skills_root: Path,
    agents_root: Path,
    config_file: Path,
) -> str:
    return textwrap.dedent(
        f"""\
        #!/usr/bin/env bash

        set -euo pipefail

        PROJECT_ROOT={sh_quote(project_root)}
        ARTIFACT_ROOT={sh_quote(artifact_root)}
        SKILLS_ROOT={sh_quote(skills_root)}
        AGENTS_ROOT={sh_quote(agents_root)}
        CONFIG_FILE={sh_quote(config_file)}
        CONFIG_ROOT_MARKER_START={sh_quote(CONFIG_ROOT_MARKER_START)}
        CONFIG_ROOT_MARKER_END={sh_quote(CONFIG_ROOT_MARKER_END)}
        CONFIG_AGENTS_MARKER_START={sh_quote(CONFIG_AGENTS_MARKER_START)}
        CONFIG_AGENTS_MARKER_END={sh_quote(CONFIG_AGENTS_MARKER_END)}
        EXCLUDE_MARKER_START={sh_quote(EXCLUDE_MARKER_START)}
        EXCLUDE_MARKER_END={sh_quote(EXCLUDE_MARKER_END)}
        SKILL_OWNER_MARKER={sh_quote(SKILL_OWNER_MARKER)}
        SKILL_OWNER_VALUE={sh_quote(SKILL_OWNER_VALUE)}
        CUSTOM_AGENT_MARKER={sh_quote(CUSTOM_AGENT_MARKER)}

        remove_managed_block_file() {{
            local path="$1"
            local start="$2"
            local end="$3"
            local tmp_file

            if [ ! -f "$path" ]; then
                return 0
            fi

            tmp_file="$(mktemp "${{TMPDIR:-/tmp}}/double-sdd-config.XXXXXX")"
            awk -v start="$start" -v end="$end" '
                $0 == start {{ skip = 1; next }}
                $0 == end {{ skip = 0; next }}
                !skip {{ print }}
            ' "$path" > "$tmp_file"
            mv "$tmp_file" "$path"
        }}

        remove_managed_skills() {{
            local candidate
            local marker
            local owner

            [ -d "$SKILLS_ROOT" ] || return 0
            for candidate in "$SKILLS_ROOT"/*; do
                [ -d "$candidate" ] || continue
                marker="$candidate/$SKILL_OWNER_MARKER"
                [ -f "$marker" ] || continue
                owner="$(cat "$marker" 2>/dev/null || true)"
                if [ "$owner" = "$SKILL_OWNER_VALUE" ]; then
                    rm -rf "$candidate"
                fi
            done
        }}

        remove_managed_agents() {{
            local candidate
            local first_line

            [ -d "$AGENTS_ROOT" ] || return 0
            for candidate in "$AGENTS_ROOT"/*.toml; do
                [ -f "$candidate" ] || continue
                first_line="$(sed -n '1p' "$candidate" 2>/dev/null || true)"
                if [ "$first_line" = "$CUSTOM_AGENT_MARKER" ]; then
                    rm -f "$candidate"
                fi
            done
        }}

        prune_empty_directories() {{
            local path="$1"
            local stop="$2"

            while [ "$path" != "$stop" ] && [ "$path" != "/" ]; do
                rmdir "$path" 2>/dev/null || break
                path="$(dirname "$path")"
            done
        }}

        remove_git_exclude() {{
            if ! git -C "$PROJECT_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
                return 0
            fi

            local exclude_file
            local tmp_file
            exclude_file="$(cd "$PROJECT_ROOT" && git rev-parse --git-path info/exclude)"
            case "$exclude_file" in
                /*) ;;
                *) exclude_file="${{PROJECT_ROOT}}/${{exclude_file}}" ;;
            esac

            if [ ! -f "$exclude_file" ]; then
                return 0
            fi

            tmp_file="$(mktemp "${{TMPDIR:-/tmp}}/double-sdd-exclude.XXXXXX")"
            awk -v start="$EXCLUDE_MARKER_START" -v end="$EXCLUDE_MARKER_END" '
                $0 == start {{ skip = 1; next }}
                $0 == end {{ skip = 0; next }}
                !skip {{ print }}
            ' "$exclude_file" > "$tmp_file"
            mv "$tmp_file" "$exclude_file"
        }}

        remove_managed_block_file "$CONFIG_FILE" "$CONFIG_ROOT_MARKER_START" "$CONFIG_ROOT_MARKER_END"
        remove_managed_block_file "$CONFIG_FILE" "$CONFIG_AGENTS_MARKER_START" "$CONFIG_AGENTS_MARKER_END"
        remove_managed_skills
        remove_managed_agents
        prune_empty_directories "$SKILLS_ROOT" "$PROJECT_ROOT"
        prune_empty_directories "$AGENTS_ROOT" "$PROJECT_ROOT"
        remove_git_exclude

        printf 'Removing project-local double-SDD helpers from %s\\n' "$ARTIFACT_ROOT"
        exec /bin/sh -c 'rm -rf "$1"' sh "$ARTIFACT_ROOT"
        """
    )


def build_cmd_uninstaller() -> str:
    return textwrap.dedent(
        """\
        @echo off
        setlocal

        "%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1" %*
        """
    )


def build_ps_uninstaller(
    project_root: Path,
    artifact_root: Path,
    skills_root: Path,
    agents_root: Path,
    config_file: Path,
) -> str:
    cleanup_artifact_root = cmd_escape(artifact_root)
    return textwrap.dedent(
        f"""\
        Set-StrictMode -Version Latest
        $ErrorActionPreference = 'Stop'

        $ProjectRoot = {ps_quote(project_root)}
        $ArtifactRoot = {ps_quote(artifact_root)}
        $SkillsRoot = {ps_quote(skills_root)}
        $AgentsRoot = {ps_quote(agents_root)}
        $ConfigFile = {ps_quote(config_file)}
        $ConfigRootMarkerStart = {ps_quote(CONFIG_ROOT_MARKER_START)}
        $ConfigRootMarkerEnd = {ps_quote(CONFIG_ROOT_MARKER_END)}
        $ConfigAgentsMarkerStart = {ps_quote(CONFIG_AGENTS_MARKER_START)}
        $ConfigAgentsMarkerEnd = {ps_quote(CONFIG_AGENTS_MARKER_END)}
        $ExcludeMarkerStart = {ps_quote(EXCLUDE_MARKER_START)}
        $ExcludeMarkerEnd = {ps_quote(EXCLUDE_MARKER_END)}
        $SkillOwnerMarker = {ps_quote(SKILL_OWNER_MARKER)}
        $SkillOwnerValue = {ps_quote(SKILL_OWNER_VALUE)}
        $CustomAgentMarker = {ps_quote(CUSTOM_AGENT_MARKER)}

        function Write-Utf8File([string]$Path, [string]$Content) {{
            $directory = Split-Path -Parent $Path
            if ($directory) {{
                New-Item -ItemType Directory -Force -Path $directory | Out-Null
            }}

            $encoding = New-Object System.Text.UTF8Encoding($false)
            [System.IO.File]::WriteAllText($Path, $Content, $encoding)
        }}

        function Remove-ManagedBlockText([string]$Content, [string]$StartMarker, [string]$EndMarker) {{
            $result = New-Object System.Collections.Generic.List[string]
            $skip = $false

            foreach ($line in ($Content -split "`r?`n")) {{
                if ($line -eq $StartMarker) {{
                    $skip = $true
                    continue
                }}

                if ($line -eq $EndMarker) {{
                    $skip = $false
                    continue
                }}

                if (-not $skip) {{
                    $null = $result.Add($line)
                }}
            }}

            while ($result.Count -gt 0 -and $result[$result.Count - 1] -eq '') {{
                $result.RemoveAt($result.Count - 1)
            }}

            return [string]::Join("`n", $result)
        }}

        function Remove-ManagedBlockFile([string]$Path, [string]$StartMarker, [string]$EndMarker) {{
            if (-not (Test-Path -LiteralPath $Path)) {{
                return
            }}

            $existing = Get-Content -LiteralPath $Path -Raw
            $cleaned = Remove-ManagedBlockText -Content $existing -StartMarker $StartMarker -EndMarker $EndMarker
            if ($cleaned.Length -gt 0) {{
                $cleaned = $cleaned.TrimEnd("`r", "`n") + "`n"
            }}

            Write-Utf8File -Path $Path -Content $cleaned
        }}

        function Remove-ManagedSkills() {{
            if (-not (Test-Path -LiteralPath $SkillsRoot)) {{
                return
            }}

            foreach ($candidate in Get-ChildItem -LiteralPath $SkillsRoot -Force -ErrorAction SilentlyContinue) {{
                if (-not $candidate.PSIsContainer) {{
                    continue
                }}

                $markerPath = Join-Path $candidate.FullName $SkillOwnerMarker
                if (-not (Test-Path -LiteralPath $markerPath)) {{
                    continue
                }}

                $owner = (Get-Content -LiteralPath $markerPath -Raw).Trim()
                if ($owner -eq $SkillOwnerValue) {{
                    Remove-Item -LiteralPath $candidate.FullName -Recurse -Force
                }}
            }}
        }}

        function Remove-ManagedAgents() {{
            if (-not (Test-Path -LiteralPath $AgentsRoot)) {{
                return
            }}

            foreach ($candidate in Get-ChildItem -LiteralPath $AgentsRoot -Filter '*.toml' -File -ErrorAction SilentlyContinue) {{
                $firstLine = Get-Content -LiteralPath $candidate.FullName -TotalCount 1 -ErrorAction SilentlyContinue | Select-Object -First 1
                if ($null -ne $firstLine -and $firstLine -eq $CustomAgentMarker) {{
                    Remove-Item -LiteralPath $candidate.FullName -Force
                }}
            }}
        }}

        function Remove-EmptyDirectories([string]$StartPath, [string]$StopPath) {{
            $path = $StartPath
            while ($path -and $path -ne $StopPath) {{
                if (-not (Test-Path -LiteralPath $path)) {{
                    $path = Split-Path -Parent $path
                    continue
                }}

                $items = Get-ChildItem -LiteralPath $path -Force -ErrorAction SilentlyContinue
                if ($items.Count -gt 0) {{
                    break
                }}

                Remove-Item -LiteralPath $path -Force
                $path = Split-Path -Parent $path
            }}
        }}

        function Get-GitExcludePath() {{
            if (-not (Get-Command git -ErrorAction SilentlyContinue)) {{
                return $null
            }}

            & git -C $ProjectRoot rev-parse --is-inside-work-tree 1>$null 2>$null
            if ($LASTEXITCODE -ne 0) {{
                return $null
            }}

            $gitPath = (& git -C $ProjectRoot rev-parse --git-path info/exclude 2>$null | Select-Object -First 1)
            if (-not $gitPath) {{
                return $null
            }}

            $gitPath = $gitPath.Trim()
            if ([System.IO.Path]::IsPathRooted($gitPath)) {{
                return $gitPath
            }}

            return Join-Path $ProjectRoot $gitPath
        }}

        function Remove-GitExcludeBlock() {{
            $excludePath = Get-GitExcludePath
            if (-not $excludePath -or -not (Test-Path -LiteralPath $excludePath)) {{
                return
            }}

            $existing = Get-Content -LiteralPath $excludePath -Raw
            $cleaned = Remove-ManagedBlockText -Content $existing -StartMarker $ExcludeMarkerStart -EndMarker $ExcludeMarkerEnd
            if ($cleaned.Length -gt 0) {{
                $cleaned = $cleaned.TrimEnd("`r", "`n") + "`n"
            }}

            Write-Utf8File -Path $excludePath -Content $cleaned
        }}

        Remove-ManagedBlockFile -Path $ConfigFile -StartMarker $ConfigRootMarkerStart -EndMarker $ConfigRootMarkerEnd
        Remove-ManagedBlockFile -Path $ConfigFile -StartMarker $ConfigAgentsMarkerStart -EndMarker $ConfigAgentsMarkerEnd
        Remove-ManagedSkills
        Remove-ManagedAgents
        Remove-EmptyDirectories -StartPath $SkillsRoot -StopPath $ProjectRoot
        Remove-EmptyDirectories -StartPath $AgentsRoot -StopPath $ProjectRoot
        Remove-GitExcludeBlock

        Write-Host "Removing project-local double-SDD helpers from $ArtifactRoot"

        $cleanupPath = Join-Path ([System.IO.Path]::GetTempPath()) ("double-sdd-uninstall-" + [Guid]::NewGuid().ToString() + ".cmd")
        $cleanupContent = "@echo off`r`nping 127.0.0.1 -n 2 >nul`r`nrmdir /s /q ""{cleanup_artifact_root}""`r`ndel ""%~f0""`r`n"
        Write-Utf8File -Path $cleanupPath -Content $cleanupContent

        Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $cleanupPath -WindowStyle Hidden | Out-Null
        """
    )


def write_project_helpers(
    project_root: Path,
    artifact_root: Path,
    skills_root: Path,
    agents_root: Path,
    config_file: Path,
) -> None:
    shell_uninstaller = artifact_root / "uninstall"
    cmd_uninstaller = artifact_root / "uninstall.cmd"
    ps_uninstaller = artifact_root / "uninstall.ps1"

    write_text(
        shell_uninstaller,
        build_shell_uninstaller(project_root, artifact_root, skills_root, agents_root, config_file),
    )
    write_text(cmd_uninstaller, build_cmd_uninstaller())
    write_text(
        ps_uninstaller,
        build_ps_uninstaller(project_root, artifact_root, skills_root, agents_root, config_file),
    )

    make_executable(shell_uninstaller)


def git_exclude_path(project_root: Path) -> Path | None:
    try:
        subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "--is-inside-work-tree"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    result = subprocess.run(
        ["git", "-C", str(project_root), "rev-parse", "--git-path", "info/exclude"],
        check=True,
        capture_output=True,
        text=True,
    )
    relative_path = result.stdout.strip()
    if not relative_path:
        return None

    candidate = Path(relative_path)
    return candidate if candidate.is_absolute() else project_root / candidate


def ensure_git_exclude(project_root: Path, artifact_root: Path) -> None:
    default_artifact_root = project_root / ".double-sdd"
    if resolve_path(artifact_root) != resolve_path(default_artifact_root):
        return

    exclude_path = git_exclude_path(project_root)
    if exclude_path is None:
        return

    existing = read_text(exclude_path).rstrip("\n")
    if EXCLUDE_MARKER_START in existing.splitlines():
        return

    sections: list[str] = []
    if existing:
        sections.append(existing)
    sections.append("\n".join([EXCLUDE_MARKER_START, ".double-sdd/", EXCLUDE_MARKER_END]))
    write_text(exclude_path, "\n\n".join(sections) + "\n")


def remove_git_exclude(project_root: Path) -> None:
    exclude_path = git_exclude_path(project_root)
    if exclude_path is None or not exclude_path.is_file():
        return

    cleaned = strip_managed_block(read_text(exclude_path), EXCLUDE_MARKER_START, EXCLUDE_MARKER_END)
    if cleaned:
        write_text(exclude_path, cleaned.rstrip("\n") + "\n")
    else:
        write_text(exclude_path, "")


def cleanup_project_artifact_root(artifact_root: Path) -> None:
    for child_name in [
        "codex-home",
        "codex",
        "codex.cmd",
        "codex.ps1",
        "uninstall",
        "uninstall.cmd",
        "uninstall.ps1",
    ]:
        remove_path(artifact_root / child_name)


def install_project(
    repo_root: Path,
    project_root: Path,
    artifact_root: Path | None = None,
) -> None:
    project_root = resolve_path(project_root)
    artifact_root = resolve_path(artifact_root or (project_root / ".double-sdd"))
    skills_root = default_project_skills_root(project_root)
    agents_root = default_project_agents_root(project_root)
    config_file = default_project_config_file(project_root)

    artifact_root.mkdir(parents=True, exist_ok=True)
    cleanup_project_artifact_root(artifact_root)

    with tempfile.TemporaryDirectory(prefix="double-sdd-codex-project.") as temp_dir:
        staging_root = Path(temp_dir)
        render_codex_bundle(repo_root, staging_root, project_root)
        install_rendered_bundle(staging_root, skills_root, agents_root, config_file)

    write_project_helpers(project_root, artifact_root, skills_root, agents_root, config_file)
    ensure_git_exclude(project_root, artifact_root)

    print(f"Installed project Codex skills to {skills_root}")
    print(f"Installed project Codex subagents to {agents_root}")
    print(f"Updated {config_file} with managed double-SDD Codex config")
    print(f"Created uninstaller at {artifact_root / 'uninstall'}")
    print(f"Created Windows uninstaller at {artifact_root / 'uninstall.cmd'}")
    print("Start Codex for this project by running `codex` inside the project root")


def uninstall_project(
    project_root: Path,
    artifact_root: Path | None = None,
) -> None:
    project_root = resolve_path(project_root)
    artifact_root = resolve_path(artifact_root or (project_root / ".double-sdd"))
    skills_root = default_project_skills_root(project_root)
    agents_root = default_project_agents_root(project_root)
    config_file = default_project_config_file(project_root)

    remove_managed_skill_targets(skills_root)
    remove_managed_agent_targets(agents_root)
    remove_managed_config_file(config_file)
    remove_git_exclude(project_root)
    prune_empty_directories(skills_root, project_root)
    prune_empty_directories(agents_root, project_root)
    cleanup_project_artifact_root(artifact_root)
    remove_path(artifact_root)

    print(f"Removed project Codex skills from {skills_root}")
    print(f"Removed project Codex subagents from {agents_root}")
    print(f"Removed managed double-SDD Codex config from {config_file}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_global_parser = subparsers.add_parser("install-global")
    install_global_parser.add_argument("--repo-root", required=True, type=Path)
    install_global_parser.add_argument("--codex-home", type=Path)

    uninstall_global_parser = subparsers.add_parser("uninstall-global")
    uninstall_global_parser.add_argument("--codex-home", type=Path)

    install_project_parser = subparsers.add_parser("install-project")
    install_project_parser.add_argument("--repo-root", required=True, type=Path)
    install_project_parser.add_argument("--project-root", required=True, type=Path)
    install_project_parser.add_argument("--artifact-root", type=Path)

    uninstall_project_parser = subparsers.add_parser("uninstall-project")
    uninstall_project_parser.add_argument("--project-root", required=True, type=Path)
    uninstall_project_parser.add_argument("--artifact-root", type=Path)

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.command == "install-global":
        install_global(resolve_path(args.repo_root), args.codex_home or default_codex_home())
        return

    if args.command == "uninstall-global":
        uninstall_global(args.codex_home or default_codex_home())
        return

    if args.command == "install-project":
        install_project(
            repo_root=resolve_path(args.repo_root),
            project_root=args.project_root,
            artifact_root=args.artifact_root,
        )
        return

    if args.command == "uninstall-project":
        uninstall_project(
            project_root=args.project_root,
            artifact_root=args.artifact_root,
        )
        return

    raise RuntimeError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    main()
