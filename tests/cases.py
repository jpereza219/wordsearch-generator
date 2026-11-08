"""Configuraciones de puzzle usadas por los snapshots y las propiedades.

Cada caso reproduce lo que la interfaz pasaría a generate_puzzle().
"""

from conftest import CUSTOM_DEFAULT_DECOYS, CUSTOM_DEFAULT_DIRS, DEFAULT_SPECIALS_UI

ALL_DIRS = ["H", "HR", "V", "VR", "D1", "D2", "D3", "D4"]

CASES = {
    # 15x15, Custom con valores por defecto, especiales "ÑÁÉÍÓÚÜ".
    "paises_15x15_custom": dict(
        seed=101,
        rows=15,
        cols=15,
        difficulty="Custom",
        allowed_dirs=CUSTOM_DEFAULT_DIRS,
        decoys=CUSTOM_DEFAULT_DECOYS,
        specials_ui="ÑÁÉÍÓÚÜ",
        words=[
            "BELICE", "COLOMBIA", "CUBA", "EL SALVADOR", "GUATEMALA",
            "ISLAS CAIMÁN", "JAMAICA", "MÉXICO", "NICARAGUA",
        ],
    ),
    # 20x20, Custom con las 8 direcciones y 6 señuelos, especiales "ÑÁÉÍÓÚÜ-".
    "departamentos_20x20_custom8": dict(
        seed=202,
        rows=20,
        cols=20,
        difficulty="Custom",
        allowed_dirs=ALL_DIRS,
        decoys=6,
        specials_ui="ÑÁÉÍÓÚÜ-",
        words=[
            "ATLÁNTIDA", "COLÓN", "COMAYAGUA", "COPÁN", "CORTÉS", "CHOLUTECA",
            "EL PARAÍSO", "FRANCISCO MORAZÁN", "GRACIAS A DIOS", "INTIBUCÁ",
            "ISLAS DE LA BAHÍA", "LA PAZ", "LEMPIRA", "OCOTEPEQUE", "OLANCHO",
            "SANTA BÁRBARA", "VALLE", "YORO",
        ],
    ),
    # 15x15, nivel Medium, especiales con el valor por defecto de la UI (incluye ’).
    "montanas_15x15_medium": dict(
        seed=303,
        rows=15,
        cols=15,
        difficulty="Medium",
        allowed_dirs=None,  # se toma de DIFFICULTY_PRESETS
        decoys=None,
        specials_ui=DEFAULT_SPECIALS_UI,
        words=["MERENDÓN", "CELAQUE", "PUCA-OPALACA", "PUCA", "LEPATERIQUE", "DIPILTO"],
    ),
    # 20x20, Custom con las 8 direcciones (6 señuelos por defecto), municipios de Francisco Morazán.
    "municipios_fm_20x20_custom8": dict(
        seed=404,
        rows=20,
        cols=20,
        difficulty="Custom",
        allowed_dirs=ALL_DIRS,
        decoys=CUSTOM_DEFAULT_DECOYS,
        specials_ui="ÑÁÉÍÓÚÜ",
        words=[
            "DISTRITO CENTRAL", "ALUBARÉN", "CEDROS", "CURARÉN", "EL PORVENIR", "GUAIMACA",
            "LA LIBERTAD", "LA VENTA", "LEPATERIQUE", "MARAITA", "MARALE", "NUEVA ARMENIA",
            "OJOJONA", "ORICA", "REITOCA", "SABANAGRANDE", "SAN ANTONIO DE ORIENTE",
            "SAN BUENAVENTURA", "SAN IGNACIO", "SANTA ANA", "SANTA LUCÍA", "TALANGA",
            "TATUMBLA", "VALLE DE ÁNGELES", "VALLECILLO", "VILLA DE SAN FRANCISCO",
        ],
    ),
    # 15x15, Custom con las 8 direcciones y 6 señuelos, con una palabra oculta (Ruta Secreta).
    "ruta_secreta_15x15_custom8": dict(
        seed=505,
        rows=15,
        cols=15,
        difficulty="Custom",
        allowed_dirs=ALL_DIRS,
        decoys=CUSTOM_DEFAULT_DECOYS,
        specials_ui="ÑÁÉÍÓÚÜ",
        words=[
            "BELICE", "COLOMBIA", "CUBA", "EL SALVADOR", "GUATEMALA",
            "ISLAS CAIMÁN", "JAMAICA", "MÉXICO", "NICARAGUA",
        ],
        hidden=["GRACIAS"],
    ),
}


def resolve(motor, case):
    """Devuelve (allowed_dirs, decoys, extra_chars) tal como los calcularía la UI."""
    if case["difficulty"] == "Custom":
        allowed_dirs, decoys = list(case["allowed_dirs"]), case["decoys"]
    else:
        preset_dirs, preset_decoys = motor.DIFFICULTY_PRESETS[case["difficulty"]]
        allowed_dirs, decoys = list(preset_dirs), preset_decoys
    extra_chars = motor.clean_specials_input(case["specials_ui"])
    return allowed_dirs, decoys, extra_chars
