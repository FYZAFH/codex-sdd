---
name: finishing-a-development-branch
description: Use when implementation is complete or a development branch needs safe closure, and you need to apply changes back as uncommitted local changes, retain the branch, or discard work while test-gating completion paths
---

# Finishing a Development Branch

## Overview

Guide completion or safe closure of development work by presenting clear local-only options and handling the chosen workflow.

**Core principle:** Verify tests -> resolve metadata -> present allowed local-only options -> apply uncommitted changes, keep, or discard -> update metadata only after delivery -> clean up.

Normal completion applies the task result to the original main worktree as uncommitted file changes. It must not create commits, integrate branches, update remotes, or open PRs as part of finishing. If the user wants any of those actions, they can do them manually after the changes are present in the original main worktree.

**Announce at start:** "I'm using the finishing-a-development-branch skill to complete this work."

## The Process

### Completed Cleanup Recovery Entry Path

If the user explicitly requests cleanup for metadata that is already `status: completed` and provides the exact metadata path, enter the completed cleanup recovery entry path instead of the normal top-level finishing flow. This single entry path covers legacy retained PR worktree cleanup and completed Option 1 apply-back cleanup. It is keyed by the exact user-provided metadata path and metadata `status: completed`; automatic metadata matching must not enter it.

Before Step 7, require an explicit user branch action for the completed cleanup recovery:
- Preserve the branch after worktree cleanup. This is the retained/legacy behavior and forbids branch deletion.
- Delete the temporary branch after completed apply-back. This is allowed only when the user explicitly confirms Option 1 apply-back already delivered the final contents.

When branch deletion is selected and `git worktree list --porcelain` shows the target worktree is already absent, require the exact previously reported pre-removal branch identity token before deleting the branch. If that token is unavailable or mismatched, preserve the branch and limit recovery to non-deleting cleanup only.

For this completed cleanup recovery path, skip Step 1 test verification and skip Steps 4-6 option presentation/execution. Do not run or re-run apply-back, do not discard work, and do not allow publication, history rewriting, or metadata status changes from this entry. If completed cleanup recovery metadata validation or explicit branch-action selection fails, stop and ask the user instead of falling back to normal finishing or automatic metadata matching.

### Abandoned Discard Cleanup Recovery Entry Path

If the user explicitly requests abandoned discard cleanup recovery from a previously confirmed discard and provides the exact metadata path, enter the abandoned discard cleanup recovery entry path instead of the normal top-level finishing flow. In this abandoned cleanup recovery path, validate the exact metadata path and abandoned cleanup metadata using the Step 2 abandoned cleanup recovery rules, then proceed directly to Step 7 cleanup only.

For this abandoned cleanup recovery path, skip Step 1 test verification and skip Steps 4-6 option presentation/execution. Do not allow apply-back, a new discard decision, publication, history rewriting, or metadata status changes from this entry. If abandoned cleanup recovery metadata validation fails, stop and ask the user instead of falling back to normal finishing or automatic metadata matching.

### No-Metadata Cleanup Recovery Entry Path

If the user explicitly requests cleanup recovery for a previously started no-metadata cleanup and provides exact recorded no-metadata cleanup evidence, enter the no-metadata cleanup recovery entry path instead of the normal top-level finishing flow. This entry covers only partial no-metadata Option 1 cleanup after tracked apply-back and all approved file copies already succeeded, or partial no-metadata discard cleanup after the exact typed `discard` confirmation already happened. It must not be entered from automatic branch/worktree discovery.

For this no-metadata cleanup recovery path, skip Step 1 test verification, skip Step 3 current-branch/current-worktree discovery, and skip Steps 4-6 option presentation/execution. Do not ask for an apply-back destination or diff base, do not run or re-run apply-back, do not create a new discard decision, and do not guess the target branch or target worktree after the feature worktree is gone.

Require exact recorded evidence before resuming Step 7 cleanup:
- The prior no-metadata cleanup flow: Option 1 after successful apply-back, or Option 3 discard after exact typed `discard`.
- For prior no-metadata Option 1, a valid pre-cleanup handoff captured after apply-back/file copies and before Step 7 cleanup starts: prior flow `Option 1`, successful tracked apply-back, successful approved file copies for all approved untracked or ignored files, exact cleanup checkout path and cleanup checkout branch, feature branch, feature worktree path, feature branch tip, pre-removal branch identity token from the feature worktree `HEAD`, and any unavailable branch identity token state.
- Exact `<feature-branch>` and exact `<feature-worktree-path>`.
- Exact cleanup checkout path and cleanup checkout branch used or recorded for safe cleanup.
- The pre-removal branch identity token captured from the feature worktree `HEAD`.
- The local `refs/heads/<feature-branch>` tip captured before removal.
- Separate cleanup-state/failure evidence captured during or after the prior cleanup attempt: whether worktree removal succeeded, whether branch deletion remains, whether forced worktree removal was explicitly accepted during cleanup, and whether branch deletion was explicitly confirmed during cleanup before failure.

Validate the recorded cleanup checkout before any remaining cleanup: it must be the exact recorded cleanup checkout path/branch, it must not be inside `<feature-worktree-path>`, it must not be attached to `refs/heads/<feature-branch>`, and it must have no active merge, rebase, cherry-pick, or bisect. Validate branch/worktree identity from the evidence before deletion: if the target worktree still exists, `git worktree list --porcelain` must show the exact `<feature-worktree-path>` attached to `refs/heads/<feature-branch>`, the target worktree `HEAD` must match the recorded pre-removal branch identity token, and the current local `refs/heads/<feature-branch>` tip must match that same token. If the target worktree is already absent, porcelain output must have no record for the exact `<feature-worktree-path>`, and the current local branch tip must still match the recorded pre-removal branch identity token before any branch deletion. If any required identity token is unavailable, mismatched, or cannot be validated, stop and preserve the branch; do not delete by name alone.

No-metadata recovery may complete only the remaining validated worktree removal and branch-deletion cleanup. For no-metadata Option 1 recovery, branch deletion is allowed only if exact recovery evidence includes the valid pre-cleanup handoff plus explicit branch-deletion confirmation captured during cleanup before failure for the exact unmerged `<feature-branch>`. For no-metadata discard recovery, the exact typed `discard` confirmation is not enough for branch deletion; branch deletion is allowed only if exact cleanup evidence also records the additional explicit force branch deletion confirmation captured before the branch deletion attempt. If the recorded confirmation is absent, preserve the branch.

### Step 1: Verify Tests

**Before presenting completion options, verify tests pass:**

```bash
# Run the project's test suite
npm test / cargo test / pytest / go test ./...
```

If tests fail, completion is unavailable. Continue to Step 2 only far enough to resolve metadata and present or execute cleanup-safe non-completion choices. Do not apply changes back to the destination worktree and do not transition metadata to `completed` until tests pass. Discard remains reachable only after all discard prechecks, exact typed discard confirmation, active-operation guards, metadata `abandoned` transition rules, and exact-path recovery rules.

**If tests pass:** Continue to Step 2 with apply-back completion available.

### Step 2: Recorded-Base Metadata and Base Branch Authority

If this branch was created by `subagent-driven-development`, prefer the exact `.worktrees/<run-id>.metadata.json` path provided by the orchestrator.

If no path is provided, search the repo-local `.worktrees/*.metadata.json` directory under the shared checkout root for active metadata whose `featureBranch` matches the current branch or whose `worktreePath` matches the current worktree. Ignore `completed` and `abandoned` metadata files during automatic matching.

Automatic matching must use this per-candidate safety sequence before any JSON read or match decision:
1. Resolve the shared checkout root from `git rev-parse --git-common-dir`, then resolve the repo-local `.worktrees` anchor from that shared root.
2. Validate the `.worktrees` anchor with `lstat`, symlink, junction, reparse-point, and resolved-containment checks before enumerating candidates.
3. Enumerate only top-level `.worktrees/*.metadata.json` candidates from the validated anchor.
4. For each candidate, perform full metadata path validation before any JSON read: the candidate path must be exactly `.worktrees/<run-id>.metadata.json` relative to the shared checkout root, the `<run-id>` must be filesystem-safe using the same safe character rules as the metadata contract, and the suffix must be `.metadata.json`.
5. Reject any candidate with parent traversal, absolute paths, drive prefixes, nested path segments below `.worktrees`, path separators inside `<run-id>`, an empty `<run-id>`, shell metacharacters, or non-ASCII characters.
6. For each candidate that passes the path contract, run `lstat`, symlink, junction, reparse-point, and resolved-containment checks before any JSON read.
7. Only after a candidate passes full metadata path validation and filesystem checks may its JSON be read and considered for automatic matching.
8. Candidates failing any path-contract, `lstat`, reparse/junction/symlink, or containment check stop the flow immediately before JSON read; do not ignore them and do not let them participate in matching.
9. After safe candidate validation and JSON parsing, ignore `completed` and `abandoned` metadata during active automatic matching.

If the user explicitly asks to clean up already completed metadata and provides an exact metadata path, treat that as completed cleanup recovery re-entry. This is a Step 7-only cleanup mode. After exact metadata validation and explicit branch-action selection, exit the normal top-level flow and proceed directly to Step 7 cleanup only. Do not use automatic metadata matching for this mode, and do not proceed to apply-back, a new apply-back decision, discard, publication, history rewriting, or metadata status changes from the non-attached checkout.

If the user explicitly asks for abandoned discard cleanup recovery from a previously confirmed discard and provides an exact metadata path, treat that as abandoned discard cleanup recovery re-entry. This is a Step 7-only cleanup mode. After exact metadata validation for abandoned cleanup recovery, exit the normal top-level flow and proceed directly to Step 7 cleanup only. Do not use automatic metadata matching for this mode, and do not proceed to apply-back, a new discard decision, publication, history rewriting, or metadata status changes from the non-attached checkout.

Metadata lookup outcomes are authoritative:
- If zero active metadata files match the current branch or worktree, stop and ask the user to provide the exact metadata path or confirm this is an ordinary non-SDD branch with no recorded-base metadata expected. Do not guess and do not silently bypass cleanup for a possible SDD branch.
- If exactly one active metadata file matches, validate and use it.
- If more than one active metadata file matches, stop and ask the user which metadata file applies.
- If the orchestrator provided an explicit metadata path and that metadata is missing, malformed, invalid, stale, or mismatched, stop and ask the user instead of falling back to no metadata.
- In completed cleanup recovery re-entry, if the exact user-provided metadata path is missing, malformed, invalid, stale, or does not identify the completed target worktree and branch or verified absence state, stop and ask the user instead of falling back to no metadata.
- In completed cleanup recovery re-entry, if the user has not explicitly selected whether to preserve the branch or delete the temporary branch after completed apply-back, stop and ask the user instead of inferring branch deletion from metadata.
- In abandoned discard cleanup recovery re-entry, if the exact user-provided metadata path is missing, malformed, invalid, stale, or does not identify the abandoned target worktree and branch or verified absence state, stop and ask the user instead of falling back to no metadata.

#### Consumer Metadata Validation

Before any read, update, or use of `mainBase`, complete consumer-side metadata validation. If the metadata is malformed, stale, or fails any validation check, stop instead of guessing.

Validate the metadata file path first:
- The path must be repo-relative and must exactly match the top-level pattern `.worktrees/<run-id>.metadata.json`.
- `<run-id>` must be filesystem-safe: ASCII letters, numbers, `.`, `_`, and `-` only. Reject path separators, drive prefixes, `..`, shell metacharacters, empty values, and non-ASCII characters.
- Define the shared checkout root before resolving metadata paths. For normal non-bare repositories, run `git rev-parse --git-common-dir`, normalize it to an absolute path, require that it identifies the shared `.git` directory, and use that directory's parent as the shared checkout root. If `git rev-parse --git-common-dir` does not identify a normal shared `.git` directory, stop and ask before using recorded-base metadata.
- Resolve the repo-local `.worktrees` directory, `metadataPath`, and metadata `worktreePath` from the shared checkout root. Do not use `git rev-parse --show-toplevel` as the metadata root when inside a linked worktree, because `show-toplevel` resolves to the linked feature worktree itself.
- Reject absolute paths, nested `.worktrees` paths, symlink escapes, reparse-point escapes, junction escapes, and any final-path escape outside the repo-local `.worktrees` directory.
- On Windows, compare normalized absolute paths case-insensitively when checking containment under repo-local `.worktrees`.

Validate the JSON payload before using operational fields:
- `schemaVersion` must be integer `1`.
- `runId` must match the filename run id.
- `metadataPath` must be a string that exactly matches the repo-relative path of the file being read.
- In normal finishing mode, `status` must remain string `active`; stop on `completed`, `abandoned`, missing, or any other stale status.
- In completed cleanup recovery re-entry, the exact user-provided metadata path is completed cleanup context, not an active automatic lookup. `status` must be `completed`; stop on `active`, `abandoned`, missing, or any other stale status.
- In abandoned discard cleanup recovery re-entry, the exact user-provided metadata path is abandoned cleanup recovery context, not an active automatic lookup. `status` must be `abandoned`; stop on `active`, `completed`, missing, or any other stale status.
- `mainBranch`, `mainBase`, `featureBranch`, and `worktreePath` must be present with valid types.
- `mainBranch` and `featureBranch` must be non-empty strings naming branches.
- `mainBase` must be a 40-character hexadecimal commit id that resolves in this repository.
- In normal finishing mode, after `mainBase` resolves, verify it is an ancestor of the current feature `HEAD` and that the merge base between `mainBase` and the current feature `HEAD` is exactly `mainBase`. If either check fails, stop because the metadata is stale or mismatched.
- In completed cleanup recovery re-entry, do not use the current checkout `HEAD` as the feature lineage check. Validate the completed target worktree and branch from `git worktree list --porcelain`, or validate the exact target worktree's absence from that output when recovering after worktree removal already happened, then allow only Step 7 cleanup.
- In abandoned discard cleanup recovery re-entry, do not use the current checkout `HEAD` as the feature lineage check. Validate the abandoned target worktree and branch from `git worktree list --porcelain`, or validate the exact target worktree's absence from that output when recovering after worktree removal already happened, then allow only Step 7 cleanup.
- `worktreePath` must be a non-empty repo-relative string when metadata is being used for finishing. Reject `null`, empty strings, absolute paths, drive-prefixed paths, paths containing `..`, and paths outside the repo-local `.worktrees` directory under the shared checkout root.
- Resolve `worktreePath` from the shared checkout root and confirm the final normalized path remains under the repo-local `.worktrees` directory. In normal finishing mode, compare that final path with the current linked worktree path from `git rev-parse --show-toplevel` or an equivalent current-checkout top-level query. In completed cleanup recovery re-entry, compare that final path with the target worktree path recorded by `git worktree list --porcelain`, or confirm the porcelain output has no record for that exact normalized path before treating worktree removal as already completed. In abandoned discard cleanup recovery re-entry, compare that final path with the target worktree path recorded by `git worktree list --porcelain`, or confirm the porcelain output has no record for that exact normalized path before treating worktree removal as already completed. On Windows, perform final absolute-path comparisons case-insensitively.
- `temporaryCheckpoints` must be an array when present, and `preexistingTrackedCheckpoint` must be `null` or a string when present.

When metadata exists and passes validation, read:
- `mainBranch`
- `mainBase`
- `featureBranch`
- `worktreePath`
- `temporaryCheckpoints`
- `preexistingTrackedCheckpoint`
- `metadataPath`
- `status`

Use `mainBase` as the recorded diff anchor for task extraction and cleanup validation.

When `preexistingTrackedCheckpoint` is non-null, treat that checkpoint as user pre-existing tracked state, not as task work or an ordinary temporary checkpoint. Before apply-back:
- Verify the checkpoint resolves in this repository and is in the lineage between `mainBase` and the current `HEAD`; if it does not resolve, is not descended from `mainBase`, or is not an ancestor of the current `HEAD`, stop and ask because the metadata no longer safely describes this branch.
- Explain the required split: the pre-existing tracked diff is `mainBase..preexistingTrackedCheckpoint`, and the task diff is `preexistingTrackedCheckpoint..HEAD`, subject to later edits in the working tree or index.
- Apply the task diff back separately from the pre-existing tracked diff.
- Keep `mainBase..preexistingTrackedCheckpoint` separate from the task diff; never fold the pre-existing tracked diff into the task result, even with user approval.
- If the pre-existing tracked diff and task diff overlap or cannot be separated safely, preserve the feature worktree and stop before apply-back.

In the non-null `preexistingTrackedCheckpoint` path, a plain direct reset to `mainBase` is always unsafe and forbidden. Direct reset to `mainBase` is valid only when `preexistingTrackedCheckpoint` is `null`. When `preexistingTrackedCheckpoint` is non-null, require checkpoint-aware separation or reconstruction using `mainBase..preexistingTrackedCheckpoint` and `preexistingTrackedCheckpoint..HEAD`; if safe separation or reconstruction is impossible, preserve the worktree and stop and ask. Do not discard the pre-existing tracked checkpoint contents, and do not let those edits be silently folded into the task result.

For normal finishing from the feature checkout, validate that the current branch is not detached. When metadata exists, validate that metadata `featureBranch` matches the current branch and that metadata `worktreePath` matches the current worktree when available. If these checks fail, stop and ask the user.

For completed cleanup recovery re-entry, require all of the following before Step 7 cleanup:
- The user explicitly requested cleanup of already completed metadata and provided the exact metadata path.
- The user explicitly selected one branch action: preserve the branch after worktree cleanup, or delete the temporary branch after completed apply-back.
- If the selected action is branch deletion, the user explicitly confirms Option 1 apply-back already delivered the final contents. If the user cannot confirm delivery, preserve the branch.
- The current shell is in the repository but is not inside the target worktree from metadata when that target still exists.
- `git worktree list --porcelain` either contains a `worktree` record whose normalized path exactly matches metadata `worktreePath` and whose branch entry is `refs/heads/<feature-branch>`, or contains no `worktree` record for that exact normalized path when recovering after worktree removal already happened.
- Before deleting a branch, verify the local branch ref is exactly `refs/heads/<feature-branch>`, and verify branch identity. If the target worktree still exists, the local branch tip must match that target worktree `HEAD`. If branch deletion is selected and `git worktree list --porcelain` shows the target worktree is absent, explicitly revalidate the branch tip against the exact previously reported pre-removal branch identity token from the completed cleanup failure report before deletion. If the token is unavailable, mismatched, or cannot prove identity, stop and preserve the branch, and limit recovery to non-deleting cleanup only. If the branch is already absent, report that cleanup recovery has no remaining branch deletion work. These checks are not permission to delete the branch unless the user selected the delete-temporary-branch action.
- The active-operation guard passes for the current cleanup checkout and for the target worktree when accessible.
- The cleanup checkout is the original/main worktree recorded by metadata `mainBranch`, or another safe non-attached checkout that is not the target feature worktree. Do not require that checkout to be clean, because completed apply-back may intentionally leave delivered changes uncommitted in the destination worktree.

In this completed cleanup recovery mode, do not require the current branch or current worktree to match metadata `featureBranch` or `worktreePath`. Use metadata `mainBranch`, `featureBranch`, and `worktreePath` only to identify the cleanup checkout, target worktree, and target branch for Step 7, or to verify that the target worktree is already absent. Do not use automatic active metadata matching for completed cleanup recovery, because completed metadata is ignored by automatic matching. Do not infer branch deletion from `status: completed`, and do not run apply-back again.

For abandoned discard cleanup recovery re-entry, require all of the following before Step 7 cleanup:
- The user explicitly requested cleanup recovery of a previously confirmed discard and provided the exact metadata path.
- The user confirms the original exact typed discard confirmation already happened, and that this entry is only to finish or remediate worktree removal and branch deletion.
- The current shell is in the repository but is not inside the target worktree from metadata when that target still exists.
- `git worktree list --porcelain` either contains a `worktree` record whose normalized path exactly matches metadata `worktreePath` and whose branch entry is `refs/heads/<feature-branch>`, or contains no `worktree` record for that exact normalized path when recovering after worktree removal already happened.
- Before deleting a branch, verify the local branch ref is exactly `refs/heads/<feature-branch>`, and verify branch identity. If the target worktree still exists, the local branch tip must match that target worktree `HEAD`. If the target worktree is absent, explicitly revalidate the branch tip against the exact recorded pre-removal branch identity token before deletion. If the token is unavailable, mismatched, or cannot prove identity, stop and preserve the branch, and limit recovery to non-deleting cleanup only. If the branch is already absent, report that cleanup recovery has no remaining branch deletion work.
- The active-operation guard passes for the current cleanup checkout and for the target worktree when accessible.
- The checkout used to perform cleanup must be concrete and safe: it must not be the target feature worktree, must not be attached to `refs/heads/<feature-branch>`, must have no active merge, rebase, cherry-pick, or bisect, and if any local changes would be affected by switching or deleting, stop and ask before cleanup.

In this abandoned cleanup recovery mode, do not require the current branch or current worktree to match metadata `featureBranch` or `worktreePath`. Use metadata `featureBranch` and `worktreePath` only to identify the target worktree and branch for Step 7, or to verify that the target worktree is already absent. Do not use automatic active metadata matching for abandoned cleanup recovery, because abandoned metadata is ignored by automatic matching.

When validated metadata exists, the recorded `mainBranch` is authoritative. Do not heuristically choose `main`, `master`, or any other destination branch after metadata is found. Use the validated recorded `mainBranch` for Option 1 apply-back and cleanup context for Options 2 and 3, or stop if it is missing, invalid, unavailable, or mismatched with the intended target.

Only after the user confirms this is an ordinary non-SDD branch with no recorded-base metadata expected, proceed to Step 3. Do not guess a destination, do not silently bypass cleanup for a possible SDD branch, and do not run remote-publication or branch-integration fallbacks.

### Step 3: Confirm Feature Context Without Metadata

Only when no recorded-base metadata exists and the user confirms this is an ordinary non-SDD branch, determine and confirm only the current feature branch and current feature worktree from explicit local evidence before Step 4. Do not use ancestry output as a branch-name heuristic. Do not confirm the destination branch, destination worktree, or diff base before the user selects no-metadata Option 1.

Before presenting options, determine the current feature branch:

```bash
git branch --show-current
```

Require a single non-empty current branch name and use that exact value as `<feature-branch>`. If the output is empty because `HEAD` is detached, blank, multi-line, or otherwise ambiguous, stop and ask the user before presenting options.

Before presenting options, determine and confirm the current no-metadata feature worktree path:

```bash
git rev-parse --show-toplevel
```

Require a single normalized checkout path and use it as `<feature-worktree-path>`. If the worktree path is unavailable or ambiguous, stop and ask the user before presenting options.

For no-metadata tests-passing flows, do not confirm the destination branch, destination worktree, or diff base before Step 4. In the Step 4 prompt, treat `<main-branch>` as the prompt placeholder until Option 1 is selected. The actual destination branch/worktree and diff base are confirmed only after no-metadata Option 1 is selected and before applying changes.

For no-metadata tests-failing flows, do not require a destination branch, destination worktree, or diff base before presenting the tests-failing prompt. Option 2 keep-as-is and Option 3 discard need only the minimum no-metadata feature branch/worktree context for the chosen action.

Do not run remote publication, branch integration, or PR-opening steps from the no-metadata path. The only normal no-metadata choices are the same local-only choices in Step 4.

### Step 4: Present Options

If tests pass, present exactly the prompt below with literal `<main-branch>` in all tests-passing cases. Do not substitute a destination branch in this prompt. Actual destination branch and worktree validation happens only after Option 1 is selected.

```text
Implementation complete. What would you like to do?

1. Apply changes to <main-branch> as uncommitted local changes
2. Keep the branch as-is
3. Discard this work

Which option?
```

If tests fail, completion is unavailable. Present only:

```text
Tests are still failing. What would you like to do?

2. Keep the branch as-is
3. Discard this work

Which option?
```

**Don't add explanation** - keep options concise.

### Step 5: Apply-Back Preparation and Guards

Before executing Option 1 apply-back, Option 3 discard, branch deletion, or worktree removal, always confirm no merge, rebase, cherry-pick, or bisect is active. For Option 1, this active-operation guard applies to the source feature checkout and to the destination original main worktree or user-confirmed no-metadata destination checkout. For Option 3 and cleanup recovery, it applies to the cleanup checkout and to the target feature worktree when that target is accessible.

For each checkout being used or affected, inspect the checkout-specific Git paths for active operations, for example:

```bash
git rev-parse --git-path MERGE_HEAD
git rev-parse --git-path rebase-merge
git rev-parse --git-path rebase-apply
git rev-parse --git-path CHERRY_PICK_HEAD
git rev-parse --git-path BISECT_LOG
```

After resolving these checkout-specific Git paths, explicitly check whether each returned marker file or directory exists, for example with `Test-Path -LiteralPath <resolved-path>` on PowerShell, `[ -e "<resolved-path>" ]` in POSIX shell, or an equivalent Git state check. Any existing marker means an active operation is present; stop and ask the user before apply-back, discard cleanup, branch deletion, or worktree removal. Do not continue through a no-metadata fallback path while an active operation is present.

Run non-destructive cleanup preflight only before Option 1 apply-back, after Option 1 is selected and after any required no-metadata destination worktree and diff-base confirmation:
- Identify the exact feature worktree and feature branch from validated metadata or user-confirmed no-metadata evidence.
- Identify the destination original main worktree and destination branch.
- Confirm the current shell is not inside the target feature worktree.
- Confirm no active operation is present in the feature checkout or destination checkout.
- If cleanup preflight fails, stop before apply-back, preserve the feature worktree, and leave metadata active.

For Option 2 keep-as-is and Option 3 discard, do not ask for a no-metadata apply-back destination or diff base. Use only the feature branch/worktree context plus the active-operation and cleanup-checkout evidence needed for the chosen action.

Before applying the task diff to the destination checkout during Option 1:
- Validate that the destination checkout is the recorded `mainBranch` and the original non-attached main worktree when metadata exists. For no-metadata finishing, validate that it is the user-confirmed destination branch/worktree. The destination must not be the feature linked worktree.
- Require a clean destination index by default. If the destination has staged changes, stop unless the user explicitly approves handling those exact staged paths and the task diff does not modify them.
- Preserve destination tracked worktree modifications. Apply-back may proceed only when Git can apply the task patch cleanly without overwriting those modifications. If the task patch touches the same file as a destination tracked modification, require a clean patch check and stop on any conflict.
- Preserve destination untracked files. If a task-created path already exists as an untracked destination path, stop and ask the user to move it, delete it, or keep the feature worktree.
- Preserve destination ignored files. If a task-created path already exists as an ignored destination path, stop and ask the user to move it, delete it, or keep the feature worktree.
- Refuse to copy any untracked or ignored feature file over an existing destination tracked, untracked, or ignored path.
- Stop and preserve the feature worktree if apply-back cannot be completed safely.

Before Option 1 cleanup can be reached, enumerate all dirty/staged tracked files in the feature worktree. Each dirty/staged tracked path must be included in the delivered result or explicitly approved for deletion/loss from the source worktree; stop if any tracked change is unresolved.

Determine the tracked task diff before apply-back:
- With `preexistingTrackedCheckpoint: null`, the task diff is `mainBase..HEAD`, plus any user-approved dirty or staged tracked changes in the feature worktree. If temporary workflow commits will be removed in the feature worktree, capture the task diff or otherwise verify it is recoverable before that cleanup.
- With a non-null `preexistingTrackedCheckpoint`, the pre-existing tracked diff is `mainBase..preexistingTrackedCheckpoint`; the task diff is `preexistingTrackedCheckpoint..HEAD`, plus any user-approved dirty or staged tracked changes in the feature worktree. Apply the task diff separately from the pre-existing tracked diff.
- In the non-null checkpoint path, treat the destination main worktree's current tracked state as the user's authoritative local state. If it diverges from the recorded `mainBase..preexistingTrackedCheckpoint` diff, stop before apply-back unless the user explicitly approves treating the current destination state as authoritative and the task patch applies cleanly without overwriting those current changes.
- Keep `mainBase..preexistingTrackedCheckpoint` separate from the task diff; never fold the pre-existing tracked diff into the task result, even when the user approves treating the current destination tracked state as authoritative.

Account for feature worktree untracked and ignored files before apply-back:
- Enumerate untracked files in the feature worktree before apply-back.
- Enumerate ignored files in the feature worktree before apply-back.
- Copy task-created untracked files to the destination only after the user approves those exact paths as part of the result.
- Copy ignored files only after the user explicitly approves those exact ignored paths.
- Generated caches, build outputs, and unrelated ignored files must remain excluded.
- If an untracked or ignored feature file might be part of the result and the user has not approved inclusion or exclusion, stop and preserve the feature worktree.
- Refuse to overwrite pre-existing tracked, untracked, or ignored destination paths.

Metadata and cleanup ordering is fixed:
- Apply the tracked task diff and copy all user-approved untracked or ignored task files first.
- Only after tracked apply-back and all approved file copies succeed, update recorded-base metadata to `completed`.
- After metadata is completed, run destructive cleanup commands that remove the feature worktree and feature branch through Step 7.
- If destructive cleanup fails after metadata is completed, do not re-run apply-back. Report completed cleanup recovery instructions with the exact `metadataPath`, `featureBranch`, `worktreePath`, feature branch tip, feature worktree HEAD before removal when available, and any unavailable branch identity token; the recovery flow will require explicit branch action and branch identity proof before any branch deletion. If the token is unavailable, recovery must preserve the branch.

### Step 6: Execute Choice

#### Option 1: Apply Changes As Uncommitted Local Changes

Run tests first. If tests are still failing, Option 1 is unavailable.

Then execute the recorded-metadata or no-metadata apply-back path:
1. Resolve and validate metadata. If no metadata exists, after Option 1 is selected require the user to confirm the actual destination branch, the destination worktree that should receive uncommitted local changes, and the diff base commit or base ref for extracting current branch changes. Do not reuse or infer a real branch from the Step 4 `<main-branch>` prompt placeholder. Stop if the destination branch, destination worktree, or diff base is ambiguous.
2. Validate the destination checkout is the recorded `mainBranch` in the original non-attached main worktree, or the user-confirmed no-metadata destination branch/worktree. The destination must not be the feature linked worktree.
3. Run cleanup preflight before apply-back by identifying the exact feature worktree and branch, confirming the current shell is outside that feature worktree, and confirming no active operation is present in the feature or destination checkout.
4. Enumerate all dirty/staged tracked files in the feature worktree. Resolve each one by including it in the delivered result or by getting explicit approval for deletion/loss from the source worktree; stop if any tracked change is unresolved.
5. Capture the tracked task diff from the validated metadata state or no-metadata base:
   - If metadata exists and `preexistingTrackedCheckpoint` is `null`, the tracked task diff is `mainBase..HEAD`, plus any user-approved dirty or staged tracked changes in the feature worktree.
   - If metadata exists and `preexistingTrackedCheckpoint` is non-null, the tracked task diff is `preexistingTrackedCheckpoint..HEAD`, plus any user-approved dirty or staged tracked changes in the feature worktree. The pre-existing tracked user state in `mainBase..preexistingTrackedCheckpoint` is never part of the apply-back or delivered result.
   - For no-metadata finishing, capture the tracked task diff from the user-confirmed diff base to current `HEAD`, plus any user-approved dirty or staged tracked changes in the feature worktree.
6. Enumerate feature worktree untracked files and ignored files before apply-back.
7. Account for approved feature worktree untracked or ignored files while excluding generated caches, build outputs, and unrelated ignored files.
8. Stop if inclusion or exclusion of a possibly relevant untracked or ignored file is unresolved.
9. Dry-run the tracked patch against the destination worktree. Stop if it cannot apply cleanly or would overwrite destination changes.
10. Apply the tracked patch to the destination worktree without committing.
11. Copy approved untracked or ignored files without overwriting any destination tracked, untracked, or ignored path.
12. Mark recorded-base metadata `completed` only after tracked apply-back and all approved file copies succeed. Skip this step when no metadata exists.
13. For no-metadata Option 1, after tracked apply-back and all approved file copies succeed and before Step 7 cleanup begins, capture a pre-cleanup handoff record. The pre-cleanup handoff record must include only fields knowable at that point: prior flow `Option 1`, successful tracked apply-back, successful approved file copies for all approved untracked or ignored files, exact cleanup checkout path and branch, feature branch, feature worktree path, feature branch tip, pre-removal branch identity token from the feature worktree `HEAD`, and any unavailable branch identity token state. Keep cleanup-state/failure fields separate: whether worktree removal succeeded, whether branch deletion remains, whether forced worktree removal was explicitly accepted during cleanup, and whether branch deletion was explicitly confirmed during cleanup are recorded or reported only after those cleanup decisions or outcomes exist.
14. Remove the feature worktree and branch through guarded cleanup in Step 7.

After Option 1 succeeds, final task contents remain as uncommitted changes in the destination main worktree. Workflow temporary commits are not preserved as delivered history.

If cleanup fails after metadata completion, report the exact `metadataPath`, `featureBranch`, `worktreePath`, feature branch tip, feature worktree HEAD before removal when available, and any unavailable branch identity token; state that apply-back already completed; and do not re-run apply-back. If the token is unavailable, recovery must preserve the branch.

#### Option 2: Keep As-Is

Report: "Keeping branch <name>. Worktree preserved at <path>."

If recorded-base metadata exists, do not mark metadata `status` as `completed` merely because the branch is kept as-is. Option 2 is preserve-only whether tests pass or fail: keep the branch and worktree as-is for later work, do not apply changes back, and do not run destructive cleanup.

#### Option 3: Discard

**Confirm first.** When recorded-base metadata exists, the task boundary is known from metadata, so use:

```text
This will permanently delete:
- Branch <feature-branch>
- Task commits from recorded metadata boundary: <commit-list>
- Worktree at <worktree-path>

Type 'discard' to confirm.
```

When no recorded-base metadata exists and no explicit no-metadata discard boundary has been user-confirmed, use only known destructive targets:

```text
This will permanently delete:
- Branch <feature-branch>
- Worktree at <feature-worktree-path>

Type 'discard' to confirm.
```

If the user already confirmed an explicit no-metadata discard commit boundary, include only that exact boundary or commit list as an additional destructive target. Otherwise omit any task-commit-list line and do not ask the operator to guess a commit list.

Wait for exact confirmation.

After exact typed discard confirmation and after all prechecks pass, discard is the only path that may intentionally remove a dirty linked worktree. Before discard cleanup, branch deletion, or worktree removal, confirm no merge, rebase, cherry-pick, or bisect is active in the checkout used to perform cleanup and in the target worktree when it is accessible. If any active operation exists, stop and ask the user instead of deleting the branch or removing the worktree.

For no-metadata discard, exact typed `discard` confirms the discard decision and any approved worktree removal, but it does not authorize force branch deletion. Before any no-metadata `git branch -D <feature-branch>` after typed `discard`, require an additional explicit confirmation for force-deleting that exact branch:

```text
No recorded metadata exists. Force-delete branch <feature-branch> with git branch -D?

Type 'delete branch <feature-branch>' to confirm.
```

If the user does not provide that exact additional confirmation, preserve the branch after any allowed worktree cleanup. Record whether this additional force branch deletion confirmation was given in the no-metadata cleanup recovery evidence.

If any discard precheck fails before the abandoned transition, leave recorded-base metadata `status` as `active` so finishing can resume safely. After exact typed discard confirmation and after all discard/removal prechecks pass, update recorded-base metadata `status` to `abandoned` immediately before irreversible worktree/branch removal when practical. If the metadata update itself cannot be performed safely, stop before removal and ask; do not remove the worktree while metadata still falsely says active if updating was practical but failed. If worktree removal succeeds but branch deletion fails after the abandoned transition, require a later abandoned discard cleanup recovery request with the exact metadata path. In that recovery mode, treat the missing worktree only as an already-completed removal step after confirming `git worktree list --porcelain` no longer records that target worktree, then continue only with the remaining branch deletion checks.

When discard transitions recorded-base metadata to `abandoned`, provide a user-visible handoff that abandoned discard cleanup recovery is exact-path-only. Report the exact `metadataPath`, metadata `worktreePath`, metadata `featureBranch`, and recorded branch identity evidence from the validated cleanup state. If cleanup fails after the abandoned transition, report those same exact values again as the required recovery evidence.

For no-metadata discard, require the user-confirmed cleanup checkout path and cleanup checkout branch before any worktree removal or branch deletion. The cleanup checkout may be the user-confirmed destination branch/worktree if one was already confirmed for the chosen flow, or another safe non-attached checkout. It must not be the target feature worktree and must not be any checkout attached to `<feature-branch>`. Do not use `<main-branch>` as a placeholder when no metadata exists.

For no-metadata discard, record recovery evidence before irreversible cleanup starts: exact `<feature-branch>`, exact `<feature-worktree-path>`, cleanup checkout path and branch, feature branch tip, feature worktree HEAD before removal when available, whether forced worktree removal was explicitly accepted, and whether the additional force branch deletion confirmation for `git branch -D <feature-branch>` was explicitly accepted. If cleanup fails, additionally report whether worktree removal succeeded, whether branch deletion remains, and any unavailable branch identity token. If any required evidence is missing, stop before destructive cleanup; if a branch identity token is unavailable, later recovery must preserve the branch.

If confirmed, leave the feature linked worktree first if the current shell is inside it. From the original/main worktree or another safe non-attached checkout, remove the attached feature worktree through Cleanup Worktree (Step 7) before deleting a branch that is still checked out by that worktree. Use the validated recorded `mainBranch` as `<cleanup-branch>` when metadata exists; use the user-confirmed no-metadata cleanup checkout branch when metadata does not exist.

Before discard branch deletion, verify the local branch ref is exactly `refs/heads/<feature-branch>` and compare the current `refs/heads/<feature-branch>` tip to the pre-removal branch identity token captured from the feature worktree `HEAD`. If the branch is already absent, report that no branch deletion is needed. If the identity token is unavailable or the current branch tip differs from that token, stop and preserve the branch, or enter the matching cleanup recovery path with exact evidence if cleanup is already partial. For no-metadata discard, this identity check is required in addition to the separate force branch deletion confirmation after typed `discard`.

After the feature worktree is no longer attached:

```bash
# In the original/main worktree or another safe non-attached checkout,
# or the user-confirmed no-metadata cleanup checkout
git switch <cleanup-branch>
git branch -D <feature-branch>
```

Then: finish Cleanup Worktree (Step 7) if it was not already needed before branch deletion.

### Step 7: Cleanup Worktree

**For Option 1 after successful apply-back and for Option 3 after exact typed discard confirmation:**

Remove the feature worktree only after the selected option allows removal and only when the current shell is not inside that attached feature checkout. For linked worktrees, operate from the original/main worktree or another safe non-attached checkout. Before removal, confirm the user-approved or discard-safe condition for the selected option still holds, the worktree path matches validated metadata when metadata exists or confirmed no-metadata refs when metadata does not exist, and no uncommitted work would be destroyed without explicit approval.

For completed cleanup recovery re-entry, Step 7 may be entered directly only when the user explicitly requested cleanup for exact-path completed metadata and selected the branch action: preserve the branch after worktree cleanup, or delete the temporary branch after completed apply-back. Use metadata `mainBranch`, `worktreePath`, and `featureBranch` as the cleanup checkout, target worktree, and target branch identifiers, not the current checkout. Do not require the current branch or current worktree to match the metadata target, but require the current shell to be outside the target worktree when the target still exists before any removal or branch deletion. Do not infer branch deletion from metadata, and do not run apply-back again.

For abandoned discard cleanup recovery re-entry, Step 7 may be entered directly only when the user explicitly requested cleanup recovery for a previously confirmed discard and provided the exact abandoned metadata path. Use metadata `worktreePath` and `featureBranch` as the target identifiers, not the current checkout. Do not require the current branch or current worktree to match the metadata target, but require the current shell to be outside the target worktree when the target still exists before any removal or branch deletion.

For no-metadata cleanup recovery re-entry, Step 7 may be entered directly only when the user explicitly requested no-metadata cleanup recovery and provided the exact recorded no-metadata cleanup evidence from the earlier failed cleanup handoff. Use that evidence as the sole source for the cleanup checkout, target worktree, target branch, prior flow, branch identity tokens, and remaining cleanup state. Do not run Step 3 current branch/current worktree discovery, do not ask for an apply-back destination or diff base, and do not infer any target from the current checkout after the feature worktree is gone.

Before any Step 7 worktree removal or branch deletion, confirm no merge, rebase, cherry-pick, or bisect is active in the checkout used to perform cleanup and in the target worktree when it is accessible. This guard is mandatory for discard cleanup as well as normal post-apply-back cleanup; if any active operation exists, stop and ask the user.

Before normal Option 1 cleanup or discard cleanup removes the target worktree, capture branch identity evidence for deletion safety and later recovery: resolve `refs/heads/<feature-branch>` as the current branch tip, and when the target worktree is still accessible, resolve that feature worktree `HEAD` as the pre-removal branch identity token. The branch tip and feature worktree `HEAD` must match before cleanup can later delete the branch. Include both tokens in any completed cleanup, abandoned discard, or no-metadata cleanup failure handoff. If the feature worktree `HEAD` token is unavailable, branch deletion is not allowed; preserve the branch or route to the matching recovery entry path.

Identify the exact target worktree with porcelain output before removal:

```bash
git worktree list --porcelain
```

Use the `worktree` and `branch` records to confirm the target path is the validated `worktreePath` when metadata exists, or the user-confirmed worktree path when no metadata exists. Confirm the target `branch` record is `refs/heads/<feature-branch>` before deleting `<feature-branch>`.

For completed cleanup recovery, split Step 7 into explicit recovery branches after reading `git worktree list --porcelain`:
- If the target worktree is still present, validate that the worktree record path exactly matches normalized metadata `worktreePath`, its `branch` record is `refs/heads/<feature-branch>`, the current shell is outside that target path, and all active-operation and cleanup checkout guards pass. Before any branch deletion, resolve the local branch tip and the target worktree `HEAD`; they must be the same commit. Then remove the target worktree from the original/main worktree recorded by metadata `mainBranch` or another safe non-attached checkout. If the selected branch action is preserve branch, do not force removal of a dirty target; stop and preserve the target worktree instead. If the selected branch action is delete temporary branch after completed apply-back, forced worktree removal is allowed only under the same metadata-backed Option 1 force-removal preconditions below.
- If the target worktree is already absent, verify through `git worktree list --porcelain` that no record exists for the exact normalized metadata `worktreePath`. In this branch, skip `git worktree remove` because worktree removal is already complete, and proceed only to the remaining branch action chosen by the user after the current branch tip is explicitly revalidated against the exact previously reported pre-removal branch identity token from the completed cleanup failure report. If the token is unavailable or mismatched, preserve the branch and limit recovery to non-deleting cleanup only. This verified absence does not permit apply-back, a new apply-back decision, discard, publication, history rewriting, metadata status changes, or branch deletion without that exact token match.

Before any cleanup command in completed cleanup recovery, reconfirm this is only cleanup for already completed metadata and that the explicit branch action is still the user's intent. If the branch action is preserve branch, never delete `<feature-branch>`; report that the branch was intentionally preserved. Before deleting a branch in the delete-temporary-branch-after-completed-apply-back action, verify the user confirmed delivery, verify no worktree remains attached to `refs/heads/<feature-branch>`, verify the local branch ref is exactly `refs/heads/<feature-branch>`, and verify branch identity from the still-present target worktree `HEAD` or, when the target worktree is absent, from the exact previously reported pre-removal branch identity token. If the branch is already absent, report that no branch deletion is needed. Do not delete by branch name alone. Because completed cleanup recovery skips Step 6, include the remaining worktree removal and branch action directly in Step 7 and do not run apply-back again.

For abandoned discard cleanup recovery, split Step 7 into explicit recovery branches after reading `git worktree list --porcelain`:
- If the target worktree is still present, validate that the worktree record path exactly matches normalized metadata `worktreePath`, its `branch` record is `refs/heads/<feature-branch>`, the current shell is outside that target path, and all active-operation and cleanup checkout guards pass. Before any branch deletion, resolve the local branch tip and the target worktree `HEAD`; they must be the same commit. Then remove the target worktree from the original/main worktree or another safe non-attached checkout.
- If the target worktree is already absent, verify through `git worktree list --porcelain` that no record exists for the exact normalized metadata `worktreePath`. In this branch, skip `git worktree remove` because worktree removal is already complete, and proceed only to the remaining validated branch deletion or cleanup remediation checks after the current branch tip is explicitly revalidated against the exact recorded pre-removal branch identity token. If the token is unavailable or mismatched, preserve the branch and limit recovery to non-deleting cleanup only. This verified absence does not permit apply-back, a new discard decision, publication, history rewriting, metadata status changes, or branch deletion without that exact token match.

Before any cleanup command in abandoned discard cleanup recovery, reconfirm the user intends only to finish or remediate the previously confirmed discard cleanup. Before deleting a branch in this mode, verify the local branch ref is exactly `refs/heads/<feature-branch>`, and verify branch identity from the still-present target worktree `HEAD` or, when the target worktree is absent, from the exact recorded pre-removal branch identity token. If the branch is already absent, report that no branch deletion is needed. Do not delete by branch name alone. Use `<cleanup-branch>` for the validated cleanup checkout branch: metadata `mainBranch` when using the original/main worktree, or the explicitly selected safe non-attached checkout branch. Because abandoned discard cleanup recovery skips Step 6, include the remaining branch deletion/remediation action directly in Step 7:

```bash
# In the original/main worktree or another safe non-attached checkout
git switch <cleanup-branch>
git branch -D <feature-branch>
```

For no-metadata cleanup recovery, split Step 7 into explicit recovery branches after reading `git worktree list --porcelain`:
- If the target worktree is still present, validate that the worktree record path exactly matches recorded `<feature-worktree-path>`, its `branch` record is `refs/heads/<feature-branch>`, the current shell is outside that target path, the cleanup checkout exactly matches the recorded cleanup checkout path/branch, and all active-operation guards pass. The target worktree `HEAD` must match the recorded pre-removal branch identity token, and the current local branch tip must match that same token before any branch deletion.
- If the target worktree is already absent, verify through `git worktree list --porcelain` that no record exists for the exact recorded `<feature-worktree-path>`. In this branch, skip `git worktree remove` because worktree removal is already complete, and proceed only to the remaining branch deletion check if the current local branch tip matches the recorded pre-removal branch identity token. If the token is unavailable or mismatched, stop and preserve the branch.

Before any cleanup command in no-metadata cleanup recovery, reconfirm this is only cleanup recovery for the recorded prior flow. For prior no-metadata Option 1, branch deletion is allowed only when exact recovery evidence includes a valid pre-cleanup handoff record with successful tracked apply-back and successful approved file copies for all approved untracked or ignored files, plus explicit branch deletion confirmation captured during cleanup before failure. For prior no-metadata discard, branch deletion is allowed only when the exact evidence records the typed `discard` confirmation and the additional explicit force branch deletion confirmation. If the required confirmation is missing, preserve the branch. Because no-metadata cleanup recovery skips Step 6, include only the remaining validated worktree removal and branch-deletion cleanup directly in Step 7.

Confirm the current shell is not inside the target worktree before removal or branch deletion:

```bash
git rev-parse --show-toplevel
```

Compare the current top-level path with the target worktree path, and stop if they match or if the current path is inside the target. Move to the original/main worktree or another safe non-attached checkout first.

For normal discard with recorded-base metadata, after exact typed discard confirmation and after all discard/removal prechecks pass, update recorded-base metadata `status` to `abandoned` immediately before irreversible worktree/branch removal when practical. If the metadata update itself cannot be performed safely, stop before removal and ask; do not remove the worktree while metadata still falsely says active if updating was practical but failed. If cleanup later fails after this transition, resume only through exact-path abandoned discard cleanup recovery.

After the checks pass and the selected option allows worktree removal, or when completed cleanup recovery, abandoned discard cleanup recovery, or no-metadata cleanup recovery verified that the target worktree is still present:

```bash
# Run from the original/main worktree or another safe non-attached checkout
git worktree remove <worktree-path>
```

For normal Option 1 cleanup, successful worktree removal alone does not complete cleanup. Delete the feature branch only after apply-back succeeded, all approved files were delivered, metadata is `completed` when metadata exists, and `git worktree list --porcelain` confirms no remaining worktree is attached to `refs/heads/<feature-branch>`. Run branch deletion from the original/main worktree recorded by metadata `mainBranch`, or another safe non-attached checkout on that branch. For no-metadata Option 1 cleanup, run from the user-confirmed destination worktree or another safe non-attached checkout on the user-confirmed destination branch. Never run Option 1 branch deletion from inside the target feature worktree.

Before Option 1 branch deletion, verify the local branch ref is exactly `refs/heads/<feature-branch>` and compare the current `refs/heads/<feature-branch>` tip to the pre-removal branch identity token captured from the feature worktree `HEAD`. If the branch is already absent, report that no branch deletion is needed. If the identity token is unavailable or the current branch tip differs from that token, stop and preserve the branch, or report the matching cleanup recovery evidence if cleanup is already partial. If any worktree remains attached to the feature branch, stop and report completed cleanup recovery evidence when metadata exists, or exact no-metadata cleanup evidence when metadata does not exist. Include the feature branch tip and feature worktree HEAD before removal when available; if either token is unavailable, state that recovery must preserve the branch.

For metadata-backed Option 1, normal `git worktree remove <worktree-path>` is sufficient when the source worktree is clean enough to remove. Before any Option 1 worktree removal, enumerate all dirty/staged tracked files in the feature worktree and verify each one was included in the delivered result or explicitly approved for deletion/loss from the source worktree. Stop and preserve the feature worktree if any dirty/staged tracked change remains unresolved.

If the feature worktree remains dirty after the tracked apply-back and all approved untracked or ignored file copies have succeeded, guarded forced removal is permitted only after all of these are true:
- Apply-back delivered final tracked contents and every approved untracked or ignored file to the destination.
- Force removal is allowed only when all dirty/staged tracked changes were either delivered or explicitly approved for deletion, and all relevant untracked/ignored files were either delivered or explicitly excluded/approved for deletion.
- Any unresolved possibly relevant untracked or ignored feature file was handled by stopping earlier; no unresolved inclusion or exclusion decision remains.
- Recorded-base metadata is already `status: completed`.
- The current shell is outside the target feature worktree.
- The target worktree path and target `branch refs/heads/<feature-branch>` entry exactly match validated metadata from `git worktree list --porcelain`.
- The active-operation guard passes for the cleanup checkout and for the target worktree when accessible.
- Any remaining source-only dirt has exact-path explicit loss acceptance; otherwise require no leftover source-only dirt and preserve the feature worktree if normal removal refuses.

When every metadata-backed Option 1 force-removal precondition is satisfied and normal removal refuses because the source worktree is dirty, this command is permitted:

```bash
# Metadata-backed Option 1 only, after apply-back delivery, metadata completion, and all force prechecks
git worktree remove --force <worktree-path>
```

For metadata-backed Option 1 cleanup:

```bash
# In the original/main worktree or another safe non-attached checkout
git switch <main-branch>
git branch -D <feature-branch>
```

Use this metadata-backed `git branch -D` only after apply-back delivered final contents, recorded-base metadata is `status: completed`, `git worktree list --porcelain` confirms no remaining worktree is attached to `refs/heads/<feature-branch>`, the local branch ref is exactly `refs/heads/<feature-branch>`, the current branch tip matches the pre-removal branch identity token captured from the feature worktree, and active-operation guards pass. The force-delete is for the temporary workflow branch after successful metadata-backed delivery; it is not a general unmerged-branch deletion rule. If the identity token is unavailable or mismatched, stop and preserve the branch instead of deleting by name.

For no-metadata Option 1 cleanup, first attempt normal worktree removal. If the source worktree remains dirty after tracked apply-back and all approved file copies succeed, require explicit user acceptance for deleting the remaining source worktree dirt at the exact path, or preserve the source worktree. If the user accepts, forced worktree removal may be used only after the active-operation guard passes, the current shell is outside the target, and the target path and branch match the user-confirmed no-metadata evidence.

For no-metadata Option 1 branch cleanup, do not silently force-delete an unmerged branch. Require explicit user confirmation for deleting the exact unmerged `<feature-branch>` after successful apply-back and worktree removal, and require the current `refs/heads/<feature-branch>` tip to match the pre-removal branch identity token captured from the feature worktree. If the user does not confirm deletion, or if the identity token is unavailable or mismatched, preserve the branch. If the user confirms deletion and the identity check passes:

```bash
# In the confirmed destination worktree or another safe non-attached checkout
git switch <destination-branch>
git branch -D <feature-branch>
```

If metadata-backed cleanup fails after metadata completion, do not re-run apply-back and do not modify metadata. Report completed cleanup recovery with the exact metadata path, feature branch, feature worktree path, feature branch tip, feature worktree HEAD before removal when available as the pre-removal branch identity token, any unavailable branch identity token, and the remaining cleanup state. If the target worktree is already absent during recovery, branch deletion requires that exact previously reported pre-removal branch identity token; if it is unavailable or mismatched, recovery must preserve the branch and remain limited to non-deleting cleanup only. Completed cleanup recovery resumes only the remaining worktree-removal and explicit branch-action procedure from the verified cleanup state.

If no-metadata Option 1 cleanup fails after tracked apply-back and all approved file copies succeeded, do not re-run apply-back. Report exact no-metadata cleanup recovery evidence in two groups. Pre-cleanup handoff: prior flow `Option 1`, successful tracked apply-back, successful approved file copies for all approved untracked or ignored files, feature branch, feature worktree path, feature branch tip, pre-removal branch identity token from the feature worktree `HEAD`, cleanup checkout path and branch, and any unavailable branch identity token state. Cleanup-state/failure fields: whether worktree removal succeeded, whether branch deletion remains, whether forced worktree removal was explicitly accepted during cleanup, and whether branch deletion was explicitly confirmed during cleanup before failure. Resume only through the no-metadata cleanup recovery entry path; if the branch identity token is unavailable, recovery must preserve the branch.

For discard, successful worktree removal alone does not complete cleanup. After metadata has transitioned to `abandoned`, any failure in required worktree removal or branch deletion must be recovered only through exact-path abandoned discard cleanup recovery.

For no-metadata discard, there is no metadata transition or exact metadata path. If cleanup fails after exact typed discard confirmation, report exact no-metadata cleanup recovery evidence: prior flow `Option 3 discard`, feature branch, feature worktree path, feature branch tip, pre-removal branch identity token from the feature worktree `HEAD`, cleanup checkout path and branch, whether worktree removal succeeded, whether branch deletion remains, whether forced worktree removal was explicitly accepted, whether the additional force branch deletion confirmation was explicitly accepted, and any unavailable branch identity token. Resume no-metadata discard cleanup only through the no-metadata cleanup recovery entry path, using the recorded cleanup checkout path/branch, never from the target feature worktree and never by guessing `<main-branch>`. If a branch identity token is unavailable, recovery must preserve the branch.

If completed cleanup recovery preserves the branch for retained/legacy behavior, leave metadata `status` as `completed` after removal succeeds and do not delete the branch. Completed cleanup recovery must be driven by exact user-provided metadata/path evidence and explicit branch action, not automatic active metadata matching.

Use forced worktree removal only for metadata-backed Option 1 after delivery, no-metadata Option 1 after explicit source-dirt acceptance, or discard. For discard, force removal is permitted only after all of these are true:
- The user has given the exact typed `discard` confirmation.
- The active-operation guard passes for the cleanup checkout and the target worktree when accessible.
- The current shell is not inside the target worktree.
- The target path and feature branch match validated metadata, or match user-confirmed no-metadata refs.
- The user has explicitly accepted losing dirty tracked changes, untracked files, and ignored files in the linked worktree.
- In abandoned discard cleanup recovery, force removal is allowed only if the original typed discard was already confirmed and the user again explicitly accepts losing dirty tracked changes, untracked files, and ignored files in the still-present target worktree.

When every discard-only force precondition is satisfied and normal removal refuses because the target worktree is dirty, this command is permitted:

```bash
# Discard only, after exact typed discard confirmation and all force prechecks
git worktree remove --force <worktree-path>
```

Do not use `git worktree remove --force` for completed cleanup recovery that preserves the branch, or for any path that has not satisfied the exact force-removal preconditions for metadata-backed Option 1, no-metadata Option 1 with explicit source-dirt acceptance, or confirmed discard.

**For Option 2:** Keep worktree.

## Quick Reference

| Option | Tests Required | Result | Worktree/Branch | Metadata |
|--------|----------------|--------|-----------------|----------|
| 1. Apply as uncommitted local changes | Yes | Task changes appear in `<main-branch>` worktree without committing | Clean up after delivery | `completed` after tracked apply-back and approved file copies |
| 2. Keep as-is | No | Branch remains for later manual handling | Preserve | Remains active |
| 3. Discard | No | Work is deleted after exact typed confirmation | Remove through guarded cleanup | `abandoned` immediately before irreversible removal when practical |

## Common Mistakes

**Skipping test verification**
- **Problem:** Applying incomplete work to the destination worktree.
- **Fix:** Always verify tests before offering Option 1.

**Open-ended questions**
- **Problem:** "What should I do next?" is ambiguous.
- **Fix:** Present exactly 3 structured options when tests pass; when tests fail, present only Option 2 keep-as-is and Option 3 discard.

**Overwriting destination state**
- **Problem:** Applying task changes over existing tracked, untracked, or ignored destination files.
- **Fix:** Treat destination local state as authoritative, require clean patch checks, and refuse file-copy overwrites.

**Ignoring checkpoint boundaries**
- **Problem:** Dirty-start tracked edits get folded into the task result.
- **Fix:** Use `mainBase..preexistingTrackedCheckpoint` only as pre-existing state and apply `preexistingTrackedCheckpoint..HEAD` as the task diff.

**Copying generated ignored files**
- **Problem:** Caches, build outputs, or unrelated ignored files become part of the delivered result.
- **Fix:** Copy only exact user-approved untracked or ignored paths; exclude generated and unrelated files.

**Completing metadata too early**
- **Problem:** Metadata says `completed` before approved files are delivered.
- **Fix:** Mark `completed` only after tracked apply-back and all approved file copies succeed, then run destructive cleanup.

**Re-running apply-back after cleanup failure**
- **Problem:** A completed run is applied twice while trying to fix cleanup.
- **Fix:** If cleanup fails after metadata completion, report exact cleanup recovery evidence and do not re-run apply-back.

**No confirmation for discard**
- **Problem:** Accidentally delete work.
- **Fix:** Require exact typed "discard" confirmation.

**Deleting branches by name only**
- **Problem:** `git branch -D <feature-branch>` can delete a branch that moved after the worktree was removed.
- **Fix:** Compare the current `refs/heads/<feature-branch>` tip to the pre-removal branch identity token captured from the feature worktree before every normal branch deletion.

**Treating no-metadata discard as branch deletion approval**
- **Problem:** Typed `discard` confirms the discard decision but not no-metadata force branch deletion.
- **Fix:** Require the separate `delete branch <feature-branch>` confirmation before no-metadata `git branch -D`.

## Red Flags

**Never:**
- Proceed with apply-back while tests are failing.
- Offer branch integration, remote publication, or PR opening as normal completion.
- Create commits as part of normal finishing.
- Delete work without exact typed confirmation.
- Continue when a merge, rebase, cherry-pick, or bisect is active.
- Overwrite destination tracked, untracked, or ignored files.
- Mark metadata `completed` before tracked apply-back and all approved file copies succeed.
- Re-run apply-back after metadata is completed and cleanup fails.
- Run forced worktree removal before apply-back delivery, without exact path/branch guards, or outside the allowed Option 1 and confirmed-discard force-removal preconditions.
- Treat typed discard as a general cleanup permission. The sole exception is confirmed discard after all force-removal prechecks pass and the user explicitly accepts losing dirty tracked changes, untracked files, and ignored files in that linked worktree.
- Run `git branch -D <feature-branch>` when the current branch tip does not match the pre-removal branch identity token captured from the feature worktree.
- Run no-metadata `git branch -D <feature-branch>` after typed `discard` without the separate force branch deletion confirmation.

**Always:**
- Verify tests before offering Option 1.
- Present exactly 3 options when tests pass; when tests fail, present only Option 2 keep-as-is or Option 3 discard.
- Use checkpoint-aware task diff extraction when `preexistingTrackedCheckpoint` is non-null.
- Preserve destination local changes unless the user gives exact scoped approval and the task patch applies cleanly.
- Enumerate and resolve untracked and ignored feature files before apply-back.
- Mark metadata `completed` only after the result is delivered to the destination worktree.
- Capture and compare branch identity tokens before normal Option 1 or discard branch deletion.
- Preserve the feature worktree and leave metadata active whenever apply-back cannot be completed safely.

## Integration

**Called by:**
- **subagent-driven-development** - After all tasks complete (passes or records metadata for cleanup of the worktree created during setup)
