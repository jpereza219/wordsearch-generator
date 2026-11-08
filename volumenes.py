"""Bancos de palabras por volumen (sin dependencias de Streamlit).

Cada volumen es una carpeta dentro de volumenes/ con dos archivos CSV:

- puzzles.csv:  puzzle, titulo, filas, columnas, dificultad, senuelos, especiales, notas
- palabras.csv: puzzle, palabra, oculta

La lectura es tolerante con lo que producen Excel y Google Sheets: UTF-8 con o
sin BOM, separador coma o punto y coma, encabezados con o sin tildes y en
cualquier combinación de mayúsculas. Ver volumenes/LEEME.md.
"""

import csv
import io
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from motor import DIFFICULTY_PRESETS, clean_specials_input, clean_word, nfc

ROOT = Path(__file__).resolve().parent / "volumenes"
PUZZLES_FILE = "puzzles.csv"
WORDS_FILE = "palabras.csv"
MAX_PUZZLES = 50

PUZZLE_COLUMNS = ("puzzle", "titulo", "filas", "columnas", "dificultad", "senuelos", "especiales", "notas")
PUZZLE_REQUIRED = ("puzzle", "titulo")
WORD_COLUMNS = ("puzzle", "palabra", "oculta")
WORD_REQUIRED = ("puzzle", "palabra")

TRUE_VALUES = {"si", "x", "1"}  # se comparan sin tildes ni mayúsculas: «Sí», «SI», «X»
FALSE_VALUES = {"", "no", "0"}

# Valores por defecto de la app (se usan cuando la columna está vacía).
APP_DEFAULTS = dict(
    filas=15,
    columnas=15,
    dificultad="Medium",
    senuelos=6,  # valor por defecto del control de señuelos en Custom
    especiales="Ñ,Á,É,Í,Ó,Ú,Ü, ’",
)
CUSTOM_DEFAULT_DIRS = ["H", "HR", "V", "VR", "D1", "D4"]


class VolumenError(ValueError):
    """Errores de un volumen. `errors` tiene un mensaje por problema."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("\n".join(self.errors))


@dataclass
class PuzzleDef:
    numero: int
    titulo: str
    linea: int                      # línea en puzzles.csv
    filas: int | None = None
    columnas: int | None = None
    dificultad: str | None = None
    senuelos: int | None = None
    especiales: str | None = None   # como en el campo de la app ("Ñ,Á,...")
    notas: str = ""
    palabras: list = field(default_factory=list)
    ocultas: list = field(default_factory=list)

    @property
    def etiqueta(self):
        return f"{self.numero:02d} — {self.titulo}"


@dataclass
class Volumen:
    nombre: str
    puzzles: list                   # PuzzleDef ordenados por número
    warnings: list = field(default_factory=list)

    def puzzle(self, numero):
        for p in self.puzzles:
            if p.numero == numero:
                return p
        raise KeyError(numero)

    @property
    def ruta_secreta(self):
        """Mensaje de la Ruta Secreta: las ocultas en orden de puzzle."""
        return " ".join(w for p in self.puzzles for w in p.ocultas)

    def resumen(self):
        return {
            "volumen": self.nombre,
            "puzzles": len(self.puzzles),
            "palabras": sum(len(p.palabras) for p in self.puzzles),
            "ocultas": sum(len(p.ocultas) for p in self.puzzles),
            "ruta_secreta": self.ruta_secreta,
        }


# ----------------------------------------------------------------- lectura CSV

def _key(text):
    """Encabezado normalizado: minúsculas, sin tildes ni espacios sobrantes (señuelos -> senuelos)."""
    text = unicodedata.normalize("NFKD", text.strip().lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch)).replace(" ", "_")


def read_csv(data, filename):
    """Lee un CSV tolerante. Devuelve (encabezados_normalizados, [(línea, {col: valor}), ...]).

    `data` es el contenido del archivo (bytes o str). Acepta BOM y separador coma
    o punto y coma.
    """
    if isinstance(data, (bytes, bytearray)):
        try:
            text = bytes(data).decode("utf-8-sig")
        except UnicodeDecodeError as e:
            raise VolumenError([
                f"{filename}: no está en UTF-8 (byte {e.start}). Guárdalo como «CSV UTF-8» (ver LEEME.md)."
            ]) from e
    else:
        text = str(data).lstrip("﻿")
    text = nfc(text)
    first = text.split("\n", 1)[0]
    delimiter = ";" if first.count(";") > first.count(",") else ","
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    rows = []
    header = None
    for record in reader:
        line = reader.line_num
        if header is None:
            if not any(cell.strip() for cell in record):
                continue
            header = [_key(h) for h in record]
            continue
        if not any(cell.strip() for cell in record):
            continue  # filas vacías (Excel suele dejarlas al final)
        values = {h: (record[i].strip() if i < len(record) else "") for i, h in enumerate(header) if h}
        rows.append((line, values))
    return header or [], rows


# ----------------------------------------------------------------- validación

def _int(value, where, name, errors, low=None, high=None):
    if value == "":
        return None
    try:
        n = int(value)
    except ValueError:
        errors.append(f"{where}: «{name}» debe ser un número entero (dice «{value}»).")
        return None
    if (low is not None and n < low) or (high is not None and n > high):
        errors.append(f"{where}: «{name}» debe estar entre {low} y {high} (dice {n}).")
        return None
    return n


def _difficulty(value, where, errors):
    if value == "":
        return None
    for name in DIFFICULTY_PRESETS:
        if name != "Custom" and _key(name) == _key(value):
            return name
    valid = ", ".join(n for n in DIFFICULTY_PRESETS if n != "Custom")
    errors.append(f"{where}: dificultad desconocida «{value}». Usa una de: {valid}.")
    return None


def parse_volume(puzzles_data, words_data, nombre="borrador"):
    """Lee y valida un volumen a partir del contenido de sus dos CSV.

    Lanza VolumenError con todos los errores (archivo y línea). Devuelve un
    Volumen con los avisos en `warnings`.
    """
    errors, warnings = [], []
    p_header, p_rows = read_csv(puzzles_data, PUZZLES_FILE)
    w_header, w_rows = read_csv(words_data, WORDS_FILE)

    for fname, header, required in ((PUZZLES_FILE, p_header, PUZZLE_REQUIRED), (WORDS_FILE, w_header, WORD_REQUIRED)):
        missing = [c for c in required if c not in header]
        if missing:
            errors.append(f"{fname}: faltan columnas: {', '.join(missing)} (línea 1, encabezados).")
    if errors:
        raise VolumenError(errors)

    puzzles = {}
    for line, row in p_rows:
        where = f"{PUZZLES_FILE}, línea {line}"
        numero = _int(row.get("puzzle", ""), where, "puzzle", errors, 1, MAX_PUZZLES)
        if row.get("puzzle", "") == "":
            errors.append(f"{where}: falta el número de puzzle.")
        titulo = row.get("titulo", "")
        if not titulo:
            errors.append(f"{where}: el puzzle no tiene título.")
        if numero is None:
            continue
        if numero in puzzles:
            errors.append(f"{where}: el puzzle {numero} está repetido (ya aparece en la línea {puzzles[numero].linea}).")
            continue
        puzzles[numero] = PuzzleDef(
            numero=numero,
            titulo=titulo,
            linea=line,
            filas=_int(row.get("filas", ""), where, "filas", errors, 5, 40),
            columnas=_int(row.get("columnas", ""), where, "columnas", errors, 5, 40),
            dificultad=_difficulty(row.get("dificultad", ""), where, errors),
            senuelos=_int(row.get("senuelos", ""), where, "senuelos", errors, 0, 30),
            especiales=row.get("especiales") or None,
            notas=row.get("notas", ""),
        )

    seen_words = {}
    for line, row in w_rows:
        where = f"{WORDS_FILE}, línea {line}"
        numero = _int(row.get("puzzle", ""), where, "puzzle", errors, 1, MAX_PUZZLES)
        if row.get("puzzle", "") == "":
            errors.append(f"{where}: falta el número de puzzle.")
        palabra = row.get("palabra", "")
        if not palabra:
            errors.append(f"{where}: la palabra está vacía.")
        flag = _key(row.get("oculta", ""))
        if flag in TRUE_VALUES:
            oculta = True
        elif flag in FALSE_VALUES:
            oculta = False
        else:
            errors.append(f"{where}: en «oculta» escribe «sí» o déjalo vacío (dice «{row.get('oculta')}»).")
            oculta = False
        if numero is None or not palabra:
            continue
        if numero not in puzzles:
            errors.append(f"{where}: la palabra «{palabra}» apunta al puzzle {numero}, que no está en {PUZZLES_FILE}.")
            continue
        target = puzzles[numero]
        (target.ocultas if oculta else target.palabras).append(palabra)
        seen_words.setdefault(clean_word(palabra), []).append((numero, line, palabra))

    if errors:
        raise VolumenError(errors)

    ordered = [puzzles[n] for n in sorted(puzzles)]
    for p in ordered:
        if not p.palabras:
            warnings.append(f"El puzzle {p.numero} («{p.titulo}») no tiene palabras ({PUZZLES_FILE}, línea {p.linea}).")
        if not p.ocultas:
            warnings.append(f"El puzzle {p.numero} («{p.titulo}») no tiene palabra oculta de la Ruta Secreta.")
    for clean, uses in seen_words.items():
        if len(uses) > 1:
            where = ", ".join(f"puzzle {n} (línea {ln})" for n, ln, _ in uses)
            warnings.append(f"«{uses[0][2]}» se repite en el volumen: {where}.")

    return Volumen(nombre=nombre, puzzles=ordered, warnings=warnings)


def list_volumes(root=ROOT):
    """Carpetas de volumen (las que tienen puzzles.csv), en orden natural."""
    root = Path(root)
    if not root.is_dir():
        return []
    names = [d.name for d in root.iterdir() if d.is_dir() and (d / PUZZLES_FILE).exists()]
    return sorted(names, key=lambda n: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", n)])


def load_volume(nombre, root=ROOT):
    folder = Path(root) / nombre
    words = folder / WORDS_FILE
    return parse_volume(
        (folder / PUZZLES_FILE).read_bytes(),
        words.read_bytes() if words.exists() else b"puzzle,palabra,oculta\n",
        nombre=nombre,
    )


# ----------------------------------------------------------------- configuración

def resolve_config(p, defaults=None):
    """Configuración completa de un puzzle: lo del CSV o, si está vacío, lo de la app.

    Devuelve un dict con: titulo, filas, columnas, dificultad, allowed_dirs,
    senuelos, especiales_campo, extra_chars, palabras, ocultas.

    Si el CSV da «senuelos» y no coincide con los de la dificultad elegida, se
    usa «Custom» con las direcciones de esa dificultad y esos señuelos (en la
    app los señuelos solo se pueden elegir en Custom).
    """
    d = {**APP_DEFAULTS, **(defaults or {})}
    dificultad = p.dificultad or d["dificultad"]
    preset_dirs, preset_decoys = DIFFICULTY_PRESETS[dificultad] if dificultad != "Custom" else (CUSTOM_DEFAULT_DIRS, d["senuelos"])
    allowed_dirs, senuelos = list(preset_dirs), preset_decoys
    if p.senuelos is not None and p.senuelos != preset_decoys:
        dificultad, senuelos = "Custom", p.senuelos
        if not p.dificultad:
            allowed_dirs = list(CUSTOM_DEFAULT_DIRS)
    especiales_campo = p.especiales if p.especiales is not None else d["especiales"]
    return {
        "titulo": p.titulo,
        "filas": p.filas or d["filas"],
        "columnas": p.columnas or d["columnas"],
        "dificultad": dificultad,
        "allowed_dirs": allowed_dirs,
        "senuelos": senuelos,
        "especiales_campo": especiales_campo,
        "extra_chars": clean_specials_input(especiales_campo),
        "palabras": list(p.palabras),
        "ocultas": list(p.ocultas),
    }


# ----------------------------------------------------------------- nombres

def volume_tag(nombre):
    """«vol2» -> «v2»; otros nombres, en forma corta."""
    m = re.fullmatch(r"vol(?:umen)?[_-]?(\d+)", nombre or "", flags=re.I)
    return f"v{int(m.group(1))}" if m else short_title(nombre, 12) or "vol"


def short_title(text, limit=30):
    """Título corto para nombres de archivo: minúsculas, sin tildes ni espacios, máx. `limit`."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:limit].rstrip("-")
