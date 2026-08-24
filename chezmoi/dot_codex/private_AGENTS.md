## Orchestration

- For Issue drafting, design, implementation, review, merging, or deployment, use `$orchestrator` throughout the task unless a more specific repository orchestrator applies.

## Tool use

- In Code Mode, within each bounded stage, run independent, functions.exec-available tool calls concurrently in one functions.exec call. Use `await Promise.allSettled([...])` when partial results are useful, and inspect every result; use `await Promise.all([...])` only when any failure should abort the batch. Keep dependencies, waits/resumes, approvals, conflicting or interdependent mutations, and adaptive investigations sequential.
- Use `request_user_input` in Default Mode when available for consequential, bounded choices that affect the next action or result. Do not use it for routine confirmations, informational questions, or genuinely open-ended clarification. If unavailable, ask normally.
- When using `request_user_input`, put the recommended choice first and suffix its label with `(Recommended)`. Provide concrete choices and ensure the final choice allows free-form input. The tool supplies this option automatically; do not add an `Other` option manually.

## Code quality

- Avoid `any` and minimize type assertions with `as`.
- Prefer non-destructive operations for arrays and objects.
- Prefer `const` over `let` unless reassignment is required.
- Avoid speculative abstractions, configuration options, or generalization beyond what the current task requires. Prefer the simplest solution that satisfies the stated requirement over one that anticipates hypothetical future needs.
- Fix the root cause, not the symptom. Avoid workarounds such as suppressing errors, catching and ignoring exceptions, or hardcoding special cases to make a failure disappear without resolving the underlying issue.

## Verification

- Before completing a task, inspect `package.json`, find and run the repository's typecheck and lint commands, and resolve all reported type, lint, and diagnostic errors.
- If both `lint` and `lint-types` exist, run only `lint-types`.

## Pull requests

- Before creating a pull request, check for and follow any repository PR template.

@/Users/t1190078/.codex/RTK.md
