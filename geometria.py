"""Geometría compartida por las salidas PDF y SVG (sin dependencias de Streamlit).

Sistema de coordenadas: origen en la esquina superior izquierda del MARCO de la
cuadrícula, x hacia la derecha, y hacia abajo, en puntos. El PDF invierte el
eje y al dibujar; el SVG lo usa tal cual. Así ambas salidas comparten exactamente
la misma posición de letras y bandas.
"""

import math
from dataclasses import dataclass

from motor import clean_word

# Margen interior entre las letras y el marco, en celdas.
PAD = 0.3
# Tamaño de letra respecto a la celda.
FONT_RATIO = 0.62
# Alto de la banda de solución respecto a la celda (~75 % pedido; se usa 0.70).
# Dos diagonales paralelas vecinas están a 1/√2 ≈ 0.707 celdas de distancia: con
# 0.75 sus bandas se solapaban en una franja finísima que se veía como una línea
# oscura. Con 0.70 no se solapan, y los cruces siguen viéndose más oscuros.
BAND_HEIGHT = 0.70
# Opacidad de la banda (negro con alpha): en los cruces se ve más oscuro.
BAND_ALPHA = 0.25
# Cuánto sobresale la banda de los centros de la primera y la última celda, en celdas.
BAND_OVERHANG = 0.5
# Grosor del marco respecto a la celda.
FRAME_RATIO = 0.04


def frame_size(rows, cols, cell):
    """Ancho y alto del marco de la cuadrícula."""
    return (cols + 2 * PAD) * cell, (rows + 2 * PAD) * cell


def cell_center(r, c, cell):
    """Centro de la celda (r, c) dentro del marco."""
    return (PAD + c + 0.5) * cell, (PAD + r + 0.5) * cell


@dataclass(frozen=True)
class Band:
    word: str
    x1: float  # centro de la primera celda
    y1: float
    x2: float  # centro de la última celda
    y2: float
    cx: float  # punto medio
    cy: float
    length: float  # largo total, incluidos los extremos redondeados
    height: float
    angle: float  # grados, sentido horario con y hacia abajo (como en SVG)

    @property
    def radius(self):
        return self.height / 2


def band_for(word, coords, cell):
    (r1, c1), (r2, c2) = coords[0], coords[-1]
    x1, y1 = cell_center(r1, c1, cell)
    x2, y2 = cell_center(r2, c2, cell)
    dist = math.hypot(x2 - x1, y2 - y1)
    angle = math.degrees(math.atan2(y2 - y1, x2 - x1)) if dist else 0.0
    return Band(
        word=word,
        x1=x1, y1=y1, x2=x2, y2=y2,
        cx=(x1 + x2) / 2, cy=(y1 + y2) / 2,
        length=dist + 2 * BAND_OVERHANG * cell,
        height=BAND_HEIGHT * cell,
        angle=angle,
    )


def bands_for(placed, cell, exclude=()):
    """Una banda por palabra colocada, salvo las de `exclude` (forma escrita o limpia)."""
    excluded = {clean_word(w) for w in exclude}
    return [band_for(w, coords, cell) for w, coords in placed if w not in excluded]


def font_size(cell):
    return FONT_RATIO * cell


def baseline_offset(size, cap_height_1000):
    """Distancia del centro de la celda a la línea base para centrar las mayúsculas."""
    return cap_height_1000 / 1000 * size / 2
