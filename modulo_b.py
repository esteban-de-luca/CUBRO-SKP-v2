"""
modulo_b.py — Módulo B: Interfaz y selección.
Responsable: Esteban.

Interviene en dos momentos del flujo:
- Paso 1 (antes de C): recoge opciones opcionales por mueble.
- Paso 2 (después de C): revisión final y export a DealHub.

Pantalla 0 (Validación) bloquea el avance si el CSV trae errores duros.
"""

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
    "op_126": "Rellena los 4 campos del electrodoméstico para poder marcar el mueble como revisado.",
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
_MAPEOS_PATH = pathlib.Path(__file__).parent / "data" / "mapeos.yaml"
_REGLAS_PATH = pathlib.Path(__file__).parent / "data" / "reglas.yaml"


@st.cache_data
def _cargar_catalogo() -> dict:
    """Carga data/catalogo.json. Si todavía no se ha subido, devuelve {}."""
    if not _CATALOGO_PATH.exists():
        return {}
    return json.loads(_CATALOGO_PATH.read_text(encoding="utf-8"))


@st.cache_data
def _cargar_interfaz() -> dict:
    """Sección `interfaz` de mapeos.yaml — metadatos UI de las 8 opcionales."""
    if not _MAPEOS_PATH.exists():
        return {}
    with _MAPEOS_PATH.open(encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("interfaz", {}) or {}


@st.cache_data
def _cargar_reglas_muebles() -> dict:
    """Sección `muebles` de reglas.yaml — facultativas/forzadas por mueble."""
    if not _REGLAS_PATH.exists():
        return {}
    with _REGLAS_PATH.open(encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("muebles", {}) or {}


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


def _cabecera_card(mueble: dict, catalogo: dict, revisado: bool) -> str:
    """[check] · Name · Designación · Gama Color · Tirador Color (CLAUDE.md §7)."""
    check = "☑" if revisado else "☐"
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


def _opcionales_aplicables(mueble: dict, interfaz: dict, reglas_muebles: dict) -> list[str]:
    """Lista de op_ids (en clave de `interfaz`) que aplican al mueble."""
    name = (mueble.get("Name") or "").strip()
    if not name:
        return []
    facultativas = set(reglas_muebles.get(name, {}).get("facultativas", []) or [])
    aplicables: list[str] = []

    if "op_121" in facultativas:
        aplicables.append("op_121")
    if "op_207" in facultativas and name in (
        interfaz.get("op_207_opcional", {}).get("muebles") or {}
    ):
        aplicables.append("op_207_opcional")
    for op_id in ("op_220", "op_222", "op_223", "op_227"):
        clave_facult = op_id
        if clave_facult in facultativas and name in (
            interfaz.get(op_id, {}).get("muebles") or []
        ):
            aplicables.append(op_id)
    if "op_700" in facultativas and name not in (
        interfaz.get("op_700_opcional", {}).get("excluidos") or []
    ):
        aplicables.append("op_700_opcional")
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


# Subcampos obligatorios de op_126 cuando mapeos.yaml no provee `subcampos`.
# La fuente de verdad es data/mapeos.yaml; esto es solo fallback defensivo.
_SUBCAMPOS_OP_126_DEFAULT = {
    "marca": "Marca",
    "referencia": "Referencia",
    "altura": "Altura",
    "tipo": "Tipo",
}


def _op_126_completo(valor) -> bool:
    if not isinstance(valor, dict):
        return False
    return all(
        str(valor.get(k, "")).strip()
        for k in _SUBCAMPOS_OP_126_DEFAULT.keys()
    )


def _control_electrodomestico_op_126(
    clave: str, meta: dict, opcionales: dict, selecciones: dict
) -> None:
    subcampos = meta.get("subcampos") or _SUBCAMPOS_OP_126_DEFAULT
    prev_raw = opcionales.get("op_126")
    prev = prev_raw if isinstance(prev_raw, dict) else {}

    st.markdown(f"**{meta.get('etiqueta', 'Electrodoméstico')}**")
    if _TOOLTIPS_OPCIONALES.get("op_126"):
        st.caption(_TOOLTIPS_OPCIONALES["op_126"])

    nuevo: dict[str, str] = {}
    for sub_key, sub_label in subcampos.items():
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
    clave: str, aplicables: list[str], interfaz: dict, selecciones: dict
) -> None:
    """Renderiza checkboxes y radio. op_126 (texto libre) va aparte tras divisor."""
    opcionales = selecciones[clave].setdefault("opcionales", {})
    for op_id in aplicables:
        if op_id == "op_126":
            continue
        meta = interfaz.get(op_id, {})
        if op_id == "op_222":
            _control_radio_op_222(clave, meta, opcionales, selecciones)
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
    reglas_muebles = _cargar_reglas_muebles()
    selecciones = st.session_state.selecciones_paso_1
    abiertos = st.session_state.setdefault("paso_1_abiertos", set())

    # Inicializa estado y pre-check para todos los muebles antes de pintar la
    # cabecera (los contadores deben verlos ya inicializados).
    for mueble in muebles:
        clave = _identificador_mueble(mueble)
        aplicables = _opcionales_aplicables(mueble, interfaz, reglas_muebles)
        estado = selecciones.setdefault(clave, {})
        estado.setdefault("opcionales", {})
        if "check" not in estado:
            # Pre-check para muebles sin opcionales aplicables (CLAUDE.md §7).
            estado["check"] = (len(aplicables) == 0)

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
            aplicables = _opcionales_aplicables(mueble, interfaz, reglas_muebles)
            estado = selecciones[clave]
            revisado = bool(estado["check"])
            expanded = clave in abiertos

            with st.expander(
                _cabecera_card(mueble, catalogo, revisado),
                expanded=expanded,
            ):
                _bloque_informativo(mueble)

                if aplicables:
                    _renderizar_opcionales(clave, aplicables, interfaz, selecciones)
                    if "op_126" in aplicables:
                        st.divider()
                        _control_electrodomestico_op_126(
                            clave, interfaz.get("op_126", {}),
                            estado["opcionales"], selecciones,
                        )
                else:
                    st.caption(
                        "Este mueble no tiene opciones opcionales aplicables. "
                        "Pre-marcado como revisado."
                    )

                if "op_126" in aplicables and not _op_126_completo(
                    estado["opcionales"].get("op_126")
                ):
                    razon_bloqueo = (
                        "Completa los 4 datos del electrodoméstico "
                        "(marca, referencia, altura y tipo)."
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
    """Pares (etiqueta, valor) del bloque Configuración (origen CSV)."""
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


def _bloque_dimensiones(mueble: dict, catalogo: dict) -> list[tuple[str, str]]:
    """Pares (etiqueta, valor) del bloque Dimensiones (origen catálogo)."""
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


def _render_lista_items(items: list[tuple[str, str]]) -> None:
    for etiqueta, valor in items:
        st.markdown(f"- **{etiqueta}:** {valor}")


def _render_card_resumen(mueble: dict, catalogo: dict) -> None:
    """Card-resumen NO plegable de un mueble (CLAUDE.md §7)."""
    nombre = mueble.get("Name") or mueble.get("Name SKP") or "—"
    designacion = _designacion(mueble, catalogo)
    titulo = f"### {nombre}"
    if designacion:
        titulo += f"  ·  {designacion}"

    with st.container(border=True):
        st.markdown(titulo)

        configuracion = _bloque_configuracion(mueble)
        if configuracion:
            st.markdown("**Configuración**")
            st.caption("Origen: CSV exportado desde SketchUp")
            _render_lista_items(configuracion)

        dimensiones = _bloque_dimensiones(mueble, catalogo)
        if dimensiones:
            st.markdown("**Dimensiones**")
            st.caption("Origen: catálogo de muebles")
            _render_lista_items(dimensiones)

        opciones_adicionales = mueble.get("opciones_adicionales") or []
        if opciones_adicionales:
            st.markdown("**Opciones adicionales**")
            for entry in opciones_adicionales:
                marcador = " ⚙" if entry.get("origen") == "automatico" else ""
                st.markdown(
                    f"- **{entry.get('etiqueta', '')}:** "
                    f"{entry.get('valor', '')}{marcador}"
                )
            if any(e.get("origen") == "automatico" for e in opciones_adicionales):
                st.caption("⚙ Forzado automáticamente por reglas")

        if MOSTRAR_DETALLE_TECNICO:
            with st.expander("Ver detalle técnico"):
                codigos = mueble.get("codigos_sg") or {}
                if codigos:
                    for op_id, valor in sorted(codigos.items()):
                        st.markdown(f"- `{op_id}`: `{valor}`")
                else:
                    st.caption("Sin códigos SG calculados.")


def paso_2(pedido: list[dict] | None) -> None:
    """Paso 2 — Revisión final del pedido y export a DealHub."""
    catalogo = _cargar_catalogo()

    st.header("Paso 2 — Revisión")

    if st.button("← Volver al Paso 1"):
        st.session_state.pantalla = PANTALLA_PASO_1
        st.rerun()

    if not pedido:
        st.error("No hay pedido que revisar. Vuelve al Paso 1.")
        return

    st.success(f"Pedido listo: **{len(pedido)} muebles** configurados.")

    for entrada in pedido:
        _render_card_resumen(entrada, catalogo)

    st.divider()
    st.button(
        "Exportar a DealHub",
        type="primary",
        disabled=True,
        help=(
            "Export a DealHub pendiente de implementar. El schema del archivo "
            "de salida se cerrará con el equipo (CLAUDE.md §11)."
        ),
    )
