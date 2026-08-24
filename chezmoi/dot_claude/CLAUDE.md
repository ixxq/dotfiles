- When specifications are ambiguous or information is insufficient and requires user judgment, use the `AskUserQuestion Tool`.
- Always resolve any type errors and linting errors displayed in the console.
- Avoid using `any`.
- Minimize the use of type casting with `as`.
- Prefer non-destructive operations over destructive ones when working with arrays and objects.
- Use `const` instead of `let` as a general rule, since `let` can lead to unnecessary reassignment.
- Check package.json, find and run commands for linting and type error detection, and ensure there are no errors.
  - In many cases, type detection is `typecheck`, and linting is `lint` or `lint-types`.
  - If both `lint` and `lint-types` exist, please run only `lint-types`.
- Never consider a task complete until all diagnostic errors are resolved.
- When creating a pull request, please check if there is a PR template in the repository and follow it if available.
- Use `rg` (ripgrep) instead of `grep` for text search. `rg` is faster, honors `.gitignore` by default, and is already permitted without prompts. Reserve `grep` only for piping short command output (e.g. `ps aux | grep foo`) where `rg` would be awkward.
- Prefer the built-in `LSP` tool for symbol-level work: jumping to a definition, finding references, inspecting types/signatures via hover, or listing symbols in a file or workspace. Use it instead of `rg`/`find` whenever the target is a named symbol (function, class, variable, type), because LSP returns semantic results rather than text matches and is dramatically faster on large codebases.
  - Fall back to `rg`/`find` only for non-symbol text: comments, markdown, log strings, config values, or when LSP cannot resolve the language.
  - If `LSP` is not loaded yet, load it via `ToolSearch` with `select:LSP` before first use.
- After editing code, check LSP diagnostics (e.g. `mcp__ide__getDiagnostics` or the `LSP` tool's diagnostics operation) to surface type/lint errors immediately, rather than waiting for a separate `typecheck`/`lint` run. Still run the project's `typecheck`/`lint` commands before declaring a task complete.

@RTK.md
