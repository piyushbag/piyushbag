#!/usr/bin/env python3
"""Generate profile README from profile/config.yaml and live GitHub PR search."""

from __future__ import annotations

import json
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "profile" / "config.yaml"
SNAPSHOT_PATH = ROOT / "profile" / "pr-snapshot.json"
README_PATH = ROOT / "README.md"
_star_cache: dict[str, int] = {}


def gh_json(args: list[str]) -> list | dict | None:
    result = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(result.stderr.strip(), file=sys.stderr)
        return None
    return json.loads(result.stdout or "null")


def load_config() -> dict:
    if yaml is None:
        raise SystemExit("PyYAML required: pip install pyyaml")
    with CONFIG_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise SystemExit(f"Invalid config: {CONFIG_PATH}")
    return data


def fetch_prs(author: str, limit: int) -> list[dict]:
    data = gh_json(
        [
            "search",
            "prs",
            f"--author={author}",
            f"--limit={limit}",
            "--json",
            "repository,title,number,state,url,updatedAt",
            "--sort",
            "updated",
            "--order",
            "desc",
        ]
    )
    return data if isinstance(data, list) else []


def repo_stars(repo: str) -> int:
    if repo in _star_cache:
        return _star_cache[repo]
    data = gh_json(["api", f"repos/{repo}", "--jq", ".stargazers_count"])
    stars = int(data) if isinstance(data, int) else 0
    _star_cache[repo] = stars
    return stars


def pr_recent_enough(config: dict, pr: dict) -> bool:
    since = config.get("contributing_since")
    if not since:
        return True
    updated = pr.get("updatedAt")
    if not updated:
        return True
    try:
        cutoff = datetime.fromisoformat(str(since))
        touched = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        return touched.date() >= cutoff.date()
    except ValueError:
        return True


def display_name(config: dict, repo: str) -> str:
    names = config.get("display_names") or {}
    if repo in names:
        return names[repo]
    slug = repo.split("/", 1)[-1]
    return slug.replace("-", " ").replace("_", " ").title()


def should_include_repo(config: dict, repo: str) -> bool:
    exclude_repos = set(config.get("contributing_exclude_repos") or [])
    if repo in exclude_repos:
        return False
    owner = repo.split("/", 1)[0]
    exclude_owners = set(config.get("contributing_exclude_owners") or [])
    return owner not in exclude_owners


def format_pr(pr: dict) -> str:
    num = pr["number"]
    url = pr["url"]
    title = pr["title"].strip()
    state = (pr.get("state") or "").lower()
    suffix = " merged" if state == "merged" else ""
    return f"{title} ([#{num}]({url}){suffix})"


def build_contributing_lines(config: dict, prs: list[dict]) -> list[str]:
    by_repo: dict[str, list[dict]] = defaultdict(list)
    for pr in prs:
        repo = pr["repository"]["nameWithOwner"]
        if should_include_repo(config, repo) and pr_recent_enough(config, pr):
            by_repo[repo].append(pr)

    lines: list[str] = []
    for repo in sorted(by_repo, key=lambda r: (-repo_stars(r), r.lower())):
        name = display_name(config, repo)
        stars = repo_stars(repo)
        repo_prs = sorted(by_repo[repo], key=lambda p: p["number"])
        pr_text = ", ".join(format_pr(p) for p in repo_prs)
        lines.append(
            f"- **[{name}](https://github.com/{repo})** "
            f"[![GitHub stars](https://img.shields.io/github/stars/{repo}?style=flat&color=gold)](https://github.com/{repo}) "
            f"- {pr_text}"
        )
    return lines


def build_tagline(config: dict, prs: list[dict]) -> str:
    building = config.get("building") or []
    if not building:
        return config["role"]["tagline"]

    first = building[0]["repo"]
    stars = repo_stars(first)
    parts = [f"[{first.split('/')[-1]}](https://github.com/{first}) {stars}★"]

    merged_upstream = [
        p
        for p in prs
        if (p.get("state") or "").lower() == "merged"
        and should_include_repo(config, p["repository"]["nameWithOwner"])
    ]
    if merged_upstream:
        top = merged_upstream[0]
        repo = top["repository"]["nameWithOwner"]
        label = display_name(config, repo)
        parts.append(
            f"[{label}]({top['url']}) merged"
        )

    open_upstream = [
        p
        for p in prs
        if (p.get("state") or "").lower() == "open"
        and should_include_repo(config, p["repository"]["nameWithOwner"])
    ]
    if open_upstream:
        top = open_upstream[0]
        label = display_name(config, top["repository"]["nameWithOwner"])
        parts.append(f"[{label}]({top['url']}) in flight")

    return " · ".join(parts)


def build_readme(config: dict, prs: list[dict]) -> str:
    role = config["role"]
    social = config["social"]
    writing = config["writing"]
    today = date.today().isoformat()

    building_lines = []
    for item in config.get("building") or []:
        repo = item["repo"]
        desc = item["description"]
        building_lines.append(
            f"- **[{repo.split('/')[-1]}](https://github.com/{repo})** "
            f"[![GitHub stars](https://img.shields.io/github/stars/{repo}?style=flat&color=gold)](https://github.com/{repo}) "
            f"- {desc}"
        )

    contributing_lines = build_contributing_lines(config, prs)
    tagline_highlights = build_tagline(config, prs)

    return f"""### Hey, I'm Piyush Bag

[![Blog](https://img.shields.io/badge/Blog-piyushbag.com-FF5722?style=flat&logo=google-chrome&logoColor=white)]({social['blog']}) [![LinkedIn](https://img.shields.io/badge/LinkedIn-piyushbag-0A66C2?style=flat&logo=linkedin)]({social['linkedin']}) [![X @piyushbagitall](https://img.shields.io/badge/X-@piyushbagitall-000?style=flat&logo=x)]({social['x']})

Test automation engineer at [{role['company']}]({role['company_url']}). {role['tagline']} Open source: {tagline_highlights}

#### Building

{chr(10).join(building_lines)}

#### Contributing to

{chr(10).join(contributing_lines) if contributing_lines else "- *No upstream PRs found yet — check back after the next sync.*"}

#### Writing

{writing['text']}: [{writing['url'].replace('https://', '')}]({writing['url']})

*Last updated: {today}*

<!-- Generated by scripts/generate_profile_readme.py — do not edit by hand; change profile/config.yaml or merge upstream PRs. -->
"""


def write_snapshot(prs: list[dict]) -> None:
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": date.today().isoformat(),
        "author": "piyushbag",
        "pull_requests": prs,
    }
    SNAPSHOT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    config = load_config()
    author = config.get("author", "piyushbag")
    limit = int(config.get("pr_search_limit", 100))

    prs = fetch_prs(author, limit)
    if prs is None:
        return 1

    write_snapshot(prs)
    readme = build_readme(config, prs)

    if README_PATH.exists() and README_PATH.read_text(encoding="utf-8") == readme:
        print("README.md unchanged")
        return 0

    README_PATH.write_text(readme, encoding="utf-8")
    print(f"README.md updated ({len(prs)} PRs scanned, {len(build_contributing_lines(config, prs))} upstream repos)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
