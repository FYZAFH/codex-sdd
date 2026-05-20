---
name: ui-design-reference
description: "Only use when the user explicitly names `ui-design-reference` or asks to use the UI design reference skill during `writing-specs`; do not auto-use for generic UI work."
---

# UI Design Reference

Create a direct, presentable UI reference during the spec phase, then use that artifact to anchor the written spec and later plan. Inputs may be verbal descriptions, screenshots from other software, hand-drawn sketches, existing product screens, or any combination of those.

<HARD-GATE>
Use this skill only when all of these are true:
1. The user directly referenced `ui-design-reference` or explicitly asked to use the UI design reference skill. Generic UI, UX, frontend, or mockup requests do not count.
2. The work is in the `writing-specs` phase before final spec approval.
3. The requested work has a user-facing interface or interaction that benefits from a visual reference.

If any condition is false, do not use this skill. Continue the normal `writing-specs` workflow unchanged.
</HARD-GATE>

## Role Of The Artifact

- The artifact is a reference, not production code and not an implementation contract.
- It anchors visual hierarchy, layout intent, states, flows, content priority, and interaction direction.
- Later implementation may adapt component structure, CSS values, framework choices, accessibility mechanics, responsive behavior, and asset handling as long as the approved spec remains satisfied.
- Exact colors, spacing, type sizes, DOM structure, animation curves, and generated image details are binding only if the user explicitly approves them as requirements and the spec records them that way.

## Default Design Style Reference

Unless the user asks for a different visual direction, design references should lean toward a restrained industrial engineering-tool aesthetic. The target is an analytical interface for engineering, operations, diagnostics, measurements, simulation, waveform inspection, process history, or decision support. It should feel like robust desktop engineering software or instrument software, not like a marketing-oriented web product.

Reference tone:

- oscilloscope software and physical oscilloscopes
- trend analyzers, process historians, and PI ProcessBook-style tools
- MATLAB / Simulink, AspenTech, NI DIAdem, DewesoftX, and Beckhoff TwinCAT Scope
- Inductive Automation Ignition Perspective-style operational interfaces
- EDA waveform analyzers, NVH tools, engineering diagnostic consoles, and trading terminals
- Siemens-like system structure and console framework

Use this direction as a tone reference, not as a license to copy outdated, plastic, or vendor-specific visual details.

Visual principles:

- restrained, robust, low-saturation, tool-like, and clearly structured
- professional information density without making the screen feel piled up
- dense data surfaces paired with clear grouping, hierarchy, alignment, and scanning paths
- details available through clicking, right-clicking, expanding, inspecting, drilling down, panels, tabs, drawers, and contextual views instead of being spread across the full screen by default
- controls that feel operational and instrument-like: tables, traces, split panes, inspectors, channel lists, parameter grids, status strips, tree views, tabs, toolbars, cursors, annotations, and measurement readouts
- charts only when they directly serve the workflow, data inspection, comparison, diagnostics, or result explanation
- aesthetics that serve information, operations, and results

## Viewport And Scrolling Model

When the UI reference is HTML or otherwise web-rendered, design it as a fixed software view, not as a web page that keeps extending downward.

- Default to a single application viewport using `100vh` / `100dvh` and avoid document-level scrolling.
- Keep the main shell fixed: top toolbars, side navigation, status bars, inspectors, and primary work areas should remain in place.
- Put overflow inside the relevant component: tables, logs, traces, tree views, property inspectors, side panels, and result grids may scroll internally.
- Long tables should use an internal scroll region, sticky headers when useful, stable column widths, and row density appropriate for engineering tools.
- Prefer split panes, tabs, accordions, drawers, modal inspectors, drill-down views, and contextual panels over stacking all sections vertically.
- Use page-level scrolling only when the product surface is genuinely document-like, content-like, or intentionally page-based, and record that exception in the spec.

Avoid designing software screens as landing pages, admin dashboards, or long vertical web pages where every module is stacked below the previous one.

Avoid:

- cyberpunk styling, glowing borders, "big screen" dashboards, glassmorphism, gradient backgrounds, or decorative tech visuals
- Flutter / Material Design, generic SaaS dashboard, admin template, or marketing-site feel
- large rounded cards, huge KPIs, weak whitespace, oversized hero composition, or eager-to-please styling
- overuse of donut charts, gauges, decorative charts, or charts added only to make the screen look designed
- showing every detail at once when the workflow should reveal details through inspection or drill-down

## Direct Artifact Options

Default to the most direct artifact that gives the user something easy to review:

- **Self-contained HTML** for application screens, dashboards, forms, product pages, tools, and multi-state flows.
  - Save it under `docs/double-sdd/ui-designs/YYYY-MM-DD-<topic>.html`.
  - Keep it openable directly in a browser.
  - Use inline CSS and minimal inline JavaScript only when needed to show state, navigation, or interaction.
  - Do not add a backend, build system, framework scaffold, package install, or production app structure.
- **Text-to-image output** for concept visuals, brand mood, image-heavy first passes, or when the user asks for an image mockup.
  - Present the generated image directly when the environment supports it.
  - Save or reference the image path/URL in the spec if it is part of the approved design reference.
- **Static annotated screenshots or exported images** may be used when they are the fastest way to show an existing-screen adaptation.

If the requested design does not need a visual artifact, stop using this skill and continue the original spec workflow.

## Input Sources

- If the user provides an image, inspect it as design input before creating or revising the reference.
- Treat screenshots as inspiration and constraint discovery, not as a requirement to clone another product unless the user explicitly says so.
- Treat hand-drawn sketches as intent: preserve layout, information hierarchy, flows, and annotations, while improving polish and filling obvious UI details.
- If the image is ambiguous, ask only the smallest number of questions needed to resolve material design intent.
- If the user provides both an image and verbal instructions, follow the verbal instructions for priority and use the image to clarify visual structure.

## Workflow

1. Confirm the skill was explicitly requested and that `writing-specs` is active.
2. Inspect the relevant product context, existing UI conventions, design system, frontend framework, and nearby screens if they exist.
3. Inspect any provided image inputs and extract the intended layout, interaction model, states, content priority, and visual direction.
4. Ask only the UI questions needed to remove material ambiguity before creating the artifact.
5. Choose the fastest direct artifact format: self-contained HTML by default, text-to-image when that better matches the user's request.
6. Create the artifact as disposable reference material, not implementation source.
7. Present the artifact path or image to the user with a concise summary of what decisions it illustrates.
8. Iterate on concrete user feedback, revised descriptions, or updated image inputs until the user approves the design reference or chooses to proceed without one.
9. Return control to `writing-specs` for the written spec and review loop.

## Spec Integration

When the user approves a UI reference, the spec must include a `UI Design Reference` section with:

- artifact path(s) or URL(s)
- source inputs used, including user-provided image names/paths when available
- the screens, states, or flows represented
- the user-approved design decisions that should influence implementation
- which details are intentionally non-binding reference material
- any accessibility, responsive, content, or interaction requirements derived from the design

Do not paste large HTML, image prompts, or generated asset internals into the spec. Distill the decisions that matter.

## Plan And Implementation Handoff

When `writing-plans` consumes a spec with a `UI Design Reference` section:

- cite the artifact path(s) in the plan as supporting context
- derive implementation tasks from the spec's accepted requirements, not from hidden assumptions in the artifact
- tell implementer and reviewer subagents to inspect the artifact only for visual and interaction intent
- keep the spec and plan authoritative if the artifact and written requirements conflict

## Never

- Do not invoke this skill automatically just because the feature has UI.
- Do not use this skill during planning, implementation, review, or branch finishing.
- Do not let a mockup bypass unresolved product, compatibility, accessibility, or edge-case questions.
- Do not treat disposable HTML as production code.
- Do not make later work depend on a backend, build step, or local server just to view the reference.
