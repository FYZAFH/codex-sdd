---
name: finishing-a-development-branch
description: Use when implementation is complete and verified - either present merge/PR/keep/discard options or report branch completion to the caller.
---

# Finishing a Development Branch

## Overview

Guide completion of development work by verifying the branch and either
presenting direct options or reporting completion to the caller.

**Core principle:** Verify tests → determine integration mode → either execute
the chosen direct option or report branch-completion evidence to the caller.

**Announce at start:** "I'm using the finishing-a-development-branch skill to complete this work."

## The Process

### Step 1: Verify Tests

**Before presenting options or reporting completion, verify tests pass:**

```bash
# Run project's test suite
npm test / cargo test / pytest / go test ./...
```

**If tests fail:**
```
Tests failing (<N> failures). Must fix before completing:

[Show failures]

Cannot proceed with merge/PR until tests pass.
```

Stop. Don't proceed to Step 2.

**If tests pass:** Continue to Step 2.

### Step 2: Determine Base Branch

```bash
# Try common base branches
git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null
```

In option mode, ask if needed: "This branch split from main - is that correct?"

In report mode, ask the caller if needed.

### Step 3: Determine Integration Mode

Use **report mode** when running under `direction-worker-conductor` or when the
task prompt says branch completion must be reported rather than offered as a
menu.

Use **option mode** otherwise.

### Step 4A: Option Mode - Present Options

Present exactly these 4 options:

```
Implementation complete. What would you like to do?

1. Merge back to <base-branch> locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)
4. Discard this work

Which option?
```

**Don't add explanation** - keep options concise.

### Step 4B: Report Mode - Report Completion

Do not present the 4-option menu.

Instead, leave the branch unmerged unless the caller explicitly pre-authorized
the exact merge path. Produce a completion report for the caller with:

- branch and worktree path;
- tip commit and base or merge-base;
- task commits;
- spec, plan, per-task review, and whole-implementation review status;
- stop-condition contacts and approved exceptions;
- verification commands with exact pass/fail counts;
- build and `git diff --check` results;
- touched-file list and file-size evidence;
- rebase/merge risk if the base branch has advanced;
- final `git status --short --branch`;
- explicit note that unrelated local work was left untouched.

If the caller already pre-authorized a local merge, run the specified
no-fast-forward merge, verify on the merged base branch, clean up only
task-owned worktrees/branches, and report the merge commit, parents,
verification evidence, cleanup result, and final status.

### Step 5: Option Mode - Execute Choice

#### Option 1: Merge Locally

```bash
# Switch to base branch
git checkout <base-branch>

# Pull latest
git pull

# Merge feature branch
git merge <feature-branch>

# Verify tests on merged result
<test command>

# If tests pass
git branch -d <feature-branch>
```

Then: Cleanup worktree (Step 6)

#### Option 2: Push and Create PR

```bash
# Push branch
git push -u origin <feature-branch>

# Create PR
gh pr create --title "<title>" --body "$(cat <<'EOF'
## Summary
<2-3 bullets of what changed>

## Test Plan
- [ ] <verification steps>
EOF
)"
```

Report the PR URL and keep the branch/worktree unless the user explicitly asks
for cleanup.

#### Option 3: Keep As-Is

Report: "Keeping branch <name>. Worktree preserved at <path>."

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

If confirmed:
```bash
git checkout <base-branch>
git branch -D <feature-branch>
```

Then: Cleanup worktree (Step 6)

### Step 6: Cleanup Worktree

**For Options 1 and 4:**

Check if in worktree:
```bash
git worktree list | grep $(git branch --show-current)
```

If yes:
```bash
git worktree remove <worktree-path>
```

**For Options 2 and 3:** Keep worktree unless explicitly instructed otherwise.

## Quick Reference

| Option | Merge | Push | Keep Worktree | Cleanup Branch |
|--------|-------|------|---------------|----------------|
| 1. Merge locally | ✓ | - | - | ✓ |
| 2. Create PR | - | ✓ | ✓ | - |
| 3. Keep as-is | - | - | ✓ | - |
| 4. Discard | - | - | - | ✓ (force) |

## Common Mistakes

**Skipping test verification**
- **Problem:** Merge broken code, create failing PR
- **Fix:** Always verify tests before offering options

**Open-ended questions**
- **Problem:** "What should I do next?" → ambiguous
- **Fix:** Present exactly 4 structured options

**Automatic worktree cleanup**
- **Problem:** Remove worktree when might need it (Option 2, 3)
- **Fix:** Only cleanup for Options 1 and 4

**No confirmation for discard**
- **Problem:** Accidentally delete work
- **Fix:** Require typed "discard" confirmation

## Red Flags

**Never:**
- Proceed with failing tests
- Merge without verifying tests on result
- Delete work without confirmation
- Force-push without explicit request
- In report mode, present the 4-option branch menu
- In report mode, self-merge without caller approval

**Always:**
- Verify tests before offering options
- Present exactly 4 options in option mode
- Report branch-completion evidence in report mode
- Get typed confirmation for Option 4
- Clean up worktree for Options 1 & 4 only

## Integration

**Called by:**
- **subagent-driven-development** - After all tasks complete (cleans up worktree created during setup)
