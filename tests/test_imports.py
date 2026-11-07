"""Separación motor / PDF / interfaz."""

import importlib.util
import logging
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_motor_y_pdf_no_cargan_streamlit():
    # Se ejecuta en un proceso aparte: en esta sesión de pytest otra prueba
    # importa app.py, que sí carga streamlit.
    code = (
        "import sys, motor, pdf\n"
        "cargados = sorted(m for m in sys.modules if m == 'streamlit' or m.startswith('streamlit.'))\n"
        "assert not cargados, cargados\n"
        "print('ok')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_app_se_importa_sin_errores():
    """app.py (solo interfaz) se sigue importando en el bare mode de Streamlit.

    Fuera de `streamlit run`, st.button devuelve False, así que la importación
    no genera ningún puzzle.
    """
    logging.getLogger("streamlit").setLevel(logging.ERROR)
    spec = importlib.util.spec_from_file_location("app", REPO_ROOT / "app.py")
    app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app)

    import motor
    import pdf

    assert app.create_puzzle is motor.create_puzzle
    assert app.generate_pdf is pdf.generate_pdf
