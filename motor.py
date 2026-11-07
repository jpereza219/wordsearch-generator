"""Motor de generación de sopas de letras (sin dependencias de Streamlit).

Todas las decisiones al azar usan una instancia propia `random.Random(seed)`:
con la misma entrada, configuración y semilla, el resultado es idéntico.

Flujo de create_puzzle():
  1. Normalización NFC de palabras y caracteres especiales.
  2. Validación previa: repetidas (aviso), largo mínimo (error), palabras que no
     caben en ninguna dirección permitida (error), sin direcciones (error),
     palabras contenidas en otras (aviso), letras fuera del alfabeto de relleno
     (aviso).
  3. Colocación de la más larga a la más corta. Cada palabra recibe una
     dirección preferida (reparto parejo entre las permitidas) y prueba TODAS
     sus posiciones en orden barajado; si no cabe, prueba las demás direcciones
     (las menos usadas primero). Si una palabra no cabe en ninguna, o si faltan
     diagonales o palabras al revés pudiendo haberlas, se reinicia el puzzle.
  4. Señuelos y relleno (igual que antes).
  5. Verificación de copias: cada palabra debe aparecer exactamente una vez
     (salvo las contenidas en otras). Las copias con celdas de relleno se
     corrigen cambiando esas letras; si no se puede, se reinicia el puzzle.
"""

import random
import string
import unicodedata
from dataclasses import dataclass, field

# ----------------------------
# Directions (8-way)
# ----------------------------
DIRS = {
    "H":  (0, 1),    # horizontal →
    "HR": (0, -1),   # horizontal ←
    "V":  (1, 0),    # vertical ↓
    "VR": (-1, 0),   # vertical ↑
    "D1": (1, 1),    # diagonal ↘
    "D2": (-1, -1),  # diagonal ↖
    "D3": (-1, 1),   # diagonal ↗
    "D4": (1, -1),   # diagonal ↙
}

# Difficulty presets -> (allowed_directions, decoy_fragments)
DIFFICULTY_PRESETS = {
    "Very easy": (["H", "V"], 0),
    "Easy":      (["H", "HR", "V", "VR"], 0),
    "Medium":    (["H", "HR", "V", "VR", "D1", "D4"], 0),
    "Hard":      (["H", "HR", "V", "VR", "D1", "D4", "D2", "D3"], 0),
    "Very hard": (["H", "HR", "V", "VR", "D1", "D4", "D2", "D3"], 8),
    "Extreme":   (["H", "HR", "V", "VR", "D1", "D4", "D2", "D3"], 16),
    "Custom":    ([], 0),
}

MIN_WORD_LEN = 3

# Direcciones "al revés": se leen de derecha a izquierda o de abajo arriba
# (←, ↑, ↖, ↙). Las otras cuatro (→, ↓, ↘, ↗) se leen hacia delante.
REVERSED_DIRS = ("HR", "VR", "D2", "D4")
DIAGONAL_DIRS = ("D1", "D2", "D3", "D4")

# Puzzles completos que se intentan antes de rendirse. Cada intento reinicia la
# cuadrícula con el mismo rng (que sigue avanzando). Ver PR del paso 3.
MAX_ATTEMPTS = 50

# Cambios de letras de relleno por intento para eliminar copias por azar.
MAX_FILL_FIXES = 200


class PuzzleError(ValueError):
    """Error de validación o de generación. `errors` tiene un mensaje por problema."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("\n".join(self.errors))


@dataclass
class PuzzleResult:
    grid: list
    placed: list            # [(palabra_limpia, [(fila, col), ...]), ...] en orden de colocación
    words_display: list     # lista impresa (sin repetidas), tal como se escribió (NFC)
    warnings: list = field(default_factory=list)
    attempts: int = 1


# ----------------------------
# Helpers
# ----------------------------
def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def clean_specials_input(text: str) -> str:
    if not text:
        return ""
    return "".join([ch for ch in text.replace(",", "").replace(" ", "")])


def clean_word(word: str) -> str:
    """Forma que ocupa la cuadrícula: NFC, sin espacios, en mayúsculas."""
    return nfc(nfc(word).replace(" ", "").strip().upper())


def filler_alphabet(extra_chars: str) -> str:
    """Alfabeto de relleno: A–Z + especiales (en mayúsculas, NFC)."""
    extra = nfc(nfc(extra_chars).upper()) if extra_chars else ""
    return string.ascii_uppercase + extra


def can_place(grid, word, row, col, dr, dc):
    rows, cols = len(grid), len(grid[0])
    for i, ch in enumerate(word):
        r, c = row + dr * i, col + dc * i
        if not (0 <= r < rows and 0 <= c < cols):
            return False
        if grid[r][c] not in ("", ch):
            return False
    return True

def place_word(grid, word, row, col, dr, dc):
    coords = []
    for i, ch in enumerate(word):
        r, c = row + dr * i, col + dc * i
        grid[r][c] = ch
        coords.append((r, c))
    return coords

def add_decoy_fragments(grid, placed_positions, num_decoys: int, filler_chars: str, *, rng: random.Random):
    if num_decoys <= 0:
        return
    rows, cols = len(grid), len(grid[0])
    letters = [grid[r][c] for r in range(rows) for c in range(cols) if grid[r][c]]
    if not letters:
        letters = list(filler_chars)

    attempts = 0
    added = 0
    while added < num_decoys and attempts < num_decoys * 50:
        attempts += 1
        frag_len = rng.randint(3, 5)
        frag = "".join(rng.choice(letters) for _ in range(frag_len))
        dir_key = rng.choice(list(DIRS.keys()))
        dr, dc = DIRS[dir_key]
        r0, c0 = rng.randrange(rows), rng.randrange(cols)

        coords = [(r0 + dr * i, c0 + dc * i) for i in range(frag_len)]
        if all(0 <= r < rows and 0 <= c < cols and grid[r][c] == "" for r, c in coords):
            for (rr, cc), ch in zip(coords, frag):
                grid[rr][cc] = ch
            added += 1

def fill_empty(grid, filler_chars: str, *, rng: random.Random):
    rows, cols = len(grid), len(grid[0])
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == "":
                grid[r][c] = rng.choice(filler_chars)


def max_word_length(rows, cols, allowed_dirs):
    """Largo máximo que cabe con las direcciones permitidas."""
    best = 0
    for key in allowed_dirs:
        dr, dc = DIRS[key]
        if dr == 0:
            best = max(best, cols)
        elif dc == 0:
            best = max(best, rows)
        else:
            best = max(best, min(rows, cols))
    return best


def find_occurrences(grid, word):
    """Conjuntos de celdas donde se lee `word` en cualquiera de las 8 direcciones.

    Un palíndromo leído en los dos sentidos sobre las mismas celdas cuenta una vez.
    Devuelve una lista ordenada (determinista) de tuplas de celdas.
    """
    rows, cols = len(grid), len(grid[0])
    n = len(word)
    found = set()
    first = word[0]
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] != first:
                continue
            for dr, dc in DIRS.values():
                er, ec = r + dr * (n - 1), c + dc * (n - 1)
                if not (0 <= er < rows and 0 <= ec < cols):
                    continue
                if all(grid[r + dr * i][c + dc * i] == word[i] for i in range(1, n)):
                    found.add(tuple(sorted((r + dr * i, c + dc * i) for i in range(n))))
    return sorted(found)


# ----------------------------
# Validación
# ----------------------------
@dataclass
class Prepared:
    words_display: list
    words_clean: list
    filler_chars: str
    allowed_dirs: list
    warnings: list


def prepare_words(words, rows, cols, allowed_dirs, extra_chars: str) -> Prepared:
    """Normaliza y valida. Lanza PuzzleError con todos los errores encontrados."""
    errors, warnings = [], []

    # 1. Normalización
    entries = [nfc(w).strip() for w in words if w.strip()]
    filler_chars = filler_alphabet(extra_chars)

    # 2a. Repetidas (forma limpia)
    words_display, words_clean, removed = [], [], []
    seen = set()
    for display in entries:
        clean = clean_word(display)
        if clean in seen:
            removed.append(display)
            continue
        seen.add(clean)
        words_display.append(display)
        words_clean.append(clean)
    if removed:
        warnings.append("Se eliminaron palabras repetidas: " + ", ".join(removed) + ".")

    # 2d. Direcciones
    dirs = []
    for key in allowed_dirs or []:
        if key not in DIRS:
            errors.append(f"Dirección desconocida: {key}.")
        elif key not in dirs:
            dirs.append(key)
    if not allowed_dirs:
        errors.append("No hay ninguna dirección permitida: marca al menos una.")

    if not words_clean:
        errors.append("No hay palabras para colocar.")

    # 2b. Largo mínimo
    short = [d for d, c in zip(words_display, words_clean) if len(c) < MIN_WORD_LEN]
    if short:
        errors.append(
            f"Palabras con menos de {MIN_WORD_LEN} letras: " + ", ".join(short) + "."
        )

    # 2c. Palabras que no caben
    if dirs:
        limit = max_word_length(rows, cols, dirs)
        for d, c in zip(words_display, words_clean):
            if len(c) > limit:
                errors.append(
                    f"«{d}» tiene {len(c)} letras y no cabe: el máximo con estas direcciones "
                    f"en {rows}x{cols} es {limit}."
                )

    if errors:
        raise PuzzleError(errors)

    # 2e. Palabras contenidas en otras (aviso). La lectura al revés solo se
    # avisa si las direcciones permitidas incluyen alguna junto con su opuesta.
    vectors = {DIRS[k] for k in dirs}
    reversed_allowed = any((-dr, -dc) in vectors for dr, dc in vectors)
    for d_a, a in zip(words_display, words_clean):
        for d_b, b in zip(words_display, words_clean):
            if a == b:
                continue
            if a in b:
                warnings.append(
                    f"«{d_a}» está dentro de «{d_b}»: aparecerá más de una vez en la cuadrícula."
                )
            elif reversed_allowed and a[::-1] in b:
                warnings.append(
                    f"«{d_a}» está dentro de «{d_b}» leída al revés: aparecerá más de una vez "
                    f"en la cuadrícula."
                )

    # 2f. Letras fuera del alfabeto de relleno (aviso)
    alphabet = set(filler_chars)
    missing = {}
    for d, c in zip(words_display, words_clean):
        for ch in c:
            if ch not in alphabet:
                missing.setdefault(ch, [])
                if d not in missing[ch]:
                    missing[ch].append(d)
    for ch, owners in missing.items():
        warnings.append(
            f"El carácter «{ch}» de {', '.join(owners)} no está en el alfabeto de relleno y "
            f"delatará la palabra. Agrégalo al campo de caracteres especiales."
        )

    return Prepared(words_display, words_clean, filler_chars, dirs, warnings)


# ----------------------------
# Colocación
# ----------------------------
def _candidates(rows, cols, n, dirs):
    out = []
    for key in dirs:
        dr, dc = DIRS[key]
        for r in range(rows):
            er = r + dr * (n - 1)
            if not 0 <= er < rows:
                continue
            for c in range(cols):
                ec = c + dc * (n - 1)
                if 0 <= ec < cols:
                    out.append((r, c, dr, dc))
    return out


def _fits(n, key, rows, cols):
    """¿Cabe una palabra de `n` letras en la dirección `key`?"""
    return n <= max_word_length(rows, cols, [key])


def assign_directions(order, rows, cols, dirs, rng):
    """Dirección preferida de cada palabra, repartidas de la forma más pareja posible.

    Las direcciones se barajan con rng y se reparten en ronda, de la palabra más
    larga a la más corta. Cada palabra va a la dirección con menos palabras
    asignadas entre aquellas en las que cabe (empates: orden barajado). Si todas
    caben en todas, el número de palabras por dirección difiere como máximo en 1.
    """
    rotation = list(dirs)
    rng.shuffle(rotation)
    counts = {d: 0 for d in rotation}
    preferred = []
    for w in order:
        fitting = [d for d in rotation if _fits(len(w), d, rows, cols)]
        choice = min(fitting, key=lambda d: (counts[d], rotation.index(d)))
        counts[choice] += 1
        preferred.append(choice)
    return preferred


def _try_direction(grid, w, key, rows, cols, rng):
    cands = _candidates(rows, cols, len(w), [key])
    rng.shuffle(cands)
    for r, c, dr, dc in cands:
        if not can_place(grid, w, r, c, dr, dc):
            continue
        # Al menos una celda nueva: una palabra no puede quedar entera
        # encima de letras de otras palabras.
        if all(grid[r + dr * i][c + dc * i] for i in range(len(w))):
            continue
        return place_word(grid, w, r, c, dr, dc)
    return None


def _place_all(order, rows, cols, dirs, rng):
    """Coloca las palabras en `order`. Devuelve (grid, placed, palabra_que_falló).

    Cada palabra prueba primero todas las posiciones de su dirección preferida
    (barajadas). Si no hay lugar, prueba las demás direcciones permitidas,
    empezando por las menos usadas hasta ese momento (empates al azar).
    """
    grid = [["" for _ in range(cols)] for _ in range(rows)]
    placed = []
    used = {d: 0 for d in dirs}
    preferred = assign_directions(order, rows, cols, dirs, rng)
    for w, pref in zip(order, preferred):
        others = [d for d in dirs if d != pref]
        rng.shuffle(others)
        others.sort(key=lambda d: used[d])  # estable: el barajado decide los empates
        for key in [pref] + others:
            coords = _try_direction(grid, w, key, rows, cols, rng)
            if coords is not None:
                placed.append((w, coords))
                used[key] += 1
                break
        else:
            return grid, placed, w
    return grid, placed, None


def direction_of(coords):
    """Clave de dirección (H, HR, …) de una palabra colocada."""
    (r1, c1), (r2, c2) = coords[0], coords[1]
    return _DIR_BY_VECTOR[(r2 - r1, c2 - c1)]


_DIR_BY_VECTOR = {v: k for k, v in DIRS.items()}


def _variety_goals(order, rows, cols, dirs):
    """Qué exigir a cada intento: (al menos una diagonal, al menos una al revés).

    Solo se exige cuando hay al menos tantas palabras como direcciones permitidas
    y alguna palabra cabe en una dirección de ese tipo.
    """
    if len(order) < len(dirs):
        return False, False

    def possible(kind):
        return any(_fits(len(w), d, rows, cols) for w in order for d in dirs if d in kind)

    return possible(DIAGONAL_DIRS), possible(REVERSED_DIRS)


def _has_variety(placed, goals):
    need_diag, need_rev = goals
    used = {direction_of(coords) for _, coords in placed}
    if need_diag and not used & set(DIAGONAL_DIRS):
        return False
    if need_rev and not used & set(REVERSED_DIRS):
        return False
    return True


def _illegal_copies(grid, placed):
    """Copias de palabras que no son su colocación ni están dentro de otra palabra."""
    cells_of = {w: set(coords) for w, coords in placed}
    bad = []
    for w, coords in placed:
        own = tuple(sorted(coords))
        for occ in find_occurrences(grid, w):
            if occ == own:
                continue
            occ_set = set(occ)
            if any(o != w and occ_set <= cells for o, cells in cells_of.items()):
                continue  # dentro de otra palabra (avisado en 2e)
            bad.append((w, occ))
    return bad


def _fix_copies(grid, placed, filler_chars, rng):
    """Cambia letras de relleno hasta que no haya copias. False si hay que reiniciar."""
    word_cells = {rc for _, coords in placed for rc in coords}
    alphabet = list(dict.fromkeys(filler_chars))
    for _ in range(MAX_FILL_FIXES):
        bad = _illegal_copies(grid, placed)
        if not bad:
            return True
        _, occ = bad[0]
        free = [rc for rc in occ if rc not in word_cells]
        if not free:
            return False  # copia hecha solo con letras de palabras colocadas
        r, c = rng.choice(free)
        grid[r][c] = rng.choice([ch for ch in alphabet if ch != grid[r][c]])
    return False


# ----------------------------
# Generator
# ----------------------------
def create_puzzle(words, rows, cols, allowed_dirs, extra_chars: str, decoy_fragments: int, seed=None) -> PuzzleResult:
    """Genera un puzzle validado. Lanza PuzzleError si no se puede.

    Con la misma `seed` se obtiene siempre el mismo puzzle. Si `seed` es None,
    la instancia de Random se inicializa desde el sistema operativo (no se usa
    ni se altera el `random` global).
    """
    prep = prepare_words(words, rows, cols, allowed_dirs, extra_chars)
    rng = random.Random(seed)

    # De la más larga a la más corta; empates en el orden de entrada.
    order = sorted(prep.words_clean, key=len, reverse=True)

    goals = _variety_goals(order, rows, cols, prep.allowed_dirs)

    failed_words, copy_failures = [], 0
    fallback = None  # primer puzzle válido, por si nunca se logra la variedad
    for attempt in range(1, MAX_ATTEMPTS + 1):
        grid, placed, failed = _place_all(order, rows, cols, prep.allowed_dirs, rng)
        if failed is not None:
            if failed not in failed_words:
                failed_words.append(failed)
            continue

        varied = _has_variety(placed, goals)
        if not varied and fallback is not None:
            continue  # ya hay un puzzle válido de respaldo; se busca uno con variedad

        if decoy_fragments > 0:
            add_decoy_fragments(grid, placed, decoy_fragments, prep.filler_chars, rng=rng)
        fill_empty(grid, prep.filler_chars, rng=rng)

        if not _fix_copies(grid, placed, prep.filler_chars, rng):
            copy_failures += 1
            continue

        result = PuzzleResult(grid, placed, prep.words_display, list(prep.warnings), attempt)
        if varied:
            return result
        fallback = result

    if fallback is not None:
        fallback.warnings.append(
            "No se logró que hubiera palabras en diagonal y al revés en "
            f"{MAX_ATTEMPTS} intentos; revisa el reparto de direcciones."
        )
        fallback.attempts = MAX_ATTEMPTS
        return fallback

    display_of = dict(zip(prep.words_clean, prep.words_display))
    errors = []
    if failed_words:
        errors.append(
            f"No se pudieron colocar en {MAX_ATTEMPTS} intentos: "
            + ", ".join(display_of[w] for w in failed_words)
            + ". Prueba una cuadrícula más grande, más direcciones o menos palabras."
        )
    if copy_failures:
        errors.append(
            f"En {copy_failures} intentos no se pudieron evitar copias repetidas de alguna palabra."
        )
    raise PuzzleError(errors)


def generate_puzzle(words, rows, cols, allowed_dirs, extra_chars: str, decoy_fragments: int, seed=None):
    """Compatibilidad: devuelve (grid, placed, words_display). Lanza PuzzleError."""
    result = create_puzzle(words, rows, cols, allowed_dirs, extra_chars, decoy_fragments, seed=seed)
    return result.grid, result.placed, result.words_display
