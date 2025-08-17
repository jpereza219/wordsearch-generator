import streamlit as st
import random
import string
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

# --- Helper functions ---
def clean_words(word_list):
    """Clean and normalize words: remove spaces, keep uppercase."""
    return [w.replace(" ", "").upper() for w in word_list if w.strip()]

def get_alphabet(include_special, extra_chars):
    alphabet = list(string.ascii_uppercase)
    if include_special:
        extra_chars = [c.strip().upper() for c in extra_chars.split(",") if c.strip()]
        alphabet.extend(extra_chars)
    return alphabet

def place_words(grid, words, directions):
    size = len(grid)
    for word in words:
        placed = False
        attempts = 0
        while not placed and attempts < 200:
            direction = random.choice(directions)
            if direction == "H":
                row = random.randint(0, size-1)
                col = random.randint(0, size-len(word))
                if all(grid[row][col+i] in ("", word[i]) for i in range(len(word))):
                    for i in range(len(word)):
                        grid[row][col+i] = word[i]
                    placed = True
            elif direction == "HR":
                row = random.randint(0, size-1)
                col = random.randint(len(word)-1, size-1)
                if all(grid[row][col-i] in ("", word[i]) for i in range(len(word))):
                    for i in range(len(word)):
                        grid[row][col-i] = word[i]
                    placed = True
            elif direction == "V":
                row = random.randint(0, size-len(word))
                col = random.randint(0, size-1)
                if all(grid[row+i][col] in ("", word[i]) for i in range(len(word))):
                    for i in range(len(word)):
                        grid[row+i][col] = word[i]
                    placed = True
            elif direction == "VR":
                row = random.randint(len(word)-1, size-1)
                col = random.randint(0, size-1)
                if all(grid[row-i][col] in ("", word[i]) for i in range(len(word))):
                    for i in range(len(word)):
                        grid[row-i][col] = word[i]
                    placed = True
            elif direction == "D":
                row = random.randint(0, size-len(word))
                col = random.randint(0, size-len(word))
                if all(grid[row+i][col+i] in ("", word[i]) for i in range(len(word))):
                    for i in range(len(word)):
                        grid[row+i][col+i] = word[i]
                    placed = True
            elif direction == "DR":
                row = random.randint(len(word)-1, size-1)
                col = random.randint(len(word)-1, size-1)
                if all(grid[row-i][col-i] in ("", word[i]) for i in range(len(word))):
                    for i in range(len(word)):
                        grid[row-i][col-i] = word[i]
                    placed = True
            attempts += 1
    return grid

def fill_grid(grid, alphabet, decoy_density=0):
    size = len(grid)
    for r in range(size):
        for c in range(size):
            if grid[r][c] == "":
                if decoy_density > 0 and random.random() < decoy_density:
                    grid[r][c] = random.choice(alphabet)
                else:
                    grid[r][c] = random.choice(alphabet)
    return grid

def generate_pdf(grid, solution_grid, words, puzzle_size):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Puzzle Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Sopa de Letras")

    # Word List (left side)
    c.setFont("Helvetica", 10)
    y = height - 80
    c.drawString(50, y, "Lista de palabras:")
    y -= 15
    for word in words:
        c.drawString(50, y, word)
        y -= 12
        if y < 50:
            c.showPage()
            y = height - 50

    # Puzzle Grid
    c.setFont("Courier", 12)
    start_x = 200
    start_y = height - 100
    for r in range(puzzle_size):
        row_str = " ".join(grid[r])
        c.drawString(start_x, start_y - r*15, row_str)

    c.showPage()

    # Solution page
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Solución")

    start_y = height - 100
    for r in range(puzzle_size):
        row_str = " ".join(solution_grid[r])
        c.drawString(50, start_y - r*15, row_str)

    c.save()
    buffer.seek(0)
    return buffer

# --- Streamlit UI ---
st.title("Generador de Sopa de Letras Cultural (Honduras)")

puzzle_size = st.slider("Tamaño del tablero", 10, 25, 15)

words_input = st.text_area("Palabras (separadas por coma):", "niño, asó, ’üsü, san pedro sula")
words = clean_words(words_input.split(","))

# Difficulty levels
difficulty = st.selectbox(
    "Nivel de dificultad",
    ["Very Easy", "Easy", "Medium", "Hard", "Very Hard", "Extreme"]
)

include_special = st.checkbox("¿Incluir caracteres especiales?")
extra_chars = ""
if include_special:
    extra_chars = st.text_input("Caracteres adicionales (separados por coma):", "Ñ, Á, É, Í, Ó, Ú, Ü, ’")

alphabet = get_alphabet(include_special, extra_chars)

# Difficulty mapping
directions_map = {
    "Very Easy": ["H", "V"],
    "Easy": ["H", "V", "HR", "VR"],
    "Medium": ["H", "V", "HR", "VR", "D"],
    "Hard": ["H", "V", "HR", "VR", "D", "DR"],
    "Very Hard": ["H", "V", "HR", "VR", "D", "DR"],
    "Extreme": ["H", "V", "HR", "VR", "D", "DR"]
}
decoy_density_map = {
    "Very Easy": 0.0,
    "Easy": 0.0,
    "Medium": 0.0,
    "Hard": 0.0,
    "Very Hard": 0.1,
    "Extreme": 0.3
}

if st.button("Generar Sopa de Letras"):
    grid = [["" for _ in range(puzzle_size)] for _ in range(puzzle_size)]
    solution_grid = [["" for _ in range(puzzle_size)] for _ in range(puzzle_size)]

    grid = place_words(grid, words, directions_map[difficulty])
    solution_grid = [row[:] for row in grid]
    grid = fill_grid(grid, alphabet, decoy_density_map[difficulty])

    st.write("### Puzzle:")
    for row in grid:
        st.text(" ".join(row))

    st.write("### Solución:")
    for row in solution_grid:
        st.text(" ".join(row))

    pdf_buffer = generate_pdf(grid, solution_grid, words, puzzle_size)
    st.download_button("Descargar PDF", data=pdf_buffer, file_name="sopa_de_letras.pdf", mime="application/pdf")
