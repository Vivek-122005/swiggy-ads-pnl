#!/usr/bin/env bash
# ship.sh - replay queued commits with YOUR local git identity and push as Vivek-122005.
#
# Claude writes code into this folder and queues small commits in .ship/queue/*.commit
# (subject line, optional body, then a ---files--- list). Running this script turns each
# queue entry into one commit, in order, using the git user configured on this Mac,
# then pushes to github.com/Vivek-122005/swiggy-ads-pnl. Nothing is pushed by any bot.
#
#   ./ship.sh            # commit everything queued, then push
#   ./ship.sh --dry-run  # show what would be committed
set -euo pipefail
cd "$(dirname "$0")"

EXPECTED_USER="Vivek-122005"
REPO="swiggy-ads-pnl"
DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

die() { echo "ship.sh: $*" >&2; exit 1; }

command -v git >/dev/null || die "git not found"
command -v gh  >/dev/null || die "GitHub CLI (gh) not found: brew install gh && gh auth login"
login="$(gh api user --jq .login 2>/dev/null || true)"
[ "$login" = "$EXPECTED_USER" ] || die "gh is logged in as '${login:-nobody}', expected $EXPECTED_USER. Run: gh auth switch -u $EXPECTED_USER"
git config user.name >/dev/null || die "git user.name is not set on this machine"

if [ ! -d .git ]; then
  [ $DRY = 1 ] && { echo "(dry run) would run: git init -b main"; } || git init -q -b main
fi

# (written for the bash 3.2 that ships with macOS: no empty-array expansion under set -u)
n=0
for f in .ship/queue/*.commit; do [ -e "$f" ] && n=$((n + 1)); done
echo "Queued commits: $n"
for f in .ship/queue/*.commit; do
  [ -e "$f" ] || continue
  subject="$(head -n 1 "$f")"
  body="$(awk 'NR==1{next} /^---files---$/{exit} {print}' "$f" | sed -e '/./,$!d')"
  files="$(awk 'found{print} /^---files---$/{found=1}' "$f")"
  if [ $DRY = 1 ]; then
    echo "  - $subject"; echo "$files" | sed 's/^/      /'; continue
  fi
  while IFS= read -r p; do
    [ -n "$p" ] && git add -A -- "$p"
  done <<< "$files"
  if git diff --cached --quiet; then
    echo "  skip (nothing changed): $subject"
  elif [ -n "$body" ]; then
    git commit -q -m "$subject" -m "$body" && echo "  committed: $subject"
  else
    git commit -q -m "$subject" && echo "  committed: $subject"
  fi
  mkdir -p .ship/done && mv "$f" .ship/done/
done
[ $DRY = 1 ] && exit 0

if ! git remote get-url origin >/dev/null 2>&1; then
  if gh repo view "$EXPECTED_USER/$REPO" >/dev/null 2>&1; then
    git remote add origin "https://github.com/$EXPECTED_USER/$REPO.git"
  else
    gh repo create "$EXPECTED_USER/$REPO" --public \
      --description "Weekly ads P&L reporting for a simulated Bengaluru food + quick-commerce ads marketplace: simulator -> dbt -> dashboard -> WBR" \
      --source . --remote origin
  fi
fi
# GitHub Pages served by the Actions workflow (idempotent; ignored if already enabled)
gh api -X POST "repos/$EXPECTED_USER/$REPO/pages" -f build_type=workflow >/dev/null 2>&1 || true
git push -u origin main
echo "Pushed to https://github.com/$EXPECTED_USER/$REPO as $login"
