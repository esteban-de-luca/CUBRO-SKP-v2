"""
modulo_a.py — Módulo A: Validación del CSV de SketchUp.
Responsable: Javier.

Lee catalogo.json y opciones_mueble.yaml desde data/ al importarse.
Todas las listas de muebles son data-driven — ninguna constante hardcodeada.
"""

import io
import json
import pathlib
import re
from collections import defaultdict

import pandas as pd
import yaml


# ── Carga de datos ─────────────────────────────────────────────────────────────

_DATA_DIR = pathlib.Path(__file__).parent / "data"


def _cargar_catalogo() -> dict:
    path = _DATA_DIR / "catalogo.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró catalogo.json en {_DATA_DIR}. "
            "Asegúrate de que el archivo está en data/catalogo.json."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _cargar_opciones() -> dict:
    path = _DATA_DIR / "opciones_mueble.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró opciones_mueble.yaml en {_DATA_DIR}. "
            "Asegúrate de que el archivo está en data/opciones_mueble.yaml."
        )
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


_CATALOGO = _cargar_catalogo()
_OPCIONES = _cargar_opciones()


def _cargar_ui_aviso() -> dict[str, dict]:
    """Carga las tablas de traducción SKP→UI desde mapeos_SKP_UI_SG.yaml.

    Se llama dentro de parsear_csv() en cada parseo (no en tiempo de importación)
    para garantizar datos frescos. Si el archivo no existe o falla el parseo,
    devuelve dicts vacíos como fallback silencioso (los avisos mostrarán el valor crudo).

    Devuelve un dict con claves: gama, frente, interior, tirador, trasera.
    """
    def _tabla(tabla: list) -> dict:
        return {str(e["skp"]): str(e["ui"]) for e in (tabla or []) if "skp" in e and "ui" in e}

    try:
        path = _DATA_DIR / "mapeos_SKP_UI_SG.yaml"
        if not path.exists():
            return {}
        with path.open(encoding="utf-8") as f:
            del_csv = (yaml.safe_load(f) or {}).get("del_csv") or {}
        return {
            "gama":     _tabla(del_csv.get("op_100")),           # "1"→"LACA", "2"→"WOOD"…
            "frente":   _tabla(del_csv.get("op_101")),           # "Crema LACA"→"Crema"…
            "interior": _tabla(del_csv.get("op_200")),           # "Blanco mueble"→"Blanco"…
            "tirador":  _tabla(del_csv.get("op_300")),           # "2"→"Round", "7"→"Plantea"…
            "trasera":  _tabla(del_csv.get("op_301_integrado")), # "Oak WOOD"→"Oak"…
        }
    except Exception:
        return {}


# ── Constantes globales (valores fijos, no dependen del mueble) ────────────────

COLUMNAS_VALIDAS = [
    "Name", "Ancho", "LenZ", "Apertura", "D_Gama", "ColorFrente",
    "Color del interior", "Tirador", "Trasera",
    "Color tir. de superficie", "C_Rodapietext", "Ancho reducido",
]

COLUMNAS_OBLIGATORIAS = ["Name", "D_Gama", "ColorFrente", "Tirador", "C_Rodapietext"]

PREFIJOS_INSTALACION = [
    "DESAGUE_", "FONTANERIA_", "ELECT_", "FONTANERÍA_",
    "DESAGÜE", "DESAGÜES", "ENCHUFE", "TOMAS DE AGUA", "FONTANERIA",
    "Enchufe estándar", "PLACA",
]

TIRADORES_VALIDOS    = {2, 3, 4, 5, 7, 20, 21}
TIRADORES_TRASERA    = {2, 3}      # Round, Square → color desde Trasera
TIRADORES_SUPERFICIE = {4, 5, 7}   # Curve, Line, Plantea → color desde Color tir. de superficie
TIRADORES_MECANISMO  = {20, 21}    # Touch Latch, Prise de main → sin color

TRASERA_VALIDAS        = {"LACA", "NORDIC OAK WOOD", "OAK WOOD", "SMOKED OAK WOOD"}
COLOR_INTERIOR_VALIDOS = {"Blanco mueble", "Gris mueble", "Negro mueble", "Roble mueble"}
RODAPIE_VALIDOS        = {"70 mm", "100 mm", "0 mm"}
D_GAMA_LACA            = "1"
GAMA_SUFIJOS = {
    "1": ["LACA"],
    "2": ["WOOD"],
    "3": ["LINOLEO", "LINÓLEO"],
    "4": ["LAMINADO"],
}

LENZ_TOLERANCIA_MM = 5


# ── Derivar conjuntos de muebles desde los archivos de datos ──────────────────

# Todos los códigos válidos del catálogo
CATALOGO_CODIGOS: set[str] = set(_CATALOGO.keys())

# Muebles sin apertura: nulo (2 puertas horizontales) + coulissant (sin puerta batiente)
_p_hinge = _OPCIONES.get("p_hinge") or {}
CODIGOS_SIN_APERTURA: set[str] = set(
    (_p_hinge.get("nulo") or []) + (_p_hinge.get("coulissant") or [])
)

# Muebles que admiten reducción de ancho (op_231)
CODIGOS_CON_OP231: set[str] = set(_OPCIONES.get("op_231") or [])

# Muebles sin color interior (frentes sin mueble: POBIF, PO1BIF, PO2BIF)
CODIGOS_SIN_INTERIOR: set[str] = set(
    ((_OPCIONES.get("op_200") or {}).get("excepciones")) or []
)

# Muebles suspendidos: no llevan rodapié (H, HH, HAV, HR, HLVV, HPT)
CODIGOS_SUSPENSO: set[str] = set(
    ((_OPCIONES.get("op_402") or {}).get("excepciones")) or []
)

# Frentes sin mueble (fondo_mm = null): tampoco llevan rodapié
_codigos_sin_fondo: set[str] = {
    code for code, data in _CATALOGO.items()
    if data.get("fondo_mm") is None
}

# Conjunto unificado: todos los que no necesitan rodapié
CODIGOS_SIN_RODAPIE: set[str] = CODIGOS_SUSPENSO | _codigos_sin_fondo

# Altos estándar por código para validación A21
CATALOG_ALTOS: dict[str, int] = {
    code: data["alto_mm"]
    for code, data in _CATALOGO.items()
    if data.get("alto_mm") is not None
}

# Anchos estándar por código para validación A22
CATALOG_ANCHOS: dict[str, int] = {
    code: data["ancho_mm"]
    for code, data in _CATALOGO.items()
    if data.get("ancho_mm") is not None
}

# Rangos de dimensiones variables (HLVV, HR, HPT) derivados del catálogo
def _build_rangos_variables() -> dict:
    rangos: dict = {}
    for code, data in _CATALOGO.items():
        m = re.match(r'^([A-Z]+)', code)
        if not m:
            continue
        familia = m.group(1)
        av  = data.get("alto_variable")
        axv = data.get("ancho_variable")
        if av or axv:
            if familia not in rangos:
                rangos[familia] = {
                    "ancho_min": None, "ancho_max": None,
                    "alto_min":  None, "alto_max":  None,
                }
            if av:
                rangos[familia]["alto_min"] = av["min"]
                rangos[familia]["alto_max"] = av["max"]
            if axv:
                rangos[familia]["ancho_min"] = axv["min"]
                rangos[familia]["ancho_max"] = axv["max"]
    return rangos

RANGOS_VARIABLES = _build_rangos_variables()


# ── Catálogo de anchos por (familia, alto, fondo) — para corrección op_231 ────

_FAMILY_PREFIXES = [
    'BCUB2T', 'BB2T', 'BE2B', 'B2B',
    'HAV1', 'HAV2', 'HH1', 'H1',
    'AQC31P', 'AQC3', 'AVA1P', 'AFS2B', 'AFSMOBT', 'AFSMO', 'A2I1P', 'A2I',
    'BAV1P',
]


def _parse_catalog_code(code: str):
    """Devuelve (family, ancho_cm, alto_cm, fondo_cm) o None."""
    m = re.match(r'^(HLVV)(\d{2})$', code)
    if m:
        return m.group(1), 0, 0, int(m.group(2))

    m = re.match(r'^(HR|HPT)(\d{2})V(\d{2})$', code)
    if m:
        return m.group(1), int(m.group(2)), 0, int(m.group(3))

    m = re.match(r'^(PO1BIF|PO2BIF|POBIF|FHABS)(\d{2})(\d{2})$', code)
    if m:
        return m.group(1), int(m.group(2)), int(m.group(3)), 0

    for prefix in _FAMILY_PREFIXES:
        if code.startswith(prefix):
            rest = code[len(prefix):]
            m = re.match(r'^(\d{2})(\d{2,3})(\d{2})$', rest)
            if m:
                return prefix, int(m.group(1)), int(m.group(2)), int(m.group(3))

    m = re.match(r'^([A-Z]+)(\d{2})(\d{2,3})(\d{2})$', code)
    if m:
        return m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))

    return None


def _build_catalog_widths() -> dict:
    """Agrupa los anchos disponibles por (familia, alto_cm, fondo_cm)."""
    by_suffix: dict = defaultdict(list)
    for code in CATALOGO_CODIGOS:
        result = _parse_catalog_code(code)
        if result:
            family, ancho, alto, fondo = result
            by_suffix[(family, alto, fondo)].append(ancho)
    return {k: sorted(set(v)) for k, v in by_suffix.items()}


CATALOG_WIDTHS = _build_catalog_widths()


def _build_familias_op231() -> set:
    """Extrae (familia, alto_cm, fondo_cm) de los códigos admitidos en op_231.

    Permite que códigos con ancho no estándar (ej. AVA4722057) también pasen
    la comprobación, ya que en SketchUp el Name lleva el ancho real del modelo.
    """
    familias: set = set()
    for code in CODIGOS_CON_OP231:
        parsed = _parse_catalog_code(code)
        if parsed:
            family, _, alto, fondo = parsed
            familias.add((family, alto, fondo))
    return familias


FAMILIAS_CON_OP231 = _build_familias_op231()


def _corregir_name_reduccion(name_skp: str, ancho_reducido_mm: float):
    """Corrige el Name SKP al ancho estándar más cercano por encima del valor reducido.

    Devuelve (name_corregido, aviso). Si todo va bien, aviso es None.
    """
    suffix_sub = ""
    name_base  = name_skp
    for suf in ("-C1", "-C2", "-C3", "-C4", "-P1", "-P2", "-P3"):
        if name_base.endswith(suf):
            suffix_sub = suf
            name_base  = name_base[: -len(suf)]
            break

    name_clean = name_base.replace(".", "")

    parsed = None
    for prefix in _FAMILY_PREFIXES:
        if name_clean.startswith(prefix):
            rest = name_clean[len(prefix):]
            mp = re.match(r'^(\d+)(\d{3})(\d{2})$', rest)
            if mp:
                parsed = (prefix, int(mp.group(1)), int(mp.group(2)), int(mp.group(3)))
                break
    if not parsed:
        mp = re.match(r'^([A-Z]+)(\d+)(\d{3})(\d{2})$', name_clean)
        if mp:
            parsed = (mp.group(1), int(mp.group(2)), int(mp.group(3)), int(mp.group(4)))

    if not parsed:
        return name_skp, (
            f"No se pudo parsear el Name '{name_skp}' para corregir la reducción de ancho"
        )

    family, _, alto, fondo = parsed
    anchos_std = CATALOG_WIDTHS.get((family, alto, fondo))

    if not anchos_std:
        return name_skp, (
            f"No se encontraron anchos estándar para {family} "
            f"(alto={alto}cm, fondo={fondo}cm)"
        )

    if ancho_reducido_mm < 300:
        return name_skp, (
            f"El ancho reducido ({ancho_reducido_mm:.0f}mm) está por debajo del mínimo de 300mm"
        )

    anchos_mayores = [a for a in anchos_std if a * 10 >= ancho_reducido_mm]
    if not anchos_mayores:
        return name_skp, (
            f"El ancho reducido ({ancho_reducido_mm:.0f}mm) supera el ancho máximo estándar"
        )

    ancho_correcto = min(anchos_mayores)
    alto_str       = f"{alto:03d}" if alto >= 100 else f"{alto:02d}"
    name_corregido = f"{family}{ancho_correcto:02d}{alto_str}{fondo:02d}{suffix_sub}"
    return name_corregido, None


# ── Helpers de normalización ───────────────────────────────────────────────────

def _normalizar_apertura(valor) -> str | None:
    if pd.isna(valor) or str(valor).strip() == "":
        return None
    v = str(valor).strip().upper()
    if v in ("I", "1", "IZQUIERDA"):
        return "izquierda"
    if v in ("D", "2", "DERECHA"):
        return "derecha"
    if v in ("HORIZONTAL", "H", "3"):
        return "horizontal"
    return None


def _normalizar_tirador(valor) -> int | None:
    if pd.isna(valor) or str(valor).strip() == "":
        return None
    try:
        return int(float(str(valor).strip()))
    except (ValueError, TypeError):
        return None


def _str_or_none(valor) -> str | None:
    if pd.isna(valor) or str(valor).strip() == "":
        return None
    return str(valor).strip()


def _es_instalacion(name: str) -> bool:
    name_upper = str(name).strip().upper()
    return any(name_upper.startswith(p.upper()) for p in PREFIJOS_INSTALACION)


def _get_familia(name: str) -> str:
    m = re.match(r'^([A-Z]+)', str(name))
    return m.group(1) if m else ""


# ── Parser principal ───────────────────────────────────────────────────────────

def parsear_csv(archivo) -> dict:
    """
    Parsea el CSV de SketchUp (plantilla CUBRO x SG.grt) y devuelve:
    {
        "ok": bool,
        "error_archivo": str | None,
        "muebles": list[dict],
        "filas_descartadas": []   # siempre vacío — filosofía no-discard
    }

    Cada mueble tiene:
        name, name_skp, estado, apertura, d_gama, color_frente,
        color_interior, tirador, trasera, color_tirador,
        rodapie, ancho, ancho_reducido, len_z, avisos
    """
    resultado = {
        "ok": False,
        "error_archivo": None,
        "muebles": [],
        "filas_descartadas": [],
    }

    # Traducciones SKP→UI para mensajes de aviso (cargadas aquí, no en importación,
    # para garantizar datos frescos en cada parseo).
    _ui = _cargar_ui_aviso()
    _ui_gama     = _ui.get("gama")     or {}
    _ui_frente   = _ui.get("frente")   or {}
    _ui_interior = _ui.get("interior") or {}
    _ui_tirador  = _ui.get("tirador")  or {}
    _ui_trasera  = _ui.get("trasera")  or {}

    # 1. Leer CSV
    try:
        if hasattr(archivo, "read"):
            contenido = archivo.read()
            if isinstance(contenido, bytes):
                contenido = contenido.decode("utf-8-sig")
            df = pd.read_csv(io.StringIO(contenido), dtype=str)
        else:
            df = pd.read_csv(archivo, dtype=str)
    except Exception as e:
        resultado["error_archivo"] = f"No se pudo leer el archivo: {e}"
        return resultado

    # 2. Limpiar columnas y descartar las no válidas (I03)
    df.columns = [str(c).strip() for c in df.columns]
    df = df[[c for c in COLUMNAS_VALIDAS if c in df.columns]]

    # 3. Columnas obligatorias (E01 — bloqueante)
    faltantes = [c for c in COLUMNAS_OBLIGATORIAS if c not in df.columns]
    if faltantes:
        resultado["error_archivo"] = (
            f"Columnas obligatorias ausentes en el archivo: {', '.join(faltantes)}"
        )
        return resultado

    resultado["ok"] = True

    # 4. Procesar fila a fila
    for _, fila in df.iterrows():
        avisos: list[str] = []

        # I01 — Name vacío → descarte silencioso
        name_raw = _str_or_none(fila.get("Name", ""))
        if name_raw is None:
            continue

        # I02 — Instalación → descarte silencioso
        if _es_instalacion(name_raw):
            continue

        # I05 — Ancho vacío → descarte silencioso (subcomponentes -C1, -P1, etc.)
        ancho_check = _str_or_none(fila.get("Ancho", ""))
        if ancho_check is None:
            continue

        ancho_raw          = ancho_check
        ancho_reducido_raw = _str_or_none(fila.get("Ancho reducido", ""))
        name_skp           = name_raw  # preservar Name original de SketchUp

        # ── Op. 231 — Reducción de ancho ──────────────────────────────────────
        if ancho_raw == "10000 mm":
            # Comprobación por familia+alto+fondo para aceptar anchos no estándar
            _parsed_skp = _parse_catalog_code(name_skp)
            _admite_op231 = (
                name_skp in CODIGOS_CON_OP231
                or (
                    _parsed_skp is not None
                    and (_parsed_skp[0], _parsed_skp[2], _parsed_skp[3]) in FAMILIAS_CON_OP231
                )
            )
            if not _admite_op231:
                # A16a
                avisos.append("Este mueble no admite reducción de ancho")
            elif ancho_reducido_raw is None:
                # A16b
                avisos.append("El mueble tiene reducción de ancho pero falta el valor reducido")
            else:
                try:
                    ancho_reducido_mm = float(ancho_reducido_raw.replace(" mm", "").strip())
                    name_corregido, aviso_231 = _corregir_name_reduccion(name_raw, ancho_reducido_mm)
                    if aviso_231:
                        avisos.append(aviso_231)   # A17 u otros errores de corrección
                    else:
                        # A18 — informativo, no bloquea estado CORRECTO
                        avisos.append(
                            f"Nombre corregido por reducción de ancho: "
                            f"'{name_skp}' → '{name_corregido}' ({ancho_reducido_mm:.0f}mm)"
                        )
                        name_raw = name_corregido
                except ValueError:
                    avisos.append(f"No se pudo leer 'Ancho reducido': '{ancho_reducido_raw}'")

        # A10 — Name no encontrado en catálogo
        if name_raw not in CATALOGO_CODIGOS:
            avisos.append(f"'{name_raw}' no existe en el catálogo — revisar el código")

        # A21 — LenZ vs alto del catálogo
        len_z_raw = _str_or_none(fila.get("LenZ", ""))
        if len_z_raw is not None:
            try:
                len_z_mm = float(len_z_raw.replace(" mm", "").replace(",", ".").strip())
                familia  = _get_familia(name_raw)
                if familia in RANGOS_VARIABLES:
                    rango = RANGOS_VARIABLES[familia]
                    if rango["alto_min"] is not None and rango["alto_max"] is not None:
                        if not (rango["alto_min"] <= len_z_mm <= rango["alto_max"]):
                            avisos.append(
                                f"Alto fuera de rango: el mueble mide {len_z_mm:.0f}mm, "
                                f"el rango válido es {rango['alto_min']}–{rango['alto_max']}mm"
                            )
                elif name_raw in CATALOG_ALTOS:
                    alto_cat = CATALOG_ALTOS[name_raw]
                    if abs(len_z_mm - alto_cat) > LENZ_TOLERANCIA_MM:
                        avisos.append(
                            f"Alto incorrecto: el mueble mide {len_z_mm:.0f}mm, "
                            f"el catálogo indica {alto_cat}mm"
                        )
            except ValueError:
                pass

        # A22 — Ancho vs catálogo
        if ancho_raw is not None and ancho_raw != "10000 mm":
            try:
                ancho_mm       = float(ancho_raw.replace(" mm", "").replace(",", ".").strip())
                familia_ancho  = _get_familia(name_raw)
                rango          = RANGOS_VARIABLES.get(familia_ancho, {})
                if rango.get("ancho_min") is not None and rango.get("ancho_max") is not None:
                    if not (rango["ancho_min"] <= ancho_mm <= rango["ancho_max"]):
                        avisos.append(
                            f"Ancho fuera de rango: el mueble mide {ancho_mm:.0f}mm, "
                            f"el rango válido es {rango['ancho_min']}–{rango['ancho_max']}mm"
                        )
                elif name_raw in CATALOG_ANCHOS:
                    ancho_std = CATALOG_ANCHOS[name_raw]
                    if abs(ancho_mm - ancho_std) > 5:
                        avisos.append(
                            f"Ancho incorrecto: el mueble mide {ancho_mm:.0f}mm, "
                            f"el catálogo indica {ancho_std}mm"
                        )
            except ValueError:
                pass

        # A12/A14 — Tirador
        tirador = _normalizar_tirador(fila.get("Tirador", ""))
        if tirador is None:
            avisos.append("Falta el tipo de tirador")
        elif tirador not in TIRADORES_VALIDOS:
            avisos.append(f"Tipo de tirador '{_ui_tirador.get(str(tirador), str(tirador))}' no reconocido")

        # A11 — D_Gama vacío
        d_gama = _str_or_none(fila.get("D_Gama", ""))
        if d_gama is None:
            avisos.append("Falta la gama del frente")

        # A05/A13 — Color del interior (no aplica a frentes sin mueble)
        color_interior = _str_or_none(fila.get("Color del interior", ""))
        if name_raw not in CODIGOS_SIN_INTERIOR:
            if color_interior is None:
                avisos.append("Falta el color del interior")
            elif color_interior not in COLOR_INTERIOR_VALIDOS:
                avisos.append(f"Color del interior '{_ui_interior.get(color_interior, color_interior)}' no reconocido")

        # A07 — D_Gama incompatible con ColorFrente
        color_frente_val = _str_or_none(fila.get("ColorFrente", ""))
        if d_gama is not None and color_frente_val is not None:
            sufijos = GAMA_SUFIJOS.get(d_gama, [])
            if sufijos and not any(s in color_frente_val.upper() for s in sufijos):
                avisos.append(
                    f"La gama ({_ui_gama.get(d_gama, d_gama)}) no coincide con el color de frente "
                    f"'{_ui_frente.get(color_frente_val, color_frente_val)}'"
                )

        # A23 — Apertura
        apertura = _normalizar_apertura(fila.get("Apertura", ""))

        if name_raw in CODIGOS_SIN_APERTURA:
            if apertura is not None:
                avisos.append("Este mueble no requiere apertura — el valor se ignorará")
            apertura = None
        elif name_raw in CATALOGO_CODIGOS:
            if apertura is None:
                avisos.append(
                    "Este mueble requiere apertura (izquierda o derecha) "
                    "pero no tiene ninguna asignada"
                )

        # ── Lógica tirador / color ─────────────────────────────────────────────
        trasera_raw   = _str_or_none(fila.get("Trasera", ""))
        color_tir_raw = _str_or_none(fila.get("Color tir. de superficie", ""))
        color_tirador = None
        trasera       = None

        if tirador in TIRADORES_TRASERA:
            trasera = trasera_raw
            if trasera is None:
                avisos.append("Falta el color de la trasera")
            elif trasera.upper() not in TRASERA_VALIDAS:
                avisos.append(f"Color de trasera '{_ui_trasera.get(trasera, trasera)}' no reconocido")

        elif tirador in TIRADORES_SUPERFICIE:
            color_tirador = color_tir_raw
            if color_tirador is None:
                avisos.append("Falta el color del tirador de superficie")

        # A09 — Frente no-LACA con Trasera Laca
        if (tirador in TIRADORES_TRASERA
                and trasera is not None
                and d_gama is not None
                and d_gama != D_GAMA_LACA
                and trasera.upper() == "LACA"):
            avisos.append("La trasera Laca no es compatible con un frente que no es LACA")

        # ── Lógica rodapié ─────────────────────────────────────────────────────
        rodapie_raw = _str_or_none(fila.get("C_Rodapietext", ""))

        if name_raw in CODIGOS_SIN_RODAPIE:
            if rodapie_raw is not None and name_raw in CODIGOS_SUSPENSO:
                # Solo avisamos para suspendidos explícitos, no para frentes sin mueble
                avisos.append(f"Mueble suspenso — el rodapié '{rodapie_raw}' se ignorará")
            rodapie = None
        else:
            rodapie = rodapie_raw
            if rodapie is None:
                avisos.append("Falta el valor de rodapié")
            elif rodapie not in RODAPIE_VALIDOS:
                avisos.append(
                    f"Valor de rodapié '{rodapie}' no reconocido — "
                    "los valores válidos son 70 mm, 100 mm y 0 mm"
                )

        # Estado: CORRECTO si no hay avisos bloqueantes.
        # Avisos informativos (no bloquean): A18 (reducción de ancho) y A23-info
        # (apertura ignorada en muebles sin puerta batiente).
        _AVISOS_INFORMATIVOS = (
            "Nombre corregido por reducción",   # A18
            "Este mueble no requiere apertura", # A23-info
        )
        avisos_revisables = [
            a for a in avisos
            if not any(a.startswith(p) for p in _AVISOS_INFORMATIVOS)
        ]
        estado = "✅ CORRECTO" if not avisos_revisables else "⚠️ REVISAR"

        resultado["muebles"].append({
            "name":           name_raw,
            "name_skp":       name_skp,
            "estado":         estado,
            "apertura":       apertura,
            "d_gama":         d_gama,
            "color_frente":   color_frente_val,
            "color_interior": color_interior,
            "tirador":        tirador,
            "trasera":        trasera,
            "color_tirador":  color_tirador,
            "rodapie":        rodapie,
            "ancho":          ancho_raw,
            "ancho_reducido": ancho_reducido_raw,
            "len_z":          len_z_raw,
            "avisos":         avisos,
        })

    return resultado


# ── Integración con Módulo B ───────────────────────────────────────────────────

def _a_formato_b(m: dict) -> dict:
    """Convierte el dict interno del Módulo A al formato de claves que espera el Módulo B.

    Módulo A usa claves snake_case internas (name, d_gama, tirador como int...).
    Módulo B espera las claves originales del CSV (Name, D_Gama, Tirador como str...).
    """
    tirador = m.get("tirador")
    return {
        "Name":                     m.get("name") or "",
        "Name SKP":                 m.get("name_skp") or "",
        "Estado":                   m.get("estado") or "",
        "Apertura":                 m.get("apertura") or "",
        "D_Gama":                   m.get("d_gama") or "",
        "ColorFrente":              m.get("color_frente") or "",
        "Color del interior":       m.get("color_interior") or "",
        "Tirador":                  str(tirador) if tirador is not None else "",
        "Trasera":                  m.get("trasera") or "",
        "Color tir. de superficie": m.get("color_tirador") or "",
        "C_Rodapietext":            m.get("rodapie") or "",
        "Ancho":                    m.get("ancho") or "",
        "Ancho reducido":           m.get("ancho_reducido") or "",
        "LenZ":                     m.get("len_z") or "",
        "Avisos":                   " | ".join(m.get("avisos") or []),
    }


def parsear_csv_para_modulo_b(archivo) -> dict:
    """Como parsear_csv() pero los muebles usan las claves que espera el Módulo B.

    Devuelve el mismo shape que parsear_csv():
    {
        "ok": bool,
        "error_archivo": str | None,
        "muebles": list[dict],   ← claves en formato Módulo B
        "filas_descartadas": []
    }

    El app.py integrado llama a esta función en lugar de parsear_csv().
    La app standalone de Javier sigue usando parsear_csv() sin cambios.
    """
    resultado = parsear_csv(archivo)
    if resultado["ok"]:
        resultado["muebles"] = [_a_formato_b(m) for m in resultado["muebles"]]
    return resultado
