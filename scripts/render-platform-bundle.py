#!/usr/bin/env python3

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def copy_tree(src_root: Path, dst_root: Path) -> None:
    for src_path in sorted(src_root.rglob("*")):
        relpath = src_path.relative_to(src_root)
        dst_path = dst_root / relpath

        if src_path.is_dir():
            dst_path.mkdir(parents=True, exist_ok=True)
            continue

        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dst_path)


def toml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def codex_skill_dirs() -> list[Path]:
    return sorted(path for path in (REPO_ROOT / "codex" / "skills").iterdir() if path.is_dir())


def render_codex_agent(source_agent: Path, logical_root: Path) -> str:
    source_text = source_agent.read_text(encoding="utf-8").rstrip("\n")
    skill_blocks = []

    for skill_dir in codex_skill_dirs():
        skill_path = (logical_root / ".agents" / "skills" / skill_dir.name / "SKILL.md").as_posix()
        skill_blocks.append(
            "\n".join(
                [
                    "[[skills.config]]",
                    f"path = {toml_quote(skill_path)}",
                    "enabled = false",
                ]
            )
        )

    return source_text + "\n\n" + "\n\n".join(skill_blocks) + "\n"


def render_codex_bundle(output_dir: Path, logical_root: Path | None = None) -> None:
    logical_root = logical_root or output_dir
    copy_tree(REPO_ROOT / "codex" / "skills", output_dir / ".agents" / "skills")
    agents_output_dir = output_dir / ".codex" / "agents"
    agents_output_dir.mkdir(parents=True, exist_ok=True)

    for source_agent in sorted((REPO_ROOT / "codex" / "agents").glob("*.toml")):
        rendered_agent = render_codex_agent(source_agent, logical_root)
        (agents_output_dir / source_agent.name).write_text(rendered_agent, encoding="utf-8")

    codex_dir = REPO_ROOT / "codex"
    (output_dir / ".codex" / "config.toml").write_text(
        (codex_dir / "config.toml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
def render_bundle(platform: str, output_dir: Path, logical_root: Path | None = None) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    if platform != "codex":
        raise ValueError(f"unsupported platform: {platform}")
    render_codex_bundle(output_dir, logical_root)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["codex"], required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--logical-root", type=Path)
    args = parser.parse_args()

    render_bundle(args.platform, args.output, args.logical_root)


if __name__ == "__main__":
    main()
