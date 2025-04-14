import streamlit as st
import random
import string
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Direction vectors
DIRECTIONS = {
    'H':  (0, 1), 'HR': (0, -1),
    'V':  (1, 0), 'VR': (-1, 0),
    'D1':  (1, 1), 'D2': (-1, -1),
    'D3': (-1,1), 'D4': (1,-1)
}

# Core grid helpers
def can_place(grid, word, row, col, direction):
    dr, dc = DIRECTIONS[direction]
    for i, char in enumerate(word):
        r, c = row + dr * i, col + dc * i
        if not (0 <= r < len(grid) and 0 <= c < len(grid[0])) or (grid[r][c] not in ('', char)):
            return False
    return True

def place_word(grid, word, row, col, direction):
    dr, dc = DIRECTIONS[direction]
    coords = [(row + dr * i, col + dc * i) for i in range(len(word))]
    for (r, c), char in zip(coords, word):
        grid[r][c] = char
    return coords

def fill_grid(grid):
    for r in range(len(grid)):
        for c in range(len(grid[0])):
            if grid[r][c] == '':
                grid[r][c] = random.choice(string.ascii_uppercase)

# Word placement logic with overlap scoring
def find_best_position(grid, word, orientations):
    best_score, best_position = -1, None
    rows, cols = len(grid), len(grid[0])

    for direction in orientations:
        dr, dc = DIRECTIONS[direction]
        for row in range(rows):
            for col in range(cols):
                score, valid = 0, True
                for i, char in enumerate(word):
                    r, c = row + dr * i, col + dc * i
                    if not (0 <= r < rows and 0 <= c < cols):
                        valid = False
                        break
                    existing = grid[r][c]
                    if existing not in ('', char):
                        valid = False
                        break
                    if existing == char:
                        score += 1
                if valid and score >= best_score:
                    best_score = score
                    best_position = (row, col, direction)
    return best_position

# Decoy fragment insertion for difficulty
def add_decoys(grid, placed_words, num_decoys=5):
    rows, cols = len(grid), len(grid[0])
    fragments = []

    for word, *_ in placed_words:
        if len(word) > 3:
            start = random.randint(0, len(word) - 4)
            frag_len = random.randint(3, min(5, len(word) - start))
            fragments.append(word[start:start + frag_len])

    random.shuffle(fragments)
    added = 0

    while added < num_decoys and fragments:
        frag = fragments.pop()
        direction = random.choice(list(DIRECTIONS.keys()))
        dr, dc = DIRECTIONS[direction]

        row = random.randint(0, rows - 1)
        col = random.randint(0, cols - 1)

        coords = [(row + dr * i, col + dc * i) for i in range(len(frag))]
        if all(0 <= r < rows and 0 <= c < cols and grid[r][c] == '' for r, c in coords):
            for (r, c), char in zip(coords, frag):
                grid[r][c] = char
            added += 1

# Puzzle builder wrapper
def generate_puzzle(grid_size, num_words, word_list, orientations, difficulty_mode=False):
    rows, cols = grid_size
    grid = [['' for _ in range(cols)] for _ in range(rows)]
    placed_words = []

    filtered_words = [w.upper() for w in word_list if len(w.strip()) <= max(rows, cols)]
    random.shuffle(filtered_words)

    for word in filtered_words[:num_words]:
        pos = find_best_position(grid, word, orientations)
        if pos:
            r, c, d = pos
            coords = place_word(grid, word, r, c, d)
            placed_words.append((word, d, r, c, coords))

    if difficulty_mode:
        add_decoys(grid, placed_words)

    fill_grid(grid)
    return grid, placed_words

# Grid HTML view
def display_grid(grid, highlight_coords=None):
    html = "<table style='font-family: monospace; border-collapse: collapse;'>"
    highlight_coords = set(highlight_coords or [])  # Ensure it's a set

    for r in range(len(grid)):
        html += "<tr>"
        for c in range(len(grid[0])):
            char = grid[r][c]
            is_highlighted = (r, c) in highlight_coords
            style = (
                "padding:5px; border:1px solid #ccc; text-align:center;"
                + (" background-color: yellow; font-weight: bold;" if is_highlighted else "")
            )
            html += f"<td style='{style}'>{char}</td>"
        html += "</tr>"
    html += "</table>"
    return html

# PDF export
def generate_pdf(grid, solution_coords):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    def draw_grid(grid, x, y, highlight=None):
        size = 14
        for r, row in enumerate(grid):
            for c_index, char in enumerate(row):
                px, py = x + c_index * size, y - r * size
                c.setFont("Helvetica-Bold" if highlight and (r, c_index) in highlight else "Helvetica", 12)
                c.setFillColorRGB(1, 0, 0) if highlight and (r, c_index) in highlight else c.setFillColorRGB(0, 0, 0)
                c.drawString(px, py, char)

    c.drawString(50, 750, "Word Search Puzzle")
    draw_grid(grid, 50, 700)
    c.showPage()
    c.drawString(50, 750, "Solution View")
    draw_grid(grid, 50, 700, highlight=solution_coords)
    c.save()
    buffer.seek(0)
    return buffer

# --- Streamlit UI ---
st.set_page_config(page_title="Word Search Generator", layout="centered")
st.title("🧩 Word Search Puzzle Generator")

cols = st.columns(2)
rows = cols[0].number_input("Grid Rows", min_value=5, max_value=30, value=10)
cols = cols[1].number_input("Grid Columns", min_value=5, max_value=30, value=10)

num_words = st.slider("Number of Words to Place", 1, 20, 5)
word_input = st.text_area("Enter Words (comma-separated)", "export, import, invoice, shipment, freight")
orientation_options = st.multiselect("Allowed Directions", list(DIRECTIONS.keys()), default=['H', 'HR', 'V', 'VR', 'D1', 'D2', 'D3', 'D4'])
difficulty_mode = st.checkbox("🎯 Add Difficulty (decoy fragments)", value=False)

if st.button("Generate Puzzle"):
    words = [w.strip() for w in word_input.split(',') if w.strip()]
    grid, placed = generate_puzzle((rows, cols), num_words, words, set(orientation_options), difficulty_mode)
    st.session_state["grid"] = grid
    st.session_state["placed"] = placed

if "grid" in st.session_state and "placed" in st.session_state:
    grid = st.session_state["grid"]
    placed = st.session_state["placed"]

    st.markdown("### 🔤 Puzzle Grid")
    st.markdown(display_grid(grid), unsafe_allow_html=True)

    if placed:
        st.markdown("### ✅ Words Placed")
        for word, d, r, c, _ in placed:
            st.markdown(f"**{word}** at ({r}, {c}) `{d}`")

    solution_coords = {(r, c) for *_, coords in placed for (r, c) in coords}
    st.markdown("### 🧠 Solution View")
    st.markdown(display_grid(grid, highlight_coords=solution_coords), unsafe_allow_html=True)

    pdf = generate_pdf(grid, solution_coords)
    st.download_button("🗕️ Download PDF (Puzzle + Solution)", data=pdf, file_name="wordsearch_puzzle.pdf", mime="application/pdf")
