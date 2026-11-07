"""Validación previa (2a–2f) y error de colocación (3)."""

import pytest

import motor
from motor import DIRS, PuzzleError, create_puzzle, find_occurrences

ALL_DIRS = list(DIRS)
MED = ["H", "HR", "V", "VR", "D1", "D4"]


def _errors(*args, **kwargs):
    with pytest.raises(PuzzleError) as exc:
        create_puzzle(*args, **kwargs)
    return exc.value.errors


# 2a. Repetidas -------------------------------------------------------------

def test_2a_repetidas_se_eliminan_y_se_avisa():
    r = create_puzzle(["COPÁN", "Copán", "co pán", "YORO"], 15, 15, MED, "Á", 0, seed=1)
    assert r.words_display == ["COPÁN", "YORO"]
    assert [w for w, _ in r.placed].count("COPÁN") == 1
    assert any("repetidas" in w and "Copán" in w and "co pán" in w for w in r.warnings)


# 2b. Largo mínimo ----------------------------------------------------------

def test_2b_palabras_cortas_son_error_que_las_nombra():
    errors = _errors(["SOL", "TÉ", "OK", "MAR"], 15, 15, MED, "", 0, seed=1)
    assert any("TÉ" in e and "OK" in e for e in errors)
    assert not any("SOL" in e for e in errors)


def test_2b_largo_cuenta_celdas_sin_espacios():
    errors = _errors(["A B"], 15, 15, MED, "", 0, seed=1)  # "AB": 2 celdas
    assert any("A B" in e for e in errors)


# 2c. No caben --------------------------------------------------------------

def test_2c_no_cabe_nombra_largo_y_maximo():
    errors = _errors(["FRANCISCO MORAZÁN", "SANTA ROSA DE COPÁN", "YORO"], 15, 15, MED, "", 0, seed=1)
    assert len(errors) == 2
    assert all("16 letras" in e and "es 15" in e for e in errors)


@pytest.mark.parametrize(
    "dirs,rows,cols,limit",
    [
        (["H"], 10, 20, 20),        # horizontal: columnas
        (["V", "VR"], 10, 20, 10),  # vertical: filas
        (["D1"], 10, 20, 10),       # diagonal: mínimo
        (["V", "D1", "H"], 10, 20, 20),
    ],
)
def test_2c_maximo_segun_direcciones(dirs, rows, cols, limit):
    assert motor.max_word_length(rows, cols, dirs) == limit
    create_puzzle(["A" * limit], rows, cols, dirs, "", 0, seed=1)
    errors = _errors(["A" * (limit + 1)], rows, cols, dirs, "", 0, seed=1)
    assert any(f"es {limit}" in e for e in errors)


def test_2c_no_genera_nada():
    # Una palabra válida y una que no cabe: error, sin resultado parcial.
    with pytest.raises(PuzzleError):
        motor.generate_puzzle(["YORO", "X" * 21], 20, 20, ALL_DIRS, "", 0, seed=1)


# 2d. Sin direcciones -------------------------------------------------------

def test_2d_sin_direcciones_es_error():
    errors = _errors(["HONDURAS"], 15, 15, [], "", 0, seed=1)
    assert any("dirección" in e for e in errors)


# 2e. Contenidas ------------------------------------------------------------

def test_2e_contenida_es_aviso_y_ambas_se_colocan():
    words = ["SANTA ROSA DE COPÁN", "COPÁN"]
    r = create_puzzle(words, 20, 20, MED, "Á", 0, seed=3)
    assert any("COPÁN" in w and "SANTA ROSA DE COPÁN" in w for w in r.warnings)
    assert {w for w, _ in r.placed} == {"SANTAROSADECOPÁN", "COPÁN"}
    # COPÁN aparece 2 veces (una propia y otra dentro de la larga); no más.
    assert len(find_occurrences(r.grid, "COPÁN")) == 2
    own = tuple(sorted(dict(r.placed)["COPÁN"]))
    long_cells = set(dict(r.placed)["SANTAROSADECOPÁN"])
    assert not set(own) <= long_cells, "COPÁN no debe quedar solo dentro de la larga"


def test_2e_al_reves_solo_se_avisa_con_direcciones_opuestas():
    words = ["AMOR", "ROMAS"]  # AMOR al revés = ROMA, dentro de ROMAS
    con = create_puzzle(words, 15, 15, ["H", "HR"], "", 0, seed=1)
    sin = create_puzzle(words, 15, 15, ["H", "V"], "", 0, seed=1)
    assert any("al revés" in w for w in con.warnings)
    assert not any("al revés" in w for w in sin.warnings)


# 2f. Letras fuera del alfabeto ---------------------------------------------

def test_2f_letra_fuera_del_alfabeto_es_aviso():
    r = create_puzzle(["NIÑO", "PUCA-OPALACA", "MORAZÁN"], 15, 15, MED, "ÁÉ", 0, seed=1)
    joined = "\n".join(r.warnings)
    assert "«Ñ» de NIÑO" in joined
    assert "«-» de PUCA-OPALACA" in joined
    assert "MORAZÁN" not in joined  # Á sí está en el campo de especiales


def test_2f_especiales_tambien_se_normalizan():
    import unicodedata
    nfd_specials = unicodedata.normalize("NFD", "Ñ")
    r = create_puzzle(["NIÑO"], 15, 15, MED, nfd_specials, 0, seed=1)
    assert not any("Ñ" in w for w in r.warnings)


# 3. Error de colocación ----------------------------------------------------

def test_3_error_si_no_se_puede_colocar():
    # 6 palabras de 5 letras, solo horizontal, 5 filas y sin letras en común
    # por posición: la sexta nunca cabe.
    words = ["ABCDE", "FGHIJ", "KLMNO", "PQRST", "UVWXY", "ZABCD"]
    errors = _errors(words, 5, 5, ["H"], "", 0, seed=1)
    assert any("No se pudieron colocar" in e for e in errors)


def test_3_reinicia_si_la_copia_esta_hecha_con_letras_de_palabras():
    # ABC se lee en la fila 0 con letras de tres palabras verticales distintas:
    # no hay celdas de relleno que cambiar, así que _fix_copies pide reiniciar.
    grid = [list(row) for row in ["ABCQ", "XYZQ", "XYZQ", "ABCQ"]]
    placed = [
        ("AXX", [(0, 0), (1, 0), (2, 0)]),
        ("BYY", [(0, 1), (1, 1), (2, 1)]),
        ("CZZ", [(0, 2), (1, 2), (2, 2)]),
        ("ABC", [(3, 0), (3, 1), (3, 2)]),
    ]
    import random
    assert motor._fix_copies(grid, placed, "Q", random.Random(0)) is False


def test_4_copia_con_relleno_se_corrige():
    import random
    grid = [list(row) for row in ["SOLQ", "QQQQ", "SOLQ", "QQQQ"]]
    placed = [("SOL", [(0, 0), (0, 1), (0, 2)])]
    assert motor._fix_copies(grid, placed, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", random.Random(0)) is True
    assert len(find_occurrences(grid, "SOL")) == 1


# Determinismo --------------------------------------------------------------

def test_5_misma_semilla_mismo_resultado_con_reintentos():
    words = ["FRANCISCO MORAZÁN", "ISLAS DE LA BAHÍA", "SANTA BÁRBARA", "OCOTEPEQUE", "SOL", "MAR"]
    a = create_puzzle(words, 17, 17, ALL_DIRS, "ÁÍ", 16, seed=99)
    b = create_puzzle(words, 17, 17, ALL_DIRS, "ÁÍ", 16, seed=99)
    assert (a.grid, a.placed, a.warnings, a.attempts) == (b.grid, b.placed, b.warnings, b.attempts)
