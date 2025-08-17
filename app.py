import streamlit as st
st.set_page_config(page_title="Word Search Generator", layout="centered")

import random
import string
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

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

def add_decoy_fragments(grid, placed_positions, num_decoys: int, filler_chars: str):
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
        frag_len = random.randint(3, 5)
        frag = "".join(random.choice(letters) for _ in range(frag_len))
        dir_key = random.choice(list(DIRS.keys()))
        dr, dc = DIRS[dir_key]
        r0, c0 = random.randrange(rows), random.randrange(cols)

        coords = [(r0 + dr * i, c0 + dc * i) for i in range(frag_len)]
        if all(0 <= r < rows and 0 <= c < cols and grid[r][c] == "" for r, c in coords):
            for (rr, cc), ch in zip(coords, frag):
                grid[rr][cc] = ch
            added += 1

def fill_empty(grid, filler_chars: str):
    rows, cols = len(grid), len(grid[0])
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == "":
                grid[r][c] = random.choice(filler_chars)

# ----------------------------
# Generator
# ----------------------------
def generate_puzzle(words, rows, cols, allowed_dirs, extra_chars: str, decoy_fragments: int):
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
        random.shuffle(dirs_cycle)
        while not placed_ok and tries < 300:
            tries += 1
            dr_key = random.choice(dirs_cycle)
            dr, dc = DIRS[dr_key]
            r0 = random.randrange(rows)
            c0 = random.randrange(cols)
            if can_place(grid, w, r0, c0, dr, dc):
                coords = place_word(grid, w, r0, c0, dr, dc)
                placed.append((w, coords))
                placed_ok = True

    if decoy_fragments > 0:
        add_decoy_fragments(grid, placed, decoy_fragments, filler_chars)

    fill_empty(grid, filler_chars)

    return grid, placed, words_display

# ----------------------------
# PDF Export: puzzle + solution
# ----------------------------
def generate_pdf(grid, placed, words_display):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    cell = 20
    grid_cols = len(grid[0])
    grid_rows = len(grid)
    grid_x = width/2 - (grid_cols * cell)/2 + 110
    grid_y = height - 140

    def draw_word_list(title="Palabras:", words=None):
        c.setFont("Helvetica-Bold", 12)
        c.drawString(60, height - 110, title)
        c.setFont("Helvetica", 10)
        y = height - 130
        if not words:
            return
        col_height = 12 * 30
        col_x = [60, 180]
        col_idx, lines_in_col = 0, 0
        for w in words:
            c.drawString(col_x[col_idx], y - 12*lines_in_col, w.upper())
            lines_in_col += 1
            if 12*lines_in_col > col_height:
                col_idx += 1
                lines_in_col = 0
                if col_idx >= len(col_x):
                    y -= col_height + 20
                    col_idx = 0

    def draw_grid_letters(highlight_coords=None):
        for r in range(grid_rows):
            for col in range(grid_cols):
                x = grid_x + col * cell
                y = grid_y - r * cell
                ch = grid[r][col]
                if highlight_coords and (r, col) in highlight_coords:
                    c.setFillColor(colors.red)
                    c.setFont("Helvetica-Bold", 12)
                    c.drawString(x, y, ch.upper())
                    c.setFillColor(colors.black)
                    c.setFont("Helvetica", 12)
                else:
                    c.setFont("Helvetica", 12)
                    c.drawString(x, y, ch.upper())

    # Page 1
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, height - 60, "Sopa de Letras")
    draw_word_list("Palabras:", words_display)
    draw_grid_letters()
    c.showPage()

    # Page 2
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, height - 60, "Solución")
    highlights = set()
    for _, coords in placed:
        for rc in coords:
            highlights.add(rc)
    draw_word_list("Palabras:", words_display)
    draw_grid_letters(highlight_coords=highlights)
    c.showPage()

    c.save()
    buffer.seek(0)
    return buffer

# ----------------------------
# Streamlit UI
# ----------------------------
st.title("🧩 Generador de Sopa de Letras (con niveles y caracteres especiales)")

c1, c2 = st.columns(2)
rows = c1.number_input("Filas", min_value=5, max_value=40, value=15)
cols = c2.number_input("Columnas", min_value=5, max_value=40, value=15)

default_words = "niño\nasó\n’üsü\nhonduras\nbaleada\ntamales\nceiba\ncopán\nmarimba\niguana"
words_input = st.text_area("Palabras (una por línea):", default_words)
words_list = [w for w in (words_input.split("\n")) if w.strip()]

difficulty = st.selectbox(
    "Dificultad",
    ["Very easy", "Easy", "Medium", "Hard", "Very hard", "Extreme", "Custom"],
    index=2
)

all_dir_keys = list(DIRS.keys())
if difficulty == "Custom":
    allowed_dirs = st.multiselect(
        "Direcciones permitidas",
        options=all_dir_keys,
        default=["H", "HR", "V", "VR", "D1", "D4"]
    )
    decoys = st.slider("Decoys (fragmentos señuelo)", 0, 30, 6)
else:
    preset_dirs, preset_decoys = DIFFICULTY_PRESETS[difficulty]
    allowed_dirs = preset_dirs
    decoys = preset_decoys
    st.caption(f"Direcciones: {', '.join(allowed_dirs)} | Decoys: {decoys}")

use_specials = st.checkbox("🔡 Usar caracteres especiales en el relleno", value=True)
custom_specials = ""
if use_specials:
    custom_specials = st.text_input(
        "Caracteres especiales (separados por comas)",
        value="Ñ,Á,É,Í,Ó,Ú,Ü, ’"
    )
custom_specials = clean_specials_input(custom_specials) if use_specials else ""

if st.button("Generar sopa"):
    grid, placed, words_display = generate_puzzle(
        words=words_list,
        rows=rows,
        cols=cols,
        allowed_dirs=allowed_dirs,
        extra_chars=custom_specials,
        decoy_fragments=decoys
    )

    st.markdown("### 🧩 Vista previa")
    # collect solution coords
    solution_coords = set()
    for _, coords in placed:
        for rc in coords:
            solution_coords.add(rc)

    # build HTML table with bold solution letters
    html = "<table style='font-family: monospace; border-collapse: collapse;'>"
    for r in range(rows):
        html += "<tr>"
        for c in range(cols):
            ch = grid[r][c]
            if (r, c) in solution_coords:
                html += f"<td style='padding:3px;'><b>{ch}</b></td>"
            else:
                html += f"<td style='padding:3px;'>{ch}</td>"
        html += "</tr>"
    html += "</table>"

    st.markdown(html, unsafe_allow_html=True)

    pdf_buffer = generate_pdf(grid, placed, [w.upper() for w in words_display])
    st.download_button(
        "🗕 Descargar PDF (puzzle + solución)",
        data=pdf_buffer,
        file_name="sopa_de_letras.pdf",
        mime="application/pdf"
    )
