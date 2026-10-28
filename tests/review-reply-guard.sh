#!/bin/bash
# review-reply-guard.sh の自己チェック。1 件でも期待と違えば exit 1。
# 実行: bash tests/review-reply-guard.sh（~/.claude/hooks に反映済みの実体を検査する）
h=~/.claude/hooks/review-reply-guard.sh
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
echo '{"body":"@claude 対応しました"}' > "$d/ok.json"
echo '{"body":"対応しました"}' > "$d/ng.json"
fail=0
t() {
  printf '%-30s %-5s ' "$1" "$2"
  out=$(printf '%s' "$4" | "$h")
  r=$([ -n "$out" ] && echo DENY || echo allow)
  if [ "$r" = "$3" ]; then echo "$r"; else echo "$r  <-- FAIL expected $3"; fail=1; fi
}
b() { jq -cn --arg c "$1" --arg cwd "$d" '{tool_name:"Bash",cwd:$cwd,tool_input:{command:$c}}'; }
m() { jq -cn --arg b "$1" '{tool_name:"mcp__claude_ai_GitHub__reply_to_review_comment",tool_input:{owner:"o",repo:"r",comment_id:1,body:$b}}'; }
u='gh api repos/o/r/pulls/12/comments/345/replies'

t "prefix ok (@codex )"      bash allow "$(b "$u -f body=\"@codex 修正しました\"")"
t "prefix ok (/q )"          bash allow "$(b "$u -f body=\"/q fixed\"")"
t "no prefix"                bash DENY  "$(b "$u -f body=\"修正しました\"")"
t "prefix + newline"         bash allow "$(b "$u -f body=\"@codex"$'\n'"修正しました\"")"
t "--input abs file (ok)"    bash allow "$(b "$u --input $d/ok.json")"
t "--input abs file (ng)"    bash DENY  "$(b "$u --input $d/ng.json")"
t "--input rel file (ok)"    bash allow "$(b "$u --input ok.json")"
t "--input quoted file (ok)" bash allow "$(b "$u --input \"$d/ok.json\"")"
t "--input missing file"     bash DENY  "$(b "$u --input nope.json")"
t "--input - heredoc (ok)"   bash allow "$(b "$u --input - <<'EOF'"$'\n''{"body":"@claude 対応"}'$'\n''EOF')"
t "--input - heredoc (ng)"   bash DENY  "$(b "$u --input - <<'EOF'"$'\n''{"body":"対応"}'$'\n''EOF')"
t "unrelated gh pr comment"  bash allow "$(b 'gh pr comment 12 --body "hello"')"
t "GET thread list"          bash allow "$(b 'gh api repos/o/r/pulls/12/comments')"
t "mcp body ok"              mcp  allow "$(m '@codex 対応しました')"
t "mcp body ng"              mcp  DENY  "$(m '対応しました')"
t "mcp other tool"           mcp  allow "$(jq -cn '{tool_name:"mcp__claude_ai_GitHub__get_pull_request",tool_input:{number:1}}')"

echo "--- deny payload ---"
printf '%s' "$(b "$u -f body=x")" | "$h" | jq -c '.hookSpecificOutput | {hookEventName, permissionDecision}'
exit $fail
