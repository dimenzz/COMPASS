# Integrate grill-me into Trellis flow

## Goal

Make Matt Pocock's `grill-me` planning behavior a first-class part of this local Trellis workflow, placed where it naturally belongs: Phase 1 requirement exploration before implementation starts.

## Requirements

- Treat `grill-me` as a Phase 1 planning behavior, not a separate implementation or check phase.
- Route user requests such as "grill me" or "stress-test this plan/design" to `trellis-brainstorm`.
- Preserve Trellis persistence: questions, decisions, and acceptance criteria continue to land in task `prd.md`.
- Keep platform skill descriptions aligned for Codex shared skills, Claude, and OpenCode.
- Avoid introducing a second standalone skill that duplicates the existing `trellis-brainstorm` loop.

## Acceptance Criteria

- [x] `.trellis/workflow.md` explicitly documents grill-me behavior under Phase 1.1.
- [x] The workflow skill routing tables route plan/design grilling requests to `trellis-brainstorm`.
- [x] Local `trellis-brainstorm` skill descriptions mention grill-me / stress-test triggering.
- [x] Equivalent platform copies stay aligned where this project has local skill copies.
- [x] Verification confirms the edited workflow text can be parsed by the existing context script.

## Definition of Done

- Relevant Trellis workflow and skill files are updated.
- Research/source notes are persisted under this task.
- Basic validation commands pass.
- No unrelated local changes are reverted.

## Technical Approach

Use the existing `trellis-brainstorm` skill as the integration point because it already owns requirement exploration, one-question-at-a-time interviewing, research-first behavior, and PRD updates. Update `.trellis/workflow.md` so the behavior is visible in the canonical phase guide and route tables, then align the local platform skill metadata.

## Decision (ADR-lite)

**Context**: `grill-me` is a planning pressure-test skill. Trellis already has a Phase 1 planning loop and a PRD persistence model.

**Decision**: Fold `grill-me` into Phase 1.1 via `trellis-brainstorm` rather than adding a separate skill or phase.

**Consequences**: Users can ask to be grilled and still get Trellis task/PRD discipline. The flow remains simple, but `trellis-brainstorm` now carries both requirements-discovery and plan stress-test trigger language.

## Out of Scope

- Installing third-party skills globally.
- Changing upstream Trellis templates or npm package code.
- Adding a new Trellis phase.
- Refactoring task lifecycle scripts.

## Research References

- [`research/grill-me-integration.md`](research/grill-me-integration.md) - summary of upstream behavior and local integration choice.

## Technical Notes

- Upstream source reviewed: https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md
- Local Trellis customization guidance read from `trellis-meta`.
- Existing `trellis-brainstorm` already contained the core interview/research-first behavior, so the change is primarily routing and documentation alignment.
