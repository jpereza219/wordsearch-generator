"""Fallos de la auditoría (commit 0c32c04), ya corregidos en el paso 3.

Hasta el paso 2 estas pruebas eran xfail(strict=True). Ahora deben pasar.
"""

import unicodedata

import pytest

from motor import DIRS, PuzzleError, create_puzzle, find_occurrences

ALL_DIRS = list(DIRS)


def test_problema1_palabra_que_no_cabe_no_se_omite_en_silencio(seeded):
    # FRANCISCOMORAZÁN tiene 16 celdas y la cuadrícula es 15x15: antes se
    # omitía sin aviso y seguía en la lista. Ahora es un error que la nombra.
    words = ["FRANCISCO MORAZÁN", "COPÁN"]
    with pytest.raises(PuzzleError) as exc:
        seeded(0, words, 15, 15, ["H", "V"], "", 0)
    assert any("FRANCISCO MORAZÁN" in m and "16" in m and "15" in m for m in exc.value.errors)


@pytest.mark.parametrize("seed", range(50))
def test_problema1_nunca_falta_una_palabra_de_la_lista(seeded, seed):
    words = ["FRANCISCO MORAZÁN", "ISLAS DE LA BAHÍA", "COPÁN", "OLANCHO", "YORO"]
    grid, placed, words_display = seeded(seed, words, 20, 20, ["H", "HR", "V", "VR", "D1", "D4"], "", 0)
    placed_words = {w for w, _ in placed}
    for shown in words_display:
        assert shown.replace(" ", "").upper() in placed_words


def test_problema5_nfd_ocupa_lo_mismo_que_nfc(seeded):
    nfd = unicodedata.normalize("NFD", "MORAZÁN")
    assert len(nfd) == 8  # M O R A Z A ◌́ N
    grid, placed, words_display = seeded(1, [nfd], 15, 15, ["H"], "", 0)
    assert len(placed) == 1
    word, coords = placed[0]
    assert word == "MORAZÁN"
    assert len(coords) == 7, f"MORAZÁN ocupa {len(coords)} celdas: {[grid[r][c] for r, c in coords]}"
    assert words_display == ["MORAZÁN"]


@pytest.mark.parametrize("decoys", [0, 16])
@pytest.mark.parametrize("seed", range(20))
def test_problema6_sin_copias_extra(seeded, seed, decoys):
    # Antes, con la semilla 0, LUZ aparecía 3 veces. ("TÉ" se cambió por "PEZ"
    # porque ahora el largo mínimo es 3.)
    words = ["SOL", "MAR", "RÍO", "PAN", "OSO", "ORO", "LUZ", "AVE", "SAL", "PEZ"]
    grid, placed, _ = seeded(seed, words, 15, 15, ALL_DIRS, "", decoys)
    duplicated = {w: len(find_occurrences(grid, w)) for w, _ in placed}
    assert {w: n for w, n in duplicated.items() if n != 1} == {}


def test_custom_sin_direcciones_no_usa_las_8_en_silencio():
    words = ["HONDURAS", "BALEADA", "MARIMBA", "IGUANA", "TAMALES"]
    with pytest.raises(PuzzleError) as exc:
        create_puzzle(words, 15, 15, [], "", 0, seed=0)
    assert any("dirección" in m for m in exc.value.errors)
