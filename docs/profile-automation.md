# Profile README automation

Your GitHub profile README is **generated**, not hand-edited. Two cloud layers keep it current.

## What runs where

| Layer | Runs on | Mac 24/7? | Purpose |
|-------|---------|-----------|---------|
| **GitHub Actions** | GitHub cloud | No | Daily PR sync at 09:00 PT; opens bot PR; Mergify merges |
| **Cursor Automation** | Cursor cloud | No | Same generator; optional agent pass for config/README polish |

## Source of truth

| File | Role |
|------|------|
| `profile/config.yaml` | Building repos, display names, exclude own-repo PRs from Contributing |
| `scripts/generate_profile_readme.py` | Fetches PRs via `gh`, writes `README.md` + `profile/pr-snapshot.json` |
| `README.md` | Generated output (shown on github.com/piyushbag) |

## Contributing section logic

1. Search up to 100 PRs authored by `piyushbag` (sorted by recently updated).
2. **Exclude** PRs to your own repos (`piyushbag/*`) — those belong in **Building**, not upstream contributions.
3. Group by **GitHub org** → **repo** → **PR** (three levels: org bullet, nested repo + star badge, nested PR lines with 4-space indent).

Star badges use static counts from `gh` at generate time (`badge/stars-N-gold`). Avoid dynamic `github/stars` shields URLs; they often render as `invalid` on profile READMEs.

## Manual run

```bash
pip install -r profile/requirements.txt
gh auth status
python3 scripts/generate_profile_readme.py
git diff README.md profile/pr-snapshot.json
```

## Cursor Automation

Import or enable **Profile README daily refresh** (cron `0 16 * * *` = 09:00 PT). The cloud agent checks out `piyushbag/piyushbag`, runs the generator, and opens a PR when the diff is non-empty. Template: `.cursor/automation-profile-readme.json`.

## Customize

- Add display names: `profile/config.yaml` → `display_names`
- Add Building repos: `profile/config.yaml` → `building`
- Exclude a fork mirror: `contributing_exclude_repos`
