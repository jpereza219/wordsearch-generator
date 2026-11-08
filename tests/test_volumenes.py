"""Paso 6: bancos de palabras por volumen."""

import io
import json
import zipfile

import pytest

import ficha as fichamod
import motor
import pdf
import salidas
import volumenes as vol
from volumenes import VolumenError, parse_volume

PUZZLES = """puzzle,titulo,filas,columnas,dificultad,senuelos,especiales,notas
1,Próceres de Honduras,,,,,,ejemplo
2,Pueblos y ríos,15,15,Hard,,"Ñ,Á,É,Í,Ó,Ú,Ü,-,’",ejemplo
3,Repaso,12,12,Easy,4,,ejemplo
"""
PALABRAS = """puzzle,palabra,oculta
1,LEMPIRA,
1,MORAZÁN,
1,CABAÑAS,
1,POLICARPO PAZ,
1,NUESTRA,sí
2,PUCA-OPALACA,
2,’ÜSÜ,
2,AGÜERO,
2,ÑANDÚ,
2,HISTORIA,X
3,REFORMA,
3,COLONIA,
3,VIVE,1
"""


def _to(text, sep=",", bom=False):
    """Convierte el CSV de ejemplo a punto y coma y/o con BOM, como haría Excel."""
    if sep == ";":
        import csv
        rows = list(csv.reader(io.StringIO(text)))
        out = io.StringIO()
        csv.writer(out, delimiter=";", lineterminator="\r\n").writerows(rows)
        text = out.getvalue()
    data = text.encode("utf-8")
    return (b"\xef\xbb\xbf" + data) if bom else data


def _errors(puzzles, palabras):
    with pytest.raises(VolumenError) as exc:
        parse_volume(puzzles.encode("utf-8"), palabras.encode("utf-8"))
    return exc.value.errors


# ----------------------------------------------------------------- lectura

@pytest.mark.parametrize("sep", [",", ";"])
@pytest.mark.parametrize("bom", [False, True])
def test_lectura_coma_y_punto_y_coma_con_y_sin_bom(sep, bom):
    v = parse_volume(_to(PUZZLES, sep, bom), _to(PALABRAS, sep, bom), nombre="vol9")
    assert [p.numero for p in v.puzzles] == [1, 2, 3]
    p1, p2, p3 = v.puzzles
    assert p1.titulo == "Próceres de Honduras"
    assert p1.palabras == ["LEMPIRA", "MORAZÁN", "CABAÑAS", "POLICARPO PAZ"]
    assert p2.palabras == ["PUCA-OPALACA", "’ÜSÜ", "AGÜERO", "ÑANDÚ"]
    assert p2.especiales == "Ñ,Á,É,Í,Ó,Ú,Ü,-,’"
    assert (p2.filas, p2.columnas, p2.dificultad) == (15, 15, "Hard")
    assert (p3.senuelos, p3.dificultad) == (4, "Easy")
    assert [p.ocultas for p in v.puzzles] == [["NUESTRA"], ["HISTORIA"], ["VIVE"]]


def test_valores_de_oculta_aceptados():
    words = "puzzle,palabra,oculta\n" + "\n".join(
        f"1,PALABRA{i},{flag}" for i, flag in enumerate(["sí", "si", "SÍ", "Si", "x", "X", "1", "", "no", "0"])
    ) + "\n"
    v = parse_volume(b"puzzle,titulo\n1,Uno\n", words.encode("utf-8"))
    assert len(v.puzzles[0].ocultas) == 7 and len(v.puzzles[0].palabras) == 3


def test_encabezados_con_tildes_y_mayusculas():
    v = parse_volume("Puzzle;Título;Señuelos\n1;Uno;3\n".encode("utf-8"),
                     "PUZZLE;Palabra;Oculta\n1;SOL;\n".encode("utf-8"))
    assert v.puzzles[0].senuelos == 3 and v.puzzles[0].titulo == "Uno"


def test_nfd_se_normaliza():
    import unicodedata
    nfd = unicodedata.normalize("NFD", "MORAZÁN")
    v = parse_volume(b"puzzle,titulo\n1,Uno\n", f"puzzle,palabra\n1,{nfd}\n".encode("utf-8"))
    assert v.puzzles[0].palabras == ["MORAZÁN"]


def test_no_utf8_da_error_claro():
    with pytest.raises(VolumenError, match="UTF-8"):
        parse_volume("puzzle,titulo\n1,Próceres\n".encode("latin-1"), b"puzzle,palabra\n")


# ----------------------------------------------------------------- errores

def test_puzzle_sin_titulo():
    errors = _errors("puzzle,titulo\n1,Uno\n2,\n", "puzzle,palabra\n1,SOL\n")
    assert errors == ["puzzles.csv, línea 3: el puzzle no tiene título."]


@pytest.mark.parametrize("n", ["0", "51", "-3"])
def test_numero_fuera_de_rango(n):
    errors = _errors(f"puzzle,titulo\n1,Uno\n{n},Dos\n", "puzzle,palabra\n1,SOL\n")
    assert errors == [f"puzzles.csv, línea 3: «puzzle» debe estar entre 1 y 50 (dice {int(n)})."]


def test_numero_no_numerico():
    errors = _errors("puzzle,titulo\nuno,Uno\n", "puzzle,palabra\n")
    assert errors == ["puzzles.csv, línea 2: «puzzle» debe ser un número entero (dice «uno»)."]


def test_numero_repetido():
    errors = _errors("puzzle,titulo\n1,Uno\n2,Dos\n1,Otra vez\n", "puzzle,palabra\n1,SOL\n")
    assert errors == ["puzzles.csv, línea 4: el puzzle 1 está repetido (ya aparece en la línea 2)."]


def test_palabra_a_puzzle_inexistente():
    errors = _errors("puzzle,titulo\n1,Uno\n", "puzzle,palabra\n1,SOL\n7,LUNA\n")
    assert errors == ["palabras.csv, línea 3: la palabra «LUNA» apunta al puzzle 7, que no está en puzzles.csv."]


def test_columnas_faltantes():
    errors = _errors("numero,titulo\n1,Uno\n", "puzzle,termino\n1,SOL\n")
    assert errors == [
        "puzzles.csv: faltan columnas: puzzle (línea 1, encabezados).",
        "palabras.csv: faltan columnas: palabra (línea 1, encabezados).",
    ]


def test_otros_valores_invalidos_con_linea():
    errors = _errors(
        "puzzle,titulo,filas,dificultad\n1,Uno,quince,\n2,Dos,,Difícil\n",
        "puzzle,palabra,oculta\n1,SOL,quizá\n1,,\n",
    )
    assert "puzzles.csv, línea 2: «filas» debe ser un número entero (dice «quince»)." in errors
    assert any(e.startswith("puzzles.csv, línea 3: dificultad desconocida «Difícil»") for e in errors)
    assert "palabras.csv, línea 2: en «oculta» escribe «sí» o déjalo vacío (dice «quizá»)." in errors
    assert "palabras.csv, línea 3: la palabra está vacía." in errors


def test_lineas_con_filas_vacias_y_punto_y_coma():
    # Excel deja filas vacías; la línea del error debe ser la real del archivo.
    puzzles = "puzzle;titulo\r\n1;Uno\r\n;\r\n\r\n2;\r\n"
    errors = _errors(puzzles, "puzzle;palabra\r\n1;SOL\r\n")
    assert errors == ["puzzles.csv, línea 5: el puzzle no tiene título."]


# ----------------------------------------------------------------- avisos

def test_avisos():
    v = parse_volume(
        "puzzle,titulo\n1,Uno\n2,Dos\n3,Tres\n".encode("utf-8"),
        "puzzle,palabra,oculta\n1,YORO,\n1,LA PAZ,\n1,HOLA,sí\n3,yoro,\n3,LA  PAZ,\n3,ADIÓS,sí\n".encode("utf-8"),
    )
    assert "El puzzle 2 («Dos») no tiene palabras (puzzles.csv, línea 3)." in v.warnings
    assert "El puzzle 2 («Dos») no tiene palabra oculta de la Ruta Secreta." in v.warnings
    assert "«YORO» se repite en el volumen: puzzle 1 (línea 2), puzzle 3 (línea 5)." in v.warnings
    assert "«LA PAZ» se repite en el volumen: puzzle 1 (línea 3), puzzle 3 (línea 6)." in v.warnings
    assert len(v.warnings) == 4


# ----------------------------------------------------------------- resumen

def test_ruta_secreta_en_orden_de_puzzle():
    # puzzles.csv y palabras.csv desordenados a propósito.
    v = parse_volume(
        "puzzle,titulo\n3,Tres\n1,Uno\n2,Dos\n".encode("utf-8"),
        "puzzle,palabra,oculta\n3,UNIDA,sí\n2,PATRIA,sí\n1,NUESTRA,sí\n3,SIEMPRE,sí\n1,SOL,\n".encode("utf-8"),
    )
    assert v.ruta_secreta == "NUESTRA PATRIA UNIDA SIEMPRE"
    assert v.resumen() == {"volumen": "borrador", "puzzles": 3, "palabras": 1, "ocultas": 4,
                           "ruta_secreta": "NUESTRA PATRIA UNIDA SIEMPRE"}


# ----------------------------------------------------------------- volúmenes del repositorio

@pytest.mark.parametrize("nombre", vol.list_volumes())
def test_volumenes_del_repositorio_son_validos_y_generan(nombre):
    """Cada volumen subido a volumenes/ se lee sin errores y todos sus puzzles se generan."""
    v = vol.load_volume(nombre)
    for p in v.puzzles:
        if not p.palabras:
            continue
        c = vol.resolve_config(p)
        motor.create_puzzle(c["palabras"], c["filas"], c["columnas"], c["allowed_dirs"], c["extra_chars"],
                            c["senuelos"], seed=1, hidden_words=c["ocultas"])


def test_vol2_de_ejemplo():
    v = vol.load_volume("vol2")
    assert v.resumen() == {"volumen": "vol2", "puzzles": 3, "palabras": 11, "ocultas": 3,
                           "ruta_secreta": "NUESTRA HISTORIA VIVE"}
    assert all("EJEMPLO" in p.notas for p in v.puzzles)
    assert "vol2" in vol.list_volumes()


# ----------------------------------------------------------------- configuración

def test_resolve_config_valores_de_la_app_y_propios():
    v = parse_volume(_to(PUZZLES), _to(PALABRAS))
    c1, c2, c3 = (vol.resolve_config(p) for p in v.puzzles)
    assert (c1["filas"], c1["columnas"], c1["dificultad"], c1["senuelos"]) == (15, 15, "Medium", 0)
    assert c1["especiales_campo"] == "Ñ,Á,É,Í,Ó,Ú,Ü, ’" and c1["extra_chars"] == "ÑÁÉÍÓÚÜ’"
    assert c2["dificultad"] == "Hard" and c2["allowed_dirs"] == motor.DIFFICULTY_PRESETS["Hard"][0]
    assert c2["extra_chars"] == "ÑÁÉÍÓÚÜ-’"
    # Señuelos distintos de los de Easy: Custom con las direcciones de Easy.
    assert (c3["dificultad"], c3["allowed_dirs"], c3["senuelos"]) == ("Custom", ["H", "HR", "V", "VR"], 4)


def test_desde_volumen_igual_que_a_mano():
    v = parse_volume(_to(PUZZLES), _to(PALABRAS))
    p = v.puzzle(2)
    c = vol.resolve_config(p)
    desde_volumen = motor.create_puzzle(c["palabras"], c["filas"], c["columnas"], c["allowed_dirs"],
                                        c["extra_chars"], c["senuelos"], seed=77, hidden_words=c["ocultas"])
    a_mano = motor.create_puzzle(
        ["PUCA-OPALACA", "’ÜSÜ", "AGÜERO", "ÑANDÚ"], 15, 15,
        ["H", "HR", "V", "VR", "D1", "D4", "D2", "D3"], motor.clean_specials_input("Ñ,Á,É,Í,Ó,Ú,Ü,-,’"), 0,
        seed=77, hidden_words=["HISTORIA"],
    )
    assert (desde_volumen.grid, desde_volumen.placed) == (a_mano.grid, a_mano.placed)


# ----------------------------------------------------------------- nombres, ficha y PDF

@pytest.mark.parametrize("title,expected", [
    ("Próceres de Honduras", "proceres-de-honduras"),
    ("Ñandú, ’Üsü y el río: ¿qué tal?", "nandu-usu-y-el-rio-que-tal"),
    ("Una frase muy larga que no cabe en treinta caracteres", "una-frase-muy-larga-que-no-cab"),
    ("", ""),
])
def test_titulo_corto(title, expected):
    assert vol.short_title(title) == expected
    assert len(vol.short_title(title)) <= 30


def test_nombres_de_archivo_con_volumen():
    names = salidas.file_names(123, volume="vol2", puzzle=7, title="Próceres de Honduras")
    assert names["solucion_svg"] == "v2_p07_proceres-de-honduras_s123_solucion.svg"
    assert names["zip"] == "v2_p07_proceres-de-honduras_s123_sopa.zip"
    assert salidas.file_names(123)["solucion_svg"] == "s123_solucion.svg"  # sin volumen, como antes
    assert salidas.file_names(123, title="Solo título")["solucion_svg"] == "s123_solucion.svg"
    assert vol.volume_tag("vol12") == "v12" and vol.volume_tag("borrador") == "borrador"


def test_ficha_y_zip_con_volumen_puzzle_y_titulo():
    v = vol.load_volume("vol2")
    p = v.puzzle(1)
    c = vol.resolve_config(p)
    r = motor.create_puzzle(c["palabras"], c["filas"], c["columnas"], c["allowed_dirs"], c["extra_chars"],
                            c["senuelos"], seed=5, hidden_words=c["ocultas"])
    f = fichamod.build_ficha(r, seed=5, rows=c["filas"], cols=c["columnas"], allowed_dirs=c["allowed_dirs"],
                             decoys=c["senuelos"], extra_chars=c["extra_chars"], words=c["palabras"],
                             hidden_words=c["ocultas"], difficulty=c["dificultad"],
                             specials_field=c["especiales_campo"], title=p.titulo, volume="vol2", puzzle=1)
    assert (f["volumen"], f["puzzle"], f["titulo"]) == ("vol2", 1, "Próceres de Honduras")
    files = salidas.puzzle_files(r.grid, r.placed, r.words_display, 5, hidden=r.hidden_words, ficha=f,
                                 volume="vol2", puzzle=1, title=p.titulo)
    assert len(files) == 8
    assert all(name.startswith("v2_p01_proceres-de-honduras_s5_") for name in files)
    stored = json.loads(files["v2_p01_proceres-de-honduras_s5_ficha.json"])
    assert (stored["volumen"], stored["puzzle"], stored["titulo"]) == ("vol2", 1, "Próceres de Honduras")
    assert fichamod.regenerate_from_ficha(stored).grid == r.grid
    zf = zipfile.ZipFile(io.BytesIO(salidas.puzzle_zip(files)))
    assert sorted(zf.namelist()) == sorted(files)


def test_titulo_en_el_pdf():
    from pypdf import PdfReader
    r = motor.create_puzzle(["LEMPIRA", "MORAZÁN"], 10, 10, ["H", "V"], "", 0, seed=1)
    data = pdf.generate_pdf(r.grid, r.placed, r.words_display, title="Próceres de Honduras").getvalue()
    p1, p2 = (pg.extract_text() for pg in PdfReader(io.BytesIO(data)).pages)
    assert "Próceres de Honduras" in p1 and "Solución: Próceres de Honduras" in p2
    # Sin título, como antes.
    plain = pdf.generate_pdf(r.grid, r.placed, r.words_display).getvalue()
    q1, q2 = (pg.extract_text() for pg in PdfReader(io.BytesIO(plain)).pages)
    assert "Sopa de Letras" in q1 and "Solución" in q2


def test_titulo_largo_se_achica_y_cabe():
    r = motor.create_puzzle(["LEMPIRA"], 10, 10, ["H"], "", 0, seed=1)
    long = "Un título larguísimo para comprobar que se achica y no se sale de la página carta"
    data = pdf.generate_pdf(r.grid, r.placed, r.words_display, title=long).getvalue()
    from pypdf import PdfReader
    assert long in PdfReader(io.BytesIO(data)).pages[0].extract_text().replace("\n", " ")
