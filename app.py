import streamlit as st
st.set_page_config(page_title="Word Search Generator", layout="centered")

import base64
import secrets

from motor import DIRS, DIFFICULTY_PRESETS, PuzzleError, clean_specials_input, create_puzzle
from salidas import file_names, grid_svg, grid_text, puzzle_files, puzzle_zip

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

    try:
        result = create_puzzle(
            words=words_list,
            rows=rows,
            cols=cols,
            allowed_dirs=allowed_dirs,
            extra_chars=custom_specials,
            decoy_fragments=decoys,
            seed=seed
        )
    except PuzzleError as e:
        st.session_state.pop("puzzle", None)
        for message in e.errors:
            st.error(message)
        st.stop()

    # Se guarda todo lo generado para que la vista previa no desaparezca al
    # pulsar un botón de descarga (cada clic vuelve a ejecutar el script).
    files = puzzle_files(result.grid, result.placed, result.words_display, seed)
    st.session_state["puzzle"] = {
        "seed": seed,
        "result": result,
        "files": files,
        "zip": puzzle_zip(files),
        "text": grid_text(result.grid),
        "solution_svg": grid_svg(result.grid, result.placed, solution=True),
    }

puzzle = st.session_state.get("puzzle")
if puzzle:
    seed, result = puzzle["seed"], puzzle["result"]
    grid, placed, words_display = result.grid, result.placed, result.words_display
    names = file_names(seed)

    st.write(f"Semilla usada: {seed}")
    st.write(f"{len(placed)} de {len(words_display)} palabras colocadas")
    for message in result.warnings:
        st.warning(message)

    st.markdown("### 🧩 Vista previa")
    # collect solution coords
    solution_coords = set()
    for _, coords in placed:
        for rc in coords:
            solution_coords.add(rc)

    # build HTML table with bold solution letters
    html = "<table style='font-family: monospace; border-collapse: collapse;'>"
    for r in range(len(grid)):
        html += "<tr>"
        for c in range(len(grid[0])):
            ch = grid[r][c]
            if (r, c) in solution_coords:
                html += f"<td style='padding:3px;'><b>{ch}</b></td>"
            else:
                html += f"<td style='padding:3px;'>{ch}</td>"
        html += "</tr>"
    html += "</table>"

    st.markdown(html, unsafe_allow_html=True)

    st.download_button(
        "🗕 Descargar PDF (puzzle + solución)",
        data=puzzle["files"][names["pdf"]],
        file_name=names["pdf"],
        mime="application/pdf"
    )
    st.download_button(
        "🗂 Descargar todo (ZIP)",
        data=puzzle["zip"],
        file_name=f"s{seed}_sopa.zip",
        mime="application/zip"
    )

    st.markdown("### 📋 Cuadrícula en texto")
    st.caption("Una fila por línea, letras separadas por un espacio. Usa el botón de copiar.")
    st.code(puzzle["text"], language=None)

    st.markdown("### ✅ Solución")
    svg_b64 = base64.b64encode(puzzle["solution_svg"].encode("utf-8")).decode("ascii")
    st.markdown(
        f'<img alt="Solución" style="max-width:100%;" src="data:image/svg+xml;base64,{svg_b64}">',
        unsafe_allow_html=True,
    )
