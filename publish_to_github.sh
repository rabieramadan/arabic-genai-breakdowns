#!/usr/bin/env bash
# Publish the Arabic generative-AI breakdown repository to GitHub.
#
#   bash publish_to_github.sh [repo-name]
#
# Run it from inside 03_github_repository/ (the folder containing README.md,
# LICENSE and code/). Requires git and the GitHub CLI (gh). Install gh from
# https://cli.github.com and run `gh auth login` once beforehand.

set -euo pipefail

REPO_NAME="${1:-arabic-genai-breakdowns}"

# --- sanity checks ----------------------------------------------------------
for f in README.md LICENSE CITATION.cff code data probes results; do
  [ -e "$f" ] || { echo "ERROR: $f not found. Run this from inside 03_github_repository/." >&2; exit 1; }
done
command -v git >/dev/null || { echo "ERROR: git is not installed." >&2; exit 1; }
command -v gh  >/dev/null || { echo "ERROR: the GitHub CLI (gh) is not installed. See https://cli.github.com" >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "ERROR: not logged in. Run: gh auth login" >&2; exit 1; }

USER_LOGIN=$(gh api user --jq .login)

echo "Publishing as $USER_LOGIN -> $USER_LOGIN/$REPO_NAME (public)"
read -r -p "The survey data and all results will become publicly visible. Continue? [y/N] " ok
[ "$ok" = "y" ] || [ "$ok" = "Y" ] || { echo "Aborted."; exit 1; }

# --- fill in the repository path in CITATION.cff ----------------------------
if grep -q "USERNAME/REPOSITORY" CITATION.cff; then
  sed -i.bak "s|USERNAME/REPOSITORY|$USER_LOGIN/$REPO_NAME|g" CITATION.cff
  rm -f CITATION.cff.bak
  echo "CITATION.cff: repository path set to $USER_LOGIN/$REPO_NAME"
fi

# --- commit and push --------------------------------------------------------
if [ ! -d .git ]; then
  git init -q
  git branch -M main
fi
git add -A
git commit -q -m "Data, code and evaluation suite for the Arabic generative-AI breakdown study" || \
  echo "Nothing new to commit."

gh repo create "$REPO_NAME" --public --source=. --push \
  --description "Learner-reported breakdowns and measured model failure in Arabic generative AI use: survey data, probe suite and analysis code"

URL="https://github.com/$USER_LOGIN/$REPO_NAME"
echo
echo "Published: $URL"
echo
echo "Next steps:"
echo "  1. Paste the data availability paragraph into SNAPP under Declaration -> Data Availability."
echo "  2. For a citable DOI, link the repo at https://zenodo.org/account/settings/github/"
echo "     then cut a release:  gh release create v1.0.0 --notes 'Version accompanying the published paper'"
echo "     Zenodo mints a DOI for the release; put that DOI in the paper, not the bare GitHub URL."
