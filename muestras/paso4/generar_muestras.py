"""Genera las muestras de revisión visual del paso 4.

Uso (desde la raíz del repositorio):

    python muestras/paso4/generar_muestras.py

Escribe en muestras/paso4/<caso>/ los SVG, los PDF (cuadrícula sola y de 2
páginas), el .txt y PNG a 150 ppp de cada PDF (con pdftoppm, de poppler-utils).
Los PNG de los SVG se generan aparte con Chromium:

    node muestras/paso4/svg_a_png.cjs muestras/paso4
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import motor  # noqa: E402
import salidas  # noqa: E402

OUT = Path(__file__).resolve().parent
ALL_DIRS = list(motor.DIRS)

DEPARTAMENTOS = [
    "ATLÁNTIDA", "COLÓN", "COMAYAGUA", "COPÁN", "CORTÉS", "CHOLUTECA", "EL PARAÍSO",
    "FRANCISCO MORAZÁN", "GRACIAS A DIOS", "INTIBUCÁ", "ISLAS DE LA BAHÍA", "LA PAZ",
    "LEMPIRA", "OCOTEPEQUE", "OLANCHO", "SANTA BÁRBARA", "VALLE", "YORO",
]
MUNICIPIOS_FM = [
    "DISTRITO CENTRAL", "ALUBARÉN", "CEDROS", "CURARÉN", "EL PORVENIR", "GUAIMACA",
    "LA LIBERTAD", "LA VENTA", "LEPATERIQUE", "MARAITA", "MARALE", "NUEVA ARMENIA",
    "OJOJONA", "ORICA", "REITOCA", "SABANAGRANDE", "SAN ANTONIO DE ORIENTE",
    "SAN BUENAVENTURA", "SAN IGNACIO", "SANTA ANA", "SANTA LUCÍA", "TALANGA",
    "TATUMBLA", "VALLE DE ÁNGELES", "VALLECILLO", "VILLA DE SAN FRANCISCO",
]

# FRANCISCO MORAZÁN (16 letras) no cabe en 15x15: la validación 2c lo rechaza,
# así que la muestra de 15x15 usa los otros 17 departamentos.
# Desde el paso 3b las palabras se reparten entre las 8 direcciones en
# cualquier semilla; se conservan las semillas de las muestras del paso 4.
CASOS = {
    "15x15_departamentos": dict(
        words=[w for w in DEPARTAMENTOS if w != "FRANCISCO MORAZÁN"], size=15, seed=10
    ),
    "20x20_municipios_fm": dict(words=MUNICIPIOS_FM, size=20, seed=1449),
}


def main():
    for name, case in CASOS.items():
        folder = OUT / name
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)
        result = motor.create_puzzle(
            case["words"], case["size"], case["size"], ALL_DIRS, "ÑÁÉÍÓÚÜ", 6, seed=case["seed"]
        )
        files = salidas.puzzle_files(result.grid, result.placed, result.words_display, case["seed"])
        for fname, data in files.items():
            (folder / fname).write_bytes(data)
            if fname.endswith(".pdf"):
                subprocess.run(
                    ["pdftoppm", "-r", "150", "-png", fname, fname[:-4] + ".pdf"],
                    cwd=folder, check=True,
                )
        print(f"{name}: {len(result.placed)} de {len(result.words_display)} palabras, avisos: {result.warnings}")


if __name__ == "__main__":
    main()
