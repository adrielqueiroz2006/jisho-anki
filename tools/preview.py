#!/usr/bin/env python3
"""Pré-visualização dos cartões: renderiza com o motor de templates real do Anki (pacote `anki`)
e tira capturas com o Edge em modo headless.

  python tools/preview.py            # gera build/preview/*.html
  python tools/preview.py --shots    # também gera os PNG (claro/escuro, desktop/celular)

Requer: pip install anki. O Edge só é preciso para --shots.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from anki.collection import Collection  # noqa: E402

from addon import notetype as nt  # noqa: E402

OUT = os.path.join(ROOT, "build", "preview")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# nome -> (largura, altura) da janela
VIEWPORTS = {"desktop": (760, 1500), "celular": (390, 1900)}


def render_all(words=None, with_audio=False):
    """Devolve [(palavra, frente_html, verso_html)] renderizados pelo Anki, com o conteúdo do preenchimento real."""
    from addon import dbmanager, lookup, settings, testdeck

    conn = dbmanager.get_connection(settings.defaults())
    tmp = tempfile.mkdtemp()
    col = Collection(os.path.join(tmp, "preview.anki2"))
    try:
        m = nt.ensure_notetype(col)
        out = []
        for word, _why in testdeck.WORDS:
            if words and word not in words:
                continue
            fields, _tags = testdeck.build_test_fields(conn, word)
            if with_audio:
                from addon import audio

                cfg = settings.defaults()
                jobs = audio.plan_jobs(fields, cfg)
                result = audio.run_jobs(jobs, cfg, col.media.dir())
                fields.update(audio.apply_result(jobs, result, col.media.dir(), col.media.write_data))
                for name in os.listdir(col.media.dir()):
                    if name.startswith("jisho_"):
                        shutil.copy(os.path.join(col.media.dir(), name), os.path.join(OUT, name))
                if result.errors:
                    print("  áudio:", audio.summarize_errors(result))
            note = col.new_note(m)
            for k, v in fields.items():
                note[k] = v
            col.add_note(note, col.decks.id("Preview"))
            card = note.cards()[0]
            out.append((word, card.question(), card.answer()))
        return out
    finally:
        col.close()
        shutil.rmtree(tmp, ignore_errors=True)


def page(body_html, night):
    # no Anki real o reprodutor troca isto por um botão; aqui só marca onde ele ficaria
    body_html = re.sub(r"\[anki:play:[^\]]*\]", '<span style="display:inline-block;width:22px;height:22px;border-radius:50%;border:1.5px solid currentColor;text-align:center;line-height:20px;font-size:10px">▶</span>', body_html)
    cls = "card card1 nightMode" if night else "card card1"
    return (f'<!doctype html><html><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1"></head>'
            f'<body class="{cls}">{body_html}</body></html>')


def shoot(html_path, png_path, size, wait_ms=3500):
    w, h = size
    if w < 500:
        # o Edge headless não abre janelas com menos de 500 px: simula o celular com um iframe
        wrapper = html_path[:-5] + "_iframe.html"
        with open(wrapper, "w", encoding="utf-8") as f:
            f.write(f'<body style="margin:0;background:#555"><iframe src="{os.path.basename(html_path)}" '
                    f'style="width:{w}px;height:{h}px;border:0;display:block;margin:0 auto"></iframe></body>')
        html_path, w = wrapper, 500
    subprocess.run([
        EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        f"--window-size={w},{h}", f"--virtual-time-budget={wait_ms}",
        f"--screenshot={png_path}", "file:///" + html_path.replace("\\", "/"),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", action="store_true")
    ap.add_argument("--only", help="só esta palavra")
    ap.add_argument("--audio", action="store_true", help="gera o áudio de verdade (usa a internet)")
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    fonts = os.path.join(ROOT, "addon", "fonts")
    for name in os.listdir(fonts):
        if name.endswith(".woff2"):
            shutil.copy(os.path.join(fonts, name), os.path.join(OUT, name))

    jobs = []
    for word, front, back in render_all([args.only] if args.only else None, args.audio):
        for side, html_ in (("frente", front), ("verso", back)):
            for night in (False, True):
                tag = "escuro" if night else "claro"
                path = os.path.join(OUT, f"{word}_{side}_{tag}.html")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(page(html_, night))
                jobs.append((path, word, side, tag))
                if side == "verso" and 'class="conj"' in html_:
                    path = os.path.join(OUT, f"{word}_verso-conj_{tag}.html")
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(page(html_.replace('<details class="conj">', '<details class="conj" open>'), night))
                    jobs.append((path, word, "verso-conj", tag))
    print(f"{len(jobs)} páginas em {OUT}")
    if args.shots:
        for path, word, side, tag in jobs:
            for vp, size in VIEWPORTS.items():
                png = path[:-5] + f"_{vp}.png"
                shoot(path, png, size)
                print("  ", os.path.basename(png))


if __name__ == "__main__":
    main()
