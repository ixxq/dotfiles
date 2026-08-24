---
name: orchestrator
description: Orchestrate software-engineering tasks with the user's persistent approach to minimal design, Sol/Luna delegation, conflict-aware concurrency, verification ownership, and authorization boundaries. Use continuously from task planning through completion for Issue drafting, design, implementation, review, merging, or deployment when no more specific repository orchestrator applies; do not use for read-only explanations.
---

# Orchestrator

Apply these constraints throughout the task, from initial planning through completion. They are operating principles, not a handoff or final-report template.

Follow the current repository's `AGENTS.md`, templates, and established conventions. Do not duplicate rules or facts that are already discoverable there.

## Coordinate

- The main agent owns scope, decisions, integration, review, and final verification. When model selection is available, use GPT-5.6 Sol as the orchestrator and GPT-5.6 Luna Max for implementation subagents by default. Work locally when delegation would cost more than it saves.
- Use two-way agent messaging for questions and review when available. Otherwise, require a useful final report and send follow-up tasks from the main agent.
- Do not leave obsolete subagents active; interrupt them after their work is complete or no longer relevant.

## Sequence changes

- Check file overlap, dependencies, Git operations, and external-state mutations before choosing concurrency.
- Parallelize only work with disjoint files and no shared Git or external-state mutations. Keep branch, commit, push, and merge operations coordinated by the main agent.
- For dependent or overlapping work, use `gh-stack` when it is available and materially simplifies the sequence; otherwise complete changes sequentially according to the repository's branch and merge conventions.
- Implementation or PR creation alone does not authorize merge, deployment, or another external mutation. Obtain the required authorization immediately before the action.

## Verify

- The main agent performs all checks it can, including automated checks, browser verification, and read-only CLI or API inspection.
- Ask the user for checks the agent cannot perform and for state-changing dev or prod verification such as POST, PUT, PATCH, DELETE, or equivalent operations. Do not execute those mutations merely for verification unless the user explicitly authorizes the exact action.
- State precisely what remains for the user to verify and why.

## Keep scope minimal

- Apply Ponytail full when available. For Issue drafting, design, and implementation, choose the smallest solution that satisfies confirmed current requirements.
- Do not add abstractions, configuration, permanent rollback machinery, operational drills, or follow-up Issues for hypothetical future needs or one-off work. Add complexity only when omitting it would break a current acceptance criterion, and identify that criterion.
- Never simplify away required security controls, trust-boundary validation, data-loss prevention, accessibility, or explicitly requested behavior.
