---
name: github-review-thread-reply
description: Reply to GitHub pull request review feedback one thread at a time, then wait for the reviewer, resolve withdrawn threads, and follow up on the rest. Use when a user asks to respond to PR review comments, especially Amazon Q `/q`, Codex `@codex`, or Claude `@claude` feedback, and the response must stay attached to each inline review thread instead of becoming a top-level PR comment.
---

# GitHub Review Thread Reply

Use this skill when responding to review feedback on a GitHub pull request.

## Procedure

1. Resolve the repository and PR, then fetch review threads with `gh api graphql` (query below). It returns the thread node `id` (needed to resolve), `isResolved`/`isOutdated`, and each comment's `databaseId`, author, and timestamp.
2. Group only the unresolved, non-outdated actionable threads. Keep the response mapped to the exact file/line and comment that it addresses.
3. Reply to each thread's top-level inline comment individually. Use the GitHub review-comment reply endpoint or the GitHub connector's `github_reply_to_review_comment` (without a connector: `gh api repos/OWNER/REPO/pulls/PR/comments/COMMENT_ID/replies -f body=...`); do not use `gh pr comment` for the default response path.
4. Begin every reply with the reviewer prefix from the table below. Apply any other prefix the user explicitly requests. Use Japanese when the repository or user requests Japanese review communication.
5. Verify that every intended thread has a reply URL, then continue with the Follow-up loop. Leave unrelated, resolved, or outdated threads untouched.

| Reviewer | Login | Prefix |
| --- | --- | --- |
| Amazon Q | `amazon-q-developer[bot]` | `/q ` |
| ChatGPT Codex Connector | `chatgpt-codex-connector[bot]` | `@codex ` |
| Claude | `claude[bot]` | `@claude ` |

```bash
gh api graphql -F owner=OWNER -F repo=REPO -F pr=PR -f query='
query($owner:String!,$repo:String!,$pr:Int!){
  repository(owner:$owner,name:$repo){
    pullRequest(number:$pr){
      reviewThreads(first:100){
        nodes{
          id isResolved isOutdated path line
          comments(first:100){ nodes{ databaseId author{login} createdAt body url } }
        }
      }
    }
  }
}'
```

GraphQL returns bot logins without the `[bot]` suffix (e.g. `amazon-q-developer`); match both forms.

## Follow-up loop

Run this by default after replying. One round:

1. **Wait.** In a background loop with an exit condition (not a long-running monitor), re-run the query every 30 seconds until every awaited thread's last comment is from the reviewer bot and newer than your reply, or 30 minutes pass. Notify once when the loop exits.
2. **Classify** each awaited thread by the reviewer's response:
   - **Withdrawn or accepted** → resolve it: `gh api graphql -F id=THREAD_ID -f query='mutation($id:ID!){resolveReviewThread(input:{threadId:$id}){thread{isResolved}}}'`.
   - **Maintained or new concern** → assess it yourself:
     - **Change needed** and scoped to the thread's concern → fix it, run the repository's lint/typecheck/tests, commit, push to the PR head branch, and reply with the commit URL.
     - **No change needed** → reply with the reason and the code or behavior that supports it.
     - **Cannot decide** (ambiguous concern, spec or design trade-off, contradicts another thread, or the fix spreads beyond the thread) → call the `advisor` tool once if available. If its advice settles the case, act on it; otherwise ask the user, then act on the answer.
   - **No response or non-committal** (e.g. "will re-review") by the timeout → leave unresolved and mark pending. Amazon Q sometimes answers in a new top-level review instead of the thread; mention that in the pending note.
3. Threads you replied to in this round become the awaited set for the next round.

Stop when no thread is awaited or after 3 rounds. Report a table: thread → latest reply URL → reviewer verdict → action (resolved / replied / pending / asked user).

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
- Resolve only threads whose reviewer withdrew or accepted in the Follow-up loop. Never resolve on your own assessment alone, and never touch threads you did not reply to in this run.
- Do not submit an approval/request-changes review. Push only to the PR head branch, never force-push.
- Outside the Follow-up loop's "change needed" case, do not modify code unless the user asks. If a comment is informational, contradictory, or ambiguous, explain the assessment and ask before changing code.
- Preserve reviewer context: answer the specific concern first, then cite the relevant workflow/code behavior or validation evidence.
