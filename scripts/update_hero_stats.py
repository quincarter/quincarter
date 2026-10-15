#!/usr/bin/env python3
"""Refresh the live numbers in assets/hero.svg and README.md.

Pulls public repo count, follower count, and total stars (across public,
non-fork repos) from the GitHub API, and sorts the README projects table
by star count, most-starred first. Set GITHUB_TOKEN to avoid the
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


def repo_stars(user):
    """Map of repo name -> star count for the user's own public repos."""
    stars, page = {}, 1
    while True:
        repos = get(f"https://api.github.com/users/{user}/repos?per_page=100&type=owner&page={page}")
        stars.update({r["name"]: r["stargazers_count"] for r in repos if not r["fork"]})
        if len(repos) < 100:
            return stars
        page += 1


ROW = re.compile(r"^\|.*?\]\(https://github\.com/[^/]+/([^)/]+)\)")


def sort_projects(md, stars):
    """Sort each run of project table rows by stars, descending.

    Ties keep their current order; repos the API doesn't know sink to the bottom.
    """
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        if not ROW.match(lines[i]):
            i += 1
            continue
        j = i
        while j < len(lines) and ROW.match(lines[j]):
            j += 1
        lines[i:j] = sorted(lines[i:j], key=lambda line: -stars.get(ROW.match(line).group(1), -1))
        i = j
    return "\n".join(lines)


def sub(text, pattern, value, path, required=True):
    new, n = re.subn(pattern, lambda m: f"{m.group(1)}{value}{m.group(2)}", text)
    if n == 0:
        if required:
            sys.exit(f"pattern not found in {path}: {pattern}")
        print(f"skipped (not in {path.name}): {pattern}")
    return new


def main():
    profile = get(f"https://api.github.com/users/{USER}")
    stats = {
        "repos": profile["public_repos"],
        "followers": profile["followers"],
    }
    stars = repo_stars(USER)
    stats["stars"] = sum(stars.values())
    print(stats)

    hero = ROOT / "assets" / "hero.svg"
    svg = hero.read_text()
    for key, value in stats.items():
        svg = sub(svg, rf'(<text id="stat-{key}"[^>]*>)[^<]*(</text>)', value, hero)
    hero.write_text(svg)

    readme = ROOT / "README.md"
    md = readme.read_text()
    # README mentions are optional so editing the README never breaks the run
    md = sub(md, r"(badge/)\d+(_public_repos-)", stats["repos"], readme, required=False)
    md = sub(md, r"(alt=\")\d+( public repos\")", stats["repos"], readme, required=False)
    md = sub(md, r"(\[)\d+( public repos\]\(https://github\.com/[^)]*\) · )", stats["repos"], readme, required=False)
    md = sub(md, r"( · )\d+( followers\n)", stats["followers"], readme, required=False)
    md = sort_projects(md, stars)
    readme.write_text(md)


if __name__ == "__main__":
    main()
