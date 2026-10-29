# chezmoi source

This directory is the chezmoi source tree for mutable dotfiles.

Nix owns packages, system settings, and stable Home Manager modules. chezmoi owns files that are edited by app UIs or day-to-day commands, such as Codex, Claude, SidePulse, Karabiner, Ghostty, mise, VS Code, and Cursor settings.

Meltype's user dictionary is managed at `private_Library/private_Application Support/Meltype/userdict.txt`. Each UTF-8 line contains a hiragana reading and its replacement, separated by a tab. Apply only the dictionary with `chezmoi apply --exclude scripts "$HOME/Library/Application Support/Meltype/userdict.txt"`, then restart Meltype to reload it. The `あぴ` entry converts to `API` when Space is pressed.

After editing words in Meltype for Mac's dictionary window, capture them with `chezmoi add "$HOME/Library/Application Support/Meltype/userdict.txt"` before applying dotfiles again.

SidePulse's six customized Python files are also managed here, under `dot_local/share/sidepulse/venv/lib/python3.13/site-packages/sidepulse`. Git records the upstream files before the customizations. See [SidePulse](../sidepulse/README.md) for the matching CLI version, LED settings, agent hooks, and restart / OFF / ON commands. `chezmoi apply` restores both settings and these Python files after installing that version.

## Local Setup

chezmoi normally creates its source tree at `~/.local/share/chezmoi`, but this repository keeps it under `~/.dotfiles/chezmoi`.

Configure that once per machine:

```sh
mkdir -p ~/.config/chezmoi
printf 'sourceDir = "%s"\n' "$HOME/.dotfiles/chezmoi" > ~/.config/chezmoi/chezmoi.toml
```

`~/.config/chezmoi/chezmoi.toml` is intentionally local and not managed by this repository. Without it, chezmoi will use the default source directory instead.

## Daily Usage

Check local changes before applying them:

```sh
chezmoi diff
```

Apply the files in this source tree to `$HOME`:

```sh
chezmoi apply
```

Capture changes made from app UIs:

```sh
chezmoi add ~/.codex/config.toml
chezmoi add ~/.config/karabiner/karabiner.json
chezmoi add ~/.config/mise/config.toml
```

## Switching Meltype distributions

`hosts/common/homebrew.nix` selects `whitewater-png/meltype-for-mac/meltype-for-mac`. The upstream `yksr-melt/meltype` tap is retained so it is easy to switch back.

Both distributions install `~/Library/Input Methods/Meltype.app` and share `~/Library/Application Support/Meltype/`. Git tracks the Homebrew configuration and user dictionary; it does not track the installed app, preferences, or learning data. The pre-switch backup on this Mac is `~/Library/Application Support/Meltype-backups/20261029-161951-upstream-1.4.0/`. Its `manifest.json` records the upstream version and original dotfiles commit; it includes the app, data directory, preferences, and cached upstream ZIP. Create a fresh backup before future switches; Nix and chezmoi do not create these snapshots automatically.

To return to upstream:

1. Select ABC or Apple's Japanese input source.
2. Change the cask entry in `hosts/common/homebrew.nix` back to `yksr-melt/meltype/meltype`.
3. Replace only the Meltype cask, preserving its shared data:

   ```sh
   brew uninstall --cask meltype-for-mac
   brew install --cask yksr-melt/meltype/meltype
   "$HOME/Library/Input Methods/Meltype.app/Contents/MacOS/MeltypeRegisterInputSource" \
     "$HOME/Library/Input Methods/Meltype.app"
   ```

Complete these scoped commands before the next `nix run .#switch`: this repository uses Homebrew cleanup `zap`, which can delete shared learning data when it removes the old cask. Do not use `--zap` when changing Meltype distributions.

For the original learning state, stop Meltype, move the current data directory aside, and restore the snapshot's `Meltype/` directory before starting upstream. Keep any words added since the snapshot by capturing the current user dictionary first. Log out and log back in if the input source does not refresh after replacement.

## Notes

`README.md` is listed in `.chezmoiignore`, so this file is documentation for the source tree only and is not written to `$HOME`.
