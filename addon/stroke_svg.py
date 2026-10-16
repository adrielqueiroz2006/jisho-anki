"""Ordem dos traços como SVG animado (CSS), a partir dos paths do KanjiVG.

O SVG é gravado direto no campo `Traços`; não gera arquivo de mídia. Cores e grade vêm de
variáveis CSS definidas no template (`--traco-*`), então o claro e o escuro funcionam sozinhos.
Cada traço é desenhado em rosa (`--traco-atual`) e depois assenta na cor de tinta.

Não depende do Anki nem de Qt.
"""
import math
import re

VIEWBOX = "-3 -3 115 115"          # KanjiVG usa 109x109; sobra margem para a moldura
PAUSA_FINAL = 1.5                  # segundos com o kanji completo antes de repetir
INTERVALO = 0.18                   # segundos entre um traço e o seguinte
REALCE = 0.45                      # segundos que o traço fica rosa depois de desenhado

_TOKEN = re.compile(r"([MmCcSsLlHhVvZzQqTtAa])|(-?\d*\.?\d+(?:e-?\d+)?)")

# Direções candidatas para o número de cada traço, da preferida (acima à esquerda, como nos
# cadernos de caligrafia) à menos preferida; (dx, dy) com y para baixo.
_DIRECTIONS = [(-1, -1), (0, -1), (-1, 0), (1, -1), (-1, 1), (0, 1), (1, 0), (1, 1)]


def _tokens(d):
    for cmd, num in _TOKEN.findall(d):
        if cmd:
            yield cmd
        else:
            yield float(num)


def _walk(d):
    """Percorre um path do KanjiVG: (início, comprimento aproximado, pontos amostrados da linha).

    Cobre os comandos que o KanjiVG usa (M m C c S s L l H h V v Z); as curvas de Bézier são
    amostradas em 8 pontos, o bastante para dosar o tempo do traço e achar espaço livre.
    """
    toks = list(_tokens(d))
    i = 0
    cmd = None
    cur = (0.0, 0.0)
    start = None
    last_c2 = None
    length = 0.0
    points = []

    def num():
        nonlocal i
        v = toks[i]
        i += 1
        return v

    def cubic(p0, p1, p2, p3):
        total, prev = 0.0, p0
        for k in range(1, 9):
            t = k / 8
            mt = 1 - t
            x = mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t ** 3 * p3[0]
            y = mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t ** 3 * p3[1]
            total += math.hypot(x - prev[0], y - prev[1])
            prev = (x, y)
            points.append(prev)
        return total

    def line_to(p):
        # amostra a reta de 4 em 4 unidades, para o "espaço livre" não escapar por entre dois pontos
        n = max(1, int(math.hypot(p[0] - cur[0], p[1] - cur[1]) // 4))
        for k in range(1, n + 1):
            points.append((cur[0] + (p[0] - cur[0]) * k / n, cur[1] + (p[1] - cur[1]) * k / n))
        return math.hypot(p[0] - cur[0], p[1] - cur[1])

    while i < len(toks):
        if isinstance(toks[i], str):
            cmd = toks[i]
            i += 1
            if cmd in "Zz":
                continue
        rel = cmd.islower()
        c = cmd.upper()
        ox, oy = cur if rel else (0.0, 0.0)
        if c == "M":
            cur = (ox + num(), oy + num())
            if start is None:
                start = cur
                points.append(cur)
            cmd = "l" if rel else "L"   # pares seguintes após M são linhas
            last_c2 = None
        elif c == "L":
            p = (ox + num(), oy + num())
            length += line_to(p)
            cur, last_c2 = p, None
        elif c == "H":
            p = (ox + num() if rel else num(), cur[1])
            length += line_to(p)
            cur, last_c2 = p, None
        elif c == "V":
            p = (cur[0], oy + num() if rel else num())
            length += line_to(p)
            cur, last_c2 = p, None
        elif c == "C":
            p1 = (ox + num(), oy + num())
            p2 = (ox + num(), oy + num())
            p3 = (ox + num(), oy + num())
            length += cubic(cur, p1, p2, p3)
            cur, last_c2 = p3, p2
        elif c == "S":
            p1 = (2 * cur[0] - last_c2[0], 2 * cur[1] - last_c2[1]) if last_c2 else cur
            p2 = (ox + num(), oy + num())
            p3 = (ox + num(), oy + num())
            length += cubic(cur, p1, p2, p3)
            cur, last_c2 = p3, p2
        else:
            raise ValueError(f"comando de path não suportado: {cmd}")
    if start is None:
        raise ValueError("path sem M")
    return start, length, points


def path_info(d):
    """(x, y do início, comprimento aproximado) de um path do KanjiVG."""
    start, length, _points = _walk(d)
    return start[0], start[1], length


def number_positions(paths, radius=7.5):
    """Centro do número de cada traço: perto do início do traço, no ponto mais livre.

    Testa 8 direções ao redor do início e fica com a que está mais longe de qualquer traço
    (com preferência por acima/à esquerda), sem sair da moldura de 109x109.
    """
    walked = [_walk(d) for d in paths]
    everything = [p for _s, _l, pts in walked for p in pts]
    out = []
    for (sx, sy), _length, _pts in walked:
        best, best_score = None, -1e9
        # raios crescentes: só se afasta mais do início do traço se o ponto perto estiver ocupado
        for ridx, r in enumerate((radius, radius * 1.5, radius * 2)):
            for rank, (dx, dy) in enumerate(_DIRECTIONS):
                norm = math.hypot(dx, dy)
                x, y = sx + dx / norm * r, sy + dy / norm * r
                if not (3 <= x <= 106 and 3 <= y <= 106):
                    continue
                free_of_strokes = min(math.hypot(x - px, y - py) for px, py in everything) / 6.0
                free_of_numbers = min((math.hypot(x - nx, y - ny) for nx, ny in out), default=99) / 8.0
                # 1.0 = livre dos traços e dos outros números; os termos pequenos desempatam pela preferência
                score = min(1.0, free_of_strokes, free_of_numbers) - rank * 0.02 - ridx * 0.08
                if score > best_score:
                    best, best_score = (x, y), score
        if best is None:  # início colado na borda: empurra para dentro
            best = (min(max(sx, 4), 105), min(max(sy, 4), 105))
        out.append(best)
    return out


def _fmt(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def stroke_durations(lengths):
    """Segundos para desenhar cada traço: proporcional ao comprimento, entre 0,4 s e 1,1 s."""
    return [min(1.1, max(0.4, 0.3 + length / 90 * 0.45)) for length in lengths]


def build_kanji_svg(literal, paths, animated=True):
    """SVG de um kanji. `paths` = lista de 'd' dos traços, em ordem.

    `animated=False` devolve a versão estática (todos os traços e os números), para impressão.
    """
    cp = f"{ord(literal):x}"
    cls = f"k{cp}"
    infos = [path_info(d) for d in paths]
    spots = number_positions(paths)
    ghost = "".join(f'<path d="{d}"/>' for d in paths)

    if not animated:
        draw = "".join(f'<path d="{d}"/>' for d in paths)
        nums = "".join(
            f'<text x="{_fmt(x)}" y="{_fmt(y)}">{n}</text>' for n, (x, y) in enumerate(spots, start=1))
        return (
            f'<svg class="kk kk-estatico" viewBox="{VIEWBOX}" role="img" aria-label="{literal}: traços numerados">'
            '<rect class="kk-moldura" x="0" y="0" width="109" height="109"/>'
            '<path class="kk-grade" d="M54.5 0V109M0 54.5H109"/>'
            f'<g class="kk-tracos">{draw}</g><g class="kk-numeros">{nums}</g></svg>'
        )

    durs = stroke_durations([length for _x, _y, length in infos])
    starts, t = [], 0.0
    for dur in durs:
        starts.append(t)
        t += dur + INTERVALO
    total = t + PAUSA_FINAL

    def pct(x):
        return f"{x / total * 100:.3f}".rstrip("0").rstrip(".")

    css = []
    for n, (a, dur) in enumerate(zip(starts, durs), start=1):
        b = a + dur
        c = b + REALCE
        css.append(
            f"@keyframes {cls}p{n}{{0%,{pct(a)}%{{opacity:0;stroke-dashoffset:1;stroke:var(--traco-atual)}}"
            f"{pct(a + 0.01)}%{{opacity:1}}{pct(b)}%{{stroke-dashoffset:0;stroke:var(--traco-atual)}}"
            f"{pct(c)}%,100%{{opacity:1;stroke-dashoffset:0;stroke:var(--traco-feito)}}}}"
            f"@keyframes {cls}n{n}{{0%,{pct(a)}%{{opacity:0}}{pct(a + 0.01)}%,100%{{opacity:1}}}}"
            f".{cls} .p{n}{{animation:{cls}p{n} {_fmt(total)}s linear infinite}}"
            f".{cls} .n{n}{{animation:{cls}n{n} {_fmt(total)}s linear infinite}}"
        )

    draw = "".join(
        f'<path class="p{n}" pathLength="1" d="{d}"/>' for n, d in enumerate(paths, start=1)
    )
    nums = "".join(
        f'<text class="n{n}" x="{_fmt(x)}" y="{_fmt(y)}">{n}</text>' for n, (x, y) in enumerate(spots, start=1)
    )
    return (
        f'<svg class="kk {cls}" viewBox="{VIEWBOX}" role="img" aria-label="{literal}: ordem dos traços">'
        f"<style>{''.join(css)}</style>"
        '<rect class="kk-moldura" x="0" y="0" width="109" height="109"/>'
        '<path class="kk-grade" d="M54.5 0V109M0 54.5H109"/>'
        f'<g class="kk-fantasma">{ghost}</g>'
        f'<g class="kk-tracos">{draw}</g>'
        f'<g class="kk-numeros">{nums}</g>'
        "</svg>"
    )


def build_strokes_html(word, get_paths):
    """Um SVG por kanji distinto da palavra, na ordem em que aparecem.

    `get_paths(literal)` devolve a lista de paths ou None (kanji sem dados no KanjiVG).
    Devolve '' se a palavra não tiver nenhum kanji com traços.
    """
    seen, out = set(), []
    for ch in word:
        if ch in seen or not ("一" <= ch <= "鿿" or ch in "々〆ヶ"):
            continue
        seen.add(ch)
        paths = get_paths(ch)
        if paths:
            out.append(build_kanji_svg(ch, paths))
    return "".join(out)
