import streamlit as st
import os
import glob
from datetime import datetime

# Fecha de última modificación de cualquier archivo del proyecto
archivos = glob.glob(os.path.join(os.path.dirname(__file__), "**", "*"), recursive=True)
archivos = [f for f in archivos if os.path.isfile(f)]
ultima_actualizacion = max((os.path.getmtime(f) for f in archivos), default=None)
_MESES = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
if ultima_actualizacion:
    dt = datetime.fromtimestamp(ultima_actualizacion)
    fecha_str = f"{dt.day} de {_MESES[dt.month - 1]} de {dt.year}"
else:
    fecha_str = "—"

hoy = datetime.today()
fecha_hoy = f"{hoy.day} de {_MESES[hoy.month - 1]} de {hoy.year}"

with st.sidebar:
    st.title("CUBRO")
    st.caption(fecha_hoy)
    st.caption(f"Última actualización: {fecha_str}")

st.title("CUBRO × Schmidt Groupe")
st.write("App en construcción.")
