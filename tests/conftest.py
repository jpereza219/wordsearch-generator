"""Configuración compartida de las pruebas.

motor.py y pdf.py se importan directamente (no dependen de Streamlit).
app.py solo contiene la interfaz; se importa en el "bare mode" de Streamlit
únicamente en tests/test_imports.py, para confirmar que sigue cargando.
"""

import pytest

import motor
import pdf

# Valor por defecto del campo "Caracteres especiales" en la interfaz (app.py).
DEFAULT_SPECIALS_UI = "Ñ,Á,É,Í,Ó,Ú,Ü, ’"

# Direcciones por defecto del multiselect de "Custom" y valor por defecto
# del slider de señuelos (app.py).
CUSTOM_DEFAULT_DIRS = ["H", "HR", "V", "VR", "D1", "D4"]
CUSTOM_DEFAULT_DECOYS = 6


@pytest.fixture(scope="session")
def motor_mod():
    return motor


@pytest.fixture(scope="session")
def pdf_mod():
    return pdf


@pytest.fixture
def seeded():
    """Devuelve una función que genera un puzzle con una semilla dada.

    La semilla N equivale exactamente a `random.seed(N)` sobre el código
    anterior (ver tests/test_seed.py), por eso los snapshots no cambian.
    """

    def _generate(seed, words, rows, cols, allowed_dirs, extra_chars, decoys):
        return motor.generate_puzzle(
            words=words,
            rows=rows,
            cols=cols,
            allowed_dirs=allowed_dirs,
            extra_chars=extra_chars,
            decoy_fragments=decoys,
            seed=seed,
        )

    return _generate
