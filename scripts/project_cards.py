#!/usr/bin/env python3
"""Draw the featured project cards and language bar.

Writes assets/projects.svg (two-column grid) and assets/projects-mobile.svg
(one column, larger text, swapped in on phones by the README). Languages
are counted by each repo's primary language, so no special token is needed.

    python3 scripts/project_cards.py [username]
"""
import html
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from update_hero_stats import get  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
USER = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GITHUB_USER", "quincarter")

FEATURED = [
    "marvel-champions-digital-game",
    "component-library-starter",
    "document-viewer-web-component",
    "ClaudeUsage-MacOS-App-Widget",
    "brew-me-app-lit",
    "dnd-syncer",
]

# Neural Pulse Lattice palette (matches assets/hero.svg)
BG, CARD, EDGE = "#050810", "#0a1222", "#1a2a4a"
BLUE, CREAM, MUTED = "#4fbcff", "#fef3c7", "#a5b4cf"
MONO = "'JetBrains Mono','IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
CHAR = 0.6  # monospace advance width, in em

# GitHub's language colours, so the dots read the same as on github.com
LANG_COLORS = {
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Python": "#3572a5", "Kotlin": "#a97bff",
    "Swift": "#f05138", "HTML": "#e34c26", "CSS": "#663399", "Shell": "#89e051", "Go": "#00add8",
    "Rust": "#dea584", "Java": "#b07219", "Dart": "#00b4ab", "Dockerfile": "#384d54", "Vue": "#41b883",
    "SCSS": "#c6538c", "C#": "#178600", "Astro": "#ff5a03",
}
OTHER = "#4a5670"

DESKTOP = dict(W=1200, pad=24, cols=2, gap=24, name=20, desc=15, meta=14, lines=3,
               bar_title=13, legend=14, card_pad=22)
MOBILE = dict(W=600, pad=20, cols=1, gap=18, name=26, desc=19, meta=18, lines=3,
              bar_title=16, legend=18, card_pad=22)


def fetch(user):
    repos, page = [], 1
    while True:
        batch = get(f"https://api.github.com/users/{user}/repos?per_page=100&type=owner&page={page}")
        repos += batch
        if len(batch) < 100:
            return [r for r in repos if not r["fork"]]
        page += 1


def wrap(text, width, max_lines):
    """Greedy word wrap to `width` characters, ellipsising past `max_lines`."""
    lines, line = [], ""
    for word in text.split():
        if len(line) + len(word) + (1 if line else 0) <= width:
            line = f"{line} {word}" if line else word
        else:
            lines.append(line)
            line = word[:width]
    if line:
        lines.append(line)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: width - 1].rstrip() + "…"
    return lines


def language_counts(repos):
    counts = {}
    for r in repos:
        if r.get("language") and not r.get("archived"):
            counts[r["language"]] = counts.get(r["language"], 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


def render(repos, L):
    W, pad, cols, gap, cp = L["W"], L["pad"], L["cols"], L["gap"], L["card_pad"]
    by_name = {r["name"]: r for r in repos}
    cards = [by_name[n] for n in FEATURED if n in by_name]
    o = []
    a = o.append

    # language bar: top five languages by repo count, the rest grouped as "other"
    langs = language_counts(repos)
    total = sum(c for _, c in langs) or 1
    top = langs[:5]
    rest = total - sum(c for _, c in top)
    segments = [(n, c, LANG_COLORS.get(n, OTHER)) for n, c in top] + ([("other", rest, OTHER)] if rest else [])

    bar_y = pad + L["bar_title"] + 14
    bar_h = 12
    # legend wraps onto as many rows as it needs
    legend_rows, row, row_w = [], [], 0
    for name, count, color in segments:
        label = f"{name} {round(100 * count / total)}%"
        w = 22 + len(label) * L["legend"] * CHAR + 26
        if row and row_w + w > W - 2 * pad:
            legend_rows.append(row)
            row, row_w = [], 0
        row.append((label, color, row_w))
        row_w += w
    legend_rows.append(row)
    legend_y = bar_y + bar_h + L["legend"] + 14
    grid_y = legend_y + (len(legend_rows) - 1) * (L["legend"] + 12) + 30

    card_w = (W - 2 * pad - (cols - 1) * gap) / cols
    wrap_chars = int((card_w - 2 * cp) / (L["desc"] * CHAR))
    desc_lh = L["desc"] * 1.45
    card_h = cp + L["name"] + 14 + L["lines"] * desc_lh + 22 + L["meta"] + cp
    rows = -(-len(cards) // cols)
    H = int(grid_y + rows * card_h + (rows - 1) * gap + pad)

    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
      f'aria-label="Featured projects and languages used across {len(repos)} repositories">')
    a(f"<style>text{{font-family:{MONO}}}</style>")
    a(f'<rect width="{W}" height="{H}" rx="10" fill="{BG}"/>')

    a(f'<text x="{pad}" y="{pad + L["bar_title"]}" font-size="{L["bar_title"]}" letter-spacing="3" fill="{MUTED}">'
      f"LANGUAGES · {len(repos)} REPOS</text>")
    x = pad
    a(f'<clipPath id="bar"><rect x="{pad}" y="{bar_y}" width="{W - 2 * pad}" height="{bar_h}" rx="6"/></clipPath>')
    a('<g clip-path="url(#bar)">')
    for name, count, color in segments:
        w = (W - 2 * pad) * count / total
        a(f'<rect x="{x:.1f}" y="{bar_y}" width="{w:.1f}" height="{bar_h}" fill="{color}"/>')
        x += w
    a("</g>")
    for r, row in enumerate(legend_rows):
        y = legend_y + r * (L["legend"] + 12)
        for label, color, dx in row:
            a(f'<circle cx="{pad + dx + 7}" cy="{y - L["legend"] * 0.35:.1f}" r="6" fill="{color}"/>')
            a(f'<text x="{pad + dx + 20}" y="{y}" font-size="{L["legend"]}" fill="{CREAM}">{html.escape(label)}</text>')

    for i, r in enumerate(cards):
        cx = pad + (i % cols) * (card_w + gap)
        cy = grid_y + (i // cols) * (card_h + gap)
        a("<g>")
        a(f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{card_w:.1f}" height="{card_h:.1f}" rx="10" fill="{CARD}" stroke="{EDGE}"/>')
        name = r["name"]
        max_name = int((card_w - 2 * cp) / (L["name"] * CHAR))
        if len(name) > max_name:
            name = name[: max_name - 1] + "…"
        ty = cy + cp + L["name"]
        a(f'<text x="{cx + cp:.1f}" y="{ty:.1f}" font-size="{L["name"]}" fill="{BLUE}">{html.escape(name)}</text>')
        ty += 14
        for line in wrap(r.get("description") or "", wrap_chars, L["lines"]):
            ty += desc_lh
            a(f'<text x="{cx + cp:.1f}" y="{ty:.1f}" font-size="{L["desc"]}" fill="{MUTED}">{html.escape(line)}</text>')
        my = cy + card_h - cp
        lang = r.get("language") or "—"
        a(f'<circle cx="{cx + cp + 6:.1f}" cy="{my - L["meta"] * 0.35:.1f}" r="6" fill="{LANG_COLORS.get(lang, OTHER)}"/>')
        meta = f'{html.escape(lang)}   ★ {r["stargazers_count"]}   ⑂ {r["forks_count"]}'
        a(f'<text x="{cx + cp + 20:.1f}" y="{my:.1f}" font-size="{L["meta"]}" fill="{CREAM}" xml:space="preserve">{meta}</text>')
        a("</g>")
    a("</svg>")
    return "\n".join(o)


def main():
    repos = fetch(USER)
    for name, layout in (("projects.svg", DESKTOP), ("projects-mobile.svg", MOBILE)):
        out = ROOT / "assets" / name
        out.write_text(render(repos, layout))
        print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
