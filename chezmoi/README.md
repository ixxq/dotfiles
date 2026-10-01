# chezmoi source

This directory is the chezmoi source tree for mutable dotfiles.

Nix owns packages, system settings, and stable Home Manager modules. chezmoi owns files that are edited by app UIs or day-to-day commands, such as Codex, Claude, SidePulse, Karabiner, Ghostty, mise, VS Code, and Cursor settings.

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

## Notes

`README.md` is listed in `.chezmoiignore`, so this file is documentation for the source tree only and is not written to `$HOME`.
