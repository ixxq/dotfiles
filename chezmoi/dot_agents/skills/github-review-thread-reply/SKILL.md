---
name: github-review-thread-reply
description: Reply to GitHub pull request review feedback one thread at a time. Use when a user asks to respond to PR review comments, especially Amazon Q `/q`, Codex `@codex`, or Claude `@claude` feedback, and the response must stay attached to each inline review thread instead of becoming a top-level PR comment.
---

# GitHub Review Thread Reply

Use this skill when responding to review feedback on a GitHub pull request.

## Procedure

1. Resolve the repository and PR, then fetch review threads with their inline comment IDs and `isResolved`/`isOutdated` state. Prefer the thread-aware `fetch_comments.py` workflow from `github:gh-address-comments` or the GitHub connector's thread API; if neither is available, query `pullRequest.reviewThreads` via `gh api graphql`.
2. Group only the unresolved, non-outdated actionable threads. Keep the response mapped to the exact file/line and comment that it addresses.
3. Reply to each thread's top-level inline comment individually. Use the GitHub review-comment reply endpoint or the GitHub connector's `github_reply_to_review_comment` (without a connector: `gh api repos/OWNER/REPO/pulls/PR/comments/COMMENT_ID/replies -f body=...`); do not use `gh pr comment` for the default response path.
4. Begin every reply with the reviewer prefix from the table below. Apply any other prefix the user explicitly requests. Use Japanese when the repository or user requests Japanese review communication.
5. Verify that every intended thread has a reply URL. Report the thread-to-reply mapping and leave unrelated, resolved, or outdated threads untouched.

| Reviewer | Login | Prefix |
| --- | --- | --- |
| Amazon Q | `amazon-q-developer[bot]` | `/q ` |
| ChatGPT Codex Connector | `chatgpt-codex-connector[bot]` | `@codex ` |
| Claude | `claude[bot]` | `@claude ` |

## Reply body format

- After the reviewer prefix, start directly with what changed. Do not use formulaic lead-ins such as `確認ありがとうございます`, `ご指摘ありがとうございます`, or `レビューありがとうございます`.
- Do not mention the commit in the prose: no commit hash (short or full) and no phrases such as `〜で対応しました`. The trailing URL is the only commit reference.
- Pass actual newline characters in the reply body. Never submit literal escaped sequences such as `\n`; when building a payload in JavaScript, use a multiline template literal or join lines with a single `"\n"` operation.
- When the thread is addressed by a commit, append one blank line followed by the bare PR commit URL with the full 40-character SHA as the final line: `https://github.com/OWNER/REPO/pull/PR_NUMBER/commits/FULL_SHA`. Do not add labels such as `コミット:` or `Commit:`, Markdown link syntax, or backticks around the URL.
- If no code changed, omit the commit URL. If multiple commits are relevant, append one bare URL per line at the end, with no labels.

OK:

```text
@codex 並び替え時に選択を解除する仕様に変更しました（`ConstructionSearchPage.handleSortChange`）。
同じ並び順を選び直した場合は解除しないよう、`SortSelector` 側でガードしています。

https://github.com/OWNER/REPO/pull/1758/commits/2de30876143fe25e573b8abe9e3d5f72f37bcaec
```

NG:

```text
@codex ご指摘ありがとうございます。2de308761 で対応しました。
```

## Guardrails

- Do not combine multiple inline comments into one top-level comment unless the user explicitly asks for a summary comment.
- Do not resolve threads, submit an approval/request-changes review, or modify code unless the user explicitly requests that action.
- If a review comment is informational, contradictory, or ambiguous, explain the assessment and ask before changing code.
- Preserve reviewer context: answer the specific concern first, then cite the relevant workflow/code behavior or validation evidence.
