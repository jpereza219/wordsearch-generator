"""Salidas por puzzle (paso 4): fuente, PDF, SVG, texto, ZIP y geometría de bandas."""

import io
import math
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

import pytest
from pypdf import PdfReader
from reportlab.pdfbase.ttfonts import TTFontFile

import geometria as geo
import motor
import pdf
import salidas
from cases import CASES, resolve

SVG_NS = "{http://www.w3.org/2000/svg}"
LETTER_W, LETTER_H = 612, 792
MARGIN = 36  # 0.5 pulgadas

DEPARTAMENTOS = CASES["departamentos_20x20_custom8"]["words"]


def _case(name):
    case = CASES[name]
    allowed_dirs, decoys, extra = resolve(motor, case)
    return motor.create_puzzle(
        case["words"], case["rows"], case["cols"], allowed_dirs, extra, decoys, seed=case["seed"]
    )


@pytest.fixture(scope="module")
def puzzle():
    return _case("municipios_fm_20x20_custom8")


# ----------------------------------------------------------------- fuente

@pytest.mark.parametrize("font", ["LiberationMono-Regular.ttf", "LiberationMono-Bold.ttf"])
def test_fuente_cubre_los_caracteres(font):
    face = TTFontFile(str(pdf.FONTS_DIR / font))
    needed = "ABCDEFGHIJKLMNOPQRSTUVWXYZÑÁÉÍÓÚÜ-’0123456789"
    assert [ch for ch in needed if ord(ch) not in face.charToGlyph] == []


def test_licencia_de_la_fuente_incluida():
    text = (pdf.FONTS_DIR / "LICENSE-LiberationMono.txt").read_text(encoding="utf-8")
    assert "SIL OPEN FONT LICENSE Version 1.1" in text


# ----------------------------------------------------------------- PDF

def _pdf_outputs(p):
    return {
        "2 páginas": pdf.generate_pdf(p.grid, p.placed, p.words_display).getvalue(),
        "sopa cuadrícula": pdf.generate_grid_pdf(p.grid).getvalue(),
        "solución cuadrícula": pdf.generate_grid_pdf(p.grid, p.placed, solution=True).getvalue(),
    }


def test_pdf_fuente_incrustada_y_sin_helvetica(puzzle):
    for name, data in _pdf_outputs(puzzle).items():
        assert b"/FontFile2" in data, name
        assert b"LiberationMono" in data, name
        assert b"Helvetica" not in data, name


def test_pdf_cuadricula_una_pagina_recortada(puzzle):
    rows, cols = len(puzzle.grid), len(puzzle.grid[0])
    w, h = geo.frame_size(rows, cols, pdf.GRID_ONLY_CELL)
    for solution in (False, True):
        data = pdf.generate_grid_pdf(puzzle.grid, puzzle.placed, solution=solution).getvalue()
        reader = PdfReader(io.BytesIO(data))
        assert len(reader.pages) == 1
        box = reader.pages[0].mediabox
        assert float(box.width) == pytest.approx(w)
        assert float(box.height) == pytest.approx(h)


def test_pdf_cuadricula_texto_en_orden(puzzle):
    """Al extraer el texto, cada fila de la cuadrícula sale en su orden."""
    data = pdf.generate_grid_pdf(puzzle.grid).getvalue()
    text = PdfReader(io.BytesIO(data)).pages[0].extract_text()
    joined = text.replace(" ", "").replace("\n", "")
    assert joined == "".join("".join(row) for row in puzzle.grid)


def _long_list(n):
    return [f"PALABRA NÚMERO {i:02d}" for i in range(n)]


@pytest.mark.parametrize("size", [5, 15, 20, 30, 40])
@pytest.mark.parametrize("words", [DEPARTAMENTOS, _long_list(80)], ids=["18 palabras", "80 palabras"])
def test_layout_dentro_de_margenes_y_sin_pisar_la_lista(size, words):
    layout = pdf.page_layout(size, size, words)
    fx0, fy0, fx1, fy1 = layout.frame_box
    lx0, ly0, lx1, ly1 = layout.list_box
    for x0, y0, x1, y1 in (layout.frame_box, layout.list_box):
        assert x0 >= MARGIN - 1e-6 and y0 >= MARGIN - 1e-6
        assert x1 <= LETTER_W - MARGIN + 1e-6 and y1 <= LETTER_H - MARGIN + 1e-6
    assert layout.title_y + pdf.TITLE_SIZE <= LETTER_H - MARGIN + 1e-6
    # La lista queda a la izquierda o debajo de la cuadrícula, con separación.
    side = lx1 + pdf.LIST_GRID_GAP <= fx0 + 1e-6
    below = ly1 + pdf.LIST_GRID_GAP <= fy0 + 1e-6
    assert side or below
    # Celdas legibles incluso en 40x40.
    assert layout.cell >= 8
    # Cada palabra de la lista cabe en el ancho de su columna.
    for column in layout.list_columns:
        for w in column:
            assert pdf.pdfmetrics.stringWidth(w, pdf.FONT, pdf.LIST_SIZE) <= layout.list_col_w


@pytest.mark.parametrize("size", [5, 15, 20, 30, 40])
def test_pdf_dos_paginas_en_todos_los_tamanos(size):
    words = ["SOL", "MAR", "PAZ"] if size == 5 else [
        w for w in DEPARTAMENTOS if len(w.replace(" ", "")) <= size
    ][:10]
    result = motor.create_puzzle(words, size, size, list(motor.DIRS), "ÑÁÉÍÓÚÜ", 0, seed=size)
    data = pdf.generate_pdf(result.grid, result.placed, result.words_display).getvalue()
    reader = PdfReader(io.BytesIO(data))
    assert len(reader.pages) == 2
    assert "Sopa de Letras" in reader.pages[0].extract_text()
    assert "Solución" in reader.pages[1].extract_text()


# ----------------------------------------------------------------- bandas

DIR_CASES = {
    "H": ((2, 1), (0, 1)), "HR": ((2, 5), (0, -1)), "V": ((1, 2), (1, 0)), "VR": ((5, 2), (-1, 0)),
    "D1": ((1, 1), (1, 1)), "D2": ((5, 5), (-1, -1)), "D3": ((5, 1), (-1, 1)), "D4": ((1, 5), (1, -1)),
}


@pytest.mark.parametrize("key", sorted(DIR_CASES))
def test_banda_coincide_con_primera_y_ultima_celda(key):
    (r0, c0), (dr, dc) = DIR_CASES[key]
    n, cell = 4, 20.0
    coords = [(r0 + dr * i, c0 + dc * i) for i in range(n)]
    band = geo.band_for("SOLO", coords, cell)
    x1, y1 = geo.cell_center(*coords[0], cell)
    x2, y2 = geo.cell_center(*coords[-1], cell)
    assert (band.x1, band.y1, band.x2, band.y2) == pytest.approx((x1, y1, x2, y2))
    assert (band.cx, band.cy) == pytest.approx(((x1 + x2) / 2, (y1 + y2) / 2))
    dist = math.hypot(x2 - x1, y2 - y1)
    assert band.length == pytest.approx(dist + cell)  # media celda por cada extremo
    assert band.height == pytest.approx(geo.BAND_HEIGHT * cell)
    assert band.radius == pytest.approx(band.height / 2)  # extremos redondeados
    expected = math.degrees(math.atan2(dr, dc))  # y hacia abajo
    assert band.angle == pytest.approx(expected)
    # Los extremos del eje de la banda caen media celda más allá de los centros.
    ux, uy = math.cos(math.radians(band.angle)), math.sin(math.radians(band.angle))
    assert (band.cx - ux * band.length / 2, band.cy - uy * band.length / 2) == pytest.approx(
        (x1 - ux * cell / 2, y1 - uy * cell / 2)
    )
    assert (band.cx + ux * band.length / 2, band.cy + uy * band.length / 2) == pytest.approx(
        (x2 + ux * cell / 2, y2 + uy * cell / 2)
    )


def test_banda_cabe_dentro_del_marco(puzzle):
    rows, cols = len(puzzle.grid), len(puzzle.grid[0])
    cell = 24.0
    w, h = geo.frame_size(rows, cols, cell)
    for b in geo.bands_for(puzzle.placed, cell):
        ux, uy = math.cos(math.radians(b.angle)), math.sin(math.radians(b.angle))
        for sign in (-1, 1):
            ex, ey = b.cx + sign * ux * b.length / 2, b.cy + sign * uy * b.length / 2
            assert 0 < ex < w and 0 < ey < h


# ----------------------------------------------------------------- SVG

def _svg(p, **kw):
    return ET.fromstring(salidas.grid_svg(p.grid, p.placed, **kw))


def test_svg_es_xml_valido_y_tiene_texto_real(puzzle):
    for kw in ({}, {"solution": True}):
        root = _svg(puzzle, **kw)
        assert root.tag == SVG_NS + "svg"
        texts = root.iter(SVG_NS + "text")
        letters = [t.text for t in texts]
        assert letters == [ch for row in puzzle.grid for ch in row]


def test_svg_fuente_con_respaldo(puzzle):
    root = _svg(puzzle)
    group = root.find(f"{SVG_NS}g[@class='letras']")
    assert group.get("font-family") == "'Liberation Mono', 'Courier New', monospace"


def test_svg_sopa_sin_bandas_y_solucion_con_una_por_palabra(puzzle):
    sopa = _svg(puzzle)
    sol = _svg(puzzle, solution=True)
    bands = sol.findall(f".//{SVG_NS}rect[@class='banda']")
    assert sopa.findall(f".//{SVG_NS}rect[@class='banda']") == []
    assert len(bands) == len(puzzle.placed)
    assert {b.get("data-palabra") for b in bands} == {w for w, _ in puzzle.placed}
    assert all(float(b.get("fill-opacity")) == geo.BAND_ALPHA for b in bands)


def test_svg_bandas_antes_que_las_letras(puzzle):
    children = [c.get("class") for c in _svg(puzzle, solution=True)]
    assert children.index("bandas") < children.index("letras")


def test_excluir_una_palabra_quita_solo_su_banda(puzzle):
    hidden_display = "LA LIBERTAD"
    hidden = motor.clean_word(hidden_display)
    sol = _svg(puzzle, solution=True, exclude=[hidden_display])
    names = [b.get("data-palabra") for b in sol.findall(f".//{SVG_NS}rect[@class='banda']")]
    assert hidden not in names
    assert sorted(names) == sorted(w for w, _ in puzzle.placed if w != hidden)
    # Las letras siguen en la cuadrícula.
    assert [t.text for t in sol.iter(SVG_NS + "text")] == [ch for row in puzzle.grid for ch in row]
    # Lo mismo en la geometría que usa el PDF.
    assert len(geo.bands_for(puzzle.placed, 20, exclude=[hidden])) == len(puzzle.placed) - 1


def test_excluir_en_el_pdf_de_solucion(puzzle):
    full = pdf.generate_grid_pdf(puzzle.grid, puzzle.placed, solution=True).getvalue()
    hidden = pdf.generate_grid_pdf(puzzle.grid, puzzle.placed, solution=True, exclude=["LA LIBERTAD"]).getvalue()
    assert full != hidden


# ----------------------------------------------------------------- texto

def test_txt_coincide_con_la_cuadricula(puzzle):
    text = salidas.grid_text(puzzle.grid)
    assert text.endswith("\n")
    assert unicodedata.is_normalized("NFC", text)
    lines = text.rstrip("\n").split("\n")
    assert len(lines) == len(puzzle.grid)
    for line, row in zip(lines, puzzle.grid):
        assert line.split(" ") == row


def test_txt_nfd_se_normaliza():
    nfd = unicodedata.normalize("NFD", "Á")
    assert salidas.grid_text([["A", nfd]]) == "A Á\n"


# ----------------------------------------------------------------- archivos y ZIP

def test_puzzle_files_y_zip(puzzle):
    files = salidas.puzzle_files(puzzle.grid, puzzle.placed, puzzle.words_display, seed=404)
    assert sorted(files) == sorted([
        "s404_sopa_de_letras.pdf", "s404_sopa.svg", "s404_solucion.svg",
        "s404_sopa_cuadricula.pdf", "s404_solucion_cuadricula.pdf", "s404_cuadricula.txt",
        "s404_solucion_autor.svg",
    ])  # sin ficha: 6 del libro + solución del autor (con ficha: 8, ver test_ruta_secreta.py)
    data = salidas.puzzle_zip(files)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert sorted(zf.namelist()) == sorted(files)
        for name in files:
            assert zf.read(name) == files[name]
    # Determinista: mismo puzzle, mismos bytes.
    again = salidas.puzzle_files(puzzle.grid, puzzle.placed, puzzle.words_display, seed=404)
    assert again == files
