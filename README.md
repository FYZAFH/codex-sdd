# codex-sdd

Codex-native **double-SDD** workflow for Codex CLI.

double-SDD means:
- Specification-Driven Development
- Subagent-Driven Development

This repository is Codex-only. It installs native Codex assets into:
- project scope: `.agents/skills/`, `.codex/config.toml`, `.codex/agents/`
- user scope: `~/.agents/skills/`, `~/.codex/config.toml`, `~/.codex/agents/`

## Install

Requirements:
- macOS / Linux: `bash`, `python3`
- Windows: `PowerShell`, `Python 3`
- Bootstrap flows also require `git`

Project-local install, macOS / Linux:

```bash
cd ~/example_sound
bash <(curl -fsSL https://raw.githubusercontent.com/FYZAFH/codex-sdd/main/scripts/bootstrap-codex-project.sh)
codex
```

Project-local install, Windows PowerShell:

```powershell
cd ~\example_sound
irm https://raw.githubusercontent.com/FYZAFH/codex-sdd/main/scripts/bootstrap-codex-project.ps1 | iex
codex
```

Project-local uninstall:

```bash
./.double-sdd/uninstall
```

```powershell
.\.double-sdd\uninstall.ps1
```

Global install, macOS / Linux:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/FYZAFH/codex-sdd/main/scripts/bootstrap-codex-global.sh)
codex
```

Global install, Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/FYZAFH/codex-sdd/main/scripts/bootstrap-codex-global.ps1 | iex
codex
```

## Source Layout

- `codex/config.toml` — orchestrator instructions and registered subagents
- `codex/agents/*.toml` — Codex custom subagents
- `codex/skills/*/SKILL.md` — Codex-native skills
- `scripts/` — install, uninstall, bootstrap, and render helpers
- `tests/shared/` — Codex install/render validation

## Validation

```bash
python3 -m py_compile scripts/render-platform-bundle.py scripts/codex_installer.py
bash tests/shared/test-platform-bundle.sh
bash tests/shared/test-codex-install.sh
bash tests/shared/test-codex-project-install.sh
```

## Notes

- Installed subagents have their skills disabled explicitly through `[[skills.config]]` entries.

## License

MIT License — see [LICENSE](LICENSE).
