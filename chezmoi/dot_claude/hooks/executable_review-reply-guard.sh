#!/bin/bash
# Claude Code の PreToolUse hook（matcher: Bash と mcp__*reply_to_review_comment*）。
# PR レビュースレッドへの返信に reviewer prefix（/q, @codex, @claude）が無ければ拒否し、
# github-review-thread-reply スキルを使うよう促す。
# 対象: gh api .../pulls/N/comments/ID/replies（-f body= / --input FILE / --input - heredoc）と
#       GitHub connector の reply_to_review_comment。
# reviewer を追加するときは SKILL.md の表と下の prefix 正規表現の両方を更新する。
input=$(cat)
tool=$(jq -r '.tool_name // ""' <<<"$input")
cmd=$(jq -r '.tool_input.command // ""' <<<"$input")
if [[ "$tool" != *reply_to_review_comment* ]] && ! [[ "$cmd" =~ pulls/[0-9]+/comments/[0-9]+/replies ]]; then
  exit 0
fi

# tool_input 内の全文字列を検査対象にする（Bash の command も MCP の body も field 名に依らず拾える）
text=$(jq -r '.tool_input | .. | strings' <<<"$input")
# --input FILE の場合は本文がコマンド文字列に無いのでファイルを読む（--input - の heredoc は command に含まれる）
if [[ "$cmd" =~ --input[[:space:]=]+([^[:space:]]+) ]] && [[ "${BASH_REMATCH[1]}" != "-" ]]; then
  f="${BASH_REMATCH[1]//[\"\']/}"
  f="${f/#\~/$HOME}"
  [[ "$f" != /* ]] && f="$(jq -r '.cwd // "."' <<<"$input")/$f"
  text=$(jq -r '.body // ""' "$f" 2>/dev/null)
fi

prefix_re='(/q|@codex|@claude)[[:space:]]'
[[ "$text" =~ $prefix_re ]] && exit 0
jq -n '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:"レビュースレッドへの返信に reviewer prefix（/q, @codex, @claude）がありません。先に github-review-thread-reply スキルを読み込み、その手順（prefix 付き返信、定型の書き出し禁止、Follow-up ループ）に従ってください。"}}'
