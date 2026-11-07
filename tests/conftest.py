"""Configuración compartida de las pruebas.

app.py ejecuta la interfaz de Streamlit al importarse (líneas 1-2 y todo el
bloque final a nivel de módulo). Para probar generate_puzzle y generate_pdf
SIN modificar app.py lo importamos en el "bare mode" de Streamlit: fuera de
`streamlit run`, los widgets devuelven su valor por defecto (st.button -> False),
así que la importación no genera ningún puzzle ni abre un servidor.

Se eligió esta opción frente a un mock de `streamlit` porque:
  * no hay que imitar a mano cada widget que usa la interfaz (columns,
    number_input, text_area, selectbox, multiselect, slider, checkbox, ...);
  * se ejecuta el mismo código de interfaz que en producción, así que si una
    versión de Streamlit rompiera la importación, las pruebas lo detectarían.
"""

import importlib.util
import logging
import random
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_PATH = REPO_ROOT / "app.py"

# Valor por defecto del campo "Caracteres especiales" en la interfaz (app.py:243).
DEFAULT_SPECIALS_UI = "Ñ,Á,É,Í,Ó,Ú,Ü, ’"

# Direcciones por defecto del multiselect de "Custom" (app.py:229) y
# valor por defecto del slider de señuelos (app.py:231).
CUSTOM_DEFAULT_DIRS = ["H", "HR", "V", "VR", "D1", "D4"]
CUSTOM_DEFAULT_DECOYS = 6


def _load_app():
    # Silenciar los avisos de "bare mode" / ScriptRunContext de Streamlit.
    logging.getLogger("streamlit").setLevel(logging.ERROR)
    spec = importlib.util.spec_from_file_location("app", APP_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def app():
    return _load_app()


@pytest.fixture
def seeded(app):
    """Devuelve una función que fija la semilla global y genera un puzzle."""

    def _generate(seed, words, rows, cols, allowed_dirs, extra_chars, decoys):
        random.seed(seed)
        return app.generate_puzzle(
            words=words,
            rows=rows,
            cols=cols,
            allowed_dirs=allowed_dirs,
            extra_chars=extra_chars,
            decoy_fragments=decoys,
        )

    return _generate
