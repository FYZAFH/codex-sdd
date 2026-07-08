---
name: writing-specs
description: "You MUST use this before any implementation work. Clarifies requirements, explores approaches, validates the design, and writes the approved spec before planning."
---

# Writing Specs

Turn ideas into an approved design and written spec through collaborative dialogue.

<HARD-GATE>
Do NOT write code, scaffold anything, or invoke any implementation skill until you have:
1. explored the current project context
2. resolved material product questions
3. presented the design
4. received user approval

This applies to EVERY project regardless of perceived simplicity.
</HARD-GATE>

<QUESTION-GATE>
If any material product question is unresolved, stop and ask the user before moving forward.

Treat unresolved questions as blockers. This includes:
- missing behavior decisions
- unclear constraints or success criteria
- unknown edge cases or failure handling
- unresolved compatibility expectations
- ambiguous scope boundaries

Do NOT carry unresolved questions into approach selection, design approval, spec writing, review loops, or the handoff to `writing-plans`.

Surface these questions early so you can move into each next step with confidence, not silent doubts.
</QUESTION-GATE>

## Core Rules

- Every project goes through this flow, even if it looks simple. The design can be short, but it still must be explicit and approved.
- Ask one question at a time.
- If the request is too large for one spec, stop and help the user decompose it before continuing.
- Explicitly determine the compatibility posture before locking the design.
- The normal successful terminal state of `writing-specs` is invoking `writing-plans` with the exact runtime `metadataPath` created for this development task.
- Because `writing-specs` creates runtime metadata at the start of a new development task, do not invoke `writing-plans` without the exact `metadataPath` on a successful handoff.
- If metadata creation or exact-path handoff cannot be completed, stop and ask the user for correction instead of invoking `writing-plans` without a path.
- If the user stops or discards the workflow before handoff, mark pre-handoff metadata `status` as `abandoned` when practical, then stop.
- Do not invoke implementation skills or imply implementation starts from `writing-specs`.

## Source Scope Guard

- When modifying this project's source skills, target files under `codex/skills/...`.
- Installed or runtime copies under dot-prefixed directories such as `.agents/` and `.codex/` are out of scope unless the user explicitly asks to modify them.
- Do not synchronize local installed copies after changing the project source unless the user explicitly requests it.

## Git Hygiene

- At the start of every new development task, record the current `HEAD` as the immutable base even if the worktree starts clean.
- Use the recorded base as the cleanup anchor for the whole workflow.
- If tracked files already have changes, commit those tracked changes as a temporary checkpoint before writing design or plan documents.
- If untracked or ignored files already exist, record their paths as pre-existing local state in non-committed orchestration metadata; do not add ignored or unrelated untracked files merely to checkpoint them.
- Preserve staged and partially staged user intent when practical. If checkpointing would blur that boundary, stop and ask the user before proceeding.
- Treat later workflow commits, including the approved-spec commit, as temporary checkpoints unless the user approves a final local commit.
- Before history cleanup, confirm there is no active merge, rebase, cherry-pick, or bisect. If one is active, stop and ask the user.
- During cleanup, preserve tracked file contents and do not delete untracked or ignored files.
- Choose and explain a concrete content-preserving cleanup operation for the current state.
- Treat upstream alignment as advisory. Prefer not to leave unnecessary local commits on top of the configured upstream; if a named upstream does not exist, report it and compare with the actual configured upstream when available.
- Ask the user before creating a final local commit.

Acceptable final states:

- Without user approval for a final local commit, temporary workflow commits should be removed from the branch being integrated back to the original worktree, using the recorded base as the cleanup anchor, while final file contents remain in the worktree.
- With user approval for a final local commit, final history should contain only approved final commit(s), not intermediate temporary checkpoints.
- Do not rewrite user-approved permanent commits without asking.
- Cleanup applies at the end of the full requested task, after planning and implementation complete or after the user stops the workflow.

Workflow ownership rules:

- `writing-specs` owns recording the immutable base and checkpointing pre-existing local tracked changes before spec or plan work begins.
- `writing-specs` owns creating the initial non-committed JSON metadata file before spec or plan work begins.
- `writing-specs` must record base/checkpoint context so later workflow steps can use the same cleanup anchor. Local-only inventories, such as untracked or ignored path lists, and temporary checkpoint identifiers must stay in non-committed orchestration metadata and must not be written into committed specs. Committed specs may include only durable metadata that remains valid after cleanup, such as the recorded base, and must not include checkpoint commit identifiers.
- Later planning, implementation, review, and finishing steps must treat the recorded base as the cleanup anchor.
- Final cleanup and integration are owned by the later finishing/integration step on the branch being integrated back to the original worktree, and must preserve final file contents.
- If the worktree starts clean, still record the current base before creating workflow commits.

## Runtime Metadata Contract

At the start of a new development task, after recording the current `HEAD` as the immutable base and before spec or plan work begins, create a repo-local ignored metadata file at `.worktrees/<run-id>.metadata.json`.

- Metadata is UTF-8 JSON runtime workflow state and must not be committed.
- This runtime metadata under `.worktrees` is allowed only as non-committed workflow state; it must not be committed and does not permit source modifications under dot-prefixed directories such as `.agents/` or `.codex/`.
- Initial metadata creation must run from the original main worktree, not from a linked worktree. First confirm the current checkout is the original main worktree; if it is a linked worktree or this cannot be confirmed, stop and ask the user to rerun from the original main worktree. Only after that check passes, derive the repository root with `git rev-parse --show-toplevel` and derive the repo-local worktree area as `<repo-root>/.worktrees`.
- Before writing `mainBranch`, run `git branch --show-current` and reject detached `HEAD` or a blank branch name. Stop and ask instead of writing ambiguous `mainBranch` state.
- Before the first metadata write, prove that `.worktrees` is a repo-local directory under the root from `git rev-parse --show-toplevel` and is not a symlink, junction, or other reparse point. If this cannot be proven, stop before writing metadata.
- Before the first metadata write, prove that `.worktrees/` itself is git-ignored as the repo-local ignored worktree area, for example with `git check-ignore -- .worktrees/` or the platform-equivalent directory path with a trailing slash. Also prove git currently ignores the exact target metadata path, for example with `git check-ignore -- .worktrees/<run-id>.metadata.json`. If either ignore proof fails, stop before writing metadata.
- Before any read or write of the exact `.worktrees/<run-id>.metadata.json` file, run `lstat` or an equivalent check on that final path itself. If the final path already exists as a symlink, junction, or other reparse point, reject it even if its resolved target remains inside `.worktrees`.
- Before the first metadata write, resolve the target `.worktrees/<run-id>.metadata.json` path and prove the normalized absolute path remains inside the repository's `.worktrees` directory. On Windows, use case-insensitive normalized absolute path comparison. If containment fails, stop before writing metadata.
- `runId` must be filesystem-safe: ASCII letters, numbers, `.`, `_`, and `-` only, and must not contain `..` anywhere.
- `metadataPath` must be a repo-relative POSIX path exactly matching `.worktrees/<run-id>.metadata.json`, top-level under `.worktrees`.
- Because `metadataPath` is derived from `runId`, reject any `runId` or metadata path containing `..`, parent traversal, path separators inside `runId`, drive prefixes, absolute paths, shell metacharacters, or non-ASCII characters.
- `metadataPath` must resolve under the repository `.worktrees` directory after path normalization.
- Do not follow symlinked metadata paths outside `.worktrees`.
- On Windows, compare normalized absolute paths case-insensitively for containment checks.
- Do not overwrite an existing metadata file for a different `runId`.
- Do not store file contents, environment variables, tokens, or command output.

Initial metadata written by `writing-specs`:

```json
{
  "schemaVersion": 1,
  "runId": "YYYYMMDD-HHMMSS-topic",
  "status": "active",
  "mainBranch": "<branch at task start>",
  "mainBase": "<40-character commit sha>",
  "featureBranch": null,
  "worktreePath": null,
  "metadataPath": ".worktrees/YYYYMMDD-HHMMSS-topic.metadata.json",
  "preexistingTrackedCheckpoint": null,
  "temporaryCheckpoints": [],
  "preexistingUntracked": [],
  "preexistingIgnored": []
}
```

Metadata field rules:

- `schemaVersion` is `1`.
- `status` starts as `active`.
- `mainBranch` is the branch at task start.
- `mainBase` is the immutable base recorded from `HEAD`, even when the worktree starts clean.
- `featureBranch` and `worktreePath` start as `null`; later isolated-worktree setup updates them.
- `metadataPath` stores the same repo-relative POSIX path used to create the metadata file.
- `preexistingTrackedCheckpoint` is `null` unless tracked files already changed before spec or plan work. If tracked files already changed, checkpoint those tracked changes before spec or plan work and record that checkpoint only in metadata.
- `temporaryCheckpoints` starts as an empty array and later stores workflow checkpoint commit identifiers only in metadata.
- `preexistingUntracked` and `preexistingIgnored` store only path strings for pre-existing untracked or ignored files. Do not add ignored or unrelated untracked files just to checkpoint them, and do not copy these inventories into committed specs.

Metadata lifecycle rules:

- `writing-specs` creates metadata with `status: "active"` before spec or plan work begins, so `writing-specs` owns the metadata lifecycle until implementation handoff ownership begins.
- If the workflow is stopped, discarded, or will not be handed off to `writing-plans`, `writing-specs` must update the metadata `status` to `abandoned` before ending the workflow when practical.
- Marking pre-implementation metadata as `abandoned` removes stale runs from active candidate lookup while preserving the non-committed runtime record.
- Status ownership transfers only after the metadata path is explicitly passed to `writing-plans`.
- After that transfer, downstream planning, implementation, finishing, or subagent skills own later status transitions from `active` to `completed` or `abandoned`.
- Keep metadata non-committed. Do not delete the metadata file automatically unless the user asks.

Fresh downstream agents and later skills must receive, read, and pass this metadata path explicitly instead of relying on hidden session memory.

## Workflow

1. Explore the current project context: relevant files, docs, recent commits, and existing patterns.
2. Assess scope early. If the request spans multiple independent subsystems or deliverables, stop and decompose it with the user first.
3. Ask clarifying questions one at a time until purpose, constraints, success criteria, edge cases, and compatibility expectations are explicit.
4. Propose 2-3 approaches with trade-offs and recommend one.
5. Present the design in sections scaled to the complexity of the work and get user approval as you go.
6. If approval, spec writing, or review feedback exposes a new unresolved question, stop and return to the clarification loop.
7. Write the approved spec to `docs/double-sdd/specs/YYYY-MM-DD-<topic>-design.md`
8. Run the `spec-document-reviewer` loop until the spec is approved or you hit 5 iterations.
9. Ask the user to review the written spec.
10. If the user requests changes, update the spec and re-run review as needed.
11. After both the spec review loop and the user review pass, commit the approved spec document.
12. Invoke `writing-plans` with the exact runtime `metadataPath` created for this development task. If metadata creation or exact-path handoff cannot be completed, stop and ask the user for correction instead of invoking `writing-plans` without a path.

## Understanding the Request

- Check the current repo before asking detailed questions.
- Prefer multiple-choice questions when possible, but use open-ended questions when needed.
- Momentum is never a reason to skip a needed question.
- If it is unclear whether backward compatibility matters, ask.

Compatibility posture must cover:
- whether backward compatibility is required, not required, or partial
- which surfaces are protected: API, CLI, config, file format, database schema, user-visible behavior, or other project-specific surfaces
- which breaking changes are acceptable, if any
- whether migration, compatibility layers, or deprecation support are required

## Designing

- Propose 2-3 approaches with clear trade-offs.
- Lead with your recommendation and explain why.
- Cover the level of detail the work actually needs: architecture, components, data flow, error handling, and testing.
- When code changes are expected, capture exception behavior deliberately in the generated spec. Name failure boundaries clearly, require new exception throwing to have semantic, diagnostic, or recovery value, and disallow overdefensive broad catching unless the boundary and justification are explicit.
- When code changes are expected, capture global state decisions deliberately in the generated spec. Prefer class or instance scope when that is enough. If a global constant is necessary, place it under an appropriate `consts` directory following project conventions.
- Design smaller units with clear responsibilities and interfaces.
- Follow existing codebase patterns unless the work requires targeted structural improvement.
- Do not introduce unrelated refactors.

## Writing the Spec

- Write the validated design to `docs/double-sdd/specs/YYYY-MM-DD-<topic>-design.md`
- User preferences for spec location override this default.
- Include a `Compatibility / Migration` section with:
  - `Backward compatibility: required | not required | partial`
  - `Protected surfaces: [...]`
  - `Allowed breakage: [...]`
  - `Migration strategy: none | compatibility layer | migration script | deprecation window | other`
- When code changes are expected, include constraints for meaningful exception throwing and cautious global state so `writing-plans` can turn them into concrete implementation and review steps.
- For exception constraints, state where failures should be handled, propagated, or normalized, and call out unjustified broad catches, silent fallback, and duplicate defensive wrapping as disallowed.
- Do not hide unresolved questions behind `TBD`, `later`, or vague wording.
- If writing the spec exposes a new unresolved product decision, constraint, edge case, or compatibility question, stop and ask the user before continuing.

## Spec Review Loop

After writing the spec document:

1. Dispatch `spec-document-reviewer` via `spawn_agent`
2. Use:
   - `agent_type: spec-document-reviewer`
   - `fork_context: false`
3. Provide the spec file path and only the minimal review context needed.
4. Never pass your session history or chain-of-thought.
5. If the reviewer returns required clarifications that you can resolve with the current context, update the spec and re-dispatch.
6. If the reviewer returns a required clarification that depends on a new unresolved product question or compatibility requirement, stop and ask the user before continuing.
7. If the loop exceeds 5 iterations, surface it to the user.

## User Review Gate

After the spec review loop passes, ask the user to review the written spec before proceeding.

Use:

> "Spec written to `<path>`. Please review it and let me know if you want any changes before we write the implementation plan."

Wait for the user's response. If they request changes, update the spec and re-run review as needed.

## Commit Gate

After both the spec review loop and the user review pass, commit the approved spec document to git.

## Completion

The normal successful terminal state of `writing-specs` is invoking `writing-plans` with the exact runtime `metadataPath` created for this development task.

Because `writing-specs` creates runtime metadata at the start of a new development task, successful completion must pass that exact `metadataPath` to `writing-plans`. If metadata creation or exact-path handoff cannot be completed, stop and ask the user for correction instead of invoking `writing-plans` without a path.

If the user stops or discards the workflow before that handoff, update pre-handoff metadata `status` to `abandoned` when practical and stop without invoking `writing-plans`.

Do NOT invoke any implementation skill after `writing-specs`.
