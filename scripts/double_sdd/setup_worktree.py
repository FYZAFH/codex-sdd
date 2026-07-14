from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

if __package__ in (None, ""):
    helper_scripts_root = Path(__file__).resolve().parents[1]
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(helper_scripts_root))
    sys.path.insert(0, str(repo_root))

try:
    from scripts.double_sdd.metadata import (
        ACTIVE_STATUS,
        MetadataError,
        _validate_metadata_common_fields,
        find_single_preimplementation_metadata,
        metadata_relpath_for_run_id,
        read_metadata,
        validate_metadata_relpath,
        validate_reused_metadata,
    )
    from scripts.double_sdd.path_safety import (
        PathSafetyError,
        ensure_contained,
        is_mount_point,
        reject_link_or_reparse,
        validate_worktrees_anchor,
    )
except ModuleNotFoundError:
    from double_sdd.metadata import (
        ACTIVE_STATUS,
        MetadataError,
        _validate_metadata_common_fields,
        find_single_preimplementation_metadata,
        metadata_relpath_for_run_id,
        read_metadata,
        validate_metadata_relpath,
        validate_reused_metadata,
    )
    from double_sdd.path_safety import (
        PathSafetyError,
        ensure_contained,
        is_mount_point,
        reject_link_or_reparse,
        validate_worktrees_anchor,
    )


COMPLETED_OR_ABANDONED = frozenset(("completed", "abandoned"))
WINDOWS_RESERVED_BASENAMES = frozenset(
    ("con", "prn", "aux", "nul")
    + tuple(f"com{index}" for index in range(1, 10))
    + tuple(f"lpt{index}" for index in range(1, 10))
)
WINDOWS_INVALID_PATH_CHARS = frozenset('<>:"\\|?*')
PREEXISTING_TARGET_RECOVERY = (
    "manually verify and reconcile metadata, remove the stale branch/worktree after approval, "
    "or choose a new branch/path"
)


class SetupError(ValueError):
    """Raised when isolated worktree setup cannot proceed safely."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create the double-SDD isolated worktree.")
    parser.add_argument("--branch", required=True, help="feature branch to create for the implementation worktree")
    parser.add_argument(
        "--metadata-path",
        default="",
        help="repo-relative upstream metadata path, e.g. .worktrees/<run-id>.metadata.json",
    )
    parser.add_argument("--run-id", default="", help="filesystem-safe run id for direct/manual mode")
    parser.add_argument(
        "--no-upstream-metadata",
        action="store_true",
        help="create direct/manual metadata using --run-id instead of upstream metadata",
    )
    return parser


def success_payload(metadata_path: str, worktree_path: str, branch: str) -> str:
    return json.dumps(
        {
            "metadataPath": metadata_path,
            "worktreePath": worktree_path,
            "featureBranch": branch,
        }
    )


def determine_metadata_relpath(
    repo: Path,
    worktrees_dir: Path,
    metadata_path: str,
    run_id: str,
    no_upstream_metadata: bool,
) -> str:
    if metadata_path and (run_id or no_upstream_metadata):
        raise SetupError(
            "--metadata-path cannot be combined with --run-id or --no-upstream-metadata. "
            "Use the exact upstream metadata path by itself, or use direct/manual mode with --run-id."
        )
    if run_id and not no_upstream_metadata:
        raise SetupError("--run-id is valid only with --no-upstream-metadata.")

    try:
        if metadata_path:
            return validate_metadata_relpath(metadata_path, repo, worktrees_dir, require_existing=True)
        if no_upstream_metadata:
            if not run_id:
                raise SetupError("Direct/manual mode requires --run-id.")
            relpath = metadata_relpath_for_run_id(run_id)
            return validate_metadata_relpath(relpath, repo, worktrees_dir, require_existing=False)
        return find_single_preimplementation_metadata(repo, worktrees_dir)
    except MetadataError as exc:
        raise SetupError(str(exc)) from exc


def setup_worktree(
    branch: str,
    metadata_path: str = "",
    run_id: str = "",
    no_upstream_metadata: bool = False,
    cwd: str | os.PathLike[str] | None = None,
) -> dict[str, str]:
    if not isinstance(branch, str) or not branch.strip():
        raise SetupError("--branch must be a non-empty branch name")
    branch = branch.strip()
    git_cwd = Path(cwd).resolve() if cwd is not None else None

    git_dir = _run_git(["rev-parse", "--path-format=absolute", "--git-dir"], git_cwd)
    git_common_dir = _run_git(["rev-parse", "--path-format=absolute", "--git-common-dir"], git_cwd)
    if _norm_path(git_dir) != _norm_path(git_common_dir):
        raise SetupError(
            "Setup must run from the original main worktree. This checkout is a linked worktree; "
            "return to the original main worktree and retry."
        )

    repo = Path(_run_git(["rev-parse", "--show-toplevel"], git_cwd)).resolve()
    worktrees_dir = validate_worktrees_anchor(repo)
    _validate_branch_ref(repo, branch)
    worktree_relpath = _worktree_relpath_for_branch(branch)
    worktree_path = _repo_path_from_posix(repo, worktree_relpath)
    metadata_relpath = determine_metadata_relpath(
        repo,
        worktrees_dir,
        metadata_path,
        run_id,
        no_upstream_metadata,
    )

    _require_git_ignored(repo, ".worktrees/")
    _require_git_ignored(repo, metadata_relpath)
    try:
        worktrees_dir.mkdir(exist_ok=True)
    except OSError as exc:
        raise SetupError(
            f"failed to create repo-local .worktrees directory at {worktrees_dir}: {exc}. "
            "Repair permissions or remove the blocking path before rerunning setup."
        ) from exc
    worktrees_dir = validate_worktrees_anchor(repo)

    metadata_abspath = _repo_path_from_posix(repo, metadata_relpath)
    direct_target_prechecked = False
    if no_upstream_metadata:
        branch_exists = _target_branch_exists(repo, branch)
        worktree_exists = _target_path_exists(worktree_path, "worktree path")
        if branch_exists or worktree_exists:
            _reject_direct_existing_target(branch_exists, worktree_exists)
        _validate_worktree_target(repo, worktrees_dir, worktree_path, "worktree path", require_existing=False)
        direct_target_prechecked = True
        data = _create_direct_metadata(repo, worktrees_dir, metadata_abspath, metadata_relpath, run_id)
    else:
        data = _load_reused_metadata(repo, worktrees_dir, metadata_abspath, metadata_relpath)

    main_base = data["mainBase"]
    _validate_main_base(repo, main_base)

    if direct_target_prechecked:
        branch_exists = False
        worktree_exists = False
    else:
        branch_exists = _target_branch_exists(repo, branch)
        worktree_exists = _target_path_exists(worktree_path, "worktree path")
    if branch_exists or worktree_exists:
        _reject_existing_target_for_repair(
            repo,
            worktrees_dir,
            metadata_abspath,
            metadata_relpath,
            worktree_path,
            worktree_relpath,
            branch,
            branch_exists,
            worktree_exists,
            main_base,
            data,
            git_common_dir,
        )
    else:
        if not direct_target_prechecked:
            _validate_worktree_target(repo, worktrees_dir, worktree_path, "worktree path", require_existing=False)
        _run_git(["worktree", "add", str(worktree_path), "-b", branch, main_base], repo)

        try:
            _post_add_update_metadata(
                repo,
                worktrees_dir,
                metadata_abspath,
                metadata_relpath,
                worktree_path,
                worktree_relpath,
                branch,
                data["runId"],
                main_base,
            )
        except SetupError as exc:
            raise SetupError(
                "git worktree add succeeded but metadata update failed; leaving the just-created worktree "
                "and branch in place for inspection. Stop before dispatching agents. Reconcile or replace "
                f"the metadata file, or remove the worktree/branch only after verifying them. Details: {exc}"
            ) from exc

    return {
        "metadataPath": metadata_relpath,
        "worktreePath": worktree_relpath,
        "featureBranch": branch,
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    try:
        result = setup_worktree(
            branch=args.branch,
            metadata_path=args.metadata_path,
            run_id=args.run_id,
            no_upstream_metadata=args.no_upstream_metadata,
        )
    except (SetupError, PathSafetyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(
        success_payload(
            metadata_path=result["metadataPath"],
            worktree_path=result["worktreePath"],
            branch=result["featureBranch"],
        )
    )
    return 0


def _run_git(args: list[str], cwd: Path | None) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise SetupError(f"failed to run git {' '.join(args)}: {exc}") from exc
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        suffix = f": {details}" if details else ""
        raise SetupError(f"git {' '.join(args)} failed{suffix}")
    return result.stdout.strip()


def _git_success(args: list[str], cwd: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise SetupError(f"failed to run git {' '.join(args)}: {exc}") from exc
    return result.returncode == 0


def _norm_path(value: str) -> str:
    return os.path.normcase(str(Path(value).resolve(strict=False)))


def _repo_path_from_posix(repo: Path, relpath: str) -> Path:
    return repo / Path(*PurePosixPath(relpath).parts)


def _require_git_ignored(repo: Path, relpath: str) -> None:
    if not _git_success(["check-ignore", "-q", "--", relpath], repo):
        raise SetupError(
            f"{relpath} must be ignored by git before setup writes runtime metadata or worktrees. "
            "Add the ignore rule or reconcile repository tracking before continuing."
        )


def _load_reused_metadata(repo: Path, worktrees_dir: Path, metadata_path: Path, metadata_relpath: str) -> dict[str, Any]:
    try:
        validate_metadata_relpath(metadata_relpath, repo, worktrees_dir, require_existing=True)
        return validate_reused_metadata(read_metadata(metadata_path), metadata_relpath, repo, worktrees_dir)
    except MetadataError as exc:
        raise SetupError(str(exc)) from exc


def _create_direct_metadata(
    repo: Path,
    worktrees_dir: Path,
    metadata_path: Path,
    metadata_relpath: str,
    run_id: str,
) -> dict[str, Any]:
    if metadata_path.exists():
        raise SetupError(
            "Direct/manual metadata target already exists. Choose a new --run-id, pass the exact "
            "--metadata-path for upstream metadata, or reconcile the existing file before continuing."
        )
    _ensure_direct_entry_clean(repo, worktrees_dir)

    main_branch = _run_git(["branch", "--show-current"], repo).strip()
    if not main_branch:
        raise SetupError(
            "Detached HEAD or empty branch name; stop and ask for an explicit base branch before "
            "creating direct-entry metadata."
        )
    main_base = _run_git(["rev-parse", "--verify", "HEAD"], repo)
    _validate_main_base(repo, main_base)
    data: dict[str, Any] = {
        "schemaVersion": 1,
        "runId": run_id,
        "status": ACTIVE_STATUS,
        "mainBranch": main_branch,
        "mainBase": main_base,
        "featureBranch": None,
        "worktreePath": None,
        "metadataPath": metadata_relpath,
        "preexistingTrackedCheckpoint": None,
        "temporaryCheckpoints": [],
        "preexistingUntracked": [],
        "preexistingIgnored": [],
    }
    _write_metadata(metadata_path, data)
    try:
        return validate_reused_metadata(read_metadata(metadata_path), metadata_relpath, repo, worktrees_dir)
    except MetadataError as exc:
        raise SetupError(str(exc)) from exc


def _ensure_direct_entry_clean(repo: Path, worktrees_dir: Path) -> None:
    tracked = _split_git_lines(_run_git(["status", "--porcelain=v1", "--untracked-files=no"], repo))
    untracked = _split_git_lines(_run_git(["ls-files", "--others", "--exclude-standard"], repo))
    ignored = _split_git_lines(_run_git(["ls-files", "--others", "--ignored", "--exclude-standard"], repo))
    ignored_with_directories = _split_git_lines(
        _run_git(["ls-files", "--others", "--ignored", "--exclude-standard", "--directory"], repo)
    )
    worktrees_children = _blocking_direct_worktrees_children(repo, worktrees_dir)
    empty_untracked_directories = _blocking_empty_directories(repo, worktrees_dir)

    blocking_ignored = _blocking_ignored_entries(repo, worktrees_dir, ignored, ignored_with_directories)
    if tracked or untracked or blocking_ignored or worktrees_children or empty_untracked_directories:
        raise SetupError(
            "Direct-entry metadata creation cannot safely record preexisting tracked/untracked/ignored state; "
            "run the upstream recording step (`writing-specs`) first."
        )


def _split_git_lines(output: str) -> list[str]:
    return [line for line in output.splitlines() if line]


def _blocking_direct_worktrees_children(repo: Path, worktrees_dir: Path) -> list[str]:
    if not worktrees_dir.exists():
        return []
    try:
        children = sorted(worktrees_dir.iterdir(), key=lambda child: child.name)
    except OSError as exc:
        raise SetupError(f"could not inspect .worktrees contents before direct-entry setup: {exc}") from exc

    blocking: list[str] = []
    for child in children:
        relpath = Path(os.path.relpath(child, repo)).as_posix()
        try:
            child_stat = reject_link_or_reparse(child, ".worktrees child", allow_missing=False)
        except (FileNotFoundError, PathSafetyError):
            blocking.append(relpath)
            continue
        if stat.S_ISDIR(child_stat.st_mode):
            blocking.append(relpath)
            continue
        if not _is_allowed_retained_metadata(repo, worktrees_dir, relpath):
            blocking.append(relpath)
    return blocking


def _blocking_empty_directories(repo: Path, worktrees_dir: Path) -> list[str]:
    blocking: list[str] = []

    def visit(directory: Path) -> None:
        try:
            entries = sorted(directory.iterdir(), key=lambda child: child.name)
        except OSError as exc:
            raise SetupError(f"could not inspect repository directories before direct-entry setup: {exc}") from exc

        counted_entries: list[Path] = []
        for entry in entries:
            if directory == repo and entry.name == ".git":
                continue
            if directory == repo and entry == worktrees_dir:
                continue
            counted_entries.append(entry)
            relpath = Path(os.path.relpath(entry, repo)).as_posix()

            try:
                entry_stat = reject_link_or_reparse(entry, "repository directory entry", allow_missing=False)
            except FileNotFoundError:
                continue
            except PathSafetyError:
                blocking.append(relpath)
                continue
            if stat.S_ISDIR(entry_stat.st_mode):
                try:
                    if is_mount_point(entry):
                        blocking.append(relpath)
                        continue
                except PathSafetyError:
                    blocking.append(relpath)
                    continue
                visit(entry)

        if directory != repo and not counted_entries:
            blocking.append(Path(os.path.relpath(directory, repo)).as_posix())

    visit(repo)
    return blocking


def _blocking_ignored_entries(
    repo: Path,
    worktrees_dir: Path,
    ignored: list[str],
    ignored_with_directories: list[str],
) -> list[str]:
    blocking: list[str] = []
    seen: set[str] = set()
    for ignored_path in [*ignored, *ignored_with_directories]:
        if ignored_path in seen:
            continue
        seen.add(ignored_path)
        if _is_allowed_retained_metadata(repo, worktrees_dir, ignored_path):
            continue
        if _is_worktrees_directory_aggregate(ignored_path):
            continue
        blocking.append(ignored_path)
    return blocking


def _is_worktrees_directory_aggregate(ignored_path: str) -> bool:
    if "\\" in ignored_path:
        return False
    rel = PurePosixPath(ignored_path.rstrip("/"))
    return rel.parts == (".worktrees",)


def _is_allowed_retained_metadata(repo: Path, worktrees_dir: Path, ignored_path: str) -> bool:
    rel = PurePosixPath(ignored_path)
    if (
        "\\" in ignored_path
        or rel.parts[:1] != (".worktrees",)
        or rel.parent != PurePosixPath(".worktrees")
        or len(rel.parts) != 2
        or not rel.name.endswith(".metadata.json")
    ):
        return False

    try:
        metadata_relpath = validate_metadata_relpath(ignored_path, repo, worktrees_dir, require_existing=True)
        metadata_path = _repo_path_from_posix(repo, metadata_relpath)
        data = _validate_metadata_common_fields(read_metadata(metadata_path), metadata_relpath, repo, worktrees_dir)
    except MetadataError:
        return False
    return data["status"] in COMPLETED_OR_ABANDONED


def _validate_main_base(repo: Path, main_base: str) -> None:
    if not isinstance(main_base, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", main_base):
        raise SetupError("mainBase must be a 40-character commit SHA before git worktree add.")
    _run_git(["rev-parse", "--verify", f"{main_base}^{{commit}}"], repo)


def _validate_branch_ref(repo: Path, branch: str) -> None:
    try:
        result = subprocess.run(
            ["git", "check-ref-format", "--branch", branch],
            cwd=repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise SetupError(f"failed to validate branch name {branch!r}: {exc}") from exc
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        message = f"invalid branch name {branch!r}; choose a valid Git branch name before setup writes metadata."
        if details:
            message = f"{message} Git said: {details}"
        raise SetupError(message)


def _worktree_relpath_for_branch(branch: str) -> str:
    relpath = f".worktrees/{branch}"
    if "\\" in relpath:
        raise SetupError("branch-derived worktree path must use POSIX separators and contain no backslashes")
    rel = PurePosixPath(relpath)
    if (
        rel.is_absolute()
        or rel.parts[:1] != (".worktrees",)
        or len(rel.parts) < 2
        or ".." in rel.parts
        or any(part in ("", ".") for part in rel.parts[1:])
    ):
        raise SetupError(
            "branch-derived worktree path must remain under .worktrees and contain no parent traversal"
        )
    for part in rel.parts[1:]:
        _validate_worktree_path_segment(part)
    return rel.as_posix()


def _validate_worktree_path_segment(segment: str) -> None:
    if segment.endswith((" ", ".")):
        raise SetupError("branch-derived worktree path segment is not filesystem-safe on Windows")
    if any(ord(char) < 32 or char in WINDOWS_INVALID_PATH_CHARS for char in segment):
        raise SetupError("branch-derived worktree path segment contains a character unsafe for Windows")
    stem = segment.split(".", 1)[0].casefold()
    if stem in WINDOWS_RESERVED_BASENAMES:
        raise SetupError("branch-derived worktree path segment is a Windows reserved device name")


def _target_path_exists(path: Path, label: str) -> bool:
    try:
        return reject_link_or_reparse(path, label, allow_missing=True) is not None
    except PathSafetyError as exc:
        raise SetupError(str(exc)) from exc


def _validate_worktree_target(
    repo: Path,
    worktrees_dir: Path,
    worktree_path: Path,
    label: str,
    require_existing: bool,
) -> None:
    try:
        st = reject_link_or_reparse(worktree_path, label, allow_missing=not require_existing)
        _reject_unsafe_worktree_ancestors(worktrees_dir, worktree_path, label)
        if st is not None and is_mount_point(worktree_path):
            raise PathSafetyError(f"{label} must not be a symlink, junction, mount point, or reparse point")
    except FileNotFoundError as exc:
        raise SetupError(f"{label} does not exist after git worktree add") from exc
    except PathSafetyError as exc:
        raise SetupError(str(exc)) from exc
    if require_existing and not worktree_path.is_dir():
        raise SetupError(f"{label} must be a directory after git worktree add")
    if not ensure_contained(worktree_path.resolve(strict=False), worktrees_dir):
        raise SetupError(f"{label} must resolve under verified repo-local .worktrees")
    if not ensure_contained(worktree_path.resolve(strict=False), repo):
        raise SetupError(f"{label} must remain under the repo root")


def _reject_unsafe_worktree_ancestors(worktrees_dir: Path, worktree_path: Path, label: str) -> None:
    normalized_worktrees_dir = Path(os.path.normpath(worktrees_dir))
    normalized_parent = Path(os.path.normpath(worktree_path.parent))
    try:
        relative_parent = normalized_parent.relative_to(normalized_worktrees_dir)
    except ValueError:
        return

    current = normalized_worktrees_dir
    for part in relative_parent.parts:
        if part in ("", "."):
            continue
        current = current / part
        st = reject_link_or_reparse(current, f"{label} ancestor", allow_missing=True)
        if st is None:
            continue
        if not stat.S_ISDIR(st.st_mode):
            raise PathSafetyError(f"{label} ancestor must be a directory under verified repo-local .worktrees")
        if is_mount_point(current):
            raise PathSafetyError(f"{label} ancestor must not be a symlink, junction, mount point, or reparse point")


def _target_branch_exists(repo: Path, branch: str) -> bool:
    return _git_success(["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], repo)


def _reject_direct_existing_target(branch_exists: bool, worktree_exists: bool) -> None:
    existing = []
    if branch_exists:
        existing.append("target branch")
    if worktree_exists:
        existing.append("target worktree path")
    target = " and ".join(existing)
    raise SetupError(
        f"Direct/manual setup cannot create metadata because {target} already exists; "
        f"{PREEXISTING_TARGET_RECOVERY}."
    )


def _reject_existing_target_for_repair(
    repo: Path,
    worktrees_dir: Path,
    metadata_path: Path,
    metadata_relpath: str,
    worktree_path: Path,
    worktree_relpath: str,
    branch: str,
    branch_exists: bool,
    worktree_exists: bool,
    main_base: str,
    data: dict[str, Any],
    main_git_common_dir: str,
) -> None:
    if data.get("featureBranch") not in (None, "") or data.get("worktreePath") not in (None, ""):
        raise _preexisting_target_error("metadata is already finalized or partially finalized")
    if not data.get("runId"):
        raise _preexisting_target_error("metadata runId cannot be verified")
    if not branch_exists or not worktree_exists:
        raise _preexisting_target_error("both the target branch and worktree path must exist for repair")

    branch_commit = _resolve_existing_branch_commit(repo, branch)
    if not _same_commit(branch_commit, main_base):
        raise _preexisting_target_error("existing branch does not match mainBase")

    try:
        _validate_worktree_target(repo, worktrees_dir, worktree_path, "worktree path", require_existing=True)
    except SetupError as exc:
        raise _preexisting_target_error(f"existing worktree path cannot be verified: {exc}") from exc

    _verify_existing_worktree_repository(main_git_common_dir, worktree_path)
    _ensure_existing_worktree_clean(worktree_path)

    checked_out_branch = _existing_worktree_branch(worktree_path)
    if checked_out_branch != branch:
        raise _preexisting_target_error("existing worktree branch does not match the expected branch")

    worktree_head = _existing_worktree_head(worktree_path)
    if not _same_commit(worktree_head, main_base):
        raise _preexisting_target_error("existing worktree HEAD does not match mainBase")

    try:
        _finalize_verified_metadata(
            repo,
            worktrees_dir,
            metadata_path,
            metadata_relpath,
            worktree_path,
            worktree_relpath,
            branch,
            data["runId"],
            main_base,
            require_unfinalized=True,
        )
    except (MetadataError, PathSafetyError, SetupError) as exc:
        raise SetupError(
            "existing branch/worktree matched the requested setup, but metadata repair failed; "
            "stop before dispatching agents. Reconcile or replace the metadata file before continuing. "
            f"Details: {exc}"
        ) from exc


def _verify_existing_worktree_repository(main_git_common_dir: str, worktree_path: Path) -> None:
    try:
        worktree_common_dir = _run_git(["rev-parse", "--path-format=absolute", "--git-common-dir"], worktree_path)
    except SetupError as exc:
        raise _preexisting_target_error(f"existing worktree repository identity could not be verified: {exc}") from exc
    if _norm_path(worktree_common_dir) != _norm_path(main_git_common_dir):
        raise _preexisting_target_error("existing worktree is not a linked worktree of this repository")


def _ensure_existing_worktree_clean(worktree_path: Path) -> None:
    try:
        status = _run_git(["status", "--porcelain=v1", "--untracked-files=all"], worktree_path)
    except SetupError as exc:
        raise _preexisting_target_error(f"existing worktree clean status could not be verified: {exc}") from exc
    if _split_git_lines(status):
        raise _preexisting_target_error("existing worktree is not clean")


def _resolve_existing_branch_commit(repo: Path, branch: str) -> str:
    try:
        return _run_git(["rev-parse", "--verify", f"refs/heads/{branch}^{{commit}}"], repo)
    except SetupError as exc:
        raise _preexisting_target_error(f"existing branch could not be resolved: {exc}") from exc


def _existing_worktree_branch(worktree_path: Path) -> str:
    try:
        return _run_git(["symbolic-ref", "--quiet", "--short", "HEAD"], worktree_path)
    except SetupError as exc:
        raise _preexisting_target_error(f"existing worktree branch could not be verified: {exc}") from exc


def _existing_worktree_head(worktree_path: Path) -> str:
    try:
        return _run_git(["rev-parse", "--verify", "HEAD"], worktree_path)
    except SetupError as exc:
        raise _preexisting_target_error(f"existing worktree HEAD could not be verified: {exc}") from exc


def _same_commit(actual: str, expected: str) -> bool:
    return actual.lower() == expected.lower()


def _preexisting_target_error(reason: str) -> SetupError:
    return SetupError(
        "target branch or worktree path already exists while metadata is incomplete, "
        f"but {reason}; {PREEXISTING_TARGET_RECOVERY}."
    )


def _post_add_update_metadata(
    repo: Path,
    worktrees_dir: Path,
    metadata_path: Path,
    metadata_relpath: str,
    worktree_path: Path,
    worktree_relpath: str,
    branch: str,
    run_id: str,
    expected_main_base: str,
    require_unfinalized: bool = False,
) -> None:
    try:
        _finalize_verified_metadata(
            repo,
            worktrees_dir,
            metadata_path,
            metadata_relpath,
            worktree_path,
            worktree_relpath,
            branch,
            run_id,
            expected_main_base,
            require_unfinalized,
        )
    except (MetadataError, PathSafetyError) as exc:
        raise SetupError(
            "Post-add metadata revalidation failed. Roll back the just-created worktree/branch, "
            f"then reconcile or replace the metadata file before continuing. Details: {exc}"
        ) from exc


def _finalize_verified_metadata(
    repo: Path,
    worktrees_dir: Path,
    metadata_path: Path,
    metadata_relpath: str,
    worktree_path: Path,
    worktree_relpath: str,
    branch: str,
    run_id: str,
    expected_main_base: str,
    require_unfinalized: bool = False,
) -> None:
    worktrees_dir = validate_worktrees_anchor(repo)
    validate_metadata_relpath(metadata_relpath, repo, worktrees_dir, require_existing=True)
    _validate_worktree_target(repo, worktrees_dir, worktree_path, "worktree path", require_existing=True)
    data = _validate_post_add_metadata(
        read_metadata(metadata_path),
        metadata_relpath,
        repo,
        worktrees_dir,
        run_id,
        expected_main_base,
        branch,
        worktree_relpath,
        require_unfinalized,
    )
    data["featureBranch"] = branch
    data["worktreePath"] = worktree_relpath
    _write_metadata(metadata_path, data)


def _validate_post_add_metadata(
    data: Any,
    metadata_relpath: str,
    repo: Path,
    worktrees_dir: Path,
    run_id: str,
    expected_main_base: str,
    branch: str,
    worktree_relpath: str,
    require_unfinalized: bool = False,
) -> dict[str, Any]:
    data = _validate_metadata_common_fields(data, metadata_relpath, repo, worktrees_dir)
    if data["runId"] != run_id:
        raise MetadataError("post-add metadata update refusing different runId")
    if data["mainBase"] != expected_main_base:
        raise MetadataError("post-add metadata update refusing different mainBase")
    if data["status"] != ACTIVE_STATUS:
        raise MetadataError("post-add metadata update requires status active")
    allowed_feature_branches = (None, "") if require_unfinalized else (None, "", branch)
    allowed_worktree_paths = (None, "") if require_unfinalized else (None, "", worktree_relpath)
    if data["featureBranch"] not in allowed_feature_branches:
        raise MetadataError("post-add metadata update found a populated featureBranch mismatch")
    if data["worktreePath"] not in allowed_worktree_paths:
        raise MetadataError("post-add metadata update found a populated worktreePath mismatch")
    return data


def _write_metadata(path: Path, data: dict[str, Any]) -> None:
    try:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        raise SetupError(f"failed to write metadata {path}: {exc}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
