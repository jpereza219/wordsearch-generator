"""Exportación a PDF (sin dependencias de Streamlit).

- generate_pdf(): PDF carta de 2 páginas (sopa y solución con bandas).
- generate_grid_pdf(): PDF de una página recortada al tamaño de la cuadrícula.

Todo el texto usa Liberation Mono (incrustada; métricamente compatible con
Courier New). La geometría de letras y bandas viene de geometria.py y es la
misma que usa el SVG.
"""

import math
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

import geometria as geo

FONTS_DIR = Path(__file__).resolve().parent / "fonts"
FONT = "LiberationMono"
FONT_BOLD = "LiberationMono-Bold"

if FONT not in pdfmetrics.getRegisteredFontNames():
    pdfmetrics.registerFont(TTFont(FONT, str(FONTS_DIR / "LiberationMono-Regular.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, str(FONTS_DIR / "LiberationMono-Bold.ttf")))

CAP_HEIGHT = pdfmetrics.getFont(FONT).face.capHeight  # en milésimas de em

# ----------------------------
# Página carta (2 páginas)
# ----------------------------
MARGIN = 36            # 0.5 pulgadas
TITLE_SIZE = 16
TITLE_GAP = 24         # espacio entre el título y el contenido
LIST_TITLE_SIZE = 12
LIST_TITLE_GAP = 18
LIST_SIZE = 10
LIST_LEADING = 12
LIST_COL_GAP = 12
LIST_GRID_GAP = 24     # separación mínima entre la lista y la cuadrícula
MAX_CELL = 28          # tamaño máximo de celda en la página carta
MIN_SIDE_CELL = 12     # por debajo, se pasa la lista debajo de la cuadrícula si da más espacio
GRID_ONLY_CELL = 24    # tamaño de celda en las salidas de cuadrícula sola


@dataclass(frozen=True)
class PageLayout:
    page_w: float
    page_h: float
    title_y: float
    list_x: float
    list_top: float          # parte superior de la lista (y PDF, hacia arriba)
    list_w: float
    list_columns: list       # [[palabra, ...], ...]
    list_col_w: float
    list_bottom: float
    cell: float
    frame_x: float           # esquina superior izquierda del marco (y PDF)
    frame_top: float
    frame_w: float
    frame_h: float

    @property
    def list_box(self):
        """(x0, y0, x1, y1) de la lista en coordenadas PDF."""
        return (self.list_x, self.list_bottom, self.list_x + self.list_w, self.list_top)

    @property
    def frame_box(self):
        """(x0, y0, x1, y1) del marco en coordenadas PDF."""
        return (self.frame_x, self.frame_top - self.frame_h, self.frame_x + self.frame_w, self.frame_top)


def _list_metrics(words):
    widest = max(
        [pdfmetrics.stringWidth(w, FONT, LIST_SIZE) for w in words]
        + [pdfmetrics.stringWidth("Palabras:", FONT_BOLD, LIST_TITLE_SIZE)]
    )
    return widest + LIST_COL_GAP


_DESCENT = LIST_SIZE * 0.25            # margen para descendentes bajo la última línea
_FIRST_DROP = LIST_TITLE_GAP + LIST_SIZE  # de la parte superior de la lista a la 1.ª línea base


def _lines_that_fit(height):
    return int((height - _FIRST_DROP - _DESCENT) // LIST_LEADING) + 1


def _list_height(lines):
    return _FIRST_DROP + LIST_LEADING * max(0, lines - 1) + _DESCENT


def _split(words, lines_per_col):
    return [words[i:i + lines_per_col] for i in range(0, len(words), lines_per_col)] or [[]]


def page_layout(rows, cols, words_display, pagesize=letter):
    """Diseño de la página carta con márgenes de 0.5 pulgadas.

    Se prueban dos disposiciones. Se usa "lado" (como el Vol. 1) mientras la
    celda mida al menos MIN_SIDE_CELL; si no, la que dé la celda más grande:
      - "lado":  lista a la izquierda (en tantas columnas como haga falta) y
                 cuadrícula a la derecha;
      - "abajo": cuadrícula arriba a todo el ancho y lista debajo en columnas.
    En ambas, la cuadrícula nunca toca la lista ni los márgenes.
    """
    page_w, page_h = pagesize
    title_y = page_h - MARGIN - TITLE_SIZE
    content_top = title_y - TITLE_GAP
    content_h = content_top - MARGIN
    content_w = page_w - 2 * MARGIN

    words = [w.upper() for w in words_display]
    col_w = _list_metrics(words)
    options = []

    # Lista a la izquierda
    lines = max(1, _lines_that_fit(content_h))
    columns = _split(words, lines)
    list_w = len(columns) * col_w - LIST_COL_GAP
    area_x0 = MARGIN + list_w + LIST_GRID_GAP
    area_w = page_w - MARGIN - area_x0
    if area_w > 0:
        cell = min(area_w / (cols + 2 * geo.PAD), content_h / (rows + 2 * geo.PAD), MAX_CELL)
        frame_w, frame_h = geo.frame_size(rows, cols, cell)
        options.append(dict(
            cell=cell, list_x=MARGIN, list_top=content_top, list_w=list_w, list_columns=columns,
            list_bottom=content_top - _list_height(max(len(c) for c in columns)),
            frame_x=area_x0 + (area_w - frame_w) / 2, frame_top=content_top,
            frame_w=frame_w, frame_h=frame_h,
        ))

    # Lista debajo: la celda más grande con la que la lista aún cabe a lo ancho.
    max_cols = max(1, int((content_w + LIST_COL_GAP) // col_w))

    def fits_below(cell):
        _, frame_h = geo.frame_size(rows, cols, cell)
        rest = content_h - frame_h - LIST_GRID_GAP
        if rest < _list_height(1):
            return False
        return -(-len(words) // _lines_that_fit(rest)) <= max_cols

    hi = min(content_w / (cols + 2 * geo.PAD), MAX_CELL)
    if fits_below(hi):
        best = hi
    else:
        lo, best = 0.0, None
        for _ in range(40):
            mid = (lo + hi) / 2
            if fits_below(mid):
                lo = best = mid
            else:
                hi = mid
    if best:
        cell = best
        frame_w, frame_h = geo.frame_size(rows, cols, cell)
        rest = content_h - frame_h - LIST_GRID_GAP
        columns = _split(words, _lines_that_fit(rest))
        list_top = content_top - frame_h - LIST_GRID_GAP
        options.append(dict(
            cell=cell, list_x=MARGIN, list_top=list_top,
            list_w=len(columns) * col_w - LIST_COL_GAP, list_columns=columns,
            list_bottom=list_top - _list_height(max(len(c) for c in columns)),
            frame_x=MARGIN + (content_w - frame_w) / 2, frame_top=content_top,
            frame_w=frame_w, frame_h=frame_h,
        ))

    if not options:
        raise ValueError("La lista de palabras no cabe en la página.")
    # Se prefiere la lista al lado (como el Vol. 1) mientras la celda sea legible.
    side = options[0] if options[0]["list_top"] == content_top else None
    if side is not None and side["cell"] >= MIN_SIDE_CELL:
        chosen = side
    else:
        chosen = max(options, key=lambda o: o["cell"])
    return PageLayout(page_w=page_w, page_h=page_h, title_y=title_y, list_col_w=col_w, **chosen)


# ----------------------------
# Dibujo
# ----------------------------
def draw_grid(c, grid, x0, top, cell, bands=()):
    """Dibuja marco, bandas (antes que las letras) y letras centradas.

    (x0, top) es la esquina superior izquierda del marco en coordenadas PDF.
    """
    rows, cols = len(grid), len(grid[0])
    frame_w, frame_h = geo.frame_size(rows, cols, cell)
    lw = geo.FRAME_RATIO * cell

    # Marco
    c.saveState()
    c.setLineWidth(lw)
    c.setStrokeColor(colors.black)
    c.rect(x0 + lw / 2, top - frame_h + lw / 2, frame_w - lw, frame_h - lw, stroke=1, fill=0)
    c.restoreState()

    # Bandas: negro semitransparente; en los cruces se acumula y se ve más oscuro.
    for band in bands:
        c.saveState()
        c.setFillColor(colors.black)
        c.setFillAlpha(geo.BAND_ALPHA)
        c.translate(x0 + band.cx, top - band.cy)
        c.rotate(-band.angle)  # el ángulo es con y hacia abajo; el PDF tiene y hacia arriba
        c.roundRect(-band.length / 2, -band.height / 2, band.length, band.height, band.radius, stroke=0, fill=1)
        c.restoreState()

    # Letras centradas en su celda
    size = geo.font_size(cell)
    offset = geo.baseline_offset(size, CAP_HEIGHT)
    c.setFillColor(colors.black)
    c.setFont(FONT, size)
    for r in range(rows):
        for col in range(cols):
            cx, cy = geo.cell_center(r, col, cell)
            c.drawCentredString(x0 + cx, top - cy - offset, grid[r][col].upper())


def _new_canvas(buffer, pagesize):
    return canvas.Canvas(
        buffer, pagesize=pagesize, invariant=1,
        initialFontName=FONT, initialFontSize=12,
    )


def _draw_page(c, layout, title, grid, bands):
    c.setFont(FONT_BOLD, TITLE_SIZE)
    c.drawCentredString(layout.page_w / 2, layout.title_y, title)

    c.setFont(FONT_BOLD, LIST_TITLE_SIZE)
    c.drawString(layout.list_x, layout.list_top - LIST_TITLE_SIZE, "Palabras:")
    c.setFont(FONT, LIST_SIZE)
    first_line = layout.list_top - LIST_TITLE_GAP - LIST_SIZE
    for i, column in enumerate(layout.list_columns):
        x = layout.list_x + i * layout.list_col_w
        for j, w in enumerate(column):
            c.drawString(x, first_line - j * LIST_LEADING, w)

    draw_grid(c, grid, layout.frame_x, layout.frame_top, layout.cell, bands)


def generate_pdf(grid, placed, words_display, exclude=()):
    """PDF carta de 2 páginas: sopa y solución con bandas.

    `exclude`: palabras que no se marcan en la solución (p. ej. la Ruta Secreta).
    """
    buffer = BytesIO()
    layout = page_layout(len(grid), len(grid[0]), words_display)
    c = _new_canvas(buffer, (layout.page_w, layout.page_h))

    _draw_page(c, layout, "Sopa de Letras", grid, bands=())
    c.showPage()
    _draw_page(c, layout, "Solución", grid, bands=geo.bands_for(placed, layout.cell, exclude))
    c.showPage()

    c.save()
    buffer.seek(0)
    return buffer


def generate_grid_pdf(grid, placed=(), solution=False, exclude=(), cell=GRID_ONLY_CELL):
    """PDF de una página recortada al marco de la cuadrícula (sin título ni lista)."""
    rows, cols = len(grid), len(grid[0])
    frame_w, frame_h = geo.frame_size(rows, cols, cell)
    buffer = BytesIO()
    c = _new_canvas(buffer, (frame_w, frame_h))
    bands = geo.bands_for(placed, cell, exclude) if solution else ()
    draw_grid(c, grid, 0, frame_h, cell, bands)
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer
