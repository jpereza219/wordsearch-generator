"""Motor de generación de sopas de letras (sin dependencias de Streamlit).

Código movido desde app.py sin cambios de lógica. La única diferencia es que
todas las decisiones al azar usan una instancia propia `random.Random(seed)`
en lugar del módulo `random` global. Las llamadas se hacen en el mismo orden
que antes, así que `generate_puzzle(..., seed=N)` produce exactamente lo mismo
que el código anterior tras `random.seed(N)`.
"""

import random
import string

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

# ----------------------------
# Helpers
# ----------------------------
def clean_specials_input(text: str) -> str:
    if not text:
        return ""
    return "".join([ch for ch in text.replace(",", "").replace(" ", "")])

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

# ----------------------------
# Generator
# ----------------------------
def generate_puzzle(words, rows, cols, allowed_dirs, extra_chars: str, decoy_fragments: int, seed=None):
    """Genera un puzzle. Con la misma `seed` se obtiene siempre el mismo puzzle.

    Si `seed` es None, la instancia de Random se inicializa desde el sistema
    operativo (no se usa ni se altera el `random` global).
    """
    rng = random.Random(seed)

    grid = [["" for _ in range(cols)] for _ in range(rows)]

    # Keep original for display
    words_display = [w.strip() for w in words if w.strip()]

    # Remove spaces only for grid placement
    words_clean = [w.replace(" ", "").strip() for w in words if w.strip()]

    words_up = [w.upper() for w in words_clean if len(w) <= max(rows, cols)]

    filler_chars = string.ascii_uppercase + (extra_chars.upper() if extra_chars else "")

    placed = []
    for w in words_up:
        placed_ok = False
        tries = 0
        dirs_cycle = allowed_dirs[:] if allowed_dirs else list(DIRS.keys())
        rng.shuffle(dirs_cycle)
        while not placed_ok and tries < 300:
            tries += 1
            dr_key = rng.choice(dirs_cycle)
            dr, dc = DIRS[dr_key]
            r0 = rng.randrange(rows)
            c0 = rng.randrange(cols)
            if can_place(grid, w, r0, c0, dr, dc):
                coords = place_word(grid, w, r0, c0, dr, dc)
                placed.append((w, coords))
                placed_ok = True

    if decoy_fragments > 0:
        add_decoy_fragments(grid, placed, decoy_fragments, filler_chars, rng=rng)

    fill_empty(grid, filler_chars, rng=rng)

    return grid, placed, words_display
