"""Snapshots deterministas del comportamiento actual de generate_puzzle.

Cada caso fija random.seed(N), genera el puzzle y compara la cuadrícula, las
posiciones (placed) y la lista impresa con tests/snapshots/<caso>.json.

Si un cambio en el generador es INTENCIONAL, regenera los snapshots con:

    UPDATE_SNAPSHOTS=1 pytest tests/test_snapshots.py

y revisa el diff de tests/snapshots/ antes de hacer commit.
"""

import json
import os
from pathlib import Path

import pytest

from cases import CASES, resolve

SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshots"
UPDATE = os.environ.get("UPDATE_SNAPSHOTS") == "1"


def _serialize(case_name, case, extra_chars, allowed_dirs, decoys, grid, placed, words_display):
    for row in grid:
        for cell in row:
            assert len(cell) == 1 and cell != " ", f"celda inesperada: {cell!r}"
    return {
        "case": case_name,
        "config": {
            "seed": case["seed"],
            "rows": case["rows"],
            "cols": case["cols"],
            "difficulty": case["difficulty"],
            "allowed_dirs": allowed_dirs,
            "decoy_fragments": decoys,
            "specials_ui": case["specials_ui"],
            "extra_chars": extra_chars,
            "words": case["words"],
        },
        # Una fila por cadena, celdas separadas por un espacio.
        "grid": [" ".join(row) for row in grid],
        "placed": [{"word": w, "coords": [list(rc) for rc in coords]} for w, coords in placed],
        "words_display": words_display,
    }


@pytest.mark.parametrize("case_name", sorted(CASES))
def test_snapshot(app, seeded, case_name):
    case = CASES[case_name]
    allowed_dirs, decoys, extra_chars = resolve(app, case)
    grid, placed, words_display = seeded(
        case["seed"], case["words"], case["rows"], case["cols"], allowed_dirs, extra_chars, decoys
    )
    actual = _serialize(case_name, case, extra_chars, allowed_dirs, decoys, grid, placed, words_display)

    path = SNAPSHOT_DIR / f"{case_name}.json"
    if UPDATE:
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(actual, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return

    assert path.exists(), (
        f"Falta el snapshot {path.name}. Créalo con: UPDATE_SNAPSHOTS=1 pytest tests/test_snapshots.py"
    )
    expected = json.loads(path.read_text(encoding="utf-8"))
    assert actual == expected, (
        "La salida del generador cambió. Si el cambio es intencional, regenera con "
        "UPDATE_SNAPSHOTS=1 pytest tests/test_snapshots.py y revisa el diff."
    )
