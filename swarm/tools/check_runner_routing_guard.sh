#!/usr/bin/env bash
set -euo pipefail

workflow_dir="${1:-.github/workflows}"
bad=0

if [[ ! -d "$workflow_dir" ]]; then
  echo "Workflow directory not found: $workflow_dir" >&2
  exit 2
fi

echo "Checking GitHub Actions runner routing in $workflow_dir..."

if rg -n --glob '*.yml' --glob '*.yaml' 'runs-on:[[:space:]]*\[[^]]*self-hosted[^]]*linux[^]]*x64[^]]*\]' "$workflow_dir"; then
  echo "Bare inline self-hosted/linux/x64 runs-on is forbidden." >&2
  bad=1
fi

if rg -n --glob '*.yml' --glob '*.yaml' 'repos/[^[:space:]"'"'"']+/[^[:space:]"'"'"']+/actions/runners' "$workflow_dir"; then
  echo "Repository runner discovery is forbidden; use orgs/EffortlessMetrics/actions/runners?per_page=100." >&2
  bad=1
fi

while IFS=: read -r file line _; do
  window="$(sed -n "${line},$((line+16))p" "$file")"

  if printf '%s\n' "$window" | rg -q '^[[:space:]]*-[[:space:]]*linux[[:space:]]*$' &&
     printf '%s\n' "$window" | rg -q '^[[:space:]]*-[[:space:]]*x64[[:space:]]*$' &&
     ! printf '%s\n' "$window" | rg -q 'group:[[:space:]]*em-ci-' &&
     ! printf '%s\n' "$window" | rg -q '^[[:space:]]*-[[:space:]]*(em-ci|ci-nano|policy-nano|workflow-nano|rust-tiny|rust-medium|rust-large|rust-16gb|cx23|cx33|cx43|cx53|cpx42)[[:space:]]*$'; then
    echo "$file:$line: bare self-hosted block lacks group/capacity labels" >&2
    bad=1
  fi
done < <(rg -n --glob '*.yml' --glob '*.yaml' '^[[:space:]]*-[[:space:]]*self-hosted[[:space:]]*$' "$workflow_dir" || true)

if [[ "$bad" -eq 0 ]]; then
  echo "✓ Runner routing guard passed"
fi

exit "$bad"
