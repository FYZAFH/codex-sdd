---
name: finishing-a-development-branch
description: Use when implementation is complete or a development branch needs safe closure, and you need to decide whether to merge, create a PR, retain, or discard work while test-gating completion paths
---

# Finishing a Development Branch

## Overview

Guide completion or safe closure of development work by presenting clear options and handling the chosen workflow.

**Core principle:** Verify tests → test-gate merge/PR/final-storage paths → resolve metadata → present allowed options → execute choice → clean up.

**Announce at start:** "I'm using the finishing-a-development-branch skill to complete this work."

## The Process

### Retained-Cleanup Entry Path

If the user explicitly requests retained PR worktree cleanup from an earlier Option 2 run and provides the exact metadata path, enter the retained-cleanup entry path instead of the normal top-level finishing flow. In this retained-cleanup entry path, validate the exact metadata path and retained cleanup metadata using the Step 2 retained cleanup rules, then proceed directly to Step 7 cleanup only.

For this retained-cleanup entry path, skip Step 1 test verification and skip Steps 4-6 option presentation/execution. Do not allow merge, push, PR creation, discard, clean-history preparation, or final local storage from this entry. If retained cleanup metadata validation fails, stop and ask the user instead of falling back to normal finishing or automatic metadata matching.

### Abandoned Discard Cleanup Recovery Entry Path

If the user explicitly requests abandoned discard cleanup recovery from a previously confirmed Option 4 discard and provides the exact metadata path, enter the abandoned discard cleanup recovery entry path instead of the normal top-level finishing flow. In this abandoned cleanup recovery path, validate the exact metadata path and abandoned cleanup metadata using the Step 2 abandoned cleanup recovery rules, then proceed directly to Step 7 cleanup only.

For this abandoned cleanup recovery path, skip Step 1 test verification and skip Steps 4-6 option presentation/execution. Do not allow merge, push, PR creation, a new discard decision, clean-history preparation, or final local storage from this entry. If abandoned cleanup recovery metadata validation fails, stop and ask the user instead of falling back to normal finishing or automatic metadata matching.

### Step 1: Verify Tests

**Before presenting completion options, verify tests pass:**

```bash
# Run project's test suite
npm test / cargo test / pytest / go test ./...
```

**If tests fail:**
```
Tests failing (<N> failures). Must fix before completing:

[Show failures]

Cannot proceed with merge, push/PR, final local storage, final local commit(s), or metadata `completed` transition until tests pass.
```

Continue to Step 2 only far enough to resolve metadata and present or execute cleanup-safe non-completion choices. When tests fail, this skill allows only the restricted keep-as-is/preserve flow and Option 4 discard. Do not allow Option 1 merge, Option 2 push/PR, clean-history preparation, user-approved final local storage, final local commit(s), or metadata `completed` transition while tests fail. Option 4 discard remains reachable after all existing discard prechecks, exact typed discard confirmation, active-operation guards, metadata `abandoned` transition rules, and exact-path recovery rules.

**If tests pass:** Continue to Step 2 with completion paths available.

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

If the user explicitly asks to clean up a retained PR worktree from an earlier Option 2 run and provides an exact metadata path, treat that as retained PR worktree cleanup re-entry. This is a Step 7-only cleanup mode. After exact metadata validation for retained cleanup, exit the normal top-level flow and proceed directly to Step 7 cleanup only. Do not use automatic metadata matching for this mode, and do not proceed to merge, push, PR creation, discard, clean-history preparation, or final local storage from the non-attached checkout.

If the user explicitly asks for abandoned discard cleanup recovery from a previously confirmed Option 4 discard and provides an exact metadata path, treat that as abandoned discard cleanup recovery re-entry. This is a Step 7-only cleanup mode. After exact metadata validation for abandoned cleanup recovery, exit the normal top-level flow and proceed directly to Step 7 cleanup only. Do not use automatic metadata matching for this mode, and do not proceed to merge, push, PR creation, a new discard decision, clean-history preparation, or final local storage from the non-attached checkout.

Metadata lookup outcomes are authoritative:
- If zero active metadata files match the current branch or worktree, stop and ask the user to provide the exact metadata path or confirm this is an ordinary non-SDD branch with no recorded-base metadata expected. Do not guess and do not silently bypass cleanup for a possible SDD branch.
- If exactly one active metadata file matches, validate and use it.
- If more than one active metadata file matches, stop and ask the user which metadata file applies.
- If the orchestrator provided an explicit metadata path and that metadata is missing, malformed, invalid, stale, or mismatched, stop and ask the user instead of falling back to no metadata.
- In retained PR worktree cleanup re-entry, if the exact user-provided metadata path is missing, malformed, invalid, stale, or does not identify the retained target worktree and branch, stop and ask the user instead of falling back to no metadata.
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
- In retained PR worktree cleanup re-entry, the exact user-provided metadata path is retained cleanup context, not an active automatic lookup. `status` must be `completed`; stop on `active`, `abandoned`, missing, or any other stale status.
- In abandoned discard cleanup recovery re-entry, the exact user-provided metadata path is abandoned cleanup recovery context, not an active automatic lookup. `status` must be `abandoned`; stop on `active`, `completed`, missing, or any other stale status.
- `mainBranch`, `mainBase`, `featureBranch`, and `worktreePath` must be present with valid types.
- `mainBranch` and `featureBranch` must be non-empty strings naming branches.
- `mainBase` must be a 40-character hexadecimal commit id that resolves in this repository.
- In normal finishing mode, after `mainBase` resolves, verify it is an ancestor of the current feature `HEAD` before using it as the cleanup anchor, for example with `git merge-base --is-ancestor <mainBase> HEAD`. Also confirm the merge-base between `mainBase` and the current feature `HEAD` is `mainBase`, so the metadata is consistent with the current run branch lineage. If either check fails, stop because the metadata is stale or mismatched.
- In retained PR worktree cleanup re-entry, do not use the current checkout `HEAD` as the feature lineage check. Validate the retained target worktree and branch from `git worktree list --porcelain` instead, then allow only Step 7 cleanup.
- In abandoned discard cleanup recovery re-entry, do not use the current checkout `HEAD` as the feature lineage check. Validate the abandoned target worktree and branch from `git worktree list --porcelain`, or validate the exact target worktree's absence from that output when recovering after worktree removal already happened, then allow only Step 7 cleanup.
- `worktreePath` must be a non-empty repo-relative string when metadata is being used for finishing. Reject `null`, empty strings, absolute paths, drive-prefixed paths, paths containing `..`, and paths outside the repo-local `.worktrees` directory under the shared checkout root.
- Resolve `worktreePath` from the shared checkout root and confirm the final normalized path remains under the repo-local `.worktrees` directory. In normal finishing mode, compare that final path with the current linked worktree path from `git rev-parse --show-toplevel` or an equivalent current-checkout top-level query. In retained PR worktree cleanup re-entry, compare that final path with the target worktree path recorded by `git worktree list --porcelain`. In abandoned discard cleanup recovery re-entry, compare that final path with the target worktree path recorded by `git worktree list --porcelain`, or confirm the porcelain output has no record for that exact normalized path before treating worktree removal as already completed. On Windows, perform final absolute-path comparisons case-insensitively.
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

Use `mainBase` as the cleanup anchor for temporary workflow commits.

When `preexistingTrackedCheckpoint` is non-null, treat that checkpoint as user pre-existing tracked state, not as task work or an ordinary temporary checkpoint. Before any final clean commit, merge, push, PR creation, or final local storage, run checkpoint-aware cleanup:
- Verify the checkpoint resolves in this repository and is in the lineage between `mainBase` and the current `HEAD`; if it does not resolve, is not descended from `mainBase`, or is not an ancestor of the current `HEAD`, stop and ask because the metadata no longer safely describes this branch.
- Explain the required split: the pre-existing tracked diff is `mainBase..preexistingTrackedCheckpoint`, and the task diff is `preexistingTrackedCheckpoint..HEAD`, subject to later edits in the working tree or index.
- Reconstruct or preserve pre-existing tracked edits separately as uncommitted tracked changes unless the user explicitly says to include them in the final task result.
- Create, merge, push, or store locally only the task-approved clean result, not a combined `mainBase..HEAD` staged diff.
- If the pre-existing tracked diff and task diff overlap or cannot be separated safely, stop and ask instead of creating a final commit, merge, push, PR, or final local storage.

In the non-null `preexistingTrackedCheckpoint` path, a plain direct `git reset --soft <mainBase>` is always unsafe and forbidden. Direct reset to `mainBase` is valid only when `preexistingTrackedCheckpoint` is `null`. When `preexistingTrackedCheckpoint` is non-null, require checkpoint-aware separation or reconstruction using `mainBase..preexistingTrackedCheckpoint` and `preexistingTrackedCheckpoint..HEAD`; if safe separation or reconstruction is impossible, preserve the worktree and stop and ask. Do not discard the pre-existing tracked checkpoint contents, and do not let those edits be silently folded into the final task commit, merge, or PR.

For normal finishing from the feature checkout, validate that the current branch is not detached. When metadata exists, validate that metadata `featureBranch` matches the current branch and that metadata `worktreePath` matches the current worktree when available. If these checks fail, stop and ask the user.

For retained PR worktree cleanup re-entry, require all of the following before Step 7 cleanup:
- The user explicitly requested cleanup of a retained PR worktree and provided the exact metadata path.
- The current shell is in the repository but is not inside the target worktree from metadata.
- `git worktree list --porcelain` contains a `worktree` record whose normalized path exactly matches metadata `worktreePath`.
- That same worktree entry contains `branch refs/heads/<feature-branch>`.
- The active-operation guard passes for the current cleanup checkout and for the target worktree when accessible.

In this retained-cleanup mode, do not require the current branch or current worktree to match metadata `featureBranch` or `worktreePath`. Use metadata `featureBranch` and `worktreePath` only to identify the target worktree and branch for Step 7. Do not use automatic active metadata matching for retained cleanup, because completed metadata is ignored by automatic matching.

For abandoned discard cleanup recovery re-entry, require all of the following before Step 7 cleanup:
- The user explicitly requested cleanup recovery of a previously confirmed discard and provided the exact metadata path.
- The user confirms the original Option 4 exact typed discard confirmation already happened, and that this entry is only to finish or remediate worktree removal and branch deletion.
- The current shell is in the repository but is not inside the target worktree from metadata when that target still exists.
- `git worktree list --porcelain` either contains a `worktree` record whose normalized path exactly matches metadata `worktreePath` and whose branch entry is `refs/heads/<feature-branch>`, or contains no `worktree` record for that exact normalized path when recovering after worktree removal already happened.
- Before deleting a branch, verify the local branch ref is exactly `refs/heads/<feature-branch>`, or verify it is already absent when cleanup recovery has no remaining branch deletion work.
- The active-operation guard passes for the current cleanup checkout and for the target worktree when accessible.
- The destination checkout cleanliness guard passes for the checkout used to perform cleanup.

In this abandoned cleanup recovery mode, do not require the current branch or current worktree to match metadata `featureBranch` or `worktreePath`. Use metadata `featureBranch` and `worktreePath` only to identify the target worktree and branch for Step 7, or to verify that the target worktree is already absent. Do not use automatic active metadata matching for abandoned cleanup recovery, because abandoned metadata is ignored by automatic matching.

When validated metadata exists, the recorded `mainBranch` is authoritative. Do not heuristically choose `main`, `master`, or any other base branch after metadata is found. Use the validated recorded `mainBranch` for Options 1, 2, and 4, or stop if it is missing, invalid, unavailable, or mismatched with the intended target.

Only after the user confirms this is an ordinary non-SDD branch with no recorded-base metadata expected, keep the existing finishing behavior and state that temporary checkpoint cleanup was not applied.

### Step 3: Determine Base Branch and Remote Without Metadata

Only when no recorded-base metadata exists, determine the base branch from actual branch names or explicit user confirmation. Do not use `git merge-base` output as a branch-name heuristic.

Before presenting options, determine the current feature branch:

```bash
git branch --show-current
```

Require a single non-empty current branch name and use that exact value as `<feature-branch>`. If the output is empty because `HEAD` is detached, blank, multi-line, or otherwise ambiguous, stop and ask the user before presenting options.

Use branch-name evidence such as the current branch's configured upstream, known local branch refs, known remote branch refs, or the user's explicit answer. If the evidence is ambiguous, ask the user to choose the intended `<base-branch>` before presenting merge or PR commands.

#### Resolve Remote and Branch From Upstream

Before branch-ref validation, fetch, push, remote-divergence checks, or PR operations, resolve `<remote>`, `<remote-branch>`, and `<upstream-short>` from the selected branch's configured upstream when one exists. The selected branch is `<base-branch>` for base branch validation and Option 1 fetch/fast-forward updates, and `<feature-branch>` for Option 2 push and remote-divergence checks.

Use Git's configured upstream data instead of assuming a remote name. `%(upstream:short)` returns the full short remote-tracking ref, such as `<remote>/<branch>`, not a branch-only name. Do not concatenate it with `<remote>` again.

```bash
git for-each-ref --format='%(upstream:remotename)' refs/heads/<selected-branch>
git for-each-ref --format='%(upstream:short)' refs/heads/<selected-branch>
git config --get branch.<selected-branch>.merge
```

If the selected branch has an upstream:
- Use `%(upstream:remotename)` as `<remote>`.
- Use `%(upstream:short)` as `<upstream-short>` for local remote-tracking refs, for example `refs/remotes/<upstream-short>`.
- Derive `<remote-branch>` from `branch.<selected-branch>.merge` by requiring a `refs/heads/<remote-branch>` value and stripping only the `refs/heads/` prefix.

If no upstream or remote is configured, keep a documented local-only path for actions that do not require network access, or ask the user to choose and confirm a remote before any fetch, push, remote-divergence check, or PR operation. Any fallback remote must require explicit confirmation; do not default to any remote name.

Before using `<base-branch>` in `git switch`, require it to resolve to a local branch ref:

```bash
git show-ref --verify --quiet refs/heads/<base-branch>
```

Before using `<pr-base>` in `gh pr create --base`, require the requested or user-confirmed PR base branch itself to resolve. Do not let an unrelated selected branch upstream satisfy PR base validation.

```bash
git show-ref --verify --quiet refs/heads/<pr-base>

# Or, when the PR base is confirmed to live on a specific remote-tracking branch:
git show-ref --verify --quiet refs/remotes/<pr-base-remote>/<pr-base-remote-branch>
```

For remote-tracking validation, `<pr-base-remote>/<pr-base-remote-branch>` must be the explicit remote-tracking ref for the same PR base branch the user requested or confirmed. If the branch name passed to `gh pr create --base <pr-base>` differs from `<pr-base-remote-branch>`, require explicit confirmation of that PR target before continuing. If the chosen PR base does not resolve to the required local or matching remote-tracking branch ref, stop and ask the user for a valid PR base instead of guessing.

### Step 4: Present Options

If tests pass, present exactly these 4 options:

```
Implementation complete. What would you like to do?

1. Merge back to <base-branch> locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)
4. Discard this work

Which option?
```

If tests fail, do not present or execute completion paths. Present only cleanup-safe non-completion choices, preserving the existing option identities:

```
Tests are still failing. What would you like to do?

3. Keep the branch as-is (no final local storage)
4. Discard this work

Which option?
```

**Don't add explanation** - keep options concise.

### Step 5: Mandatory Active-Operation Guard and Clean-History Preparation

Before executing Option 1, Option 2, Option 4, or any final local storage path, always confirm no merge, rebase, cherry-pick, or bisect is active, regardless of whether recorded-base metadata exists. This includes Option 3 when the user explicitly requests final local storage or user-approved final local commit(s). This active-operation guard applies to the source feature checkout and to any destination checkout used for local merge, cleanup, branch deletion, worktree removal, or final local storage. When the target linked worktree is accessible, check that target worktree too before removing it or deleting its branch.

For each checkout being used or affected, inspect the checkout-specific git paths for active operations, for example:

```bash
git rev-parse --git-path MERGE_HEAD
git rev-parse --git-path rebase-merge
git rev-parse --git-path rebase-apply
git rev-parse --git-path CHERRY_PICK_HEAD
git rev-parse --git-path BISECT_LOG
```

After resolving these checkout-specific git paths, explicitly check whether each returned marker file or directory exists, for example with `Test-Path -LiteralPath <resolved-path>` on PowerShell, `[ -e "<resolved-path>" ]` in POSIX shell, or an equivalent Git state check. Any existing marker means a merge, rebase, cherry-pick, or bisect is active; stop and ask the user before cleanup, merge, push, PR creation, discard cleanup, branch deletion, or worktree removal. Do not continue through a no-metadata fallback path while a merge, rebase, cherry-pick, or bisect is active.

Before using any destination checkout for `git switch`, fetch/merge, final local storage, branch deletion, or worktree removal, explicitly confirm that destination checkout has a clean worktree and clean index. This destination checkout cleanliness guard is additional to the active-operation guard and applies even when recorded-base metadata does not exist.

If dirty or staged local changes exist in a destination checkout and the user has not explicitly approved how to handle those exact local changes, stop and ask before continuing. Do not mix unrelated destination checkout changes into merge, discard, branch deletion, worktree removal, or final local storage flows. If the user approves a handling path, keep that approval scoped to the named checkout, paths, and operation.

Run the remaining clean-history preparation before any merge, push, PR creation, or final local storage when recorded-base metadata exists.

Require a clean commit for any final git storage:
- Explain that final git storage requires a clean commit built from the final file state, with temporary checkpoints removed from branch history.
- Ask the user before creating that final local commit.
- If the user does not approve the final local commit or final git storage, do not merge, push, or create a PR. After the active-operation guard passes and after explaining the concrete cleanup operation, remove temporary workflow commits from branch history with a content-preserving cleanup anchored at metadata `mainBase`, preserving the final tracked file contents in the worktree and index as uncommitted changes. Report that the work remains uncommitted because the final local commit was declined.
- The declined-final-commit path is not a partial-success state and must not preserve temporary workflow checkpoints merely because the final local commit was declined.
- If the declined-final-commit cleanup would rewrite permanent or user-approved commits, ask before rewriting them.
- If the user approves the final local commit, final history should contain only approved final commit(s), not intermediate temporary checkpoints.
- If the user has already approved specific permanent commits, do not rewrite them without asking.

Prefer a content-preserving soft reset or squash-style cleanup from metadata `mainBase` only when that cleanup preserves the checkpoint split described above. Do not recommend destructive reset, checkout, clean, or unconditional force deletion. Before running cleanup, explain the concrete operation for the current state.

Decision rules:
- If the current branch is detached, or metadata `featureBranch` does not match the current branch, stop and ask the user.
- If the worktree and index are clean, no permanent commits have been approved, and `preexistingTrackedCheckpoint` is `null`, an acceptable operation is a soft reset to `mainBase`, followed by one user-approved final commit from the staged final diff.
- If `preexistingTrackedCheckpoint` is non-null, do not use a direct soft reset to `mainBase` as the happy path. First complete the checkpoint-aware cleanup that separates `mainBase..preexistingTrackedCheckpoint` from `preexistingTrackedCheckpoint..HEAD`; preserve or reconstruct the pre-existing tracked diff separately as uncommitted changes, then commit only the task-approved result. If the diffs overlap or cannot be separated safely, stop and ask.
- If tracked files are dirty or staged, ask whether those changes are part of the final file state. If approved and `preexistingTrackedCheckpoint` is `null`, include them in the final commit after the soft reset; if approved and `preexistingTrackedCheckpoint` is non-null, include only the task-approved portion after checkpoint-aware cleanup; if not approved, stop for user direction.
- If new untracked files are part of the final deliverable, ask before adding them. Never add ignored files unless the user explicitly approves those exact paths.
- Preserve final tracked contents and do not delete untracked or ignored files.
- After cleanup, verify the final diff/content still contains the intended work before merge or push.
- If these checks cannot be satisfied safely, preserve the worktree and stop instead of forcing cleanup.

After a successful local merge, push/PR creation, or user-approved final local storage, update metadata `status` to `completed`. For options with required metadata-dependent cleanup before the workflow is considered complete, write `completed` only after those required cleanup steps succeed or after determining no cleanup re-entry is needed. Successful Option 2 PR creation still marks metadata completed even when the PR worktree is retained; do not reintroduce active metadata after successful Option 2 PR creation. If the user later asks to remove that retained PR worktree, require exact user-provided retained cleanup evidence such as the metadata path and target worktree context; do not rely on automatic active metadata matching. If cleanup or prechecks fail before a completion path succeeds, metadata must remain active so finishing can resume safely. For Option 4 discard, after exact typed discard confirmation and after all discard/removal prechecks pass, update recorded-base metadata `status` to `abandoned` immediately before irreversible worktree/branch removal when practical. If the metadata update itself cannot be performed safely, stop before removal and ask; do not remove the worktree while metadata still falsely says active if updating was practical but failed. If any discard precheck fails before the abandoned transition, leave recorded-base metadata `status` as `active` so finishing can resume safely. If worktree removal or branch deletion fails after the abandoned transition, use only exact-path abandoned discard cleanup recovery to finish or remediate cleanup; do not return to normal finishing or automatic matching. Do not delete metadata automatically unless the user asks.

### Step 6: Execute Choice

#### Option 1: Merge Locally

If recorded-base metadata exists, run Clean-History Preparation first and merge only after it succeeds. Use the validated recorded `mainBranch` as `<base-branch>`. If no metadata exists, state that temporary checkpoint cleanup was not applied and continue with the existing merge flow.

For linked worktrees, do not check out `<base-branch>` inside the feature linked worktree. Perform the merge from the original/main worktree or from another safe non-attached checkout that is not the current feature worktree. Confirm the destination checkout is on the validated recorded `mainBranch`, has no active merge/rebase/cherry-pick/bisect, has a clean worktree and clean index unless the user explicitly approved handling exact local changes there, and is safe to update before merging.

When the selected base branch has a configured upstream, update the destination base branch with an explicit fetch and fast-forward-only update from the `<remote>`, `<remote-branch>`, and `<upstream-short>` resolved from that upstream. Use `<remote-branch>` only as the branch name fetched from the remote, and use `refs/remotes/<upstream-short>` as the local remote-tracking ref. Do not use plain `git pull`, and do not rely on config-dependent pull behavior. If the destination base branch is not a clean fast-forward to the fetched base ref, stop and ask the user before merging.

```bash
# In the original/main worktree or another safe non-attached checkout
git switch <base-branch>

# Fetch and fast-forward only
git fetch <remote> <remote-branch>:refs/remotes/<upstream-short>
git merge --ff-only refs/remotes/<upstream-short>

# Merge feature branch
git merge <feature-branch>

# Verify tests on merged result
<test command>
```

When the selected base branch has no configured upstream, Option 1 may continue only as an explicitly local-only merge path. Validate the local `<base-branch>` ref, use the original/main worktree or another safe non-attached checkout, switch to `<base-branch>`, skip fetch and remote fast-forward, and state that no remote update was applied before merging. Push and PR creation still require an explicitly confirmed remote and must not reuse this local-only path.

```bash
# In the original/main worktree or another safe non-attached checkout
git show-ref --verify --quiet refs/heads/<base-branch>
git switch <base-branch>

# Local-only merge: no fetch, no remote fast-forward, and no remote update applied
git merge <feature-branch>

# Verify tests on merged result
<test command>
```

If tests pass, remove the feature worktree through Cleanup Worktree (Step 7) when it is a linked worktree attached to `<feature-branch>`. Delete `<feature-branch>` only from the original/main worktree or another safe non-attached checkout after confirming no worktree is currently attached to that branch:

```bash
git branch -d <feature-branch>
```

Then: finish Cleanup Worktree (Step 7) if it was not already needed before branch deletion.

#### Option 2: Push and Create PR

If recorded-base metadata exists, run Clean-History Preparation first and push/create the PR only after it succeeds. Use the validated recorded `mainBranch` as `<base-branch>` for PR creation, or stop if that recorded target is missing, unavailable, or mismatched with the intended PR base. If no metadata exists, state that temporary checkpoint cleanup was not applied and continue with the existing push/PR flow.

Before pushing a cleaned branch:
- Resolve `<remote>` from the selected feature branch's configured upstream. If no upstream exists, ask the user to choose and confirm the remote before pushing or creating a PR.
- Refresh remote state before any divergence comparison, remote branch existence check, or new/up-to-date/fast-forward/divergent classification.
- When an upstream exists, derive `<upstream-short>` and `<head-remote-branch>` as described in Step 3. Fetch the feature branch upstream target into the local remote-tracking ref before checking `refs/remotes/<upstream-short>` or comparing histories, for example `git fetch <remote> <head-remote-branch>:refs/remotes/<upstream-short>`. Use that same `<head-remote-branch>` for divergence checks and for the final push refspec.
- When no upstream exists and the user confirms a remote, use only an explicit branch name such as `<feature-branch>` or another user-confirmed `<head-remote-branch>`. Fetch or otherwise verify the current remote state for the exact user-confirmed `<head-remote-branch>` before deciding whether the remote branch is new, already up to date, fast-forwardable, or divergent; do not synthesize a doubled ref from `<remote>` plus `<upstream-short>`.
- After remote state refresh, if the remote branch exists, compare local and remote history and determine whether the push is a fast-forward, already up to date, or divergent. If the refreshed exact remote branch does not exist, treat the push as creating a new remote branch.
- If a non-fast-forward update is needed, stop and ask for explicit approval to use `--force-with-lease` or for a new branch name.
- Do not assume a plain push will succeed when histories diverge, and do not default to force push.
- If `<head-remote-branch>` differs from `<feature-branch>`, require explicit user confirmation before pushing to that remote branch.
- Resolve the PR base from the selected base branch's upstream target when known. Store that branch destination separately as `<base-remote-branch>` so it cannot be confused with the feature PR head. If the local `<base-branch>` name differs from `<base-remote-branch>` or the intended PR target branch, require explicit user confirmation and use that confirmed value as `<pr-base>`.
- Validate that `<pr-base>` names the PR base target and `<head-remote-branch>` names the feature PR head target. Do not reuse one placeholder for both values, and stop if the user-provided values are ambiguous.
- Treat `<head-remote-branch>` as the remote PR head after the push refspec succeeds or is validated as already up to date. Use that resolved or user-confirmed head explicitly in `gh pr create --head`; do not rely on GitHub's default head inference.
- If GitHub requires an owner-qualified head for a cross-repo PR, stop and require the user-confirmed `<head-owner>:<head-remote-branch>` value. Do not infer the head owner from the remote URL or local configuration.

PowerShell example:

```powershell
# Push branch only when it is new, fast-forward, or explicitly approved.
# Use the resolved or user-confirmed remote branch as the destination ref.
git push -u <remote> <feature-branch>:<head-remote-branch>

$prBody = New-TemporaryFile
@'
## Summary
<2-3 bullets of what changed>

## Test Plan
- [ ] <verification steps>
'@ | Set-Content -LiteralPath $prBody -Encoding UTF8

# Create PR against the resolved or user-confirmed PR base and remote head.
# For cross-repo PRs, use a user-confirmed owner-qualified head such as <head-owner>:<head-remote-branch>.
gh pr create --base <pr-base> --head <head-remote-branch> --title "<title>" --body-file $prBody
Remove-Item -LiteralPath $prBody
```

POSIX shell example:

```bash
# Push branch only when it is new, fast-forward, or explicitly approved.
# Use the resolved or user-confirmed remote branch as the destination ref.
git push -u <remote> <feature-branch>:<head-remote-branch>

pr_body_file="$(mktemp)"
cat >"$pr_body_file" <<'EOF'
## Summary
<2-3 bullets of what changed>

## Test Plan
- [ ] <verification steps>
EOF

# Create PR against the resolved or user-confirmed PR base and remote head.
# For cross-repo PRs, use a user-confirmed owner-qualified head such as <head-owner>:<head-remote-branch>.
gh pr create --base <pr-base> --head <head-remote-branch> --title "<title>" --body-file "$pr_body_file"
rm -f "$pr_body_file"
```

Then: Cleanup worktree (Step 7) only if the user asks to remove the worktree after PR creation. Otherwise preserve it.

If recorded-base metadata exists and PR creation succeeds, update metadata `status` to `completed` even when the user preserves the PR worktree. Retained PR worktree cleanup later requires exact user-provided retained cleanup evidence such as the metadata path and target worktree context; do not use automatic active metadata matching for that later cleanup.

When Option 2 completes with the PR worktree retained, provide a user-visible handoff that future retained PR cleanup is exact-path-only. Report the exact `metadataPath`, metadata `worktreePath`, and metadata `featureBranch` values from the validated metadata so the user can provide them in a future cleanup request.

#### Option 3: Keep As-Is

Report: "Keeping branch <name>. Worktree preserved at <path>."

If recorded-base metadata exists, do not mark metadata `status` as `completed` merely because the branch is kept as-is. If the user explicitly wants final local storage instead, apply the mandatory active-operation guard first, run Clean-History Preparation, create only the user-approved final local commit(s), then mark metadata `status` as `completed`.

Final local storage, final local commit(s), and metadata `status` transition to `completed` are available from Option 3 only when Step 1 tests have passed. In the failed-test flow, Option 3 is preserve-only: keep the branch and worktree as-is for later work, do not run clean-history preparation, do not create final local commit(s), and do not mark metadata `status` as `completed`.

**Don't cleanup worktree.**

#### Option 4: Discard

**Confirm first:**
```
This will permanently delete:
- Branch <name>
- All commits: <commit-list>
- Worktree at <path>

Type 'discard' to confirm.
```

Wait for exact confirmation.

After exact typed discard confirmation and after all prechecks pass, discard is the only path that may intentionally remove a dirty linked worktree. Before any Option 4 discard cleanup, branch deletion, or worktree removal, confirm no merge, rebase, cherry-pick, or bisect is active in the checkout used to perform cleanup and in the target worktree when it is accessible. If any active operation exists, stop and ask the user instead of deleting the branch or removing the worktree.

If any discard precheck fails before the abandoned transition, leave recorded-base metadata `status` as `active` so finishing can resume safely. After exact typed discard confirmation and after all discard/removal prechecks pass, update recorded-base metadata `status` to `abandoned` immediately before irreversible worktree/branch removal when practical. If the metadata update itself cannot be performed safely, stop before removal and ask; do not remove the worktree while metadata still falsely says active if updating was practical but failed. If worktree removal succeeds but branch deletion fails after the abandoned transition, require a later abandoned discard cleanup recovery request with the exact metadata path. In that recovery mode, treat the missing worktree only as an already-completed removal step after confirming `git worktree list --porcelain` no longer records that target worktree, then continue only with the remaining branch deletion checks.

When Option 4 transitions recorded-base metadata to `abandoned`, provide a user-visible handoff that abandoned discard cleanup recovery is exact-path-only. Report the exact `metadataPath`, metadata `worktreePath`, and metadata `featureBranch` values from the validated metadata. If cleanup fails after the abandoned transition, report those same exact values again as the required recovery evidence.

If confirmed, leave the feature linked worktree first if the current shell is inside it. From the original/main worktree or another safe non-attached checkout, remove the attached feature worktree through Cleanup Worktree (Step 7) before deleting a branch that is still checked out by that worktree. Use the validated recorded `mainBranch` as `<base-branch>` when metadata exists.

After the feature worktree is no longer attached:
```bash
# In the original/main worktree or another safe non-attached checkout
git switch <base-branch>
git branch -D <feature-branch>
```

Then: finish Cleanup Worktree (Step 7) if it was not already needed before branch deletion.

### Step 7: Cleanup Worktree

**For Options 1 and 4, and for Option 2 only when the user asks to remove the PR worktree:**

Remove the feature worktree only after the merge, push/PR, or discard decision no longer requires it and only when the current shell is not inside that attached feature checkout. For linked worktrees, operate from the original/main worktree or another safe non-attached checkout. Before removal, confirm the user-approved/discard-safe condition for the selected option still holds, the worktree path matches validated metadata when metadata exists or confirmed no-metadata refs when metadata does not exist, and no uncommitted work would be destroyed without explicit approval.

For retained PR worktree cleanup re-entry, Step 7 may be entered directly only when the user explicitly requested retained cleanup and provided exact retained cleanup evidence such as the completed metadata path and target worktree context. Use metadata `worktreePath` and `featureBranch` as the target identifiers, not the current checkout. Do not require the current branch or current worktree to match the metadata target, but require the current shell to be outside the target worktree before any removal or branch deletion.

For abandoned discard cleanup recovery re-entry, Step 7 may be entered directly only when the user explicitly requested cleanup recovery for a previously confirmed discard and provided the exact abandoned metadata path. Use metadata `worktreePath` and `featureBranch` as the target identifiers, not the current checkout. Do not require the current branch or current worktree to match the metadata target, but require the current shell to be outside the target worktree when the target still exists before any removal or branch deletion.

Before any Step 7 worktree removal or branch deletion, confirm no merge, rebase, cherry-pick, or bisect is active in the checkout used to perform cleanup and in the target worktree when it is accessible. This guard is mandatory for Option 4 discard cleanup as well as normal post-merge cleanup; if any active operation exists, stop and ask the user.

Identify the exact target worktree with porcelain output before removal:

```bash
git worktree list --porcelain
```

Use the `worktree` and `branch` records to confirm the target path is the validated `worktreePath` when metadata exists, or the user-confirmed worktree path when no metadata exists. Confirm the target `branch` record is `refs/heads/<feature-branch>` before deleting `<feature-branch>`.

For abandoned discard cleanup recovery, split Step 7 into explicit recovery branches after reading `git worktree list --porcelain`:

- If the target worktree is still present, validate that the worktree record path exactly matches normalized metadata `worktreePath`, its `branch` record is `refs/heads/<feature-branch>`, the current shell is outside that target path, and all active-operation and cleanup checkout guards pass. Then remove the target worktree from the original/main worktree or another safe non-attached checkout.
- If the target worktree is already absent, verify through `git worktree list --porcelain` that no record exists for the exact normalized metadata `worktreePath`. In this branch, skip `git worktree remove` because worktree removal is already complete, and proceed only to the remaining validated branch deletion or cleanup remediation checks. This verified absence does not permit merge, push, PR creation, a new discard decision, clean-history preparation, or final local storage.

Before any cleanup command in abandoned discard cleanup recovery, reconfirm the user intends only to finish or remediate the previously confirmed discard cleanup. Before deleting a branch in this mode, verify the local branch ref is exactly `refs/heads/<feature-branch>`, or verify it is already absent and report that no branch deletion is needed. Because abandoned discard cleanup recovery skips Step 6, include the remaining branch deletion/remediation action directly in Step 7:

```bash
# In the original/main worktree or another safe non-attached checkout
git switch <base-branch>
git branch -D <feature-branch>
```

Confirm the current shell is not inside the target worktree before removal or branch deletion:

```bash
git rev-parse --show-toplevel
```

Compare the current top-level path with the target worktree path, and stop if they match or if the current path is inside the target. Move to the original/main worktree or another safe non-attached checkout first.

For normal Option 4 discard with recorded-base metadata, after exact typed discard confirmation and after all discard/removal prechecks pass, update recorded-base metadata `status` to `abandoned` immediately before irreversible worktree/branch removal when practical. If the metadata update itself cannot be performed safely, stop before removal and ask; do not remove the worktree while metadata still falsely says active if updating was practical but failed. If cleanup later fails after this transition, resume only through exact-path abandoned discard cleanup recovery.

After the checks pass and the selected option allows worktree removal, or when abandoned discard cleanup recovery verified that the target worktree is still present:
```bash
# Run from the original/main worktree or another safe non-attached checkout
git worktree remove <worktree-path>
```

For Option 4 discard, successful worktree removal alone does not complete cleanup. After metadata has transitioned to `abandoned`, any failure in required worktree removal or branch deletion must be recovered only through exact-path abandoned discard cleanup recovery.

If this removal cleans up a retained Option 2 PR worktree and recorded-base metadata exists, leave metadata `status` as `completed` after removal succeeds. Retained cleanup must be driven by exact user-provided metadata/path evidence, not automatic active metadata matching.

Use forced worktree removal only for Option 4 discard, and only after all of these are true:
- The user has given the exact typed `discard` confirmation.
- The active-operation guard passes for the cleanup checkout and the target worktree when accessible.
- The current shell is not inside the target worktree.
- The target path and feature branch match validated metadata, or match user-confirmed no-metadata refs.
- The user has explicitly accepted losing dirty tracked changes, untracked files, and ignored files in the linked worktree.
- In abandoned discard cleanup recovery, force removal is allowed only if the original Option 4 typed discard was already confirmed and the user again explicitly accepts losing dirty tracked changes, untracked files, and ignored files in the still-present target worktree.

When every discard-only force precondition is satisfied and normal removal refuses because the target worktree is dirty, this command is permitted:

```bash
# Option 4 only, after exact typed discard confirmation and all force prechecks
git worktree remove --force <worktree-path>
```

Do not use `git worktree remove --force` for merge cleanup, PR cleanup, or any path other than confirmed Option 4 discard.

**For Option 3:** Keep worktree.

## Quick Reference

| Option | Merge | Push | Keep Worktree | Cleanup Branch |
|--------|-------|------|---------------|----------------|
| 1. Merge locally | ✓ | - | - | ✓ |
| 2. Create PR | - | ✓ | ✓ | - |
| 3. Keep as-is | - | - | ✓ | - |
| 4. Discard | - | - | - | ✓ (force only after typed discard and guard prechecks) |

## Common Mistakes

**Skipping test verification**
- **Problem:** Merge broken code, create failing PR
- **Fix:** Always verify tests before offering options

**Open-ended questions**
- **Problem:** "What should I do next?" → ambiguous
- **Fix:** Present exactly 4 structured options when tests pass; when tests fail, present only the restricted two-option flow: Option 3 keep-as-is/preserve or Option 4 discard

**Automatic worktree cleanup**
- **Problem:** Remove worktree when might need it (Option 2, 3)
- **Fix:** Preserve Option 2 and Option 3 worktrees by default; clean up Option 2 only when the user explicitly asks to remove the PR worktree

**Skipping metadata cleanup**
- **Problem:** Merge or push preserves temporary checkpoints
- **Fix:** When recorded-base metadata exists, prepare clean history from `mainBase` before merge, push, PR creation, or final local storage

**No confirmation for discard**
- **Problem:** Accidentally delete work
- **Fix:** Require typed "discard" confirmation

## Red Flags

**Never:**
- Proceed with failing tests
- Merge without verifying tests on result
- Delete work without confirmation
- Force-push without explicit request
- Merge or push a temporary checkpoint chain when recorded-base metadata exists
- Run destructive cleanup that deletes untracked or ignored files on merge cleanup, PR cleanup, retained cleanup, clean-history preparation, final local storage, or any other non-discard path
- Treat typed discard as a general cleanup permission. The sole exception is confirmed Option 4 typed discard after all force-removal prechecks pass and the user explicitly accepts losing dirty tracked changes, untracked files, and ignored files in that linked worktree.

**Always:**
- Verify tests before offering options
- Present exactly 4 options when tests pass; when tests fail, present only restricted Option 3 preserve or Option 4 discard
- Get typed confirmation for Option 4
- Preserve the Option 2 PR worktree by default, and clean it up only when the user explicitly asks
- Ask before creating a final local commit
- Preserve tracked contents during temporary checkpoint cleanup

## Integration

**Called by:**
- **subagent-driven-development** - After all tasks complete (passes or records metadata for cleanup of the worktree created during setup)
