"""Ficha de un puzzle (ficha.json): todo lo necesario para regenerarlo idéntico.

Sin dependencias de Streamlit.
"""

import json

from motor import DIRS, MOTOR_VERSION, PuzzleError, clean_word, create_puzzle, direction_of

FORMATO = "ficha-sopa/1"


class FichaError(ValueError):
    """La ficha no es válida o no reproduce el mismo puzzle."""


def build_ficha(result, *, seed, rows, cols, allowed_dirs, decoys, extra_chars, words, hidden_words=(),
                difficulty=None, specials_field=None, title=None):
    """Construye la ficha (un dict listo para json.dumps) de un puzzle ya generado.

    `words` y `hidden_words` son las entradas tal como se pasaron a create_puzzle
    (la ficha guarda exactamente lo que hace falta para repetir la llamada).
    """
    if not isinstance(seed, int):
        raise FichaError("La ficha necesita una semilla entera.")
    texto = {clean_word(d): d for d in result.words_display}
    texto.update(zip(result.hidden_words, result.hidden_display))
    hidden = set(result.hidden_words)

    colocacion = []
    for w, coords in result.placed:
        (r, c) = coords[0]
        colocacion.append({
            "palabra": w,
            "texto": texto.get(w, w),
            "oculta": w in hidden,
            "fila": r,
            "columna": c,
            "direccion": direction_of(coords),
            "largo": len(coords),
        })

    return {
        "formato": FORMATO,
        "motor_version": MOTOR_VERSION,
        "titulo": title,
        "semilla": seed,
        "filas": rows,
        "columnas": cols,
        "dificultad": difficulty,
        "direcciones": list(allowed_dirs),
        "senuelos": decoys,
        "especiales_campo": specials_field,
        "especiales": extra_chars,
        "palabras": [w for w in words if w.strip()],
        "ocultas": [w for w in hidden_words if w.strip()],
        "colocacion": colocacion,
        "cuadricula": [" ".join(row) for row in result.grid],
    }


def ficha_json(ficha):
    return json.dumps(ficha, ensure_ascii=False, indent=2) + "\n"


def load_ficha(data):
    """Acepta un dict, un str JSON o bytes UTF-8."""
    if isinstance(data, dict):
        return data
    if isinstance(data, (bytes, bytearray)):
        data = data.decode("utf-8")
    try:
        ficha = json.loads(data)
    except json.JSONDecodeError as e:
        raise FichaError(f"La ficha no es un JSON válido: {e}.") from e
    if not isinstance(ficha, dict):
        raise FichaError("La ficha no es un objeto JSON.")
    return ficha


def regenerate_from_ficha(data):
    """Regenera el puzzle de una ficha y verifica que la cuadrícula salga idéntica.

    Devuelve el PuzzleResult. Lanza FichaError si la ficha no es válida, si fue
    creada con otra versión del motor o si el resultado no coincide.
    """
    ficha = load_ficha(data)
    if ficha.get("formato") != FORMATO:
        raise FichaError(f"Formato de ficha desconocido: {ficha.get('formato')!r} (se esperaba {FORMATO!r}).")
    version = ficha.get("motor_version")
    if version != MOTOR_VERSION:
        raise FichaError(
            f"La ficha se creó con la versión {version} del motor y este generador usa la {MOTOR_VERSION}: "
            "con otra versión la misma semilla produce otro puzzle. Usa la versión del generador "
            f"correspondiente (etiqueta o commit con MOTOR_VERSION = \"{version}\")."
        )
    required = ("semilla", "filas", "columnas", "direcciones", "senuelos", "especiales", "palabras", "cuadricula")
    missing = [k for k in required if k not in ficha]
    if missing:
        raise FichaError("A la ficha le faltan campos: " + ", ".join(missing) + ".")
    unknown = [d for d in ficha["direcciones"] if d not in DIRS]
    if unknown:
        raise FichaError("Direcciones desconocidas en la ficha: " + ", ".join(unknown) + ".")

    try:
        result = create_puzzle(
            ficha["palabras"], ficha["filas"], ficha["columnas"], ficha["direcciones"],
            ficha["especiales"], ficha["senuelos"], seed=ficha["semilla"],
            hidden_words=ficha.get("ocultas", []),
        )
    except PuzzleError as e:
        raise FichaError("La ficha no se pudo regenerar: " + " ".join(e.errors)) from e

    grid = [" ".join(row) for row in result.grid]
    if grid != ficha["cuadricula"]:
        raise FichaError("La cuadrícula regenerada no coincide con la de la ficha.")
    if "colocacion" in ficha:
        expected = [(p["palabra"], p["fila"], p["columna"], p["direccion"], p["largo"]) for p in ficha["colocacion"]]
        actual = [(w, c[0][0], c[0][1], direction_of(c), len(c)) for w, c in result.placed]
        if expected != actual:
            raise FichaError("Las posiciones regeneradas no coinciden con las de la ficha.")
    return result
