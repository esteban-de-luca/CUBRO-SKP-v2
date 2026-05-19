import pandas as pd
import io
import re
from collections import defaultdict

# ── Configuración ──────────────────────────────────────────────────────────────

COLUMNAS_VALIDAS = [
    "Name", "Ancho", "LenZ", "Apertura", "D_Gama", "ColorFrente",
    "Color del interior", "Tirador", "Trasera",
    "Color tir. de superficie", "C_Rodapietext",
    "Ancho reducido",
]

COLUMNAS_OBLIGATORIAS = ["Name", "D_Gama", "ColorFrente", "Tirador", "C_Rodapietext"]

PREFIJOS_INSTALACION = [
    "DESAGUE_", "FONTANERIA_", "ELECT_", "FONTANERÍA_",
    "DESAGÜE", "DESAGÜES", "ENCHUFE", "TOMAS DE AGUA", "FONTANERIA",
]

TIRADORES_VALIDOS    = {2, 3, 4, 5, 7, 20, 21}
TIRADORES_TRASERA    = {2, 3}     # Round, Square → usan Trasera
TIRADORES_SUPERFICIE = {4, 5, 7}  # Curve, Line, Plantea → usan Color tir. de superficie
TIRADORES_MECANISMO  = {20, 21}   # Touch Latch, Prise de main → sin op. 301

TRASERA_VALIDAS = {"LACA", "NORDIC OAK WOOD", "OAK WOOD", "SMOKED OAK WOOD"}

D_GAMA_LACA = "1"
GAMA_SUFIJOS = {
    "1": ["LACA"],
    "2": ["WOOD"],
    "3": ["LINOLEO", "LINÓLEO"],
    "4": ["LAMINADO"],
}

COLOR_INTERIOR_VALIDOS = {"Blanco mueble", "Gris mueble", "Negro mueble", "Roble mueble"}
RODAPIE_VALIDOS = {"70 mm", "100 mm", "0 mm"}

FAMILIAS_SUSPENSO = {"H", "HH", "HAV", "HR", "HLVV", "HPT"}
CODIGOS_RODAPIE_OPCIONAL = {"BC158057"}

CATALOGO_CODIGOS = {
    "B308035","B458035","B608035","B908035","B308057","B458057","B608057","B908057",
    "BB2T458035","BB2T608035","BB2T908035","BB2T458057","BB2T608057","BB2T908057",
    "B2B458035","B2B608035","B2B908035","B2B458057","B2B608057","B2B908057",
    "BC158057","BC604035","BC604057","BFT608057",
    "BCUB2T458057","BCUB2T608057","BCUB2T908057",
    "BIBTS608057","BIBTS908057",
    "BETO458057","BETO608057","BETO908057","BETOQ908057",
    "BE2B608057","BE2B908057","BEBTS608057","BEBTS908057",
    "POBIF4580","POBIF6080","PO2BIF4580","PO2BIF6080","PO1BIF4580","PO1BIF6080",
    "FHABS6580",
    "BAV908057","BAV1208057","BAV1P908057","BAV1P1208057",
    "H1306035","H1456035","H1606035","H1906035",
    "H1308035","H1458035","H1608035","H1908035",
    "H13010035","H14510035","H16010035","H19010035",
    "HH1606035","HH1906035","HH1608035","HH1908035","HH16010035","HH19010035",
    "HAV1906035","HAV1908035","HAV19010035","HAV2906035","HAV2908035","HAV29010035",
    "HLVV57","HR45V35","HR60V35","HR45V57","HR60V57","HPT60V57",
    "AQC34520057","AQC36020057","AQC34522057","AQC36022057",
    "AQC31P4520057","AQC31P6020057","AQC31P4522057","AQC31P6022057",
    "AVA4520035","AVA6020035","AVA4520057","AVA6020057",
    "AVA4522035","AVA6022035","AVA4522057","AVA6022057",
    "AVA1P4520035","AVA1P6020035","AVA1P9020035",
    "AVA1P4520057","AVA1P6020057",
    "AVA1P4522035","AVA1P6022035","AVA1P9022035",
    "AVA1P4522057","AVA1P6022057",
    "ABA6020057","ABA6022057",
    "AFS6020057","AFS6022057",
    "AFSMO6020057","AFSMO6022057",
    "AFS2B6020057","AFS2B6022057",
    "AFSMOBT6020057","AFSMOBT6022057",
    "A2I6020057","A2I6022057","A2I7522057","A2I1P6020057","A2I1P6022057",
    "AGM9020057","AGM9022057",
}

# ── Catálogo de anchos estándar por (familia, alto_cm, fondo_cm) ───────────────
# Usado para corregir Names con reducción de ancho (op. 231)

# Known family prefixes that include a trailing digit
_FAMILY_PREFIXES = [
    # Familias con dígito en medio
    'BCUB2T', 'BB2T', 'BE2B', 'B2B',
    # Familias H con número de variante
    'HAV1', 'HAV2', 'HH1', 'H1',
    # Armarios y columnas
    'AQC31P', 'AQC3', 'AVA1P', 'AFS2B', 'AFSMOBT', 'AFSMO', 'A2I1P', 'A2I',
    'BAV1P',
    # Fachadas — handled separately below
]

def _parse_catalog_code(code):
    """Returns (family, ancho_cm, alto_cm, fondo_cm) or None"""
    # Special format: HR/HLVV/HPT + ancho + V + fondo (alto is variable)
    # HLVV57 special: just family + fondo, no fixed ancho/alto
    m_hlvv = re.match(r'^(HLVV)(\d{2})$', code)
    if m_hlvv:
        return m_hlvv.group(1), 0, 0, int(m_hlvv.group(2))
    # HR/HPT: family + ancho + V + fondo
    m_var = re.match(r'^(HR|HPT)(\d{2})V(\d{2})$', code)
    if m_var:
        return m_var.group(1), int(m_var.group(2)), 0, int(m_var.group(3))

    # Fachadas: FAMILY + 2digit_ancho + 2digit_alto (no fondo)
    m_fach = re.match(r'^(PO1BIF|PO2BIF|POBIF|FHABS)(\d{2})(\d{2})$', code)
    if m_fach:
        return m_fach.group(1), int(m_fach.group(2)), int(m_fach.group(3)), 0

    # Standard prefixes with digit in family name
    for prefix in _FAMILY_PREFIXES:
        if code.startswith(prefix):
            rest = code[len(prefix):]
            m = re.match(r'^(\d{2})(\d{2,3})(\d{2})$', rest)
            if m:
                return prefix, int(m.group(1)), int(m.group(2)), int(m.group(3))

    # Standard format: letters + 2digit + 2-3digit + 2digit
    m = re.match(r'^([A-Z]+)(\d{2})(\d{2,3})(\d{2})$', code)
    if m:
        return m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
    return None

def _build_catalog_widths():
    by_suffix = defaultdict(list)
    for code in CATALOGO_CODIGOS:
        result = _parse_catalog_code(code)
        if result:
            family, ancho, alto, fondo = result
            by_suffix[(family, alto, fondo)].append(ancho)
    for key in by_suffix:
        by_suffix[key] = sorted(set(by_suffix[key]))
    return dict(by_suffix)

CATALOG_WIDTHS = _build_catalog_widths()


def _corregir_name_reduccion(name_skp, ancho_reducido_mm):
    """
    Dado un Name de SKP con reducción (ej. AVA36.522057) y el ancho
    reducido real en mm (ej. 365), devuelve (name_corregido, aviso).
    name_corregido es el Name con el ancho estándar más cercano por encima.
    aviso es None si todo OK, o un mensaje de error si hay problema.
    """
    # Strip subcomponent suffix (-C1, -P1, etc.)
    suffix_sub = ''
    name_base = name_skp
    for suf in ['-C1','-C2','-C3','-C4','-P1','-P2','-P3']:
        if name_base.endswith(suf):
            suffix_sub = suf
            name_base = name_base[:-len(suf)]
            break

    # Remove dots (SKP uses 36.5 for 365mm in the name)
    name_clean = name_base.replace('.', '')

    # Parse: family + ancho_digits + 3-digit alto + 2-digit fondo
    # Try known prefix families first, then standard
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

    family = parsed[0]
    alto   = parsed[2]
    fondo  = parsed[3]

    key = (family, alto, fondo)
    anchos_std = CATALOG_WIDTHS.get(key)

    if not anchos_std:
        return name_skp, (
            f"No se encontraron anchos estándar para {family} "
            f"(alto={alto}cm, fondo={fondo}cm)"
        )

    # Validate range: minimum absolute width is 300mm
    if ancho_reducido_mm < 300:
        return name_skp, (
            f"El ancho reducido ({ancho_reducido_mm:.0f}mm) está por debajo del mínimo de 300mm"
        )

    # Find nearest standard width >= reduced width
    anchos_mayores = [a for a in anchos_std if a * 10 >= ancho_reducido_mm]
    if not anchos_mayores:
        return name_skp, (
            f"El ancho reducido ({ancho_reducido_mm:.0f}mm) supera el ancho máximo estándar"
        )

    ancho_correcto = min(anchos_mayores)
    name_corregido = f"{family}{ancho_correcto:02d}{alto:03d}{fondo:02d}{suffix_sub}"
    return name_corregido, None


# ── Catálogo de altos por código ──────────────────────────────────────────────
# Usado para validar LenZ (A21)

def _build_catalog_altos():
    altos = {}
    for code in CATALOGO_CODIGOS:
        result = _parse_catalog_code(code)
        if result:
            _, _, alto_cm, _ = result
            altos[code] = alto_cm * 10  # mm
    return altos

CATALOG_ALTOS = _build_catalog_altos()

LENZ_TOLERANCIA_MM = 5  # tolerancia para comparación de alto

# Rangos para muebles con dimensiones variables
RANGOS_VARIABLES = {
    'HLVV': {'ancho_min': 450, 'ancho_max': 1200, 'alto_min': 200, 'alto_max': 400},
    'HR':   {'ancho_min': None, 'ancho_max': None, 'alto_min': 200, 'alto_max': 1000},  # ancho fijo por código → validado por CATALOG_WIDTHS
    'HPT':  {'ancho_min': 600, 'ancho_max': 600, 'alto_min': 1100, 'alto_max': 1400},
}

# Muebles sin apertura — columna Ouverture vacía o coulissant en catálogo (45 códigos)
# Valores sin apertura: '' (vacío) y '- C: Coulissant'
# HLVV tiene '- L: Lift' — apertura especial, se normaliza a "horizontal"
CODIGOS_SIN_APERTURA = {
    # Vacío en catálogo — 2 puertas o sin puerta batiente
    'B908035', 'B908057', 'BETO908057', 'BETOQ908057',
    'H1906035', 'H1908035', 'H19010035',
    'HH1906035', 'HH1908035', 'HH19010035',
    'AVA1P9020035', 'AVA1P9022035',
    'AGM9020057', 'AGM9022057',
    'POBIF4580', 'POBIF6080', 'PO2BIF4580', 'PO2BIF6080',
    'PO1BIF4580', 'PO1BIF6080',
    # Coulissant — cajones, sin puerta batiente
    'BC158057', 'BC604035', 'BC604057', 'BFT608057',
    'BB2T458035', 'BB2T608035', 'BB2T908035',
    'BB2T458057', 'BB2T608057', 'BB2T908057',
    'B2B458035', 'B2B608035', 'B2B908035',
    'B2B458057', 'B2B608057', 'B2B908057',
    'BE2B608057', 'BE2B908057',
    'BEBTS608057', 'BEBTS908057',
    'BIBTS608057', 'BIBTS908057',
    'BCUB2T458057', 'BCUB2T608057', 'BCUB2T908057',
}

# Muebles sin op. 231 — no admiten reducción de ancho
# Incluye: muebles de ancho mínimo 300mm, variables (HR/HLVV/HPT), fachadas, banco BC158057
CODIGOS_SIN_OP231 = {
    # Variables — sin reducción
    'HLVV57', 'HR45V35', 'HR60V35', 'HR45V57', 'HR60V57', 'HPT60V57',
    # Fachadas — sin reducción
    'FHABS6580', 'POBIF4580', 'POBIF6080',
    # Banco — sin reducción
    'BC158057',
    # Ancho 300mm — mínimo absoluto, no se puede reducir más
    'B308035', 'B308057',
    'H1306035', 'H1308035', 'H13010035',
    # BFT — sin reducción
    'BFT608057',
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_familia(name):
    m = re.match(r'^([A-Z]+)', str(name))
    return m.group(1) if m else ""

def _es_suspenso(name):
    return _get_familia(name) in FAMILIAS_SUSPENSO

def _normalizar_apertura(valor):
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

def _normalizar_tirador(valor):
    if pd.isna(valor) or str(valor).strip() == "":
        return None
    try:
        return int(float(str(valor).strip()))
    except (ValueError, TypeError):
        return None

def _str_or_none(valor):
    if pd.isna(valor) or str(valor).strip() == "":
        return None
    return str(valor).strip()

def _es_instalacion(name):
    name_upper = str(name).strip().upper()
    return any(name_upper.startswith(p.upper()) for p in PREFIJOS_INSTALACION)


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
    Cada mueble tiene: name, name_skp, d_gama, color_frente, color_interior,
    tirador, color_tirador, trasera, apertura, rodapie, ancho, ancho_reducido,
    avisos, errores.
    """
    resultado = {
        "ok": False,
        "error_archivo": None,
        "muebles": [],
        "filas_descartadas": [],
    }

    # 1. Leer
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

    # 2. Limpiar columnas
    df.columns = [str(c).strip() for c in df.columns]

    # 3. Eliminar columnas no válidas (I03 · silencioso)
    cols_presentes = [c for c in COLUMNAS_VALIDAS if c in df.columns]
    df = df[cols_presentes]

    # 4. Columnas obligatorias (E01 · bloqueante)
    faltantes = [c for c in COLUMNAS_OBLIGATORIAS if c not in df.columns]
    if faltantes:
        resultado["error_archivo"] = (
            f"Columnas obligatorias ausentes en el archivo: {', '.join(faltantes)}"
        )
        return resultado

    resultado["ok"] = True

    # 5. Fila a fila
    for _, fila in df.iterrows():
        errores = []
        avisos  = []

        # R1 · Name vacío (I01 · silencioso)
        name_raw = _str_or_none(fila.get("Name", ""))
        if name_raw is None:
            continue

        # R3 · Instalación (I02 · silencioso)
        if _es_instalacion(name_raw):
            continue

        # I05 · Ancho vacío → descarte silencioso
        ancho_check = _str_or_none(fila.get("Ancho", ""))
        if ancho_check is None:
            continue

        # D_Gama — leído aquí, puede ser None (se avisará con A11 si aplica)
        d_gama_check = _str_or_none(fila.get("D_Gama", ""))

        # ── Op. 231 · Reducción de ancho ──────────────────────────────────────
        ancho_raw          = ancho_check
        ancho_reducido_raw = _str_or_none(fila.get("Ancho reducido", ""))
        name_skp           = name_raw  # guardar Name original de SKP

        if ancho_raw == "10000 mm":
            if name_skp in CODIGOS_SIN_OP231:
                avisos.append(
                    f"Este mueble no admite reducción de ancho"
                )
            elif ancho_reducido_raw is None:
                avisos.append(
                    "El mueble tiene reducción de ancho pero falta el valor reducido"
                )
            else:
                try:
                    ancho_reducido_mm = float(ancho_reducido_raw.replace(" mm", "").strip())
                    name_corregido, aviso_231 = _corregir_name_reduccion(name_raw, ancho_reducido_mm)
                    if aviso_231:
                        avisos.append(aviso_231)
                    else:
                        avisos.append(
                            f"Nombre corregido por reducción de ancho: '{name_skp}' → '{name_corregido}' ({ancho_reducido_mm:.0f}mm)"
                        )
                        name_raw = name_corregido
                except ValueError:
                    avisos.append(
                        f"No se pudo leer 'Ancho reducido': '{ancho_reducido_raw}'"
                    )

        # A10 · Name no en catálogo
        if name_raw not in CATALOGO_CODIGOS:
            avisos.append(f"'{name_raw}' no existe en el catálogo — revisar el código")

        # A21 · Validar LenZ contra alto del catálogo
        len_z_raw = _str_or_none(fila.get("LenZ", ""))
        if len_z_raw is not None:
            try:
                len_z_str = len_z_raw.replace(" mm", "").replace(",", ".").strip()
                len_z_mm = float(len_z_str)
                familia = _get_familia(name_raw)
                if familia in RANGOS_VARIABLES:
                    rango = RANGOS_VARIABLES[familia]
                    if rango['alto_min'] is not None and rango['alto_max'] is not None:
                        if not (rango['alto_min'] <= len_z_mm <= rango['alto_max']):
                            avisos.append(
                                f"Alto fuera de rango: el mueble mide {len_z_mm:.0f}mm, el rango válido es {rango['alto_min']}–{rango['alto_max']}mm"
                            )
                elif name_raw in CATALOG_ALTOS and CATALOG_ALTOS[name_raw] > 0:
                    alto_catalogo = CATALOG_ALTOS[name_raw]
                    if abs(len_z_mm - alto_catalogo) > LENZ_TOLERANCIA_MM:
                        avisos.append(
                            f"Alto incorrecto: el mueble mide {len_z_mm:.0f}mm, el catálogo indica {alto_catalogo}mm"
                        )
            except ValueError:
                pass

        # A22 · Validar Ancho contra anchos estándar del catálogo
        if ancho_raw is not None and ancho_raw != "10000 mm":
            try:
                ancho_str = ancho_raw.replace(" mm", "").replace(",", ".").strip()
                ancho_mm = float(ancho_str)
                familia_ancho = _get_familia(name_raw)
                rango = RANGOS_VARIABLES.get(familia_ancho, {})
                if rango.get('ancho_min') is not None and rango.get('ancho_max') is not None:
                    if not (rango['ancho_min'] <= ancho_mm <= rango['ancho_max']):
                        avisos.append(
                            f"Ancho fuera de rango: el mueble mide {ancho_mm:.0f}mm, el rango válido es {rango['ancho_min']}–{rango['ancho_max']}mm"
                        )
                else:
                    parsed_raw = _parse_catalog_code(name_raw)
                    if parsed_raw:
                        family, _, alto, fondo = parsed_raw
                        anchos_std = CATALOG_WIDTHS.get((family, alto, fondo))
                        if anchos_std:
                            anchos_std_mm = [a * 10 for a in anchos_std]
                            if not any(abs(ancho_mm - a) <= 5 for a in anchos_std_mm):
                                avisos.append(
                                    f"Ancho incorrecto: el mueble mide {ancho_mm:.0f}mm, los anchos válidos son {anchos_std_mm}mm"
                                )
            except ValueError:
                pass

        # A12 · Tirador vacío
        tirador = _normalizar_tirador(fila.get("Tirador", ""))
        if tirador is None:
            avisos.append(
                "Falta el tipo de tirador"
            )
        # A14 · Tirador no reconocido
        elif tirador not in TIRADORES_VALIDOS:
            avisos.append(
                f"Tipo de tirador '{tirador}' no reconocido"
            )

        # A11 · D_Gama vacío
        d_gama = _str_or_none(fila.get("D_Gama", ""))
        if d_gama is None:
            avisos.append(
                "Falta la gama del frente"
            )

        # A05 · Color del interior
        color_interior = _str_or_none(fila.get("Color del interior", ""))
        if color_interior is None:
            avisos.append(
                "Falta el color del interior"
            )
        # A13 · Color del interior no reconocido
        elif color_interior not in COLOR_INTERIOR_VALIDOS:
            avisos.append(
                f"Color del interior '{color_interior}' no reconocido"
            )

        # A07 · D_Gama incompatible con ColorFrente
        color_frente_val = _str_or_none(fila.get("ColorFrente", ""))
        if d_gama is not None and color_frente_val is not None:
            sufijos_esperados = GAMA_SUFIJOS.get(d_gama, [])
            if sufijos_esperados and not any(
                s in color_frente_val.upper() for s in sufijos_esperados
            ):
                avisos.append(
                    f"La gama ({d_gama}) no coincide con el color de frente '{color_frente_val}'"
                )

        # R9 · Apertura
        apertura = _normalizar_apertura(fila.get("Apertura", ""))

        # A23 · Validar apertura según catálogo
        if name_raw in CODIGOS_SIN_APERTURA:
            if apertura is not None:
                avisos.append(
                    "Este mueble no requiere apertura — el valor se ignorará"
                )
            apertura = None  # forzar null para muebles sin apertura
        elif name_raw in CATALOGO_CODIGOS and name_raw not in CODIGOS_SIN_APERTURA:
            if apertura is None:
                avisos.append(
                    "Este mueble requiere apertura (izquierda o derecha) pero no tiene ninguna asignada"
                )

        # R10 · Lógica tirador/color
        trasera_raw    = _str_or_none(fila.get("Trasera", ""))
        color_tir_raw  = _str_or_none(fila.get("Color tir. de superficie", ""))
        color_tirador  = None
        trasera        = None

        if tirador in TIRADORES_TRASERA:
            trasera = trasera_raw
            # A02 · Trasera vacía con Round/Square
            if trasera is None:
                avisos.append(
                    "Falta el color de la trasera"
                )
            # A03 · Trasera con valor no reconocido
            elif trasera.upper() not in TRASERA_VALIDAS:
                avisos.append(
                    f"Color de trasera '{trasera}' no reconocido"
                )
            # Color tir. de superficie ignorado silenciosamente — Tirador Round/Square usa Trasera

        elif tirador in TIRADORES_SUPERFICIE:
            color_tirador = color_tir_raw
            # A01 · Color tir. de superficie vacío con Curve/Line/Plantea
            if color_tirador is None:
                avisos.append(
                    "Falta el color del tirador de superficie"
                )
            # Trasera ignorada silenciosamente — Tirador Curve/Line/Plantea usa Color tir. de superficie

        # A09 · Excepción de acabados: frente no-LACA con Trasera LACA
        if (tirador in TIRADORES_TRASERA
                and trasera is not None
                and d_gama is not None
                and d_gama != D_GAMA_LACA
                and trasera.upper() == "LACA"):
            avisos.append(
                f"La trasera Laca no es compatible con un frente que no es LACA"
            )

        # ── Lógica rodapié ─────────────────────────────────────────────────────
        rodapie_raw = _str_or_none(fila.get("C_Rodapietext", ""))

        if _es_suspenso(name_raw):
            # Suspenso → nunca lleva rodapié
            if rodapie_raw is not None:
                avisos.append(
                    f"Mueble suspenso — el rodapié '{rodapie_raw}' se ignorará"
                )
            rodapie = None  # Módulo B asignará SPI (L01)

        elif name_raw in CODIGOS_RODAPIE_OPCIONAL:
            # Banco BC158057 → rodapié opcional
            rodapie = rodapie_raw  # None → Módulo B asignará SPI (P05)

        else:
            # Posé estándar → rodapié obligatorio
            rodapie = rodapie_raw
            if rodapie is None:
                avisos.append(
                    "Falta el valor de rodapié"
                )
            elif rodapie not in RODAPIE_VALIDOS:
                avisos.append(
                    f"Valor de rodapié '{rodapie}' no reconocido — los valores válidos son 70 mm, 100 mm y 0 mm"
                )

        avisos_revisables = [a for a in avisos if not a.startswith("Nombre corregido por reducción")]
        estado = "✅ CORRECTO" if not avisos_revisables else "⚠️ REVISAR"

        mueble = {
            "name":           name_raw,
            "name_skp":       name_skp,
            "estado":         estado,
            "len_z":          len_z_raw,
            "d_gama":         d_gama,
            "color_frente":   color_frente_val,
            "color_interior": color_interior,
            "tirador":        tirador,
            "color_tirador":  color_tirador,
            "trasera":        trasera,
            "apertura":       apertura,
            "rodapie":        rodapie,
            "ancho":          ancho_raw,
            "ancho_reducido": ancho_reducido_raw,
            "avisos":         avisos,
            "errores":        errores,
        }

        if errores:
            resultado["filas_descartadas"].append(mueble)
        else:
            resultado["muebles"].append(mueble)

    return resultado
