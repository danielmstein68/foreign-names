"""Draw the "names do better where residents share them" figure as a page.

Reads output/fig_bloc_data.json (from 10_bloc_figure_data.py) and writes
docs/bloc_chart.html: four small panels on the same scale, each with the
fitted line, its 95% confidence band, and the line drawn solid only where
the middle 80% of that group's candidates run (dashed where projected).

Run:  .venv/bin/python src/11_bloc_figure.py
"""

import json

from common import DOCS, OUTPUT

ORDER = ["black", "asian", "german", "hispanic"]
SHARE_NAME = {"black": "Black residents", "asian": "Asian residents",
              "german": "residents of German ancestry", "hispanic": "Hispanic residents"}

# Panel geometry (SVG units). Same scales in every panel so they can be compared.
PW, PH = 330, 250
X0, X1 = 52, 312          # 0% .. 50%
Y_MIN, Y_MAX = -8, 9
Y0, Y1 = 214, 34          # y = -8 at bottom, +9 at top


def sx(s):
    return X0 + (X1 - X0) * s / 0.5


def sy(v):
    return Y0 + (Y1 - Y0) * (v - Y_MIN) / (Y_MAX - Y_MIN)


def fmt(v):
    return f"{v:+.1f}".replace("-", "−")


def panel(key, g, ox, oy):
    pts = g["points"]
    upper = " ".join(f"{sx(s):.1f},{sy(min(hi, Y_MAX)):.1f}" for s, _, _, hi in pts)
    lower = " ".join(f"{sx(s):.1f},{sy(max(lo, Y_MIN)):.1f}" for s, _, lo, _ in reversed(pts))
    lo_s, hi_s = g["p10"], min(g["p90"], 0.5)

    def seg(a, b):
        sel = [(s, e) for s, e, _, _ in pts if a - 1e-9 <= s <= b + 1e-9]
        return " ".join(f"{sx(s):.1f},{sy(e):.1f}" for s, e in sel)

    e0, e50 = pts[0][1], pts[-1][1]
    out = [f'<g transform="translate({ox},{oy})">',
           f'<text x="{X0}" y="18" class="ptitle">{g["label"]}</text>']
    for v in (-8, -4, 4, 8):
        out.append(f'<line x1="{X0}" x2="{X1}" y1="{sy(v):.1f}" y2="{sy(v):.1f}" class="grid"/>')
        out.append(f'<text x="{X0 - 8}" y="{sy(v) + 4:.1f}" class="tick" text-anchor="end">{fmt(v).replace(".0", "")}</text>')
    out.append(f'<line x1="{X0}" x2="{X1}" y1="{sy(0):.1f}" y2="{sy(0):.1f}" class="zero"/>')
    out.append(f'<text x="{X0 - 8}" y="{sy(0) + 4:.1f}" class="tick" text-anchor="end">0</text>')
    for s in (0, 0.1, 0.2, 0.3, 0.4, 0.5):
        out.append(f'<text x="{sx(s):.1f}" y="{Y0 + 18}" class="tick" text-anchor="middle">{int(s * 100)}%</text>')
    out.append(f'<polygon points="{upper} {lower}" class="band {key}"/>')
    if lo_s > 0:
        out.append(f'<polyline points="{seg(0, lo_s)}" class="line dashed {key}"/>')
    out.append(f'<polyline points="{seg(lo_s, hi_s)}" class="line {key}"/>')
    if hi_s < 0.5:
        out.append(f'<polyline points="{seg(hi_s, 0.5)}" class="line dashed {key}"/>')
    out.append(f'<circle cx="{sx(0):.1f}" cy="{sy(e0):.1f}" r="3.5" class="dot {key}"/>')
    out.append(f'<circle cx="{sx(0.5):.1f}" cy="{sy(e50):.1f}" r="3.5" class="dot {key}"/>')
    ly0 = sy(e0) + (16 if e0 < 0 else -9)
    ly50 = sy(e50) + (-9 if e50 > 0 else 16)
    out.append(f'<text x="{sx(0) + 6:.1f}" y="{ly0:.1f}" class="val {key}">{fmt(e0)}</text>')
    out.append(f'<text x="{sx(0.5) - 2:.1f}" y="{ly50:.1f}" class="val {key}" text-anchor="end">{fmt(e50)}</text>')
    out.append(f'<text x="{(X0 + X1) / 2:.1f}" y="{Y0 + 34}" class="axis" text-anchor="middle">'
               f'share of {SHARE_NAME[key]}</text>')
    out.append("</g>")
    return "\n".join(out)


def main() -> None:
    data = json.loads((OUTPUT / "fig_bloc_data.json").read_text())
    panels = [panel(k, data[k], (i % 2) * (PW + 20), (i // 2) * (PH + 16)) for i, k in enumerate(ORDER)]
    W, H = 2 * PW + 20, 2 * PH + 16
    aria = ("Four panels. In local races, each surname group does worse than a white Anglo-named opponent where few "
            "residents share its background and better where many do. " + " ".join(
                f"{data[k]['label']}: {fmt(data[k]['points'][0][1])} points at 0%, "
                f"{fmt(data[k]['points'][-1][1])} at 50%." for k in ORDER))
    svg = (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{aria}" class="chart">\n'
           + "\n".join(panels) + "\n</svg>")
    template = (DOCS / "bloc_chart_template.html").read_text(encoding="utf-8")
    (DOCS / "bloc_chart.html").write_text(template.replace("<!--CHART-->", svg), encoding="utf-8")
    print(f"wrote {DOCS / 'bloc_chart.html'}")


if __name__ == "__main__":
    main()
