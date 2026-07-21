#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
P=0; F=0
ok(){ echo "  PASS  $*"; P=$((P+1)); }
bad(){ echo "  FAIL  $*"; F=$((F+1)); }

for f in SKILL.md PROMPTS.md WORKFLOW.md ROUTING.md agents/openai.yaml; do
  test -f "$SKILL_DIR/$f" && ok "$f" || bad "miss $f"
done
grep -qi 'ingest' "$SKILL_DIR/SKILL.md" && ok "mandatory ingest" || bad "no ingest"
grep -qi 'quality.gate' "$SKILL_DIR/SKILL.md" && ok "quality gate" || bad "no qg"
grep -q 'ORCH:' "$SKILL_DIR/SKILL.md" && ok "ORCH decision" || bad "no ORCH"
grep -q 'SKILL_REQUIREMENTS' "$SKILL_DIR/SKILL.md" && ok "skill reqs in dispatch" || bad "no skill reqs"
grep -q 'SKILL_REQUIREMENTS' "$SKILL_DIR/PROMPTS.md" && ok "prompt skill reqs" || bad "prompt no reqs"
grep -q 'DAG\|parallel\|multiple' "$SKILL_DIR/SKILL.md" && ok "multi worker" || bad "no multi"
grep -q 'herdr agent send' "$SKILL_DIR/SKILL.md" && ok "send" || bad "no send"
grep -q 'Proceed? (y/n)' "$SKILL_DIR/SKILL.md" && ok "approve" || bad "no approve"
grep -q 'Close only panes you created' "$SKILL_DIR/SKILL.md" && ok "safe close" || bad "unsafe close rule"
grep -q 'Worker idle is only a signal to inspect' "$SKILL_DIR/SKILL.md" && ok "idle not success" || bad "weak idle rule"
grep -q 'Do not chain to another primary skill' "$SKILL_DIR/PROMPTS.md" && ok "one skill prompt" || bad "missing one skill prompt rule"
grep -q 'AFK.*Herdr worker agent' "$SKILL_DIR/ROUTING.md" && ok "routing modes" || bad "missing routing modes"

echo "RESULT: $P passed, $F failed"
[[ "$F" -eq 0 ]]
