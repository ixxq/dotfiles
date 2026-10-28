#!/bin/bash
# Claude Code の PreToolUse(Bash) hook。
# PR レビュースレッドへの返信（gh api .../pulls/N/comments/ID/replies）に
# reviewer prefix（/q, @codex, @claude）が無ければ拒否し、
# github-review-thread-reply スキルを使うよう促す。
cmd=$(jq -r '.tool_input.command // ""')
if [[ "$cmd" =~ pulls/[0-9]+/comments/[0-9]+/replies ]] && ! [[ "$cmd" =~ (/q\ |@codex\ |@claude\ ) ]]; then
  jq -n '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:"レビュースレッドへの返信に reviewer prefix（/q, @codex, @claude）がありません。先に github-review-thread-reply スキルを読み込み、その手順（prefix 付き返信、定型の書き出し禁止、Follow-up ループ）に従ってください。"}}'
fi
