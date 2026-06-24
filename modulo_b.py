"""
modulo_b.py — Módulo B: Interfaz y selección.
Responsable: Esteban.

Interviene en dos momentos del flujo:
- Paso 1 (antes de C): recoge opciones opcionales por mueble.
- Paso 2 (después de C): revisión final y export a DealHub.

Pantalla 0 (Validación) bloquea el avance si el CSV trae errores duros.
"""

import base64
import json
import pathlib
import re

import streamlit as st
import yaml


PANTALLA_VALIDACION = "validacion"
PANTALLA_PASO_1 = "paso_1"
PANTALLA_PASO_2 = "paso_2"

# Feature flag (CLAUDE.md §7). True para incluir el detalle técnico bajo un
# expander en cada card-resumen del Paso 2; False para ocultarlo.
MOSTRAR_DETALLE_TECNICO = True


# Diccionario CSV → UI (CLAUDE.md §8). El Módulo B nunca expone códigos
# técnicos al usuario final.
_GAMA_UI = {"1": "LACA", "2": "WOOD", "3": "LINOLEO", "4": "LAMINADO"}
_TIRADOR_UI = {
    "0": "Sin tirador",
    "2": "Round",
    "3": "Square",
    "4": "Curve",
    "5": "Line",
    "7": "Plantea",
    "20": "Touch Latch",
    "21": "Prise de main",
}
# Placeholders de tooltips de los controles opcionales del Paso 1.
# Pendientes de redactar con la app delante (CLAUDE.md §11, hito 6).
_TOOLTIPS_OPCIONALES = {
    "op_121":                "El frente se fabrica sin taladro para tirador. Solo disponible con Curve, Line y Plantea. Se activa automáticamente con Plantea, y con Curve/Line en muebles monopuerta.",
    "op_207_opcional":       "Añade cubos de basura integrados bajo el fregadero. Disponible en muebles BE2B y BEBTS.",
    "op_207_almacenamiento": "Elige cómo se organiza el interior de la despensa: estándar (baldas) o botellero.",
    "op_220":                "Mecaniza la base del mueble para alojar un perfil LED. Al activarlo aparece la opción de sensor.",
    "op_222":                "Añade un sensor para activar el perfil LED con mando a distancia. No es obligatorio aunque el mueble lleve LED. Elige el lado más accesible según el diseño.",
    "op_223":                "Añade un cajón interior dentro del mueble.",
    "op_227":                "El mueble se vacía de baldas para alojar una caldera.",
    "op_700_opcional":       "El mueble se entrega sin pegar. Las campanas HH siempre lo llevan para facilitar el ajuste en obra.",
    "op_126":                "Datos del electrodoméstico encastrado. Si conoces la referencia del modelo, indica marca y referencia; si no, indica solo la altura del hueco en mm.",
}

_TIRADORES_SIN_COLOR = {"Touch Latch", "Prise de main", "Sin tirador"}
_GAMA_SUFIJOS = (" LACA", " WOOD", " LINOLEO", " LAMINADO")
_APERTURA_UI = {
    "1": "Izquierda",
    "i": "Izquierda",
    "izquierda": "Izquierda",
    "2": "Derecha",
    "d": "Derecha",
    "derecha": "Derecha",
    "3": "Lift",
    "horizontal": "Lift",
}
_ANCHO_REDUCCION_RAW = "10000 mm"
_RODAPIE_SIN_PATAS_RAW = "0 mm"
# Tapeta variable: FF12V acepta altos entre estos límites (ver catálogo alto_variable)
_FF12V_ALTO_MIN = 600
_FF12V_ALTO_MAX = 2450
_CATALOGO_PATH = pathlib.Path(__file__).parent / "data" / "catalogo.json"
_MAPEOS_SKP_UI_SG_PATH = pathlib.Path(__file__).parent / "data" / "mapeos_SKP_UI_SG.yaml"
_OPCIONES_MUEBLE_PATH = pathlib.Path(__file__).parent / "data" / "opciones_mueble.yaml"
_REGLAS_PATH = pathlib.Path(__file__).parent / "data" / "reglas.yaml"
_IMAGENES_PATH = pathlib.Path(__file__).parent / "data" / "imagenes_mueble.yaml"
_ASSETS_MUEBLES = pathlib.Path(__file__).parent / "assets" / "muebles"
_COLORES_PATH = pathlib.Path(__file__).parent / "data" / "colores_mueble.yaml"
_ASSETS_COLORES = pathlib.Path(__file__).parent / "assets" / "colores"
_ASSETS_OPCIONES = pathlib.Path(__file__).parent / "assets" / "opciones"

# Conjuntos de muebles abiertos (EOV/EOAVV) — carga al importar módulo
def _cargar_opciones_mueble_raw() -> dict:
    if not _OPCIONES_MUEBLE_PATH.exists():
        return {}
    with _OPCIONES_MUEBLE_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

_OPCIONES_RAW = _cargar_opciones_mueble_raw()

CODIGOS_MUEBLE_ABIERTO: set[str] = set(
    ((_OPCIONES_RAW.get("op_410") or {}).get("codigos")) or []
)
CODIGOS_PS_SEGUN_RODAPIE: set[str] = set(
    ((_OPCIONES_RAW.get("op_402") or {}).get("p_s_segun_rodapie")) or []
)

_av_d_raw = (_OPCIONES_RAW.get("avisos_desmontado") or {})
CODIGOS_DESMONTADO: set[str]        = set(_av_d_raw.get("codigos")  or [])
PREFIJOS_DESMONTADO: tuple[str, ...] = tuple(_av_d_raw.get("prefijos") or [])

# Tapetas (FF*/FFAL*): sin apertura, tirador, color interior ni rodapié.
# op_101 viene de la columna "Acabado" del CSV.
CODIGOS_TAPETA: set[str] = set(
    ((_OPCIONES_RAW.get("tapetas") or {}).get("codigos")) or []
)

# Rodapiés (SOC*): sin apertura, tirador, color interior ni patas.
# op_401 viene de la columna "Acabado" del CSV (mismo índice que op_101).
_RODAPIES_CFG = _OPCIONES_RAW.get("rodapiés") or {}
CODIGOS_RODAPIE: set[str] = set(_RODAPIES_CFG.get("codigos") or [])
CODIGOS_RODAPIE_SKP: set[str] = set(_RODAPIES_CFG.get("codigos_skp") or [])
CODIGOS_RODAPIE_SG: set[str] = set(_RODAPIES_CFG.get("codigos_sg") or [])
# Mapeo: código SKP → [código SG 3600mm, código SG 1800mm]
_RESOLUCION_RODAPIE: dict[str, list[str]] = _RODAPIES_CFG.get("resolucion") or {}

# Joues (J19*): solo op_621 (coloris panneaux) desde columna "Acabado" del CSV.
# Sin apertura, tirador, color interior, rodapié ni opcionales de usuario.
_JOUES_CFG = _OPCIONES_RAW.get("joues") or {}
CODIGOS_JOUE: set[str] = set(_JOUES_CFG.get("codigos") or [])
CODIGOS_ENCIMERA: set[str] = set((_OPCIONES_RAW.get("encimeras") or {}).get("codigos") or [])


def _es_desmontado(code: str) -> bool:
    """True si el mueble siempre se envía desmontado al cliente (aviso informativo)."""
    return code in CODIGOS_DESMONTADO or bool(
        PREFIJOS_DESMONTADO and code.startswith(PREFIJOS_DESMONTADO)
    )


@st.cache_data
def _cargar_sg_a_ui() -> dict[str, str]:
    """Diccionario inverso {código_SG → etiqueta_UI} para traducir valores en opciones_adicionales.

    Construido leyendo mapeos_SKP_UI_SG.yaml: secciones 'forzadas' y 'opcionales'.
    Si modulo_c pone un código SG en el campo 'valor' de una entrada de
    opciones_adicionales, este dict permite sustituirlo por la etiqueta legible.
    """
    if not _MAPEOS_SKP_UI_SG_PATH.exists():
        return {}
    with _MAPEOS_SKP_UI_SG_PATH.open(encoding="utf-8") as f:
        mapeos = yaml.safe_load(f) or {}

    sg_a_ui: dict[str, str] = {}

    # Sección forzadas: cada entrada tiene {sg: CODE, ui: "Etiqueta"}
    for _op_data in (mapeos.get("forzadas") or {}).values():
        if isinstance(_op_data, dict) and _op_data.get("sg") and _op_data.get("ui"):
            sg_a_ui[_op_data["sg"]] = _op_data["ui"]

    # Sección opcionales: listas de {sg: CODE, ui: "Etiqueta"}
    for _op_data in (mapeos.get("opcionales") or {}).values():
        if isinstance(_op_data, list):
            for entry in _op_data:
                if entry.get("sg") and entry.get("ui"):
                    sg_a_ui[entry["sg"]] = entry["ui"]
        elif isinstance(_op_data, dict):
            for entry in (_op_data.get("valores") or []):
                if entry.get("sg") and entry.get("ui"):
                    sg_a_ui[entry["sg"]] = entry["ui"]

    return sg_a_ui


@st.cache_data
def _cargar_catalogo() -> dict:
    """Carga data/catalogo.json. Si todavía no se ha subido, devuelve {}."""
    if not _CATALOGO_PATH.exists():
        return {}
    return json.loads(_CATALOGO_PATH.read_text(encoding="utf-8"))


@st.cache_data
def _cargar_imagenes() -> list[tuple[str, str]]:
    """Carga imagenes_mueble.yaml y devuelve lista de (prefijo, filename) ordenada
    de mayor a menor longitud (longest-prefix-first matching)."""
    if not _IMAGENES_PATH.exists():
        return []
    with _IMAGENES_PATH.open(encoding="utf-8") as f:
        datos = yaml.safe_load(f) or {}
    prefijos = datos.get("prefijos") or {}
    return sorted(prefijos.items(), key=lambda x: len(x[0]), reverse=True)


_FF12_POSICION_H = {"FF1260", "FF1280", "FF12100"}

def _imagen_mueble(code: str, posicion: str = "") -> pathlib.Path | None:
    """Devuelve la Path al PNG del mueble si existe, o None.

    Usa longest-prefix-first: el primer prefijo (de mayor a menor longitud)
    que coincida con el inicio del código de mueble determina la imagen.
    FF1260/FF1280/FF12100 con posición H usan la imagen de FF1260 (versión de pared).
    """
    if not code:
        return None
    if code in _FF12_POSICION_H and posicion.upper() == "H":
        ruta = _ASSETS_MUEBLES / "FF1260.png"
        if ruta.exists():
            return ruta
    for prefijo, filename in _cargar_imagenes():
        if code.startswith(prefijo):
            ruta = _ASSETS_MUEBLES / filename
            if ruta.exists():
                return ruta
    return None


def _imagen_opcion(op_id: str, codigo_sg: str) -> pathlib.Path | None:
    """Devuelve la Path al PNG de una opción concreta si existe, o None.

    Convención de nombre: assets/opciones/{op_id}_{codigo_sg}.png
    Ejemplo: assets/opciones/op_207_GM1.png
    """
    ruta = _ASSETS_OPCIONES / f"{op_id}_{codigo_sg}.png"
    return ruta if ruta.exists() else None


@st.cache_data
def _cargar_colores() -> dict:
    """Carga colores_mueble.yaml. Devuelve {'frente': {...}, 'interior': {...}}."""
    if not _COLORES_PATH.exists():
        return {}
    with _COLORES_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _render_swatches_color(
    color_frente: str, color_interior: str, etiqueta_frente: str = "Frente"
) -> None:
    """Muestra swatches de color apilados verticalmente (frente primero, interior debajo).

    Cada fila: imagen cuadrada 36 px a la izquierda + etiqueta a la derecha,
    renderizado con HTML inline para evitar problemas de columnas anidadas en Streamlit.
    Se omiten los colores sin imagen disponible.
    etiqueta_frente: label visible junto al swatch (por defecto "Frente"; usar "Acabado"
    para tapetas).
    """
    colores = _cargar_colores()
    items: list[tuple[str, pathlib.Path]] = []

    fn_frente = (colores.get("frente") or {}).get(color_frente)
    if fn_frente:
        p = _ASSETS_COLORES / fn_frente
        if p.exists():
            items.append((f"{etiqueta_frente}: {color_frente}", p))

    fn_interior = (colores.get("interior") or {}).get(color_interior)
    if fn_interior:
        p = _ASSETS_COLORES / fn_interior
        if p.exists():
            items.append((f"Interior: {color_interior}", p))

    for etiqueta, path in items:
        b64 = base64.b64encode(path.read_bytes()).decode()
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0">'
            f'<img src="data:image/png;base64,{b64}"'
            f' style="width:36px;height:36px;border-radius:3px;flex-shrink:0"/>'
            f'<span style="font-size:0.82em">{etiqueta}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


@st.cache_data
def _cargar_interfaz(_v: int = 3) -> dict:
    """Construye el dict de interfaz desde mapeos_SKP_UI_SG.yaml, opciones_mueble.yaml y reglas.yaml.

    La fuente de verdad son los tres YAMLs anteriores. Ningún control ni lógica
    de UI cambia — solo la fuente de los datos.
    Cada key es un op_id con etiqueta, muebles/excluidos y subcampos según corresponda.
    El parámetro _v fuerza la invalidación del caché al cambiar su valor.
    """
    if not _MAPEOS_SKP_UI_SG_PATH.exists() or not _OPCIONES_MUEBLE_PATH.exists():
        return {}
    with _MAPEOS_SKP_UI_SG_PATH.open(encoding="utf-8") as f:
        mapeos = yaml.safe_load(f) or {}
    with _OPCIONES_MUEBLE_PATH.open(encoding="utf-8") as f:
        op_mueble = yaml.safe_load(f) or {}
    reglas: dict = {}
    if _REGLAS_PATH.exists():
        with _REGLAS_PATH.open(encoding="utf-8") as f:
            reglas = yaml.safe_load(f) or {}
    reglas_b = (reglas.get("modulo_b") or {})

    opc = mapeos.get("opcionales") or {}
    interfaz: dict = {}

    # op_121 — etiqueta + condiciones de visibilidad y forzado desde reglas.yaml
    if "op_121" in opc:
        entradas   = opc["op_121"]
        r121_b     = reglas_b.get("op_121") or {}
        mono_121   = r121_b.get("forzado_en_monoporte") or {}
        interfaz["op_121"] = {
            "etiqueta": entradas[0].get("ui", "Sin mecanizado para tirador"),
            # Tiradores con los que el control se muestra (Curve=4, Line=5, Plantea=7)
            "visible_con_tiradores": [str(t) for t in (r121_b.get("visible_con_tiradores") or [])],
            # Tirador que fuerza SPF en cualquier mueble (Plantea=7)
            "forzado_siempre": [str(t) for t in (r121_b.get("forzado_siempre") or [])],
            # Tiradores + muebles donde SPF se fuerza por ser monopuerta alto
            "forzado_en_monoporte": {
                "tiradores": [str(t) for t in (mono_121.get("tiradores") or [])],
                "muebles":   mono_121.get("muebles") or [],
            },
        }

    # op_207_opcional — checkbox (P60/P90) para fregadero · radio (GM1/GM2) para despensa
    if "op_207_opcional" in opc:
        bloque_207 = opc["op_207_opcional"] or {}
        entradas_207 = bloque_207.get("valores") or []
        op207 = op_mueble.get("op_207") or {}
        reglas_207 = reglas_b.get("op_207") or {}

        # muebles_checkbox: {mueble: codigo_sg} para P60/P90
        muebles_checkbox: dict = {}
        for codigo_sg, lista in op207.items():
            if codigo_sg in ("P60", "P90") and isinstance(lista, list):
                for mueble in lista:
                    muebles_checkbox[mueble] = codigo_sg

        # muebles_seleccion: {mueble: [codigo_sg, ...]} para GM1/GM2
        muebles_seleccion: dict = {}
        for codigo_sg, lista in op207.items():
            if codigo_sg in ("GM1", "GM2") and isinstance(lista, list):
                for mueble in lista:
                    muebles_seleccion.setdefault(mueble, [])
                    if codigo_sg not in muebles_seleccion[mueble]:
                        muebles_seleccion[mueble].append(codigo_sg)

        etiqueta_por_sg: dict = {
            e.get("sg", ""): e.get("ui", "")
            for e in entradas_207
            if e.get("sg")
        }
        etiquetas_ui = bloque_207.get("etiquetas") or {}

        interfaz["op_207_opcional"] = {
            "etiqueta_fregadero": etiquetas_ui.get("fregadero", "Cubos de basura"),
            "etiqueta_despensa":  etiquetas_ui.get("despensa", "Tipo de almacenamiento"),
            "muebles_checkbox":   muebles_checkbox,
            "muebles_seleccion":  muebles_seleccion,
            "etiqueta_por_sg":    etiqueta_por_sg,
            "obligatoria_en":     reglas_207.get("obligatoria_en") or [],
        }

    # op_220, op_223, op_227 — etiqueta + lista plana de muebles
    for op_id in ("op_220", "op_223", "op_227"):
        if op_id in opc:
            entradas = opc[op_id]
            interfaz[op_id] = {
                "etiqueta": entradas[0].get("ui", op_id),
                "muebles": op_mueble.get(op_id) or [],
            }

    # op_222 — dos etiquetas (derecha / izquierda) + lista plana de muebles
    if "op_222" in opc:
        entradas = opc["op_222"]
        interfaz["op_222"] = {
            "etiqueta_derecha":   entradas[0].get("ui", "Sensor derecha")   if len(entradas) > 0 else "Sensor derecha",
            "etiqueta_izquierda": entradas[1].get("ui", "Sensor izquierda") if len(entradas) > 1 else "Sensor izquierda",
            "muebles": op_mueble.get("op_222") or [],
        }

    # op_700_opcional — etiqueta + excluidos (no_aplica) + forzadas (DEM automático)
    if "op_700_opcional" in opc:
        entradas = opc["op_700_opcional"]
        op700 = op_mueble.get("op_700") or {}
        interfaz["op_700_opcional"] = {
            "etiqueta":  entradas[0].get("ui", "Mueble sin encolar"),
            # Excluidos: muebles donde op_700 no aplica en absoluto (no se muestra).
            "excluidos": op700.get("no_aplica") or [],
            # Forzadas: muebles donde DEM es automático — se muestra desactivado y marcado.
            "forzadas":  op700.get("forzadas") or [],
        }

    # op_126 — variante por mueble (horno, placa, frigorífico, LVV/LVD, campana…)
    # Fuente de verdad única: opciones_mueble.yaml / variantes_op_126.
    # Cada entrada tiene ui, subcampos, tipo_auto/tipo_opciones (meta UI) y muebles (lista).
    # Fallback a "variantes_p_built_in_detail" por compatibilidad con versiones anteriores del YAML.
    variantes_op_126 = (
        op_mueble.get("variantes_op_126")
        or op_mueble.get("variantes_p_built_in_detail")
        or {}
    )
    if variantes_op_126:
        mueble_a_variante: dict = {}
        variantes_meta: dict = {}

        for variante_key, variante_data in variantes_op_126.items():
            variantes_meta[variante_key] = {
                "etiqueta":      variante_data.get("ui", "Electrodoméstico"),
                "subcampos":     variante_data.get("subcampos") or {},
                "tipo_auto":     variante_data.get("tipo_auto"),
                "tipo_opciones": variante_data.get("tipo_opciones"),
                "doble":         bool(variante_data.get("doble")),
                "solo_caso_a":   bool(variante_data.get("solo_caso_a", False)),
            }
            for mueble in (variante_data.get("muebles") or []):
                mueble_a_variante[mueble] = variante_key

        interfaz["op_126"] = {
            "mueble_a_variante": mueble_a_variante,
            "variantes_meta":    variantes_meta,
            "muebles":           list(mueble_a_variante.keys()),
        }

    return interfaz



def _ui_gama(d_gama: str) -> str:
    return _GAMA_UI.get((d_gama or "").strip(), "")


def _ui_color_frente(raw: str) -> str:
    """Quita el sufijo de gama del color (p. ej. 'Crema LACA' → 'Crema')."""
    raw = (raw or "").strip()
    for sufijo in _GAMA_SUFIJOS:
        if raw.endswith(sufijo):
            return raw[: -len(sufijo)].strip()
    return raw


def _gama_desde_acabado(raw: str) -> str:
    """Extrae la gama del valor completo de Acabado (p. ej. 'Crema LACA' → 'LACA')."""
    raw = (raw or "").strip()
    for sufijo in _GAMA_SUFIJOS:
        if raw.endswith(sufijo):
            return sufijo.strip()
    return ""


def _ui_color_mueble_abierto(raw: str) -> str:
    """Traduce el valor SKP del color de mueble abierto a etiqueta UI.

    Usa la misma lógica que _ui_color_frente: elimina el sufijo de gama.
    'Oak WOOD' → 'Oak', 'Crema LACA' → 'Crema'.
    """
    return _ui_color_frente(raw)


def _ui_tirador(tirador_code: str) -> str:
    return _TIRADOR_UI.get((tirador_code or "").strip(), "")


def _ui_color_tirador(mueble: dict, tirador_ui: str) -> str:
    """Color visible del tirador (CLAUDE.md §8 con caso especial Trasera=Laca)."""
    if tirador_ui in _TIRADORES_SIN_COLOR:
        return ""
    superficie = (mueble.get("Color tir. de superficie") or "").strip()
    if superficie:
        return superficie
    trasera = (mueble.get("Trasera") or "").strip()
    if not trasera:
        return ""
    if trasera == "Laca":
        return _ui_color_frente(mueble.get("ColorFrente", ""))
    return _ui_color_frente(trasera)


def _ui_apertura(value: str) -> str:
    raw = (value or "").strip()
    return _APERTURA_UI.get(raw.lower(), raw or "—")


def _ui_ancho(mueble: dict) -> str:
    """`10000 mm` indica reducción de ancho; el valor real va en `Ancho reducido`."""
    raw = (mueble.get("Ancho") or "").strip()
    if raw == _ANCHO_REDUCCION_RAW:
        reducido = (mueble.get("Ancho reducido") or "").strip()
        return f"Reducción de ancho ({reducido})" if reducido else "Reducción de ancho"
    return raw or "—"


def _ui_color_interior(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return "—"
    return raw.replace(" mueble", "").strip() or raw


def _ui_rodapie(value: str) -> str:
    raw = (value or "").strip()
    if raw == _RODAPIE_SIN_PATAS_RAW:
        return "Sin patas"
    return raw or "—"


def _designacion(mueble: dict, catalogo: dict) -> str:
    name = (mueble.get("Name") or "").strip()
    if not name:
        return ""
    entry = catalogo.get(name) or {}
    return entry.get("designaciones", {}).get("es", "")


def _identificador_mueble(mueble: dict) -> str:
    """Clave única para st.session_state.
    Usa Name SKP + posición en lista (_pos) para garantizar unicidad
    incluso cuando dos filas del CSV tienen el mismo código de mueble
    (ej. reducción de ancho que deja el Name igual al original).
    """
    base = (mueble.get("Name SKP") or mueble.get("Name") or "").strip()
    pos  = mueble.get("_pos")
    return f"{base}_{pos}" if pos is not None else base


# ----------------------------------------------------------------------------
# Builder: Paso 1 → Módulo C (contrato 2026-06-11, ver CLAUDE.md §9).
# Genera una lista plana de filas, una por mueble. Mismas keys para todos
# los muebles aunque la opcional no aplique (en ese caso "False" / "").
# ----------------------------------------------------------------------------

def _export_op_207(valor) -> str:
    """Exporta el valor de op_207_opcional al contrato con el Módulo C.

    Muebles de fregadero (P60/P90): booleano → "True" / "False".
    Muebles de despensa AGM (GM1/GM2): código SG directo (GM1 / GM2).
    El Módulo C necesita el código SG para resolver la opción; la traducción
    a etiqueta UI solo ocurre en el render del Paso 2 (_cargar_sg_a_ui).
    """
    if isinstance(valor, str) and valor not in ("True", "False", ""):
        return valor   # GM1 / GM2 → pasa directo; modulo_c lo resuelve
    return _bool_str(valor)


def _normalizar_vacio(valor: str) -> str:
    # Los helpers _ui_* usan "—" como placeholder visual; el contrato con C
    # exige cadena vacía cuando el campo no aplica.
    return "" if valor == "—" else valor


def _bool_str(valor) -> str:
    return "True" if valor else "False"


def _sensor_led_export(valor) -> str:
    if valor == "derecha":
        return "Derecha"
    if valor == "izquierda":
        return "Izquierda"
    return ""


def construir_entrada_modulo_c(
    muebles: list[dict], selecciones: dict, catalogo: dict
) -> list[dict]:
    """Construye la entrada para el Módulo C (ver contrato en CLAUDE.md §9).

    Aplica las transformaciones CSV→UI de CLAUDE.md §8, incluyendo el caso
    Trasera=Laca → color del frente (igual que en la cabecera de cards).
    Las opcionales no marcadas o no aplicables se exportan como "False" / "".

    Las filas SOCX10/SOCX07 (virtual SKP) se omiten; en su lugar se emiten
    filas SOC36010/SOC18010/SOC3607/SOC1807 con el campo "Cantidad" relleno,
    derivadas de los grupos de selección en st.session_state.rodapie_grupos.
    """
    entrada: list[dict] = []
    for mueble in muebles:
        # Saltar filas de rodapié SKP — se resuelven abajo como grupos SG
        if (mueble.get("Name") or "").strip() in CODIGOS_RODAPIE_SKP:
            continue
        clave = _identificador_mueble(mueble)
        name  = (mueble.get("Name") or "").strip()
        opcionales = (selecciones.get(clave, {}) or {}).get("opcionales", {}) or {}

        ancho_raw = (mueble.get("Ancho") or "").strip()
        reduccion = ancho_raw == _ANCHO_REDUCCION_RAW
        ancho_reducido = (
            (mueble.get("Ancho reducido") or "").strip() if reduccion else ""
        )

        # FF12V: el alto del pedido es el valor introducido por el usuario (no el de SKP)
        alto_ff12v = str(opcionales.get("alto_ff12v", "")).strip()
        if name == "FF12V" and _alto_ff12v_valido(alto_ff12v):
            alto_csv_final = f"{alto_ff12v} mm"
        else:
            alto_csv_final = (mueble.get("Alto") or "").strip()

        # Panel variable (J19VV, BPLA1, …): el usuario puede haber ajustado dimensiones en obra
        if _joue_tiene_dims_variables(name, catalogo):
            _dims = opcionales.get(f"dims_joue_var_{clave}") or {}
            _a = str(_dims.get("ancho", "")).strip()
            _h = str(_dims.get("alto",  "")).strip()
            ancho_csv_j19vv = f"{_a} mm" if _a.isdigit() else (ancho_raw if not reduccion else "")
            alto_csv_j19vv  = f"{_h} mm" if _h.isdigit() else alto_csv_final
        elif name in CODIGOS_ENCIMERA:
            _dims_enc = opcionales.get(f"dims_enc_{clave}") or {}
            _a_enc = str(_dims_enc.get("ancho", "")).strip()
            _f_enc = str(_dims_enc.get("alto",  "")).strip()
            ancho_csv_j19vv = f"{_a_enc} mm" if _a_enc.isdigit() else (ancho_raw if not reduccion else "")
            alto_csv_j19vv  = f"{_f_enc} mm" if _f_enc.isdigit() else alto_csv_final
        else:
            ancho_csv_j19vv = None  # no aplica
            alto_csv_j19vv  = None

        tirador_ui = _ui_tirador(mueble.get("Tirador", ""))

        op_126_raw = opcionales.get("op_126")
        op_126 = op_126_raw if isinstance(op_126_raw, dict) else {}
        op_126_2_raw = opcionales.get("op_126_2")
        op_126_2 = op_126_2_raw if isinstance(op_126_2_raw, dict) else {}

        fila: dict[str, str] = {
            "Código mueble": (mueble.get("Name") or "").strip(),
            "Descripción": _designacion(mueble, catalogo),
            "Posición": (mueble.get("posicion") or "").strip(),
            "Summary": (mueble.get("Summary") or "").strip(),  # identificador SKP → p_item_origin_id
            "Apertura": _normalizar_vacio(_ui_apertura(mueble.get("Apertura", ""))),
            "Gama del frente": _gama_desde_acabado(mueble.get("Acabado", "")) if name in CODIGOS_JOUE else _ui_gama(mueble.get("D_Gama", "")),
            "Acabado del frente": _ui_color_frente(mueble.get("ColorFrente", "")),
            "Color interior": _normalizar_vacio(
                _ui_color_interior(mueble.get("Color del interior", ""))
            ),
            "Tirador": tirador_ui,
            "Color tirador": _ui_color_tirador(mueble, tirador_ui),
            "Rodapié": _normalizar_vacio(
                _ui_rodapie(mueble.get("C_Rodapietext", ""))
            ),
            "Acabado del mueble abierto": _ui_color_mueble_abierto(
                mueble.get("Color del mueble abierto", "")
            ),
            "Reducción de ancho": _bool_str(reduccion),
            "Ancho reducido": ancho_reducido,
            # Tapetas y rodapiés: quitar sufijo de gama para que modulo_c pueda hacer
            # el lookup op_101 (tapetas) / op_401 (rodapiés) igual que "Acabado del frente".
            "Acabado": _ui_color_frente(mueble.get("Acabado") or "") if name in CODIGOS_TAPETA or name in CODIGOS_RODAPIE or name in CODIGOS_JOUE or name in CODIGOS_ENCIMERA else str(mueble.get("Acabado") or "").strip(),
            "Ancho CSV": ancho_csv_j19vv if ancho_csv_j19vv is not None else ("" if reduccion else ancho_raw),
            "Alto CSV": alto_csv_j19vv if alto_csv_j19vv is not None else alto_csv_final,
            "Alto final tapeta": alto_ff12v if name == "FF12V" and _alto_ff12v_valido(alto_ff12v) else "",
            "Sin mecanizado": _bool_str(opcionales.get("op_121", False)),
            "Cubos de basura": _export_op_207(opcionales.get("op_207_opcional", False)),
            "Recorte LED": _bool_str(opcionales.get("op_220", False)),
            "Sensor para mando LED": _sensor_led_export(opcionales.get("op_222")),
            "Cajón interior": _bool_str(opcionales.get("op_223", False)),
            "Mueble de caldera": _bool_str(opcionales.get("op_227", False)),
            "Sin encolar": _bool_str(opcionales.get("op_700_opcional", False)),
            "Marca electro":        str(op_126.get("marca", "")).strip(),
            "Referencia electro":   str(op_126.get("referencia", "")).strip(),
            "Alto electro":         str(op_126.get("alto", "")).strip(),
            "Marca electro 2":      str(op_126_2.get("marca", "")).strip(),
            "Referencia electro 2": str(op_126_2.get("referencia", "")).strip(),
            "Alto electro 2":       str(op_126_2.get("alto", "")).strip(),
            "Cantidad": "",
        }
        entrada.append(fila)

    # ── Filas de rodapié SG — derivadas de los grupos de selección ─────────────
    # Construir grupos a partir de las filas SOCX* del CSV original
    muebles_rodapie_skp = [m for m in muebles if (m.get("Name") or "").strip() in CODIGOS_RODAPIE_SKP]
    grupos = _agrupar_rodapies(muebles_rodapie_skp)
    rodapie_grupos_estado = st.session_state.get("rodapie_grupos", {})

    for grupo in grupos:
        key        = grupo["key"]
        code_skp   = grupo["code_skp"]
        acabado_ui = grupo["acabado_ui"]
        gama_ui    = grupo["gama_ui"]
        cod_3600   = grupo["cod_3600"]
        cod_1800   = grupo["cod_1800"]
        estado_grupo = rodapie_grupos_estado.get(key, {})
        n3600 = int(estado_grupo.get("n3600", 0) or 0)
        n1800 = int(estado_grupo.get("n1800", 0) or 0)

        for cod, cantidad in ((cod_3600, n3600), (cod_1800, n1800)):
            if not cod or cantidad <= 0:
                continue
            desc = (catalogo.get(cod) or {}).get("designaciones", {}).get("es", cod)
            fila_sg: dict[str, str] = {
                "Código mueble": cod,
                "Descripción": desc,
                "Posición": "",
                "Summary": "",
                "Apertura": "",
                "Gama del frente": gama_ui,
                "Acabado del frente": acabado_ui,
                "Color interior": "",
                "Tirador": "",
                "Color tirador": "",
                "Rodapié": "",
                "Acabado del mueble abierto": "",
                "Reducción de ancho": "False",
                "Ancho reducido": "",
                "Acabado": acabado_ui,
                "Ancho CSV": "",
                "Alto CSV": "",
                "Alto final tapeta": "",
                "Sin mecanizado": "False",
                "Cubos de basura": "False",
                "Recorte LED": "False",
                "Sensor para mando LED": "",
                "Cajón interior": "False",
                "Mueble de caldera": "False",
                "Sin encolar": "False",
                "Marca electro": "",
                "Referencia electro": "",
                "Alto electro": "",
                "Marca electro 2": "",
                "Referencia electro 2": "",
                "Alto electro 2": "",
                "Cantidad": str(cantidad),
            }
            entrada.append(fila_sg)

    return entrada


def _cabecera_card(mueble: dict, catalogo: dict, revisado: bool) -> str:
    """[check] · Summary · Name · Designación · Gama Color · Tirador Color (CLAUDE.md §7)."""
    check = "🟢" if revisado else "🔴"
    summary = (mueble.get("Summary") or "").strip()
    nombre = mueble.get("Name") or mueble.get("Name SKP") or "—"
    prefijo = f"**{summary}** " if summary else ""
    partes = [f"{check} {prefijo}{nombre}"]

    designacion = _designacion(mueble, catalogo)
    if designacion:
        partes.append(designacion)

    name_code = (mueble.get("Name") or "").strip()
    if name_code in CODIGOS_MUEBLE_ABIERTO:
        color_abierto = _ui_color_mueble_abierto(mueble.get("Color del mueble abierto", ""))
        if color_abierto:
            partes.append(color_abierto)
    elif name_code in CODIGOS_TAPETA:
        gama    = _ui_gama(mueble.get("D_Gama", ""))
        acabado = _ui_color_frente(mueble.get("Acabado") or "")   # quita sufijo gama
        gama_acabado = " ".join(p for p in (gama, acabado) if p)
        if gama_acabado:
            partes.append(gama_acabado)
        if (mueble.get("posicion") or "").strip().upper() == "H":
            partes.append("de pared")
    elif name_code in CODIGOS_RODAPIE:
        acabado = _ui_color_frente(mueble.get("Acabado") or "")   # quita sufijo gama
        if acabado:
            partes.append(acabado)
    elif name_code in CODIGOS_JOUE:
        gama    = _gama_desde_acabado(mueble.get("Acabado") or "")
        acabado = _ui_color_frente(mueble.get("Acabado") or "")
        gama_acabado = " ".join(p for p in (gama, acabado) if p)
        if gama_acabado:
            partes.append(gama_acabado)
    elif name_code in CODIGOS_ENCIMERA:
        cat_enc  = (_cargar_catalogo() or {}).get(name_code) or {}
        gama_cat = cat_enc.get("gama") or _ui_gama(mueble.get("D_Gama", ""))
        acabado  = _ui_color_frente(mueble.get("Acabado") or "")
        gama_acabado = " ".join(p for p in (gama_cat, acabado) if p)
        if gama_acabado:
            partes.append(gama_acabado)
    else:
        gama = _ui_gama(mueble.get("D_Gama", ""))
        color = _ui_color_frente(mueble.get("ColorFrente", ""))
        gama_color = " ".join(p for p in (gama, color) if p)
        if gama_color:
            partes.append(gama_color)

        tirador = _ui_tirador(mueble.get("Tirador", ""))
        if tirador:
            color_tirador = _ui_color_tirador(mueble, tirador)
            partes.append(" ".join(p for p in (tirador, color_tirador) if p))

    return " · ".join(partes)


def pantalla_validacion(muebles: list[dict]) -> None:
    """Pantalla 0 — Validación de errores del CSV. Bloquea avance si hay ⚠️ REVISAR."""
    errores = [m for m in muebles if "REVISAR" in (m.get("Estado") or "")]

    if errores:
        st.header("Errores en el CSV")
        st.error(
            f"Se han encontrado **{len(errores)}** mueble(s) con avisos. "
            "Corrige el archivo en SketchUp y vuelve a subirlo."
        )
        tabla = [
            {
                "Referencia": m.get("Summary", "") or "—",
                "Name SKP": m.get("Name SKP", "") or "—",
                "Avisos": m.get("Avisos", "") or "—",
            }
            for m in errores
        ]
        st.dataframe(tabla, hide_index=True, use_container_width=True)
        if st.button("Volver a subir CSV", type="primary"):
            st.session_state["_reset_requested"] = True
            st.rerun()
        return

    st.session_state.pantalla = PANTALLA_PASO_1
    st.rerun()


def _bloque_informativo(mueble: dict, catalogo: dict) -> None:
    """Línea inicial de la card abierta: Apertura · Ancho · Alto · Fondo · Color interior · Rodapié."""
    ancho         = _ui_ancho(mueble)
    rodapie       = _ui_rodapie(mueble.get("C_Rodapietext", ""))

    name  = (mueble.get("Name") or "").strip()
    entry = catalogo.get(name) or {}

    # Alto: columna "Alto" del CSV (altura real en SketchUp); fallback al catálogo
    len_z_raw = (mueble.get("Alto") or "").strip()
    if len_z_raw:
        try:
            alto_str = f"{int(float(len_z_raw))} mm"
        except ValueError:
            alto_str = len_z_raw
    elif entry.get("alto_mm") is not None:
        alto_str = f"{entry['alto_mm']} mm"
    else:
        alto_str = "—"

    # Fondo: del catálogo (null en frentes sin mueble)
    fondo_mm  = entry.get("fondo_mm")
    fondo_str = f"{fondo_mm} mm" if fondo_mm is not None else "—"

    if name in CODIGOS_MUEBLE_ABIERTO:
        color_abierto = _ui_color_mueble_abierto(mueble.get("Color del mueble abierto", ""))
        rodapie_label = rodapie if rodapie != "—" else ("(vacío = suspendido)" if name in CODIGOS_PS_SEGUN_RODAPIE else "—")
        posicion_ab   = (mueble.get("posicion") or "").strip().upper()
        partes_ab = [
            f"**Acabado del mueble abierto:** {color_abierto or '—'}",
            f"**Ancho:** {ancho}",
            f"**Alto:** {alto_str}",
            f"**Fondo:** {fondo_str}",
            f"**Rodapié:** {rodapie_label}",
        ]
        if posicion_ab == "S":
            partes_ab.append("**Posición:** de pared")
        elif posicion_ab == "P":
            partes_ab.append("**Posición:** con patas")
        st.markdown("  ·  ".join(partes_ab))
    elif name in CODIGOS_TAPETA:
        acabado    = _ui_color_frente(mueble.get("Acabado") or "")   # quita sufijo gama
        ancho_std  = f"{entry.get('ancho_mm')} mm" if entry.get("ancho_mm") else "—"
        ancho_skp  = ancho   # valor que viene del modelo SKP
        posicion   = (mueble.get("posicion") or "").strip().upper()
        partes = [
            f"**Acabado:** {acabado or '—'}",
            f"**Ancho:** {ancho_std}",
            f"**Alto:** {alto_str}",
            f"**Espesor:** {fondo_str}",
        ]
        if posicion == "H":
            partes.append("**Posición:** de pared")
        st.markdown("  ·  ".join(partes))
        # Las tapetas siempre se envían a la medida estándar, independientemente del modelo SKP.
        st.info(
            f"Las tapetas se envían siempre de la medida estándar "
            f"(**{ancho_std}**). El modelo 3D indica **{ancho_skp}**.",
            icon="ℹ️",
        )
    elif name in CODIGOS_RODAPIE:
        acabado   = _ui_color_frente(mueble.get("Acabado") or "")   # quita sufijo gama
        ancho_std = f"{entry.get('ancho_mm')} mm" if entry.get("ancho_mm") else "—"
        st.markdown(
            f"**Acabado:** {acabado or '—'}  ·  "
            f"**Ancho:** {ancho_std}  ·  "
            f"**Alto:** {alto_str}  ·  "
            f"**Espesor:** {fondo_str}"
        )
    elif name in CODIGOS_JOUE:
        gama      = _gama_desde_acabado(mueble.get("Acabado") or "")
        acabado   = _ui_color_frente(mueble.get("Acabado") or "")
        ancho_std = f"{entry.get('ancho_mm')} mm" if entry.get("ancho_mm") else ancho
        gama_acabado = " ".join(p for p in (gama, acabado) if p)
        st.markdown(
            f"**Acabado del panel:** {gama_acabado or '—'}  ·  "
            f"**Ancho:** {ancho_std}  ·  "
            f"**Alto:** {alto_str}  ·  "
            f"**Espesor:** {fondo_str}"
        )
    elif name in CODIGOS_ENCIMERA:
        gama_cat     = entry.get("gama") or _ui_gama(mueble.get("D_Gama", ""))
        acabado      = _ui_color_frente(mueble.get("Acabado") or "")
        gama_acabado = " ".join(p for p in (gama_cat, acabado) if p)
        espesor_str  = f"{entry['espesor_mm']} mm" if entry.get("espesor_mm") is not None else "—"
        st.markdown(
            f"**Acabado:** {gama_acabado or '—'}  ·  "
            f"**Ancho:** {ancho}  ·  "
            f"**Fondo:** {alto_str}  ·  "
            f"**Espesor:** {espesor_str}"
        )
    else:
        apertura       = _ui_apertura(mueble.get("Apertura", ""))
        color_interior = _ui_color_interior(mueble.get("Color del interior", ""))
        st.markdown(
            f"**Apertura:** {apertura}  ·  "
            f"**Ancho:** {ancho}  ·  "
            f"**Alto:** {alto_str}  ·  "
            f"**Fondo:** {fondo_str}  ·  "
            f"**Color interior:** {color_interior}  ·  "
            f"**Rodapié:** {rodapie}"
        )

    if _es_desmontado(name):
        st.info("Este mueble siempre se envía desmontado al cliente.", icon="ℹ️")


def _check_mueble(
    clave: str, selecciones: dict, razon_bloqueo: str | None = None
) -> None:
    """Checkbox explícito de revisión. Auto-cierra la card vía rerun.

    Si razon_bloqueo no es None y el check está desmarcado, se deshabilita
    para impedir marcar. Permitimos desmarcar siempre.
    """
    revisado = bool(selecciones.get(clave, {}).get("check", False))
    disabled = (not revisado) and (razon_bloqueo is not None)
    nuevo = st.checkbox(
        "He revisado este mueble",
        value=revisado,
        key=f"check_{clave}",
        disabled=disabled,
        help=razon_bloqueo if disabled else None,
    )
    if nuevo != revisado:
        selecciones.setdefault(clave, {})["check"] = nuevo
        abiertos = st.session_state.setdefault("paso_1_abiertos", set())
        if nuevo:
            abiertos.discard(clave)
        else:
            abiertos.add(clave)
        st.rerun()


def _opcionales_aplicables(mueble: dict, interfaz: dict) -> list[str]:
    """Lista de op_ids (en clave de `interfaz`) que aplican al mueble.

    La fuente de verdad de qué muebles admiten cada opcional es
    opciones_mueble.yaml, cargado en `interfaz` por _cargar_interfaz().
    """
    name = (mueble.get("Name") or "").strip()
    if not name:
        return []
    aplicables: list[str] = []

    # op_121 — solo visible cuando el tirador es de superficie (Curve=4, Line=5, Plantea=7)
    if "op_121" in interfaz:
        tirador_code = str(mueble.get("Tirador") or "").strip()
        visible_con  = interfaz["op_121"].get("visible_con_tiradores") or []
        if tirador_code in visible_con:
            aplicables.append("op_121")

    # op_207 — checkbox para fregadero (P60/P90) o radio para despensa (GM1/GM2)
    meta_207 = interfaz.get("op_207_opcional") or {}
    if (name in (meta_207.get("muebles_checkbox") or {})) or \
       (name in (meta_207.get("muebles_seleccion") or {})):
        aplicables.append("op_207_opcional")

    # op_220, op_222, op_223, op_227 — lista plana de muebles por opción
    for op_id in ("op_220", "op_222", "op_223", "op_227"):
        if name in (interfaz.get(op_id, {}).get("muebles") or []):
            aplicables.append(op_id)

    # op_700 — aplica a todos salvo los no_aplica, tapetas y rodapiés.
    # Los forzadas (campanas HH*) también se incluyen: se muestran desactivados y marcados.
    meta_700 = interfaz.get("op_700_opcional") or {}
    if "op_700_opcional" in interfaz and name not in (meta_700.get("excluidos") or []) and name not in CODIGOS_TAPETA and name not in CODIGOS_RODAPIE and name not in CODIGOS_JOUE and name not in CODIGOS_ENCIMERA:
        aplicables.append("op_700_opcional")

    # op_126 — lista plana de muebles (BFT y AFS)
    if name in (interfaz.get("op_126", {}).get("muebles") or []):
        aplicables.append("op_126")

    return aplicables


def _registrar_edicion(clave: str, selecciones: dict) -> None:
    """Reset del check al editar y mantiene la card abierta tras el rerun."""
    selecciones[clave]["check"] = False
    # Asignación explícita en lugar de pop: garantiza que el widget de Streamlit
    # muestre la casilla desmarcada visualmente en el siguiente rerun.
    st.session_state[f"check_{clave}"] = False
    st.session_state.setdefault("paso_1_abiertos", set()).add(clave)


def _control_checkbox_opcional(
    clave: str, op_id: str, meta: dict, opcionales: dict, selecciones: dict
) -> None:
    prev = bool(opcionales.get(op_id, False))
    nuevo = st.checkbox(
        meta.get("etiqueta", op_id),
        value=prev,
        key=f"{op_id}_{clave}",
        help=_TOOLTIPS_OPCIONALES.get(op_id),
    )
    if nuevo != prev:
        opcionales[op_id] = nuevo
        _registrar_edicion(clave, selecciones)
        st.rerun()


def _es_forzado_op_121(tirador_code: str, name: str, meta: dict) -> bool:
    """True si SPF debe marcarse automáticamente (Plantea siempre; Curve/Line en monoporte)."""
    forzado_siempre = meta.get("forzado_siempre") or []
    mono = meta.get("forzado_en_monoporte") or {}
    return (
        tirador_code in forzado_siempre
        or (
            tirador_code in (mono.get("tiradores") or [])
            and name in (mono.get("muebles") or [])
        )
    )


def _control_op_121(
    clave: str, name: str, tirador_code: str, meta: dict, opcionales: dict, selecciones: dict
) -> None:
    """Checkbox de op_121. Deshabilitado+marcado si es forzado; editable si no."""
    etiqueta   = meta.get("etiqueta", "Sin mecanizado para tirador")
    es_forzado = _es_forzado_op_121(tirador_code, name, meta)

    if es_forzado:
        st.checkbox(
            etiqueta,
            value=True,
            disabled=True,
            key=f"op_121_{clave}",
            help="Aplicado automáticamente por una de estas razones: el tirador no requiere taladro en el frente, o este mueble de columna monopuerta no lleva mecanizado para que la posición del tirador se ajuste en obra.",
        )
        opcionales["op_121"] = True
    else:
        prev  = bool(opcionales.get("op_121", False))
        nuevo = st.checkbox(
            etiqueta,
            value=prev,
            key=f"op_121_{clave}",
            help=_TOOLTIPS_OPCIONALES.get("op_121"),
        )
        if nuevo != prev:
            opcionales["op_121"] = nuevo
            _registrar_edicion(clave, selecciones)
            st.rerun()


def _control_op_700(
    clave: str, name: str, meta: dict, opcionales: dict, selecciones: dict
) -> None:
    """Checkbox de op_700 (Sin encolar / DEM).

    Si el mueble está en 'forzadas' → aparece desactivado y marcado
    (igual que op_121 forzado). En el resto → checkbox editable normal.
    """
    etiqueta   = meta.get("etiqueta", "Mueble sin encolar")
    es_forzado = name in (meta.get("forzadas") or [])

    if es_forzado:
        st.checkbox(
            etiqueta,
            value=True,
            disabled=True,
            key=f"op_700_opcional_{clave}",
            help="Las campanas HH siempre van sin encolar para facilitar el ajuste en obra.",
        )
        opcionales["op_700_opcional"] = True
    else:
        prev  = bool(opcionales.get("op_700_opcional", False))
        nuevo = st.checkbox(
            etiqueta,
            value=prev,
            key=f"op_700_opcional_{clave}",
            help=_TOOLTIPS_OPCIONALES.get("op_700_opcional"),
        )
        if nuevo != prev:
            opcionales["op_700_opcional"] = nuevo
            _registrar_edicion(clave, selecciones)
            st.rerun()


_OP_222_OPCIONES = ("ninguno", "derecha", "izquierda")


def _control_radio_op_222(
    clave: str, meta: dict, opcionales: dict, selecciones: dict
) -> None:
    etiquetas = {
        "ninguno": "Sin sensor",
        "derecha": meta.get("etiqueta_derecha", "Sensor derecha"),
        "izquierda": meta.get("etiqueta_izquierda", "Sensor izquierda"),
    }
    prev = opcionales.get("op_222", "ninguno")
    if prev not in _OP_222_OPCIONES:
        prev = "ninguno"
    nuevo = st.radio(
        "Sensor para mando LED",
        options=list(_OP_222_OPCIONES),
        index=_OP_222_OPCIONES.index(prev),
        format_func=lambda v: etiquetas[v],
        horizontal=True,
        key=f"op_222_{clave}",
        help=_TOOLTIPS_OPCIONALES.get("op_222"),
    )
    if nuevo != prev:
        opcionales["op_222"] = nuevo
        _registrar_edicion(clave, selecciones)
        st.rerun()


# Subcampos de op_126: fallback defensivo si mapeos_SKP_UI_SG.yaml no los provee.
# La fuente de verdad es data/mapeos_SKP_UI_SG.yaml (sección opcionales/op_126/subcampos).
_SUBCAMPOS_OP_126_DEFAULT = {
    "marca": "Marca",
    "referencia": "Referencia",
    # "alto" solo aparece en Caso B (sin referencia).
}

# Validación de formato por subcampo de op_126.
# marca      → solo letras (incluye acentos y espacio para nombres de marca compuestos)
# referencia → alfanumérico + separadores habituales en referencias de producto
# alto       → solo dígitos (valor en mm)
_VALIDACION_OP_126: dict[str, dict] = {
    "marca": {
        "patron":  re.compile(r"^[A-Za-zÀ-ÿ\s\-]+$"),
        "error":   "Solo se admiten letras",
        "ejemplo": "ej. Siemens, De Dietrich",
    },
    "referencia": {
        "patron":  re.compile(r"^[A-Za-z0-9\s\-\.\/\_]+$"),
        "error":   "Solo se admiten caracteres alfanuméricos",
        "ejemplo": "Código de modelo del fabricante. Suele aparecer en la ficha técnica.",
    },
    "alto": {
        "patron":  re.compile(r"^\d+$"),
        "error":   "Solo se admiten números enteros (en mm)",
        "ejemplo": "Altura del hueco en mm",
    },
}


def _op_126_completo(valor, meta: dict | None = None) -> bool:
    """Valida que el bloque op_126 esté completo.

    - Marca siempre obligatoria.
    - Caso A (tiene_referencia=True): Referencia obligatoria.
    - Caso B (tiene_referencia=False): Alto obligatorio (altura en mm).
    """
    if not isinstance(valor, dict):
        return False

    tiene_referencia = bool(valor.get("tiene_referencia", True))

    if tiene_referencia:
        # Caso A: Marca + Referencia obligatorios
        if not str(valor.get("marca", "")).strip():
            return False
        if not str(valor.get("referencia", "")).strip():
            return False
    else:
        # Caso B: solo Alto obligatorio (sin marca)
        if not str(valor.get("alto", "")).strip():
            return False

    # Validación de formato: ningún campo relleno puede tener formato inválido.
    for sub_key, regla in _VALIDACION_OP_126.items():
        v = str(valor.get(sub_key, "")).strip()
        if v and not regla["patron"].match(v):
            return False

    return True


def _meta_op_126(name: str, interfaz: dict) -> dict:
    """Devuelve {etiqueta, subcampos} para el mueble según su variante de op_126."""
    op126 = interfaz.get("op_126") or {}
    variante_key = (op126.get("mueble_a_variante") or {}).get(name)
    if variante_key:
        meta = (op126.get("variantes_meta") or {}).get(variante_key)
        if meta:
            return meta
    # Fallback: variante base si existe
    return (op126.get("variantes_meta") or {}).get("op_126") or {}


def _control_checkbox_op_207(
    clave: str, meta: dict, opcionales: dict, selecciones: dict
) -> None:
    """Checkbox de op_207 para muebles de fregadero (BE2B, BEBTS — P60/P90)."""
    etiqueta = meta.get("etiqueta_fregadero", "Cubos de basura")
    prev = bool(opcionales.get("op_207_opcional", False))
    nuevo = st.checkbox(
        etiqueta,
        value=prev,
        key=f"op_207_opcional_{clave}",
        help=_TOOLTIPS_OPCIONALES.get("op_207_opcional"),
    )
    if nuevo != prev:
        opcionales["op_207_opcional"] = nuevo
        _registrar_edicion(clave, selecciones)
        st.rerun()


_OP207_IMG_W = 80   # px — ancho fijo igual para todas las imágenes de op_207
_OP207_IMG_H = 65   # px — alto fijo igual para todas las imágenes de op_207


def _control_radio_op_207_seleccion(
    clave: str, name: str, meta: dict, opcionales: dict, selecciones: dict
) -> None:
    """Radio de op_207 para muebles de despensa AGM (GM1/GM2).

    Las imágenes se renderizan con HTML a dimensiones fijas e iguales para
    que ambas opciones queden a la misma altura. El radio es horizontal y
    arranca sin selección (index=None).
    """
    muebles_seleccion = meta.get("muebles_seleccion") or {}
    etiqueta_por_sg   = meta.get("etiqueta_por_sg")   or {}
    etiqueta_label    = meta.get("etiqueta_despensa", "Tipo de almacenamiento")
    opciones_sg = list(dict.fromkeys(muebles_seleccion.get(name) or []))

    if not opciones_sg:
        return

    prev = opcionales.get("op_207_opcional")
    idx  = opciones_sg.index(prev) if prev in opciones_sg else None

    # 1. Etiqueta de sección — siempre encima de todo
    st.markdown(f"**{etiqueta_label}**")

    # 2. Imágenes a tamaño idéntico, en columnas [1,1,2]
    imgs = [(sg, _imagen_opcion("op_207", sg)) for sg in opciones_sg]
    if any(p for _, p in imgs):
        img_cols = st.columns([1, 1, 2])
        for col, (sg, img_path) in zip(img_cols, imgs):
            with col:
                if img_path:
                    b64 = base64.b64encode(img_path.read_bytes()).decode()
                    st.markdown(
                        f'<img src="data:image/png;base64,{b64}" '
                        f'style="width:{_OP207_IMG_W}px;height:{_OP207_IMG_H}px;'
                        f'object-fit:contain;display:block"/>',
                        unsafe_allow_html=True,
                    )

    # 3. Radio horizontal sin etiqueta (ya se mostró arriba)
    nuevo = st.radio(
        etiqueta_label,
        options=opciones_sg,
        index=idx,
        format_func=lambda v: etiqueta_por_sg.get(v, v),
        horizontal=True,
        label_visibility="collapsed",
        key=f"op_207_opcional_{clave}",
        help=_TOOLTIPS_OPCIONALES.get("op_207_almacenamiento"),
    )
    if nuevo is not None and nuevo != prev:
        opcionales["op_207_opcional"] = nuevo
        _registrar_edicion(clave, selecciones)
        st.rerun()


def _control_op_207(
    clave: str, name: str, meta: dict, opcionales: dict, selecciones: dict
) -> None:
    """Dispatcher de op_207: checkbox (fregadero) o radio (despensa AGM)."""
    if name in (meta.get("muebles_seleccion") or {}):
        _control_radio_op_207_seleccion(clave, name, meta, opcionales, selecciones)
    else:
        _control_checkbox_op_207(clave, meta, opcionales, selecciones)


def _render_bloque_electro(
    clave: str, sufijo: str, prev: dict, solo_caso_a: bool = False
) -> dict:
    """Renderiza los campos de un electrodoméstico y retorna el nuevo valor.

    Caso A (¿Conoces la referencia? → Sí): Marca + Referencia.
    Caso B (¿Conoces la referencia? → No): solo Altura (mm), sin marca.
    Si solo_caso_a=True (campanas), el radio no se muestra y siempre es Caso A.
    """
    key = f"_{sufijo}" if sufijo else ""
    nuevo: dict = {}

    if solo_caso_a:
        # Campanas: solo Caso A, sin radio
        tiene_referencia = True
    else:
        # Radio primero
        prev_tiene_ref = bool(prev.get("tiene_referencia", True))
        radio_val = st.radio(
            "¿Conoces la referencia?",
            options=["Sí", "No"],
            index=0 if prev_tiene_ref else 1,
            key=f"op_126_tiene_ref{key}_{clave}",
            horizontal=True,
        )
        tiene_referencia = (radio_val == "Sí")

    nuevo["tiene_referencia"] = tiene_referencia

    if tiene_referencia:
        # Caso A: Marca + Referencia
        regla_marca = _VALIDACION_OP_126["marca"]
        marca_val = st.text_input(
            "Marca",
            value=prev.get("marca", ""),
            key=f"op_126_marca{key}_{clave}",
            help=regla_marca["ejemplo"],
        )
        if marca_val.strip() and not regla_marca["patron"].match(marca_val.strip()):
            st.caption(f"⚠️ {regla_marca['error']} ({regla_marca['ejemplo']})")
        nuevo["marca"] = marca_val

        regla_ref = _VALIDACION_OP_126["referencia"]
        ref_val = st.text_input(
            "Referencia",
            value=prev.get("referencia", ""),
            key=f"op_126_referencia{key}_{clave}",
            help=regla_ref["ejemplo"],
        )
        if ref_val.strip() and not regla_ref["patron"].match(ref_val.strip()):
            st.caption(f"⚠️ {regla_ref['error']} ({regla_ref['ejemplo']})")
        nuevo["referencia"] = ref_val
        nuevo["alto"] = ""
    else:
        # Caso B: solo Altura (sin marca)
        nuevo["marca"] = ""
        nuevo["referencia"] = ""
        regla_alto = _VALIDACION_OP_126["alto"]
        alto_val = st.text_input(
            "Altura (mm)",
            value=prev.get("alto", ""),
            key=f"op_126_alto{key}_{clave}",
            help=regla_alto["ejemplo"],
        )
        if alto_val.strip() and not regla_alto["patron"].match(alto_val.strip()):
            st.caption(f"⚠️ {regla_alto['error']} ({regla_alto['ejemplo']})")
        nuevo["alto"] = alto_val

    return nuevo


def _control_electrodomestico_op_126(
    clave: str, meta: dict, opcionales: dict, selecciones: dict
) -> None:
    doble       = bool(meta.get("doble"))
    solo_caso_a = bool(meta.get("solo_caso_a", False))

    st.markdown(f"**{meta.get('ui') or meta.get('etiqueta') or 'Electrodoméstico'}**")
    if solo_caso_a:
        st.caption("Indica la marca y referencia del modelo.")
    elif _TOOLTIPS_OPCIONALES.get("op_126"):
        st.caption(_TOOLTIPS_OPCIONALES["op_126"])

    if doble:
        # ── Dos slots: electro 1 (inferior) y electro 2 (superior) ───────────
        prev_1 = opcionales.get("op_126")   if isinstance(opcionales.get("op_126"),   dict) else {}
        prev_2 = opcionales.get("op_126_2") if isinstance(opcionales.get("op_126_2"), dict) else {}
        st.caption("Electrodoméstico 1 (inferior)")
        nuevo_1 = _render_bloque_electro(clave, "1", prev_1, solo_caso_a)
        st.caption("Electrodoméstico 2 (superior)")
        nuevo_2 = _render_bloque_electro(clave, "2", prev_2, solo_caso_a)
        if nuevo_1 != prev_1 or nuevo_2 != prev_2:
            opcionales["op_126"]   = nuevo_1
            opcionales["op_126_2"] = nuevo_2
            _registrar_edicion(clave, selecciones)
            st.rerun()
    else:
        # ── Un solo slot ──────────────────────────────────────────────────────
        prev = opcionales.get("op_126") if isinstance(opcionales.get("op_126"), dict) else {}
        nuevo = _render_bloque_electro(clave, "", prev, solo_caso_a)
        if nuevo != prev:
            opcionales["op_126"] = nuevo
            _registrar_edicion(clave, selecciones)
            st.rerun()


def _renderizar_opcionales(
    clave: str, name: str, tirador_code: str, aplicables: list[str], interfaz: dict, selecciones: dict
) -> None:
    """Renderiza checkboxes y radio. op_126 (texto libre) va aparte tras divisor."""
    opcionales = selecciones[clave].setdefault("opcionales", {})
    for op_id in aplicables:
        if op_id == "op_126":
            continue
        meta = interfaz.get(op_id, {})
        if op_id == "op_121":
            _control_op_121(clave, name, tirador_code, meta, opcionales, selecciones)
        elif op_id == "op_222":
            # Solo visible si "Recorte para perfil LED" (op_220) está activo.
            if bool(opcionales.get("op_220", False)):
                _control_radio_op_222(clave, meta, opcionales, selecciones)
            else:
                # Resetear selección de sensor al desactivar el recorte LED.
                if opcionales.get("op_222") not in (None, "ninguno"):
                    opcionales["op_222"] = "ninguno"
        elif op_id == "op_207_opcional":
            _control_op_207(clave, name, meta, opcionales, selecciones)
        elif op_id == "op_700_opcional":
            _control_op_700(clave, name, meta, opcionales, selecciones)
        else:
            _control_checkbox_opcional(clave, op_id, meta, opcionales, selecciones)


def _alto_ff12v_valido(valor: str) -> bool:
    """True si el valor introducido para el alto de FF12V es numéricamente válido."""
    v = str(valor).strip()
    return v.isdigit() and _FF12V_ALTO_MIN <= int(v) <= _FF12V_ALTO_MAX


def _joue_tiene_dims_variables(name: str, catalogo: dict) -> bool:
    """True si el código es una joue/panel con al menos una dimensión variable en el catálogo."""
    if name not in CODIGOS_JOUE:
        return False
    e = catalogo.get(name) or {}
    return bool(
        e.get("alto_variable") or e.get("ancho_variable") or
        e.get("alto_variable_por_gama") or e.get("ancho_variable_por_gama")
    )


def _rango_variable_joue(cat_entry: dict, dim: str, gama: str) -> dict:
    """Devuelve el dict {min, max} para la dimensión 'alto' o 'ancho' de una joue.

    Prioriza 'alto_variable_por_gama'/'ancho_variable_por_gama' si existen
    (rangos distintos por gama); si no, cae en 'alto_variable'/'ancho_variable'.
    """
    por_gama = cat_entry.get(f"{dim}_variable_por_gama") or {}
    if por_gama:
        return por_gama.get(gama) or {}
    return cat_entry.get(f"{dim}_variable") or {}


def _joue_dims_validas(dims: dict, cat_entry: dict) -> bool:
    """True si las dimensiones guardadas para una joue variable son enteras y dentro del rango."""
    av  = cat_entry.get("ancho_variable") or {}
    alt = cat_entry.get("alto_variable")  or {}
    a_s = str(dims.get("ancho", "")).strip()
    h_s = str(dims.get("alto",  "")).strip()
    if not (a_s.isdigit() and h_s.isdigit()):
        return False
    return (av.get("min", 0) <= int(a_s) <= av.get("max", 9999)
            and alt.get("min", 0) <= int(h_s) <= alt.get("max", 9999))


def _control_dimensiones_joue_variable(
    clave: str, name: str, mueble: dict, catalogo: dict, opcionales: dict, selecciones: dict
) -> None:
    """Controles para ajustar las dimensiones variables de un panel antes de enviar a SG.

    Muestra input solo para las dimensiones marcadas como variables en el catálogo.
    Pre-rellena con los valores del modelo SKP; el usuario puede ampliarlos en obra.
    """
    cat_entry  = catalogo.get(name) or {}
    gama       = _gama_desde_acabado(mueble.get("Acabado", ""))
    av         = _rango_variable_joue(cat_entry, "ancho", gama)
    alt_v      = _rango_variable_joue(cat_entry, "alto",  gama)
    tiene_av   = bool(av)
    tiene_altv = bool(alt_v)

    ancho_csv = (mueble.get("Ancho") or "").replace("mm", "").strip()
    alto_csv  = (mueble.get("Alto")  or "").replace("mm", "").strip()

    _key = f"dims_joue_var_{clave}"
    dims   = opcionales.get(_key) or {}
    prev_a = str(dims.get("ancho", ancho_csv)).strip()
    prev_h = str(dims.get("alto",  alto_csv)).strip()

    def _safe_int(s: str, fallback: int) -> int:
        return int(s) if s.isdigit() else fallback

    partes_info = []
    if tiene_av:
        partes_info.append(f"**{ancho_csv} mm** de ancho")
    if tiene_altv:
        partes_info.append(f"**{alto_csv} mm** de alto")
    st.info(
        f"Panel de dimensiones variables. El modelo 3D indica "
        f"{' · '.join(partes_info)}. "
        f"Puedes ajustar las medidas para recrecerlas y ajustar en obra.",
        icon="ℹ️",
    )

    nuevo_a_s = prev_a
    nuevo_h_s = prev_h

    cols = st.columns(2 if (tiene_av and tiene_altv) else 1)
    col_idx = 0

    if tiene_av:
        ancho_min = av.get("min", 100)
        ancho_max = av.get("max", 9999)
        with cols[col_idx]:
            nuevo_a = st.number_input(
                f"Ancho (mm)  [{ancho_min}–{ancho_max}]",
                min_value=ancho_min, max_value=ancho_max,
                value=_safe_int(prev_a, ancho_min),
                step=1,
                key=f"dims_joue_var_ancho_{clave}",
            )
        nuevo_a_s = str(nuevo_a)
        col_idx += 1

    if tiene_altv:
        alto_min = alt_v.get("min", 100)
        alto_max = alt_v.get("max", 9999)
        with cols[col_idx]:
            nuevo_h = st.number_input(
                f"Alto (mm)  [{alto_min}–{alto_max}]",
                min_value=alto_min, max_value=alto_max,
                value=_safe_int(prev_h, alto_min),
                step=1,
                key=f"dims_joue_var_alto_{clave}",
            )
        nuevo_h_s = str(nuevo_h)

    if nuevo_a_s != prev_a or nuevo_h_s != prev_h:
        opcionales[_key] = {"ancho": nuevo_a_s, "alto": nuevo_h_s}
        _registrar_edicion(clave, selecciones)
        st.rerun()
    elif _key not in opcionales:
        opcionales[_key] = {"ancho": prev_a, "alto": prev_h}


def _control_dimensiones_encimera(
    clave: str, name: str, mueble: dict, catalogo: dict, opcionales: dict, selecciones: dict
) -> None:
    """Controles para ajustar Ancho y Fondo de encimeras con dimensiones variables."""
    cat_entry  = catalogo.get(name) or {}
    av         = cat_entry.get("ancho_variable") or {}
    fv         = cat_entry.get("alto_variable")  or {}  # "alto" del CSV = fondo físico

    ancho_csv = (mueble.get("Ancho") or "").replace("mm", "").strip()
    fondo_csv = (mueble.get("Alto")  or "").replace("mm", "").strip()

    _key  = f"dims_enc_{clave}"
    dims  = opcionales.get(_key) or {}
    prev_a = str(dims.get("ancho", ancho_csv)).strip()
    prev_f = str(dims.get("alto",  fondo_csv)).strip()

    def _safe_int(s: str, fallback: int) -> int:
        return int(s) if s.isdigit() else fallback

    partes_info = []
    if av:
        partes_info.append(f"**{ancho_csv} mm** de ancho")
    if fv:
        partes_info.append(f"**{fondo_csv} mm** de fondo")
    st.info(
        f"Encimera de dimensiones variables. El modelo 3D indica "
        f"{' · '.join(partes_info)}. Puedes ajustar las medidas.",
        icon="ℹ️",
    )

    nuevo_a_s = prev_a
    nuevo_f_s = prev_f

    cols = st.columns(2 if (av and fv) else 1)
    col_idx = 0

    if av:
        with cols[col_idx]:
            nuevo_a = st.number_input(
                f"Ancho (mm)  [{av['min']}–{av['max']}]",
                min_value=av["min"], max_value=av["max"],
                value=_safe_int(prev_a, av["min"]),
                step=1,
                key=f"dims_enc_ancho_{clave}",
            )
        nuevo_a_s = str(nuevo_a)
        col_idx += 1

    if fv:
        with cols[col_idx]:
            nuevo_f = st.number_input(
                f"Fondo (mm)  [{fv['min']}–{fv['max']}]",
                min_value=fv["min"], max_value=fv["max"],
                value=_safe_int(prev_f, fv["min"]),
                step=1,
                key=f"dims_enc_fondo_{clave}",
            )
        nuevo_f_s = str(nuevo_f)

    if nuevo_a_s != prev_a or nuevo_f_s != prev_f:
        opcionales[_key] = {"ancho": nuevo_a_s, "alto": nuevo_f_s}
        _registrar_edicion(clave, selecciones)
        st.rerun()
    elif _key not in opcionales:
        opcionales[_key] = {"ancho": prev_a, "alto": prev_f}


def _control_alto_tapeta_variable(
    clave: str, mueble: dict, opcionales: dict, selecciones: dict
) -> None:
    """Advertencia + campo de alto final para FF12V (tapeta de alto variable).

    El valor introducido por el usuario reemplazará el alto de SketchUp en el
    resumen del pedido y en el JSON enviado a Schmidt Groupe (p_height).
    Rango permitido: _FF12V_ALTO_MIN – _FF12V_ALTO_MAX mm.
    """
    # Alto que viene del modelo SKP (solo para mostrar en el aviso)
    len_z_raw = (mueble.get("Alto") or "").strip()
    try:
        alto_skp_str = f"{int(float(len_z_raw))} mm" if len_z_raw else None
    except ValueError:
        alto_skp_str = len_z_raw or None

    if alto_skp_str:
        st.warning(
            f"Este elemento mide **{alto_skp_str}** de alto en el modelo 3D, pero siempre "
            f"recomendamos mandar las piezas a medida recrecidas para ajustar en obra.",
            icon="⚠️",
        )
    else:
        st.warning(
            "Siempre recomendamos mandar las piezas a medida recrecidas para ajustar en obra.",
            icon="⚠️",
        )

    prev_alto = str(opcionales.get("alto_ff12v", "")).strip()
    nuevo_alto = st.text_input(
        "¿Qué medida final de alto debe tener la pieza? (mm)",
        value=prev_alto,
        key=f"alto_ff12v_{clave}",
        placeholder=f"Entre {_FF12V_ALTO_MIN} y {_FF12V_ALTO_MAX}",
        help=f"Solo números enteros en mm. Mínimo {_FF12V_ALTO_MIN} mm, máximo {_FF12V_ALTO_MAX} mm.",
    )

    v = nuevo_alto.strip()
    if v:
        if not v.isdigit():
            st.caption("⚠️ Introduce solo números enteros (sin decimales ni unidades).")
        elif not (_FF12V_ALTO_MIN <= int(v) <= _FF12V_ALTO_MAX):
            st.caption(
                f"⚠️ El alto debe estar entre {_FF12V_ALTO_MIN} mm y {_FF12V_ALTO_MAX} mm."
            )

    if nuevo_alto != prev_alto:
        opcionales["alto_ff12v"] = nuevo_alto
        _registrar_edicion(clave, selecciones)
        st.rerun()


def _render_cabecera_global(
    muebles: list[dict],
    selecciones: dict,
    grupos_rodapie: list[dict] | None = None,
) -> None:
    """Contador en vivo + acciones globales (CLAUDE.md §7)."""
    grupos_rodapie = grupos_rodapie or []
    total = len(muebles) + len(grupos_rodapie)
    revisados_m = sum(
        1 for m in muebles
        if selecciones.get(_identificador_mueble(m), {}).get("check")
    )
    revisados_g = sum(
        1 for g in grupos_rodapie
        if st.session_state.get("rodapie_grupos", {}).get(g["key"], {}).get("check")
    )
    revisados = revisados_m + revisados_g
    pendientes = total - revisados

    st.markdown(
        f"**{total} muebles**  ·  "
        f"**{revisados} revisados**  ·  "
        f"**{pendientes} pendientes**"
    )

    col_expandir, col_colapsar, col_filtro = st.columns([1, 1, 1])
    with col_expandir:
        if st.button("Expandir todas", use_container_width=True):
            st.session_state.paso_1_abiertos = {
                _identificador_mueble(m) for m in muebles
            }
            st.rerun()
    with col_colapsar:
        if st.button("Colapsar todas", use_container_width=True):
            st.session_state.paso_1_abiertos = set()
            st.rerun()
    with col_filtro:
        st.checkbox(
            "Solo pendientes",
            key="paso_1_solo_pendientes",
        )


def _agrupar_rodapies(muebles_rodapie: list[dict]) -> list[dict]:
    """Agrupa piezas de rodapié por (código SKP, gama, acabado) y suma anchos.

    Devuelve una lista de dicts con la estructura:
        key, code_skp, gama_ui, acabado_ui, piezas, total_mm, cod_3600, cod_1800
    """
    grupos: dict[str, dict] = {}
    for m in muebles_rodapie:
        code_skp  = (m.get("Name") or "").strip()
        acabado_raw = (m.get("Acabado") or "").strip()
        acabado_ui  = _ui_color_frente(acabado_raw)
        gama_ui     = _ui_gama(m.get("D_Gama", ""))
        key = f"{code_skp}|{gama_ui}|{acabado_ui}"

        ancho_raw = (m.get("Ancho") or "").strip()
        # Acepta enteros y decimales con punto o coma ("4721,2 mm", "2769 mm", "2769.5 mm")
        match_mm  = re.match(r"^(\d+(?:[.,]\d+)?)\s*mm$", ancho_raw)
        ancho_mm  = round(float(match_mm.group(1).replace(",", "."))) if match_mm else 0
        summary   = (m.get("Summary") or "").strip()

        if key not in grupos:
            resolucion = _RESOLUCION_RODAPIE.get(code_skp, [])
            grupos[key] = {
                "key":       key,
                "code_skp":  code_skp,
                "gama_ui":   gama_ui,
                "acabado_ui": acabado_ui,
                "piezas":    [],
                "total_mm":  0,
                "cod_3600":  resolucion[0] if len(resolucion) > 0 else "",
                "cod_1800":  resolucion[1] if len(resolucion) > 1 else "",
            }
        grupos[key]["piezas"].append({"summary": summary, "ancho_mm": ancho_mm})
        grupos[key]["total_mm"] += ancho_mm

    return list(grupos.values())


def _render_card_grupo_rodapie(grupo: dict, catalogo: dict) -> None:  # noqa: C901
    """Renderiza la card de selección de piezas para un grupo de rodapié."""
    key        = grupo["key"]
    code_skp   = grupo["code_skp"]
    acabado_ui = grupo["acabado_ui"]
    gama_ui    = grupo["gama_ui"]
    cod_3600   = grupo["cod_3600"]
    cod_1800   = grupo["cod_1800"]
    total_mm   = grupo["total_mm"]

    if "rodapie_grupos" not in st.session_state:
        st.session_state.rodapie_grupos = {}
    estado = st.session_state.rodapie_grupos.setdefault(
        key, {"n3600": 0, "n1800": 0, "check": False}
    )
    revisado = bool(estado.get("check", False))

    alto_mm  = 100 if code_skp == "SOCX10" else 70
    titulo   = (
        f"{'🟢' if revisado else '🔴'}  Rodapié {alto_mm} mm  ·  "
        f"{acabado_ui} ({gama_ui})  ·  Total necesario: {total_mm} mm"
    )
    expanded = key in st.session_state.get("rodapie_grupos_abiertos", set())

    with st.expander(titulo, expanded=expanded):
        img_path = _imagen_mueble(code_skp)
        col_img, col_body = (st.columns([1, 3]) if img_path else (None, None))

        def _cuerpo() -> None:
            # Lista de piezas individuales
            st.markdown("**Piezas incluidas en este grupo:**")
            for pieza in grupo["piezas"]:
                ancho_str = f"{pieza['ancho_mm']} mm" if pieza["ancho_mm"] else "—"
                st.markdown(
                    f"- **{pieza['summary']}** · {ancho_str}"
                    if pieza["summary"] else f"- {ancho_str}"
                )
            st.markdown(f"**Total necesario: {total_mm} mm**")
            st.divider()

            # Selectores de cantidad
            st.markdown("**Selecciona el número de piezas a pedir:**")
            c1, c2 = st.columns(2)
            with c1:
                n3600_nuevo = st.number_input(
                    f"{cod_3600}  (3600 mm/pieza)",
                    min_value=0,
                    step=1,
                    value=int(estado.get("n3600", 0)),
                    key=f"rod_n3600_{key}",
                )
            with c2:
                n1800_nuevo = st.number_input(
                    f"{cod_1800}  (1800 mm/pieza)",
                    min_value=0,
                    step=1,
                    value=int(estado.get("n1800", 0)),
                    key=f"rod_n1800_{key}",
                )

            # Actualizar y resetear check si cambian las cantidades
            if n3600_nuevo != estado.get("n3600") or n1800_nuevo != estado.get("n1800"):
                estado["n3600"] = n3600_nuevo
                estado["n1800"] = n1800_nuevo
                # Resetear el check tanto en nuestro dict como en el estado interno
                # del widget de Streamlit (si no se hace los dos, el widget lo ignora)
                estado["check"] = False
                st.session_state[f"check_rod_{key}"] = False
                st.rerun()

            total_elegido = n3600_nuevo * 3600 + n1800_nuevo * 1800

            # Contador en vivo
            if total_elegido == 0:
                st.info("Selecciona las piezas necesarias.")
            elif total_elegido < total_mm:
                falta = total_mm - total_elegido
                st.error(
                    f"Total elegido: **{total_elegido} mm** — faltan **{falta} mm** "
                    f"para cubrir los {total_mm} mm necesarios."
                )
            elif total_elegido == total_mm:
                st.warning(
                    f"Total elegido: **{total_elegido} mm** — exactamente igual al necesario. "
                    "Se recomienda añadir algo más de material para evitar mermas."
                )
            else:
                sobrante = total_elegido - total_mm
                st.success(
                    f"✅ Total elegido: **{total_elegido} mm** "
                    f"(necesario: {total_mm} mm · sobrante: {sobrante} mm)"
                )

            # Check de revisado
            st.divider()
            razon = None
            if total_elegido < total_mm:
                razon = (
                    f"El total elegido ({total_elegido} mm) es inferior al necesario "
                    f"({total_mm} mm). Añade más piezas antes de marcar como revisado."
                )
            disabled = (not revisado) and (razon is not None)
            nuevo_check = st.checkbox(
                "He revisado este grupo de rodapié",
                value=revisado,
                key=f"check_rod_{key}",
                disabled=disabled,
                help=razon if disabled else None,
            )
            if nuevo_check != revisado:
                estado["check"] = nuevo_check
                abiertos_rod = st.session_state.setdefault("rodapie_grupos_abiertos", set())
                if nuevo_check:
                    abiertos_rod.discard(key)   # colapsar al marcar
                else:
                    abiertos_rod.add(key)        # expandir al desmarcar
                st.rerun()

        if img_path and col_img is not None:
            with col_img:
                st.image(str(img_path), width=229)
                _render_swatches_color(acabado_ui, "", etiqueta_frente="Acabado")
            with col_body:
                _cuerpo()
        else:
            _cuerpo()


def paso_1(muebles: list[dict]) -> None:
    """Paso 1 — Cards plegables, una por mueble, en orden del CSV."""
    catalogo = _cargar_catalogo()
    interfaz = _cargar_interfaz()
    selecciones = st.session_state.selecciones_paso_1

    # Separar rodapiés SKP del resto — se procesan aparte en cards de grupo al final.
    muebles_normales   = [m for m in muebles if (m.get("Name") or "").strip() not in CODIGOS_RODAPIE_SKP]
    muebles_rodapie_skp = [m for m in muebles if (m.get("Name") or "").strip() in CODIGOS_RODAPIE_SKP]
    grupos_rodapie = _agrupar_rodapies(muebles_rodapie_skp)

    # Inicializar estado de grupos en session_state
    if "rodapie_grupos" not in st.session_state:
        st.session_state.rodapie_grupos = {}
    if "rodapie_grupos_abiertos" not in st.session_state:
        st.session_state.rodapie_grupos_abiertos = set()
    for grupo in grupos_rodapie:
        key_g = grupo["key"]
        es_nuevo = key_g not in st.session_state.rodapie_grupos
        st.session_state.rodapie_grupos.setdefault(
            key_g, {"n3600": 0, "n1800": 0, "check": False}
        )
        if es_nuevo:
            # Solo los grupos nuevos empiezan expandidos;
            # los ya existentes conservan su estado (colapsado si estaban revisados)
            st.session_state.rodapie_grupos_abiertos.add(key_g)

    # Expandidos por defecto: inicializar con todas las claves si aún no existe.
    if "paso_1_abiertos" not in st.session_state:
        st.session_state["paso_1_abiertos"] = {
            _identificador_mueble(m) for m in muebles_normales
        }
    abiertos = st.session_state["paso_1_abiertos"]

    # Inicializa estado y pre-check para todos los muebles normales antes de pintar la
    # cabecera (los contadores deben verlos ya inicializados).
    for mueble in muebles_normales:
        clave = _identificador_mueble(mueble)
        name  = (mueble.get("Name") or "").strip()
        aplicables = _opcionales_aplicables(mueble, interfaz)
        estado = selecciones.setdefault(clave, {})
        opcionales = estado.setdefault("opcionales", {})
        if "check" not in estado:
            # El check siempre empieza desmarcado — el usuario debe marcarlo manualmente.
            estado["check"] = False
        # op_207 para muebles de despensa AGM: NO se pre-inicializa.
        # El usuario debe elegir explícitamente; hasta que lo haga el check queda bloqueado.

        # op_700 forzadas (campanas HH*): inicializar a True aunque el usuario no abra la card.
        if "op_700_opcional" in aplicables and "op_700_opcional" not in opcionales:
            meta_700 = interfaz.get("op_700_opcional") or {}
            if name in (meta_700.get("forzadas") or []):
                opcionales["op_700_opcional"] = True
        # Inicializar op_121 a True si es forzado (Plantea siempre; Curve/Line en monoporte).
        # Garantiza que "Sin mecanizado" llegue correctamente a construir_entrada_modulo_c
        # aunque el usuario no abra la card.
        if "op_121" in aplicables and "op_121" not in opcionales:
            meta_121 = interfaz.get("op_121") or {}
            tirador_code_init = str(mueble.get("Tirador") or "").strip()
            if _es_forzado_op_121(tirador_code_init, name, meta_121):
                opcionales["op_121"] = True

        # Panel variable (J19VV, BPLA1, …): pre-inicializar dimensiones con los valores del CSV.
        if _joue_tiene_dims_variables(name, catalogo):
            _key_init = f"dims_joue_var_{clave}"
            if _key_init not in opcionales:
                ancho_init = (mueble.get("Ancho") or "").replace("mm", "").strip()
                alto_init  = (mueble.get("Alto")  or "").replace("mm", "").strip()
                opcionales[_key_init] = {"ancho": ancho_init, "alto": alto_init}

        # Encimera: pre-inicializar dimensiones con los valores del CSV.
        if name in CODIGOS_ENCIMERA:
            _key_enc_init = f"dims_enc_{clave}"
            if _key_enc_init not in opcionales:
                ancho_init = (mueble.get("Ancho") or "").replace("mm", "").strip()
                fondo_init = (mueble.get("Alto")  or "").replace("mm", "").strip()
                opcionales[_key_enc_init] = {"ancho": ancho_init, "alto": fondo_init}

    st.header("Paso 1 — Selección de opciones")
    _render_cabecera_global(muebles_normales, selecciones, grupos_rodapie)
    st.divider()

    solo_pendientes = bool(st.session_state.get("paso_1_solo_pendientes", False))
    a_mostrar = sorted(
        [
            m for m in muebles_normales
            if not (
                solo_pendientes
                and selecciones.get(_identificador_mueble(m), {}).get("check")
            )
        ],
        key=lambda m: [
            int(t) if t.isdigit() else t.lower()
            for t in re.split(r"(\d+)", (m.get("Summary") or "").strip())
        ],
    )

    if a_mostrar:
        for mueble in a_mostrar:
            clave = _identificador_mueble(mueble)
            name  = (mueble.get("Name") or "").strip()
            aplicables = _opcionales_aplicables(mueble, interfaz)
            estado = selecciones[clave]
            revisado = bool(estado["check"])
            expanded = clave in abiertos

            with st.expander(
                _cabecera_card(mueble, catalogo, revisado),
                expanded=expanded,
            ):
                img_path    = _imagen_mueble(name, mueble.get("posicion") or "")
                meta_126    = _meta_op_126(name, interfaz)
                es_abierto  = name in CODIGOS_MUEBLE_ABIERTO
                # Helper local: swatch adaptado a mueble normal, tapeta o rodapié
                def _swatch(en_imagen: bool = True) -> None:
                    if es_abierto:
                        return
                    if name in CODIGOS_TAPETA:
                        _render_swatches_color(
                            _ui_color_frente(mueble.get("Acabado") or ""),
                            "",
                            etiqueta_frente="Acabado",
                        )
                    elif name in CODIGOS_RODAPIE:
                        _render_swatches_color(
                            _ui_color_frente(mueble.get("Acabado") or ""),
                            "",
                            etiqueta_frente="Acabado",
                        )
                    elif name in CODIGOS_JOUE:
                        _render_swatches_color(
                            _ui_color_frente(mueble.get("Acabado") or ""),
                            "",
                            etiqueta_frente="Acabado del panel",
                        )
                    elif name in CODIGOS_ENCIMERA:
                        _render_swatches_color(
                            _ui_color_frente(mueble.get("Acabado") or ""),
                            "",
                            etiqueta_frente="Acabado",
                        )
                    else:
                        _render_swatches_color(
                            _ui_color_frente(mueble.get("ColorFrente", "")),
                            _ui_color_interior(mueble.get("Color del interior", "")),
                        )

                if img_path:
                    col_img, col_info = st.columns([1, 3])
                    with col_img:
                        st.image(str(img_path), width=229)
                        _swatch()
                    with col_info:
                        _bloque_informativo(mueble, catalogo)
                        if aplicables:
                            tirador_code = str(mueble.get("Tirador") or "").strip()
                            _renderizar_opcionales(clave, name, tirador_code, aplicables, interfaz, selecciones)
                            if "op_126" in aplicables:
                                st.divider()
                                _control_electrodomestico_op_126(
                                    clave, meta_126,
                                    estado["opcionales"], selecciones,
                                )
                        if name == "FF12V":
                            st.divider()
                            _control_alto_tapeta_variable(
                                clave, mueble, estado["opcionales"], selecciones
                            )
                    if _joue_tiene_dims_variables(name, catalogo):
                            st.divider()
                            _control_dimensiones_joue_variable(
                                clave, name, mueble, catalogo, estado["opcionales"], selecciones
                            )
                    if name in CODIGOS_ENCIMERA:
                            st.divider()
                            _control_dimensiones_encimera(
                                clave, name, mueble, catalogo, estado["opcionales"], selecciones
                            )
                else:
                    _bloque_informativo(mueble, catalogo)
                    _swatch()
                    if aplicables:
                        tirador_code = str(mueble.get("Tirador") or "").strip()
                        _renderizar_opcionales(clave, name, tirador_code, aplicables, interfaz, selecciones)
                        if "op_126" in aplicables:
                            st.divider()
                            _control_electrodomestico_op_126(
                                clave, meta_126,
                                estado["opcionales"], selecciones,
                            )
                    if name == "FF12V":
                        st.divider()
                        _control_alto_tapeta_variable(
                            clave, mueble, estado["opcionales"], selecciones
                        )
                    if _joue_tiene_dims_variables(name, catalogo):
                        st.divider()
                        _control_dimensiones_joue_variable(
                            clave, name, mueble, catalogo, estado["opcionales"], selecciones
                        )
                    if name in CODIGOS_ENCIMERA:
                        st.divider()
                        _control_dimensiones_encimera(
                            clave, name, mueble, catalogo, estado["opcionales"], selecciones
                        )

                razon_bloqueo = None
                if name == "FF12V":
                    if not _alto_ff12v_valido(estado["opcionales"].get("alto_ff12v", "")):
                        razon_bloqueo = (
                            "Indica la medida final de alto de la pieza "
                            "antes de marcar como revisado."
                        )
                elif "op_126" in aplicables:
                    _doble = bool(meta_126.get("doble"))
                    _e1_ok = _op_126_completo(estado["opcionales"].get("op_126"), meta=meta_126)
                    _e2_ok = (not _doble) or _op_126_completo(estado["opcionales"].get("op_126_2"), meta=meta_126)
                    if not (_e1_ok and _e2_ok):
                        razon_bloqueo = (
                            "Completa todos los campos obligatorios del electrodoméstico "
                            "antes de marcar como revisado."
                        )
                elif "op_207_opcional" in aplicables:
                    _meta_207 = interfaz.get("op_207_opcional") or {}
                    _muebles_sel = _meta_207.get("muebles_seleccion") or {}
                    if name in _muebles_sel:
                        _ops_sg = list(dict.fromkeys(_muebles_sel.get(name) or []))
                        if estado["opcionales"].get("op_207_opcional") not in _ops_sg:
                            razon_bloqueo = (
                                "Selecciona el tipo de almacenamiento "
                                "antes de marcar como revisado."
                            )

                st.divider()
                _check_mueble(clave, selecciones, razon_bloqueo=razon_bloqueo)
    else:
        if muebles_normales:
            st.info("No hay muebles pendientes. Todo revisado.")

    # ── Cards de grupos de rodapié — al final, colapsadas por defecto ─────────
    if grupos_rodapie:
        st.divider()
        st.subheader("Rodapiés")
        for grupo in grupos_rodapie:
            _render_card_grupo_rodapie(grupo, catalogo)

    # Botón final de avance al Paso 2 (CLAUDE.md §7: solo al final).
    st.divider()
    todos_revisados = (
        all(
            selecciones.get(_identificador_mueble(m), {}).get("check", False)
            for m in muebles_normales
        )
        and all(
            st.session_state.get("rodapie_grupos", {}).get(g["key"], {}).get("check", False)
            for g in grupos_rodapie
        )
    )
    if st.button(
        "Continuar al Paso 2",
        type="primary",
        disabled=not todos_revisados,
        help=(
            None
            if todos_revisados
            else "Marca todos los muebles como revisados para continuar."
        ),
    ):
        st.session_state.pantalla = PANTALLA_PASO_2
        st.session_state.pedido_paso_2 = None  # fuerza recálculo en app.py
        st.rerun()


def _bloque_configuracion(mueble: dict) -> list[tuple[str, str]]:
    """Pares (etiqueta, valor) del bloque Configuración — Paso 1 (campos CSV brutos)."""
    items: list[tuple[str, str]] = []
    name = (mueble.get("Name") or "").strip()
    if name in CODIGOS_MUEBLE_ABIERTO:
        color_abierto = _ui_color_mueble_abierto(mueble.get("Color del mueble abierto", ""))
        if color_abierto:
            items.append(("Acabado del mueble abierto", color_abierto))
        rodapie = _ui_rodapie(mueble.get("C_Rodapietext", ""))
        if rodapie and rodapie != "—":
            items.append(("Rodapié", rodapie))
        elif name in CODIGOS_PS_SEGUN_RODAPIE:
            items.append(("Rodapié", "(vacío = suspendido)"))
    else:
        apertura = _ui_apertura(mueble.get("Apertura", ""))
        if apertura and apertura != "—":
            items.append(("Apertura", apertura))
        gama = _ui_gama(mueble.get("D_Gama", ""))
        color = _ui_color_frente(mueble.get("ColorFrente", ""))
        gama_color = " ".join(p for p in (gama, color) if p)
        if gama_color:
            items.append(("Gama y color frente", gama_color))
        color_int = _ui_color_interior(mueble.get("Color del interior", ""))
        if color_int and color_int != "—":
            items.append(("Color interior", color_int))
        tirador = _ui_tirador(mueble.get("Tirador", ""))
        if tirador:
            col_t = _ui_color_tirador(mueble, tirador)
            items.append(("Tirador", " ".join(p for p in (tirador, col_t) if p)))
        rodapie = _ui_rodapie(mueble.get("C_Rodapietext", ""))
        if rodapie and rodapie != "—":
            items.append(("Rodapié", rodapie))
    return items


def _bloque_configuracion_c(entrada: dict) -> list[tuple[str, str]]:
    """Pares (etiqueta, valor) del bloque Configuración — Paso 2 (campos de entrada, ya en UI)."""
    items: list[tuple[str, str]] = []
    code = (entrada.get("Código mueble") or "").strip()
    posicion_c2 = (entrada.get("Posición") or "").strip().upper()
    if code in CODIGOS_MUEBLE_ABIERTO:
        color_abierto = (entrada.get("Acabado del mueble abierto") or "").strip()
        if color_abierto:
            items.append(("Acabado del mueble abierto", color_abierto))
        rodapie = (entrada.get("Rodapié") or "").strip()
        if rodapie:
            items.append(("Rodapié", rodapie))
        if posicion_c2 == "S":
            items.append(("Posición", "de pared"))
        elif posicion_c2 == "P":
            items.append(("Posición", "con patas"))
    elif code in CODIGOS_TAPETA:
        gama    = (entrada.get("Gama del frente") or "").strip()
        acabado = _ui_color_frente(entrada.get("Acabado") or "")   # quita sufijo gama
        gama_acabado = " ".join(p for p in (gama, acabado) if p)
        if gama_acabado:
            items.append(("Gama y acabado", gama_acabado))
        if posicion_c2 == "H":
            items.append(("Posición", "de pared"))
    elif code in CODIGOS_JOUE:
        gama    = (entrada.get("Gama del frente") or "").strip()
        acabado = _ui_color_frente(entrada.get("Acabado") or "")
        gama_acabado = " ".join(p for p in (gama, acabado) if p)
        if gama_acabado:
            items.append(("Acabado del panel", gama_acabado))
    elif code in CODIGOS_ENCIMERA:
        cat_enc  = (_cargar_catalogo() or {}).get(code) or {}
        gama_cat = (cat_enc.get("gama") or (entrada.get("Gama del frente") or "")).strip()
        acabado  = _ui_color_frente(entrada.get("Acabado") or "")
        gama_acabado = " ".join(p for p in (gama_cat, acabado) if p)
        if gama_acabado:
            items.append(("Acabado", gama_acabado))
    elif code in CODIGOS_RODAPIE:
        gama    = (entrada.get("Gama del frente") or "").strip()
        acabado = _ui_color_frente(entrada.get("Acabado") or "")
        gama_acabado = " ".join(p for p in (gama, acabado) if p)
        if gama_acabado:
            items.append(("Acabado", gama_acabado))
        cantidad = (entrada.get("Cantidad") or "").strip()
        if cantidad:
            try:
                n = int(cantidad)
                items.append(("Cantidad", f"{n} pieza{'s' if n != 1 else ''}"))
            except ValueError:
                items.append(("Cantidad", cantidad))
    else:
        apertura = (entrada.get("Apertura") or "").strip()
        if apertura:
            items.append(("Apertura", apertura))
        gama  = (entrada.get("Gama del frente")   or "").strip()
        color = (entrada.get("Acabado del frente") or "").strip()
        gama_color = " ".join(p for p in (gama, color) if p)
        if gama_color:
            items.append(("Gama y color frente", gama_color))
        color_int = (entrada.get("Color interior") or "").strip()
        if color_int:
            items.append(("Color interior", color_int))
        tirador = (entrada.get("Tirador") or "").strip()
        if tirador:
            col_t = (entrada.get("Color tirador") or "").strip()
            items.append(("Tirador", " ".join(p for p in (tirador, col_t) if p)))
        rodapie = (entrada.get("Rodapié") or "").strip()
        if rodapie:
            items.append(("Rodapié", rodapie))
    return items


def _bloque_dimensiones(mueble: dict, catalogo: dict) -> list[tuple[str, str]]:
    """Pares (etiqueta, valor) del bloque Dimensiones — Paso 1 (campos CSV brutos)."""
    items: list[tuple[str, str]] = []
    name = (mueble.get("Name") or "").strip()
    entry = catalogo.get(name) or {}

    ancho_csv = _ui_ancho(mueble)
    if ancho_csv and ancho_csv != "—":
        items.append(("Ancho", ancho_csv))
    elif entry.get("ancho_mm"):
        items.append(("Ancho", f"{entry['ancho_mm']} mm"))
    elif "ancho_variable" in entry:
        av = entry["ancho_variable"]
        items.append(("Ancho", f"variable ({av['min']}–{av['max']} mm)"))

    alto = entry.get("alto_mm")
    if alto:
        items.append(("Alto", f"{alto} mm"))
    elif "alto_variable" in entry:
        av = entry["alto_variable"]
        items.append(("Alto", f"variable ({av['min']}–{av['max']} mm)"))

    fondo = entry.get("fondo_mm")
    if fondo is not None:
        items.append(("Fondo", f"{fondo} mm"))

    return items


def _fmt_mm(val: str) -> str:
    """Normaliza un valor de dimensión a 'NNN mm'.

    Acepta '600 mm', '600mm', '600', 750, etc. y devuelve siempre 'NNN mm'.
    Si no se puede parsear devuelve el valor tal cual.
    """
    v = str(val).strip()
    v_num = v.lower().removesuffix("mm").strip()
    try:
        return f"{int(float(v_num.replace(',', '.')))} mm"
    except ValueError:
        return v


def _bloque_dimensiones_c(entrada: dict, catalogo: dict) -> list[tuple[str, str]]:
    """Pares (etiqueta, valor) del bloque Dimensiones — Paso 2."""
    items: list[tuple[str, str]] = []
    code  = (entrada.get("Código mueble") or "").strip()
    entry = catalogo.get(code) or {}

    if str(entrada.get("Reducción de ancho", "False")).strip() == "True":
        ancho_red = (entrada.get("Ancho reducido") or "").strip()
        items.append(("Ancho", f"Reducción ({_fmt_mm(ancho_red)})"))
    elif entry.get("ancho_mm"):
        items.append(("Ancho", f"{entry['ancho_mm']} mm"))
    else:
        ancho_csv = (entrada.get("Ancho CSV") or "").strip()
        if ancho_csv:
            items.append(("Ancho", _fmt_mm(ancho_csv)))

    if code in CODIGOS_ENCIMERA:
        # Para encimeras: "Alto CSV" es el fondo físico. El espesor es fijo.
        alto_csv = (entrada.get("Alto CSV") or "").strip()
        if alto_csv:
            items.append(("Fondo", _fmt_mm(alto_csv)))
        espesor = entry.get("espesor_mm")
        if espesor is not None:
            items.append(("Espesor", f"{espesor} mm"))
    elif entry.get("alto_mm"):
        items.append(("Alto", f"{entry['alto_mm']} mm"))
    else:
        alto_csv = (entrada.get("Alto CSV") or "").strip()
        if alto_csv:
            items.append(("Alto", _fmt_mm(alto_csv)))

    if code not in CODIGOS_ENCIMERA:
        fondo = entry.get("fondo_mm")
        if fondo is not None:
            etiqueta_fondo = "Espesor" if code in CODIGOS_TAPETA or code in CODIGOS_RODAPIE or code in CODIGOS_JOUE else "Fondo"
            items.append((etiqueta_fondo, f"{fondo} mm"))

    return items


def _render_lista_items(items: list[tuple[str, str]]) -> None:
    for etiqueta, valor in items:
        st.markdown(f"- **{etiqueta}:** {valor}")


def _render_card_resumen(entrada: dict, catalogo: dict) -> None:
    """Card-resumen NO plegable de un mueble en el Paso 2 (CLAUDE.md §7).

    `entrada` es el dict de entrada extendido por modulo_c (ya en UI):
    'Código mueble', 'Gama del frente', 'Tirador'... + 'opciones_adicionales',
    'codigos_sg', 'p_item', 'avisos_c'.
    """
    code      = (entrada.get("Código mueble") or "").strip()
    cat_entry = catalogo.get(code) or {}
    nombre    = code or "—"
    des       = (cat_entry.get("designaciones") or {}).get("es", "")
    summary   = (entrada.get("Summary") or "").strip()

    es_tapeta      = code in CODIGOS_TAPETA
    es_encimera    = code in CODIGOS_ENCIMERA
    es_rodapie     = code in CODIGOS_RODAPIE
    es_rodapie_sg  = code in CODIGOS_RODAPIE_SG
    es_abierto     = code in CODIGOS_MUEBLE_ABIERTO
    es_joue        = code in CODIGOS_JOUE

    # Título: rodapiés SG → código · Rodapié · Gama Acabado
    if es_rodapie_sg:
        gama_t    = (entrada.get("Gama del frente") or "").strip()
        acabado_t = _ui_color_frente(entrada.get("Acabado") or "")
        ga_str    = " ".join(p for p in (gama_t, acabado_t) if p)
        titulo = f"### {nombre}  ·  Rodapié"
        if ga_str:
            titulo += f"  ·  {ga_str}"
    else:
        prefijo = f"**{summary}** · " if summary else ""
        titulo = f"### {prefijo}{nombre}"
        if des:
            titulo += f"  ·  {des}"
    img_path = _imagen_mueble(code, entrada.get("Posición") or "")

    # Tapetas, rodapiés y joues: el color llega en "Acabado", no en "Acabado del frente"
    if es_tapeta or es_rodapie or es_encimera:
        color_frente    = _ui_color_frente(entrada.get("Acabado") or "")
        etiqueta_frente = "Acabado"
    elif es_joue:
        gama_j          = (entrada.get("Gama del frente") or "").strip()
        acabado_j       = _ui_color_frente(entrada.get("Acabado") or "")
        color_frente    = " ".join(p for p in (gama_j, acabado_j) if p)
        etiqueta_frente = "Acabado del panel"
    else:
        color_frente    = (entrada.get("Acabado del frente") or "").strip()
        etiqueta_frente = "Frente"
    color_interior = (entrada.get("Color interior") or "").strip()

    with st.container(border=True):
        st.markdown(titulo)

        if _es_desmontado(code):
            st.info("Este mueble siempre se envía desmontado al cliente.", icon="ℹ️")

        col_img, col_config, col_dims, col_opc = st.columns([1, 2, 1, 2])

        with col_img:
            if img_path:
                st.image(str(img_path), width=229)
            if not es_abierto:
                _render_swatches_color(color_frente, color_interior, etiqueta_frente=etiqueta_frente)

        with col_config:
            config = _bloque_configuracion_c(entrada)
            if config:
                st.markdown("**Configuración**")
                _render_lista_items(config)

        with col_dims:
            dims = _bloque_dimensiones_c(entrada, catalogo)
            if dims:
                st.markdown("**Dimensiones**")
                _render_lista_items(dims)

        with col_opc:
            opc_adic = entrada.get("opciones_adicionales") or []

            # Datos del electrodoméstico (leídos directamente de entrada)
            marca      = (entrada.get("Marca electro")        or "").strip()
            referencia = (entrada.get("Referencia electro")   or "").strip()
            alto_e     = (entrada.get("Alto electro")         or "").strip()
            marca_2    = (entrada.get("Marca electro 2")      or "").strip()
            ref_2      = (entrada.get("Referencia electro 2") or "").strip()
            alto_e_2   = (entrada.get("Alto electro 2")       or "").strip()
            tiene_electro = bool(marca)

            if opc_adic or tiene_electro:
                st.markdown("**Opciones adicionales**")

                _sg_ui = _cargar_sg_a_ui()
                for entry_adic in opc_adic:
                    marcador  = " ⚙" if entry_adic.get("origen") == "automatico" else ""
                    etiqueta  = entry_adic.get("etiqueta") or ""
                    valor_raw = entry_adic.get("valor") or ""
                    etiqueta_ui = _sg_ui.get(etiqueta, etiqueta)
                    if valor_raw == "RL3":
                        ancho_r = (entrada.get("Ancho reducido") or "").strip()
                        ancho_r_num = ancho_r.replace("mm", "").strip()
                        valor_ui = f"{ancho_r_num} mm" if ancho_r_num else "Reducción de ancho"
                    else:
                        valor_ui = _sg_ui.get(valor_raw, valor_raw)
                    st.markdown(f"- **{etiqueta_ui}:** {valor_ui}{marcador}")
                if any(e.get("origen") == "automatico" for e in opc_adic):
                    st.caption("⚙ Forzado automáticamente por reglas")

                if tiene_electro:
                    def _linea_electro(m, r, al, label):
                        if r:
                            partes = " · ".join(p for p in (m, r) if p)
                        else:
                            altura = f"{al} mm" if al else ""
                            partes = " · ".join(p for p in (m, altura) if p)
                        st.markdown(f"- **{label}:** {partes}")
                    lbl1 = "Electrodoméstico 1" if marca_2 else "Electrodoméstico"
                    _linea_electro(marca, referencia, alto_e, lbl1)
                    if marca_2:
                        _linea_electro(marca_2, ref_2, alto_e_2, "Electrodoméstico 2")

        # Espaciador para dar margen inferior igual al superior dentro del borde
        st.markdown('<div style="margin-bottom:8px"></div>', unsafe_allow_html=True)


def _nombre_export_base() -> str:
    """Nombre base para los archivos de exportación (sin extensión)."""
    csv_origen = (st.session_state.get("csv_filename") or "").strip()
    if csv_origen.lower().endswith(".csv"):
        csv_origen = csv_origen[:-4]
    return csv_origen or "pedido_cubro"


# =============================================================================
# PDF - Exportar resumen del pedido
# =============================================================================

def generar_pdf_resumen(
    pedido: list[dict],
    catalogo: dict,
    csv_filename: str,
    fecha_export: str,
    idioma: str = 'es',
) -> bytes:
    '''Genera un PDF con el resumen completo del pedido.

    Replica los bloques Configuracion / Dimensiones / Opciones adicionales
    de cada card del Paso 2. Los elementos fluyen en paginas continuas.
    Imagen del elemento a la izquierda si existe.

    idioma: 'es' (default) o 'fr' para etiquetas y titulos de seccion en frances.
    Retorna los bytes del PDF generado.
    '''
    import struct
    from fpdf import FPDF

    MARGEN      = 12
    HEADER_H    = 8
    IMG_W       = 38
    IMG_GAP     = 5
    COL_LABEL_W = 44
    FONT_MAIN   = 'Helvetica'
    FSZ_HEADER  = 8
    FSZ_TITLE   = 11
    FSZ_SECTION = 9
    FSZ_BODY    = 8
    CELL_H      = 5.5
    GAP_SECTION = 3
    MIN_SPACE   = 45   # mm minimos antes de empezar un nuevo elemento

    sg_ui = _cargar_sg_a_ui()

    # Traducciones español -> frances para etiquetas y titulos de seccion
    _FR = {
        'Configuracion':                              'Configuration',
        'Dimensiones':                                'Dimensions',
        'Opciones adicionales':                       'Options additionnelles',
        'Apertura':                                   'Ouverture',
        'Gama y color frente':                        'Gamme et couleur facade',
        'Gama y acabado':                             'Gamme et finition',
        'Color interior':                             'Couleur interieur',
        'Tirador':                                    'Poignee',
        'Rodapié':                               'Plinthe',
        'Ancho':                                      'Largeur',
        'Alto':                                       'Hauteur',
        'Fondo':                                      'Profondeur',
        'Espesor':                                    'Epaisseur',
        'Cantidad':                                   'Quantite',
        'Acabado del mueble abierto':                 'Finition meuble ouvert',
        'Acabado del panel':                          'Finition panneau',
        'Acabado':                                    'Finition',
        'Electrodomestico':                           'Electromenager',
        'Electrodomestico 1':                         'Electromenager 1',
        'Electrodomestico 2':                         'Electromenager 2',
        'Ninguna':                                    'Aucune',
        '[auto] = Forzado automaticamente por reglas': '[auto] = Force automatiquement par les regles',
        '(i) Este mueble siempre se entrega desmontado.': '(i) Ce meuble est toujours livre demonte.',
        'Pag. ':                                      'Page ',
    }

    def _t(text):
        if idioma == 'fr':
            return _FR.get(text, text)
        return text

    class _PDF(FPDF):
        def __init__(self, csv_fn, fecha):
            super().__init__(orientation='P', unit='mm', format='A4')
            self._csv_fn = csv_fn
            self._fecha  = fecha
            self.set_margins(MARGEN, MARGEN + HEADER_H + 2, MARGEN)
            self.set_auto_page_break(auto=True, margin=15)

        def header(self):
            self.set_font(FONT_MAIN, 'I', FSZ_HEADER)
            self.set_y(6)
            self.cell(0, HEADER_H, self._csv_fn, align='L')
            self.set_y(6)
            self.cell(0, HEADER_H, self._fecha, align='R')
            self.set_y(MARGEN + HEADER_H)
            self.set_draw_color(200, 200, 200)
            self.line(MARGEN, MARGEN + HEADER_H - 1, 210 - MARGEN, MARGEN + HEADER_H - 1)

        def footer(self):
            self.set_y(-10)
            self.set_font(FONT_MAIN, 'I', 7)
            self.cell(0, 5, _t('Pag. ') + str(self.page_no()), align='C')

    def _safe(text):
        # Reemplaza caracteres Unicode fuera de latin-1 por equivalentes ASCII.
        subs = [
            ('‘', "'"), ('’', "'"),
            ('“', '"'), ('”', '"'),
            ('…', '...'),
            ('–', '-'), ('—', '-'),
            ('☐', '[ ]'), ('☑', '[x]'),
            ('⚠', '(!)'), ('ℹ', '(i)'),
            ('✅', '[OK]'), ('❌', '[X]'),
        ]
        for orig, repl in subs:
            text = text.replace(orig, repl)
        try:
            text.encode('latin-1')
        except UnicodeEncodeError:
            text = text.encode('latin-1', errors='replace').decode('latin-1')
        return text

    def _png_height_mm(path, w_mm):
        try:
            with path.open('rb') as f:
                f.read(16)
                w_px, h_px = struct.unpack('>II', f.read(8))
            if w_px:
                return w_mm * h_px / w_px
        except Exception:
            pass
        return w_mm

    def _render_tabla(pdf, items):
        for etiqueta, valor in items:
            pdf.set_font(FONT_MAIN, 'B', FSZ_BODY)
            pdf.cell(COL_LABEL_W, CELL_H, _safe(_t(etiqueta) + ':'), border=0)
            pdf.set_font(FONT_MAIN, '', FSZ_BODY)
            pdf.multi_cell(0, CELL_H, _safe(valor), border=0,
                           new_x='LMARGIN', new_y='NEXT')

    def _seccion(pdf, titulo):
        pdf.set_font(FONT_MAIN, 'B', FSZ_SECTION)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 6, _safe(_t(titulo)), border=0, fill=True,
                 new_x='LMARGIN', new_y='NEXT')
        pdf.ln(1)

    pdf = _PDF(_safe(csv_filename), _safe(fecha_export))
    pdf.add_page()

    for i, entrada in enumerate(pedido):
        code    = (entrada.get('Código mueble') or '').strip()
        cat_e   = catalogo.get(code) or {}
        des_raw = (cat_e.get('designaciones') or {})
        des     = des_raw.get(idioma) or des_raw.get('es') or ''
        summary = (entrada.get('Summary') or '').strip()

        es_rodapie_sg = code in CODIGOS_RODAPIE_SG

        # Separador entre elementos (excepto el primero)
        if i > 0:
            # Restaurar margen izquierdo (por si el elemento anterior tenia imagen)
            pdf.set_left_margin(MARGEN)
            remaining = (297 - 15) - pdf.get_y()
            if remaining < MIN_SPACE:
                pdf.add_page()
            else:
                pdf.ln(5)
                pdf.set_draw_color(160, 160, 160)
                pdf.line(MARGEN, pdf.get_y(), 210 - MARGEN, pdf.get_y())
                pdf.ln(5)

        # Titulo del elemento
        pdf.set_font(FONT_MAIN, 'B', FSZ_TITLE)
        if es_rodapie_sg:
            gama_t    = (entrada.get('Gama del frente') or '').strip()
            acabado_t = _ui_color_frente(entrada.get('Acabado') or '')
            ga_str    = ' - '.join(p for p in (gama_t, acabado_t) if p)
            titulo_pdf = code + ' - Rodapie'
            if ga_str:
                titulo_pdf += ' - ' + ga_str
        else:
            prefijo    = (summary + ' - ') if summary else ''
            titulo_pdf = prefijo + code
            if des:
                titulo_pdf += ' - ' + des

        pdf.cell(0, 7, _safe(titulo_pdf), new_x='LMARGIN', new_y='NEXT')

        desmontado_msg = '(i) Este mueble siempre se entrega desmontado.'
        if _es_desmontado(code):
            pdf.set_font(FONT_MAIN, 'I', FSZ_BODY)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 5, _safe(_t(desmontado_msg)),
                     new_x='LMARGIN', new_y='NEXT')
            pdf.set_text_color(0, 0, 0)

        pdf.ln(2)

        img_path = _imagen_mueble(code, entrada.get("Posición") or "")
        y_top    = pdf.get_y()
        img_h_mm = 0.0

        if img_path:
            img_h_mm = _png_height_mm(img_path, IMG_W)
            pdf.image(str(img_path), x=MARGEN, y=y_top, w=IMG_W)
            pdf.set_left_margin(MARGEN + IMG_W + IMG_GAP)
            pdf.set_x(MARGEN + IMG_W + IMG_GAP)

        config = _bloque_configuracion_c(entrada)
        if config:
            _seccion(pdf, 'Configuracion')
            _render_tabla(pdf, config)
            pdf.ln(GAP_SECTION)

        dims = _bloque_dimensiones_c(entrada, catalogo)
        if dims:
            _seccion(pdf, 'Dimensiones')
            _render_tabla(pdf, dims)
            pdf.ln(GAP_SECTION)

        opc_adic      = entrada.get('opciones_adicionales') or []
        marca         = (entrada.get('Marca electro')        or '').strip()
        referencia    = (entrada.get('Referencia electro')   or '').strip()
        alto_e        = (entrada.get('Alto electro')         or '').strip()
        marca_2       = (entrada.get('Marca electro 2')      or '').strip()
        ref_2         = (entrada.get('Referencia electro 2') or '').strip()
        alto_e_2      = (entrada.get('Alto electro 2')       or '').strip()
        tiene_electro = bool(marca)

        opc_items = []
        for entry_adic in opc_adic:
            marcador    = ' [auto]' if entry_adic.get('origen') == 'automatico' else ''
            etiqueta    = entry_adic.get('etiqueta') or ''
            valor_raw   = entry_adic.get('valor') or ''
            etiqueta_ui = sg_ui.get(etiqueta, etiqueta)
            if valor_raw == 'RL3':
                ancho_r     = (entrada.get('Ancho reducido') or '').strip()
                ancho_r_num = ancho_r.replace('mm', '').strip()
                valor_ui    = (ancho_r_num + ' mm') if ancho_r_num else 'Reduccion de ancho'
            else:
                valor_ui = sg_ui.get(valor_raw, valor_raw)
            opc_items.append((etiqueta_ui, valor_ui + marcador))

        electro_lbl = _t('Electrodomestico')
        if tiene_electro:
            lbl1 = (_t('Electrodomestico 1') if marca_2 else electro_lbl)
            if referencia:
                opc_items.append((lbl1, marca + ' - ' + referencia))
            else:
                alto_str = (alto_e + ' mm') if alto_e else ''
                opc_items.append((lbl1, ' - '.join(p for p in (marca, alto_str) if p)))
            if marca_2:
                if ref_2:
                    opc_items.append((_t('Electrodomestico 2'), marca_2 + ' - ' + ref_2))
                else:
                    alto_str_2 = (alto_e_2 + ' mm') if alto_e_2 else ''
                    opc_items.append((_t('Electrodomestico 2'),
                                      ' - '.join(p for p in (marca_2, alto_str_2) if p)))

        _seccion(pdf, 'Opciones adicionales')
        if opc_items:
            _render_tabla(pdf, opc_items)
            if any(e.get('origen') == 'automatico' for e in opc_adic):
                pdf.ln(1)
                pdf.set_font(FONT_MAIN, 'I', 7)
                pdf.set_text_color(100, 100, 100)
                auto_lbl = '[auto] = Forzado automaticamente por reglas'
                pdf.cell(0, 4, _safe(_t(auto_lbl)),
                         new_x='LMARGIN', new_y='NEXT')
                pdf.set_text_color(0, 0, 0)
        else:
            pdf.set_font(FONT_MAIN, 'I', FSZ_BODY)
            pdf.set_text_color(120, 120, 120)
            pdf.cell(0, CELL_H, _safe(_t('Ninguna')), new_x='LMARGIN', new_y='NEXT')
            pdf.set_text_color(0, 0, 0)

        avisos_c = entrada.get('avisos_c') or []
        if avisos_c:
            pdf.ln(2)
            pdf.set_font(FONT_MAIN, 'I', FSZ_BODY)
            pdf.set_text_color(160, 80, 0)
            for aviso in avisos_c:
                pdf.multi_cell(0, CELL_H, _safe('(!) ' + aviso),
                               new_x='LMARGIN', new_y='NEXT')
            pdf.set_text_color(0, 0, 0)

        # Restaurar margen y avanzar mas alla de la imagen si es necesario
        if img_path:
            pdf.set_left_margin(MARGEN)
            y_min = y_top + img_h_mm + 2
            if pdf.get_y() < y_min:
                pdf.set_y(y_min)

    return bytes(pdf.output())


def paso_2(pedido: list[dict] | None) -> None:
    """Paso 2 — Revisión final del pedido y exportación."""
    catalogo = _cargar_catalogo()

    st.header("Paso 2 — Revisión")

    if st.button("← Volver al Paso 1"):
        st.session_state.pantalla = PANTALLA_PASO_1
        st.session_state.pop("_export_json", None)
        st.rerun()

    if not pedido:
        st.error("No hay pedido que revisar. Vuelve al Paso 1.")
        return

    st.success(f"Pedido listo: **{len(pedido)} muebles** configurados.")

    for item in pedido:
        _render_card_resumen(item, catalogo)

    st.divider()

    def _generar_zip_export():
        import io as _io
        import zipfile as _zf
        from datetime import datetime as _dt
        csv_fn = st.session_state.get('csv_filename') or 'pedido'
        fecha  = _dt.now().strftime('%d/%m/%Y %H:%M')
        nombre = _nombre_export_base()
        buf = _io.BytesIO()
        with _zf.ZipFile(buf, 'w', _zf.ZIP_DEFLATED) as zfile:
            import modulo_c as _mc
            json_bytes = json.dumps(
                _mc.generar_json_pedido(pedido), ensure_ascii=False, indent=2
            ).encode('utf-8')
            zfile.writestr(nombre + '_pedido.json', json_bytes)
            pdf_es = generar_pdf_resumen(pedido, catalogo, csv_fn, fecha, idioma='es')
            zfile.writestr(nombre + '_resumen_es.pdf', pdf_es)
            pdf_fr = generar_pdf_resumen(pedido, catalogo, csv_fn, fecha, idioma='fr')
            zfile.writestr(nombre + '_resumen_fr.pdf', pdf_fr)
        return buf.getvalue()

    nombre = _nombre_export_base()
    st.download_button(
        '\U0001f4e6 Exportar pedido JSON',
        data=_generar_zip_export(),
        file_name=nombre + '.zip',
        mime='application/zip',
        type='primary',
        use_container_width=True,
    )
