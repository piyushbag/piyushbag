#!/usr/bin/env python3
"""Refresh profile README: last-updated date, star counts, PR merge labels."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

README = Path("README.md")
PR_URL = re.compile(r"https://github\.com/(?P<repo>[^/]+/[^/]+)/pull/(?P<num>\d+)")
LAST_UPDATED = re.compile(r"\*Last updated: \d{4}-\d{2}-\d{2}\*")
STAR_COUNT = re.compile(r"(awesome-pcb-workflow\][^\n]*?) \d+★")


def gh_json(args: list[str]) -> dict | list | None:
    result = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None
    return json.loads(result.stdout or "null")


def pr_merged(repo: str, number: str) -> bool | None:
    data = gh_json(["api", f"repos/{repo}/pulls/{number}", "--jq", ".merged"])
    return data if isinstance(data, bool) else None


def repo_stars(repo: str) -> int | None:
    data = gh_json(["api", f"repos/{repo}", "--jq", ".stargazers_count"])
    return data if isinstance(data, int) else None


def mark_merged_pr_links(content: str) -> str:
    lines: list[str] = []
    for line in content.splitlines():
        updated = line
        for match in PR_URL.finditer(line):
            repo = match.group("repo")
            num = match.group("num")
            url = match.group(0)
            window = line[match.start() : min(len(line), match.end() + 12)]
            if " merged" in window:
                continue
            merged = pr_merged(repo, num)
            if merged:
                needle = f"([#{num}]({url}))"
                replacement = f"([#{num}]({url}) merged)"
                if needle in updated and replacement not in updated:
                    updated = updated.replace(needle, replacement, 1)
        lines.append(updated)
    return "\n".join(lines)


def refresh_star_count(content: str) -> str:
    stars = repo_stars("piyushbag/awesome-pcb-workflow")
    if stars is None:
        return content
    return STAR_COUNT.sub(rf"\g<1> {stars}★", content, count=1)


def refresh_last_updated(content: str) -> str:
    today = date.today().isoformat()
    if LAST_UPDATED.search(content):
        return LAST_UPDATED.sub(f"*Last updated: {today}*", content)
    return content + f"\n\n*Last updated: {today}*"


def main() -> int:
    if not README.exists():
        print("README.md not found", file=sys.stderr)
        return 1

    original = README.read_text(encoding="utf-8")
    updated = refresh_last_updated(refresh_star_count(mark_merged_pr_links(original)))

    if updated != original:
        README.write_text(updated, encoding="utf-8")
        print("README.md updated")
        return 0

    print("README.md unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
