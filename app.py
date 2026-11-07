import streamlit as st
st.set_page_config(page_title="Word Search Generator", layout="centered")

import secrets

from motor import DIRS, DIFFICULTY_PRESETS, clean_specials_input, generate_puzzle
from pdf import generate_pdf

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

seed_input = st.text_input("Semilla (dejar vacío para una nueva)", value="")

if st.button("Generar sopa"):
    seed_text = seed_input.strip()
    if seed_text:
        try:
            seed = int(seed_text)
        except ValueError:
            st.error("La semilla debe ser un número entero (o dejarse vacía).")
            st.stop()
    else:
        seed = secrets.randbelow(10**9)

    grid, placed, words_display = generate_puzzle(
        words=words_list,
        rows=rows,
        cols=cols,
        allowed_dirs=allowed_dirs,
        extra_chars=custom_specials,
        decoy_fragments=decoys,
        seed=seed
    )

    st.write(f"Semilla usada: {seed}")

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
