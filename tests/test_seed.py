"""Semilla por puzzle: generate_puzzle usa su propia instancia random.Random(seed)."""

import random

import pytest

import motor
from cases import CASES, resolve


def _gen(case_name, seed):
    case = CASES[case_name]
    allowed_dirs, decoys, extra_chars = resolve(motor, case)
    return motor.generate_puzzle(
        case["words"], case["rows"], case["cols"], allowed_dirs, extra_chars, decoys, seed=seed
    )


@pytest.mark.parametrize("case_name", sorted(CASES))
def test_misma_semilla_mismo_puzzle(case_name):
    for seed in range(10):
        assert _gen(case_name, seed) == _gen(case_name, seed)


@pytest.mark.parametrize("case_name", sorted(CASES))
def test_semillas_distintas_puzzles_distintos(case_name):
    grids = {tuple(map(tuple, _gen(case_name, seed)[0])) for seed in range(20)}
    assert len(grids) == 20


@pytest.mark.parametrize("seed", [7, None])
def test_no_altera_el_random_global(seed):
    random.seed(12345)
    before = random.getstate()
    _gen("departamentos_20x20_custom8", seed)
    assert random.getstate() == before


def test_no_usa_funciones_del_random_global(monkeypatch):
    def prohibido(*args, **kwargs):
        raise AssertionError("se usó el random global")

    for name in ("random", "choice", "choices", "randrange", "randint", "shuffle", "sample", "seed"):
        monkeypatch.setattr(random, name, prohibido)
    # Usa colocación, señuelos (6) y relleno.
    grid, placed, _ = _gen("departamentos_20x20_custom8", 3)
    assert placed


def test_semilla_none_genera_puzzles_nuevos():
    a = _gen("paises_15x15_custom", None)[0]
    b = _gen("paises_15x15_custom", None)[0]
    assert a != b
