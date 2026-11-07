"""Propiedades que deben cumplirse siempre, para varias semillas.

Se recorren las mismas configuraciones de los snapshots con 25 semillas cada una.
"""

import string

import pytest

from cases import CASES, resolve

SEEDS = range(25)


def _generate(motor_mod, seeded, case, seed):
    allowed_dirs, decoys, extra_chars = resolve(motor_mod, case)
    grid, placed, words_display = seeded(
        seed, case["words"], case["rows"], case["cols"], allowed_dirs, extra_chars, decoys
    )
    return grid, placed, words_display, allowed_dirs, extra_chars


def _params():
    return [pytest.param(name, seed, id=f"{name}-seed{seed}") for name in sorted(CASES) for seed in SEEDS]


@pytest.mark.parametrize("case_name,seed", _params())
def test_dimensiones(motor_mod, seeded, case_name, seed):
    case = CASES[case_name]
    grid, *_ = _generate(motor_mod, seeded, case, seed)
    assert len(grid) == case["rows"]
    assert all(len(row) == case["cols"] for row in grid)
    assert all(isinstance(cell, str) and len(cell) == 1 for row in grid for cell in row)


@pytest.mark.parametrize("case_name,seed", _params())
def test_palabras_colocadas_en_sus_posiciones(motor_mod, seeded, case_name, seed):
    case = CASES[case_name]
    grid, placed, *_ = _generate(motor_mod, seeded, case, seed)
    expected_words = {w.replace(" ", "").strip().upper() for w in case["words"]}
    for word, coords in placed:
        assert word in expected_words
        assert len(coords) == len(word)
        assert "".join(grid[r][c] for r, c in coords) == word


@pytest.mark.parametrize("case_name,seed", _params())
def test_solo_direcciones_habilitadas(motor_mod, seeded, case_name, seed):
    case = CASES[case_name]
    grid, placed, _, allowed_dirs, _ = _generate(motor_mod, seeded, case, seed)
    allowed_vectors = {motor_mod.DIRS[k] for k in allowed_dirs}
    for word, coords in placed:
        assert len(coords) >= 2, "las palabras de prueba tienen 2+ letras"
        dr, dc = coords[1][0] - coords[0][0], coords[1][1] - coords[0][1]
        assert (dr, dc) in allowed_vectors, f"{word} usa dirección {(dr, dc)} no habilitada"
        for i, (r, c) in enumerate(coords):
            assert (r, c) == (coords[0][0] + dr * i, coords[0][1] + dc * i), f"{word} no es recta"


@pytest.mark.parametrize("case_name,seed", _params())
def test_relleno_solo_az_mas_especiales(motor_mod, seeded, case_name, seed):
    """Las celdas que no pertenecen a ninguna palabra usan solo A–Z + especiales.

    Nota: los señuelos (decoys) toman letras de las palabras ya colocadas
    (motor.py, add_decoy_fragments). En estas configuraciones todas las letras de las palabras
    están en A–Z + especiales, así que la propiedad se cumple igualmente.
    """
    case = CASES[case_name]
    grid, placed, _, _, extra_chars = _generate(motor_mod, seeded, case, seed)
    alphabet = set(string.ascii_uppercase) | set(extra_chars.upper())
    word_cells = {rc for _, coords in placed for rc in coords}
    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            if (r, c) not in word_cells:
                assert cell in alphabet, f"relleno {cell!r} fuera del alfabeto en {(r, c)}"
