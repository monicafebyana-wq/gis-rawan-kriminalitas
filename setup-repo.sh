#!/usr/bin/env bash
# Pakai: ./setup-repo.sh <username-github-dhea>
# Syarat: sudah install Git + GitHub CLI (gh) dan sudah `gh auth login` sebagai Monica.
set -e
REPO="gis-rawan-kriminalitas"
PARTNER="${1:?Usage: ./setup-repo.sh <username-github-dhea>}"

gh auth status
OWNER=$(gh api user -q .login)

git init -b main
git add .
git commit -m "chore: initial project structure and README"

# 1) Repo private + push
gh repo create "$REPO" --private --source=. --remote=origin --push

# 2) Invite partner (akses write)
gh api -X PUT "repos/$OWNER/$REPO/collaborators/$PARTNER" -f permission=push

# 3) Proteksi branch main: wajib PR + 1 approval
gh api -X PUT "repos/$OWNER/$REPO/branches/main/protection" --input - << JSON || \
  echo "!! Proteksi branch gagal. Repo private di akun GitHub Free tidak mendukungnya (butuh Pro/Student Pack)."
{
  "required_status_checks": null,
  "enforce_admins": true,
  "required_pull_request_reviews": { "required_approving_review_count": 1 },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON

echo "Selesai. Repo: https://github.com/$OWNER/$REPO - Dhea perlu menerima undangan (cek email/notifikasi GitHub)."
