#!/usr/bin/env sh
# Brings the current issue branch up to date with the latest dev without losing local work:
# stash, fetch, rebase onto dev, then restore the stash.
#
# Usage: sh .github/scripts/sync-with-dev.sh
set -eu

fail() {
  printf 'sync-with-dev: %s\n' "$1" >&2
  exit 1
}

git rev-parse --git-dir >/dev/null 2>&1 || fail "run this from inside the repository."

if [ -d "$(git rev-parse --git-path rebase-merge)" ] || [ -d "$(git rev-parse --git-path rebase-apply)" ]; then
  fail "a rebase is already in progress. Finish it with 'git rebase --continue' or cancel it with 'git rebase --abort'."
fi

branch=$(git symbolic-ref --quiet --short HEAD) || fail "you are not on a branch. Check out your issue branch first."
case "$branch" in
  main | dev) fail "you are on '$branch'. Create or switch to your issue branch, for example: git checkout -b feat/42-short-description" ;;
esac

# Forks track the project as 'upstream'; maintainers working in the project itself use 'origin'
if git remote get-url upstream >/dev/null 2>&1; then
  remote=upstream
else
  remote=origin
fi

stashed=0
if [ -n "$(git status --porcelain)" ]; then
  git stash push --include-untracked --message "sync-with-dev: $branch"
  stashed=1
fi

restore_hint() {
  if [ "$stashed" -eq 1 ]; then
    printf "Your uncommitted work is saved in the stash. Restore it afterwards with 'git stash pop'.\n" >&2
  fi
}

git fetch "$remote" dev || { restore_hint; fail "could not fetch dev from '$remote'."; }

if ! git rebase "$remote/dev"; then
  printf '\nThe rebase stopped on a conflict.\n' >&2
  printf "Resolve the conflicted files, run 'git add <file>' and 'git rebase --continue'.\n" >&2
  restore_hint
  exit 1
fi

if [ "$stashed" -eq 1 ] && ! git stash pop; then
  fail "your work was restored with conflicts. Resolve them, then run 'git stash drop'."
fi

printf "\n'%s' is now based on the latest %s/dev.\n" "$branch" "$remote"
printf 'Next: git add <files>, git commit, then git push --force-with-lease origin %s\n' "$branch"
