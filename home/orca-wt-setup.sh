#!/usr/bin/env bash
# Orca の setup フック（各リポジトリの orca.yaml の scripts.setup）から呼ぶ。
# git-wt の copyignored + hook=ni 相当だが、コピーはローカル設定ファイルだけに絞る。
set -euo pipefail

# Orca（GUI アプリ）経由だとログインシェルの PATH が載らないことがあるため末尾に補う
export PATH="$PATH:$HOME/.local/share/mise/shims:/etc/profiles/per-user/$USER/bin"

src="$ORCA_ROOT_PATH"
dst="$ORCA_WORKTREE_PATH"

copy() {
  mkdir -p "$dst/$(dirname "$1")"
  cp -p "$src/$1" "$dst/$1"
}

# --directory で node_modules/ や target/ は1行に畳まれ、中身を辿らない
git -C "$src" ls-files -z --others --ignored --exclude-standard --directory |
  while IFS= read -r -d '' f; do
    case "${f##*/}" in
      .env | .env.* | .envrc | .npmrc | bunfig.toml | mise.local.toml | CLAUDE.local.md) copy "$f" ;;
    esac
  done

# .claude/ はディレクトリごと ignore されていて上の一覧に出ないため個別に拾う
if [[ -f "$src/.claude/settings.local.json" ]]; then
  copy .claude/settings.local.json
fi

if [[ -f "$dst/package.json" ]]; then
  cd "$dst"
  ni --frozen
fi
