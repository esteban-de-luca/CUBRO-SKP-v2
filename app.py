"""
app.py — CUBRO × Schmidt Groupe
Orquestación Streamlit del flujo A → B → C → B.
"""

from datetime import datetime

import pandas as pd
import streamlit as st

import modulo_a
import modulo_b
import modulo_c
from modulo_b import PANTALLA_VALIDACION, PANTALLA_PASO_1, PANTALLA_PASO_2


# Mientras el Módulo A esté en stub, sustituimos su output por datos mock
# para poder desarrollar el Módulo B de forma aislada.
USE_MOCK_DATA = True

# Mientras el Módulo C esté en stub, sustituimos su output por un pedido mock
# para poder desarrollar el Paso 2. El shape generado por _mock_pedido es
# una propuesta de contrato pendiente de validar con Lucía.
USE_MOCK_C = True


def _default_state() -> dict:
    return {
        "pantalla": PANTALLA_VALIDACION,
        "csv_filename": None,
        "csv_uploaded_at": None,
        "muebles": None,
        "selecciones_paso_1": {},
        "pedido_paso_2": None,
        "entrada_modulo_c": None,
        "pending_csv": None,
        "uploader_nonce": 0,
        "csv_fallback_a_mock": False,
    }


def _init_session_state() -> None:
    for key, value in _default_state().items():
        st.session_state.setdefault(key, value)


def _hay_progreso() -> bool:
    selecciones = st.session_state.get("selecciones_paso_1") or {}
    for mueble in selecciones.values():
        if mueble.get("check") or mueble.get("opcionales"):
            return True
    return False


def _mock_muebles() -> list[dict]:
    return [
        {
            "Name": "B608035",
            "Name SKP": "B608035-1",
            "Estado": "✅ CORRECTO",
            "Apertura": "1",
            "D_Gama": "1",
            "ColorFrente": "Crema LACA",
            "Color del interior": "Blanco mueble",
            "Tirador": "2",
            "Trasera": "Laca",
            "Color tir. de superficie": "Inox",
            "C_Rodapietext": "100 mm",
            "Ancho": "600 mm",
            "Ancho reducido": "",
            "LenZ": "800",
            "Avisos": "",
        },
        {
            "Name": "H1.60",
            "Name SKP": "H1-60-1",
            "Estado": "✅ CORRECTO",
            "Apertura": "2",
            "D_Gama": "2",
            "ColorFrente": "Oak WOOD",
            "Color del interior": "Roble mueble",
            "Tirador": "20",
            "Trasera": "Oak WOOD",
            "Color tir. de superficie": "",
            "C_Rodapietext": "0 mm",
            "Ancho": "600 mm",
            "Ancho reducido": "",
            "LenZ": "720",
            "Avisos": "",
        },
        {
            "Name": "",
            "Name SKP": "MUEBLE-CON-ERROR",
            "Estado": "⚠️ REVISAR",
            "Apertura": "",
            "D_Gama": "",
            "ColorFrente": "",
            "Color del interior": "",
            "Tirador": "",
            "Trasera": "",
            "Color tir. de superficie": "",
            "C_Rodapietext": "",
            "Ancho": "10000 mm",
            "Ancho reducido": "",
            "LenZ": "",
            "Avisos": "A02 | A17",
        },
    ]


# Columnas booleanas de la entrada que se exponen como "Sí" en el bloque
# "Opciones adicionales" del Paso 2 cuando el usuario las ha marcado.
_OPCIONALES_BOOL_EN_ENTRADA = (
    "Sin mecanizado",
    "Cubos de basura",
    "Recorte LED",
    "Cajón interior",
    "Mueble de caldera",
    "Sin encolar",
)


def _mock_pedido(muebles: list[dict], entrada: list[dict]) -> list[dict]:
    """Mock del Módulo C — consume la entrada de 23 columnas (hipótesis B).

    Devuelve la misma list[dict] que espera el Paso 2: cada entrada extiende
    el dict del mueble original con:
      - opciones_adicionales: list[dict] {etiqueta, valor, origen}
      - codigos_sg: dict[op_id, valor]
    """
    pedido: list[dict] = []
    for mueble, fila in zip(muebles, entrada):
        opciones_adicionales: list[dict] = []

        for col in _OPCIONALES_BOOL_EN_ENTRADA:
            if fila.get(col) == "True":
                opciones_adicionales.append(
                    {"etiqueta": col, "valor": "Sí", "origen": "usuario"}
                )

        sensor = fila.get("Sensor para mando LED", "")
        if sensor:
            opciones_adicionales.append(
                {
                    "etiqueta": "Sensor para mando LED",
                    "valor": sensor,
                    "origen": "usuario",
                }
            )

        electro_partes = [
            fila.get("Marca electro", ""),
            fila.get("Referencia electro", ""),
            fila.get("Altura electro", ""),
            fila.get("Tipo electro", ""),
        ]
        electro_partes = [p for p in electro_partes if p]
        if electro_partes:
            opciones_adicionales.append(
                {
                    "etiqueta": "Electrodoméstico",
                    "valor": " · ".join(electro_partes),
                    "origen": "usuario",
                }
            )

        # Forzada de ejemplo para que el marcador ⚙ sea visible en el Paso 2.
        opciones_adicionales.append(
            {
                "etiqueta": "Mecanizado tirador",
                "valor": "Estándar (FSP)",
                "origen": "automatico",
            }
        )

        pedido.append(
            {
                **mueble,
                "opciones_adicionales": opciones_adicionales,
                "codigos_sg": {
                    "op_100": "L",
                    "op_101": "CR",
                    "op_300": "Q2",
                    "op_402": "P10",
                },
            }
        )
    return pedido


def _calcular_pedido_paso_2() -> list[dict]:
    """Construye la entrada y la pasa al Módulo C (o a su mock)."""
    muebles = st.session_state.muebles or []
    selecciones = st.session_state.selecciones_paso_1 or {}
    catalogo = modulo_b._cargar_catalogo()
    entrada = modulo_b.construir_entrada_modulo_c(muebles, selecciones, catalogo)
    st.session_state.entrada_modulo_c = entrada
    if USE_MOCK_C:
        return _mock_pedido(muebles, entrada)
    return modulo_c.calcular_opciones(entrada) or []


# Schema del output del Módulo A (ver CLAUDE.md §9).
_COLUMNAS_OUTPUT_MODULO_A = {
    "Name", "Name SKP", "Estado", "Apertura", "D_Gama", "ColorFrente",
    "Color del interior", "Tirador", "Trasera", "Color tir. de superficie",
    "C_Rodapietext", "Ancho", "Ancho reducido", "LenZ", "Avisos",
}


def _parsear_csv_output_modulo_a(file) -> list[dict] | None:
    # Workaround mientras modulo_a.parsear_csv siga siendo stub: si el CSV
    # subido ya es el output del Módulo A (mismas columnas), lo usamos
    # directamente. Devuelve None si el schema no coincide.
    try:
        df = pd.read_csv(file, dtype=str).fillna("")
    except Exception:
        return None
    if not _COLUMNAS_OUTPUT_MODULO_A.issubset(df.columns):
        return None
    return df.to_dict("records")


def _cargar_csv(file) -> None:
    st.session_state.csv_filename = file.name
    st.session_state.csv_uploaded_at = datetime.now()
    st.session_state.selecciones_paso_1 = {}
    st.session_state.pedido_paso_2 = None
    st.session_state.pantalla = PANTALLA_VALIDACION
    st.session_state.csv_fallback_a_mock = False

    if not USE_MOCK_DATA:
        st.session_state.muebles = modulo_a.parsear_csv(file)
        return

    muebles_reales = _parsear_csv_output_modulo_a(file)
    if muebles_reales is not None:
        st.session_state.muebles = muebles_reales
    else:
        st.session_state.muebles = _mock_muebles()
        st.session_state.csv_fallback_a_mock = True


def _reset_completo() -> None:
    nonce = st.session_state.get("uploader_nonce", 0) + 1
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    _init_session_state()
    # Cambiar la key del uploader fuerza a Streamlit a redibujarlo vacío.
    st.session_state.uploader_nonce = nonce


def _render_sidebar() -> None:
    with st.sidebar:
        # Logo PNG pendiente de subir a assets/logo_cubro.png.
        st.markdown(
            "<h1 style='font-size: 60px; margin: 0 0 0.5rem 0;'>CUBRO</h1>",
            unsafe_allow_html=True,
        )
        _MESES = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
        hoy = datetime.today()
        st.caption(f"{hoy.day} de {_MESES[hoy.month - 1]} de {hoy.year}")

        st.divider()

        uploader_key = f"csv_uploader_{st.session_state.uploader_nonce}"
        nuevo = st.file_uploader(
            "Sube el CSV exportado desde SketchUp",
            type=["csv"],
            key=uploader_key,
        )

        if nuevo is not None and nuevo.name != st.session_state.csv_filename:
            if _hay_progreso():
                st.session_state.pending_csv = nuevo
            else:
                _cargar_csv(nuevo)
                st.rerun()

        if st.session_state.csv_filename:
            st.divider()
            st.markdown(f"**Archivo:** `{st.session_state.csv_filename}`")
            st.markdown(
                f"**Subido:** {st.session_state.csv_uploaded_at:%d/%m/%Y %H:%M}"
            )
            n_muebles = len(st.session_state.muebles or [])
            st.markdown(f"**Muebles detectados:** {n_muebles}")

            if st.button("Subir otro CSV", use_container_width=True):
                if _hay_progreso():
                    st.session_state.pending_csv = "reset"
                else:
                    _reset_completo()
                    st.rerun()


def _render_modal_reemplazo() -> None:
    pending = st.session_state.get("pending_csv")
    if pending is None:
        return

    st.warning(
        "Vas a reemplazar el CSV cargado. Se perderá el progreso del Paso 1."
    )
    col_ok, col_cancel = st.columns(2)
    with col_ok:
        if st.button("Reemplazar y perder progreso", type="primary"):
            if pending == "reset":
                _reset_completo()
            else:
                _cargar_csv(pending)
            st.session_state.pending_csv = None
            st.rerun()
    with col_cancel:
        if st.button("Cancelar"):
            st.session_state.pending_csv = None
            st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="CUBRO × Schmidt Groupe",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _init_session_state()

    # modulo_b puede solicitar un reset completo desde la Pantalla 0.
    if st.session_state.pop("_reset_requested", False):
        _reset_completo()
        st.rerun()

    _render_sidebar()

    if st.session_state.get("pending_csv") is not None:
        _render_modal_reemplazo()
        return

    if st.session_state.muebles is None:
        st.title("CUBRO × Schmidt Groupe")
        st.info("Sube un CSV exportado desde SketchUp en la barra lateral para comenzar.")
        return

    if st.session_state.get("csv_fallback_a_mock"):
        st.warning(
            "El CSV no coincide con el output esperado del Módulo A — "
            "se están usando datos mock para que puedas seguir probando."
        )

    pantalla = st.session_state.pantalla
    if pantalla == PANTALLA_VALIDACION:
        modulo_b.pantalla_validacion(st.session_state.muebles)
    elif pantalla == PANTALLA_PASO_1:
        modulo_b.paso_1(st.session_state.muebles)
    elif pantalla == PANTALLA_PASO_2:
        if st.session_state.pedido_paso_2 is None:
            st.session_state.pedido_paso_2 = _calcular_pedido_paso_2()
        modulo_b.paso_2(st.session_state.pedido_paso_2)


if __name__ == "__main__":
    main()
