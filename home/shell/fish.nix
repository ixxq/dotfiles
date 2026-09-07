{
  programs.fish = {
    enable = true;

    loginShellInit = ''
      # Hardcoded output of `brew shellenv` to avoid spawning brew binary (~15ms).
      # The output is constant on Apple Silicon, so safe to inline.
      set -gx HOMEBREW_PREFIX /opt/homebrew
      set -gx HOMEBREW_CELLAR /opt/homebrew/Cellar
      set -gx HOMEBREW_REPOSITORY /opt/homebrew
      fish_add_path --path --prepend /opt/homebrew/bin /opt/homebrew/sbin
      set -q MANPATH; or set MANPATH
      set -gx MANPATH /opt/homebrew/share/man $MANPATH
      set -q INFOPATH; or set INFOPATH
      set -gx INFOPATH /opt/homebrew/share/info $INFOPATH
    '';

    interactiveShellInit = ''
      set -g fish_greeting
      test -n "$CMD_DURATION"; or set -gx CMD_DURATION 0
      set -gx GPG_TTY (tty)

      set -gx VIRTUAL_ENV_DISABLE_PROMPT true
      set -l prompt_cache_home ~/.cache
      test -n "$XDG_CACHE_HOME"; and set prompt_cache_home "$XDG_CACHE_HOME"
      set -g __prompt_session (random)(random)
      set -g __prompt_tick 0
      set -g __prompt_first_render 1
      set -g __prompt_git_cache_file "$prompt_cache_home/fish/prompt-git-$fish_pid-$__prompt_session"
      set -g __prompt_aws_cache_file "$prompt_cache_home/fish/prompt-aws-$fish_pid-$__prompt_session"
      mkdir -p (dirname $__prompt_git_cache_file)

      abbr --add g git
      abbr --add ga 'git add'
      abbr --add gc 'git commit'
      abbr --add gp 'git push'
      abbr --add gst 'git status'
      abbr --add gco 'git checkout'
      abbr --add gs 'git switch'
      abbr --add move 'git switch'
      abbr --add mdv 'gh markdown-preview'
      abbr --add cc claude
      abbr --add cci codex:commit
      abbr --add ccpr codex:create-pr
      abbr --add cs cursor
      abbr --add warp 'open -a Warp'
      abbr --add ghostty 'open -a Ghostty'
      abbr --add --command git sw switch
      abbr --add --command git ci commit
      abbr --add --command git push-f 'push --force-with-lease'
      abbr --add --command git push-u 'push -u origin HEAD'
      abbr --add --command git delete 'branch | fzf | xargs git branch -D'
      abbr --add --command git amend 'commit --amend'
      abbr --add --command git amend-n 'commit --amend --no-edit'

      alias cd='z'
      alias cdi='zi'

      awsctx activate fish --aws-wrapper | source
    '';

    shellAliases = {
      tree = "eza -T -a -I 'node_modules|.git|.cache' --icons";
      warp = "open -a Warp";
      ccusage = "bunx ccusage@latest";
      difit = "bunx difit@latest";
      biome-config = "bunx @xrryx/biome-config";
    };

    functions = {
      codex-exec-fast = ''
        codex exec \
          -m gpt-5.4-mini \
          -c model_reasoning_effort='"low"' \
          -c web_search='"disabled"' \
          --disable image_generation \
          $argv
      '';

      "codex:commit" = ''
        codex-exec-fast "Use the `commit` skill."
      '';

      "codex:create-pr" = ''
        codex-exec-fast "Use the `create-pr` skill."
      '';

      __prompt_bump_tick = {
        onEvent = "fish_preexec";
        body = ''
          set -e __prompt_git_repaint
          set -e __prompt_aws_repaint

          if string match --quiet --regex '^\s*(command\s+)?clear(\s|$)' -- "$argv[1]"
            set -g __prompt_suppress_next_git_repaint 1
          else
            set -e __prompt_suppress_next_git_repaint
          end

          if set -q __prompt_git_pid[1]
            command kill $__prompt_git_pid 2>/dev/null
            set -e __prompt_git_pid
          end
        '';
      };

      __prompt_clear_git_repaint = {
        onEvent = "fish_postexec";
        body = ''
          set -e __prompt_git_repaint
          set -e __prompt_aws_repaint

          if string match --quiet --regex '^\s*(command\s+)?aws\s+sso\s+logout(\s|$)' -- "$argv[1]"
            __prompt_expire_aws
          else if string match --quiet --regex '^\s*(command\s+)?aws\s+sso\s+login(\s|$)' -- "$argv[1]"
            __prompt_reset_aws_cache
          end
        '';
      };

      __prompt_reset_aws = {
        onVariable = "AWS_PROFILE";
        body = ''
          __prompt_reset_aws_cache

          if set -q __prompt_aws_pid[1]
            command kill $__prompt_aws_pid 2>/dev/null
            set -e __prompt_aws_pid
          end
        '';
      };

      __prompt_aws_ready = {
        onSignal = "USR2";
        body = ''
          test -f "$__prompt_aws_cache_file"
          or return

          set -l lines (string split \n -- (command cat "$__prompt_aws_cache_file"))
          test "$lines[1]" = "$AWS_PROFILE"
          or begin
            set -e __prompt_aws_pid
            return
          end

          set -g __prompt_aws_profile $lines[1]
          set -g __prompt_aws_expiration_epoch $lines[2]
          set -g __prompt_aws_fetched_at $lines[3]
          set -e __prompt_aws_pid

          set -l next_text (__prompt_aws_remaining "$__prompt_aws_expiration_epoch")
          test "$next_text" != "$__prompt_aws_text"
          or return

          set -g __prompt_aws_text "$next_text"
          set -g __prompt_aws_repaint 1
          commandline -f repaint 2>/dev/null
        '';
      };

      __prompt_reset_git = {
        onVariable = "PWD";
        body = ''
          set -e __prompt_git_root
          set -e __prompt_git_text
          set -e __prompt_git_loaded_root
          set -e __prompt_git_loaded_tick

          if set -q __prompt_git_pid[1]
            command kill $__prompt_git_pid 2>/dev/null
            set -e __prompt_git_pid
          end
        '';
      };

      __prompt_git_ready = {
        onSignal = "USR1";
        body = ''
          test -f "$__prompt_git_cache_file"
          or return

          set -l lines (string split \n -- (command cat "$__prompt_git_cache_file"))
          set -l root $lines[1]
          set -l tick $lines[2]
          set -l text (string join " " $lines[3..-1])

          if test "$PWD" != "$root"; and not string match --quiet -- "$root/*" "$PWD"
            set -e __prompt_git_pid
            return
          end

          if test "$tick" != "$__prompt_tick"
            set -e __prompt_git_pid
            set -g __prompt_git_repaint 1
            commandline -f repaint 2>/dev/null
            return
          end

          set -g __prompt_git_root $root
          set -g __prompt_git_text $text
          set -g __prompt_git_loaded_root $root
          set -g __prompt_git_loaded_tick $tick
          set -e __prompt_git_pid

          if set -q __prompt_suppress_next_git_repaint
            set -e __prompt_suppress_next_git_repaint
            return
          end

          set -g __prompt_git_repaint 1
          commandline -f repaint 2>/dev/null
        '';
      };

      __prompt_git_branch = ''
        command git symbolic-ref --short HEAD 2>/dev/null
        or command git describe --tags --exact-match HEAD 2>/dev/null
        or command git rev-parse --short HEAD 2>/dev/null | string replace --regex -- '(.+)' '@$1'
      '';

      __prompt_git_detail = ''
        set -l root $argv[1]
        set -l old_pwd $PWD

        cd "$root"
        or return

        set -l branch (__prompt_git_branch)
        if test -z "$branch"
          cd "$old_pwd"
          return
        end

        set -l porcelain (command git --no-optional-locks status --porcelain=v1 2>/dev/null)
        if test $status -ne 0
          cd "$old_pwd"
          return
        end

        set -l staged 0
        set -l unstaged 0
        set -l untracked 0

        for line in $porcelain
          set -l index_status (string sub --start 1 --length 1 -- "$line")
          set -l worktree_status (string sub --start 2 --length 1 -- "$line")

          if test "$index_status$worktree_status" = "??"
            set untracked (math $untracked + 1)
          else
            test "$index_status" != " "; and set staged (math $staged + 1)
            test "$worktree_status" != " "; and set unstaged (math $unstaged + 1)
          end
        end

        set -l detail "$branch"
        test (math $staged + $unstaged + $untracked) -gt 0
        and set detail "$detail•"

        set -l upstream @{upstream}
        command git rev-parse --verify --quiet "$upstream" >/dev/null 2>/dev/null
        or begin
          if command git show-ref --verify --quiet "refs/remotes/origin/$branch"
            set upstream "origin/$branch"
          else
            set upstream
          end
        end

        if test -n "$upstream"
          set -l upstream_range (string join "" -- "$upstream" "...@")
          command git rev-list --count --left-right "$upstream_range" 2>/dev/null | read behind ahead
          test "$ahead" -gt 0 2>/dev/null; and set --append detail "↑$ahead"
          test "$behind" -gt 0 2>/dev/null; and set --append detail "↓$behind"
        end

        test $staged -gt 0; and set --append detail "+$staged"
        test $unstaged -gt 0; and set --append detail "~$unstaged"
        test $untracked -gt 0; and set --append detail "?$untracked"

        string join " " $detail
        cd "$old_pwd"
      '';

      __prompt_git_worker = ''
        set -l start_pwd $argv[1]
        set -l tick $argv[2]
        set -l parent_pid $argv[3]
        set -l cache_file $argv[4]

        cd "$start_pwd"
        or exit 0

        set -l root (command git rev-parse --show-toplevel 2>/dev/null)
        or exit 0

        set -l detail (__prompt_git_detail "$root")

        test -n "$detail"
        or exit 0

        set -l tmp_file "$cache_file.tmp"
        printf '%s\n%s\n%s\n' "$root" "$tick" "$detail" >"$tmp_file"
        and command mv "$tmp_file" "$cache_file"
        and command kill -USR1 "$parent_pid" 2>/dev/null
      '';

      __prompt_git = ''
        set -g __prompt_git_render

        if set -q __prompt_git_loaded_root[1]
          if test "$PWD" = "$__prompt_git_loaded_root"; or string match --quiet -- "$__prompt_git_loaded_root/*" "$PWD"
            if test "$__prompt_git_loaded_tick" = "$__prompt_tick"
              set -g __prompt_git_render "$__prompt_git_text"
              return
            end
          end
        end

        if set -q __prompt_git_root[1]
          if test "$PWD" = "$__prompt_git_root"; or string match --quiet -- "$__prompt_git_root/*" "$PWD"
            set -g __prompt_git_render "$__prompt_git_text"
          end
        end

        if test -f "$__prompt_git_cache_file"
          set -l lines (string split \n -- (command cat "$__prompt_git_cache_file"))
          if test "$lines[2]" = "$__prompt_tick"; and begin
              test "$PWD" = "$lines[1]"
              or string match --quiet -- "$lines[1]/*" "$PWD"
            end
            set -g __prompt_git_text (string join " " $lines[3..-1])
            set -g __prompt_git_loaded_root $lines[1]
            set -g __prompt_git_loaded_tick $lines[2]
            set -g __prompt_git_render "$__prompt_git_text"
            set -e __prompt_git_pid
            return
          end
        end

        if set -q __prompt_git_pid[1]
          if not command kill -0 $__prompt_git_pid 2>/dev/null
            set -e __prompt_git_pid
          end
        end

        if not set -q __prompt_git_pid[1]
          command fish -c '__prompt_git_worker $argv[1] $argv[2] $argv[3] $argv[4]' "$PWD" "$__prompt_tick" "$fish_pid" "$__prompt_git_cache_file" >/dev/null 2>&1 &
          set -g __prompt_git_pid $last_pid
          disown $__prompt_git_pid 2>/dev/null
        end
      '';

      __prompt_aws_remaining = ''
        set -l expiration_epoch $argv[1]
        test -n "$expiration_epoch"; and test "$expiration_epoch" != unknown
        or return

        set -l now (command date +%s)
        set -l remaining (math "$expiration_epoch - $now" 2>/dev/null)
        test -n "$remaining"
        or return

        if test "$remaining" -le 0
          printf '[!]'
        else if test "$remaining" -le 3600
          set -l minutes (math --scale=0 "ceil($remaining / 60)")
          printf '%sm' "$minutes"
        else
          return
        end
      '';

      __prompt_reset_aws_cache = ''
        set -e __prompt_aws_profile
        set -e __prompt_aws_expiration_epoch
        set -e __prompt_aws_fetched_at
        set -e __prompt_aws_text
        command rm -f -- "$__prompt_aws_cache_file" "$__prompt_aws_cache_file.tmp" 2>/dev/null
      '';

      __prompt_expire_aws = ''
        test -n "$AWS_PROFILE"
        or return

        set -l now (command date +%s)
        set -g __prompt_aws_profile "$AWS_PROFILE"
        set -g __prompt_aws_expiration_epoch 0
        set -g __prompt_aws_fetched_at "$now"
        set -g __prompt_aws_text '[!]'

        set -l tmp_file "$__prompt_aws_cache_file.tmp"
        printf '%s\n%s\n%s\n' "$AWS_PROFILE" 0 "$now" >"$tmp_file"
        and command mv "$tmp_file" "$__prompt_aws_cache_file"
      '';

      __prompt_aws_worker = ''
        set -l profile $argv[1]
        set -l parent_pid $argv[2]
        set -l cache_file $argv[3]
        set -l now (command date +%s)
        set -l expiration_epoch unknown

        set -l credentials (command aws configure export-credentials --profile "$profile" --format process 2>/dev/null)
        set -l credentials_status $status
        set -l expiration (string match --regex --groups-only '"Expiration"[[:space:]]*:[[:space:]]*"([^"]+)"' -- $credentials)

        if test -n "$expiration"
          set -l expiration_utc (string replace --regex '(\+00:00|Z)$' 'Z' -- "$expiration")
          set expiration_epoch (command date -j -u -f '%Y-%m-%dT%H:%M:%SZ' "$expiration_utc" '+%s' 2>/dev/null)
          or set expiration_epoch (command date -d "$expiration" '+%s' 2>/dev/null)
        else
          set -l sso_start_url (command aws configure get sso_start_url --profile "$profile" 2>/dev/null)
          set -l sso_session (command aws configure get sso_session --profile "$profile" 2>/dev/null)
          if test -n "$sso_start_url$sso_session"; and begin
              test "$credentials_status" -ne 0
              or test -z "$credentials"
            end
            set expiration_epoch 0
          end
        end

        test -n "$expiration_epoch"
        or set expiration_epoch unknown

        set -l tmp_file "$cache_file.tmp"
        printf '%s\n%s\n%s\n' "$profile" "$expiration_epoch" "$now" >"$tmp_file"
        and command mv "$tmp_file" "$cache_file"
        and command kill -USR2 "$parent_pid" 2>/dev/null
      '';

      __prompt_aws = ''
        set -g __prompt_aws_render

        test -n "$AWS_PROFILE"
        or return

        set -l now (command date +%s)

        if test -f "$__prompt_aws_cache_file"
          set -l lines (string split \n -- (command cat "$__prompt_aws_cache_file"))
          if test "$lines[1]" = "$AWS_PROFILE"
            set -g __prompt_aws_profile $lines[1]
            set -g __prompt_aws_expiration_epoch $lines[2]
            set -g __prompt_aws_fetched_at $lines[3]
          end
        end

        set -l cache_age
        if test -n "$__prompt_aws_fetched_at"
          set cache_age (math "$now - $__prompt_aws_fetched_at" 2>/dev/null)
        end

        if test "$__prompt_aws_profile" = "$AWS_PROFILE"; and test -n "$__prompt_aws_expiration_epoch"
          if test "$__prompt_aws_expiration_epoch" != 0; or test -n "$cache_age"; and test "$cache_age" -lt 60
            set -g __prompt_aws_render (__prompt_aws_remaining "$__prompt_aws_expiration_epoch")
          end
        end
        set -g __prompt_aws_text "$__prompt_aws_render"

        set -l should_refresh 0
        if test "$__prompt_aws_profile" != "$AWS_PROFILE"; or test -z "$__prompt_aws_expiration_epoch"
          set should_refresh 1
        else if test -z "$__prompt_aws_fetched_at"; or test (math "$now - $__prompt_aws_fetched_at") -ge 60
          set should_refresh 1
        end

        if set -q __prompt_aws_pid[1]
          if not command kill -0 $__prompt_aws_pid 2>/dev/null
            set -e __prompt_aws_pid
          end
        end

        if test "$should_refresh" = 1; and not set -q __prompt_aws_pid[1]
          command fish -c '__prompt_aws_worker $argv[1] $argv[2] $argv[3]' "$AWS_PROFILE" "$fish_pid" "$__prompt_aws_cache_file" >/dev/null 2>&1 &
          set -g __prompt_aws_pid $last_pid
          disown $__prompt_aws_pid 2>/dev/null
        end
      '';

      __prompt_duration = ''
        test -n "$CMD_DURATION"
        or return

        test "$CMD_DURATION" -ge 1000 2>/dev/null
        or return

        if test "$CMD_DURATION" -ge 60000
          set -l minutes (math --scale=0 "floor($CMD_DURATION / 60000)")
          set -l seconds (math --scale=0 "floor(($CMD_DURATION % 60000) / 1000)")
          printf 'took %sm%ss' "$minutes" "$seconds"
        else
          printf 'took %ss' (math --scale=1 "$CMD_DURATION / 1000")
        end
      '';

      fish_prompt = ''
        set -l prompt_status $status $pipestatus
        set -l last_status $prompt_status[1]
        set -l last_pipestatus $prompt_status[2..-1]
        test -n "$last_status"; or set last_status 0
        test (count $last_pipestatus) -gt 0; or set last_pipestatus $last_status

        if set -q __prompt_git_repaint; or set -q __prompt_aws_repaint
          set -e __prompt_git_repaint
          set -e __prompt_aws_repaint
        else
          if test "$__prompt_first_render" = 1
            set -g __prompt_first_render 0
            set last_status 0
            set last_pipestatus 0
          end
          set -g __prompt_tick (math $__prompt_tick + 1)
        end

        set -l reset (set_color normal)
        set -l time_color (set_color brblack)
        set -l user_color (set_color brcyan)
        set -l pwd_color (set_color brblue)
        set -l git_color (set_color brgreen)
        set -l aws_color (set_color yellow)
        set -l aws_expired_color (set_color brred)
        set -l duration_color (set_color brblack)
        set -l prompt_color (set_color normal)
        set -l error_color (set_color brred)

        set -l parts "$time_color"(command date '+%H:%M')"$reset"

        if test -n "$USER"
          set --append parts "$user_color$USER$reset"
        end

        set --append parts "$pwd_color"(prompt_pwd)"$reset"

        if test -n "$AWS_PROFILE"
          __prompt_aws
          if test "$__prompt_aws_render" = '[!]'
            set --append parts "$aws_color"aws:$AWS_PROFILE"$reset $aws_expired_color$__prompt_aws_render$reset"
          else if test -n "$__prompt_aws_render"
            set --append parts "$aws_color"aws:$AWS_PROFILE $__prompt_aws_render"$reset"
          else
            set --append parts "$aws_color"aws:$AWS_PROFILE"$reset"
          end
        end

        __prompt_git
        set -l git_text $__prompt_git_render
        if test -n "$git_text"
          set --append parts "$git_color$git_text$reset"
        end

        set -l duration (__prompt_duration)
        if test -n "$duration"
          set --append parts "$duration_color$duration$reset"
        end

        set -l status_text
        if test "$last_status" -ne 0
          if test (count $last_pipestatus) -gt 1
            set status_text "["(string join "|" $last_pipestatus)"]"
          else
            set status_text "[$last_status]"
          end

          set --append parts "$error_color$status_text$reset"
          set prompt_color "$error_color"
        end

        printf '%s\n%s ' (string join ' ' $parts) "$prompt_color❱$reset"
      '';

      tp = ''
        if test -z "$argv[1]"
          printf "Command: \e[90mtp\e[0m\n"
          printf "Description: \e[32mCreate a file and its parent directories in one step if they don't exist.\e[0m\n"
          printf "Usage: \e[90mtp <file-path>\e[0m\n"
          printf "Example: \e[90mtp /path/to/your/file.txt\e[0m\n"
        else
          mkdir -p -- (dirname -- "$argv[1]"); and touch -- "$argv[1]"
        end
      '';

      mcd = ''
        if test -z "$argv[1]"
          printf "Command: \e[90mmcd\e[0m\n"
          printf "Description: \e[32mCreate a directory and move into it in one step.\e[0m\n"
          printf "Usage: \e[90mmcd <dir-name>\e[0m\n"
          printf "Example: \e[90mmcd /path/to/your/directory\e[0m\n"
        else
          mkdir -p -- "$argv[1]"; and cd -- "$argv[1]"
        end
      '';

      toggle-env = ''
        set -l dir (test -n "$argv[1]"; and echo "$argv[1]"; or echo .)
        if test -f "$dir/.env.stg"
          mv "$dir/.env.local" "$dir/.env.dev"
          mv "$dir/.env.stg" "$dir/.env.local"
          echo "DEV -> STG"
        else if test -f "$dir/.env.dev"
          mv "$dir/.env.local" "$dir/.env.stg"
          mv "$dir/.env.dev" "$dir/.env.local"
          echo "STG -> DEV"
        else
          echo "error: .env.stg / .env.dev が見つかりません" >&2
        end
      '';
    };
  };
}
