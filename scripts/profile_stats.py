#!/usr/bin/env python3
"""Draw the profile stats card: activity tiles plus every language used.

Writes assets/stats.svg (desktop) and assets/stats-mobile.svg (larger text,
swapped in on phones by the README). Languages are weighted by commits in
the last 12 months, per repository primary language.

    GITHUB_TOKEN=... python3 scripts/profile_stats.py [username]
"""
import datetime
import html
import json
import os
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
USER = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GITHUB_USER", "quincarter")

QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    repositoriesContributedTo(
      contributionTypes: [COMMIT, PULL_REQUEST, ISSUE, REPOSITORY]
      includeUserRepositories: true
    ) { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      totalIssueContributions
      contributionCalendar { totalContributions }
      commitContributionsByRepository(maxRepositories: 100) {
        repository { primaryLanguage { name color } }
        contributions { totalCount }
      }
    }
  }
}
"""

# Neural Pulse Lattice palette (matches assets/hero.svg)
BG, CARD, EDGE = "#050810", "#0a1222", "#1a2a4a"
BLUE, CREAM, MUTED = "#4fbcff", "#fef3c7", "#a5b4cf"
MONO = "'JetBrains Mono','IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
FALLBACK = "#4a5670"

DESKTOP = dict(W=1200, pad=24, tile_cols=5, lang_cols=2, gap=16, value=40, label=17,
               section=16, lang=20, row=40, tile_h=110)
MOBILE = dict(W=600, pad=20, tile_cols=2, lang_cols=1, gap=14, value=40, label=17,
              section=16, lang=20, row=42, tile_h=108)


def fetch(user):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN is required for the GraphQL API")
    body = json.dumps({"query": QUERY, "variables": {"login": user}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"Bearer {token}", "User-Agent": "profile-stats"},
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        data = json.load(res)
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]


def summarize(u):
    c = u["contributionsCollection"]
    years = (datetime.datetime.now(datetime.timezone.utc)
             - datetime.datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00"))).days // 365
    langs = {}
    for item in c["commitContributionsByRepository"]:
        lang = item["repository"]["primaryLanguage"]
        if lang:
            name = lang["name"]
            count, _ = langs.get(name, (0, None))
            langs[name] = (count + item["contributions"]["totalCount"], lang.get("color") or FALLBACK)
    return {
        "recent": [
            ("contributions", c["contributionCalendar"]["totalContributions"]),
            ("commits", c["totalCommitContributions"]),
            ("pull requests", c["totalPullRequestContributions"]),
            ("reviews", c["totalPullRequestReviewContributions"]),
            ("issues", c["totalIssueContributions"]),
        ],
        "all_time": [
            ("pull requests", u["pullRequests"]["totalCount"]),
            ("issues", u["issues"]["totalCount"]),
            ("contributed to", u["repositoriesContributedTo"]["totalCount"]),
            ("followers", u["followers"]["totalCount"]),
            ("years on github", years),
        ],
        "languages": sorted(((n, cnt, col) for n, (cnt, col) in langs.items()), key=lambda t: (-t[1], t[0])),
    }


def render(s, L):
    W, pad, gap = L["W"], L["pad"], L["gap"]
    body = []  # drawn first; wrapped in the <svg> header once the height is known
    a = body.append
    y = pad

    def section(title, y):
        a(f'<text x="{pad}" y="{y + L["section"]}" font-size="{L["section"]}" letter-spacing="3" fill="{MUTED}">'
          f"{html.escape(title.upper())}</text>")
        return y + L["section"] + 16

    def tiles(items, y):
        cols = L["tile_cols"]
        tw = (W - 2 * pad - (cols - 1) * gap) / cols
        for i, (label, value) in enumerate(items):
            tx = pad + (i % cols) * (tw + gap)
            ty = y + (i // cols) * (L["tile_h"] + gap)
            # a lone tile on the last row stretches across the full width
            w = W - 2 * pad if i == len(items) - 1 and i % cols == 0 and cols > 1 else tw
            a(f'<rect x="{tx:.1f}" y="{ty:.1f}" width="{w:.1f}" height="{L["tile_h"]}" rx="10" fill="{CARD}" stroke="{EDGE}"/>')
            a(f'<text x="{tx + 20:.1f}" y="{ty + 22 + L["value"]:.1f}" font-size="{L["value"]}" fill="{CREAM}">{value:,}</text>')
            a(f'<text x="{tx + 20:.1f}" y="{ty + L["tile_h"] - 18:.1f}" font-size="{L["label"]}" letter-spacing="1" '
              f'fill="{MUTED}">{html.escape(label)}</text>')
        rows = -(-len(items) // cols)
        return y + rows * L["tile_h"] + (rows - 1) * gap + 28

    y = section("last 12 months", y)
    y = tiles(s["recent"], y)
    y = section("all time", y)
    y = tiles(s["all_time"], y)

    langs = s["languages"]
    total = sum(c for _, c, _ in langs) or 1
    wide = W >= 1000
    y = section(f"languages · by commits, last 12 months · {len(langs)} total" if wide
                else f"languages · {len(langs)} · by commits", y)
    cols = L["lang_cols"]
    cw = (W - 2 * pad - (cols - 1) * 32) / cols
    per_col = -(-len(langs) // cols) if langs else 0
    name_w = 14 * L["lang"] * 0.6          # room for names up to 14 characters
    pct_w = 5 * L["lang"] * 0.6
    for i, (name, count, color) in enumerate(langs):
        col, row = divmod(i, per_col) if per_col else (0, 0)
        lx = pad + col * (cw + 32)
        ly = y + row * L["row"]
        share = count / total
        a(f'<circle cx="{lx + 7:.1f}" cy="{ly + L["lang"] * 0.65:.1f}" r="6" fill="{color}"/>')
        label = name if len(name) <= 14 else name[:13] + "…"
        a(f'<text x="{lx + 22:.1f}" y="{ly + L["lang"]:.1f}" font-size="{L["lang"]}" fill="{CREAM}">{html.escape(label)}</text>')
        bx = lx + 22 + name_w + 10
        bw = cw - (bx - lx) - pct_w - 14
        bh = 10
        by = ly + L["lang"] * 0.65 - bh / 2
        a(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh}" rx="5" fill="{EDGE}"/>')
        a(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{max(bw * share, 3):.1f}" height="{bh}" rx="5" fill="{color}"/>')
        pct = f"{100 * share:.1f}%" if share < 0.1 else f"{round(100 * share)}%"
        a(f'<text x="{lx + cw:.1f}" y="{ly + L["lang"]:.1f}" font-size="{L["lang"]}" text-anchor="end" fill="{MUTED}">{pct}</text>')
    y += per_col * L["row"]
    H = int(y + pad)

    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
             f'aria-label="GitHub activity stats and {len(langs)} languages used">')
    o.append(f"<style>text{{font-family:{MONO}}}</style>")
    o.append(f'<rect width="{W}" height="{H}" rx="10" fill="{BG}"/>')
    o.extend(body)
    o.append("</svg>")
    return "\n".join(o)


def main():
    stats = summarize(fetch(USER))
    for name, layout in (("stats.svg", DESKTOP), ("stats-mobile.svg", MOBILE)):
        out = ROOT / "assets" / name
        out.write_text(render(stats, layout))
        print(f"wrote {out.relative_to(ROOT)}: {len(stats['languages'])} languages")


if __name__ == "__main__":
    main()
