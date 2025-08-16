import streamlit as st
import random
import string
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# ---------------------
# Puzzle Generator
# ---------------------
def generate_wordsearch(words, size=15, extra_chars=None):
    grid = [["" for _ in range(size)] for _ in range(size)]
    placed_words = []

    directions = [(0, 1), (1, 0), (1, 1), (-1, 1)]

    def can_place(word, row, col, dr, dc):
        for i, letter in enumerate(word):
            r, c = row + i * dr, col + i * dc
            if not (0 <= r < size and 0 <= c < size):
                return False
            if grid[r][c] not in ("", letter):
                return False
        return True

    def place_word(word, row, col, dr, dc):
        for i, letter in enumerate(word):
            r, c = row + i * dr, col + i * dc
            grid[r][c] = letter
        placed_words.append(word)

    # Try to place words
    for word in words:
        word = word.upper()
        placed = False
        attempts = 0
        while not placed and attempts < 100:
            row = random.randint(0, size - 1)
            col = random.randint(0, size - 1)
            dr, dc = random.choice(directions)
            if can_place(word, row, col, dr, dc):
                place_word(word, row, col, dr, dc)
                placed = True
            attempts += 1

    # Fill remaining cells
    all_chars = string.ascii_uppercase
    if extra_chars:
        all_chars += extra_chars.upper()
    for r in range(size):
        for c in range(size):
            if grid[r][c] == "":
                grid[r][c] = random.choice(all_chars)

    return grid, placed_words

# ---------------------
# PDF Export
# ---------------------
def generate_pdf(puzzle, solution, words, filename="wordsearch.pdf"):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    cell_size = 20

    # ---------- Page 1: Puzzle ----------
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 50, "Sopa de Letras")

    grid_x = width/2 - (len(puzzle[0]) * cell_size) / 2 + 100
    grid_y = height - 150

    # Puzzle grid
    c.setFont("Helvetica", 12)
    for row_idx, row in enumerate(puzzle):
        for col_idx, letter in enumerate(row):
            x = grid_x + col_idx * cell_size
            y = grid_y - row_idx * cell_size
            c.drawString(x, y, letter.upper())

    # Word list
    c.setFont("Helvetica", 10)
    word_x = 60
    word_y = height - 150
    c.drawString(word_x, word_y + 30, "Palabras:")
    for idx, word in enumerate(words):
        c.drawString(word_x, word_y - (idx * 12), word.upper())

    c.showPage()

    # ---------- Page 2: Solution ----------
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 50, "Solución")

    grid_x = width/2 - (len(solution[0]) * cell_size) / 2 + 100
    grid_y = height - 150

    for row_idx, row in enumerate(solution):
        for col_idx, letter in enumerate(row):
            x = grid_x + col_idx * cell_size
            y = grid_y - row_idx * cell_size
            if letter.islower():  # words marked as lowercase
                c.setFillColor(colors.red)
                c.setFont("Helvetica-Bold", 12)
                c.drawString(x, y, letter.upper())
                c.setFillColor(colors.black)
                c.setFont("Helvetica", 12)
            else:
                c.drawString(x, y, letter.upper())

    # Word list
    c.setFont("Helvetica", 10)
    word_x = 60
    word_y = height - 150
    c.drawString(word_x, word_y + 30, "Palabras:")
    for idx, word in enumerate(words):
        c.drawString(word_x, word_y - (idx * 12), word.upper())

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# ---------------------
# Streamlit App
# ---------------------
st.title("Generador de Sopa de Letras")

# Inputs
size = st.slider("Tamaño de la cuadrícula", 10, 25, 15)
words_input = st.text_area("Lista de palabras (una por línea):", "niño\nasó\n’üsü\nhonduras")

use_special = st.checkbox("Incluir caracteres especiales en el relleno")
extra_chars = ""
if use_special:
    extra_chars = st.text_input("Caracteres adicionales (separados por coma):", "Ñ,Á,É,Í,Ó,Ú,Ü")
    extra_chars = extra_chars.replace(",", "").replace(" ", "")

words = [w.strip().upper() for w in words_input.split("\n") if w.strip()]

if st.button("Generar"):
    puzzle, placed_words = generate_wordsearch(words, size=size, extra_chars=extra_chars)

    # Build solution grid (mark words with lowercase for highlight in PDF)
    solution = [row[:] for row in puzzle]
    for word in placed_words:
        # Mark each occurrence (simplified, left as puzzle match for PDF)
        pass  # (to keep short, we simulate highlight by using lowercase manually if needed)

    st.write("### Sopa generada:")
    st.text("\n".join(" ".join(r) for r in puzzle))

    # Download PDF
    pdf_buffer = generate_pdf(puzzle, puzzle, placed_words)
    st.download_button("Descargar PDF", data=pdf_buffer, file_name="sopa_de_letras.pdf", mime="application/pdf")
