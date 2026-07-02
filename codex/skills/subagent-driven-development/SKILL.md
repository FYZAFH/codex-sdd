---
name: subagent-driven-development
description: Use before implementing anything - dispatches fresh subagent per task with parallel dual review and a spec gate. As an orchestrator, you must never implement anything yourself.
---

# Subagent-Driven Development

Execute plan by dispatching a fresh subagent per task, then dispatch `spec-code-reviewer` and `quality-code-reviewer` in parallel after each implementation pass. `spec-code-reviewer` is the gate, but only after you have verified that its reported compliance mismatch is real and should be addressed in the current pass. For how reviews are dispatched, interpreted, triaged, validated, gated, and pushed back on, follow the `code-review` skill throughout the review cycle.

**Why subagents:** You delegate tasks to specialized agents with isolated context. By precisely crafting their instructions and context, you ensure they stay focused and succeed at their task. They should never inherit your session's context or history — you construct exactly what they need. This also preserves your own context for coordination work.

**Core principle:** Fresh subagent per task + parallel review pair (spec gate over quality, `code-review` skill) = high quality, fast iteration

**Completion rule:** Keep driving the plan forward until the entire plan is completed. Do not stop after one task, one review pass, or one fix loop. Only stop when all planned tasks are done or when you hit a real unresolved issue you cannot responsibly solve yourself, such as a required spec change, a missing human decision, a missing approval, or a verified blocker that invalidates the current execution path.

## Prerequisites

This skill requires two artifacts before starting:

1. **Spec** — a design document produced by the `writing-specs` skill, saved to `docs/double-sdd/specs/YYYY-MM-DD-<topic>-design.md`. If you don't have a spec, invoke `writing-specs` first.
2. **Plan** — an implementation plan produced by the `writing-plans` skill, saved to `docs/double-sdd/plans/YYYY-MM-DD-<feature-name>.md`. If you have a spec but no plan, invoke `writing-plans` first.

**IMPORTANT:** Do NOT assume these artifacts exist based on the topic being discussed or files you find by searching. A spec/plan only counts as "existing" if the user has **explicitly pointed you to it** (e.g., by providing the path directly). If the user has not explicitly indicated these files, treat them as missing and invoke the corresponding skill.

- No spec → invoke `writing-specs`, stop here
- Spec but no plan → invoke `writing-plans`, stop here
- Both exist → proceed with this skill

## Setup: Isolated Workspace

Before executing any tasks, create an isolated worktree from a recorded main-worktree base. Use the non-committed JSON metadata file created by `writing-specs`, or create one only when this skill is entered directly with the explicit no-upstream signal `NO_UPSTREAM_METADATA=true` and an explicit filesystem-safe `RUN_ID`.

Required metadata path pattern: `.worktrees/<run-id>.metadata.json`. The metadata path contract is exactly one filename directly under `.worktrees`; reject nested paths such as `.worktrees/nested/foo.metadata.json`.

Required JSON fields:
- `schemaVersion`
- `runId`
- `status`
- `mainBranch`
- `mainBase`
- `featureBranch`
- `worktreePath`
- `metadataPath`

Additional required JSON fields:
- `preexistingTrackedCheckpoint`
- `temporaryCheckpoints`
- `preexistingUntracked`
- `preexistingIgnored`

The metadata file is UTF-8 JSON runtime workflow state and must not be committed. JSON strings preserve paths with spaces, backslashes, quotes, and newlines more safely than shell `KEY=value` parsing; prefer reading and writing the metadata as JSON instead of reconstructing paths from ad hoc environment strings.

Metadata lookup, safety, and lifecycle rules:
- `.worktrees` must be the repo-local ignored worktree area before writing runtime metadata. Reject a `.worktrees` anchor that is a symlink, Windows junction, mount point, or any other reparse point; then explicitly verify the resolved `.worktrees` anchor itself remains under the resolved repo root before using it as the trusted containment base. Reject metadata or worktree paths whose normalized real paths escape that verified anchor through symlinks, junctions, reparse points, or other redirected path components, and confirm the target metadata path is ignored by git before writing it.
- Run setup from the original main worktree only. If the current checkout is already a linked worktree, stop and ask the user to return to the original main worktree before deriving `.worktrees` from `git rev-parse --show-toplevel`.
- If a metadata path is passed by `writing-specs`, this is upstream metadataPath mode. Reject mode mixing first: `RUN_ID` and `NO_UPSTREAM_METADATA=true` must not be present with an explicit metadata path. After that, validate the explicit metadata path before any `exists()`, `read_text()`, or JSON parsing that could follow the target: reject absolute paths, parent-directory segments, nested paths under `.worktrees`, paths outside `.worktrees`, filename-derived `runId` values that fail the filesystem-safe runId contract, final-path symlinks, Windows junctions, or reparse points detected with `lstat`, file attributes/reparse tags, or an equivalent platform API, and normalized resolved paths that escape the verified repo-local `.worktrees` directory. If the selected upstream metadata file does not exist, stop with upstream correction guidance only: reconcile or recreate the handed-off metadata file, or ask for the exact correct metadata path. Do not suggest `RUN_ID` or direct-entry fallback. Only after those checks may setup update that exact metadata path.
- If no metadata path is passed and `NO_UPSTREAM_METADATA=true` is present, this is a direct/manual no-upstream run. Do not auto-search or reuse existing active `.worktrees/*.metadata.json` candidates. Require the explicit filesystem-safe `RUN_ID`, derive `.worktrees/$RUN_ID.metadata.json`, and proceed only through direct-entry metadata creation after the clean worktree and preexisting-state checks below. If `RUN_ID` is missing, unsafe, or the target metadata file already exists, stop and ask for user direction instead of reusing metadata.
- If no metadata path is passed and `NO_UPSTREAM_METADATA=true` is not present, keep the upstream lookup/stop behavior. Reject any supplied `RUN_ID` before candidate search; `RUN_ID` is valid only for direct/manual no-upstream execution. Search the repo-level `.worktrees/*.metadata.json` files for valid candidates appropriate for starting implementation: `status` is exactly `active`, and `featureBranch` and `worktreePath` are unset/null or empty. For every globbed top-level metadata file, first run `lstat` or equivalent, reject a symlinked, junctioned, or reparse-point candidate, and verify resolved containment under the verified repo-local `.worktrees` anchor. Then treat filename/runId contract violations as invalid non-candidates: skip them without reading JSON, and do not count them toward zero, one, or multiple active candidates. Only read JSON after a candidate is read-eligible by being exactly a repo-relative top-level `.worktrees/<run-id>.metadata.json` path with a filesystem-safe `runId`; malformed, invalid UTF-8, or unreadable JSON in a read-eligible candidate still stops with reconcile-or-replace guidance. If exactly one valid candidate exists, use that metadata file and derive `runId` from the file content. If none or more than one valid candidate exists, stop and ask for the exact metadata path or user direction. Explicit metadata paths are stricter: filename/runId/path-contract failures remain fatal for the selected path.
- Existing metadata may be reused only when `status` is exactly `active`. If `status` is `completed`, `abandoned`, missing, or any other value, stop and ask for direction or require a new `runId`.
- After confirming setup is running from the original main worktree, resolve the repository root explicitly before any metadata or worktree path work, for example with `git rev-parse --show-toplevel`. Derive `.worktrees`, `METADATA_PATH`, and `WORKTREE_PATH` from that repo root in shell and Python. Do not use the current process directory as the repository anchor.
- When using an existing active metadata file, use its recorded `mainBase` for `git worktree add`; fall back to `git rev-parse --verify HEAD` only when creating metadata for a direct-entry run with no existing metadata.
- Before `git worktree add`, validate `mainBase` as a 40-character commit SHA and verify it resolves with `git rev-parse --verify "$MAIN_BASE^{commit}"`. If validation fails, stop with metadata reconcile-or-replace guidance instead of falling through to a generic `git worktree add` error.
- Only direct-entry metadata creation may call `git branch --show-current` to populate `mainBranch`. When reusing existing metadata, reject a missing or blank `mainBranch`; do not backfill it from the current branch.
- Direct-entry metadata creation is allowed only when `NO_UPSTREAM_METADATA=true` is present, the explicit `RUN_ID` is safe, the target `.worktrees/$RUN_ID.metadata.json` file does not already exist, and the main worktree has no preexisting tracked, untracked, or unsafe ignored state that this skill cannot safely record. Harmless retained ignored metadata files matching `.worktrees/*.metadata.json` with completed or abandoned status (`status` `completed` or `abandoned`) do not block direct entry; unsafe ignored files still block. If blocking state exists, stop and require the upstream recording step (`writing-specs`) so it can checkpoint or inventory that state before implementation begins; do not write empty `preexisting*` defaults that falsely imply a clean start.
- `runId` must be filesystem-safe: ASCII letters, numbers, `.`, `_`, and `-` only, and it must not contain `..` anywhere.
- Persist `metadataPath` and `worktreePath` as repo-relative POSIX-style paths with forward slashes, for example `.worktrees/<run-id>.metadata.json` and `.worktrees/<feature-branch>`. `metadataPath` must be top-level under `.worktrees`, with the filename corresponding to `runId`; use absolute paths only for filesystem operations, not for persisted metadata fields or handoff text.
- `metadataPath` must resolve inside the verified repository `.worktrees` directory after path normalization. This requires checking the resolved `.worktrees` anchor itself against the repo root before trusting it.
- `worktreePath` must resolve inside the verified repo-local `.worktrees` directory for this skill flow; do not use user-approved external worktree paths here.
- Do not follow symlinked, junctioned, or reparse-point metadata paths outside `.worktrees`.
- On Windows, compare normalized absolute paths case-insensitively when checking path containment, and check file attributes/reparse tags or an equivalent platform API; `Path.is_symlink()`, shell `-L`, and `stat.S_ISLNK()` alone are not enough to detect junctions and other reparse points.
- Do not overwrite an existing metadata file for a different `runId`.
- Do not store file contents, environment variables, tokens, or command output in the metadata artifact.
- Metadata starts with `status: "active"` and finishing later marks it `completed` or `abandoned`.
- `featureBranch` and `worktreePath` must be unset/null in the initial metadata before `git worktree add`; update them only after `git worktree add` succeeds. Immediately before the post-add write, re-read the metadata, validate the same required schema and persisted `metadataPath` contract as pre-add reuse, then verify `runId` still matches, `status` is still exactly `active`, and existing `featureBranch`/`worktreePath` are unset/null or already match the expected branch and repo-local worktree path. If post-add revalidation finds missing or ill-typed required fields, an invalid persisted `metadataPath`, `completed`, `abandoned`, or populated mismatched lifecycle state, stop with rollback and reconcile-or-replace guidance instead of preserving corrupted metadata. If existing active metadata already has mismatched `featureBranch` or `worktreePath` before setup, treat it as an already active worktree and stop and ask instead of reusing or clearing it silently.
- Reused metadata must be rejected unless every required field is present and well-typed before setup: `schemaVersion` is `1`; `runId` is a string; `status` is exactly `active`; `mainBranch` is a non-empty string; `mainBase` is a 40-character commit SHA; `featureBranch` and `worktreePath` are null or empty; `metadataPath` satisfies the full persisted path contract; `preexistingTrackedCheckpoint` is present and nullable; and `temporaryCheckpoints`, `preexistingUntracked`, and `preexistingIgnored` are lists. For reused metadata, the persisted `metadataPath` field must be exactly `.worktrees/<runId>.metadata.json`, top-level under `.worktrees`, repo-relative POSIX with no parent traversal, matched to the actual metadata file path being read, and resolved under the repo-local `.worktrees` directory. If persisted `metadataPath` is invalid, stop for metadata reconciliation instead of overwriting or repairing it silently.
- Every prose dry-run and executable example must preserve the same ordering: resolve the repo root; validate the `.worktrees` anchor as the explicit prerequisite with `lstat` symlink/junction/reparse checks and resolved-anchor containment under the repo root; validate metadata syntax; validate final-path `lstat` symlink/junction/reparse status; validate resolved child containment under the verified anchor; read JSON only after those checks.
- Existing metadata reads must catch `OSError`, `UnicodeDecodeError`, and `json.JSONDecodeError` and stop with a clear instruction to reconcile or replace the malformed metadata file instead of allowing a raw traceback.
- Before retrying `git worktree add`, reconcile pre-add state for the run: detect whether the target branch or worktree path already exists. If either exists while metadata still has null `featureBranch` or `worktreePath`, repair metadata only when the existing branch, worktree path, `mainBase`, and `runId` can be verified as the intended state for this run. Otherwise stop with explicit recovery instructions, such as choosing a new branch/path, removing the stale branch/worktree after user approval, or manually repairing the metadata. Do not blindly retry creation.

Example setup and update flow:

```bash
set -euo pipefail

BRANCH_NAME=<feature-branch>
METADATA_RELPATH="${METADATA_RELPATH:-}"  # exact path from writing-specs; leave empty for lookup or direct/manual no-upstream execution
NO_UPSTREAM_METADATA="${NO_UPSTREAM_METADATA:-false}"  # must be true for direct/manual no-upstream execution
RUN_ID="${RUN_ID:-}"  # required only when NO_UPSTREAM_METADATA=true and direct-entry metadata will be created
GIT_DIR=$(git rev-parse --path-format=absolute --git-dir)
GIT_COMMON_DIR=$(git rev-parse --path-format=absolute --git-common-dir)
if [ "$GIT_DIR" != "$GIT_COMMON_DIR" ]; then
  echo "Setup must run from the original main worktree. This checkout is a linked worktree; return to the original main worktree and retry." >&2
  exit 1
fi
REPO_ROOT=$(git rev-parse --show-toplevel)
WORKTREES_RELPATH=".worktrees/"
WORKTREE_RELPATH=".worktrees/$BRANCH_NAME"
WORKTREES_DIR="$REPO_ROOT/.worktrees"
WORKTREE_PATH="$REPO_ROOT/$WORKTREE_RELPATH"
export BRANCH_NAME NO_UPSTREAM_METADATA RUN_ID REPO_ROOT WORKTREES_RELPATH WORKTREE_RELPATH METADATA_RELPATH WORKTREES_DIR WORKTREE_PATH

python - <<'PY'
import os
import stat
from pathlib import Path

repo = Path(os.environ["REPO_ROOT"]).resolve()
anchor = repo / ".worktrees"

def is_reparse_point(st):
    return bool(
        getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        and (getattr(st, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    )

try:
    anchor_lstat = anchor.lstat()
    anchor_exists = True
except FileNotFoundError:
    anchor_lstat = None
    anchor_exists = False
except OSError as exc:
    raise SystemExit(f".worktrees anchor could not be lstat-checked: {exc}")
if anchor_exists:
    if stat.S_ISLNK(anchor_lstat.st_mode) or is_reparse_point(anchor_lstat):
        raise SystemExit(".worktrees must be a repo-local directory, not a symlink, junction, or reparse point")
    if not stat.S_ISDIR(anchor_lstat.st_mode):
        raise SystemExit(".worktrees must be a repo-local directory")
else:
    resolved_parent = anchor.parent.resolve(strict=True)
    if os.path.normcase(str(resolved_parent)) != os.path.normcase(str(repo)):
        raise SystemExit("missing .worktrees anchor must have the resolved repo root as its direct parent")

resolved_anchor = anchor.resolve(strict=False)
child = os.path.normcase(str(resolved_anchor))
parent = os.path.normcase(str(repo))
try:
    contained = os.path.commonpath([child, parent]) == parent
except ValueError:
    contained = False
if not contained:
    raise SystemExit("resolved .worktrees anchor must remain under the repo root")
PY
if ! git -C "$REPO_ROOT" check-ignore -q -- "$WORKTREES_RELPATH"; then
  echo ".worktrees must be git-ignored before writing runtime metadata." >&2
  exit 1
fi

METADATA_RELPATH=$(python - <<'PY'
import json
import os
import re
import stat
from pathlib import PurePosixPath
from pathlib import Path

provided = os.environ.get("METADATA_RELPATH", "").strip()
provided_run_id = os.environ.get("RUN_ID", "").strip()
no_upstream_metadata = os.environ.get("NO_UPSTREAM_METADATA", "").strip().lower() == "true"

repo = Path(os.environ["REPO_ROOT"]).resolve()

def is_reparse_point(st):
    return bool(
        getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        and (getattr(st, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    )

def reject_link_or_reparse(path, label, allow_missing=False):
    try:
        st = path.lstat()
    except FileNotFoundError:
        if allow_missing:
            return None
        raise
    except OSError as exc:
        raise SystemExit(f"{label} could not be lstat-checked before use: {exc}")
    if stat.S_ISLNK(st.st_mode) or is_reparse_point(st):
        raise SystemExit(f"{label} must not be a symlink, junction, or reparse point")
    return st

def ensure_contained(path, parent):
    child = os.path.normcase(str(path.resolve(strict=False)))
    base = os.path.normcase(str(parent))
    try:
        return os.path.commonpath([child, base]) == base
    except ValueError:
        return False

worktrees_anchor = repo / ".worktrees"
reject_link_or_reparse(worktrees_anchor, ".worktrees anchor", allow_missing=True)
worktrees_dir = worktrees_anchor.resolve(strict=False)
if not ensure_contained(worktrees_dir, repo):
    raise SystemExit("resolved .worktrees anchor must remain under the repo root before metadata lookup")

def validate_run_id(run_id):
    if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id) or ".." in run_id:
        raise SystemExit("RUN_ID is not filesystem-safe")

def validate_metadata_relpath(relpath, require_existing=False):
    rel = PurePosixPath(relpath)
    if rel.is_absolute() or rel.parts[:1] != (".worktrees",) or ".." in rel.parts:
        raise SystemExit("explicit metadata path must be repo-relative under .worktrees with no parent-directory segments")
    if rel.parent != PurePosixPath(".worktrees") or len(rel.parts) != 2:
        raise SystemExit("explicit metadata path must match .worktrees/<run-id>.metadata.json exactly; nested metadata paths are not allowed")
    if rel.suffixes[-2:] != [".metadata", ".json"]:
        raise SystemExit("explicit metadata path must end with .metadata.json")
    run_id = rel.name[: -len(".metadata.json")]
    validate_run_id(run_id)
    path = repo / Path(*rel.parts)
    metadata_lstat = reject_link_or_reparse(path, "explicit metadata path", allow_missing=True)
    if metadata_lstat is None and require_existing:
        raise SystemExit(
            "Upstream metadataPath points to a missing file. "
            "Stop and reconcile or recreate the handed-off metadata file, "
            "or ask for the exact correct metadata path."
        )
    if not ensure_contained(path, worktrees_dir):
        raise SystemExit("explicit metadata path must resolve under verified repo-local .worktrees before read")
    return rel.as_posix()

def validate_metadata_candidate(path):
    reject_link_or_reparse(path, f"metadata candidate {path}")
    if not ensure_contained(path, worktrees_dir):
        raise SystemExit(f"metadata candidate escapes verified repo-local .worktrees and must not be read: {path}")
    try:
        rel_path = path.relative_to(repo)
    except ValueError:
        return False
    rel = PurePosixPath(rel_path.as_posix())
    if rel.is_absolute() or rel.parts[:1] != (".worktrees",) or ".." in rel.parts:
        return False
    if rel.parent != PurePosixPath(".worktrees") or len(rel.parts) != 2:
        return False
    if rel.suffixes[-2:] != [".metadata", ".json"]:
        return False
    run_id = rel.name[:-len(".metadata.json")]
    if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id) or ".." in run_id:
        return False
    return True

if provided:
    if no_upstream_metadata or provided_run_id:
        raise SystemExit(
            "Upstream metadataPath mode cannot be combined with RUN_ID or NO_UPSTREAM_METADATA=true. "
            "Clear RUN_ID and NO_UPSTREAM_METADATA before passing the exact metadata path."
        )
    print(validate_metadata_relpath(provided, require_existing=True))
    raise SystemExit

if no_upstream_metadata:
    if not provided_run_id:
        raise SystemExit(
            "Direct/manual no-upstream execution requires NO_UPSTREAM_METADATA=true and an explicit filesystem-safe RUN_ID. "
            "Stop and ask for RUN_ID before creating direct-entry metadata."
        )
    validate_run_id(provided_run_id)
    print(validate_metadata_relpath(f".worktrees/{provided_run_id}.metadata.json"))
    raise SystemExit

if provided_run_id:
    raise SystemExit(
        "RUN_ID without NO_UPSTREAM_METADATA=true cannot be combined with upstream metadata lookup. "
        "Clear RUN_ID and provide the exact metadata path, or explicitly restart as a direct/manual run with NO_UPSTREAM_METADATA=true."
    )

candidates = []
for path in sorted(worktrees_dir.glob("*.metadata.json")):
    if not validate_metadata_candidate(path):
        continue
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemExit(
            f"Metadata lookup found malformed or unreadable metadata at {path}: {exc}. "
            "Stop and reconcile or replace the metadata file, or provide the exact metadata path."
        )
    if (
        isinstance(data, dict)
        and data.get("status") == "active"
        and data.get("featureBranch") in (None, "")
        and data.get("worktreePath") in (None, "")
    ):
        candidates.append(path)

if len(candidates) > 1:
    raise SystemExit(
        f"Metadata lookup found {len(candidates)} active pre-implementation candidate(s). "
        "Stop and ask for the exact metadata path or user direction."
    )

if len(candidates) == 1:
    print(candidates[0].relative_to(repo).as_posix())
    raise SystemExit

raise SystemExit(
    "Metadata lookup found 0 active pre-implementation candidate(s). "
    "Provide the exact metadata path, or explicitly restart as a direct/manual run with "
    "NO_UPSTREAM_METADATA=true and filesystem-safe RUN_ID."
)
PY
)
METADATA_PATH="$REPO_ROOT/$METADATA_RELPATH"
export METADATA_RELPATH METADATA_PATH

if ! git -C "$REPO_ROOT" check-ignore -q -- "$METADATA_RELPATH"; then
  echo "runtime metadata must be git-ignored before writing it." >&2
  exit 1
fi

# Only create .worktrees after the anchor and exact metadata target have passed path-safety and git-ignore preflight.
mkdir -p "$WORKTREES_DIR"

RUN_ID=$(python - <<'PY'
import json
import os
import re
import stat
from pathlib import PurePosixPath
from pathlib import Path

repo = Path(os.environ["REPO_ROOT"]).resolve()

def is_reparse_point(st):
    return bool(
        getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        and (getattr(st, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    )

def reject_link_or_reparse(path, label, allow_missing=False):
    try:
        st = path.lstat()
    except FileNotFoundError:
        if allow_missing:
            return None
        raise
    except OSError as exc:
        raise SystemExit(f"{label} could not be lstat-checked before use: {exc}")
    if stat.S_ISLNK(st.st_mode) or is_reparse_point(st):
        raise SystemExit(f"{label} must not be a symlink, junction, or reparse point")
    return st

def ensure_contained(path, parent):
    child = os.path.normcase(str(path.resolve(strict=False)))
    base = os.path.normcase(str(parent))
    try:
        return os.path.commonpath([child, base]) == base
    except ValueError:
        return False

worktrees_anchor = repo / ".worktrees"
reject_link_or_reparse(worktrees_anchor, ".worktrees anchor")
worktrees_dir = worktrees_anchor.resolve(strict=False)
if not ensure_contained(worktrees_dir, repo):
    raise SystemExit("resolved .worktrees anchor must remain under the repo root before metadata read")
metadata_relpath = os.environ["METADATA_RELPATH"]
metadata_rel = PurePosixPath(metadata_relpath)
if metadata_rel.is_absolute() or metadata_rel.parts[:1] != (".worktrees",) or ".." in metadata_rel.parts:
    raise SystemExit("metadata path must be repo-relative under .worktrees with no parent-directory segments before read")
if metadata_rel.parent != PurePosixPath(".worktrees") or len(metadata_rel.parts) != 2:
    raise SystemExit("metadata path must match .worktrees/<run-id>.metadata.json exactly; nested metadata paths are not allowed")
if metadata_rel.suffixes[-2:] != [".metadata", ".json"]:
    raise SystemExit("metadata path must end with .metadata.json")
metadata_path = repo / Path(*metadata_rel.parts)
metadata_exists = reject_link_or_reparse(metadata_path, "metadata path", allow_missing=True) is not None
if not ensure_contained(metadata_path, worktrees_dir):
    raise SystemExit("metadata path must resolve under verified repo-local .worktrees before read")
provided_run_id = os.environ.get("RUN_ID", "").strip()
no_upstream_metadata = os.environ.get("NO_UPSTREAM_METADATA", "").strip().lower() == "true"
if metadata_exists:
    if no_upstream_metadata:
        raise SystemExit(
            "Direct/manual no-upstream execution must create direct-entry metadata from RUN_ID. "
            "The target metadata file already exists; stop and ask for a new RUN_ID or user direction."
        )
    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemExit(
            f"Existing metadata is malformed or unreadable: {exc}. "
            "Stop and reconcile or replace the metadata file before continuing."
        )
    if not isinstance(data, dict):
        raise SystemExit(
            "Existing metadata is malformed or unreadable: top-level JSON value must be an object. "
            "Stop and reconcile or replace the metadata file before continuing."
        )
    run_id = data.get("runId")
    if not isinstance(run_id, str) or not run_id:
        raise SystemExit("Existing metadata is missing runId; stop and reconcile or replace the metadata file before continuing.")
    if provided_run_id and provided_run_id != run_id:
        raise SystemExit("Provided RUN_ID does not match metadata runId; stop and ask for the exact metadata path or user direction.")
else:
    run_id = provided_run_id
    if not run_id:
        raise SystemExit("Direct-entry metadata creation requires an explicit filesystem-safe RUN_ID and metadata path.")

if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id) or ".." in run_id:
    raise SystemExit("RUN_ID is not filesystem-safe")
if metadata_rel.name != f"{run_id}.metadata.json":
    raise SystemExit("metadata path filename must correspond to runId")
print(run_id)
PY
)
export RUN_ID

MAIN_BASE=$(python - <<'PY'
import json
import os
import re
import stat
import subprocess
from pathlib import Path, PurePosixPath

repo = Path(os.environ["REPO_ROOT"]).resolve()
run_id = os.environ["RUN_ID"]
no_upstream_metadata = os.environ.get("NO_UPSTREAM_METADATA", "").strip().lower() == "true"
metadata_path = Path(os.environ["METADATA_PATH"])

def is_reparse_point(st):
    return bool(
        getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        and (getattr(st, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    )

def reject_link_or_reparse(path, label, allow_missing=False):
    try:
        st = path.lstat()
    except FileNotFoundError:
        if allow_missing:
            return None
        raise
    except OSError as exc:
        raise SystemExit(f"{label} could not be lstat-checked before use: {exc}")
    if stat.S_ISLNK(st.st_mode) or is_reparse_point(st):
        raise SystemExit(f"{label} must not be a symlink, junction, or reparse point")
    return st

def ensure_contained(path, parent):
    child = os.path.normcase(str(path.resolve(strict=False)))
    base = os.path.normcase(str(parent))
    try:
        return os.path.commonpath([child, base]) == base
    except ValueError:
        return False

worktrees_anchor = repo / ".worktrees"
reject_link_or_reparse(worktrees_anchor, ".worktrees anchor")
worktrees_dir = worktrees_anchor.resolve(strict=False)
if not ensure_contained(worktrees_dir, repo):
    raise SystemExit("resolved .worktrees anchor must remain under the repo root before metadata read")
worktree_path = Path(os.environ["WORKTREE_PATH"])

if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id) or ".." in run_id:
    raise SystemExit("RUN_ID is not filesystem-safe")
metadata_exists = reject_link_or_reparse(metadata_path, "metadata path", allow_missing=True) is not None
reject_link_or_reparse(worktree_path, "existing worktree path", allow_missing=True)
metadata_path = metadata_path.resolve(strict=False)
worktree_path = worktree_path.resolve(strict=False)
if not ensure_contained(metadata_path, worktrees_dir):
    raise SystemExit("METADATA_PATH must resolve under verified repo-local .worktrees after symlink/reparse checks")
if not ensure_contained(worktree_path, worktrees_dir):
    raise SystemExit("WORKTREE_PATH must resolve under verified repo-local .worktrees after symlink/reparse checks")
metadata_relpath = metadata_path.relative_to(repo).as_posix()

def stop_for_bad_metadata(message):
    raise SystemExit(
        f"Existing metadata is incomplete or not well-typed: {message}. "
        "Stop and reconcile or replace the metadata file before continuing."
    )

def read_existing_metadata(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemExit(
            f"Existing metadata is malformed or unreadable: {exc}. "
            "Stop and reconcile or replace the metadata file before continuing."
        )

def validate_persisted_metadata_path(value, run_id):
    if not isinstance(value, str):
        stop_for_bad_metadata("metadataPath must be a string")
    rel = PurePosixPath(value)
    expected = PurePosixPath(".worktrees") / f"{run_id}.metadata.json"
    if (
        rel.is_absolute()
        or rel.parts[:1] != (".worktrees",)
        or ".." in rel.parts
        or rel.parent != PurePosixPath(".worktrees")
        or len(rel.parts) != 2
        or rel != expected
    ):
        stop_for_bad_metadata(
            "metadataPath must be exactly .worktrees/<runId>.metadata.json, "
            "top-level under .worktrees, repo-relative POSIX, and contain no parent traversal"
        )
    if rel.as_posix() != metadata_relpath:
        stop_for_bad_metadata("metadataPath must match the actual metadata file path being read")
    persisted_path = repo / Path(*rel.parts)
    persisted_child = os.path.normcase(str(persisted_path.resolve(strict=False)))
    persisted_parent = os.path.normcase(str(worktrees_dir))
    try:
        contained = os.path.commonpath([persisted_child, persisted_parent]) == persisted_parent
    except ValueError:
        contained = False
    if not contained:
        stop_for_bad_metadata("metadataPath must resolve under repo-local .worktrees")

def validate_reused_metadata(data):
    if not isinstance(data, dict):
        stop_for_bad_metadata("top-level JSON value must be an object")
    required = [
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
    ]
    missing = [field for field in required if field not in data]
    if missing:
        stop_for_bad_metadata("missing required field(s): " + ", ".join(missing))
    if data["schemaVersion"] != 1:
        stop_for_bad_metadata("schemaVersion must be 1")
    if not isinstance(data["runId"], str):
        stop_for_bad_metadata("runId must be a string")
    if data["status"] != "active":
        stop_for_bad_metadata("status must be exactly active")
    if not isinstance(data["mainBranch"], str) or not data["mainBranch"].strip():
        stop_for_bad_metadata("mainBranch must be a non-empty string")
    if not isinstance(data["mainBase"], str) or not re.fullmatch(r"[0-9a-fA-F]{40}", data["mainBase"]):
        stop_for_bad_metadata("mainBase must be a 40-character commit SHA")
    if data["featureBranch"] not in (None, ""):
        stop_for_bad_metadata("featureBranch must be null or empty before setup")
    if data["worktreePath"] not in (None, ""):
        stop_for_bad_metadata("worktreePath must be null or empty before setup")
    validate_persisted_metadata_path(data["metadataPath"], data["runId"])
    if data["preexistingTrackedCheckpoint"] is not None and not isinstance(data["preexistingTrackedCheckpoint"], str):
        stop_for_bad_metadata("preexistingTrackedCheckpoint must be null or a string")
    for field in ["temporaryCheckpoints", "preexistingUntracked", "preexistingIgnored"]:
        if not isinstance(data[field], list):
            stop_for_bad_metadata(f"{field} must be a list")
        if not all(isinstance(item, str) for item in data[field]):
            stop_for_bad_metadata(f"{field} entries must be strings")

def validate_main_base(main_base):
    if not re.fullmatch(r"[0-9a-fA-F]{40}", main_base):
        stop_for_bad_metadata("mainBase must be a 40-character commit SHA")
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"{main_base}^{{commit}}"],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise SystemExit(
            "Metadata mainBase does not resolve to a commit. "
            "Stop and reconcile or replace the metadata file before continuing."
        )

if metadata_exists:
    data = read_existing_metadata(metadata_path)
    validate_reused_metadata(data)
    if data.get("runId") != run_id:
        raise SystemExit("refusing to overwrite metadata for a different runId")
    if data.get("status") != "active":
        raise SystemExit("existing metadata status must be exactly active; completed, abandoned, missing, or other statuses require a new runId or user direction")
    if data.get("featureBranch") or data.get("worktreePath"):
        raise SystemExit("metadata already records an active worktree; stop and ask before reusing it")
    if not data.get("mainBase"):
        raise SystemExit("existing metadata is missing mainBase")
    if not str(data.get("mainBranch") or "").strip():
        raise SystemExit("existing metadata is missing or blank mainBranch; do not backfill it from the current branch")
else:
    if not no_upstream_metadata:
        raise SystemExit(
            "Upstream metadata file is missing. "
            "Stop and reconcile or recreate the handed-off metadata file, "
            "or ask for the exact correct metadata path."
        )
    tracked = subprocess.check_output(["git", "status", "--porcelain=v1", "--untracked-files=no"], cwd=repo, text=True).splitlines()
    untracked = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard"], cwd=repo, text=True).splitlines()
    ignored = subprocess.check_output(["git", "ls-files", "--others", "--ignored", "--exclude-standard"], cwd=repo, text=True).splitlines()
    blocking_ignored = []
    for ignored_path in ignored:
        ignored_metadata = (
            ignored_path.startswith(".worktrees/")
            and ignored_path.endswith(".metadata.json")
            and "/" not in ignored_path[len(".worktrees/"):]
        )
        if ignored_metadata:
            retained_metadata = repo / ignored_path
            try:
                retained_lstat = reject_link_or_reparse(retained_metadata, f"retained metadata {ignored_path}")
                if retained_lstat is None:
                    retained_status = None
                    blocking_ignored.append(ignored_path)
                    continue
                if not ensure_contained(retained_metadata, worktrees_dir):
                    retained_status = None
                    blocking_ignored.append(ignored_path)
                    continue
                retained_data = json.loads(retained_metadata.read_text(encoding="utf-8"))
                if not isinstance(retained_data, dict):
                    retained_status = None
                    blocking_ignored.append(ignored_path)
                    continue
                retained_status = retained_data.get("status")
            except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError):
                retained_status = None
            if retained_status in {"completed", "abandoned"}:
                continue
        blocking_ignored.append(ignored_path)
    if tracked or untracked or blocking_ignored:
        raise SystemExit("Direct-entry metadata creation cannot safely record preexisting tracked/untracked/ignored state; run the upstream recording step (`writing-specs`) first.")
    main_branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=repo, text=True).strip()
    if not main_branch:
        raise SystemExit("Detached HEAD or empty branch name; stop and ask for an explicit base branch before creating direct-entry metadata.")
    direct_entry_main_base = subprocess.check_output(["git", "rev-parse", "--verify", "HEAD"], cwd=repo, text=True).strip()
    data = {
        "schemaVersion": 1,
        "runId": run_id,
        "status": "active",
        "mainBranch": main_branch,
        "mainBase": direct_entry_main_base,
        "featureBranch": None,
        "worktreePath": None,
        "metadataPath": metadata_relpath,
        "preexistingTrackedCheckpoint": None,
        "temporaryCheckpoints": [],
        "preexistingUntracked": [],
        "preexistingIgnored": []
    }

validate_main_base(data["mainBase"])
data.update({
    "schemaVersion": 1,
    "status": "active",
    "mainBranch": data["mainBranch"],
    "mainBase": data["mainBase"],
    "featureBranch": None,
    "worktreePath": None,
    "metadataPath": metadata_relpath,
})

metadata_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(data["mainBase"])
PY
)
export MAIN_BASE

python - <<'PY'
import json
import os
import stat
import subprocess
from pathlib import Path

repo = Path(os.environ["REPO_ROOT"]).resolve()
metadata_path = Path(os.environ["METADATA_PATH"])
worktree_path = Path(os.environ["WORKTREE_PATH"])
branch_name = os.environ["BRANCH_NAME"]

def is_reparse_point(st):
    return bool(
        getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        and (getattr(st, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    )

def reject_link_or_reparse(path, label, allow_missing=False):
    try:
        st = path.lstat()
    except FileNotFoundError:
        if allow_missing:
            return None
        raise
    except OSError as exc:
        raise SystemExit(f"{label} could not be lstat-checked before use: {exc}")
    if stat.S_ISLNK(st.st_mode) or is_reparse_point(st):
        raise SystemExit(f"{label} must not be a symlink, junction, or reparse point")
    return st

def ensure_contained(path, parent):
    child = os.path.normcase(str(path.resolve(strict=False)))
    base = os.path.normcase(str(parent))
    try:
        return os.path.commonpath([child, base]) == base
    except ValueError:
        return False

worktrees_anchor = repo / ".worktrees"
reject_link_or_reparse(worktrees_anchor, ".worktrees anchor")
worktrees_dir = worktrees_anchor.resolve(strict=False)
if not ensure_contained(worktrees_dir, repo):
    raise SystemExit("resolved .worktrees anchor must remain under the repo root before pre-add checks")
try:
    reject_link_or_reparse(metadata_path, "metadata path")
    reject_link_or_reparse(worktree_path, "existing worktree path", allow_missing=True)
    metadata_path_resolved = metadata_path.resolve(strict=False)
    if not ensure_contained(metadata_path_resolved, worktrees_dir):
        raise SystemExit("metadata path escaped verified repo-local .worktrees before read")
    data = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(
            "Existing metadata is malformed or unreadable: top-level JSON value must be an object. "
            "Stop and reconcile or replace the metadata file before continuing."
        )
except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
    raise SystemExit(
        f"Existing metadata is malformed or unreadable: {exc}. "
        "Stop and reconcile or replace the metadata file before continuing."
    )
metadata_path = metadata_path_resolved
worktree_path = worktree_path.resolve(strict=False)
branch_exists = subprocess.run(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"], cwd=repo).returncode == 0
worktree_exists = worktree_path.exists()
if (branch_exists or worktree_exists) and (not data.get("featureBranch") or not data.get("worktreePath")):
    raise SystemExit(
        "target branch or worktree path already exists while metadata is incomplete; "
        "repair metadata only after verifying this branch/path belongs to the run, "
        "or stop with recovery instructions before retrying git worktree add"
    )
PY

if git -C "$REPO_ROOT" worktree add "$WORKTREE_PATH" -b "$BRANCH_NAME" "$MAIN_BASE"; then
  if python - <<'PY'
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath

repo = Path(os.environ["REPO_ROOT"]).resolve()
metadata_path = Path(os.environ["METADATA_PATH"])
worktree_path = Path(os.environ["WORKTREE_PATH"])

def is_reparse_point(st):
    return bool(
        getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        and (getattr(st, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    )

def reject_link_or_reparse(path, label, allow_missing=False):
    try:
        st = path.lstat()
    except FileNotFoundError:
        if allow_missing:
            return None
        raise
    except OSError as exc:
        raise SystemExit(f"{label} could not be lstat-checked before use: {exc}")
    if stat.S_ISLNK(st.st_mode) or is_reparse_point(st):
        raise SystemExit(f"{label} must not be a symlink, junction, or reparse point")
    return st

def ensure_contained(path, parent):
    child = os.path.normcase(str(path.resolve(strict=False)))
    base = os.path.normcase(str(parent))
    try:
        return os.path.commonpath([child, base]) == base
    except ValueError:
        return False

worktrees_anchor = repo / ".worktrees"
reject_link_or_reparse(worktrees_anchor, ".worktrees anchor")
worktrees_dir = worktrees_anchor.resolve(strict=False)
if not ensure_contained(worktrees_dir, repo):
    raise SystemExit("resolved .worktrees anchor must remain under the repo root before post-add update")
try:
    reject_link_or_reparse(metadata_path, "metadata path")
    reject_link_or_reparse(worktree_path, "worktree path")
    metadata_path_resolved = metadata_path.resolve(strict=False)
    worktree_path_resolved = worktree_path.resolve(strict=False)
    if not ensure_contained(metadata_path_resolved, worktrees_dir) or not ensure_contained(worktree_path_resolved, worktrees_dir):
        raise SystemExit("metadata/worktree path escaped verified repo-local .worktrees during post-add update")
    data = json.loads(metadata_path.read_text(encoding="utf-8"))
except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
    raise SystemExit(
        f"Existing metadata is malformed or unreadable: {exc}. "
        "Stop and reconcile or replace the metadata file before continuing."
    )
metadata_path = metadata_path_resolved
worktree_path = worktree_path_resolved
worktree_relpath = worktree_path.relative_to(repo).as_posix()
expected_branch = os.environ["BRANCH_NAME"]
expected_worktree = worktree_relpath

def stop_for_post_add_metadata(message):
    raise SystemExit(
        f"Post-add metadata revalidation failed: {message}. "
        "Roll back the just-created worktree/branch, then reconcile or replace the metadata file before continuing."
    )

def validate_persisted_metadata_path(value, run_id):
    if not isinstance(value, str):
        stop_for_post_add_metadata("metadataPath must be a string")
    rel = PurePosixPath(value)
    expected = PurePosixPath(".worktrees") / f"{run_id}.metadata.json"
    if (
        rel.is_absolute()
        or rel.parts[:1] != (".worktrees",)
        or ".." in rel.parts
        or rel.parent != PurePosixPath(".worktrees")
        or len(rel.parts) != 2
        or rel != expected
    ):
        stop_for_post_add_metadata(
            "metadataPath must be exactly .worktrees/<runId>.metadata.json, "
            "top-level under .worktrees, repo-relative POSIX, and contain no parent traversal"
        )
    if rel.as_posix() != metadata_path.relative_to(repo).as_posix():
        stop_for_post_add_metadata("metadataPath must match the actual metadata file path being read")
    persisted_path = repo / Path(*rel.parts)
    persisted_child = os.path.normcase(str(persisted_path.resolve(strict=False)))
    persisted_parent = os.path.normcase(str(worktrees_dir))
    try:
        contained = os.path.commonpath([persisted_child, persisted_parent]) == persisted_parent
    except ValueError:
        contained = False
    if not contained:
        stop_for_post_add_metadata("metadataPath must resolve under repo-local .worktrees")

def validate_required_metadata_schema(data):
    if not isinstance(data, dict):
        stop_for_post_add_metadata("top-level JSON value must be an object")
    required = [
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
    ]
    missing = [field for field in required if field not in data]
    if missing:
        stop_for_post_add_metadata("missing required field(s): " + ", ".join(missing))
    if data["schemaVersion"] != 1:
        stop_for_post_add_metadata("schemaVersion must be 1")
    if not isinstance(data["runId"], str):
        stop_for_post_add_metadata("runId must be a string")
    if data["status"] != "active":
        stop_for_post_add_metadata("status must be exactly active")
    if not isinstance(data["mainBranch"], str) or not data["mainBranch"].strip():
        stop_for_post_add_metadata("mainBranch must be a non-empty string")
    if not isinstance(data["mainBase"], str) or not re.fullmatch(r"[0-9a-fA-F]{40}", data["mainBase"]):
        stop_for_post_add_metadata("mainBase must be a 40-character commit SHA")
    if data["featureBranch"] is not None and not isinstance(data["featureBranch"], str):
        stop_for_post_add_metadata("featureBranch must be null or a string")
    if data["worktreePath"] is not None and not isinstance(data["worktreePath"], str):
        stop_for_post_add_metadata("worktreePath must be null or a string")
    validate_persisted_metadata_path(data["metadataPath"], data["runId"])
    if data["preexistingTrackedCheckpoint"] is not None and not isinstance(data["preexistingTrackedCheckpoint"], str):
        stop_for_post_add_metadata("preexistingTrackedCheckpoint must be null or a string")
    for field in ["temporaryCheckpoints", "preexistingUntracked", "preexistingIgnored"]:
        if not isinstance(data[field], list):
            stop_for_post_add_metadata(f"{field} must be a list")
        if not all(isinstance(item, str) for item in data[field]):
            stop_for_post_add_metadata(f"{field} entries must be strings")

validate_required_metadata_schema(data)
if data.get("runId") != os.environ["RUN_ID"]:
    raise SystemExit("post-add metadata update refusing different runId; roll back the just-created worktree/branch, then reconcile or replace the metadata file before continuing")
if data.get("status") != "active":
    raise SystemExit("post-add metadata update requires status active; completed, abandoned, missing, or other statuses require rollback and metadata reconciliation before continuing")
if data.get("featureBranch") not in (None, "", expected_branch):
    raise SystemExit("post-add metadata update found a populated featureBranch mismatch; roll back the just-created worktree/branch, then reconcile or replace the metadata file before continuing")
if data.get("worktreePath") not in (None, "", expected_worktree):
    raise SystemExit("post-add metadata update found a populated worktreePath mismatch; roll back the just-created worktree/branch, then reconcile or replace the metadata file before continuing")

data.update({
    "featureBranch": expected_branch,
    "worktreePath": expected_worktree,
})

metadata_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
  then
    cd "$WORKTREE_PATH"
  else
    echo "git worktree add succeeded but metadata update failed; leaving the just-created worktree and branch in place for inspection." >&2
    echo "Stop before dispatching agents. Reconcile or replace the metadata file, or remove the worktree/branch only after verifying they contain no wanted changes." >&2
    exit 1
  fi
else
  exit 1
fi
```

Before relying on this lifecycle, dry-run the failure path mentally and with a disposable repository: setup must reject a linked worktree and ask the user to return to the original main worktree before `.worktrees` is derived from `git rev-parse --show-toplevel`; all shell and Python path work must then be anchored to `REPO_ROOT`, not the caller's current directory; the repo root must be resolved first, then the `.worktrees` anchor must be `lstat`-checked for symlink, junction, mount-point, or other reparse status and its resolved path must be contained under the resolved repo root before it becomes the trusted anchor for any metadata path; an explicit metadata path means upstream metadataPath mode and must reject `RUN_ID` or `NO_UPSTREAM_METADATA=true` before path validation, then validate the path syntactically as exactly `.worktrees/<run-id>.metadata.json`, with a top-level `.worktrees` parent, one filename, and no nested path segments, reject filename-derived `runId` values that fail the filesystem-safe runId contract, check with `lstat` plus platform reparse attributes/tags for a symlinked, junctioned, or reparse-point final path, and check for resolved child containment under the already verified `.worktrees` anchor before any `exists()`, `read_text()`, or JSON parsing that follows the target; if no exact metadata path is passed and `NO_UPSTREAM_METADATA=true` is not present, lookup must reject any supplied `RUN_ID` before candidate search, then search repo-level `.worktrees/*.metadata.json`, run lstat/reparse and verified-anchor containment checks for each globbed top-level metadata file, stop on symlinked, junctioned, reparse-point, containment-escape, or other filesystem safety failures before read, skip filename/runId contract violations such as stale manual `legacy note.metadata.json` files as invalid non-candidates without reading them or counting them toward zero/one/multiple active candidates, read JSON only from read-eligible `.worktrees/<run-id>.metadata.json` files with filesystem-safe `runId`, use the single `status: "active"` candidate with null or empty `featureBranch` and `worktreePath` when exactly one exists, stop with reconcile-or-replace guidance if a read-eligible candidate has malformed, invalid UTF-8, or unreadable JSON, and stop for the exact metadata path or user direction on both zero-candidate and ambiguous-candidate lookup cases; if `NO_UPSTREAM_METADATA=true` is present, setup must not auto-search or reuse existing active metadata candidates and must derive `.worktrees/$RUN_ID.metadata.json` only from a filesystem-safe provided `RUN_ID` so direct-entry creation can proceed; the disposable run must include a PASS case for `NO_UPSTREAM_METADATA=true` plus `RUN_ID` direct entry; direct evidence that a normal `.worktrees` anchor resolves under the repo root; FAIL/STOP cases for RUN_ID-only direct entry without the no-upstream signal, explicit metadata path plus `RUN_ID`, exact upstream `metadataPath` provided but file missing, zero active metadata candidates, ambiguous active metadata candidates, `.worktrees/nested/foo.metadata.json`, globbed top-level invalid filename/runId leftovers skipped as invalid non-candidates without read, and a Windows `.worktrees` junction/reparse anchor or final metadata-path reparse point when the platform supports creating one; because the trusted anchor is fixed as `repo/.worktrees` and symlink, junction, and reparse anchors are rejected before trust, a resolved-anchor containment escape is unreachable except through an anchor redirection that must stop before metadata handling; validate the reachable branches by showing a normal anchor containment PASS and a redirected anchor STOP; the missing exact upstream metadataPath FAIL case must produce upstream correction guidance to reconcile or recreate the handed-off metadata file or ask for the exact correct metadata path, without `RUN_ID` or direct-entry guidance; persisted `metadataPath` and `worktreePath` values must be repo-relative POSIX-style paths with forward slashes; symlinked, junctioned, reparse-point, or unignored `.worktrees` must be rejected before metadata is written; metadata and worktree paths must not escape the verified repo-local `.worktrees` anchor through symlinks, junctions, reparse points, or any other redirected path component, and `worktreePath` must stay repo-local for this skill flow; existing `featureBranch`/`worktreePath` must cause a stop-and-ask error; `completed`, `abandoned`, missing, or non-`active` metadata status must be rejected; reused metadata with any missing required field, any wrong type, missing or blank `mainBranch`, missing or structurally invalid `mainBase`, non-null/non-empty pre-setup `featureBranch` or `worktreePath`, missing `preexistingTrackedCheckpoint`, non-list `temporaryCheckpoints`, non-list `preexistingUntracked`, or non-list `preexistingIgnored` must be rejected as incomplete metadata instead of backfilled; malformed JSON, invalid UTF-8 metadata, or an unreadable metadata file must be caught as `OSError`, `UnicodeDecodeError`, or `json.JSONDecodeError` and reported with a clear reconcile-or-replace instruction rather than a raw traceback; direct-entry metadata creation must stop and require the upstream recording step (`writing-specs`) when preexisting tracked, untracked, unsafe ignored state exists, while retained ignored `.worktrees/*.metadata.json` files with `completed` or `abandoned` status may be ignored only after the same lstat, reparse, verified-anchor, and containment checks before read; target branch or worktree path already exists must trigger repair metadata or stop with recovery instructions before retrying `git worktree add`; `mainBase` must pass `git rev-parse --verify "$MAIN_BASE^{commit}"` before `git worktree add`; a failed `git worktree add` path must not write `featureBranch` or `worktreePath` or run `cd "$WORKTREE_PATH"`; after `git worktree add` succeeds, the metadata update must immediately re-read and revalidate the same required schema and persisted `metadataPath` contract as pre-add reuse, then verify that `runId` still matches, `status` is still `active`, and existing `featureBranch`/`worktreePath` are unset or already match the expected branch and repo-local worktree path; post-add revalidation must reject missing or ill-typed required fields, invalid persisted `metadataPath`, `completed` or `abandoned` metadata, and populated mismatches with rollback and reconcile-or-replace guidance instead of overwriting lifecycle state; if `git worktree add` succeeds but the metadata update fails, the example must either roll back the just-created worktree/branch or stop with an explicit metadata reconciliation requirement; and a detached HEAD or empty `git branch --show-current` result must stop before blank `mainBranch` metadata can be written for direct-entry metadata.

Run project setup (npm install / cargo build / pip install / go mod download) and verify tests pass before proceeding.

When dispatching downstream agents, pass the metadata path when relevant so fresh implementers, reviewers, and the finishing workflow can read recorded state instead of relying on hidden session memory.

## The Process

1. Read plan, extract all tasks, create and maintain `update_plan` steps
2. **For each task, keep implementation sequential: never run multiple `implementer` subagents in parallel for the same plan. Reviewer subagents may run in parallel as described below.**
   a. Dispatch `implementer` subagent
      - After dispatching, let it work. Do not keep checking in unless it is blocked, needs approval, or has clearly failed.
   b. Handle implementer status:
      - NEEDS_CONTEXT → answer their questions, re-dispatch implementer from (a)
      - DONE / DONE_WITH_CONCERNS → continue to (c)
   c. Dispatch `spec-code-reviewer` and `quality-code-reviewer` in parallel for the same git range
      - Treat each review as a single review pass, not an open-ended conversation.
      - Wait for whichever review returns first instead of repeatedly polling both.
      - Before dispatching reviews, and again when review output returns, read and follow the `code-review` skill for review dispatch, triage, validation, spec gating, and reviewer pushback.
      - **5 consecutive review loops without both reviewers approving → stop loop, orchestrator assesses and decides next step**
      - Both approved → mark task complete, advance to next task
3. After all tasks complete: dispatch `quality-code-reviewer` for the **entire implementation** (full git range)
4. Invoke `finishing-a-development-branch` skill

## Dispatching Subagents

Three custom subagents, dispatched by name via `spawn_agent`:

**`implementer`** — Implements a single task using TDD.
Dispatch with: task description, spec/plan paths, working directory, metadata path, context about dependencies.

**`spec-code-reviewer`** — Verifies whether the current implementation slice matches the requested spec-defined behavior and scope. This reviewer is the gate for the entire review pass.
Dispatch with: description, spec/plan paths, metadata path, git range (Base..Head).

**`quality-code-reviewer`** — Reviews engineering quality for the current implementation slice.
Dispatch with: description, spec/plan paths, metadata path, git range (Base..Head).

For every subagent dispatch in this skill:
- provide complete task context up front
- include the metadata path when it is relevant to the task, review range, or finishing handoff
- wait for the decisive result instead of repeatedly polling
- if more context is needed, answer once clearly and re-dispatch a fresh pass
- follow the `code-review` skill before dispatching reviews and when deciding whether spec feedback actually gates the pass

### Example Dispatch

```
spawn_agent:
  agent_type: implementer
  fork_context: false
  message: |
    Task 3: Implement user authentication endpoint

    Spec: docs/double-sdd/specs/auth-spec.md
    Plan: docs/double-sdd/plans/auth-plan.md
    Work from: .worktrees/feature-auth
    Metadata: .worktrees/20260629-120000-auth.metadata.json

    Context: This builds on the session middleware from Task 2.
    The database schema is already in place (see db/schema.ts).
```

```
spawn_agent:
  agent_type: spec-code-reviewer
  fork_context: false
  message: |
    Description: Task 3: user authentication endpoint

    Spec: docs/double-sdd/specs/auth-spec.md
    Plan: docs/double-sdd/plans/auth-plan.md
    Metadata: .worktrees/20260629-120000-auth.metadata.json
    Base: abc1234
    Head: def5678
```

```
spawn_agent:
  agent_type: quality-code-reviewer
  fork_context: false
  message: |
    Description: Task 3: user authentication endpoint

    Spec: docs/double-sdd/specs/auth-spec.md
    Plan: docs/double-sdd/plans/auth-plan.md
    Metadata: .worktrees/20260629-120000-auth.metadata.json
    Base: abc1234
    Head: def5678
```

## Temporary Checkpoint Policy

Commits inside the isolated worktree are temporary workflow checkpoints. They are useful for review ranges and recovery while the plan is running, but final integration must not preserve the temporary checkpoint chain.

Record useful checkpoint commit identifiers in the `temporaryCheckpoints` array in the non-committed metadata file, not in committed specs. Pass the metadata path to reviewers, implementers, and the finishing workflow when relevant so downstream agents can read checkpoint context from the JSON artifact.

## Handling Implementer Status

**DONE:** Proceed to the paired review dispatch.

**DONE_WITH_CONCERNS:** Read the concerns. If about correctness or scope, address before review. If observations (e.g., "this file is getting large"), note and proceed.

**NEEDS_CONTEXT:** Provide missing context and resume it.

**BLOCKED:** Assess the blocker:
1. If it's a context problem, provide more context and resume it
2. If the task is too large, break it into smaller pieces
3. If the plan itself is wrong, verify the blocker is real. Then:
      - If the fix is local to the plan (does not contradict the spec or invalidate completed tasks) → fix the plan yourself and re-dispatch
      - Otherwise → escalate to the human

**Never** ignore an escalation or force retry without changes. If the implementer said it's stuck, something needs to change.

## Evaluating Reviewer Feedback

Subagent reviewers catch real issues, but they also overreach and miss context. **Verify before implementing. Technical correctness over reviewer confidence.**

- Review output is input to evaluate, not an order to follow.
- If a reported compliance mismatch, required fix, or other review finding is real, still decide whether it should be fixed now, deferred, or skipped.
- For the full review-handling rules, read and follow the `code-review` skill.
- Keep the workflow moving until the full plan is complete unless you hit a real unresolved issue you cannot solve inside the current plan/spec boundary.

## Red Flags

**Never:**
- Implement the code yourself instead of using sub-agents.
- Start implementation on main/master branch without explicit user consent
- Skip reviews (spec compliance OR code quality)
- Proceed with unfixed issues
- Dispatch multiple implementation subagents in parallel (conflicts)
- Skip scene-setting context (subagent needs to understand where task fits)
- Ignore subagent questions (answer before letting them proceed)
- Accept "close enough" on spec compliance
- Skip review loops (reviewer found issues = implementer fixes = review again)
- Let implementer self-review replace actual review (both are needed)
- Treat code quality review as actionable before spec compliance passes
- Treat a raw reviewer `FAIL` as automatically decisive before verifying it
- Stop the workflow just because one review loop is inconvenient, noisy, or inconclusive
- Move to next task while either review gate has open issues

**If subagent asks questions:** Answer clearly and completely. Don't rush them.

**If reviewer returns `FAIL`:** verify the reported compliance mismatches or required fixes, send confirmed fixes back through the implementer, then re-review until approved.

**If subagent fails task:** Dispatch fix subagent with specific instructions. **Don't fix manually** (context pollution).

## Integration

**Required workflow skills:**
- **`writing-plans`** — Creates the plan this skill executes
- **`finishing-a-development-branch`** — Complete development after all tasks
