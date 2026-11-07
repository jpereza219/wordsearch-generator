"""generate_pdf produce un PDF válido de 2 páginas: sopa y solución."""

from io import BytesIO

from pypdf import PdfReader

from cases import CASES, resolve


def _pdf_bytes(motor_mod, pdf_mod, seeded, case_name):
    case = CASES[case_name]
    allowed_dirs, decoys, extra_chars = resolve(motor_mod, case)
    grid, placed, words_display = seeded(
        case["seed"], case["words"], case["rows"], case["cols"], allowed_dirs, extra_chars, decoys
    )
    # La interfaz pasa la lista ya en mayúsculas (app.py).
    buffer = pdf_mod.generate_pdf(grid, placed, [w.upper() for w in words_display])
    return buffer.getvalue(), grid, words_display


def test_pdf_valido_con_dos_paginas(motor_mod, pdf_mod, seeded):
    data, _, _ = _pdf_bytes(motor_mod, pdf_mod, seeded, "paises_15x15_custom")
    assert data.startswith(b"%PDF-")
    assert data.rstrip().endswith(b"%%EOF")
    reader = PdfReader(BytesIO(data))
    assert len(reader.pages) == 2


def test_pdf_titulos_y_lista(motor_mod, pdf_mod, seeded):
    data, _, words_display = _pdf_bytes(motor_mod, pdf_mod, seeded, "montanas_15x15_medium")
    reader = PdfReader(BytesIO(data))
    sopa, solucion = (page.extract_text() for page in reader.pages)
    assert "Sopa de Letras" in sopa
    assert "Solución" in solucion
    for word in words_display:
        assert word.upper() in sopa
        assert word.upper() in solucion


def test_pdf_20x20(motor_mod, pdf_mod, seeded):
    data, _, _ = _pdf_bytes(motor_mod, pdf_mod, seeded, "departamentos_20x20_custom8")
    assert len(PdfReader(BytesIO(data)).pages) == 2
