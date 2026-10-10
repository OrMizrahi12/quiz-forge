#!/bin/bash
# Reviews every pending lesson file this branch adds or changes, with Claude Code in headless mode on Sonnet 5.5
# (in rehearsal Haiku 4.5 failed a sound question again and again). The checklist Skill is allowed, subagents are not.
# One Markdown row per file, printed and added to the job summary. Exit 1 if any review fails or errors.
set -u
BASE=${BASE_REF:-origin/main}
OUT=${GITHUB_STEP_SUMMARY:-/dev/null}
SCHEMA=$(cat reviewer/verdict.schema.json)
status=0
printf '| File | Verdict | Reasons | Cost |\n|---|---|---|---|\n' | tee -a "$OUT"
for f in $(git diff --name-only --diff-filter=AM "$BASE"...HEAD -- 'bank/pending/*.json'); do
  result=$(claude -p "Review $f with the quiz-forge-tools write-exam-item checklist. Flag only problems that break a rule or the checklist." \
    --plugin-dir plugin --model claude-sonnet-5-5 --permission-mode dontAsk --allowedTools "Read,Glob,Grep,Skill" \
    --disallowedTools Agent --max-turns 20 --max-budget-usd 0.40 --no-session-persistence \
    --output-format json --json-schema "$SCHEMA" < /dev/null)
  verdict=$(jq -r '.structured_output.verdict // "error"' <<< "$result")
  reasons=$(jq -r '(.structured_output.reasons // [.result // .subtype // "no result"]) | join("; ")' <<< "$result")
  cost=$(jq -r '.total_cost_usd // 0' <<< "$result")
  printf '| %s | %s | %s | $%.4f |\n' "$f" "$verdict" "${reasons//|//}" "$cost" | tee -a "$OUT"
  [ "$verdict" = pass ] || status=1
done
exit $status
