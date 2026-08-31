#!/usr/bin/env bash
set -euo pipefail

repo=/home/acp/projects/gaussian-splats
stamp="${XDG_STATE_HOME:-$HOME/.local/state}/gaussian-splats-last-push"

cd "$repo"
[[ $(git branch --show-current) == master ]] || exit 0
[[ ! -f $stamp || $(<"$stamp") != "$(date -I)" ]] || exit 0

if [[ $(git rev-list --count origin/master..HEAD) -eq 0 ]]; then
  file=
  while IFS= read -r -d '' candidate; do
    file=$candidate
    break
  done < <(
    {
      git diff --name-only -z
      git diff --cached --name-only -z
      git ls-files --others --exclude-standard -z
    } | sort -zu | head -z -n 1
  )
  [[ -n $file ]] || exit 0

  if [[ ${1-} == --dry-run ]]; then
    printf '%s\n' "$file"
    exit 0
  fi

  git add -- "$file"
  git commit --only -m "Add $file" -- "$file"
fi

GIT_TERMINAL_PROMPT=0 git push origin HEAD:master
mkdir -p "${stamp%/*}"
date -I >"$stamp"
