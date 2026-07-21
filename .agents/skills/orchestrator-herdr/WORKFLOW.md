# Workflow

This is the tight loop for a real Herdr orchestrator. The orchestrator owns the mission; workers own one skill-bounded job each.

## 0. Preflight

1. Confirm `HERDR_ENV=1` and `herdr integration status` passes.
2. Identify project root and create `.scratch/orchestrator/<run-id>/`.
3. Read the mission and inventory project skills via `ask-matt` or on-disk `SKILL.md` files.

## 1. Plan As A DAG

1. Convert the mission into jobs with objective, primary skill, inputs, outputs, dependencies, and worker name.
2. Mark each job `AFK`, `HITL`, or `ORCH_ONLY`.
3. Present `PLAN` with the parallel set and approval boundary.
4. Wait for user `y` unless auto-run was explicitly granted.

## 2. Dispatch Ready Jobs

1. For each approved `AFK` job whose dependencies are satisfied, read that job's `SKILL.md`.
2. Copy its workflow, constraints, and done criteria into `SKILL_REQUIREMENTS`.
3. Write `PROMPT.txt` and create an artifact dir for the job.
4. Spawn/reuse a Herdr agent with `--no-focus`, send the prompt, then press Enter in that pane.
5. Dispatch independent jobs in parallel; sequence jobs with data/file dependencies.

### Worker wait timeout
Use a **60-minute** wait for every worker (`3,600,000,000` microseconds), not the shell/tool execution timeout of 180 seconds. The orchestrator must pass `--timeout 3600000000` to `herdr agent wait` and set the outer shell/tool timeout to at least 3,660 seconds so the wait is not cut short.

## 3. Ingest Every Stop

1. Wait for worker idle.
2. Read the worker transcript with Herdr.
3. Read `STATUS.md`.
4. Open every listed artifact and relevant changed repo file.
5. If `STATUS.md` is missing, request only that file once; still missing means failed.

## 4. Quality Gate

1. Compare transcript, status, artifacts, and file changes against copied skill requirements.
2. Accept only if the evidence proves the objective is met.
3. Mark the job `retry`, `rework`, `blocked`, or `failed` when evidence is incomplete or wrong.

## 5. Decide

1. Write an `ORCH` decision for the stopped job.
2. If accepted jobs unlock approved dependents, dispatch them.
3. If useful new work is outside the approval boundary, present `NEXT PLAN` and wait.
4. If all approved jobs are accepted, present `FINISH`, then close run-owned worker panes after approval.

## Failure Cases

- Treating idle as done.
- Spawning before user approval.
- Prompting a worker without copied `SKILL_REQUIREMENTS`.
- Letting one worker chain multiple primary skills.
- Inventing a skill or routing from memory when files exist.
- Advancing from `STATUS: done` without opening artifacts.
- Running dependent jobs with partial or failed upstream artifacts.
- Closing the orchestrator pane or any foreign pane.
