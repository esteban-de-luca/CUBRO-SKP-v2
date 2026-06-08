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
    "op_126":                "Datos del electrodoméstico encastrado. Marca y Tipo son obligatorios; rellena Referencia o Altura (al menos uno de los dos).",
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
_CATALOGO_PATH = pathlib.Path(__file__).parent / "data" / "catalogo.json"
_MAPEOS_SKP_UI_SG_PATH = pathlib.Path(__file__).parent / "data" / "mapeos_SKP_UI_SG.yaml"
_OPCIONES_MUEBLE_PATH = pathlib.Path(__file__).parent / "data" / "opciones_mueble.yaml"
_REGLAS_PATH = pathlib.Path(__file__).parent / "data" / "reglas.yaml"
_IMAGENES_PATH = pathlib.Path(__file__).parent / "data" / "imagenes_mueble.yaml"
_ASSETS_MUEBLES = pathlib.Path(__file__).parent / "assets" / "muebles"
_COLORES_PATH = pathlib.Path(__file__).parent / "data" / "colores_mueble.yaml"
_ASSETS_COLORES = pathlib.Path(__file__).parent / "assets" / "colores"
_ASSETS_OPCIONES = pathlib.Path(__file__).parent / "assets" / "opciones"


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


def _imagen_mueble(code: str) -> pathlib.Path | None:
    """Devuelve la Path al PNG del mueble si existe, o None.

    Usa longest-prefix-first: el primer prefijo (de mayor a menor longitud)
    que coincida con el inicio del código de mueble determina la imagen.
    """
    if not code:
        return None
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


def _render_swatches_color(color_frente: str, color_interior: str) -> None:
    """Muestra swatches de color apilados verticalmente (frente primero, interior debajo).

    Cada fila: imagen cuadrada 36 px a la izquierda + etiqueta a la derecha,
    renderizado con HTML inline para evitar problemas de columnas anidadas en Streamlit.
    Se omiten los colores sin imagen disponible.
    """
    colores = _cargar_colores()
    items: list[tuple[str, pathlib.Path]] = []

    fn_frente = (colores.get("frente") or {}).get(color_frente)
    if fn_frente:
        p = _ASSETS_COLORES / fn_frente
        if p.exists():
            items.append((f"Frente: {color_frente}", p))

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
# Builder: Paso 1 → Módulo C (contrato Hipótesis B, 2026-05-11).
# Genera una lista plana de 23 columnas por mueble. Mismas keys para todos
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
    """Construye la entrada para el Módulo C (23 columnas por mueble).

    Aplica las transformaciones CSV→UI de CLAUDE.md §8, incluyendo el caso
    Trasera=Laca → color del frente (igual que en la cabecera de cards).
    Las opcionales no marcadas o no aplicables se exportan como "False" / "".
    """
    entrada: list[dict] = []
    for mueble in muebles:
        clave = _identificador_mueble(mueble)
        opcionales = (selecciones.get(clave, {}) or {}).get("opcionales", {}) or {}

        ancho_raw = (mueble.get("Ancho") or "").strip()
        reduccion = ancho_raw == _ANCHO_REDUCCION_RAW
        ancho_reducido = (
            (mueble.get("Ancho reducido") or "").strip() if reduccion else ""
        )

        tirador_ui = _ui_tirador(mueble.get("Tirador", ""))

        op_126_raw = opcionales.get("op_126")
        op_126 = op_126_raw if isinstance(op_126_raw, dict) else {}
        op_126_2_raw = opcionales.get("op_126_2")
        op_126_2 = op_126_2_raw if isinstance(op_126_2_raw, dict) else {}

        fila: dict[str, str] = {
            "Código mueble": (mueble.get("Name") or "").strip(),
            "Descripción": _designacion(mueble, catalogo),
            "Posición": "",  # placeholder reservado, lo rellenara C en el futuro
            "Summary": (mueble.get("Summary") or "").strip(),  # identificador SKP → p_item_origin_id
            "Apertura": _normalizar_vacio(_ui_apertura(mueble.get("Apertura", ""))),
            "Gama del frente": _ui_gama(mueble.get("D_Gama", "")),
            "Acabado del frente": _ui_color_frente(mueble.get("ColorFrente", "")),
            "Color interior": _normalizar_vacio(
                _ui_color_interior(mueble.get("Color del interior", ""))
            ),
            "Tirador": tirador_ui,
            "Color tirador": _ui_color_tirador(mueble, tirador_ui),
            "Rodapié": _normalizar_vacio(
                _ui_rodapie(mueble.get("C_Rodapietext", ""))
            ),
            "Reducción de ancho": _bool_str(reduccion),
            "Ancho reducido": ancho_reducido,
            "Sin mecanizado": _bool_str(opcionales.get("op_121", False)),
            "Cubos de basura": _export_op_207(opcionales.get("op_207_opcional", False)),
            "Recorte LED": _bool_str(opcionales.get("op_220", False)),
            "Sensor para mando LED": _sensor_led_export(opcionales.get("op_222")),
            "Cajón interior": _bool_str(opcionales.get("op_223", False)),
            "Mueble de caldera": _bool_str(opcionales.get("op_227", False)),
            "Sin encolar": _bool_str(opcionales.get("op_700_opcional", False)),
            "Marca electro":        str(op_126.get("marca", "")).strip(),
            "Referencia electro":   str(op_126.get("referencia", "")).strip(),
            "Tipo electro":         str(op_126.get("tipo", "")).strip(),
            "Ancho electro":        str(op_126.get("ancho", "")).strip(),
            "Alto electro":         str(op_126.get("alto", "")).strip(),
            "Fondo electro":        str(op_126.get("fondo", "")).strip(),
            "Marca electro 2":      str(op_126_2.get("marca", "")).strip(),
            "Referencia electro 2": str(op_126_2.get("referencia", "")).strip(),
            "Tipo electro 2":       str(op_126_2.get("tipo", "")).strip(),
            "Ancho electro 2":      str(op_126_2.get("ancho", "")).strip(),
            "Alto electro 2":       str(op_126_2.get("alto", "")).strip(),
            "Fondo electro 2":      str(op_126_2.get("fondo", "")).strip(),
        }
        entrada.append(fila)
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
    apertura      = _ui_apertura(mueble.get("Apertura", ""))
    ancho         = _ui_ancho(mueble)
    color_interior = _ui_color_interior(mueble.get("Color del interior", ""))
    rodapie       = _ui_rodapie(mueble.get("C_Rodapietext", ""))

    name  = (mueble.get("Name") or "").strip()
    entry = catalogo.get(name) or {}

    # Alto: LenZ del CSV (altura real en SketchUp); fallback al catálogo
    len_z_raw = (mueble.get("LenZ") or "").strip()
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

    st.markdown(
        f"**Apertura:** {apertura}  ·  "
        f"**Ancho:** {ancho}  ·  "
        f"**Alto:** {alto_str}  ·  "
        f"**Fondo:** {fondo_str}  ·  "
        f"**Color interior:** {color_interior}  ·  "
        f"**Rodapié:** {rodapie}"
    )


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

    # op_700 — aplica a todos salvo los no_aplica.
    # Los forzadas (campanas HH*) también se incluyen: se muestran desactivados y marcados.
    meta_700 = interfaz.get("op_700_opcional") or {}
    if "op_700_opcional" in interfaz and name not in (meta_700.get("excluidos") or []):
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
    # "tipo" NO está aquí: se gestiona siempre vía tipo_auto (oculto) o tipo_opciones (selectbox).
    # "ancho"/"alto"/"fondo" solo aparecen cuando no hay referencia (Case B).
}

# Validación de formato por subcampo de op_126.
# marca      → solo letras (incluye acentos y espacio para nombres de marca compuestos)
# referencia → alfanumérico + separadores habituales en referencias de producto
# ancho/alto/fondo → solo dígitos (valor en mm)
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
    "ancho": {
        "patron":  re.compile(r"^\d+$"),
        "error":   "Solo se admiten números enteros (en mm)",
        "ejemplo": "Ancho del hueco en mm",
    },
    "alto": {
        "patron":  re.compile(r"^\d+$"),
        "error":   "Solo se admiten números enteros (en mm)",
        "ejemplo": "Alto del hueco en mm",
    },
    "fondo": {
        "patron":  re.compile(r"^\d+$"),
        "error":   "Solo se admiten números enteros (en mm)",
        "ejemplo": "Fondo del hueco en mm",
    },
}


def _op_126_completo(valor, meta: dict | None = None) -> bool:
    """Valida que el bloque op_126 esté completo según la meta de la variante.

    - tipo_auto   → tipo siempre satisfecho (fijo por mueble, no editable).
    - tipo_opciones → el usuario debe haber seleccionado una opción del desplegable.
    - Subcampos   → marca siempre requerida; ref/altura según los presentes en la variante.
    """
    if not isinstance(valor, dict):
        return False
    if meta is None:
        meta = {}

    subcampos     = meta.get("subcampos") or _SUBCAMPOS_OP_126_DEFAULT
    tipo_auto     = meta.get("tipo_auto")
    tipo_opciones = meta.get("tipo_opciones")

    marca = str(valor.get("marca", "")).strip()
    if not marca:
        return False

    # Tipo: auto → siempre OK; opciones → debe estar en la lista
    if tipo_auto:
        pass  # satisfecho automáticamente
    elif tipo_opciones:
        if str(valor.get("tipo", "")).strip() not in tipo_opciones:
            return False

    # Caso A (tiene_referencia=True): Referencia obligatoria
    # Caso B (tiene_referencia=False): Ancho + Alto + Fondo los tres obligatorios
    tiene_referencia = bool(valor.get("tiene_referencia", True))
    if tiene_referencia:
        if not str(valor.get("referencia", "")).strip():
            return False
    else:
        if not (
            str(valor.get("ancho", "")).strip()
            and str(valor.get("alto", "")).strip()
            and str(valor.get("fondo", "")).strip()
        ):
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
    clave: str, sufijo: str, tipo_auto, tipo_opciones, prev: dict, tipo_fallback: str = ""
) -> dict:
    """Renderiza los campos de un electrodoméstico y retorna el nuevo valor.

    Siempre muestra radio Sí/No para elegir entre referencia (Caso A) o
    dimensiones (Caso B).
    tipo_fallback: tipo implícito cuando el mueble no tiene tipo seleccionable
    (p.ej. "Campana" para HH). Se guarda en el dict pero no se muestra en UI.
    """
    key = f"_{sufijo}" if sufijo else ""
    nuevo: dict = {}

    # ── Tipo ─────────────────────────────────────────────────────────────────
    if tipo_auto:
        nuevo["tipo"] = tipo_auto
    elif tipo_opciones:
        prev_tipo = prev.get("tipo", tipo_opciones[0])
        if prev_tipo not in tipo_opciones:
            prev_tipo = tipo_opciones[0]
        nuevo["tipo"] = st.selectbox(
            "Tipo",
            options=tipo_opciones,
            index=tipo_opciones.index(prev_tipo),
            key=f"op_126_tipo{key}_{clave}",
            help="ej. Horno, Microondas, Placa, Frigorífico",
        )
    elif tipo_fallback:
        # Sin tipo seleccionable (campana): tipo implícito, no se muestra en UI
        nuevo["tipo"] = tipo_fallback

    # ── Marca ─────────────────────────────────────────────────────────────────
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

    # ── Radio ─────────────────────────────────────────────────────────────
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
        nuevo["ancho"] = nuevo["alto"] = nuevo["fondo"] = ""
    else:
        nuevo["referencia"] = ""
        for dim_key, dim_label in [("ancho", "Ancho (mm)"), ("alto", "Alto (mm)"), ("fondo", "Fondo (mm)")]:
            regla_dim = _VALIDACION_OP_126[dim_key]
            dim_val = st.text_input(
                dim_label,
                value=prev.get(dim_key, ""),
                key=f"op_126_{dim_key}{key}_{clave}",
                help=regla_dim["ejemplo"],
            )
            if dim_val.strip() and not regla_dim["patron"].match(dim_val.strip()):
                st.caption(f"⚠️ {regla_dim['error']} ({regla_dim['ejemplo']})")
            nuevo[dim_key] = dim_val

    return nuevo


def _control_electrodomestico_op_126(
    clave: str, meta: dict, opcionales: dict, selecciones: dict
) -> None:
    tipo_auto     = meta.get("tipo_auto")
    tipo_opciones = meta.get("tipo_opciones")
    doble         = bool(meta.get("doble"))
    # Tipo implícito para muebles sin tipo seleccionable (p.ej. campana → "Campana")
    tipo_fallback = "" if (tipo_auto or tipo_opciones) else (meta.get("etiqueta") or "")

    st.markdown(f"**{meta.get('ui') or meta.get('etiqueta') or 'Electrodoméstico'}**")
    if _TOOLTIPS_OPCIONALES.get("op_126"):
        st.caption(_TOOLTIPS_OPCIONALES["op_126"])

    if doble:
        # ── Dos slots: electro 1 (inferior) y electro 2 (superior) ───────────
        prev_1 = opcionales.get("op_126")   if isinstance(opcionales.get("op_126"),   dict) else {}
        prev_2 = opcionales.get("op_126_2") if isinstance(opcionales.get("op_126_2"), dict) else {}
        st.caption("Electrodoméstico 1 (inferior)")
        nuevo_1 = _render_bloque_electro(clave, "1", tipo_auto, tipo_opciones, prev_1, tipo_fallback)
        st.caption("Electrodoméstico 2 (superior)")
        nuevo_2 = _render_bloque_electro(clave, "2", tipo_auto, tipo_opciones, prev_2, tipo_fallback)
        if nuevo_1 != prev_1 or nuevo_2 != prev_2:
            opcionales["op_126"]   = nuevo_1
            opcionales["op_126_2"] = nuevo_2
            _registrar_edicion(clave, selecciones)
            st.rerun()
    else:
        # ── Un solo slot ──────────────────────────────────────────────────────
        prev = opcionales.get("op_126") if isinstance(opcionales.get("op_126"), dict) else {}
        nuevo = _render_bloque_electro(clave, "", tipo_auto, tipo_opciones, prev, tipo_fallback)
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


def _render_cabecera_global(muebles: list[dict], selecciones: dict) -> None:
    """Contador en vivo + acciones globales (CLAUDE.md §7)."""
    total = len(muebles)
    revisados = sum(
        1 for m in muebles
        if selecciones.get(_identificador_mueble(m), {}).get("check")
    )
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


def paso_1(muebles: list[dict]) -> None:
    """Paso 1 — Cards plegables, una por mueble, en orden del CSV."""
    catalogo = _cargar_catalogo()
    interfaz = _cargar_interfaz()
    selecciones = st.session_state.selecciones_paso_1
    # Expandidos por defecto: inicializar con todas las claves si aún no existe.
    if "paso_1_abiertos" not in st.session_state:
        st.session_state["paso_1_abiertos"] = {
            _identificador_mueble(m) for m in muebles
        }
    abiertos = st.session_state["paso_1_abiertos"]

    # Inicializa estado y pre-check para todos los muebles antes de pintar la
    # cabecera (los contadores deben verlos ya inicializados).
    for mueble in muebles:
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

        # Inicializar tipo_auto en op_126 aunque el usuario no abra la card.
        # Garantiza que "Tipo electro" llegue correctamente a construir_entrada_modulo_c.
        if "op_126" in aplicables:
            meta_126 = _meta_op_126(name, interfaz)
            tipo_auto = meta_126.get("tipo_auto")
            if tipo_auto:
                op126_val = opcionales.get("op_126")
                if not isinstance(op126_val, dict):
                    opcionales["op_126"] = {"tipo": tipo_auto}
                elif not op126_val.get("tipo"):
                    op126_val["tipo"] = tipo_auto

    st.header("Paso 1 — Selección de opciones")
    _render_cabecera_global(muebles, selecciones)
    st.divider()

    solo_pendientes = bool(st.session_state.get("paso_1_solo_pendientes", False))
    a_mostrar = sorted(
        [
            m for m in muebles
            if not (
                solo_pendientes
                and selecciones.get(_identificador_mueble(m), {}).get("check")
            )
        ],
        key=lambda m: (m.get("Summary") or "").strip(),
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
                img_path = _imagen_mueble(name)
                meta_126 = _meta_op_126(name, interfaz)
                if img_path:
                    col_img, col_info = st.columns([1, 3])
                    with col_img:
                        st.image(str(img_path), width=229)
                        _render_swatches_color(
                            _ui_color_frente(mueble.get("ColorFrente", "")),
                            _ui_color_interior(mueble.get("Color del interior", "")),
                        )
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
                        else:
                            st.caption(
                                "Este mueble no tiene opciones adicionales configurables."
                            )
                else:
                    _bloque_informativo(mueble, catalogo)
                    _render_swatches_color(
                        _ui_color_frente(mueble.get("ColorFrente", "")),
                        _ui_color_interior(mueble.get("Color del interior", "")),
                    )
                    if aplicables:
                        tirador_code = str(mueble.get("Tirador") or "").strip()
                        _renderizar_opcionales(clave, name, tirador_code, aplicables, interfaz, selecciones)
                        if "op_126" in aplicables:
                            st.divider()
                            _control_electrodomestico_op_126(
                                clave, meta_126,
                                estado["opcionales"], selecciones,
                            )
                    else:
                        st.caption(
                            "Este mueble no tiene opciones opcionales aplicables. "
                            "Pre-marcado como revisado."
                        )

                razon_bloqueo = None
                if "op_126" in aplicables:
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
        st.info("No hay muebles pendientes. Todo revisado.")

    # Botón final de avance al Paso 2 (CLAUDE.md §7: solo al final).
    st.divider()
    todos_revisados = all(
        selecciones.get(_identificador_mueble(m), {}).get("check", False)
        for m in muebles
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
    """Pares (etiqueta, valor) del bloque Configuración — Paso 2 (campos 23 columnas, ya en UI)."""
    items: list[tuple[str, str]] = []
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


def _bloque_dimensiones_c(entrada: dict, catalogo: dict) -> list[tuple[str, str]]:
    """Pares (etiqueta, valor) del bloque Dimensiones — Paso 2 (campos 23 columnas)."""
    items: list[tuple[str, str]] = []
    code  = (entrada.get("Código mueble") or "").strip()
    entry = catalogo.get(code) or {}

    if str(entrada.get("Reducción de ancho", "False")).strip() == "True":
        ancho_red = (entrada.get("Ancho reducido") or "").strip()
        items.append(("Ancho", f"Reducción ({ancho_red})"))
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


def _render_lista_items(items: list[tuple[str, str]]) -> None:
    for etiqueta, valor in items:
        st.markdown(f"- **{etiqueta}:** {valor}")


def _render_card_resumen(entrada: dict, catalogo: dict) -> None:
    """Card-resumen NO plegable de un mueble en el Paso 2 (CLAUDE.md §7).

    `entrada` tiene el formato 23 columnas extendido por modulo_c (ya en UI):
    'Código mueble', 'Gama del frente', 'Tirador'... + 'opciones_adicionales',
    'codigos_sg', 'p_item', 'avisos_c'.
    """
    code      = (entrada.get("Código mueble") or "").strip()
    cat_entry = catalogo.get(code) or {}
    nombre    = code or "—"
    des       = (cat_entry.get("designaciones") or {}).get("es", "")
    summary   = (entrada.get("Summary") or "").strip()

    prefijo = f"**{summary}** · " if summary else ""
    titulo = f"### {prefijo}{nombre}"
    if des:
        titulo += f"  ·  {des}"

    img_path = _imagen_mueble(code)

    color_frente   = (entrada.get("Acabado del frente") or "").strip()
    color_interior = (entrada.get("Color interior") or "").strip()

    with st.container(border=True):
        st.markdown(titulo)

        col_img, col_config, col_dims, col_opc = st.columns([1, 2, 1, 2])

        with col_img:
            if img_path:
                st.image(str(img_path), width=229)
            _render_swatches_color(color_frente, color_interior)

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
            tipo       = (entrada.get("Tipo electro")         or "").strip()
            ancho_e    = (entrada.get("Ancho electro")        or "").strip()
            alto_e     = (entrada.get("Alto electro")         or "").strip()
            fondo_e    = (entrada.get("Fondo electro")        or "").strip()
            marca_2    = (entrada.get("Marca electro 2")      or "").strip()
            ref_2      = (entrada.get("Referencia electro 2") or "").strip()
            tipo_2     = (entrada.get("Tipo electro 2")       or "").strip()
            ancho_e_2  = (entrada.get("Ancho electro 2")      or "").strip()
            alto_e_2   = (entrada.get("Alto electro 2")       or "").strip()
            fondo_e_2  = (entrada.get("Fondo electro 2")      or "").strip()
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
                    def _linea_electro(m, r, t, a, al, f, label):
                        if r:
                            partes = " · ".join(p for p in (m, r) if p)
                        else:
                            dims = f"{a}×{al}×{f} mm" if (a and al and f) else ""
                            partes = " · ".join(p for p in (m, t, dims) if p)
                        st.markdown(f"- **{label}:** {partes}")
                    lbl1 = "Electrodoméstico 1" if marca_2 else "Electrodoméstico"
                    _linea_electro(marca, referencia, tipo, ancho_e, alto_e, fondo_e, lbl1)
                    if marca_2:
                        _linea_electro(marca_2, ref_2, tipo_2, ancho_e_2, alto_e_2, fondo_e_2, "Electrodoméstico 2")

        # Espaciador para dar margen inferior igual al superior dentro del borde
        st.markdown('<div style="margin-bottom:8px"></div>', unsafe_allow_html=True)


def _nombre_export_base() -> str:
    """Nombre base para los archivos de exportación (sin extensión)."""
    csv_origen = (st.session_state.get("csv_filename") or "").strip()
    if csv_origen.lower().endswith(".csv"):
        csv_origen = csv_origen[:-4]
    return csv_origen or "pedido_cubro"


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

    # ── Exportar pedido ───────────────────────────────────────────────────────
    if st.button("📦 Exportar pedido JSON", type="primary"):
        import modulo_c as _mc  # importación local para mantener modulo_b autónomo
        st.session_state["_export_json"] = json.dumps(
            _mc.generar_json_pedido(pedido), ensure_ascii=False, indent=2
        ).encode("utf-8")

    if st.session_state.get("_export_json"):
        nombre = _nombre_export_base()
        st.download_button(
            "⬇ JSON de pedido",
            data=st.session_state["_export_json"],
            file_name=f"{nombre}_pedido.json",
            mime="application/json",
            use_container_width=True,
        )
