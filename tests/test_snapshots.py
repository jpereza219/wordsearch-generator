"""Snapshots deterministas del comportamiento actual de generate_puzzle.

Cada caso genera el puzzle con seed=N y compara la cuadrícula, las posiciones
(placed), la lista impresa, los avisos y el número de intentos con
tests/snapshots/<caso>.json.

Si un cambio en el generador es INTENCIONAL, regenera los snapshots con:

    UPDATE_SNAPSHOTS=1 pytest tests/test_snapshots.py

y revisa el diff de tests/snapshots/ antes de hacer commit.
"""

import json
import os
from pathlib import Path

import pytest

import motor
from cases import CASES, resolve

SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshots"
UPDATE = os.environ.get("UPDATE_SNAPSHOTS") == "1"


def _serialize(case_name, case, extra_chars, allowed_dirs, decoys, result):
    grid, placed, words_display = result.grid, result.placed, result.words_display
    for row in grid:
        for cell in row:
            assert len(cell) == 1 and cell != " ", f"celda inesperada: {cell!r}"
    data = {
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
        "warnings": result.warnings,
        "attempts": result.attempts,
    }
    # Solo los casos con Ruta Secreta llevan estas claves (los snapshots
    # anteriores no cambian).
    if case.get("hidden"):
        data["config"]["hidden"] = case["hidden"]
        data["hidden_words"] = result.hidden_words
    return data


@pytest.mark.parametrize("case_name", sorted(CASES))
def test_snapshot(motor_mod, seeded, case_name):
    case = CASES[case_name]
    allowed_dirs, decoys, extra_chars = resolve(motor_mod, case)
    result = motor.create_puzzle(
        case["words"], case["rows"], case["cols"], allowed_dirs, extra_chars, decoys, seed=case["seed"],
        hidden_words=case.get("hidden", []),
    )
    actual = _serialize(case_name, case, extra_chars, allowed_dirs, decoys, result)

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
