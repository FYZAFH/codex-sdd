---
name: writing-specs
description: "You MUST use this before any implementation work. Clarifies requirements, explores approaches, validates the design, and writes the approved spec before planning."
---

# Writing Specs

Help turn ideas into fully formed designs and specs through natural collaborative dialogue.

Start by understanding the current project context, then ask questions one at a time to refine the idea. Once you understand what you're building, present the design and get user approval.

<HARD-GATE>
Do NOT invoke any implementation skill, write any code, scaffold any project, or take any implementation action until you have presented a design and the user has approved it. This applies to EVERY project regardless of perceived simplicity.
</HARD-GATE>

<QUESTION-GATE>
If any material product question is unresolved, stop and ask the user before moving forward.

Treat unresolved questions as blockers, not as details to smooth over later. This includes:
- missing behavior decisions
- unclear constraints or success criteria
- unknown edge cases or failure handling
- unresolved compatibility expectations
- ambiguous scope boundaries

Do NOT carry unresolved questions forward into approach selection, design approval, spec writing, review-response loops, or the handoff to `writing-plans`.

The purpose of surfacing these questions early is to let you move into each next step with confidence, not with silent doubts.
</QUESTION-GATE>

## Anti-Pattern: "This Is Too Simple To Need A Design"

Every project goes through this process. A todo list, a single-function utility, a config change — all of them. "Simple" projects are where unexamined assumptions cause the most wasted work. The design can be short (a few sentences for truly simple projects), but you MUST present it and get approval.

## Checklist

You MUST create a task for each of these items and complete them in order:

1. **Explore project context** — check files, docs, recent commits
2. **Ask clarifying questions** — one at a time, aggressively surface unknowns until purpose, constraints, and success criteria are explicit
3. **Determine compatibility posture** — explicitly decide whether backward compatibility is required, for which surfaces, and whether migration/deprecation support is needed
4. **Propose 2-3 approaches** — with trade-offs and your recommendation
5. **Present design** — in sections scaled to their complexity, get user approval after each section
6. **Write design doc** — save to `docs/double-sdd/specs/YYYY-MM-DD-<topic>-design.md` and commit
7. **Spec review loop** — dispatch spec-document-reviewer subagent with precisely crafted review context (never your session history); fix issues and re-dispatch until approved (max 5 iterations, then surface to human)
8. **User reviews written spec** — ask user to review the spec file before proceeding
9. **Transition to implementation** — invoke writing-plans skill to create implementation plan

## Progress Flow

1. Explore project context.
2. Ask clarifying questions one at a time until the goal, constraints, and success criteria are clear enough to design.
3. If any material uncertainty remains, continue asking. Do not move forward with hidden questions.
4. Explicitly determine the compatibility posture before locking the design.
5. Propose 2-3 approaches with trade-offs and a recommendation.
6. Present the design in sections and get approval as you go.
7. If the user wants changes, revise and re-present the affected sections.
8. Once the design is approved, write the spec document.
9. Run the spec-document-reviewer loop until the spec is approved.
10. If writing the spec or addressing reviewer feedback exposes a new unresolved product decision, behavior question, constraint, edge case, or compatibility requirement, stop and return to the clarifying-question loop. Ask the user, update the design/spec, then continue.
11. After the spec review loop passes, ask the user to review the written spec.
12. If the user requests changes, update the spec, re-run spec review, and ask again if needed.
13. Only after the written spec is approved do you invoke `writing-plans`.

**The terminal state is invoking writing-plans.** Do NOT invoke any other implementation skill. The ONLY skill you invoke after `writing-specs` is `writing-plans`.

## The Process

**Understanding the idea:**

- Check out the current project state first (files, docs, recent commits)
- Before asking detailed questions, assess scope: if the request describes multiple independent subsystems (e.g., "build a platform with chat, file storage, billing, and analytics"), flag this immediately. Don't spend questions refining details of a project that needs to be decomposed first.
- If the project is too large for a single spec, help the user decompose into sub-projects: what are the independent pieces, how do they relate, what order should they be built? Then take the first sub-project through the normal `writing-specs` flow. Each sub-project gets its own spec → plan → implementation cycle.
- For appropriately-scoped projects, ask questions one at a time to refine the idea
- Prefer multiple choice questions when possible, but open-ended is fine too
- Only one question per message - if a topic needs more exploration, break it into multiple questions
- Focus on understanding: purpose, constraints, success criteria
- Asking a needed question is always better than pushing forward with an assumption. Momentum is not a reason to skip clarification.
- If you notice a missing decision, stop the current thread of work and ask. Do not "note it for later" unless the user explicitly told you to defer it.
- Before finalizing the design, explicitly determine the compatibility posture for any existing or user-visible surface. If it is unclear whether backward compatibility matters, ask.
- Compatibility posture means all of the following:
  - whether backward compatibility is required, not required, or partial
  - which surfaces are protected: API, CLI, config, file format, database schema, user-visible behavior, or other project-specific surfaces
  - which breaking changes are acceptable, if any
  - whether a migration strategy, compatibility layer, or deprecation window is required

**Exploring approaches:**

- Propose 2-3 different approaches with trade-offs
- Present options conversationally with your recommendation and reasoning
- Lead with your recommended option and explain why

**Presenting the design:**

- Once you believe you understand what you're building, present the design
- Scale each section to its complexity: a few sentences if straightforward, up to 200-300 words if nuanced
- Ask after each section whether it looks right so far
- Cover: architecture, components, data flow, error handling, testing
- Be ready to stop and ask a clarifying question immediately if something does not make sense

**Design for isolation and clarity:**

- Break the system into smaller units that each have one clear purpose, communicate through well-defined interfaces, and can be understood and tested independently
- For each unit, you should be able to answer: what does it do, how do you use it, and what does it depend on?
- Can someone understand what a unit does without reading its internals? Can you change the internals without breaking consumers? If not, the boundaries need work.
- Smaller, well-bounded units are also easier for you to work with - you reason better about code you can hold in context at once, and your edits are more reliable when files are focused. When a file grows large, that's often a signal that it's doing too much.

**Working in existing codebases:**

- Explore the current structure before proposing changes. Follow existing patterns.
- Where existing code has problems that affect the work (e.g., a file that's grown too large, unclear boundaries, tangled responsibilities), include targeted improvements as part of the design - the way a good developer improves code they're working in.
- Don't propose unrelated refactoring. Stay focused on what serves the current goal.

## After the Design

**Documentation:**

- Write the validated design (spec) to `docs/double-sdd/specs/YYYY-MM-DD-<topic>-design.md`
  - (User preferences for spec location override this default)
- Use elements-of-style:writing-clearly-and-concisely skill if available
- Commit the design document to git
- Include an explicit `Compatibility / Migration` section in the spec with:
  - `Backward compatibility: required | not required | partial`
  - `Protected surfaces: [...]`
  - `Allowed breakage: [...]`
  - `Migration strategy: none | compatibility layer | migration script | deprecation window | other`
- Do not hide unresolved questions behind placeholders such as `TBD`, "to decide later", or vague wording. Ask the user instead.
- If writing the spec reveals an undiscussed requirement, decision, edge case, constraint, or compatibility question, pause writing and ask the user before continuing

**Spec Review Loop:**
After writing the spec document:

1. Dispatch `spec-document-reviewer` via `spawn_agent`
   - `agent_type: spec-document-reviewer`
   - `fork_context: false`
   - Provide the spec file path and only the minimal review context needed
   - Never pass your session history or chain-of-thought
2. If Issues Found because the spec is incomplete, inconsistent, or unclear but you already have enough context, fix it and re-dispatch
3. If fixing reviewer issues reveals a new unresolved product question, missing decision, or compatibility requirement, stop and ask the user one question at a time before continuing the loop
4. If the user's answer materially changes an already-approved design section, re-present the changed section briefly, update the spec, and continue the review loop
5. If loop exceeds 5 iterations, surface to human for guidance

**User Review Gate:**
After the spec review loop passes, ask the user to review the written spec before proceeding:

> "Spec written and committed to `<path>`. Please review it and let me know if you want to make any changes before we start writing out the implementation plan."

Wait for the user's response. If they request changes, make them and re-run the spec review loop. Only proceed once the user approves.

**Implementation:**

- Invoke the writing-plans skill to create a detailed implementation plan
- Do NOT invoke any other skill. writing-plans is the next step.

## Key Principles

- **One question at a time** - Don't overwhelm with multiple questions
- **Multiple choice preferred** - Easier to answer than open-ended when possible
- **YAGNI ruthlessly** - Remove unnecessary features from all designs
- **Explore alternatives** - Always propose 2-3 approaches before settling
- **Incremental validation** - Present design, get approval before moving on
- **Be flexible** - Go back and clarify when something doesn't make sense
- **Questions over momentum** - If something important is unclear, stop and ask. Do not trade correctness for flow.
- **Never assume** - If you discover an undiscussed question while writing the spec or fixing review feedback, including compatibility expectations, stop and ask the user. Do not fill gaps with assumptions.
