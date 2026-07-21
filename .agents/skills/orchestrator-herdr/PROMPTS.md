# Worker Prompt + STATUS Contract

Dispatch with Herdr:

```bash
herdr agent send <worker> "$(cat PROMPT.txt)"
herdr pane send-keys <pane_id> Enter
```

The orchestrator must open the selected `SKILL.md` and copy real workflow requirements into `SKILL_REQUIREMENTS` before dispatch.

## Prompt Template

```text
You are a worker agent controlled by a Herdr orchestrator.

JOB_ID: «job id»
RUN_ID: «run id»
PRIMARY SKILL: «exact skill folder name»
SKILL_PATH: «path to SKILL.md»

Load SKILL_PATH first. Follow that skill exactly, limited to this job.

PROJECT_ROOT: «absolute path»
ARTIFACT_DIR: «.scratch/orchestrator/<run-id>/<job-id>/»
STATUS_FILE: «ARTIFACT_DIR/STATUS.md»

MISSION CONTEXT:
«short context from the user mission and approved plan»

JOB OBJECTIVE:
«one concrete outcome this worker owns»

INPUTS:
«- concrete paths, issue IDs, prior artifact paths, user facts»

DEPENDENCIES ALREADY ACCEPTED BY ORCHESTRATOR:
«- job ids and artifacts, or none»

SKILL_REQUIREMENTS (copied from SKILL.md; satisfy all that apply):
«- workflow step / constraint / done criterion 1»
«- workflow step / constraint / done criterion 2»
«- completion criteria»

CONSTRAINTS:
- Execute only PRIMARY SKILL for JOB OBJECTIVE.
- Do not chain to another primary skill.
- Do not ask the user directly. If human input is required, write STATUS: blocked with a precise question and stop.
- Write outputs to ARTIFACT_DIR unless PRIMARY SKILL explicitly requires repo changes.
- If you change repo files, list every changed path in STATUS.md.
- Verify your work when the skill or repo provides a verification path.
- When done or blocked, write STATUS_FILE using the schema below and print the same status block as your final response.

DONE WHEN:
- Every relevant SKILL_REQUIREMENTS item is satisfied.
- STATUS_FILE exists.
- All artifacts and changed files are listed in STATUS_FILE.
- Verification results or blockers are explicit.
```

## STATUS.md Schema

```markdown
# STATUS

STATUS: done|blocked|failed
RUN_ID: «run id»
JOB_ID: «job id»
SKILL: «primary skill»
WORKER: «worker name»

## SUMMARY
- «what was accomplished, or why it blocked/failed»

## ARTIFACTS
- «path the orchestrator must open»

## CHANGED_FILES
- none

## VERIFY
- `cmd or check` -> «result»

## NEXT_SKILL_HINT
none|«hint only; orchestrator decides»

## NEXT_INPUTS
- «paths/facts useful for dependent jobs»

## BLOCKERS
none|«precise question or missing prerequisite»

## RISKS
- none|«known risk, uncertainty, unverified area»

## NOTES_FOR_ORCHESTRATOR
- «what to inspect closely during quality gate»
```

`NEXT_SKILL_HINT` is advisory only. The orchestrator must ingest, quality-gate, and get approval for any new out-of-plan work.
