---
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git push:*), Bash(git branch:*), Bash(gh pr:*), Bash(gh repo:*)
argument-hint: [additional context]
description: Create a GitHub pull request
---

## Context

- Current repository state: !`git status -sb`
- Current branch details: !`git branch -vv`
- Default branch: !`gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'`
- PR template (if exists): !`gh repo view --json pullRequestTemplates --jq '.pullRequestTemplates[0].body' 2>/dev/null || echo ""`
- Recent commits (for language detection): !`git log -n 10 --pretty=format:"%s"`

## Your Task

Based on the above context:

1. Check changes and commits to be included:
   - Use the **Default branch** value from context above (obtained from `gh repo view`)
   - Execute `git diff origin/<default_branch>..HEAD --stat` to see the changes that will be included
   - Execute `git log origin/<default_branch>..HEAD --oneline` to see the commits that will be included
   - Review these changes and commits to confirm PR contents

2. Verify prerequisites:
   - Review the **Current repository state** and **Current branch details** from context above
   - Ensure all changes are committed (no unstaged/uncommitted changes)
   - If uncommitted changes exist, stop and ask the user, unless they explicitly said a draft/WIP PR with local changes left out is acceptable
   - Confirm the branch is appropriate for creating a PR
   - If issues are found, notify the user before proceeding

3. Push the branch to remote:
   - Execute `git push -u origin HEAD` to ensure the branch is available on GitHub
   - This is safe to run even if already pushed

4. Determine the PR language:
   - Based on the **Recent commits** from context above
   - If the majority are in English, write in English
   - If the majority are in Japanese, write in Japanese
   - If `$ARGUMENTS` includes a language instruction, follow that instead

5. Create the pull request:
   - Review the **PR template** from context above (if exists)
   - Use the repository's PR template if one was found
   - Otherwise, use the **Default PR Template** section below
   - Execute `gh pr create` with appropriate title and body
   - Refer to the **Pull Request Guidelines** section when composing

6. Finalize:
   - Execute `gh pr view --web` to open the PR in the browser
   - Provide the PR URL and summary to the user

## Default PR Template

Use this template when no repository-specific template is found:

```markdown
<!-- Instructions for GitHub Copilot Code Review: Please provide your comments and review this pull request in Japanese. -->

## Issue

<!--
  If there's a related issue: fixes #123
  If no related issue: N/A - Brief description of the purpose
  Examples:
  - fixes #42
  - N/A - Add TypeScript configuration
  - N/A - Update dependencies
-->

N/A - [brief description of the purpose]

## Changes

<!--
  List the main changes made in this PR using bullet points
  Examples:
  - Add user authentication feature
  - Fix memory leak in data processing
  - Update React from v17 to v18
-->

- [Describe the main changes made]

## Verification

<!--
  Do NOT list items already verified by CI (tests, lint, type checks, etc.).
  List manual verification steps that reviewers should actually confirm.
  These should serve as acceptance criteria — if all are met, the PR can be approved.
-->

- [ ] [Describe the expected behavior or manual verification step]

## Additional Notes

<!-- Any additional context, implementation details, or notes for reviewers -->
```

## Pull Request Guidelines

- **Title format**:
  - Follow the same convention as commit messages if applicable
  - Be descriptive but concise (max ~72 characters)
  - **Scope language matches the title language**: for Japanese PRs the scope may be written in Japanese; for English PRs keep the scope in English
  - Example (English): `feat(auth): Add user authentication with OAuth2`
  - Example (Japanese): `feat(認証): OAuth2 ログイン機能を追加`

- **Readability**:
  - Write Changes and Verification (or equivalents like `変更内容`, `確認したこと`) at a level a PM can read and understand
  - Keep them short and high-signal; do not overload readers with excessive detail
  - Keep bullet lists compact — do not insert blank lines between bullet points

- **Issue section**:
  - Use `fixes #<number>` to automatically close related issues
  - Use `N/A - <description>` if no related issue exists
  - Provide brief context when there's no issue number

- **Changes section**:
  - List all significant changes in bullet points
  - Group related changes together
  - Be specific about what was modified, added, or removed
  - Follow the examples in the template comments

- **Verification section**:
  - Do not list items already verified by CI (tests, lint, type checks, etc.)
  - List manual verification steps that reviewers should actually confirm
  - All items should serve as acceptance criteria — if met, the PR can be approved
  - Keep checkboxes unchecked (`- [ ]`)

- **Additional Notes section**:
  - Include implementation details for complex changes
  - Add context that helps reviewers understand the approach
  - Mention any trade-offs or alternatives considered

- **Verification in repository templates**:
  - If the repository's PR template has a verification/confirmation section (e.g., "確認したこと", "Verification", "Checklist"), apply the same rules as the Verification section above
  - Do not list CI-verified items — only include manual verification steps reviewers should confirm

- **Language rule**:
  - Use the same language as the majority of recent commits
  - If `$ARGUMENTS` includes a language instruction, follow that instead

- **Arguments rule**:
  - Treat `$ARGUMENTS` as additional context or instruction for the PRtitle/description

## HEREDOC Handling for PR Body

When composing the PR body with `gh pr create --body "$(cat <<...EOF ... EOF)"`, the HEREDOC quoting style affects how backticks are interpreted:

- **Single-quoted HEREDOC (`<<'EOF'`)**: No shell expansion happens, so write raw backticks directly (both inline `` ` `` and fenced ```` ``` ````)
- **Double-quoted or unquoted HEREDOC (`<<"EOF"` / `<<EOF`)**: Bash may try to interpret backticks as command substitution. Avoid inline single backticks — use triple-backtick fenced code blocks (```` ``` ````) instead

**Rationale**: In double-quoted/unquoted HEREDOC, backticks sometimes get auto-escaped as `` \` ``, which breaks Markdown rendering on GitHub (the code block fails to display properly).

**Recommendation**: Prefer `<<'EOF'` whenever the PR body contains backticks, code identifiers, or code blocks — it is the safest default.

## Important Notes

- Always ensure all changes are committed before creating a PR
- Do not force push unless absolutely necessary
- If the PR template exists in the repository, always use it over the default
- Check CI/CD status after creating the PR
- Do not merge the PR unless explicitly instructed
- The GitHub Copilot instruction comment helps ensure reviews are provided in the appropriate language
