---
name: github-review-thread-reply
description: Reply to GitHub pull request review feedback one thread at a time. Use when a user asks to respond to PR review comments, especially Amazon Q `/q` or Codex `@codex` feedback, and the response must stay attached to each inline review thread instead of becoming a top-level PR comment.
---

# GitHub Review Thread Reply

Use this skill when responding to review feedback on a GitHub pull request.

## Procedure

1. Resolve the repository and PR, then fetch review threads with their inline comment IDs and `isResolved`/`isOutdated` state. Prefer the thread-aware `fetch_comments.py` workflow from `github:gh-address-comments` or the GitHub connector's thread API.
2. Group only the unresolved, non-outdated actionable threads. Keep the response mapped to the exact file/line and comment that it addresses.
3. Reply to each thread's top-level inline comment individually. Use the GitHub review-comment reply endpoint or the GitHub connector's `github_reply_to_review_comment`; do not use `gh pr comment` for the default response path.
4. Begin every Amazon Q reply with `/q ` and every ChatGPT Codex Connector (`chatgpt-codex-connector`) reply with `@codex `. Apply any other prefix the user explicitly requests. Use Japanese when the repository or user requests Japanese review communication.
5. Verify that every intended thread has a reply URL. Report the thread-to-reply mapping and leave unrelated, resolved, or outdated threads untouched.

## Reply body format

- After the required reviewer prefix, start with the substantive response. Do not use formulaic lead-ins such as `確認ありがとうございます`, `ご指摘ありがとうございます`, or `レビューありがとうございます`.
- Begin each Amazon Q reply with `/q ` and keep the response attached to the specific thread.
- Begin each ChatGPT Codex Connector (`chatgpt-codex-connector`) reply with `@codex ` and keep the response attached to the specific thread.
- Pass actual newline characters in the reply body. Never submit literal escaped sequences such as `\n`; when building a payload in JavaScript, use a multiline template literal or join lines with a single `"\n"` operation.
- When the thread is addressed by a commit, append one blank line followed by the bare commit URL as the final line. Do not add labels such as `コミット:` or `Commit:`, Markdown link syntax, or backticks around the URL.
- Use this shape:

```text
/q 対応内容を簡潔に説明する。
追加の検証結果や補足。

https://github.com/OWNER/REPO/commit/COMMIT_SHA
```

For ChatGPT Codex Connector, use the equivalent shape:

```text
@codex 対応内容を簡潔に説明する。
追加の検証結果や補足。

https://github.com/OWNER/REPO/commit/COMMIT_SHA
```

- If no code changed, omit the commit URL. If multiple commits are relevant, append one bare URL per line at the end, with no labels.

## Guardrails

- Do not combine multiple inline comments into one top-level comment unless the user explicitly asks for a summary comment.
- Do not resolve threads, submit an approval/request-changes review, or modify code unless the user explicitly requests that action.
- If a review comment is informational, contradictory, or ambiguous, explain the assessment and ask before changing code.
- Preserve reviewer context: answer the specific concern first, then cite the relevant workflow/code behavior or validation evidence.
