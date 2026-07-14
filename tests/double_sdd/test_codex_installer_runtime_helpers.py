from __future__ import annotations

from pathlib import Path

from scripts.codex_installer import (
    cleanup_global_runtime_helpers,
    cleanup_project_artifact_root,
    install_runtime_helpers,
)


def test_install_runtime_helpers_preserves_scripts_siblings(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    artifact_root = tmp_path / ".double-sdd"
    scripts_root = artifact_root / "scripts"
    scripts_root.mkdir(parents=True)
    keep_file = scripts_root / "keep.txt"
    init_file = scripts_root / "__init__.py"
    keep_file.write_text("keep\n", encoding="utf-8")
    init_file.write_text("# user package\n", encoding="utf-8")

    install_runtime_helpers(repo_root, artifact_root)

    assert keep_file.read_text(encoding="utf-8") == "keep\n"
    assert init_file.read_text(encoding="utf-8") == "# user package\n"
    assert (scripts_root / "double_sdd" / "setup_worktree.py").is_file()
    assert not (scripts_root / "install-codex-project.sh").exists()


def test_install_runtime_helpers_does_not_create_scripts_init(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    artifact_root = tmp_path / ".double-sdd"

    install_runtime_helpers(repo_root, artifact_root)

    assert not (artifact_root / "scripts" / "__init__.py").exists()
    assert (artifact_root / "scripts" / "double_sdd" / "__init__.py").is_file()


def test_project_cleanup_removes_only_managed_runtime_helper_package(tmp_path: Path) -> None:
    artifact_root = tmp_path / ".double-sdd"
    scripts_root = artifact_root / "scripts"
    helper_package = scripts_root / "double_sdd"
    helper_package.mkdir(parents=True)
    keep_file = scripts_root / "keep.txt"
    init_file = scripts_root / "__init__.py"
    keep_file.write_text("keep\n", encoding="utf-8")
    init_file.write_text("# user package\n", encoding="utf-8")
    (helper_package / "setup_worktree.py").write_text("", encoding="utf-8")

    cleanup_project_artifact_root(artifact_root)

    assert not helper_package.exists()
    assert keep_file.read_text(encoding="utf-8") == "keep\n"
    assert init_file.read_text(encoding="utf-8") == "# user package\n"


def test_global_cleanup_removes_only_managed_runtime_helper_package(tmp_path: Path) -> None:
    artifact_root = tmp_path / ".double-sdd"
    scripts_root = artifact_root / "scripts"
    helper_package = scripts_root / "double_sdd"
    helper_package.mkdir(parents=True)
    keep_file = scripts_root / "keep.txt"
    init_file = scripts_root / "__init__.py"
    keep_file.write_text("keep\n", encoding="utf-8")
    init_file.write_text("# user package\n", encoding="utf-8")
    (helper_package / "setup_worktree.py").write_text("", encoding="utf-8")

    cleanup_global_runtime_helpers(artifact_root)

    assert not helper_package.exists()
    assert keep_file.read_text(encoding="utf-8") == "keep\n"
    assert init_file.read_text(encoding="utf-8") == "# user package\n"
