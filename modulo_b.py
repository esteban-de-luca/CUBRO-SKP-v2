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
    "op_121": "TODO: explicar cuándo seleccionar 'Sin mecanizado para tirador' (SPF).",
    "op_207_opcional": "TODO: explicar el sistema de cubos de basura integrado.",
    "op_220": "TODO: explicar el recorte para perfil LED y la diferencia respecto al sensor (op_222).",
    "op_222": "TODO: explicar el sensor para mando LED y cuándo conviene Derecha vs Izquierda.",
    "op_223": "TODO: explicar la utilidad del cajón interior y a qué muebles aplica.",
    "op_227": "TODO: explicar la opción 'Mueble de caldera' y sus implicaciones constructivas.",
    "op_700_opcional": "TODO: explicar 'Mueble sin encolar' (DEM) y los muebles excluidos.",
    "op_126": "Rellena los datos del electrodoméstico. Los campos mostrados son obligatorios.",
}

_TIRADORES_SIN_COLOR = {"Touch Latch", "Prise de main"}
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
def _cargar_interfaz() -> dict:
    """Construye el dict de interfaz desde mapeos_SKP_UI_SG.yaml, opciones_mueble.yaml y reglas.yaml.

    La fuente de verdad son los tres YAMLs anteriores. Ningún control ni lógica
    de UI cambia — solo la fuente de los datos.
    Cada key es un op_id con etiqueta, muebles/excluidos y subcampos según corresponda.
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

    # op_121 — solo etiqueta (los muebles los filtra opciones_mueble.yaml vía interfaz)
    if "op_121" in opc:
        entradas = opc["op_121"]
        interfaz["op_121"] = {
            "etiqueta": entradas[0].get("ui", "Sin mecanizado para tirador"),
        }

    # op_207_opcional — checkbox (P60/P90) para fregadero · radio (GM1/GM2) para despensa
    if "op_207_opcional" in opc:
        entradas_207 = opc["op_207_opcional"]
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
        etiquetas_ui = reglas_207.get("etiqueta_ui_por_mueble") or {}

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

    # op_700_opcional — etiqueta + excluidos (= excepciones de op_700 en opciones_mueble)
    if "op_700_opcional" in opc:
        entradas = opc["op_700_opcional"]
        op700 = op_mueble.get("op_700") or {}
        interfaz["op_700_opcional"] = {
            "etiqueta": entradas[0].get("ui", "Mueble sin encolar"),
            "excluidos": op700.get("excepciones") or [],
        }

    # op_126 — variante por mueble (base, placa, placa aspirante, frigorífico, LVV/LVD, campana…)
    # variantes_op_126 en opciones_mueble.yaml mapea variante_key → lista de muebles.
    # Los subcampos y etiquetas de cada variante vienen de mapeos_SKP_UI_SG.yaml.
    variantes_op_126 = op_mueble.get("variantes_op_126") or {}
    if variantes_op_126 or any(k.startswith("op_126") for k in opc):
        mueble_a_variante: dict = {}
        variantes_meta: dict = {}

        for variante_key, lista_muebles in variantes_op_126.items():
            meta_opc = opc.get(variante_key) or {}
            variantes_meta[variante_key] = {
                "etiqueta":      meta_opc.get("ui", "Electrodoméstico"),
                "subcampos":     meta_opc.get("subcampos") or {},
                "tipo_auto":     meta_opc.get("tipo_auto"),     # tipo fijo (p. ej. "Horno")
                "tipo_opciones": meta_opc.get("tipo_opciones"), # lista para desplegable
            }
            for mueble in (lista_muebles or []):
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
    """Clave única para st.session_state. Name SKP es siempre el original de SketchUp."""
    return (mueble.get("Name SKP") or mueble.get("Name") or "").strip()


# ----------------------------------------------------------------------------
# Builder: Paso 1 → Módulo C (contrato Hipótesis B, 2026-05-11).
# Genera una lista plana de 23 columnas por mueble. Mismas keys para todos
# los muebles aunque la opcional no aplique (en ese caso "False" / "").
# ----------------------------------------------------------------------------

def _export_op_207(valor) -> str:
    """Exporta el valor de op_207_opcional al contrato con el Módulo C.

    Muebles de fregadero (P60/P90): booleano → "True" / "False".
    Muebles de despensa AGM (GM1/GM2): el código SG directamente.
    """
    if isinstance(valor, str) and valor in ("GM1", "GM2"):
        return valor
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

        fila: dict[str, str] = {
            "Código mueble": (mueble.get("Name") or "").strip(),
            "Descripción": _designacion(mueble, catalogo),
            "Posición": "",  # placeholder reservado, lo rellenara C en el futuro
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
            "Marca electro": str(op_126.get("marca", "")).strip(),
            "Referencia electro": str(op_126.get("referencia", "")).strip(),
            "Altura electro": str(op_126.get("altura", "")).strip(),
            "Tipo electro": str(op_126.get("tipo", "")).strip(),
        }
        entrada.append(fila)
    return entrada


def _cabecera_card(mueble: dict, catalogo: dict, revisado: bool) -> str:
    """[check] · Name · Designación · Gama Color · Tirador Color (CLAUDE.md §7)."""
    check = "🟢" if revisado else "🔴"
    nombre = mueble.get("Name") or mueble.get("Name SKP") or "—"
    partes = [f"{check} {nombre}"]

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

    st.header("CSV validado correctamente")
    st.success(
        f"Los **{len(muebles)}** muebles han pasado las validaciones."
    )
    if st.button("Continuar al Paso 1", type="primary"):
        st.session_state.pantalla = PANTALLA_PASO_1
        st.rerun()


def _bloque_informativo(mueble: dict) -> None:
    """Línea inicial de la card abierta: Apertura · Ancho · Color interior · Rodapié."""
    apertura = _ui_apertura(mueble.get("Apertura", ""))
    ancho = _ui_ancho(mueble)
    color_interior = _ui_color_interior(mueble.get("Color del interior", ""))
    rodapie = _ui_rodapie(mueble.get("C_Rodapietext", ""))
    st.markdown(
        f"**Apertura:** {apertura}  ·  "
        f"**Ancho:** {ancho}  ·  "
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

    # op_121 aplica a todos los muebles (el control se muestra/oculta en función
    # del tirador, no del mueble — esa lógica está en _renderizar_opcionales).
    if "op_121" in interfaz:
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

    # op_700 — aplica a todos salvo los excluidos
    if "op_700_opcional" in interfaz and name not in (
        interfaz.get("op_700_opcional", {}).get("excluidos") or []
    ):
        aplicables.append("op_700_opcional")

    # op_126 — lista plana de muebles (BFT y AFS)
    if name in (interfaz.get("op_126", {}).get("muebles") or []):
        aplicables.append("op_126")

    return aplicables


def _registrar_edicion(clave: str, selecciones: dict) -> None:
    """Reset del check al editar y mantiene la card abierta tras el rerun."""
    selecciones[clave]["check"] = False
    st.session_state.pop(f"check_{clave}", None)
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
    "altura": "Altura",
    # "tipo" NO está aquí: se gestiona siempre vía tipo_auto (oculto) o tipo_opciones (selectbox),
    # nunca como campo de texto libre.
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

    # Tipo: auto → siempre OK; opciones → debe estar en la lista; en subcampos → debe rellenarse
    if tipo_auto:
        pass  # satisfecho automáticamente
    elif tipo_opciones:
        if str(valor.get("tipo", "")).strip() not in tipo_opciones:
            return False
    elif "tipo" in subcampos:
        if not str(valor.get("tipo", "")).strip():
            return False

    tiene_ref = "referencia" in subcampos
    tiene_alt = "altura" in subcampos
    if tiene_ref and tiene_alt:
        if not (str(valor.get("referencia", "")).strip() or str(valor.get("altura", "")).strip()):
            return False
    elif tiene_ref:
        if not str(valor.get("referencia", "")).strip():
            return False
    elif tiene_alt:
        if not str(valor.get("altura", "")).strip():
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


def _control_radio_op_207_seleccion(
    clave: str, name: str, meta: dict, opcionales: dict, selecciones: dict
) -> None:
    """Radio de op_207 para muebles de despensa AGM (GM1/GM2). Siempre tiene valor seleccionado."""
    muebles_seleccion = meta.get("muebles_seleccion") or {}
    etiqueta_por_sg   = meta.get("etiqueta_por_sg")   or {}
    etiqueta_label    = meta.get("etiqueta_despensa", "Tipo de almacenamiento")
    # dedup preservando orden
    opciones_sg = list(dict.fromkeys(muebles_seleccion.get(name) or []))

    if not opciones_sg:
        return

    prev = opcionales.get("op_207_opcional")
    if prev not in opciones_sg:
        prev = opciones_sg[0]

    nuevo = st.radio(
        etiqueta_label,
        options=opciones_sg,
        index=opciones_sg.index(prev),
        format_func=lambda v: etiqueta_por_sg.get(v, v),
        horizontal=True,
        key=f"op_207_opcional_{clave}",
        help=_TOOLTIPS_OPCIONALES.get("op_207_opcional"),
    )
    if nuevo != prev:
        opcionales["op_207_opcional"] = nuevo
        _registrar_edicion(clave, selecciones)
        st.rerun()
    elif "op_207_opcional" not in opcionales or opcionales["op_207_opcional"] not in opciones_sg:
        # Inicializar si aún no hay valor válido
        opcionales["op_207_opcional"] = nuevo


def _control_op_207(
    clave: str, name: str, meta: dict, opcionales: dict, selecciones: dict
) -> None:
    """Dispatcher de op_207: checkbox (fregadero) o radio (despensa AGM)."""
    if name in (meta.get("muebles_seleccion") or {}):
        _control_radio_op_207_seleccion(clave, name, meta, opcionales, selecciones)
    else:
        _control_checkbox_op_207(clave, meta, opcionales, selecciones)


def _control_electrodomestico_op_126(
    clave: str, meta: dict, opcionales: dict, selecciones: dict
) -> None:
    subcampos     = meta.get("subcampos") or _SUBCAMPOS_OP_126_DEFAULT
    tipo_auto     = meta.get("tipo_auto")
    tipo_opciones = meta.get("tipo_opciones")

    prev_raw = opcionales.get("op_126")
    prev = prev_raw if isinstance(prev_raw, dict) else {}

    st.markdown(f"**{meta.get('etiqueta', 'Electrodoméstico')}**")
    if _TOOLTIPS_OPCIONALES.get("op_126"):
        st.caption(_TOOLTIPS_OPCIONALES["op_126"])

    nuevo: dict[str, str] = {}

    # ── Tipo: desplegable si hay opciones, oculto si es fijo ─────────────────
    if tipo_auto:
        # Tipo determinado por el mueble — no se muestra al usuario
        nuevo["tipo"] = tipo_auto
    elif tipo_opciones:
        prev_tipo = prev.get("tipo", tipo_opciones[0])
        if prev_tipo not in tipo_opciones:
            prev_tipo = tipo_opciones[0]
        nuevo["tipo"] = st.selectbox(
            "Tipo de electrodoméstico",
            options=tipo_opciones,
            index=tipo_opciones.index(prev_tipo),
            key=f"op_126_tipo_{clave}",
        )

    # ── Campos de referencia (marca, referencia, altura) ─────────────────────
    # "tipo" se gestiona SIEMPRE en el bloque de arriba (tipo_auto u opciones) — nunca aquí.
    for sub_key, sub_label in subcampos.items():
        if sub_key == "tipo":
            continue
        nuevo[sub_key] = st.text_input(
            sub_label,
            value=prev.get(sub_key, ""),
            key=f"op_126_{sub_key}_{clave}",
        )

    if nuevo != prev:
        opcionales["op_126"] = nuevo
        _registrar_edicion(clave, selecciones)
        st.rerun()


def _renderizar_opcionales(
    clave: str, name: str, aplicables: list[str], interfaz: dict, selecciones: dict
) -> None:
    """Renderiza checkboxes y radio. op_126 (texto libre) va aparte tras divisor."""
    opcionales = selecciones[clave].setdefault("opcionales", {})
    for op_id in aplicables:
        if op_id == "op_126":
            continue
        meta = interfaz.get(op_id, {})
        if op_id == "op_222":
            _control_radio_op_222(clave, meta, opcionales, selecciones)
        elif op_id == "op_207_opcional":
            _control_op_207(clave, name, meta, opcionales, selecciones)
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
            # Pre-check para muebles sin opcionales aplicables (CLAUDE.md §7).
            estado["check"] = (len(aplicables) == 0)
        # Inicializar selección de op_207 para muebles de despensa (radio obligatorio).
        # Garantiza que siempre haya un valor válido antes de que el radio se pinte.
        if "op_207_opcional" in aplicables:
            meta_207    = interfaz.get("op_207_opcional") or {}
            muebles_sel = meta_207.get("muebles_seleccion") or {}
            if name in muebles_sel and "op_207_opcional" not in opcionales:
                opciones_sg = list(dict.fromkeys(muebles_sel.get(name) or []))
                if opciones_sg:
                    opcionales["op_207_opcional"] = opciones_sg[0]
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
    a_mostrar = [
        m for m in muebles
        if not (
            solo_pendientes
            and selecciones.get(_identificador_mueble(m), {}).get("check")
        )
    ]

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
                        _bloque_informativo(mueble)
                        if aplicables:
                            _renderizar_opcionales(clave, name, aplicables, interfaz, selecciones)
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
                else:
                    _bloque_informativo(mueble)
                    _render_swatches_color(
                        _ui_color_frente(mueble.get("ColorFrente", "")),
                        _ui_color_interior(mueble.get("Color del interior", "")),
                    )
                    if aplicables:
                        _renderizar_opcionales(clave, name, aplicables, interfaz, selecciones)
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

                if "op_126" in aplicables and not _op_126_completo(
                    estado["opcionales"].get("op_126"),
                    meta=meta_126,
                ):
                    razon_bloqueo = (
                        "Completa todos los campos obligatorios del electrodoméstico "
                        "antes de marcar como revisado."
                    )
                else:
                    razon_bloqueo = None

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

    titulo = f"### {nombre}"
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

            # Datos del electrodoméstico: modulo_c los pasa al JSON de export
            # pero no los incluye en opciones_adicionales → los leemos de entrada.
            marca     = (entrada.get("Marca electro")      or "").strip()
            referencia = (entrada.get("Referencia electro") or "").strip()
            altura    = (entrada.get("Altura electro")     or "").strip()
            tipo      = (entrada.get("Tipo electro")       or "").strip()
            tiene_electro = bool(marca)

            if opc_adic or tiene_electro:
                st.markdown("**Opciones adicionales**")

                for entry_adic in opc_adic:
                    marcador = " ⚙" if entry_adic.get("origen") == "automatico" else ""
                    st.markdown(
                        f"- **{entry_adic.get('etiqueta', '')}:** "
                        f"{entry_adic.get('valor', '')}{marcador}"
                    )
                if any(e.get("origen") == "automatico" for e in opc_adic):
                    st.caption("⚙ Forzado automáticamente por reglas")

                if tiene_electro:
                    partes = " · ".join(p for p in (marca, referencia, altura, tipo) if p)
                    st.markdown(f"- **Electrodoméstico:** {partes}")

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
        # Invalida el export guardado al volver atrás
        st.session_state.pop("_export_excel", None)
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
    # Al hacer clic se generan ambos archivos y se muestran los botones de descarga.
    if st.button("📦 Exportar pedido", type="primary"):
        import modulo_c as _mc  # importación local para mantener modulo_b autónomo
        st.session_state["_export_excel"] = _mc.generar_excel_revision(pedido)
        st.session_state["_export_json"] = json.dumps(
            _mc.generar_json_pedido(pedido), ensure_ascii=False, indent=2
        ).encode("utf-8")

    if st.session_state.get("_export_excel"):
        nombre = _nombre_export_base()
        col_xlsx, col_json = st.columns(2)
        with col_xlsx:
            st.download_button(
                "⬇ Excel de revisión",
                data=st.session_state["_export_excel"],
                file_name=f"{nombre}_revision.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument"
                    ".spreadsheetml.sheet"
                ),
                use_container_width=True,
            )
        with col_json:
            st.download_button(
                "⬇ JSON de pedido",
                data=st.session_state["_export_json"],
                file_name=f"{nombre}_pedido.json",
                mime="application/json",
                use_container_width=True,
            )
