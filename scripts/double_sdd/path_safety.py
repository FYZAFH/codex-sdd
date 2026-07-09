from __future__ import annotations

import os
import stat
from pathlib import Path


class PathSafetyError(ValueError):
    """Raised when a workflow path fails a safety invariant."""


def is_reparse_point(st: os.stat_result) -> bool:
    return bool(
        getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        and (getattr(st, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    )


def is_mount_point(path: Path) -> bool:
    try:
        return path.is_mount()
    except OSError as exc:
        raise PathSafetyError(f"{path} could not be mount-point checked before use: {exc}") from exc


def reject_link_or_reparse(path: Path, label: str, allow_missing: bool = False):
    try:
        st = path.lstat()
    except FileNotFoundError:
        if allow_missing:
            return None
        raise
    except OSError as exc:
        raise PathSafetyError(f"{label} could not be lstat-checked before use: {exc}") from exc
    if stat.S_ISLNK(st.st_mode) or is_reparse_point(st):
        raise PathSafetyError(f"{label} must not be a symlink, junction, mount point, or reparse point")
    return st


def ensure_contained(path: Path, parent: Path) -> bool:
    child = os.path.normcase(str(path.resolve(strict=False)))
    base = os.path.normcase(str(parent.resolve(strict=False)))
    try:
        return os.path.commonpath([child, base]) == base
    except ValueError:
        return False


def validate_worktrees_anchor(repo: Path) -> Path:
    anchor = repo / ".worktrees"
    st = reject_link_or_reparse(anchor, ".worktrees anchor", allow_missing=True)
    if st is not None:
        if not stat.S_ISDIR(st.st_mode):
            raise PathSafetyError(".worktrees must be a repo-local directory")
        if is_mount_point(anchor):
            raise PathSafetyError(".worktrees anchor must not be a symlink, junction, mount point, or reparse point")
    if st is None:
        resolved_parent = anchor.parent.resolve(strict=True)
        if os.path.normcase(str(resolved_parent)) != os.path.normcase(str(repo.resolve())):
            raise PathSafetyError("missing .worktrees anchor must have the resolved repo root as its direct parent")
    resolved = anchor.resolve(strict=False)
    if not ensure_contained(resolved, repo.resolve()):
        raise PathSafetyError("resolved .worktrees anchor must remain under the repo root")
    return resolved
