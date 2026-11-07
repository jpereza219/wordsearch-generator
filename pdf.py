"""Exportación a PDF (sin dependencias de Streamlit).

Código movido desde app.py sin cambios.
"""

from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

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
