from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path, PurePosixPath
from typing import Any

try:
    from scripts.double_sdd.path_safety import (
        PathSafetyError,
        ensure_contained,
        reject_link_or_reparse,
        validate_worktrees_anchor,
    )
except ModuleNotFoundError:
    from double_sdd.path_safety import (
        PathSafetyError,
        ensure_contained,
        reject_link_or_reparse,
        validate_worktrees_anchor,
    )


METADATA_SUFFIX = ".metadata.json"
WORKTREES_PART = ".worktrees"
ACTIVE_STATUS = "active"
VALID_LIFECYCLE_STATUSES = (ACTIVE_STATUS, "completed", "abandoned")
REQUIRED_FIELDS = (
    "schemaVersion",
    "runId",
    "status",
    "mainBranch",
    "mainBase",
    "featureBranch",
    "worktreePath",
    "metadataPath",
    "preexistingTrackedCheckpoint",
    "temporaryCheckpoints",
    "preexistingUntracked",
    "preexistingIgnored",
)
STRING_LIST_FIELDS = (
    "temporaryCheckpoints",
    "preexistingUntracked",
    "preexistingIgnored",
)
WINDOWS_RESERVED_BASENAMES = frozenset(
    ("con", "prn", "aux", "nul")
    + tuple(f"com{index}" for index in range(1, 10))
    + tuple(f"lpt{index}" for index in range(1, 10))
)


class MetadataError(ValueError):
    """Raised when workflow metadata is unsafe, incomplete, or malformed."""


def validate_run_id(run_id: str) -> str:
    if not isinstance(run_id, str):
        raise MetadataError("runId must be a string")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id) or ".." in run_id:
        raise MetadataError("runId is not filesystem-safe")
    if run_id.endswith("."):
        raise MetadataError("runId is not filesystem-safe: must not end with a dot")
    if run_id.split(".", 1)[0].casefold() in WINDOWS_RESERVED_BASENAMES:
        raise MetadataError("runId is not filesystem-safe: Windows reserved device name")
    return run_id


def metadata_relpath_for_run_id(run_id: str) -> str:
    return f"{WORKTREES_PART}/{validate_run_id(run_id)}{METADATA_SUFFIX}"


def validate_metadata_relpath(
    relpath: str,
    repo: Path,
    worktrees_dir: Path,
    require_existing: bool = False,
) -> str:
    if not isinstance(relpath, str):
        raise MetadataError("metadataPath must be a string")
    if "\\" in relpath:
        raise MetadataError("metadataPath must be repo-relative POSIX style")

    rel = PurePosixPath(relpath)
    if (
        rel.is_absolute()
        or rel.parts[:1] != (WORKTREES_PART,)
        or ".." in rel.parts
        or rel.parent != PurePosixPath(WORKTREES_PART)
        or len(rel.parts) != 2
        or not rel.name.endswith(METADATA_SUFFIX)
    ):
        raise MetadataError(
            "metadataPath must be exactly .worktrees/<runId>.metadata.json, "
            "top-level under .worktrees, repo-relative POSIX, and contain no parent traversal"
        )

    run_id = rel.name[: -len(METADATA_SUFFIX)]
    validate_run_id(run_id)
    expected = metadata_relpath_for_run_id(run_id)
    if relpath != expected:
        raise MetadataError("metadataPath must match its filesystem-safe runId")

    worktrees_resolved = _validated_worktrees_anchor(repo, worktrees_dir)

    metadata_path = repo / Path(*rel.parts)
    try:
        metadata_stat = reject_link_or_reparse(
            metadata_path,
            "metadata path",
            allow_missing=not require_existing,
        )
    except FileNotFoundError as exc:
        raise MetadataError(
            "metadata path does not exist. Stop and reconcile or recreate the handed-off metadata file."
        ) from exc
    except PathSafetyError as exc:
        raise MetadataError(str(exc)) from exc
    if metadata_stat is not None:
        _require_regular_metadata_file(metadata_stat, "metadata path")

    metadata_resolved = metadata_path.resolve(strict=False)
    if not ensure_contained(metadata_resolved, worktrees_resolved):
        raise MetadataError("metadataPath must resolve under repo-local .worktrees")
    return rel.as_posix()


def read_metadata(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MetadataError(
            f"Existing metadata is malformed or unreadable: {exc}. "
            "Stop and reconcile or replace the metadata file before continuing."
        ) from exc


def validate_reused_metadata(
    data: Any,
    metadata_relpath: str,
    repo: Path,
    worktrees_dir: Path,
) -> dict[str, Any]:
    data = _validate_metadata_common_fields(data, metadata_relpath, repo, worktrees_dir)
    if data["status"] != ACTIVE_STATUS:
        _bad_metadata("status must be exactly active")
    if data["featureBranch"] not in (None, ""):
        _bad_metadata("featureBranch must be null or empty before setup")
    if data["worktreePath"] not in (None, ""):
        _bad_metadata("worktreePath must be null or empty before setup")
    return data


def find_single_preimplementation_metadata(repo: Path, worktrees_dir: Path) -> str:
    worktrees_dir = _validated_worktrees_anchor(repo, worktrees_dir)
    candidates: list[str] = []
    for path in sorted(worktrees_dir.glob(f"*{METADATA_SUFFIX}")):
        _validate_globbed_candidate_path(path, repo, worktrees_dir)
        relpath = _exact_candidate_relpath_or_none(path, repo)
        if relpath is None:
            continue

        validate_metadata_relpath(relpath, repo, worktrees_dir, require_existing=True)
        data = read_metadata(path)
        data = _validate_metadata_common_fields(data, relpath, repo, worktrees_dir)
        if data["status"] not in VALID_LIFECYCLE_STATUSES:
            _bad_metadata("status must be one of active, completed, or abandoned")
        if data["status"] != ACTIVE_STATUS:
            continue
        if data["featureBranch"] not in (None, "") or data["worktreePath"] not in (None, ""):
            continue
        validate_reused_metadata(data, relpath, repo, worktrees_dir)
        candidates.append(relpath)

    if len(candidates) == 1:
        return candidates[0]
    raise MetadataError(
        f"Metadata lookup found {len(candidates)} active pre-implementation candidate(s). "
        "Pass the exact metadata path or reconcile the .worktrees metadata files before continuing."
    )


def _validate_metadata_common_fields(
    data: Any,
    metadata_relpath: str,
    repo: Path,
    worktrees_dir: Path,
) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise MetadataError(
            "Existing metadata is incomplete or not well-typed: top-level JSON value must be an object. "
            "Stop and reconcile or replace the metadata file before continuing."
        )
    missing = [field for field in REQUIRED_FIELDS if field not in data]
    if missing:
        _bad_metadata("missing required field(s): " + ", ".join(missing))
    if data["schemaVersion"] != 1:
        _bad_metadata("schemaVersion must be 1")
    if not isinstance(data["runId"], str):
        _bad_metadata("runId must be a string")
    try:
        validate_run_id(data["runId"])
    except MetadataError as exc:
        _bad_metadata_from_error(exc)
    if not isinstance(data["status"], str):
        _bad_metadata("status must be a string")
    if not isinstance(data["mainBranch"], str) or not data["mainBranch"].strip():
        _bad_metadata("mainBranch must be a non-empty string")
    if not isinstance(data["mainBase"], str) or not re.fullmatch(r"[0-9a-fA-F]{40}", data["mainBase"]):
        _bad_metadata("mainBase must be a 40-character commit SHA")
    if data["featureBranch"] is not None and not isinstance(data["featureBranch"], str):
        _bad_metadata("featureBranch must be null or a string")
    if data["worktreePath"] is not None and not isinstance(data["worktreePath"], str):
        _bad_metadata("worktreePath must be null or a string")
    if not isinstance(data["metadataPath"], str):
        _bad_metadata("metadataPath must be a string")

    try:
        expected_relpath = metadata_relpath_for_run_id(data["runId"])
    except MetadataError as exc:
        _bad_metadata_from_error(exc)
    if data["metadataPath"] != expected_relpath:
        _bad_metadata(
            "metadataPath must be exactly .worktrees/<runId>.metadata.json, "
            "top-level under .worktrees, repo-relative POSIX, and contain no parent traversal"
        )
    try:
        actual_relpath = validate_metadata_relpath(metadata_relpath, repo, worktrees_dir, require_existing=False)
        persisted_relpath = validate_metadata_relpath(data["metadataPath"], repo, worktrees_dir, require_existing=False)
    except MetadataError as exc:
        _bad_metadata_from_error(exc)
    if persisted_relpath != actual_relpath:
        _bad_metadata("metadataPath must match the actual metadata file path being read")

    if data["preexistingTrackedCheckpoint"] is not None and not isinstance(
        data["preexistingTrackedCheckpoint"], str
    ):
        _bad_metadata("preexistingTrackedCheckpoint must be null or a string")
    for field in STRING_LIST_FIELDS:
        if not isinstance(data[field], list):
            _bad_metadata(f"{field} must be a list")
        if not all(isinstance(item, str) for item in data[field]):
            _bad_metadata(f"{field} entries must be strings")
    return data


def _validate_globbed_candidate_path(path: Path, repo: Path, worktrees_dir: Path) -> None:
    worktrees_resolved = _validated_worktrees_anchor(repo, worktrees_dir)

    try:
        metadata_stat = reject_link_or_reparse(path, "metadata candidate", allow_missing=False)
    except FileNotFoundError as exc:
        raise MetadataError(
            "metadata candidate disappeared during lookup. Stop and reconcile .worktrees metadata files."
        ) from exc
    except PathSafetyError as exc:
        raise MetadataError(str(exc)) from exc
    _require_regular_metadata_file(metadata_stat, "metadata candidate")

    metadata_resolved = path.resolve(strict=False)
    if not ensure_contained(metadata_resolved, worktrees_resolved):
        raise MetadataError("metadata candidate must resolve under repo-local .worktrees")


def _exact_candidate_relpath_or_none(path: Path, repo: Path) -> str | None:
    try:
        relpath = Path(os.path.relpath(path, repo)).as_posix()
    except ValueError:
        return None

    rel = PurePosixPath(relpath)
    if (
        rel.is_absolute()
        or rel.parts[:1] != (WORKTREES_PART,)
        or ".." in rel.parts
        or rel.parent != PurePosixPath(WORKTREES_PART)
        or len(rel.parts) != 2
        or not rel.name.endswith(METADATA_SUFFIX)
    ):
        return None

    run_id = rel.name[: -len(METADATA_SUFFIX)]
    try:
        expected = metadata_relpath_for_run_id(run_id)
    except MetadataError:
        return None
    if relpath != expected:
        return None
    return relpath


def _validated_worktrees_anchor(repo: Path, worktrees_dir: Path) -> Path:
    try:
        verified_anchor = validate_worktrees_anchor(repo)
    except PathSafetyError as exc:
        raise MetadataError(
            f".worktrees anchor is unsafe: {exc}. "
            "Stop and repair the repo-local .worktrees directory before reading metadata."
        ) from exc

    worktrees_resolved = worktrees_dir.resolve(strict=False)
    if os.path.normcase(str(worktrees_resolved)) != os.path.normcase(str(verified_anchor)):
        raise MetadataError("worktrees directory must be the verified repo-local .worktrees anchor")
    return verified_anchor


def _bad_metadata(message: str) -> None:
    raise MetadataError(
        f"Existing metadata is incomplete or not well-typed: {message}. "
        "Stop and reconcile or replace the metadata file before continuing."
    )


def _bad_metadata_from_error(exc: MetadataError) -> None:
    raise MetadataError(
        f"Existing metadata is incomplete or not well-typed: {exc}. "
        "Stop and reconcile or replace the metadata file before continuing."
    ) from exc


def _require_regular_metadata_file(metadata_stat: os.stat_result, label: str) -> None:
    if not stat.S_ISREG(metadata_stat.st_mode):
        raise MetadataError(
            f"{label} must be a regular file. "
            "Stop and reconcile or replace the metadata path before continuing."
        )
