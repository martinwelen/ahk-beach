#!/usr/bin/env bash
# Publicerar dist-u15/ till roten av alingsas-ahus-beach-2026 (behåller repots
# övriga filer/historik). Kräver env DEPLOY_KEY (privat SSH deploy key med skriv).
set -euo pipefail

REPO="git@github.com:martinwelen/alingsas-ahus-beach-2026.git"
WORK="$(mktemp -d)"

if [ ! -d dist-u15 ]; then
  echo "dist-u15/ saknas – inget att publicera."; exit 0
fi

mkdir -p ~/.ssh
printf '%s\n' "$DEPLOY_KEY" > ~/.ssh/u15_deploy
chmod 600 ~/.ssh/u15_deploy
trap 'rm -f "$HOME/.ssh/u15_deploy"' EXIT
export GIT_SSH_COMMAND="ssh -i $HOME/.ssh/u15_deploy -o StrictHostKeyChecking=no"

git clone --depth 1 "$REPO" "$WORK"
# Kopiera app-filerna över; behåller allt annat (källkod/docs) i mål-repot.
cp -R dist-u15/. "$WORK"/

cd "$WORK"
git config user.name "ahk-beach-bot"
git config user.email "github-actions[bot]@users.noreply.github.com"
git add -A
if git diff --cached --quiet; then
  echo "U15 oförändrad – inget att publicera."
else
  git commit -m "U15-uppdatering från ahk-beach ($(date -u '+%Y-%m-%d %H:%M UTC'))"
  git push origin HEAD:main
  echo "U15 publicerad."
fi
