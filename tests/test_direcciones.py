"""Reparto de direcciones (paso 3b): variedad editorial en cada puzzle."""

import collections

import pytest

import motor
from motor import DIAGONAL_DIRS, DIRS, REVERSED_DIRS, create_puzzle, direction_of

ALL = list(DIRS)
MED = ["H", "HR", "V", "VR", "D1", "D4"]

DEPTOS17 = [
    "ATLÁNTIDA", "COLÓN", "COMAYAGUA", "COPÁN", "CORTÉS", "CHOLUTECA", "EL PARAÍSO",
    "GRACIAS A DIOS", "INTIBUCÁ", "ISLAS DE LA BAHÍA", "LA PAZ", "LEMPIRA", "OCOTEPEQUE",
    "OLANCHO", "SANTA BÁRBARA", "VALLE", "YORO",
]
SHORT16 = [
    "COPÁN", "YORO", "OLANCHO", "LEMPIRA", "VALLE", "COLÓN", "CORTÉS", "INTIBUCÁ",
    "ROATÁN", "UTILA", "GUANAJA", "CEIBA", "DANLÍ", "JUTICALPA", "SIGUATEPEQUE", "TELA",
]


def _dirs(result):
    return collections.Counter(direction_of(coords) for _, coords in result.placed)


# --------------------------------------------------------------- asignación

@pytest.mark.parametrize("dirs", [ALL, MED, ["H", "V", "D1"]])
@pytest.mark.parametrize("seed", range(20))
def test_asignacion_pareja_si_todas_caben(dirs, seed):
    import random
    order = sorted([motor.clean_word(w) for w in SHORT16], key=len, reverse=True)
    preferred = motor.assign_directions(order, 20, 20, dirs, random.Random(seed))
    counts = collections.Counter(preferred)
    assert set(counts) == set(dirs)
    assert max(counts.values()) - min(counts.values()) <= 1


def test_asignacion_respeta_lo_que_cabe_en_cuadricula_no_cuadrada():
    import random
    # 6 filas x 20 columnas: una palabra de 12 letras solo cabe en H/HR.
    order = ["ABCDEFGHIJKL", "SOL", "MAR", "PAN"]
    for seed in range(50):
        preferred = motor.assign_directions(order, 6, 20, ALL, random.Random(seed))
        assert preferred[0] in ("H", "HR")


# --------------------------------------------------------------- colocación

@pytest.mark.parametrize("seed", range(30))
def test_reparto_parejo_en_cuadricula_holgada(seed):
    # 16 palabras cortas, 8 direcciones, 20x20: hay sitio de sobra, así que cada
    # palabra queda en su dirección preferida y cada dirección recibe exactamente 2.
    r = create_puzzle(SHORT16, 20, 20, ALL, "ÑÁÉÍÓÚÜ", 0, seed=seed)
    assert sorted(_dirs(r).values()) == [2] * 8


@pytest.mark.parametrize(
    "words,size,dirs",
    [
        (DEPTOS17, 15, ALL),
        (DEPTOS17, 15, MED),
        (SHORT16[:8], 10, ALL),
        (SHORT16[:6], 10, MED),
    ],
    ids=["17 deptos 15x15 8dir", "17 deptos 15x15 Medium", "8 palabras 10x10 8dir", "6 palabras 10x10 Medium"],
)
def test_siempre_hay_diagonal_y_palabra_al_reves(words, size, dirs):
    for seed in range(100):
        r = create_puzzle(words, size, size, dirs, "ÑÁÉÍÓÚÜ", 6, seed=seed)
        used = set(_dirs(r))
        assert used & set(DIAGONAL_DIRS), f"semilla {seed}: sin diagonales {dict(_dirs(r))}"
        assert used & set(REVERSED_DIRS), f"semilla {seed}: sin palabras al revés {dict(_dirs(r))}"
        assert not any("diagonal y al revés" in w for w in r.warnings)


def test_con_8_direcciones_casi_siempre_6_o_mas():
    distinct = [len(_dirs(create_puzzle(DEPTOS17, 15, 15, ALL, "ÑÁÉÍÓÚÜ", 6, seed=s))) for s in range(200)]
    assert sum(d >= 6 for d in distinct) / len(distinct) >= 0.95


def test_palabra_que_no_cabe_en_su_direccion_preferida_va_a_otra(monkeypatch):
    # Se fuerza V como preferida para una palabra de 5 letras en 3 filas: en V no
    # hay ninguna posición posible, así que debe colocarse en H.
    monkeypatch.setattr(motor, "assign_directions", lambda order, rows, cols, dirs, rng: ["V"] * len(order))
    r = create_puzzle(["CEIBA"], 3, 7, ["V", "H"], "", 0, seed=1)
    assert [direction_of(c) for _, c in r.placed] == ["H"]


def test_sin_exigencia_si_ninguna_cabe_en_diagonal():
    # 10x20: palabras de 11-12 letras solo caben en horizontal. No se puede pedir
    # diagonales; el puzzle se genera sin aviso de variedad.
    words = ["TEGUCIGALPA", "COMAYAGUELA", "SANPEDROSULA", "CHOLUTECANA",
             "OCOTEPEQUES", "SANTABARBARA", "DANLIOLANCHO", "PUERTOCORTES"]
    r = create_puzzle(words, 10, 20, ALL, "", 0, seed=1)
    assert set(_dirs(r)) <= {"H", "HR"}
    assert set(_dirs(r)) & set(REVERSED_DIRS)  # HR sí es posible y aparece
    assert not any("diagonal y al revés" in w for w in r.warnings)


def test_sin_exigencia_con_menos_palabras_que_direcciones():
    goals = motor._variety_goals(["SOL", "MAR"], 15, 15, ALL)
    assert goals == (False, False)


def test_determinismo_con_reparto():
    a = create_puzzle(DEPTOS17, 15, 15, ALL, "ÑÁÉÍÓÚÜ", 6, seed=77)
    b = create_puzzle(DEPTOS17, 15, 15, ALL, "ÑÁÉÍÓÚÜ", 6, seed=77)
    assert (a.grid, a.placed, a.warnings, a.attempts) == (b.grid, b.placed, b.warnings, b.attempts)
