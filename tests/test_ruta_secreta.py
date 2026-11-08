"""Paso 5: palabras ocultas (Ruta Secreta) y ficha del puzzle."""

import copy
import io
import json
import xml.etree.ElementTree as ET
import zipfile

import pytest

import ficha as fichamod
import motor
import pdf
import salidas
from motor import DIRS, PuzzleError, create_puzzle, find_occurrences

SVG = "{http://www.w3.org/2000/svg}"
ALL = list(DIRS)
PAISES = ["BELICE", "COLOMBIA", "CUBA", "EL SALVADOR", "GUATEMALA", "ISLAS CAIMÁN", "JAMAICA", "MÉXICO", "NICARAGUA"]
CONFIG = dict(rows=15, cols=15, allowed_dirs=ALL, extra_chars="ÑÁÉÍÓÚÜ", decoy_fragments=6)


def _make(seed=505, hidden=("GRACIAS",), words=PAISES, **over):
    cfg = {**CONFIG, **over}
    return create_puzzle(words, cfg["rows"], cfg["cols"], cfg["allowed_dirs"], cfg["extra_chars"],
                         cfg["decoy_fragments"], seed=seed, hidden_words=list(hidden))


def _ficha(result, seed=505, hidden=("GRACIAS",), words=PAISES):
    return fichamod.build_ficha(
        result, seed=seed, rows=15, cols=15, allowed_dirs=ALL, decoys=6, extra_chars="ÑÁÉÍÓÚÜ",
        words=list(words), hidden_words=list(hidden), difficulty="Custom",
        specials_field="ÑÁÉÍÓÚÜ", title="Prueba",
    )


def _bands(svg_bytes, cls="banda"):
    root = ET.fromstring(svg_bytes)
    return [r.get("data-palabra") for r in root.iter(SVG + "rect") if r.get("class") == cls]


# ------------------------------------------------------------- colocación

@pytest.mark.parametrize("seed", range(40))
def test_oculta_colocada_una_sola_vez_y_fuera_de_la_lista(seed):
    r = _make(seed)
    assert r.hidden_words == ["GRACIAS"]
    assert "GRACIAS" in {w for w, _ in r.placed}
    assert [w for w, _ in r.hidden_placed] == ["GRACIAS"]
    assert "GRACIAS" not in {w for w, _ in r.visible_placed}
    assert all(motor.clean_word(d) != "GRACIAS" for d in r.words_display)
    assert len(r.visible_placed) == len(r.words_display) == len(PAISES)
    assert len(find_occurrences(r.grid, "GRACIAS")) == 1
    coords = dict(r.placed)["GRACIAS"]
    assert "".join(r.grid[a][b] for a, b in coords) == "GRACIAS"


def test_varias_ocultas():
    r = _make(7, hidden=["GRACIAS", "POR", "JUGAR"])
    assert r.hidden_words == ["GRACIAS", "POR", "JUGAR"]
    for w in r.hidden_words:
        assert len(find_occurrences(r.grid, w)) == 1


def test_sin_ocultas_resultado_identico():
    a = create_puzzle(PAISES, 15, 15, ALL, "ÑÁÉÍÓÚÜ", 6, seed=99)
    b = create_puzzle(PAISES, 15, 15, ALL, "ÑÁÉÍÓÚÜ", 6, seed=99, hidden_words=[])
    assert (a.grid, a.placed, a.words_display, a.warnings) == (b.grid, b.placed, b.words_display, b.warnings)
    assert b.hidden_words == [] and b.visible_placed == b.placed


def test_determinismo_con_ocultas():
    a, b = _make(31), _make(31)
    assert (a.grid, a.placed, a.warnings) == (b.grid, b.placed, b.warnings)


# ------------------------------------------------------------- validaciones

def _errors(**kw):
    with pytest.raises(PuzzleError) as exc:
        _make(**kw)
    return exc.value.errors


def test_oculta_igual_a_una_de_la_lista_es_error():
    errors = _errors(hidden=["cuba"])
    assert any("oculta «cuba» ya está en la lista" in e for e in errors)


def test_oculta_demasiado_larga_es_error():
    errors = _errors(hidden=["SAN PEDRO SULA CORTES"])  # 18 letras en 15x15
    assert any("«SAN PEDRO SULA CORTES» (oculta) tiene 18 letras" in e and "es 15" in e for e in errors)


def test_oculta_demasiado_corta_es_error():
    errors = _errors(hidden=["SÍ"])
    assert any("SÍ (oculta)" in e for e in errors)


def test_oculta_dentro_de_una_de_la_lista_avisa_nombrando_ambas():
    r = _make(hidden=["SALVA"])  # dentro de EL SALVADOR
    assert any("«SALVA» (oculta) está dentro de «EL SALVADOR»" in w for w in r.warnings)
    # Aparece en su colocación y dentro de EL SALVADOR, nada más.
    assert len(find_occurrences(r.grid, "SALVA")) == 2


def test_una_de_la_lista_dentro_de_la_oculta_avisa_nombrando_ambas():
    r = _make(hidden=["CUBANITOS"])  # CUBA dentro de la oculta
    assert any("«CUBA» está dentro de «CUBANITOS» (oculta)" in w for w in r.warnings)


def test_oculta_con_letra_delatora_avisa():
    r = _make(hidden=["NIÑO"], extra_chars="ÁÉ")
    assert any("«Ñ» de NIÑO (oculta)" in w for w in r.warnings)


def test_ocultas_repetidas_avisan():
    r = _make(hidden=["GRACIAS", "gracias"])
    assert r.hidden_words == ["GRACIAS"]
    assert any("ocultas repetidas: gracias" in w for w in r.warnings)


# ------------------------------------------------------------- salidas

@pytest.fixture(scope="module")
def puzzle():
    return _make(505)


@pytest.fixture(scope="module")
def files(puzzle):
    return salidas.puzzle_files(puzzle.grid, puzzle.placed, puzzle.words_display, 505,
                                hidden=puzzle.hidden_words, ficha=_ficha(puzzle))


def test_solucion_del_libro_no_marca_la_oculta(files, puzzle):
    names = salidas.file_names(505)
    book = _bands(files[names["solucion_svg"]])
    assert "GRACIAS" not in book
    assert sorted(book) == sorted(w for w, _ in puzzle.visible_placed)
    assert b"USO INTERNO" not in files[names["solucion_svg"]]
    # PDF de 2 páginas y PDF de cuadrícula: iguales a los generados excluyendo la oculta.
    excl = ["GRACIAS"]
    assert files[names["pdf"]] == pdf.generate_pdf(puzzle.grid, puzzle.placed, puzzle.words_display, excl).getvalue()
    assert files[names["pdf"]] != pdf.generate_pdf(puzzle.grid, puzzle.placed, puzzle.words_display).getvalue()
    assert files[names["solucion_pdf"]] == pdf.generate_grid_pdf(
        puzzle.grid, puzzle.placed, solution=True, exclude=excl).getvalue()


def test_lista_impresa_sin_la_oculta(files):
    from pypdf import PdfReader
    text = PdfReader(io.BytesIO(files[salidas.file_names(505)["pdf"]])).pages[0].extract_text()
    assert "GUATEMALA" in text
    # En la cuadrícula las letras salen separadas por espacios: "GRACIAS" seguida
    # solo podría venir de la lista impresa.
    assert "GRACIAS" not in text


def test_solucion_autor_marca_la_oculta(files, puzzle):
    svg = files[salidas.file_names(505)["autor_svg"]]
    assert _bands(svg, "banda-oculta") == ["GRACIAS"]
    assert sorted(_bands(svg)) == sorted(w for w, _ in puzzle.visible_placed)
    root = ET.fromstring(svg)
    label = [t.text for t in root.iter(SVG + "text") if t.get("class") == "uso-interno"]
    assert label == ["USO INTERNO — no imprimir"]
    outline = [r for r in root.iter(SVG + "rect") if r.get("class") == "banda-oculta"][0]
    assert outline.get("fill") == "none" and outline.get("stroke-dasharray")


def test_zip_con_8_archivos(files):
    data = salidas.puzzle_zip(files)
    names = sorted(zipfile.ZipFile(io.BytesIO(data)).namelist())
    assert len(names) == 8
    assert "s505_solucion_autor.svg" in names and "s505_ficha.json" in names


# ------------------------------------------------------------- ficha

def test_ficha_contenido(puzzle):
    f = _ficha(puzzle)
    assert f["motor_version"] == motor.MOTOR_VERSION == "3.0"
    assert f["semilla"] == 505 and (f["filas"], f["columnas"]) == (15, 15)
    assert f["palabras"] == PAISES and f["ocultas"] == ["GRACIAS"] and f["titulo"] == "Prueba"
    assert f["direcciones"] == ALL and f["senuelos"] == 6 and f["dificultad"] == "Custom"
    by_word = {p["palabra"]: p for p in f["colocacion"]}
    assert set(by_word) == {w for w, _ in puzzle.placed}
    assert by_word["GRACIAS"]["oculta"] is True and by_word["CUBA"]["oculta"] is False
    for w, coords in puzzle.placed:
        p = by_word[w]
        assert (p["fila"], p["columna"]) == coords[0]
        assert p["direccion"] == motor.direction_of(coords) and p["largo"] == len(w)
    assert by_word["ISLASCAIMÁN"]["texto"] == "ISLAS CAIMÁN"


@pytest.mark.parametrize("seed", range(100))
def test_ida_y_vuelta(seed):
    hidden = ["GRACIAS"] if seed % 2 else ["GRACIAS", "TOTAL"]
    r = _make(seed, hidden=hidden)
    text = fichamod.ficha_json(_ficha(r, seed=seed, hidden=hidden))
    again = fichamod.regenerate_from_ficha(text)
    assert again.grid == r.grid
    assert again.placed == r.placed


def test_ida_y_vuelta_desde_bytes_del_zip(files, puzzle):
    again = fichamod.regenerate_from_ficha(files["s505_ficha.json"])
    assert again.grid == puzzle.grid


def test_ficha_de_otra_version_da_error_claro(puzzle):
    f = _ficha(puzzle)
    f["motor_version"] = "2.9"
    with pytest.raises(fichamod.FichaError, match=r"versión 2\.9 del motor.*usa la 3\.0"):
        fichamod.regenerate_from_ficha(f)


def test_ficha_alterada_da_error(puzzle):
    f = copy.deepcopy(_ficha(puzzle))
    first = f["cuadricula"][0]
    f["cuadricula"][0] = ("Q" if first[0] != "Q" else "X") + first[1:]
    with pytest.raises(fichamod.FichaError, match="no coincide"):
        fichamod.regenerate_from_ficha(f)


@pytest.mark.parametrize("bad,match", [("{no es json", "JSON válido"), ("[]", "objeto JSON"),
                                       (json.dumps({"formato": "otro"}), "Formato de ficha")])
def test_ficha_invalida(bad, match):
    with pytest.raises(fichamod.FichaError, match=match):
        fichamod.regenerate_from_ficha(bad)
