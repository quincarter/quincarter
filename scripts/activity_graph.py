#!/usr/bin/env python3
"""Draw assets/activity-graph.svg: daily contributions over the last 31 days.

Reads the contribution calendar from the GitHub GraphQL API, so GITHUB_TOKEN
must be set (any token works for public contributions).

    GITHUB_TOKEN=... python3 scripts/activity_graph.py [username]
"""
import datetime
import json
import os
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
USER = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GITHUB_USER", "quincarter")
DAYS = 31

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

# Neural Pulse Lattice palette (matches assets/hero.svg)
BG, GRID, EDGE = "#050810", "#0e1a30", "#1a2a4a"
BLUE, VIOLET, CREAM, MUTED, PULSE = "#4fbcff", "#a78bfa", "#fef3c7", "#a5b4cf", "#7ddbff"
MONO = "'JetBrains Mono','IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

W, H = 1200, 320
LEFT, RIGHT, TOP, BOTTOM = 70, 40, 80, 50


def fetch_days(user):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN is required for the GraphQL API")
    body = json.dumps({"query": QUERY, "variables": {"login": user}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"Bearer {token}", "User-Agent": "activity-graph"},
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        data = json.load(res)
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [(d["date"], d["contributionCount"]) for w in weeks for d in w["contributionDays"]]
    return days[-DAYS:]


def monotone_path(points):
    """Smooth path through points without overshooting (Fritsch-Carlson)."""
    n = len(points)
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    d = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(n - 1)]
    m = [d[0]] + [0 if d[i - 1] * d[i] <= 0 else (d[i - 1] + d[i]) / 2 for i in range(1, n - 1)] + [d[-1]]
    for i in range(n - 1):
        if d[i] == 0:
            m[i] = m[i + 1] = 0
        else:
            a, b = m[i] / d[i], m[i + 1] / d[i]
            s = a * a + b * b
            if s > 9:
                t = 3 / s ** 0.5
                m[i], m[i + 1] = t * a * d[i], t * b * d[i]
    out = [f"M{xs[0]:.1f} {ys[0]:.1f}"]
    for i in range(n - 1):
        h = (xs[i + 1] - xs[i]) / 3
        out.append(
            f"C{xs[i] + h:.1f} {ys[i] + m[i] * h:.1f} {xs[i + 1] - h:.1f} {ys[i + 1] - m[i + 1] * h:.1f} "
            f"{xs[i + 1]:.1f} {ys[i + 1]:.1f}"
        )
    return " ".join(out)


def nice_max(v):
    """Round the y-axis top up to a tidy number so gridlines land on integers."""
    for step in (1, 2, 5, 10, 20, 25, 50, 100):
        if v <= step * 4:
            return step * 4, step
    step = -(-v // 4)
    return step * 4, step


def render(days):
    counts = [c for _, c in days]
    total, peak = sum(counts), max(counts)
    ymax, ystep = nice_max(max(peak, 1))
    pw, ph = W - LEFT - RIGHT, H - TOP - BOTTOM
    x = lambda i: LEFT + pw * i / (len(days) - 1)
    y = lambda c: TOP + ph * (1 - c / ymax)
    pts = [(x(i), y(c)) for i, c in enumerate(counts)]
    line = monotone_path(pts)
    area = f"{line} L{pts[-1][0]:.1f} {TOP + ph} L{pts[0][0]:.1f} {TOP + ph} Z"
    start = datetime.date.fromisoformat(days[0][0])
    end = datetime.date.fromisoformat(days[-1][0])

    o = []
    a = o.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" '
      f'viewBox="0 0 {W} {H}" role="img" aria-label="{total} contributions over the last {DAYS} days">')
    a("<defs>")
    a(f'<linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{VIOLET}" stop-opacity="0.45"/>'
      f'<stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></linearGradient>')
    a(f'<linearGradient id="stroke" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{VIOLET}"/>'
      f'<stop offset="1" stop-color="{BLUE}"/></linearGradient>')
    a('<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.4" result="b"/>'
      '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    a(f'<path id="line" d="{line}"/>')
    a("</defs>")
    a(f"<style>text{{font-family:{MONO}}}"
      ".draw{stroke-dasharray:1;stroke-dashoffset:1;animation:draw 2.4s ease-out forwards}"
      ".rise{opacity:0;animation:rise .8s ease-out 1.6s forwards}"
      "@keyframes draw{to{stroke-dashoffset:0}}@keyframes rise{to{opacity:1}}</style>")
    a(f'<rect width="{W}" height="{H}" rx="8" fill="{BG}"/>')

    # header
    a(f'<text x="{LEFT}" y="40" font-size="20" letter-spacing="2" fill="{CREAM}">commit signals</text>')
    span = f"LAST {DAYS} DAYS · {start:%b %d} → {end:%b %d}".upper()
    a(f'<text x="{LEFT}" y="60" font-size="10" letter-spacing="3" fill="{MUTED}">{span}</text>')
    a(f'<text x="{W - RIGHT}" y="40" font-size="20" text-anchor="end" fill="{CREAM}">{total}</text>')
    a(f'<text x="{W - RIGHT}" y="60" font-size="10" letter-spacing="3" text-anchor="end" fill="{MUTED}">'
      f"CONTRIBUTIONS · PEAK {peak}/DAY</text>")

    # grid + y labels
    for v in range(0, ymax + 1, ystep):
        gy = y(v)
        a(f'<line x1="{LEFT}" y1="{gy:.1f}" x2="{W - RIGHT}" y2="{gy:.1f}" stroke="{GRID if v else EDGE}"/>')
        a(f'<text x="{LEFT - 14}" y="{gy + 4:.1f}" font-size="10" text-anchor="end" fill="{MUTED}">{v}</text>')
    # x labels every 5 days, plus the last day
    for i, (date, _) in enumerate(days):
        if i % 5 == 0 or i == len(days) - 1:
            d = datetime.date.fromisoformat(date)
            a(f'<text x="{x(i):.1f}" y="{H - 20}" font-size="10" text-anchor="middle" fill="{MUTED}">'
              f"{d:%b} {d.day}</text>")

    # area, line, points
    a(f'<path d="{area}" fill="url(#fill)" class="rise"/>')
    a(f'<use href="#line" xlink:href="#line" fill="none" stroke="url(#stroke)" stroke-width="2.5" '
      f'stroke-linejoin="round" stroke-linecap="round" pathLength="1" class="draw" filter="url(#glow)"/>')
    a('<g class="rise">')
    for (px, py), c in zip(pts, counts):
        if c:
            a(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.2" fill="{CREAM if c == peak else BLUE}"/>')
    a("</g>")

    # a signal pulse travelling along the line, like the hero lattice
    a(f'<circle r="4" fill="{PULSE}" filter="url(#glow)" opacity="0">'
      f'<animateMotion dur="6s" begin="2.4s" repeatCount="indefinite"><mpath href="#line" xlink:href="#line"/></animateMotion>'
      f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.05;0.9;1" dur="6s" begin="2.4s" repeatCount="indefinite"/>'
      "</circle>")
    a("</svg>")
    return "\n".join(o)


def main():
    days = fetch_days(USER)
    out = ROOT / "assets" / "activity-graph.svg"
    out.write_text(render(days))
    print(f"wrote {out.relative_to(ROOT)}: {sum(c for _, c in days)} contributions over {len(days)} days")


if __name__ == "__main__":
    main()
