"""Fallos conocidos (auditoría del generador, informe sobre el commit 0c32c04).

Cada prueba describe el comportamiento DESEADO y está marcada como
xfail(strict=True): hoy falla. Cuando un paso futuro corrija el fallo, la prueba
pasará, pytest la reportará como XPASS y, por ser strict, la sesión fallará.
En ese momento hay que quitar el marcador xfail y dejarla como prueba normal.
"""

import unicodedata

import pytest

ALL_DIRS = ["H", "HR", "V", "VR", "D1", "D2", "D3", "D4"]


def _occurrences(grid, word, dirs):
    """Conjuntos distintos de celdas donde se lee `word` (un palíndromo cuenta una vez)."""
    rows, cols = len(grid), len(grid[0])
    found = set()
    for r in range(rows):
        for c in range(cols):
            for dr, dc in dirs:
                cells = [(r + dr * i, c + dc * i) for i in range(len(word))]
                if all(0 <= rr < rows and 0 <= cc < cols for rr, cc in cells) and all(
                    grid[rr][cc] == ch for (rr, cc), ch in zip(cells, word)
                ):
                    found.add(frozenset(cells))
    return found


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Problema 1: una palabra que no cabe se omite sin aviso y sigue en la lista impresa (app.py:100, 105)",
)
def test_problema1_palabra_que_no_cabe_no_se_omite_en_silencio(seeded):
    # FRANCISCOMORAZÁN tiene 16 celdas y la cuadrícula es 15x15: se descarta en app.py:105.
    words = ["FRANCISCO MORAZÁN", "COPÁN"]
    grid, placed, words_display = seeded(0, words, 15, 15, ["H", "V"], "", 0)
    placed_words = {w for w, _ in placed}
    for shown in words_display:
        assert shown.replace(" ", "").upper() in placed_words, (
            f"{shown!r} se imprime en la lista pero no está en la cuadrícula"
        )


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Problema 5: no se aplica NFC; la tilde combinante ocupa su propia celda",
)
def test_problema5_nfd_ocupa_lo_mismo_que_nfc(seeded):
    nfd = unicodedata.normalize("NFD", "MORAZÁN")
    assert len(nfd) == 8  # M O R A Z A ◌́ N
    grid, placed, _ = seeded(1, [nfd], 15, 15, ["H"], "", 0)
    assert len(placed) == 1
    word, coords = placed[0]
    assert len(coords) == 7, f"MORAZÁN ocupa {len(coords)} celdas: {[grid[r][c] for r, c in coords]}"


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Problema 6: el relleno aleatorio puede formar una copia extra de una palabra corta",
)
def test_problema6_sin_copias_extra(app, seeded):
    words = ["SOL", "MAR", "RÍO", "PAN", "OSO", "ORO", "LUZ", "AVE", "SAL", "TÉ"]
    # Con la semilla 0, LUZ aparece 3 veces en la cuadrícula (verificado en la auditoría).
    grid, placed, _ = seeded(0, words, 15, 15, ALL_DIRS, "", 0)
    vectors = list(app.DIRS.values())
    duplicated = {w: len(_occurrences(grid, w, vectors)) for w, _ in placed}
    duplicated = {w: n for w, n in duplicated.items() if n > 1}
    assert not duplicated, f"palabras con copias extra: {duplicated}"


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Custom sin direcciones usa las 8 direcciones sin avisar (app.py:113)",
)
def test_custom_sin_direcciones_no_usa_las_8_en_silencio(app, seeded):
    words = ["HONDURAS", "BALEADA", "MARIMBA", "IGUANA", "TAMALES"]
    try:
        grid, placed, _ = seeded(0, words, 15, 15, [], "", 0)
    except ValueError:
        return  # Comportamiento aceptable: rechazar la configuración vacía.
    # Si no se rechaza, no se debería usar ninguna dirección (no hay habilitadas).
    assert placed == [], f"se colocaron {len(placed)} palabras sin direcciones habilitadas"
