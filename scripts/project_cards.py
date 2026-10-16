#!/usr/bin/env python3
"""Draw one card per featured project and link each one from the README.

GitHub shows SVGs as plain images, so links inside an SVG never work. Each
card is therefore its own image, wrapped in a link to its repo:

    assets/cards/<repo>.svg          desktop (full width)
    assets/cards/<repo>-mobile.svg   phones (larger text), via <picture>

The README block between the `featured-cards` markers is regenerated from
FEATURED, so editing that list is all it takes to change the cards.

    python3 scripts/project_cards.py [username]
"""
import html
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from update_hero_stats import get  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
USER = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GITHUB_USER", "quincarter")
RAW = "https://raw.githubusercontent.com/{user}/{user}/main/"

FEATURED = [
    "marvel-champions-digital-game",
    "component-library-starter",
    "document-viewer-web-component",
    "ClaudeUsage-MacOS-App-Widget",
    "brew-me-app-lit",
    "dnd-syncer",
]

# Neural Pulse Lattice palette (matches assets/hero.svg)
BG, EDGE = "#0a1222", "#1a2a4a"
BLUE, CREAM, MUTED = "#4fbcff", "#fef3c7", "#a5b4cf"
MONO = "'JetBrains Mono','IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
CHAR = 0.6  # monospace advance width, in em

# GitHub's language colours, so the dots read the same as on github.com
LANG_COLORS = {
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Python": "#3572a5", "Kotlin": "#a97bff",
    "Swift": "#f05138", "HTML": "#e34c26", "CSS": "#663399", "Shell": "#89e051", "Go": "#00add8",
    "Rust": "#dea584", "Java": "#b07219", "Dart": "#00b4ab", "Dockerfile": "#384d54", "Vue": "#41b883",
    "SCSS": "#c6538c", "C#": "#178600", "Astro": "#ff5a03", "MDX": "#fcb32c",
}
OTHER = "#4a5670"

DESKTOP = dict(W=1200, pad=30, name=28, desc=21, meta=20, lines=2)
MOBILE = dict(W=600, pad=26, name=26, desc=21, meta=20, lines=4)

START, END = "<!-- featured-cards:start -->", "<!-- featured-cards:end -->"


def fetch(user):
    repos, page = [], 1
    while True:
        batch = get(f"https://api.github.com/users/{user}/repos?per_page=100&type=owner&page={page}")
        repos += batch
        if len(batch) < 100:
            return {r["name"]: r for r in repos if not r["fork"]}
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


def render(r, L):
    W, pad = L["W"], L["pad"]
    desc_lh = L["desc"] * 1.45
    H = int(pad + L["name"] + 18 + L["lines"] * desc_lh + 24 + L["meta"] + pad)
    o = []
    a = o.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
      f'aria-label="{html.escape(r["name"])}: {html.escape(r.get("description") or "")}">')
    a(f"<style>text{{font-family:{MONO}}}</style>")
    a(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="12" fill="{BG}" stroke="{EDGE}" stroke-width="2"/>')

    # name, plus an arrow that says "this opens something" (the README links the image)
    arrow = L["name"]
    name = r["name"]
    max_name = int((W - 2 * pad - arrow * 1.5) / (L["name"] * CHAR))
    if len(name) > max_name:
        name = name[: max_name - 1] + "…"
    y = pad + L["name"]
    a(f'<text x="{pad}" y="{y}" font-size="{L["name"]}" fill="{BLUE}">{html.escape(name)}</text>')
    a(f'<text x="{W - pad}" y="{y}" font-size="{arrow}" text-anchor="end" fill="{MUTED}">↗</text>')

    y += 18
    wrap_chars = int((W - 2 * pad) / (L["desc"] * CHAR))
    for line in wrap(r.get("description") or "", wrap_chars, L["lines"]):
        y += desc_lh
        a(f'<text x="{pad}" y="{y:.1f}" font-size="{L["desc"]}" fill="{MUTED}">{html.escape(line)}</text>')

    my = H - pad
    lang = r.get("language") or "—"
    a(f'<circle cx="{pad + 7}" cy="{my - L["meta"] * 0.35:.1f}" r="7" fill="{LANG_COLORS.get(lang, OTHER)}"/>')
    meta = f'{html.escape(lang)}   ★ {r["stargazers_count"]}   ⑂ {r["forks_count"]}'
    a(f'<text x="{pad + 24}" y="{my}" font-size="{L["meta"]}" fill="{CREAM}" xml:space="preserve">{meta}</text>')
    a("</svg>")
    return "\n".join(o)


def readme_block(user, names):
    raw = RAW.format(user=user)
    parts = [START]
    for n in names:
        parts.append(
            f'<a href="https://github.com/{user}/{n}">\n'
            f"<picture>\n"
            f'  <source media="(max-width: 700px)" srcset="{raw}assets/cards/{n}-mobile.svg" />\n'
            f'  <img src="assets/cards/{n}.svg" alt="{n}" width="100%" />\n'
            f"</picture>\n"
            f"</a>"
        )
    parts.append(END)
    # blank lines make each linked card its own block, so GitHub spaces them apart
    return "\n\n".join(parts)


def main():
    repos = fetch(USER)
    names = [n for n in FEATURED if n in repos]
    out_dir = ROOT / "assets" / "cards"
    out_dir.mkdir(parents=True, exist_ok=True)
    for n in names:
        (out_dir / f"{n}.svg").write_text(render(repos[n], DESKTOP))
        (out_dir / f"{n}-mobile.svg").write_text(render(repos[n], MOBILE))
    # drop cards for repos no longer featured
    for f in out_dir.glob("*.svg"):
        if f.name.removesuffix(".svg").removesuffix("-mobile") not in names:
            f.unlink()

    readme = ROOT / "README.md"
    text = readme.read_text()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if pattern.search(text):
        readme.write_text(pattern.sub(lambda _: readme_block(USER, names), text))
    else:
        print("README has no featured-cards markers; cards drawn but not linked")
    print(f"wrote {len(names)} cards")


if __name__ == "__main__":
    main()
