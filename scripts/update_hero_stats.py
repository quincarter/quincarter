#!/usr/bin/env python3
"""Refresh the live numbers in assets/hero.svg and README.md.

Pulls public repo count, follower count, and total stars (across public,
non-fork repos) from the GitHub API. Set GITHUB_TOKEN to avoid the
unauthenticated rate limit.

    python3 scripts/update_hero_stats.py [username]
"""
import json
import os
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
USER = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GITHUB_USER", "quincarter")


def get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "hero-stats"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.load(res)


def total_stars(user):
    stars, page = 0, 1
    while True:
        repos = get(f"https://api.github.com/users/{user}/repos?per_page=100&type=owner&page={page}")
        stars += sum(r["stargazers_count"] for r in repos if not r["fork"])
        if len(repos) < 100:
            return stars
        page += 1


def sub(text, pattern, value, path):
    new, n = re.subn(pattern, lambda m: f"{m.group(1)}{value}{m.group(2)}", text)
    if n == 0:
        sys.exit(f"pattern not found in {path}: {pattern}")
    return new


def main():
    profile = get(f"https://api.github.com/users/{USER}")
    stats = {
        "repos": profile["public_repos"],
        "followers": profile["followers"],
        "stars": total_stars(USER),
    }
    print(stats)

    hero = ROOT / "assets" / "hero.svg"
    svg = hero.read_text()
    for key, value in stats.items():
        svg = sub(svg, rf'(<text id="stat-{key}"[^>]*>)[^<]*(</text>)', value, hero)
    hero.write_text(svg)

    readme = ROOT / "README.md"
    md = readme.read_text()
    md = sub(md, r"(badge/)\d+(_public_repos-)", stats["repos"], readme)
    md = sub(md, r"(alt=\")\d+( public repos\")", stats["repos"], readme)
    md = sub(md, r"(\[)\d+( public repos\]\(https://github\.com/[^)]*\) · )", stats["repos"], readme)
    md = sub(md, r"( · )\d+( followers\n)", stats["followers"], readme)
    readme.write_text(md)


if __name__ == "__main__":
    main()
