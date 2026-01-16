# Model Policy

Match model capability to task complexity.

## Model Assignment by Role

| Role Family | Model | Why |
|-------------|-------|-----|
| Shaping, Verification, Reporter, Infra | haiku | Mechanical tasks |
| Spec/Design, Implementation, Critic, Analytics | sonnet | Requires judgment |
| Wisdom | opus | Deep synthesis |
| Navigator | haiku | Fast, bounded decisions |

## The Rule

> Default to the cheapest model that works.
> Override only when necessary (in agent config or flow spec).

## Cost Reference

- Haiku: ~$0.25/M input, $1.25/M output
- Sonnet: ~$3/M input, $15/M output
- Opus: ~$15/M input, $75/M output

Mixed policy run (50 steps): ~$5-15 vs all-Opus: ~$50-100

> Config: `swarm/config/model_policy.json`
