---
name: orchestrator
description: Orchestrate software-engineering tasks with the user's persistent approach to minimal design, conflict-aware concurrency, verification, frontend PR screenshots, and external-mutation boundaries. Use continuously from task planning through completion for Issue drafting, design, implementation, review, merging, or deployment when no more specific repository orchestrator applies; do not use for read-only explanations.
---

# Orchestrator

Apply these constraints throughout the task, from initial planning through completion. They are operating principles, not a handoff or final-report template.

Follow the current repository's `AGENTS.md`, templates, and established conventions. Do not duplicate rules or facts that are already discoverable there.

## Sequence changes

- Check file overlap, dependencies, Git operations, and external-state mutations before choosing concurrency.
- Parallelize only work with disjoint files and no shared Git or external-state mutations. Keep branch, commit, push, and merge operations sequential.
- For dependent or overlapping work, use `gh-stack` when it is available and materially simplifies the sequence; otherwise complete changes sequentially according to the repository's branch and merge conventions.

## Verify

- Ask the user for checks the agent cannot perform and for state-changing dev or prod verification such as POST, PUT, PATCH, DELETE, or equivalent operations. Do not execute those mutations merely for verification unless the user explicitly authorizes the exact action.
- State precisely what remains for the user to verify and why.

## Frontend PR screenshots

- Every PR that changes frontend code must include screenshots of the affected screens captured from the running application during browser verification, even when the expected appearance is unchanged.
- Place screenshot references such as `![Description of the verified screen](./screenshot.png)` in the PR template's existing screenshot section when preparing the PR body. If the template has no screenshot section, add one. Pass that body with `--body-file` and upload the referenced files with `gh pr create --attach ./screenshot.png` or `gh pr edit <number> --attach ./screenshot.png`; `gh` rewrites the references to uploaded asset URLs in place. Repeat `--attach` for multiple screenshots and label the verified screen or state clearly.
- Verify that the uploaded screenshots appear in the PR body's screenshot section. If capture or upload is blocked, report the blocker and do not mark the PR ready for review until the screenshots are attached.

## Keep scope minimal

- Apply Ponytail full when available. For Issue drafting, design, and implementation, choose the smallest solution that satisfies confirmed current requirements.
- Do not add abstractions, configuration, permanent rollback machinery, operational drills, or follow-up Issues for hypothetical future needs or one-off work. Add complexity only when omitting it would break a current acceptance criterion, and identify that criterion.
- Never simplify away required security controls, trust-boundary validation, data-loss prevention, accessibility, or explicitly requested behavior.
