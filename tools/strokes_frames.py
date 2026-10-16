#!/usr/bin/env python3
"""Quadros congelados da animação dos traços, para conferir o visual em instantes exatos.

  python tools/strokes_frames.py                  # 食書日水必鬱 em t = 1,5 s, 3,5 s e no fim (kanji completo)
  python tools/strokes_frames.py --kanji 鬱 --times 1 5 10 15 --night

O Edge headless não avança animações CSS no tempo virtual, então cada quadro pausa a animação e a
desloca com `animation-delay` negativo. Saída em build/frames/.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import preview  # noqa: E402
from addon import dbmanager, settings, stroke_svg  # noqa: E402

OUT = os.path.join(ROOT, "build", "frames")


def total_seconds(paths):
    durs = stroke_svg.stroke_durations([stroke_svg.path_info(d)[2] for d in paths])
    return sum(durs) + len(durs) * stroke_svg.INTERVALO + stroke_svg.PAUSA_FINAL


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kanji", default="食書日水必鬱")
    ap.add_argument("--times", type=float, nargs="*", default=[1.5, 3.5], help="segundos; 'fim' é sempre incluído")
    ap.add_argument("--night", action="store_true")
    ap.add_argument("--static", action="store_true", help="folha estática com todos os traços numerados (impressão)")
    ap.add_argument("--size", type=int, default=230)
    args = ap.parse_args()

    conn = dbmanager.get_connection(settings.defaults())
    css = open(os.path.join(ROOT, "addon", "templates", "style.css"), encoding="utf-8").read()
    data = {}
    for lit in args.kanji:
        row = conn.execute("SELECT strokes_svg FROM kanji WHERE literal=?", (lit,)).fetchone()
        data[lit] = json.loads(row[0])
    os.makedirs(OUT, exist_ok=True)
    cols = 3
    rows = (len(data) + cols - 1) // cols
    size = (cols * (args.size + 14) + 30, rows * (args.size + 14) + 30)
    if args.static:
        cells = "".join(stroke_svg.build_kanji_svg(lit, paths, animated=False) for lit, paths in data.items())
        body = (f"<style>{css}</style><style>.kk{{width:{args.size}px;height:{args.size}px;margin:6px}}"
                f".g{{display:flex;flex-wrap:wrap;padding:10px}}</style><div class='g'>{cells}</div>")
        html_path = os.path.join(OUT, "tracos_numerados.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(preview.page(body, args.night))
        png = html_path[:-5] + ".png"
        preview.shoot(html_path, png, size, 1500)
        print(png)
        return
    moments = [(f"{t:g}s", t) for t in args.times] + [("fim", None)]
    for label, t in moments:
        cells = ""
        for lit, paths in data.items():
            at = t if t is not None else total_seconds(paths) - 0.5  # fim: kanji completo, antes de repetir
            freeze = f".{'k%x' % ord(lit)} *{{animation-play-state:paused!important;animation-delay:-{at}s!important}}"
            cells += f"<style>{freeze}</style>" + stroke_svg.build_kanji_svg(lit, paths)
        body = (f"<style>{css}</style><style>.kk{{width:{args.size}px;height:{args.size}px;margin:6px}}"
                f".g{{display:flex;flex-wrap:wrap;padding:10px}}</style><div class='g'>{cells}</div>")
        tag = "escuro" if args.night else "claro"
        html_path = os.path.join(OUT, f"quadro_{label}_{tag}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(preview.page(body, args.night))
        png = html_path[:-5] + ".png"
        preview.shoot(html_path, png, size, 1500)
        print(png)


if __name__ == "__main__":
    main()
