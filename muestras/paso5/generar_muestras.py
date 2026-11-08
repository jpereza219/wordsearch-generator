"""Genera las muestras de revisión del paso 5 (Ruta Secreta).

Uso (desde la raíz del repositorio):

    python muestras/paso5/generar_muestras.py
    node muestras/paso4/svg_a_png.cjs muestras/paso5

Escribe en muestras/paso5/<caso>/ los 8 archivos del ZIP del puzzle. El segundo
comando crea PNG a 150 ppp de cada SVG (solución del libro y solución del autor).
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import ficha  # noqa: E402
import motor  # noqa: E402
import salidas  # noqa: E402

OUT = Path(__file__).resolve().parent
ALL_DIRS = list(motor.DIRS)

CASOS = {
    "15x15_paises_gracias": dict(
        words=["BELICE", "COLOMBIA", "CUBA", "EL SALVADOR", "GUATEMALA",
               "ISLAS CAIMÁN", "JAMAICA", "MÉXICO", "NICARAGUA"],
        hidden=["GRACIAS"], size=15, seed=505, decoys=6, specials="ÑÁÉÍÓÚÜ",
    ),
}


def main():
    for name, case in CASOS.items():
        folder = OUT / name
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)
        n = case["size"]
        result = motor.create_puzzle(case["words"], n, n, ALL_DIRS, case["specials"], case["decoys"],
                                     seed=case["seed"], hidden_words=case["hidden"])
        f = ficha.build_ficha(
            result, seed=case["seed"], rows=n, cols=n, allowed_dirs=ALL_DIRS, decoys=case["decoys"],
            extra_chars=case["specials"], words=case["words"], hidden_words=case["hidden"],
            difficulty="Custom", specials_field=case["specials"],
        )
        files = salidas.puzzle_files(result.grid, result.placed, result.words_display, case["seed"],
                                     hidden=result.hidden_words, ficha=f)
        for fname, data in files.items():
            (folder / fname).write_bytes(data)
        print(f"{name}: {len(result.visible_placed)} de {len(result.words_display)} palabras "
              f"+ {len(result.hidden_placed)} oculta(s), {len(files)} archivos")


if __name__ == "__main__":
    main()
