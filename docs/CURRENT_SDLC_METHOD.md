# Current SDLC method

Issue: [#1463](https://github.com/EffortlessMetrics/flow-studio-swarm/issues/1463)

Status: current normative interpretation for Flow Studio documentation and
provider guidance. The existing YAML topology, runtime, generated UI and
historical runs have not all migrated to this model. Their observed behavior
must be reported separately.

## Outcome

The system should increase accepted useful software without making review,
qualification, integration cost or escaped defects rise in proportion to code
generation.

The normal route is:

```text
understand the real claim and consumer
-> challenge premise, plan and discriminating proof
-> implement and test in a warm candidate context
-> challenge correctness, test oracle/cost, simplicity, docs and product fit
-> return material findings to the same candidate writer
-> publish actual-source evidence and a current review disposition
-> explicitly request qualification for the selected candidate
-> execute mandatory plus justified risk-directed proof
-> make a separate current product/repository/integration judgment
-> perform the authorized protected expected-head merge
-> reconcile the actual landed result and remaining delivery work
```

The reasoning questions may recur or run concurrently. This is not a mandatory
fresh-agent conveyor. A candidate enters at the earliest missing or stale useful
judgment. One current writer mutates it; readers and reviewers do not need a
reservation.

## Authority

| Fact or effect | Native owner |
|---|---|
| Accepted product direction and bounded claim | Maintainer plus current issue/spec/decision |
| Source, candidate, PR, reviews, checks and merge state | Git and GitHub |
| Unpublished bytes, processes, caches and warm build state | Current worker environment |
| Review finding and disposition | Producing review surface plus accountable root |
| Independent proof execution and result | Selected qualification producer |
| Physical allocation, isolation and cleanup | Runtime/host controller |
| Privileged GitHub mutation | Narrow authorized publisher/integrator |
| Cross-session continuation and next useful action | Accountable root/coordinator derived from native owners |

`swarm/runs/<run-id>/` records local execution and retained evidence. It does
not override current GitHub facts, prove that a remote effect never happened,
or become a second liveness/transaction database.

## Questions and transitions are different

Question contracts direct investigation:

- Is this the actual user or production problem?
- Does an existing owner already solve it?
- What plausible wrong implementation would pass these tests?
- Did the test execute the actual production decision?
- Can the implementation or fixture be simpler and cheaper?
- Do docs, compatibility, configuration and installed behavior agree?
- Does the candidate still fit current product direction and repository state?

Transition contracts constrain effects:

- publication is not qualification;
- no current exact request means no expensive allocation;
- missing or invalid required evidence is not success;
- qualification success is not merge permission;
- merge permission is not release or deployment authority.

Flow Studio should display both without representing every question as a rigid
machine state or every transition as an agent opinion.

## Warm development and evidence

Keep useful repository, model, compiler and test state across implementation,
review and repair. Commit and publish coherent progress early enough for other
readers to inspect. In the target design, ordinary push, Draft and Ready changes
remain cheap.

A useful evidence record identifies:

- actual tested bytes/tree, including staged or dirty differences;
- relevant base/integration subject;
- command, toolchain, platform, features and configuration;
- selected and actually executed subjects;
- native outcome and capture completeness;
- proposition established and explicit non-claims;
- producer/custody and accessible original evidence;
- inputs that determine current applicability.

A digest binds bytes. It does not authenticate the producer, prove execution,
show that any tests ran, or establish that the oracle was meaningful. Historical
results remain factual while their applicability can change.

## Review

Review is cumulative challenge, not a vote count. Different models, tools or
identities add value only when they change the method, evidence, threat model,
platform, oracle or attention surface.

A prior clean review never suppresses later substantive review. A new material
finding can withdraw readiness without a new commit. A formatting-only commit
need not invalidate an architecture review. Refresh affected dimensions and
preserve the rest.

One writer receives accepted repairs. Reviewers inspect source and evidence;
source-only persistent reviewers must not execute candidate-controlled hooks,
builds, scripts, language servers or plugins.

## Explicit late qualification

Ready is a GitHub review/UI state, not the qualification request. A retained
label or request for H1 cannot authorize H2.

The request binds the selected repository/PR/head, current review and evidence,
selected proof plan, requester authority and stable operation identity. Duplicate
or uncertain requests read back the native operation before retry.

Every declared obligation receives one outcome:

```text
execute
reuse_verified
not_applicable_with_evidence
blocked_or_not_proven
```

Unknown impact widens proof or blocks. An available check catalogue is not an
instruction to run everything.

The normal complete active qualification targets 20 minutes or less, including
required setup, selected children, evidence finalization and trusted result
publication. Queue/request latency and shifted warm-session work are measured
separately. The target may not be met by hiding work or weakening proof.

## Final judgment and landing

After qualification, reacquire current findings, product fit, base and evidence
applicability. Passing proof can coexist with a decision not to merge.

The selected normal design has no routine auto-merge or PR merge queue. Use the
installed protected expected-head merge after the final judgment. Expected-head
checking does not atomically freeze the base; inspect material integration change
and run affected proof where necessary.

Read the merge state and actual landed commit/tree back from GitHub. Do not claim
that earlier qualification executed a different final squash composition.
Ordinary main health is separately admitted after both one hour and ten merges
from its accepted baseline. Incident, deep and release work retain their own
triggers.

Tagging, package publication, release creation, source promotion and production
deployment are separate operations with separate authority and evidence.

## Product and method completion

Keep four outcomes distinct:

1. product learning and accepted direction;
2. source/change delivery;
3. release and real installed delivery;
4. improvement of the operating method.

For method learning, retain the loaded method/harness version, information
available to the agent, action taken, evidence, failure and smallest effective
correction. A valid document, rendered graph or passing structural test does not
establish behavioral adoption.

## Migration rule

The existing Flow Studio YAML, generated topology, runtime and historical runs
remain evidence of earlier designs until their own migration is qualified. Do
not rewrite history or call a documentation update a runtime cutover.

When old and current instructions conflict, this document governs intended
method; live source/settings govern what the installed system actually does.
Record the discrepancy and route it to #1463 rather than pretending either side
does not exist.
