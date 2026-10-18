# Review — substantive challenge and joined repair

**Current responsibility:** Establish a current, evidence-backed review
disposition over the actual candidate and return valid findings to its writer.

Review is not limited to harvesting existing bot comments. Inspect the claim,
load-bearing source, production consumers, original proof and plausible wrong
behavior. Use different models, tools or people when they change the evidence,
oracle, threat model, platform or attention surface—not to fill a reviewer count.

A prior clean review never suppresses a later substantive pass. A new material
finding can withdraw readiness without a source change. A new SHA does not erase
unaffected review. Refresh the dimensions actually changed.

Cluster feedback for repair efficiency without losing original finding identity,
attribution or contradictory evidence. Verify a finding against current source;
reply with the repair or contrary evidence. Thread resolution and author prose are
not proof that the underlying defect is fixed.

One writer integrates accepted repairs. Readers do not need a reservation.
Source-only persistent review must not execute candidate-controlled code. Do not
hold an idle worker while a remote reviewer runs; retain its native operation and
wake condition, then do other useful work.

Review can be current while independent qualification is NotRun. Draft/Ready is
informational review state, not the qualification request. A current candidate
with material findings dispositioned proceeds to Gate for an explicit request.

## Generated demo topology

This block is generated from `swarm/config/flows/review.yaml` and still models
the earlier fixed worklist/Ready route. It remains visible for compatibility and
historical scenarios; it does not override the current responsibility above.

<!-- FLOW AUTOGEN START -->
## Steps Overview

| Step | Agent(s) | Purpose |
|------|----------|---------|
| run_prep | run-prep | Establish review directory |
| branch | repo-operator | Ensure run branch exists |
| pr_create | pr-creator | Create Draft PR if missing (for bot feedback) |
| harvest | pr-feedback-harvester | Pull all PR feedback |
| cluster | review-worklist-writer | Group feedback into work items |
| worklist_loop | Multiple | **Microloop**: resolve work items |
| finalize | pr-commenter | Update PR with resolution summary (informational) |
| cleanup | review-cleanup, build-cleanup | Write review_receipt.json |
| sanitize | secrets-sanitizer | Scan for secrets |
| commit | repo-operator | Commit and push |
| gh_update | gh-issue-manager, gh-reporter | Update GitHub |
<!-- FLOW AUTOGEN END -->
