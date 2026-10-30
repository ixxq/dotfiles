# cache_eval: cache expensive eval commands to disk
# eval "$(cmd)" is slow because it spawns a subprocess every time (~6-10ms each).
# This function runs the command once, saves the output to a file, and sources it on subsequent startups.
# Cache is stored in ~/.cache/zsh/<command_name>.zsh
# To invalidate: rm -rf ~/.cache/zsh
cache_eval() {
  local cache_dir="$HOME/.cache/zsh"
  local cache_file="$cache_dir/$(echo "$1" | tr ' /' '_').zsh"
  if [[ ! -s "$cache_file" ]]; then
    mkdir -p "$cache_dir"
    eval "$1" > "$cache_file"
  fi
  source "$cache_file"
}

# GPG_TTY (dynamic value, cannot use sessionVariables)
export GPG_TTY=$TTY

# brew completions (gh, etc.)
# Hardcoded instead of $(brew --prefix) to avoid spawning brew binary (~15ms)
FPATH="/opt/homebrew/share/zsh/site-functions:${FPATH}"

# zsh options (Oh My Zsh compatible completion settings)
zmodload -i zsh/complist
unsetopt menu_complete
setopt auto_menu complete_in_word always_to_end always_last_prompt auto_cd
zstyle ':completion:*:*:*:*:*' menu select

# Zeno fallback: create a completion widget that bypasses FSH widget wrapping.
# zle -C creates a "completion widget" (not a "user widget") that calls
# _main_complete directly through the raw .expand-or-complete builtin.
# This avoids the zeno → fzf → expand-or-complete → FSH → recursion loop.
zle -C _zeno_safe_complete .expand-or-complete _main_complete
export ZENO_COMPLETION_FALLBACK=_zeno_safe_complete
# Avoid running `deno cache` on every deferred zeno load. Run it manually after
# updating zeno if dependencies change.
export ZENO_DISABLE_EXECUTE_CACHE_COMMAND=1

# make word deletion stop at path separators
WORDCHARS=""

# ~/Downloads とその配下では claude を起動しない
# (lazy.zsh だと定義前の貼り付け実行をすり抜けるため同期で読む)
claude() {
  [[ $PWD == ~/Downloads(|/*) ]] && return 1
  command claude "$@"
}
