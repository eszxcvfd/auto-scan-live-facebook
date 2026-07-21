# Routing Map (ask-matt aligned)

The orchestrator routes work to agents. It does not route by vibes: it verifies a real skill exists, chooses one primary skill per job, and records why that skill fits.

Always prefer re-reading the project's `skills/engineering/ask-matt/SKILL.md` when present. This file is the fallback and quick index.

Buckets under project root:

- Promoted (routine dispatch): `skills/engineering/`, `skills/productivity/`
- Not routine: `misc/`, `personal/`, `in-progress/`, `deprecated/`

If `ask-matt` is missing, list `**/SKILL.md` under engineering and productivity; route from folder name plus frontmatter `description`.

## Job Modes

| Mode | Run where | Use when |
|------|-----------|----------|
| `AFK` | Herdr worker agent | The skill can make progress from concrete inputs without interviewing the user. |
| `HITL` | Orchestrator pane | The skill's core value is asking the user questions or steering a decision. |
| `ORCH_ONLY` | Orchestrator pane | The work is routing, synthesis, quality-gating, or presenting a plan/final result. |

Never spawn `ask-matt`; it is the orchestrator's map. Never spawn another user-invoked skill if its value is direct conversation with the user.

## Main flow — idea → ship

| Situation | Skill | Mode | Worker hint |
|-----------|--------|------|-------------|
| Sharpen idea in a codebase | `grill-with-docs` | HITL | `grill` |
| No codebase, pure plan grill | `grill-me` | HITL | `grill` |
| Design needs runnable answer | `prototype` | AFK | `proto` |
| Thread → published spec | `to-spec` | AFK if grilled | `spec` |
| Spec/plan → tracer tickets | `to-tickets` | AFK if spec exists | `tickets` |
| Build one ticket/spec | `implement` | AFK (tdd+review inside) | `impl` |
| Single behaviour test-first | `tdd` | AFK | `tdd` |
| Review diff vs fixed point | `code-review` | AFK | `review` |

Context hygiene: keep grill → to-spec → to-tickets in **one** orchestrator
thread when possible. Each `implement` = fresh worker + ticket/spec in INPUTS.

## On-ramps

| Situation | Skill | Mode |
|-----------|--------|------|
| Inbox bugs/requests | `triage` | HITL-heavy |
| Hard / flaky bug | `diagnosing-bugs` | AFK |
| Huge foggy multi-session effort | `wayfinder` | You chart; AFK `research` per research ticket |

## Codebase health / vocabulary

| Situation | Skill | Mode |
|-----------|--------|------|
| Deepening opportunities | `improve-codebase-architecture` | HITL pick |
| Deep-module shape | `codebase-design` | with design work |
| Domain terms / ADR | `domain-modeling` | often with grill |

## Crossing sessions / standalone

| Situation | Skill | Mode |
|-----------|--------|------|
| Compact for another session | `handoff` | you write |
| Primary-source investigation | `research` | **always** AFK |
| Merge/rebase conflicts | `resolving-merge-conflicts` | AFK |
| First-time repo config | `setup-matt-pocock-skills` | HITL once |
| “Which skill?” | `ask-matt` | **you only** — never spawn |

## Parallel Recipes

- **`code-review`**: one worker by default because the skill already parallelizes review axes. Split panes only if the user explicitly wants separate reviews.
- **`wayfinder` research tickets**: one `research` worker per independent decision ticket.
- **Independent implementation tickets**: one `implement` worker per ticket once blockers are accepted.
- **`research` plus planning**: run `research` AFK while the orchestrator keeps HITL planning in this pane.
- **Bug plus unrelated research**: `diagnosing-bugs` and `research` can run in parallel only if they do not touch the same files or depend on the same feedback loop.

## Mode Rules

**HITL** — user must answer in-band: grill*, triage questions, wayfinder HITL tickets, teach, setup, ask-matt.

**AFK** — safe background when inputs are complete: research, implement, tdd, code-review, diagnosing-bugs, prototype, resolving-merge-conflicts, to-spec, to-tickets.

**ORCH_ONLY** — always in this pane: building PLAN/NEXT PLAN, merging worker outputs, judging quality gates, deciding dependencies, closing panes, and final reporting.
