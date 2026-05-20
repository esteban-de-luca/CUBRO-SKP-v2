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
CODIGOS_RODAPIE_OPCIONAL = {"BC158057", "FHABS6580", "POBIF4580", "POBIF6080", "PO1BIF4580", "PO1BIF6080", "PO2BIF4580", "PO2BIF6080"}

CATALOGO_CODIGOS = {
    "A2I1P6020057",
    "A2I1P6022057",
    "A2I6020057",
    "A2I6022057",
    "A2I7522057",
    "ABA6020057",
    "ABA6022057",
    "AFS2B6020057",
    "AFS2B6022057",
    "AFS6020057",
    "AFS6022057",
    "AFSMO6020057",
    "AFSMO6022057",
    "AFSMOBT6020057",
    "AFSMOBT6022057",
    "AGM9020057",
    "AGM9022057",
    "AQC31P4520057",
    "AQC31P4522057",
    "AQC31P6020057",
    "AQC31P6022057",
    "AQC34520057",
    "AQC34522057",
    "AQC36020057",
    "AQC36022057",
    "AVA1P4520035",
    "AVA1P4520057",
    "AVA1P4522035",
    "AVA1P4522057",
    "AVA1P6020035",
    "AVA1P6020057",
    "AVA1P6022035",
    "AVA1P6022057",
    "AVA1P9020035",
    "AVA1P9022035",
    "AVA4520035",
    "AVA4520057",
    "AVA4522035",
    "AVA4522057",
    "AVA6020035",
    "AVA6020057",
    "AVA6022035",
    "AVA6022057",
    "B2B458035",
    "B2B458057",
    "B2B608035",
    "B2B608057",
    "B2B908035",
    "B2B908057",
    "B308035",
    "B308057",
    "B458035",
    "B458057",
    "B608035",
    "B608057",
    "B908035",
    "B908057",
    "BAV1208057",
    "BAV1P1208057",
    "BAV1P908057",
    "BAV908057",
    "BB2T458035",
    "BB2T458057",
    "BB2T608035",
    "BB2T608057",
    "BB2T908035",
    "BB2T908057",
    "BC158057",
    "BC604035",
    "BC604057",
    "BCUB2T458057",
    "BCUB2T608057",
    "BCUB2T908057",
    "BE2B608057",
    "BE2B908057",
    "BEBTS608057",
    "BEBTS908057",
    "BETO458057",
    "BETO608057",
    "BETO908057",
    "BETOQ908057",
    "BFT608057",
    "BIBTS608057",
    "BIBTS908057",
    "FHABS6580",
    "H13010035",
    "H1306035",
    "H1308035",
    "H14510035",
    "H1456035",
    "H1458035",
    "H16010035",
    "H1606035",
    "H1608035",
    "H19010035",
    "H1906035",
    "H1908035",
    "HAV19010035",
    "HAV1906035",
    "HAV1908035",
    "HAV29010035",
    "HAV2906035",
    "HAV2908035",
    "HH16010035",
    "HH1606035",
    "HH1608035",
    "HH19010035",
    "HH1906035",
    "HH1908035",
    "HLVV57",
    "HPT60V57",
    "HR45V35",
    "HR45V57",
    "HR60V35",
    "HR60V57",
    "PO1BIF4580",
    "PO1BIF6080",
    "PO2BIF4580",
    "PO2BIF6080",
    "POBIF4580",
    "POBIF6080",
}

# Catálogo JSON — dimensiones por código (fuente: catalogo.json)
CATALOGO_JSON = {
    "A2I1P6020057": {"ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 570},
    "A2I1P6022057": {"ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 570},
    "A2I6020057": {"ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 570},
    "A2I6022057": {"ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 570},
    "A2I7522057": {"ancho_mm": 750, "alto_mm": 2200, "fondo_mm": 570},
    "ABA6020057": {"ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 570},
    "ABA6022057": {"ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 570},
    "AFS2B6020057": {"ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 570},
    "AFS2B6022057": {"ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 570},
    "AFS6020057": {"ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 570},
    "AFS6022057": {"ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 570},
    "AFSMO6020057": {"ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 570},
    "AFSMO6022057": {"ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 570},
    "AFSMOBT6020057": {"ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 570},
    "AFSMOBT6022057": {"ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 570},
    "AGM9020057": {"ancho_mm": 900, "alto_mm": 2000, "fondo_mm": 570},
    "AGM9022057": {"ancho_mm": 900, "alto_mm": 2200, "fondo_mm": 570},
    "AQC31P4520057": {"ancho_mm": 450, "alto_mm": 2000, "fondo_mm": 570},
    "AQC31P4522057": {"ancho_mm": 450, "alto_mm": 2200, "fondo_mm": 570},
    "AQC31P6020057": {"ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 570},
    "AQC31P6022057": {"ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 570},
    "AQC34520057": {"ancho_mm": 450, "alto_mm": 2000, "fondo_mm": 570},
    "AQC34522057": {"ancho_mm": 450, "alto_mm": 2200, "fondo_mm": 570},
    "AQC36020057": {"ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 570},
    "AQC36022057": {"ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 570},
    "AVA1P4520035": {"ancho_mm": 450, "alto_mm": 2000, "fondo_mm": 350},
    "AVA1P4520057": {"ancho_mm": 450, "alto_mm": 2000, "fondo_mm": 570},
    "AVA1P4522035": {"ancho_mm": 450, "alto_mm": 2200, "fondo_mm": 350},
    "AVA1P4522057": {"ancho_mm": 450, "alto_mm": 2200, "fondo_mm": 570},
    "AVA1P6020035": {"ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 350},
    "AVA1P6020057": {"ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 570},
    "AVA1P6022035": {"ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 350},
    "AVA1P6022057": {"ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 570},
    "AVA1P9020035": {"ancho_mm": 900, "alto_mm": 2000, "fondo_mm": 350},
    "AVA1P9022035": {"ancho_mm": 900, "alto_mm": 2200, "fondo_mm": 350},
    "AVA4520035": {"ancho_mm": 450, "alto_mm": 2000, "fondo_mm": 350},
    "AVA4520057": {"ancho_mm": 450, "alto_mm": 2000, "fondo_mm": 570},
    "AVA4522035": {"ancho_mm": 450, "alto_mm": 2200, "fondo_mm": 350},
    "AVA4522057": {"ancho_mm": 450, "alto_mm": 2200, "fondo_mm": 570},
    "AVA6020035": {"ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 350},
    "AVA6020057": {"ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 570},
    "AVA6022035": {"ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 350},
    "AVA6022057": {"ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 570},
    "B2B458035": {"ancho_mm": 450, "alto_mm": 800, "fondo_mm": 350},
    "B2B458057": {"ancho_mm": 450, "alto_mm": 800, "fondo_mm": 570},
    "B2B608035": {"ancho_mm": 600, "alto_mm": 800, "fondo_mm": 350},
    "B2B608057": {"ancho_mm": 600, "alto_mm": 800, "fondo_mm": 570},
    "B2B908035": {"ancho_mm": 900, "alto_mm": 800, "fondo_mm": 350},
    "B2B908057": {"ancho_mm": 900, "alto_mm": 800, "fondo_mm": 570},
    "B308035": {"ancho_mm": 300, "alto_mm": 800, "fondo_mm": 350},
    "B308057": {"ancho_mm": 300, "alto_mm": 800, "fondo_mm": 570},
    "B458035": {"ancho_mm": 450, "alto_mm": 800, "fondo_mm": 350},
    "B458057": {"ancho_mm": 450, "alto_mm": 800, "fondo_mm": 570},
    "B608035": {"ancho_mm": 600, "alto_mm": 800, "fondo_mm": 350},
    "B608057": {"ancho_mm": 600, "alto_mm": 800, "fondo_mm": 570},
    "B908035": {"ancho_mm": 900, "alto_mm": 800, "fondo_mm": 350},
    "B908057": {"ancho_mm": 900, "alto_mm": 800, "fondo_mm": 570},
    "BAV1208057": {"ancho_mm": 1200, "alto_mm": 800, "fondo_mm": 570},
    "BAV1P1208057": {"ancho_mm": 1200, "alto_mm": 800, "fondo_mm": 570},
    "BAV1P908057": {"ancho_mm": 900, "alto_mm": 800, "fondo_mm": 570},
    "BAV908057": {"ancho_mm": 900, "alto_mm": 800, "fondo_mm": 570},
    "BB2T458035": {"ancho_mm": 450, "alto_mm": 800, "fondo_mm": 350},
    "BB2T458057": {"ancho_mm": 450, "alto_mm": 800, "fondo_mm": 570},
    "BB2T608035": {"ancho_mm": 600, "alto_mm": 800, "fondo_mm": 350},
    "BB2T608057": {"ancho_mm": 600, "alto_mm": 800, "fondo_mm": 570},
    "BB2T908035": {"ancho_mm": 900, "alto_mm": 800, "fondo_mm": 350},
    "BB2T908057": {"ancho_mm": 900, "alto_mm": 800, "fondo_mm": 570},
    "BC158057": {"ancho_mm": 150, "alto_mm": 800, "fondo_mm": 570},
    "BC604035": {"ancho_mm": 600, "alto_mm": 400, "fondo_mm": 350},
    "BC604057": {"ancho_mm": 600, "alto_mm": 400, "fondo_mm": 570},
    "BCUB2T458057": {"ancho_mm": 450, "alto_mm": 800, "fondo_mm": 570},
    "BCUB2T608057": {"ancho_mm": 600, "alto_mm": 800, "fondo_mm": 570},
    "BCUB2T908057": {"ancho_mm": 900, "alto_mm": 800, "fondo_mm": 570},
    "BE2B608057": {"ancho_mm": 600, "alto_mm": 800, "fondo_mm": 570},
    "BE2B908057": {"ancho_mm": 900, "alto_mm": 800, "fondo_mm": 570},
    "BEBTS608057": {"ancho_mm": 600, "alto_mm": 800, "fondo_mm": 570},
    "BEBTS908057": {"ancho_mm": 900, "alto_mm": 800, "fondo_mm": 570},
    "BETO458057": {"ancho_mm": 450, "alto_mm": 800, "fondo_mm": 570},
    "BETO608057": {"ancho_mm": 600, "alto_mm": 800, "fondo_mm": 570},
    "BETO908057": {"ancho_mm": 900, "alto_mm": 800, "fondo_mm": 570},
    "BETOQ908057": {"ancho_mm": 900, "alto_mm": 800, "fondo_mm": 570},
    "BFT608057": {"ancho_mm": 600, "alto_mm": 800, "fondo_mm": 570},
    "BIBTS608057": {"ancho_mm": 600, "alto_mm": 800, "fondo_mm": 570},
    "BIBTS908057": {"ancho_mm": 900, "alto_mm": 800, "fondo_mm": 570},
    "FHABS6580": {"ancho_mm": 650, "alto_mm": 800, "fondo_mm": None},
    "H13010035": {"ancho_mm": 300, "alto_mm": 1000, "fondo_mm": 350},
    "H1306035": {"ancho_mm": 300, "alto_mm": 600, "fondo_mm": 350},
    "H1308035": {"ancho_mm": 300, "alto_mm": 800, "fondo_mm": 350},
    "H14510035": {"ancho_mm": 450, "alto_mm": 1000, "fondo_mm": 350},
    "H1456035": {"ancho_mm": 450, "alto_mm": 600, "fondo_mm": 350},
    "H1458035": {"ancho_mm": 450, "alto_mm": 800, "fondo_mm": 350},
    "H16010035": {"ancho_mm": 600, "alto_mm": 1000, "fondo_mm": 350},
    "H1606035": {"ancho_mm": 600, "alto_mm": 600, "fondo_mm": 350},
    "H1608035": {"ancho_mm": 600, "alto_mm": 800, "fondo_mm": 350},
    "H19010035": {"ancho_mm": 900, "alto_mm": 1000, "fondo_mm": 350},
    "H1906035": {"ancho_mm": 900, "alto_mm": 600, "fondo_mm": 350},
    "H1908035": {"ancho_mm": 900, "alto_mm": 800, "fondo_mm": 350},
    "HAV19010035": {"ancho_mm": 900, "alto_mm": 1000, "fondo_mm": 350},
    "HAV1906035": {"ancho_mm": 900, "alto_mm": 600, "fondo_mm": 350},
    "HAV1908035": {"ancho_mm": 900, "alto_mm": 800, "fondo_mm": 350},
    "HAV29010035": {"ancho_mm": 900, "alto_mm": 1000, "fondo_mm": 350},
    "HAV2906035": {"ancho_mm": 900, "alto_mm": 600, "fondo_mm": 350},
    "HAV2908035": {"ancho_mm": 900, "alto_mm": 800, "fondo_mm": 350},
    "HH16010035": {"ancho_mm": 600, "alto_mm": 1000, "fondo_mm": 350},
    "HH1606035": {"ancho_mm": 600, "alto_mm": 600, "fondo_mm": 350},
    "HH1608035": {"ancho_mm": 600, "alto_mm": 800, "fondo_mm": 350},
    "HH19010035": {"ancho_mm": 900, "alto_mm": 1000, "fondo_mm": 350},
    "HH1906035": {"ancho_mm": 900, "alto_mm": 600, "fondo_mm": 350},
    "HH1908035": {"ancho_mm": 900, "alto_mm": 800, "fondo_mm": 350},
    "HLVV57": {"ancho_mm": None, "alto_mm": None, "fondo_mm": 570},
    "HPT60V57": {"ancho_mm": 600, "alto_mm": None, "fondo_mm": 570},
    "HR45V35": {"ancho_mm": 450, "alto_mm": None, "fondo_mm": 350},
    "HR45V57": {"ancho_mm": 450, "alto_mm": None, "fondo_mm": 570},
    "HR60V35": {"ancho_mm": 600, "alto_mm": None, "fondo_mm": 350},
    "HR60V57": {"ancho_mm": 600, "alto_mm": None, "fondo_mm": 570},
    "PO1BIF4580": {"ancho_mm": 450, "alto_mm": 800, "fondo_mm": None},
    "PO1BIF6080": {"ancho_mm": 600, "alto_mm": 800, "fondo_mm": None},
    "PO2BIF4580": {"ancho_mm": 450, "alto_mm": 800, "fondo_mm": None},
    "PO2BIF6080": {"ancho_mm": 600, "alto_mm": 800, "fondo_mm": None},
    "POBIF4580": {"ancho_mm": 450, "alto_mm": 800, "fondo_mm": None},
    "POBIF6080": {"ancho_mm": 600, "alto_mm": 800, "fondo_mm": None},
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
    alto_str = f"{alto:03d}" if alto >= 100 else f"{alto:02d}"
    name_corregido = f"{family}{ancho_correcto:02d}{alto_str}{fondo:02d}{suffix_sub}"
    return name_corregido, None


# ── Catálogo de altos por código ──────────────────────────────────────────────
# Usado para validar LenZ (A21)

def _build_catalog_altos():
    """Build alto lookup from catalogo.json data embedded here."""
    import json as _json
    _cat = _json.loads('''
{"B308035": {"designaciones": {"es": "Mueble bajo con baldas, 1 puerta"}, "ancho_mm": 300, "alto_mm": 800, "fondo_mm": 350}, "B458035": {"designaciones": {"es": "Mueble bajo con baldas, 1 puerta"}, "ancho_mm": 450, "alto_mm": 800, "fondo_mm": 350}, "B608035": {"designaciones": {"es": "Mueble bajo con baldas, 1 puerta"}, "ancho_mm": 600, "alto_mm": 800, "fondo_mm": 350}, "B908035": {"designaciones": {"es": "Mueble bajo con baldas, 2 puertas"}, "ancho_mm": 900, "alto_mm": 800, "fondo_mm": 350}, "B308057": {"designaciones": {"es": "Mueble bajo con baldas, 1 puerta"}, "ancho_mm": 300, "alto_mm": 800, "fondo_mm": 570}, "B458057": {"designaciones": {"es": "Mueble bajo con baldas, 1 puerta"}, "ancho_mm": 450, "alto_mm": 800, "fondo_mm": 570}, "B608057": {"designaciones": {"es": "Mueble bajo con baldas, 1 puerta"}, "ancho_mm": 600, "alto_mm": 800, "fondo_mm": 570}, "B908057": {"designaciones": {"es": "Mueble bajo con baldas, 2 puertas"}, "ancho_mm": 900, "alto_mm": 800, "fondo_mm": 570}, "BB2T458035": {"designaciones": {"es": "Mueble bajo, 3 cajones"}, "ancho_mm": 450, "alto_mm": 800, "fondo_mm": 350}, "BB2T608035": {"designaciones": {"es": "Mueble bajo, 3 cajones"}, "ancho_mm": 600, "alto_mm": 800, "fondo_mm": 350}, "BB2T908035": {"designaciones": {"es": "Mueble bajo, 3 cajones"}, "ancho_mm": 900, "alto_mm": 800, "fondo_mm": 350}, "BB2T458057": {"designaciones": {"es": "Mueble bajo, 3 cajones"}, "ancho_mm": 450, "alto_mm": 800, "fondo_mm": 570}, "BB2T608057": {"designaciones": {"es": "Mueble bajo, 3 cajones"}, "ancho_mm": 600, "alto_mm": 800, "fondo_mm": 570}, "BB2T908057": {"designaciones": {"es": "Mueble bajo, 3 cajones"}, "ancho_mm": 900, "alto_mm": 800, "fondo_mm": 570}, "B2B458035": {"designaciones": {"es": "Mueble bajo, 2 cajones"}, "ancho_mm": 450, "alto_mm": 800, "fondo_mm": 350}, "B2B608035": {"designaciones": {"es": "Mueble bajo, 2 cajones"}, "ancho_mm": 600, "alto_mm": 800, "fondo_mm": 350}, "B2B908035": {"designaciones": {"es": "Mueble bajo, 2 cajones"}, "ancho_mm": 900, "alto_mm": 800, "fondo_mm": 350}, "B2B458057": {"designaciones": {"es": "Mueble bajo, 2 cajones"}, "ancho_mm": 450, "alto_mm": 800, "fondo_mm": 570}, "B2B608057": {"designaciones": {"es": "Mueble bajo, 2 cajones"}, "ancho_mm": 600, "alto_mm": 800, "fondo_mm": 570}, "B2B908057": {"designaciones": {"es": "Mueble bajo, 2 cajones"}, "ancho_mm": 900, "alto_mm": 800, "fondo_mm": 570}, "BC158057": {"designaciones": {"es": "Mueble bajo extra\u00edble"}, "ancho_mm": 150, "alto_mm": 800, "fondo_mm": 570}, "BC604035": {"designaciones": {"es": "Mueble de banco, 1 caj\u00f3n"}, "ancho_mm": 600, "alto_mm": 400, "fondo_mm": 350}, "BC604057": {"designaciones": {"es": "Mueble de banco, 1 caj\u00f3n"}, "ancho_mm": 600, "alto_mm": 400, "fondo_mm": 570}, "BFT608057": {"designaciones": {"es": "Mueble bajo para horno"}, "ancho_mm": 600, "alto_mm": 800, "fondo_mm": 570}, "BCUB2T458057": {"designaciones": {"es": "Mueble para placa, 3 cajones"}, "ancho_mm": 450, "alto_mm": 800, "fondo_mm": 570}, "BCUB2T608057": {"designaciones": {"es": "Mueble para placa, 3 cajones"}, "ancho_mm": 600, "alto_mm": 800, "fondo_mm": 570}, "BCUB2T908057": {"designaciones": {"es": "Mueble para placa, 3 cajones"}, "ancho_mm": 900, "alto_mm": 800, "fondo_mm": 570}, "BIBTS608057": {"designaciones": {"es": "Mueble para placa aspirante, 2 cajones, 1 fijo"}, "ancho_mm": 600, "alto_mm": 800, "fondo_mm": 570}, "BIBTS908057": {"designaciones": {"es": "Mueble para placa aspirante, 2 cajones, 1 fijo"}, "ancho_mm": 900, "alto_mm": 800, "fondo_mm": 570}, "BETO458057": {"designaciones": {"es": "Mueble para fregadero, 1 puerta"}, "ancho_mm": 450, "alto_mm": 800, "fondo_mm": 570}, "BETO608057": {"designaciones": {"es": "Mueble para fregadero, 1 puerta"}, "ancho_mm": 600, "alto_mm": 800, "fondo_mm": 570}, "BETO908057": {"designaciones": {"es": "Mueble para fregadero, 2 puertas"}, "ancho_mm": 900, "alto_mm": 800, "fondo_mm": 570}, "BETOQ908057": {"designaciones": {"es": "Mueble para fregadero, 2 puertas (equipado con cubos de basura)"}, "ancho_mm": 900, "alto_mm": 800, "fondo_mm": 570}, "BE2B608057": {"designaciones": {"es": "Mueble para fregadero, 2 cajones"}, "ancho_mm": 600, "alto_mm": 800, "fondo_mm": 570}, "BE2B908057": {"designaciones": {"es": "Mueble para fregadero, 2 cajones"}, "ancho_mm": 900, "alto_mm": 800, "fondo_mm": 570}, "BEBTS608057": {"designaciones": {"es": "Mueble para fregadero, 3 cajones"}, "ancho_mm": 600, "alto_mm": 800, "fondo_mm": 570}, "BEBTS908057": {"designaciones": {"es": "Mueble para fregadero, 3 cajones"}, "ancho_mm": 900, "alto_mm": 800, "fondo_mm": 570}, "POBIF4580": {"designaciones": {"es": "Puerta completa para LVV y LVD integrables"}, "ancho_mm": 450, "alto_mm": 800, "fondo_mm": null}, "POBIF6080": {"designaciones": {"es": "Puerta completa para LVV y LVD integrables"}, "ancho_mm": 600, "alto_mm": 800, "fondo_mm": null}, "PO2BIF4580": {"designaciones": {"es": "Puerta completa para LVV y LVD integrables"}, "ancho_mm": 450, "alto_mm": 800, "fondo_mm": null}, "PO2BIF6080": {"designaciones": {"es": "Puerta completa para LVV y LVD integrables"}, "ancho_mm": 600, "alto_mm": 800, "fondo_mm": null}, "PO1BIF4580": {"designaciones": {"es": "Puerta completa para LVV y LVD integrables"}, "ancho_mm": 450, "alto_mm": 800, "fondo_mm": null}, "PO1BIF6080": {"designaciones": {"es": "Puerta completa para LVV y LVD integrables"}, "ancho_mm": 600, "alto_mm": 800, "fondo_mm": null}, "FHABS6580": {"designaciones": {"es": "Puerta para LVV y LVD no integrables"}, "ancho_mm": 650, "alto_mm": 800, "fondo_mm": null}, "BAV908057": {"designaciones": {"es": "Mueble bajo esquinero con baldas, 1 puerta"}, "ancho_mm": 900, "alto_mm": 800, "fondo_mm": 570}, "BAV1208057": {"designaciones": {"es": "Mueble bajo esquinero con baldas, 1 puerta"}, "ancho_mm": 1200, "alto_mm": 800, "fondo_mm": 570}, "BAV1P908057": {"designaciones": {"es": "Mueble bajo esquinero con accesorio extra\u00edble, 1 puerta"}, "ancho_mm": 900, "alto_mm": 800, "fondo_mm": 570}, "BAV1P1208057": {"designaciones": {"es": "Mueble bajo esquinero con accesorio extra\u00edble, 1 puerta"}, "ancho_mm": 1200, "alto_mm": 800, "fondo_mm": 570}, "H1306035": {"designaciones": {"es": "Mueble de pared con baldas, 1 puerta"}, "ancho_mm": 300, "alto_mm": 600, "fondo_mm": 350}, "H1456035": {"designaciones": {"es": "Mueble de pared con baldas, 1 puerta"}, "ancho_mm": 450, "alto_mm": 600, "fondo_mm": 350}, "H1606035": {"designaciones": {"es": "Mueble de pared con baldas, 1 puerta"}, "ancho_mm": 600, "alto_mm": 600, "fondo_mm": 350}, "H1906035": {"designaciones": {"es": "Mueble de pared con baldas, 2 puertas"}, "ancho_mm": 900, "alto_mm": 600, "fondo_mm": 350}, "H1308035": {"designaciones": {"es": "Mueble de pared con baldas, 1 puerta"}, "ancho_mm": 300, "alto_mm": 800, "fondo_mm": 350}, "H1458035": {"designaciones": {"es": "Mueble de pared con baldas, 1 puerta"}, "ancho_mm": 450, "alto_mm": 800, "fondo_mm": 350}, "H1608035": {"designaciones": {"es": "Mueble de pared con baldas, 1 puerta"}, "ancho_mm": 600, "alto_mm": 800, "fondo_mm": 350}, "H1908035": {"designaciones": {"es": "Mueble de pared con baldas, 2 puertas"}, "ancho_mm": 900, "alto_mm": 800, "fondo_mm": 350}, "H13010035": {"designaciones": {"es": "Mueble de pared con baldas, 1 puerta"}, "ancho_mm": 300, "alto_mm": 1000, "fondo_mm": 350}, "H14510035": {"designaciones": {"es": "Mueble de pared con baldas, 1 puerta"}, "ancho_mm": 450, "alto_mm": 1000, "fondo_mm": 350}, "H16010035": {"designaciones": {"es": "Mueble de pared con baldas, 1 puerta"}, "ancho_mm": 600, "alto_mm": 1000, "fondo_mm": 350}, "H19010035": {"designaciones": {"es": "Mueble de pared con baldas, 2 puertas"}, "ancho_mm": 900, "alto_mm": 1000, "fondo_mm": 350}, "HH1606035": {"designaciones": {"es": "Mueble para campana, 1 puerta"}, "ancho_mm": 600, "alto_mm": 600, "fondo_mm": 350}, "HH1906035": {"designaciones": {"es": "Mueble para campana, 2 puertas"}, "ancho_mm": 900, "alto_mm": 600, "fondo_mm": 350}, "HH1608035": {"designaciones": {"es": "Mueble para campana, 1 puerta"}, "ancho_mm": 600, "alto_mm": 800, "fondo_mm": 350}, "HH1908035": {"designaciones": {"es": "Mueble para campana, 2 puertas"}, "ancho_mm": 900, "alto_mm": 800, "fondo_mm": 350}, "HH16010035": {"designaciones": {"es": "Mueble para campana, 1 puerta"}, "ancho_mm": 600, "alto_mm": 1000, "fondo_mm": 350}, "HH19010035": {"designaciones": {"es": "Mueble para campana, 2 puertas"}, "ancho_mm": 900, "alto_mm": 1000, "fondo_mm": 350}, "HAV1906035": {"designaciones": {"es": "Mueble de pared esquinero con baldas, 1 puerta (45cm)"}, "ancho_mm": 900, "alto_mm": 600, "fondo_mm": 350}, "HAV1908035": {"designaciones": {"es": "Mueble de pared esquinero con baldas, 1 puerta (45cm)"}, "ancho_mm": 900, "alto_mm": 800, "fondo_mm": 350}, "HAV19010035": {"designaciones": {"es": "Mueble de pared esquinero con baldas, 1 puerta (45cm)"}, "ancho_mm": 900, "alto_mm": 1000, "fondo_mm": 350}, "HAV2906035": {"designaciones": {"es": "Mueble de pared esquinero con baldas, 1 puerta (60cm)"}, "ancho_mm": 900, "alto_mm": 600, "fondo_mm": 350}, "HAV2908035": {"designaciones": {"es": "Mueble de pared esquinero con baldas, 1 puerta (60cm)"}, "ancho_mm": 900, "alto_mm": 800, "fondo_mm": 350}, "HAV29010035": {"designaciones": {"es": "Mueble de pared esquinero con baldas, 1 puerta (60cm)"}, "ancho_mm": 900, "alto_mm": 1000, "fondo_mm": 350}, "HR45V35": {"designaciones": {"es": "Altillo de altura variable con baldas, 1 puerta"}, "ancho_mm": 450, "alto_mm": null, "fondo_mm": 350, "alto_variable": {"min": 200, "max": 1000}}, "HR60V35": {"designaciones": {"es": "Altillo de altura variable con baldas, 1 puerta"}, "ancho_mm": 600, "alto_mm": null, "fondo_mm": 350, "alto_variable": {"min": 200, "max": 1000}}, "HR45V57": {"designaciones": {"es": "Altillo de altura variable con baldas, 1 puerta"}, "ancho_mm": 450, "alto_mm": null, "fondo_mm": 570, "alto_variable": {"min": 200, "max": 1000}}, "HR60V57": {"designaciones": {"es": "Altillo de altura variable con baldas, 1 puerta"}, "ancho_mm": 600, "alto_mm": null, "fondo_mm": 570, "alto_variable": {"min": 200, "max": 1000}}, "HLVV57": {"designaciones": {"es": "Altillo de altura variable con baldas, 1 puerta (apertura lift)"}, "ancho_mm": null, "alto_mm": null, "fondo_mm": 570, "ancho_variable": {"min": 450, "max": 1200}, "alto_variable": {"min": 200, "max": 400}}, "HPT60V57": {"designaciones": {"es": "Mueble sobre encimera de altura variable con baldas, 1 puerta"}, "ancho_mm": 600, "alto_mm": null, "fondo_mm": 570, "alto_variable": {"min": 110, "max": 140}}, "AVA4520035": {"designaciones": {"es": "Columna con baldas, 2 puertas"}, "ancho_mm": 450, "alto_mm": 2000, "fondo_mm": 350}, "AVA6020035": {"designaciones": {"es": "Columna con baldas, 2 puertas"}, "ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 350}, "AVA4522035": {"designaciones": {"es": "Columna con baldas, 2 puertas"}, "ancho_mm": 450, "alto_mm": 2200, "fondo_mm": 350}, "AVA6022035": {"designaciones": {"es": "Columna con baldas, 2 puertas"}, "ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 350}, "AVA4520057": {"designaciones": {"es": "Columna con baldas, 2 puertas"}, "ancho_mm": 450, "alto_mm": 2000, "fondo_mm": 570}, "AVA6020057": {"designaciones": {"es": "Columna con baldas, 2 puertas"}, "ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 570}, "AVA4522057": {"designaciones": {"es": "Columna con baldas, 2 puertas"}, "ancho_mm": 450, "alto_mm": 2200, "fondo_mm": 570}, "AVA6022057": {"designaciones": {"es": "Columna con baldas, 2 puertas"}, "ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 570}, "AVA1P4520035": {"designaciones": {"es": "Columna con baldas, 1 puerta"}, "ancho_mm": 450, "alto_mm": 2000, "fondo_mm": 350}, "AVA1P6020035": {"designaciones": {"es": "Columna con baldas, 1 puerta"}, "ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 350}, "AVA1P9020035": {"designaciones": {"es": "Columna con baldas, 2 puertas"}, "ancho_mm": 900, "alto_mm": 2000, "fondo_mm": 350}, "AVA1P4520057": {"designaciones": {"es": "Columna con baldas, 1 puerta"}, "ancho_mm": 450, "alto_mm": 2000, "fondo_mm": 570}, "AVA1P6020057": {"designaciones": {"es": "Columna con baldas, 1 puerta"}, "ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 570}, "AVA1P4522035": {"designaciones": {"es": "Columna con baldas, 1 puerta"}, "ancho_mm": 450, "alto_mm": 2200, "fondo_mm": 350}, "AVA1P6022035": {"designaciones": {"es": "Columna con baldas, 1 puerta"}, "ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 350}, "AVA1P9022035": {"designaciones": {"es": "Columna con baldas, 2 puertas"}, "ancho_mm": 900, "alto_mm": 2200, "fondo_mm": 350}, "AVA1P4522057": {"designaciones": {"es": "Columna con baldas, 1 puerta"}, "ancho_mm": 450, "alto_mm": 2200, "fondo_mm": 570}, "AVA1P6022057": {"designaciones": {"es": "Columna con baldas, 1 puerta"}, "ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 570}, "AQC34520057": {"designaciones": {"es": "Columna con 5 cajones interiores, 2 puertas"}, "ancho_mm": 450, "alto_mm": 2000, "fondo_mm": 570}, "AQC36020057": {"designaciones": {"es": "Columna con 5 cajones interiores, 2 puertas"}, "ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 570}, "AQC34522057": {"designaciones": {"es": "Columna con 5 cajones interiores, 2 puertas"}, "ancho_mm": 450, "alto_mm": 2200, "fondo_mm": 570}, "AQC36022057": {"designaciones": {"es": "Columna con 5 cajones interiores, 2 puertas"}, "ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 570}, "AQC31P4520057": {"designaciones": {"es": "Columna con 5 cajones interiores, 1 puerta"}, "ancho_mm": 450, "alto_mm": 2000, "fondo_mm": 570}, "AQC31P6020057": {"designaciones": {"es": "Columna con 5 cajones interiores, 1 puerta"}, "ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 570}, "AQC31P4522057": {"designaciones": {"es": "Columna con 5 cajones interiores, 1 puerta"}, "ancho_mm": 450, "alto_mm": 2200, "fondo_mm": 570}, "AQC31P6022057": {"designaciones": {"es": "Columna con 5 cajones interiores, 1 puerta"}, "ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 570}, "ABA6020057": {"designaciones": {"es": "Mueble escobero, 2 puertas"}, "ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 570}, "ABA6022057": {"designaciones": {"es": "Mueble escobero, 2 puertas"}, "ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 570}, "AFS6020057": {"designaciones": {"es": "Columna para horno o micro, 1 puerta"}, "ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 570}, "AFS6022057": {"designaciones": {"es": "Columna para horno o micro, 1 puerta"}, "ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 570}, "AFS2B6020057": {"designaciones": {"es": "Columna para horno o micro, 1 puerta, 2 cajones"}, "ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 570}, "AFS2B6022057": {"designaciones": {"es": "Columna para horno o micro, 1 puerta, 2 cajones"}, "ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 570}, "AFSMO6020057": {"designaciones": {"es": "Columna para horno+micro, 1 puerta"}, "ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 570}, "AFSMO6022057": {"designaciones": {"es": "Columna para horno+micro, 1 puerta"}, "ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 570}, "AFSMOBT6020057": {"designaciones": {"es": "Columna para horno+micro, 1 puerta, 2 cajones"}, "ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 570}, "AFSMOBT6022057": {"designaciones": {"es": "Columna para horno+micro, 1 puerta, 2 cajones"}, "ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 570}, "A2I6020057": {"designaciones": {"es": "Columna para frigor\u00edfico integrable, 2 puertas"}, "ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 570}, "A2I6022057": {"designaciones": {"es": "Columna para frigor\u00edfico integrable, 2 puertas"}, "ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 570}, "A2I7522057": {"designaciones": {"es": "Columna para frigor\u00edfico integrable, 2 puertas"}, "ancho_mm": 750, "alto_mm": 2200, "fondo_mm": 570}, "A2I1P6020057": {"designaciones": {"es": "Columna para frigor\u00edfico integrable, 1 puerta"}, "ancho_mm": 600, "alto_mm": 2000, "fondo_mm": 570}, "A2I1P6022057": {"designaciones": {"es": "Columna para frigor\u00edfico integrable, 1 puerta"}, "ancho_mm": 600, "alto_mm": 2200, "fondo_mm": 570}, "AGM9020057": {"designaciones": {"es": "Mueble de despensa, 4 puertas"}, "ancho_mm": 900, "alto_mm": 2000, "fondo_mm": 570}, "AGM9022057": {"designaciones": {"es": "Mueble de despensa, 4 puertas"}, "ancho_mm": 900, "alto_mm": 2200, "fondo_mm": 570}}
    ''')
    altos = {}
    for code, data in _cat.items():
        alto = data.get('alto_mm')
        if alto is not None:
            altos[code] = alto
        elif data.get('alto_variable'):
            altos[code] = 0  # variable — use range check
    return altos

CATALOG_ALTOS = _build_catalog_altos()

LENZ_TOLERANCIA_MM = 5  # tolerancia para comparación de alto

# Rangos para muebles con dimensiones variables
RANGOS_VARIABLES = {
    'HLVV': {'ancho_min': 450, 'ancho_max': 1200, 'alto_min': 200, 'alto_max': 400},
    'HR':   {'ancho_min': None, 'ancho_max': None, 'alto_min': 200, 'alto_max': 1000},  # ancho fijo por código → validado por CATALOG_WIDTHS
    'HPT':  {'ancho_min': 600, 'ancho_max': 600, 'alto_min': 1100, 'alto_max': 1400},
}

# Muebles sin apertura — fuente: opciones_mueble.yaml p_hinge (nulo + coulissant)
CODIGOS_SIN_APERTURA = {
    'AGM9020057',
    'AGM9022057',
    'AVA1P9020035',
    'AVA1P9022035',
    'B2B458035',
    'B2B458057',
    'B2B608035',
    'B2B608057',
    'B2B908035',
    'B2B908057',
    'B908035',
    'B908057',
    'BB2T458035',
    'BB2T458057',
    'BB2T608035',
    'BB2T608057',
    'BB2T908035',
    'BB2T908057',
    'BC158057',
    'BC604035',
    'BC604057',
    'BCUB2T458057',
    'BCUB2T608057',
    'BCUB2T908057',
    'BE2B608057',
    'BE2B908057',
    'BEBTS608057',
    'BEBTS908057',
    'BETO908057',
    'BETOQ908057',
    'BFT608057',
    'BIBTS608057',
    'BIBTS908057',
    'FHABS6580',
    'H19010035',
    'H1906035',
    'H1908035',
    'HH19010035',
    'HH1906035',
    'HH1908035',
    'PO1BIF4580',
    'PO1BIF6080',
    'PO2BIF4580',
    'PO2BIF6080',
    'POBIF4580',
    'POBIF6080',
}

# Muebles sin op. 231 — fuente: opciones_mueble.yaml op_231 (muebles que NO están en la lista)
CODIGOS_SIN_OP231 = {
    'A2I1P6020057',
    'A2I1P6022057',
    'A2I6020057',
    'A2I6022057',
    'A2I7522057',
    'AFS2B6020057',
    'AFS2B6022057',
    'AFS6020057',
    'AFS6022057',
    'AFSMO6020057',
    'AFSMO6022057',
    'AFSMOBT6020057',
    'AFSMOBT6022057',
    'AGM9020057',
    'AGM9022057',
    'AQC31P4520057',
    'AQC31P4522057',
    'AQC31P6020057',
    'AQC31P6022057',
    'AQC34520057',
    'AQC34522057',
    'AQC36020057',
    'AQC36022057',
    'AVA1P9020035',
    'AVA1P9022035',
    'B2B458035',
    'B2B458057',
    'B2B608035',
    'B2B608057',
    'B2B908035',
    'B2B908057',
    'B908035',
    'B908057',
    'BAV1208057',
    'BAV1P1208057',
    'BAV1P908057',
    'BAV908057',
    'BB2T458035',
    'BB2T458057',
    'BB2T608035',
    'BB2T608057',
    'BB2T908035',
    'BB2T908057',
    'BC158057',
    'BC604035',
    'BC604057',
    'BCUB2T458057',
    'BCUB2T608057',
    'BCUB2T908057',
    'BE2B608057',
    'BE2B908057',
    'BEBTS608057',
    'BEBTS908057',
    'BETO458057',
    'BETO608057',
    'BETO908057',
    'BETOQ908057',
    'BFT608057',
    'BIBTS608057',
    'BIBTS908057',
    'FHABS6580',
    'H19010035',
    'H1906035',
    'H1908035',
    'HAV19010035',
    'HAV1906035',
    'HAV1908035',
    'HAV29010035',
    'HAV2906035',
    'HAV2908035',
    'HH16010035',
    'HH1606035',
    'HH1608035',
    'HH19010035',
    'HH1906035',
    'HH1908035',
    'HLVV57',
    'HPT60V57',
    'HR45V35',
    'HR45V57',
    'HR60V35',
    'HR60V57',
    'PO1BIF4580',
    'PO1BIF6080',
    'PO2BIF4580',
    'PO2BIF6080',
    'POBIF4580',
    'POBIF6080',
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
                elif name_raw in CATALOGO_JSON:
                    ancho_std = CATALOGO_JSON[name_raw].get('ancho_mm')
                    if ancho_std and abs(ancho_mm - ancho_std) > 5:
                        avisos.append(
                            f"Ancho incorrecto: el mueble mide {ancho_mm:.0f}mm, el catálogo indica {ancho_std}mm"
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

        # A05 · Color del interior (no aplica a fachadas)
        CODIGOS_SIN_INTERIOR = {'PO1BIF4580', 'PO1BIF6080', 'PO2BIF4580', 'PO2BIF6080', 'POBIF4580', 'POBIF6080'}
        color_interior = _str_or_none(fila.get("Color del interior", ""))
        if color_interior is None and name_raw not in CODIGOS_SIN_INTERIOR:
            avisos.append(
                "Falta el color del interior"
            )
        # A13 · Color del interior no reconocido
        elif color_interior not in COLOR_INTERIOR_VALIDOS and name_raw not in CODIGOS_SIN_INTERIOR:
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

