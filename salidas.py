"""Salidas por puzzle para maquetar en Canva (sin dependencias de Streamlit).

- grid_svg(): cuadrícula con marco (sopa o solución con bandas), vectorial y con texto real.
- grid_text(): una fila por línea, letras separadas por un espacio (UTF-8, NFC).
- puzzle_files(): los archivos de un puzzle, con la semilla en el nombre (6 para
  el libro + solucion_autor.svg + ficha.json).
- puzzle_zip(): esos archivos en un ZIP.

Las palabras ocultas (Ruta Secreta) NO se marcan en ninguna salida del libro;
solo en solucion_autor.svg, con contorno discontinuo y el rótulo de uso interno.
"""

import io
import unicodedata
import zipfile
from xml.sax.saxutils import escape, quoteattr

import geometria as geo
from ficha import ficha_json
from motor import clean_word
from pdf import CAP_HEIGHT, GRID_ONLY_CELL, generate_grid_pdf, generate_pdf

SVG_FONT_FAMILY = "'Liberation Mono', 'Courier New', monospace"
INTERNAL_LABEL = "USO INTERNO — no imprimir"
LABEL_RATIO = 0.9  # alto de la franja del rótulo interno, en celdas


def _num(x):
    return f"{x:.3f}".rstrip("0").rstrip(".")


def _band_rect(b, cls, attrs):
    return (
        f'<rect class="{cls}" data-palabra={quoteattr(b.word)} '
        f'x="{_num(b.cx - b.length / 2)}" y="{_num(b.cy - b.height / 2)}" '
        f'width="{_num(b.length)}" height="{_num(b.height)}" '
        f'rx="{_num(b.radius)}" ry="{_num(b.radius)}" {attrs} '
        f'transform="rotate({_num(b.angle)} {_num(b.cx)} {_num(b.cy)})"/>'
    )


def grid_svg(grid, placed=(), solution=False, exclude=(), cell=GRID_ONLY_CELL,
             outline=(), internal=False):
    """SVG con SOLO la cuadrícula y su marco. Unidades en puntos (pt).

    - solution: dibuja las bandas de las palabras de `placed` salvo las de `exclude`.
    - outline: palabras que se marcan con contorno discontinuo sin relleno
      (las ocultas, en la solución del autor).
    - internal: agrega arriba el rótulo «USO INTERNO — no imprimir».
    """
    rows, cols = len(grid), len(grid[0])
    w, h = geo.frame_size(rows, cols, cell)
    lw = geo.FRAME_RATIO * cell
    size = geo.font_size(cell)
    offset = geo.baseline_offset(size, CAP_HEIGHT)
    top = LABEL_RATIO * cell if internal else 0.0  # franja extra por encima del marco

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_num(w)}pt" height="{_num(h + top)}pt" '
        f'viewBox="0 {_num(-top)} {_num(w)} {_num(h + top)}">',
    ]
    if internal:
        out.append(
            f'<text class="uso-interno" x="{_num(lw)}" y="{_num(-top * 0.3)}" '
            f'font-family="{SVG_FONT_FAMILY}" font-size="{_num(0.5 * cell)}" font-weight="bold" '
            f'fill="#b00000">{escape(INTERNAL_LABEL)}</text>'
        )
    out.append(
        f'<rect class="marco" x="{_num(lw / 2)}" y="{_num(lw / 2)}" width="{_num(w - lw)}" '
        f'height="{_num(h - lw)}" fill="none" stroke="#000" stroke-width="{_num(lw)}"/>'
    )
    if solution:
        out.append('<g class="bandas">')
        for b in geo.bands_for(placed, cell, exclude):
            out.append(_band_rect(b, "banda", f'fill="#000" fill-opacity="{geo.BAND_ALPHA}"'))
        out.append("</g>")
    if outline:
        keep = {clean_word(x) for x in outline}
        marked = [(word, coords) for word, coords in placed if word in keep]
        dash = f"{_num(0.25 * cell)} {_num(0.15 * cell)}"
        out.append('<g class="ocultas">')
        for b in geo.bands_for(marked, cell):
            out.append(_band_rect(
                b, "banda-oculta",
                f'fill="none" stroke="#000" stroke-width="{_num(0.08 * cell)}" stroke-dasharray="{dash}"',
            ))
        out.append("</g>")
    out.append(
        f'<g class="letras" font-family="{SVG_FONT_FAMILY}" font-size="{_num(size)}" '
        f'text-anchor="middle" fill="#000">'
    )
    for r in range(rows):
        for c in range(cols):
            cx, cy = geo.cell_center(r, c, cell)
            out.append(f'<text x="{_num(cx)}" y="{_num(cy + offset)}">{escape(grid[r][c].upper())}</text>')
    out.append("</g>")
    out.append("</svg>")
    return "\n".join(out) + "\n"


def grid_text(grid):
    """Cuadrícula en texto plano: una fila por línea, letras separadas por un espacio."""
    text = "\n".join(" ".join(row) for row in grid) + "\n"
    return unicodedata.normalize("NFC", text)


def file_names(seed):
    p = f"s{seed}_"
    return {
        "pdf": p + "sopa_de_letras.pdf",
        "sopa_svg": p + "sopa.svg",
        "solucion_svg": p + "solucion.svg",
        "sopa_pdf": p + "sopa_cuadricula.pdf",
        "solucion_pdf": p + "solucion_cuadricula.pdf",
        "txt": p + "cuadricula.txt",
        "autor_svg": p + "solucion_autor.svg",
        "ficha": p + "ficha.json",
    }


def puzzle_files(grid, placed, words_display, seed, exclude=(), hidden=(), ficha=None):
    """Devuelve {nombre_de_archivo: bytes} con las salidas del puzzle.

    - Libro (6): PDF de 2 páginas, sopa.svg, solucion.svg, sopa_cuadricula.pdf,
      solucion_cuadricula.pdf y cuadricula.txt. Las palabras de `hidden` (Ruta
      Secreta) y de `exclude` no se marcan en ninguna solución del libro.
    - Autor: solucion_autor.svg (ocultas con contorno discontinuo y rótulo de
      uso interno) y, si se pasa `ficha`, ficha.json.
    """
    names = file_names(seed)
    book_exclude = list(exclude) + list(hidden)
    files = {
        names["pdf"]: generate_pdf(grid, placed, words_display, book_exclude).getvalue(),
        names["sopa_svg"]: grid_svg(grid).encode("utf-8"),
        names["solucion_svg"]: grid_svg(grid, placed, solution=True, exclude=book_exclude).encode("utf-8"),
        names["sopa_pdf"]: generate_grid_pdf(grid).getvalue(),
        names["solucion_pdf"]: generate_grid_pdf(grid, placed, solution=True, exclude=book_exclude).getvalue(),
        names["txt"]: grid_text(grid).encode("utf-8"),
        names["autor_svg"]: grid_svg(
            grid, placed, solution=True, exclude=book_exclude, outline=hidden, internal=True
        ).encode("utf-8"),
    }
    if ficha is not None:
        files[names["ficha"]] = ficha_json(ficha).encode("utf-8")
    return files


def puzzle_zip(files):
    """ZIP en memoria con los archivos dados ({nombre: bytes}), en orden fijo."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, files[name])
    return buffer.getvalue()
