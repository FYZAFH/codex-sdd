---
name: roundtable-discussion
description: Facilitate real subagent roundtable meetings for uncertain futures, difficult decisions, product or architecture brainstorming, pre-mortems, and explicit disagreement during spec writing. Use during `writing-specs` before approach selection when multiple plausible paths need pressure-testing, stakeholder perspectives conflict, or potential product issues need to be surfaced. Use only when subagent use has already been approved for the current workflow; otherwise stop. Do not use for routine implementation tasks, settled decisions, or simulated roleplay.
---

# Roundtable Discussion

## Overview

Run a bounded but resumable roundtable meeting with real subagent participants, then synthesize their disagreement into decisions, risks, unresolved questions, and spec-writing inputs.

The main assistant is the host because it has the most complete project and conversation context. Participants contribute focused perspectives; the host owns framing, dispatch, synthesis, meeting state, continuation rounds, closure, and the handoff back into the active workflow.

## Hard Prerequisites

- This skill requires real subagent participants.
- Use this skill only when the user has already approved subagent use for the current workflow.
- If prior approval is absent or unclear, stop immediately and state that the roundtable skill cannot run until that prerequisite is satisfied.
- Do not ask for approval as part of the roundtable flow.
- Do not simulate a roundtable meeting.
- Do not impersonate participants from the main assistant.
- Do not continue with a degraded fallback if subagents are unavailable.

Use this exact stop message when the prerequisite is not met:

> Roundtable discussion requires pre-approved subagent use. I cannot run this skill until that prerequisite is satisfied.

## Host Responsibilities

The main assistant acts as host and must:

- Frame the decision from current context before dispatching participants.
- Select only the participant roles that are useful for the decision.
- Dispatch each participant as a real `roundtable-participant` subagent with the standard participant prompt plus one role preset.
- Provide each participant the same decision frame, options, constraints, and output contract.
- Gather participant outputs before synthesizing.
- Separate consensus, disagreement, assumptions, evidence gaps, and recommendations.
- Convert unresolved material questions into blockers for `writing-specs`.
- Avoid letting participant opinions override user requirements or project constraints.
- Maintain the roundtable as open after the first synthesis unless closure conditions are met.
- On user follow-up, objections, or new evidence, continue the same meeting with the relevant previous roles instead of starting from scratch.

## When To Run

Run a roundtable when the decision has at least one of:

- uncertain future costs or strategic consequences
- multiple viable approaches with meaningful trade-offs
- disagreement between user, agent, reviewers, product goals, or technical constraints
- unclear product risks, adoption risks, or edge cases
- a need for pre-mortem thinking before locking a spec
- high downside if the spec chooses the wrong direction

Do not run it for:

- ordinary clarification questions
- implementation details already settled by the approved spec
- code review findings that can be verified directly
- decisions where one local inspection or test can resolve the uncertainty

## Modes

Choose the smallest useful mode:

- **Decision**: compare known options and recommend a path.
- **Brainstorm**: surface product issues, missing workflows, risks, or opportunities.
- **Pre-mortem**: imagine the decision failed months later and identify causes.
- **Disagreement**: clarify opposing positions and identify the real crux.
- **Spec checkpoint**: pressure-test a proposed design before writing or approving a spec.

## Participant Roles

Default to 3-5 participants. Use 6-7 only for unusually consequential or ambiguous decisions. Pick roles based on the decision; do not include every role by habit.

- **Conservative Steward**: protects compatibility, reliability, migration safety, and maintenance cost.
- **Aggressive Strategist**: pushes speed, decisive bets, user learning, and upside.
- **YAGNI Minimalist**: argues for the smallest reversible useful move.
- **Optimization Architect**: looks for scale, performance, extensibility, and future-cost traps.
- **Customer Advocate**: focuses on user pain, adoption, UX, support burden, and trust.
- **Risk Skeptic**: hunts for failure modes, abuse, privacy, security, and testing gaps.
- **Operations Owner**: focuses on deployability, observability, rollback, incident response, and support.
- **Domain Expert**: applies project-specific, market-specific, or technical domain knowledge when available.
- **Contrarian**: challenges the emerging consensus and names hidden assumptions.

Participants should have distinct judgment styles, but they must stay practical. Do not turn personalities into theater.

## Prompt Presets

Every participant prompt must be composed from:

1. the standard participant prompt from `agents/participant-prompts.md`
2. exactly one role preset from `agents/participant-prompts.md`
3. the shared decision frame
4. one optional mode instruction from `agents/participant-prompts.md`

Read `agents/participant-prompts.md` before dispatching participants. The files under this skill's `agents/` directory are skill-local participant prompt resources, not globally registered Codex custom agent configs.

Do not invent ad hoc personality prompts when a preset fits. Use a custom participant only when no preset covers a necessary perspective; name the role and keep it as constrained as the bundled presets.

## Decision Frame

Before dispatching participants, write a concise frame for the meeting:

- **Question**: the decision or uncertainty being discussed.
- **Context**: relevant project facts, user goals, and constraints.
- **Options**: known paths, if any.
- **Time horizon**: immediate, near-term, or long-term.
- **Success criteria**: what good looks like.
- **Non-goals**: what the meeting should not expand into.
- **Known unknowns**: uncertainties participants should examine.

If the question is too broad to frame, ask one clarifying question before dispatching participants.

## Dispatch Protocol

Dispatch participants in parallel when possible using `agent_type: roundtable-participant`. Each participant gets the standard participant prompt, one role preset, the same decision frame, and the selected mode instruction.

Use a prompt shaped like:

```text
<standard participant prompt with selected role preset, decision frame, and mode instruction filled in>
```

If a participant blocks on missing context, the host may provide the missing facts once. Do not let the meeting become an open-ended subagent conversation.

## Meeting Lifecycle

A roundtable is a meeting state, not a single response. After the first synthesis, keep the meeting open in the host's context unless one of the closure conditions below is met.

Track the open meeting state:

- original decision frame
- participant roles used
- prior participant positions
- prior consensus, disagreement, crux, recommendation, and confidence
- unresolved questions and evidence gaps
- user follow-up, objections, corrections, or new constraints
- roles that should continue in the next round and roles that can be dropped

When the user responds with additional context, objections, disagreement, revised requirements, or asks the meeting to keep discussing:

1. Treat it as a continuation of the same roundtable unless the user clearly starts a different decision.
2. Identify which parts of the previous synthesis are challenged or newly relevant.
3. Reuse only the useful subset of previous participant roles, typically 2-4 roles.
4. Add a new role only when the user's follow-up introduces a materially new lens.
5. Provide continuing participants with the original decision frame, prior synthesis, their previous position when available, and the user's new input.
6. Ask participants to respond to the delta, not to repeat the entire first-round analysis.
7. Produce an updated synthesis that clearly distinguishes unchanged conclusions from revised conclusions.

If the subagent system supports continuing the same participant conversations, continue those conversations. If it only supports fresh dispatches, re-dispatch the same participant roles with the prior roundtable state included so the meeting remains logically continuous.

## Closure Protocol

Do not automatically close the meeting merely because one synthesis was delivered.

Close the roundtable only when:

- the user explicitly asks to close, end, finalize, proceed, write the spec, or stop discussing the roundtable
- the user accepts the recommendation and there are no material unresolved disagreements or blockers
- the host has just produced a synthesis where the relevant participants have no remaining material disagreement, the decision crux is resolved, and the next workflow step is clear

When closing, say that the roundtable is closed and summarize what will be carried into the active workflow.

If closure conditions are not met, end the synthesis with the meeting status as open and make clear what kind of follow-up would continue the same meeting.

## Synthesis Protocol

After participant outputs return, the host produces the roundtable result:

- **Decision frame**: restate the question.
- **Participants**: list roles used.
- **Consensus**: points of agreement.
- **Disagreement**: real conflicts, not stylistic differences.
- **Decision crux**: the assumption or evidence most likely to change the recommendation.
- **Options**: strongest viable paths and trade-offs.
- **Risks and mitigations**: practical actions, not generic warnings.
- **Unresolved questions**: material questions that block spec writing or approach selection.
- **Recommendation**: one recommended path, confidence level, and why.
- **Spec impact**: requirements, constraints, non-goals, tests, or compatibility notes to carry into `writing-specs`.
- **Meeting status**: `open` or `closed`, with the reason.

If there is no honest consensus, preserve dissent instead of forcing agreement.

## Integration With Writing Specs

During `writing-specs`, use this skill before approach selection when uncertainty or disagreement is material.

After the roundtable:

- Treat unresolved material product questions as blockers under `writing-specs`.
- Ask the user about blockers before writing or approving a spec.
- Convert accepted recommendations into the design proposal.
- Convert risks into explicit edge cases, constraints, testing themes, or compatibility notes.
- Do not let the roundtable expand the scope beyond the user's requested outcome without user approval.

## Quality Bar

A good roundtable result is specific enough to change the design, expose a real blocker, or increase confidence in the selected path.

A bad roundtable result is generic, performative, unanimous without pressure, or disconnected from the current repo and user goals.
