import streamlit as st
import random
import string
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# Register a Unicode font to support accents and ñ
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))

# ----------------------------
# Directions
# ----------------------------
DIRS = {
    "horizontal": (0, 1),
    "horizontal_rev": (0, -1),
    "vertical": (1, 0),
    "vertical_rev": (-1, 0),
    "diagonal": (1, 1),
    "diagonal_rev": (-1, -1),
    "diag_up": (-1, 1),
    "diag_up_rev": (-1, -1)
}

# Difficulty levels
DIFFICULTY_SETTINGS = {
    "Very Easy": ["horizontal", "vertical"],
    "Easy": ["horizontal", "horizontal_rev", "vertical", "vertical_rev"],
    "Medium": ["horizontal", "horizontal_rev", "vertical", "vertical_rev",
               "diagonal", "diagonal_rev"],
    "Hard": ["horizontal", "horizontal_rev", "vertical", "vertical_rev",
             "diagonal", "diagonal_rev", "diag_up", "diag_up_rev"],
    "Very Hard": ["horizontal", "horizontal_rev", "vertical", "vertical_rev",
                  "diagonal", "diagonal_rev", "diag_up", "diag_up_rev"],
    "Extreme": ["horizontal", "horizontal_rev", "vertical", "vertical_rev",
                "diagonal", "diagonal_rev", "diag_up", "diag_up_rev"]
}

# ----------------------------
# Helpers
# ----------------------------
def can_place(grid, word, r, c, dr, dc):
    rows, cols = len(grid), len(grid[0])
    for i in range(len(word)):
        rr = r + dr * i
        cc = c + dc * i
        if not (0 <= rr < rows and 0 <= cc < cols):
            return False
        if grid[rr][cc] not in ("", word[i]):
            return False
    return True

def place_word(grid, word, r, c, dr, dc):
    coords = []
    for i in range(len(word)):
        rr = r + dr * i
        cc = c + dc * i
        grid[rr][cc] = word[i]
        coords.append((rr, cc))
    return coords

def fill_empty(grid, filler_chars):
    for r in range(len(grid)):
        for c in range(len(grid[0])):
            if grid[r][c] == "":
                grid[r][c] = random.choice(filler_chars)

def add_decoy_fragments(grid, placed, decoy_count, filler_chars):
    # Add random fake word fragments
    rows, cols = len(grid), len(grid[0])
    for _ in range(decoy_count):
        frag_len = random.randint(3, 6)
        frag = "".join(random.choice(filler_chars) for _ in range(frag_len))
        tries = 0
        while tries < 100:
            tries += 1
            dr, dc = random.choice(list(DIRS.values()))
            r0 = random.randrange(rows)
            c0 = random.randrange(cols)
            if can_place(grid, frag, r0, c0, dr, dc):
                place_word(grid, frag, r0, c0, dr, dc)
                break

# ----------------------------
# Generator
# ----------------------------
def generate_puzzle(words, rows, cols, allowed_dirs, extra_chars: str, decoy_fragments: int):
    grid = [["" for _ in range(cols)] for _ in range(rows)]
    
    # Keep original words for the list
    words_original = [w.strip() for w in words if w.strip()]
    # Clean for placement: remove spaces
    words_clean = [w.strip().replace(" ", "") for w in words if w.strip()]
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

    return grid, placed, words_original

# ----------------------------
# PDF Export
# ----------------------------
def export_pdf(grid, placed, words_original, show_solution=False):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    cell_size = 18
    margin_x = 50
    margin_y = height - 50
    word_list_x = width - 200  # right side column

    # Draw grid
    for r, row in enumerate(grid):
        for cidx, val in enumerate(row):
            x = margin_x + cidx * cell_size
            y = margin_y - r * cell_size
            if show_solution and any((r, cidx) in coords for _, coords in placed):
                c.setFillColor(colors.red)
            else:
                c.setFillColor(colors.black)
            c.setFont("HeiseiMin-W3", 12)
            c.drawString(x, y, val)

    # Word list
    c.setFillColor(colors.black)
    c.setFont("HeiseiMin-W3", 10)
    c.drawString(word_list_x, margin_y, "Lista de palabras:")
    y_offset = margin_y - 20
    for w in words_original:
        c.drawString(word_list_x, y_offset, w)
        y_offset -= 15

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# ----------------------------
# Streamlit UI
# ----------------------------
st.title("Generador de Sopas de Letras - Honduras en Palabras")

st.sidebar.header("Configuración")

rows = st.sidebar.number_input("Filas", 10, 50, 15)
cols = st.sidebar.number_input("Columnas", 10, 50, 15)

difficulty = st.sidebar.selectbox("Dificultad",
    ["Very Easy", "Easy", "Medium", "Hard", "Very Hard", "Extreme"])

use_specials = st.sidebar.checkbox("Incluir caracteres especiales")
extra_chars = ""
if use_specials:
    extra_chars = st.sidebar.text_input("Caracteres especiales (ej: Ñ,Á,É,Í,Ó,Ú,Ü,’)")

decoy_fragments = 0
if difficulty == "Very Hard":
    decoy_fragments = 5
elif difficulty == "Extreme":
    decoy_fragments = 15

allowed_dirs = DIFFICULTY_SETTINGS[difficulty]

words_input = st.text_area("Ingrese palabras (una por línea):", height=200)
words = words_input.split("\n")

if st.button("Generar"):
    grid, placed, words_original = generate_puzzle(
        words, rows, cols, allowed_dirs, extra_chars, decoy_fragments
    )

    st.write("### Puzzle")
    st.text("\n".join(" ".join(row) for row in grid))

    # PDF download links
    pdf_puzzle = export_pdf(grid, placed, words_original, show_solution=False)
    st.download_button("📥 Descargar PDF (Puzzle)", data=pdf_puzzle,
                       file_name="puzzle.pdf", mime="application/pdf")

    pdf_solution = export_pdf(grid, placed, words_original, show_solution=True)
    st.download_button("📥 Descargar PDF (Solución)", data=pdf_solution,
                       file_name="solution.pdf", mime="application/pdf")
