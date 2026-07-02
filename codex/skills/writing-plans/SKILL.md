---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

## Overview

Write a comprehensive implementation plan assuming the implementer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume the implementer is a skilled developer, but knows almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Context:** Write the plan against the current repo state.

**Save plans to:** `docs/double-sdd/plans/YYYY-MM-DD-<feature-name>.md`

## Scope Check

This skill writes one plan file for the current requested scope.

If the request appears to span multiple independent features, modules, or deliverables, raise that concern to the user before finalizing the plan. Do not silently split the work into multiple plan files unless the user explicitly wants that.

The user owns the product boundary. Your job is to plan the requested scope clearly, not to quietly redefine it.

## Execution Model

This plan will later be executed from a dedicated `.worktrees/...` worktree by subagents.

Write the plan so it can be followed from repository state alone:
- use repo-relative paths
- use explicit commands
- do not rely on unstated local context, editor state, or session memory

The normal execution model is:
- execution proceeds sequentially through the plan
- one implementation task is typically handled by one fresh implementer subagent
- after each task is implemented, it goes through review before the next task continues
- the orchestrator will keep driving the plan until the full plan is complete unless it hits a real unresolved blocker

Write tasks so they fit that execution model:
- each task should be self-contained enough for one implementer subagent to complete
- each task should have clear spec boundaries and clear verification steps
- each task should leave the repo in a state that can be reviewed before moving on

## Runtime Metadata Handoff

`writing-plans` has two valid invocation modes:

1. Upstream `writing-specs` handoff: the invocation provides the exact runtime `metadataPath` created by `writing-specs`, with no `RUN_ID` and no `NO_UPSTREAM_METADATA`.
2. Direct/manual planning: the invocation explicitly provides the no-upstream signal `NO_UPSTREAM_METADATA=true`.

Default to stop-and-ask unless the invocation either provides an exact `metadataPath` or explicitly provides `NO_UPSTREAM_METADATA=true`. Do not silently treat a missing or broken `writing-specs` handoff as a manual planning run. A direct/manual run must not rely on omitted `metadataPath` alone.

If `writing-plans` is invoked with a runtime `metadataPath` from `writing-specs`, record the exact path in this planning run's orchestration and handoff context.

- Preserve the path exactly as received; do not reinterpret it from hidden session memory.
- Treat this as upstream metadataPath mode only. Do not include `RUN_ID` or `NO_UPSTREAM_METADATA` in the execution handoff with an upstream `metadataPath`.
- The plan document does not need to include `metadataPath` unless it is relevant to the durable implementation instructions.
- When the user approves execution, pass the exact same `metadataPath` to `subagent-driven-development` as part of the execution handoff.
- If the upstream `writing-specs` workflow created runtime metadata but did not provide the exact `metadataPath`, stop and ask for correction before continuing.
- For direct/manual planning runs, record `NO_UPSTREAM_METADATA=true` in the orchestration and handoff context. Do not invent a `metadataPath`; state that no runtime metadata path was received.
- If a direct/manual planning run should create a direct-entry execution run after approval, also collect and pass an explicit filesystem-safe `RUN_ID` with the same character rules used by `subagent-driven-development`: ASCII letters, numbers, `.`, `_`, and `-` only, with no `..`, path separators, drive prefixes, shell metacharacters, or non-ASCII characters. If `RUN_ID` is missing or unsafe, stop and ask before execution handoff.

## File Structure

Before defining tasks, map out which files will be created or modified and what each one is responsible for. This is where decomposition decisions get locked in.

- Design units with clear boundaries and well-defined interfaces. Each file should have one clear responsibility.
- You reason best about code you can hold in context at once, and your edits are more reliable when files are focused. Prefer smaller, focused files over large ones that do too much.
- Files that change together should live together. Split by responsibility, not by technical layer.
- In existing codebases, follow established patterns. If the codebase uses large files, don't unilaterally restructure - but if a file you're modifying has grown unwieldy, including a split in the plan is reasonable.

This structure informs the task decomposition. Each task should produce self-contained changes that make sense independently.

## Code Discipline Constraints

When code changes are expected, read the spec for exception and global-state constraints and incorporate them into the implementation plan as concrete implementation steps, review instructions, and verification expectations where relevant.

- If the spec includes exception behavior constraints, turn them into concrete implementation and review instructions. Do not add new throw sites unless each one has clear semantic, diagnostic, or recovery value.
- If the spec includes global-state constraints, plan class or instance scope where sufficient. If a global constant is necessary, place it under an appropriate `consts` directory following project conventions.

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

## Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

> **For agentic workers:** REQUIRED: Use the `subagent-driven-development` skill to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

## Task Structure

````markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

- [ ] **Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

## Remember

- Exact file paths always
- Complete code in plan (not "add validation")
- Exact commands with expected output
- Reference relevant skills by name
- DRY, YAGNI, TDD, frequent commits
- This plan will later be executed from a dedicated worktree in a sequential subagent workflow, so write it to be reproducible from repo state alone
- If you discover an undiscussed question or ambiguity while writing the plan, stop and ask the user. Do not fill gaps with assumptions.

## Plan Review Loop

After completing the full plan document:

1. Dispatch `plan-document-reviewer` via `spawn_agent`
   - `agent_type: plan-document-reviewer`
   - `fork_context: false`
   - Provide exactly these fields in the review message:
     - `Spec: <path to the spec document>`
     - `Plan: <path to the plan document>`
   - Never pass your session history or chain-of-thought
2. If ❌ Issues Found:
   - Fix the issues in the plan
   - Re-dispatch reviewer against the updated full plan document
   - Repeat until ✅ Approved
3. If ✅ Approved: proceed to the execution handoff

**Review loop guidance:**
- Review the full plan file by default. Do not invent internal "chunks" or review arbitrary sections in isolation.
- If the plan becomes so long that it is difficult to review or execute coherently, raise that concern to the user. Do not automatically split it into multiple plan files unless the user explicitly wants that.
- The same agent that wrote the plan fixes it (preserves context)
- If loop exceeds 5 iterations, surface to human for guidance
- Reviewer feedback is advisory, not authoritative. Evaluate it against the spec, the repo reality, and the execution needs of the plan.
- If reviewer feedback is incorrect, overreaching, or not worth applying, keep the plan and record the reason briefly instead of obeying mechanically.

## Execution Handoff

After the plan document is complete and the plan review loop has approved it, ask the user for approval before invoking `subagent-driven-development` or beginning implementation.

Do not start implementation from this skill until the user has explicitly agreed to execute the reviewed plan.

**"Plan complete and saved to `docs/double-sdd/plans/<filename>.md`. Ready to execute?"**

**REQUIRED:** Use the `subagent-driven-development` skill for execution.
- Fresh subagent per task + parallel spec/quality review with a spec gate
- If this planning run received a runtime `metadataPath`, pass that exact `metadataPath` to `subagent-driven-development` in the execution handoff without `RUN_ID` or `NO_UPSTREAM_METADATA`.
- If this planning run used `NO_UPSTREAM_METADATA=true`, pass `NO_UPSTREAM_METADATA=true` and the explicit filesystem-safe `RUN_ID` to `subagent-driven-development`; do not pass an omitted `metadataPath` as the only signal for direct/manual execution.
- If this planning run received a runtime `metadataPath` and the user declines execution, discards the plan, or ends the workflow after planning rather than intentionally leaving execution pending, update the handed-off metadata `status` to `abandoned` when practical before ending.
- Keep handed-off metadata `status` as `active` only when execution is intentionally pending or when passing the exact `metadataPath` to `subagent-driven-development` after approval.
