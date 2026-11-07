"""Salidas por puzzle para maquetar en Canva (sin dependencias de Streamlit).

- grid_svg(): cuadrícula con marco (sopa o solución con bandas), vectorial y con texto real.
- grid_text(): una fila por línea, letras separadas por un espacio (UTF-8, NFC).
- puzzle_files(): los 6 archivos de un puzzle, con la semilla en el nombre.
- puzzle_zip(): esos 6 archivos en un ZIP.
"""

import io
import unicodedata
import zipfile
from xml.sax.saxutils import escape, quoteattr

import geometria as geo
from pdf import CAP_HEIGHT, GRID_ONLY_CELL, generate_grid_pdf, generate_pdf

SVG_FONT_FAMILY = "'Liberation Mono', 'Courier New', monospace"


def _num(x):
    return f"{x:.3f}".rstrip("0").rstrip(".")


def grid_svg(grid, placed=(), solution=False, exclude=(), cell=GRID_ONLY_CELL):
    """SVG con SOLO la cuadrícula y su marco. Unidades en puntos (pt)."""
    rows, cols = len(grid), len(grid[0])
    w, h = geo.frame_size(rows, cols, cell)
    lw = geo.FRAME_RATIO * cell
    size = geo.font_size(cell)
    offset = geo.baseline_offset(size, CAP_HEIGHT)

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_num(w)}pt" height="{_num(h)}pt" '
        f'viewBox="0 0 {_num(w)} {_num(h)}">',
        f'<rect class="marco" x="{_num(lw / 2)}" y="{_num(lw / 2)}" width="{_num(w - lw)}" '
        f'height="{_num(h - lw)}" fill="none" stroke="#000" stroke-width="{_num(lw)}"/>',
    ]
    if solution:
        out.append('<g class="bandas">')
        for b in geo.bands_for(placed, cell, exclude):
            out.append(
                f'<rect class="banda" data-palabra={quoteattr(b.word)} '
                f'x="{_num(b.cx - b.length / 2)}" y="{_num(b.cy - b.height / 2)}" '
                f'width="{_num(b.length)}" height="{_num(b.height)}" '
                f'rx="{_num(b.radius)}" ry="{_num(b.radius)}" '
                f'fill="#000" fill-opacity="{geo.BAND_ALPHA}" '
                f'transform="rotate({_num(b.angle)} {_num(b.cx)} {_num(b.cy)})"/>'
            )
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
    }


def puzzle_files(grid, placed, words_display, seed, exclude=()):
    """Devuelve {nombre_de_archivo: bytes} con las 6 salidas del puzzle."""
    names = file_names(seed)
    return {
        names["pdf"]: generate_pdf(grid, placed, words_display, exclude).getvalue(),
        names["sopa_svg"]: grid_svg(grid).encode("utf-8"),
        names["solucion_svg"]: grid_svg(grid, placed, solution=True, exclude=exclude).encode("utf-8"),
        names["sopa_pdf"]: generate_grid_pdf(grid).getvalue(),
        names["solucion_pdf"]: generate_grid_pdf(grid, placed, solution=True, exclude=exclude).getvalue(),
        names["txt"]: grid_text(grid).encode("utf-8"),
    }


def puzzle_zip(files):
    """ZIP en memoria con los archivos dados ({nombre: bytes}), en orden fijo."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, files[name])
    return buffer.getvalue()
