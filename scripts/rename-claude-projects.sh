#!/usr/bin/env bash
set -uo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

OLD_USER=""
NEW_USER=""
DRY_RUN=0
VERBOSE=0
REWRITE_CONTENT=0
PROJECTS_DIR="${HOME}/.claude/projects"

print_usage() {
  cat <<'USAGE'
Rename Claude Code project session directories after a macOS user rename.

Claude Code stores per-project sessions under directories whose names encode the
absolute CWD, e.g. /Users/<shortname>/.dotfiles becomes -Users-<shortname>--dotfiles.
When the macOS shortname changes, those directories no longer match the new CWD
and `/resume` cannot find past sessions. This script migrates them in place.

Options:
  --old OLD_SHORTNAME    (required) previous macOS shortname
  --new NEW_SHORTNAME    (required) new macOS shortname
  --dry-run              Show what would happen without renaming
  --verbose              Print every directory considered, not just acted on
  --rewrite-content      In addition to renaming directories, rewrite
                         /Users/OLD/ -> /Users/NEW/ inside every *.jsonl
                         file under PROJECTS_DIR. Creates a .bak sibling
                         per modified file.
  -h, --help             Show this help

Examples:
  rename-claude-projects.sh --old lemtoc --new ve62ca --dry-run
  rename-claude-projects.sh --old lemtoc --new ve62ca
  rename-claude-projects.sh --old mfyuu  --new t1190078 --rewrite-content

Notes:
  - Operates on ~/.claude/projects/ only.
  - Only the leading "-Users-<OLD>-" prefix of each directory name is
    rewritten, so project paths that happen to contain <OLD> as a non-
    prefix segment (e.g. /Users/mfyuu/dev/oss/mfyuu.dev) are preserved.
  - If the target directory already exists, the source is left untouched
    (collision). Resolve manually by merging the two directories' JSONL files.
  - --rewrite-content does not undo a previous rename; it only fixes the
    cwd / path strings recorded inside session jsonl files.
USAGE
}

log_info()    { printf "${BLUE}[INFO]${NC} %s\n" "$*"; }
log_ok()      { printf "${GREEN}[ OK ]${NC} %s\n" "$*"; }
log_skip()    { printf "${YELLOW}[SKIP]${NC} %s\n" "$*"; }
log_warn()    { printf "${YELLOW}[WARN]${NC} %s\n" "$*"; }
log_error()   { printf "${RED}[ERR ]${NC} %s\n" "$*" >&2; }
log_dryrun()  { printf "${CYAN}[DRY ]${NC} %s\n" "$*"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --old)              OLD_USER="${2:-}"; shift 2 ;;
    --new)              NEW_USER="${2:-}"; shift 2 ;;
    --dry-run)          DRY_RUN=1;         shift   ;;
    --verbose)          VERBOSE=1;         shift   ;;
    --rewrite-content)  REWRITE_CONTENT=1; shift   ;;
    -h|--help)          print_usage;       exit 0  ;;
    *)                  log_error "Unknown argument: $1"; print_usage; exit 2 ;;
  esac
done

if [[ -z "$OLD_USER" || -z "$NEW_USER" ]]; then
  log_error "--old and --new are required"
  print_usage
  exit 2
fi

if [[ "$OLD_USER" == "$NEW_USER" ]]; then
  log_error "--old and --new must differ (both were '$OLD_USER')"
  exit 2
fi

if [[ ! -d "$PROJECTS_DIR" ]]; then
  log_error "$PROJECTS_DIR not found"
  exit 1
fi

PATTERN="-Users-${OLD_USER}-"
log_info "Scanning $PROJECTS_DIR for entries matching '${PATTERN}*'"
[[ $DRY_RUN -eq 1 ]] && log_info "Dry-run mode: no changes will be applied"

migrated=0
skipped=0
collisions=0
errors=0

shopt -s nullglob 2>/dev/null || true

for dir in "$PROJECTS_DIR"/${PATTERN}*; do
  [[ -d "$dir" ]] || continue
  base="$(basename "$dir")"
  # Replace only the leading "-Users-<OLD>-" prefix, not every occurrence of
  # OLD inside the encoded path (e.g. /Users/mfyuu/dev/oss/mfyuu.dev must
  # keep its trailing "mfyuu-dev" segment).
  new_base="-Users-${NEW_USER}-${base#-Users-${OLD_USER}-}"
  target="$PROJECTS_DIR/$new_base"

  if [[ "$base" == "$new_base" ]]; then
    [[ $VERBOSE -eq 1 ]] && log_skip "$base (no substitution)"
    skipped=$((skipped + 1))
    continue
  fi

  if [[ -e "$target" ]]; then
    log_warn "collision: $new_base already exists — leaving $base in place"
    collisions=$((collisions + 1))
    continue
  fi

  if [[ $DRY_RUN -eq 1 ]]; then
    log_dryrun "$base -> $new_base"
    migrated=$((migrated + 1))
  else
    if mv "$dir" "$target"; then
      log_ok "$base -> $new_base"
      migrated=$((migrated + 1))
    else
      log_error "failed to rename $base"
      errors=$((errors + 1))
    fi
  fi
done

printf "\n"
log_info "Summary: migrated=${migrated} collisions=${collisions} skipped=${skipped} errors=${errors}"

if [[ $REWRITE_CONTENT -eq 1 ]]; then
  printf "\n"
  log_info "Rewriting /Users/${OLD_USER}/ -> /Users/${NEW_USER}/ inside *.jsonl"

  rewritten=0
  rewrite_skipped=0
  rewrite_errors=0
  needle="/Users/${OLD_USER}/"
  replacement="/Users/${NEW_USER}/"

  while IFS= read -r -d '' jsonl; do
    if ! grep -q -F -- "$needle" "$jsonl"; then
      [[ $VERBOSE -eq 1 ]] && log_skip "$jsonl (no occurrences)"
      rewrite_skipped=$((rewrite_skipped + 1))
      continue
    fi
    if [[ $DRY_RUN -eq 1 ]]; then
      log_dryrun "rewrite: $jsonl"
      rewritten=$((rewritten + 1))
      continue
    fi
    # macOS sed: `-i .bak` keeps a sibling backup so the change is reversible.
    if sed -i .bak "s|${needle}|${replacement}|g" "$jsonl"; then
      log_ok "rewrote: $jsonl"
      rewritten=$((rewritten + 1))
    else
      log_error "failed to rewrite: $jsonl"
      rewrite_errors=$((rewrite_errors + 1))
    fi
  done < <(find "$PROJECTS_DIR" -type f -name "*.jsonl" -print0)

  log_info "Rewrite summary: rewritten=${rewritten} skipped=${rewrite_skipped} errors=${rewrite_errors}"
  if [[ $DRY_RUN -ne 1 && $rewritten -gt 0 ]]; then
    log_info "Backups stored as *.jsonl.bak. Clean up with:"
    log_info "  find \"$PROJECTS_DIR\" -name '*.jsonl.bak' -delete"
  fi
  errors=$((errors + rewrite_errors))
fi

if [[ $errors -gt 0 ]]; then
  exit 1
fi
