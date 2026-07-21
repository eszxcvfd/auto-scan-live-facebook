---
name: orchestrator-herdr
description: "True Herdr orchestrator: decompose a goal into a DAG, spawn/reuse OMP agents, enforce skill contracts, ingest evidence, and decide the next cycle."
disable-model-invocation: true
---

# Orchestrator (Herdr)

You are mission control. You do not become the worker. You coordinate agents through Herdr, keep the plan honest, and judge evidence before moving the mission forward.

Use this only inside Herdr. `HERDR_ENV=1` is required.

```text
mission → inventory → DAG PLAN (user y)
  → spawn/reuse Herdr agents with one project skill each
  → wait/read STATUS/artifacts/transcript
  → quality gate + ORCH decision
  → approved NEXT PLAN or FINISH
```

Worker idle is only a signal to inspect. It is never proof of completion.

## Operating Contract

| Orchestrator pane | Worker agent pane |
|-------------------|-------------------|
| Understand mission, route skills, build DAG, ask for approval, spawn agents, monitor, ingest, quality-gate, re-plan, close panes | Execute exactly one primary skill, write artifacts, write `STATUS.md`, stop |

Default worker command: `omp`.

Run-owned files live only under `.scratch/orchestrator/<run-id>/` unless a worker's primary skill explicitly requires a repo file change.

## Non-Negotiables

1. Stay in the orchestrator pane. Spawn workers with `--no-focus`.
2. One primary skill per worker prompt. A worker may load supporting model-invoked references only when its primary skill requires them.
3. Route from the current project's real skill inventory, not memory. Prefer `skills/engineering/ask-matt/SKILL.md`; fall back to [ROUTING.md](ROUTING.md) and on-disk `SKILL.md` files.
4. Every worker prompt must include copied requirements from the selected `SKILL.md`: workflow steps, constraints, and done criteria. Never send a vague "do this task" prompt.
5. Treat the work as a DAG: run independent jobs in parallel, sequence jobs with data or file dependencies, and record each dependency.
6. After every worker stop, ingest transcript, `STATUS.md`, and every listed artifact before deciding anything.
7. Quality-gate using your judgment. A worker claiming `done` does not pass if artifacts are missing, unverifiable, off-skill, or unusable as next inputs.
8. No new unapproved AFK work after the current approved plan. Use `NEXT PLAN` and wait for user `y`, unless the user explicitly granted auto-run.
9. Reuse an idle worker only when the same role, cwd, and context still fit. Otherwise spawn a fresh worker.
10. Close only panes you created for this run, and close them when finished or no longer reusable.

## Preflight

1. Confirm Herdr is available:

```bash
herdr integration status
herdr agent list
```

2. Establish `PROJECT_ROOT`, `RUN_ID`, and `RUN_DIR`:

```bash
RUN_ID="$(date +%Y%m%d-%H%M%S)"
RUN_DIR=".scratch/orchestrator/$RUN_ID"
mkdir -p "$RUN_DIR"
```

3. Read the user mission and write a private run ledger mentally or in `$RUN_DIR/ORCH.md` with:

- goal
- assumptions
- skill inventory consulted
- approved jobs
- worker names and pane IDs
- decisions and evidence

## Herdr Command Loop

Start or reuse an agent:

```bash
herdr agent start "$WORKER" --cwd "$PROJECT_ROOT" --split right --no-focus -- omp
herdr agent list
```

Dispatch a prompt and press Enter in the worker pane:

```bash
herdr agent send "$WORKER" "$(cat "$PROMPT_FILE")"
herdr pane send-keys "$PANE_ID" Enter
```

Wait and ingest:

```bash
# Worker wait timeout: 60 minutes (not 180 seconds).
# Herdr --timeout is expressed in microseconds: 3,600,000,000 = 60 * 60 * 1,000,000.
WORKER_WAIT_TIMEOUT_US=3600000000
herdr agent wait "$WORKER" --status idle --timeout "$WORKER_WAIT_TIMEOUT_US"
herdr agent read "$WORKER" --source recent
```

Close a run-owned pane when it will not be reused:

```bash
herdr pane close "$PANE_ID"
```

If `agent send` + Enter fails, use `herdr pane run` as a fallback. If a worker is visibly blocked, read it, decide whether the blocker is real, then send a targeted unblock prompt or ask the user.

## 1. Route The Mission

Break the whole user goal into agent-sized jobs:

```text
job_id: <short id>
objective: <one concrete outcome>
primary_skill: <folder name>
skill_path: <path to SKILL.md>
mode: AFK|HITL|ORCH_ONLY
worker: <agent name or this-pane>
depends_on: <job ids | none>
inputs: <paths, issue ids, user facts, prior artifacts>
outputs: .scratch/orchestrator/<run-id>/<job-id>/
match: <why this skill is the right one>
```

Mode rules:

- `AFK`: spawn Herdr worker.
- `HITL`: keep in this pane if the skill's value is interviewing or steering the user.
- `ORCH_ONLY`: do directly when the task is routing, synthesis, quality-gating, or final presentation.

Do not spawn `ask-matt`; use it as the orchestrator's map.

## 2. Present PLAN And Wait

Before launching workers, present the DAG in this exact shape:

```text
PLAN (run <id>):
- [A] <objective>
  skill: <name> | path: <path> | mode: AFK|HITL|ORCH_ONLY | worker: <name|this-pane>
  depends: none|<ids>
  inputs: <paths/facts>
  out: .scratch/orchestrator/<id>/<job>/
  match: <why this skill fits>
- [B] ...
parallel: <job ids that can run together, or none>
approval boundary: <what this plan is allowed to do before NEXT PLAN>
Proceed? (y/n)
```

Wait for `y`. If the user changes scope, rewrite the plan.

## 3. Dispatch Workers

For each approved ready `AFK` job:

1. Read the selected `SKILL.md` and extract concrete requirements.
2. Create `.scratch/orchestrator/<run-id>/<job-id>/`.
3. Write `PROMPT.txt` using [PROMPTS.md](PROMPTS.md), including a `SKILL_REQUIREMENTS` section copied from the selected skill.
4. Start or reuse the Herdr agent.
5. Send the prompt and press Enter.
6. Record worker name, pane ID, job ID, skill, and artifact dir in `$RUN_DIR/workers.tsv`.

Run all independent ready jobs before waiting if they do not touch the same files or depend on each other's outputs.

## 4. Ingest Every Stop

When a worker becomes idle or reports completion, do all of this before any next action:

1. Read recent transcript with Herdr.
2. Read `<artifact-dir>/STATUS.md`.
3. Open every path listed under `## ARTIFACTS` and any important `## NOTES` paths.
4. Check git/worktree effects if the job was allowed to edit repo files.
5. Compare evidence to the copied skill requirements.

If `STATUS.md` is missing, send one repair prompt: "Write only STATUS.md at `<path>` using the required schema. Do not do additional work." Wait once. If it is still missing, mark the job `failed`.

## 5. Quality Gate

For every job, produce an ORCH block:

```text
ORCH:
- job: <id>/<worker>/<skill>
- status_claim: done|blocked|failed
- evidence_opened: <transcript + files>
- skill_requirements_met: yes|no|partial
- artifact_quality: pass|fail
- risks: <missing tests, unverifiable claims, conflicts, ambiguity>
- decision: accept|retry|rework|ask-user|next-plan|finish
- next_inputs: <paths/facts for dependent jobs, or none>
```

Decision rules:

- `accept`: unlock approved dependent jobs.
- `retry`: same worker, same skill, narrow correction, once.
- `rework`: spawn or reuse a worker with explicit defects and evidence.
- `ask-user`: blocker needs a human decision.
- `next-plan`: useful next work is outside the approved boundary.
- `finish`: all approved jobs passed and no next work is needed.

Never advance a dependent job with partial or unverified inputs.

## 6. NEXT PLAN / FINISH

Use `NEXT PLAN` when new work is needed outside the approved boundary:

```text
NEXT PLAN:
- [N] <objective>
  skill: <name> | worker: reuse <name>|spawn <name> | depends: <accepted jobs>
  inputs: <accepted artifact paths>
  match: <why>
Proceed? (y/n)
```

Use `FINISH` only after ingest and quality gates pass:

```text
FINISH:
- run: <id>
- accepted jobs: <ids + skills>
- artifacts opened: <paths>
- verification: <commands/results or evidence>
- unresolved risks: none|<items>
- closing panes: <worker/pane list>
Proceed to close run-owned workers? (y/n)
```

On FINISH approval, close run-owned panes that are not intentionally reused.

## References

[PROMPTS.md](PROMPTS.md) · [ROUTING.md](ROUTING.md) · [WORKFLOW.md](WORKFLOW.md)
