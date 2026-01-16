# Flow Charters

Every routing decision must pass the charter test.

## The Rule

> "Does this help achieve the flow's objective?"
> If not in service of the goal, reject or escalate.

## Do

- Check actions against the flow's goal before executing
- Reject work that falls under `non_goals`
- Log scope drift in observations

## Don't

- Add features not in requirements
- Refactor unrelated code ("while I'm here" changes)
- Expand scope based on feedback

## Escalate

- If goal alignment is unclear, escalate for human decision

> Full flow charters: `swarm/flows/*.md` (each flow defines goal, exit_criteria, non_goals)
> Docs: docs/explanation/OPERATING_MODEL.md
