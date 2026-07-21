## Agent skills

### Issue tracker

Issues live in GitHub Issues via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Uses the default canonical triage labels. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repo using root `CONTEXT.md` and `docs/adr/`. See `docs/agents/domain.md`.

### Product and design docs

Before designing or implementing user-facing behavior, read `PRODUCT.md` and `DESIGN.md`. They define the product register, target operator, product purpose, design principles, visual direction, component conventions, accessibility expectations, and interaction states.

### Specs and architecture decisions

Before changing feature behavior, read the relevant specification in `docs/specs/`, currently `docs/specs/live-scout.md`, and the relevant ADRs in `docs/adr/`. Treat accepted ADRs as constraints. If a proposed change conflicts with an ADR or the specification, surface the conflict before editing.

The current product decisions include public-only best-effort discovery, browser automation without automatic login, live verification before showing results, opening playback on Facebook, a local web application, and the FastAPI plus React/TypeScript stack with shadcn/ui conventions.

## Language

- Write all source code, comments, documentation, commit messages, and agent-generated project artifacts in English.
- Use Vietnamese only when communicating directly with the user.
