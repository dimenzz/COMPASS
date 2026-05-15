# grill-me integration research

## Upstream behavior

Source: https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md

The upstream skill is a compact planning pressure-test. It tells the agent to interrogate a plan or design until shared understanding is reached, ask questions individually, recommend an answer with each question, and inspect the codebase when the answer can be derived locally.

## Local Trellis fit

The behavior maps directly to Phase 1.1 Requirement exploration:

- Phase 1 happens before implementation.
- `trellis-brainstorm` already owns task PRD creation and iteration.
- The existing brainstorm skill already says to ask one question at a time, research before asking, and persist decisions to `prd.md`.
- Adding a separate `grill-me` skill would duplicate the planning loop and risk bypassing Trellis persistence.

## Recommended integration

Integrate `grill-me` as a named behavior of `trellis-brainstorm`:

- Update `.trellis/workflow.md` planning breadcrumbs and Phase 1.1 text.
- Add a skill-routing row for "grill me" / plan stress-test requests.
- Update local `trellis-brainstorm` skill descriptions across existing platform copies.

## Non-goals

- Do not install the upstream skill as a separate project skill.
- Do not modify upstream Trellis source.
- Do not change Phase 2 implementation or Phase 3 checking semantics.
