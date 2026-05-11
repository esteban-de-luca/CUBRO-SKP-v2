# CLAUDE.md — Proyecto HbM CUBRO × Schmidt Groupe

> Este archivo es el puente de contexto para Claude Code. Lee esto antes de tocar nada.
> Última actualización: 10/05/2026 (cierre de arquitectura del Módulo B).

---

## 1. Qué es este proyecto

CUBRO ha desarrollado un catálogo de muebles de cocina fabricados por **Schmidt Groupe (SG)**. Para hacer pedidos a SG, cada mueble debe enviarse con un conjunto de opciones variantes — parámetros de configuración con códigos que definen acabados, mecanismos y equipamiento.

Este repositorio construye una **app interna en Streamlit** que automatiza ese proceso: el equipo de CUBRO sube el CSV exportado desde SketchUp, la app aplica toda la lógica de opciones automáticamente y genera el archivo de export hacia DealHub.

**Flujo general:**
```
SketchUp → Export CSV → Módulo A (validación) → Módulo B (UI Paso 1)
                                                       ↓
                                              Módulo C (mapeo)
                                                       ↓
                                              Módulo B (UI Paso 2 + export)
                                                       ↓
                                                  DealHub → SG
```

**Despliegue:** Streamlit Cloud (plan gratuito → repo público).
**Repo:** https://github.com/luciarodriguez-cpu/CUBRO-skp
**URL pública:** https://cubro-skp-hmtqcrnptzyqww353nataj.streamlit.app

---

## 2. Equipo y propiedad de archivos

| Persona | Módulo | Archivo Python | Rama Git | Email |
|---|---|---|---|---|
| Javier | A — Validación CSV | `modulo_a.py` | `feature/modulo-a` | javier.abad@cubrodesign.com |
| Esteban | B — Interfaz y selección | `modulo_b.py` | `feature/modulo-b` | esteban.deluca@cubrodesign.com |
| Lucía | C — Mapeo y cálculo | `modulo_c.py` | `feature/modulo-c` | lucia.rodriguez@cubrodesign.com |

**Reglas Git inviolables:**
- Nadie hace push a `main` directamente.
- Cada persona trabaja exclusivamente en su rama.
- Los merges a `main` se coordinan entre los tres antes de integrar.

**Reglas de archivos:**
- `modulo_X.py` → solo lo toca su responsable.
- `data/*.yaml` y `data/catalogo.json` → archivos compartidos. Cualquier cambio debe comunicarse al equipo **antes** de push.

---

## 3. Quién soy yo en este contexto

Estás interactuando con **Esteban**, responsable del Módulo B. Por tanto:

- Solo se modifica `modulo_b.py` y `app.py` (la orquestación general también es responsabilidad del Módulo B, ya que B es la UI).
- **NO se modifican** `modulo_a.py`, `modulo_c.py`, `data/mapeos.yaml`, `data/reglas.yaml` ni `data/catalogo.json` sin coordinación explícita.
- Si una decisión arquitectónica afecta a A o C, hay que documentarla y avisar a Javier/Lucía — no modificar sus archivos.

---

## 4. Principio rector: separación lógica / datos

**Python contiene lógica. YAML/JSON contienen datos.**

- Si cambia una regla de negocio → se edita `data/reglas.yaml`, no `modulo_c.py`.
- Si cambia un código SG, un mapeo de colores o una etiqueta UI → se edita `data/mapeos.yaml`.
- Si cambia el catálogo de muebles → se edita `data/catalogo.json`.

El código Python debería ser estable; los YAML/JSON evolucionan.

---

## 5. Stack y arranque

- **Lenguaje:** Python 3
- **Framework:** Streamlit
- **Dependencias:** ver `requirements.txt` (streamlit, pandas, pyyaml)

**Arrancar la app localmente:**
```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 6. Estructura del repo

```
CUBRO-skp/
├── app.py                  # Orquestación Streamlit (A → B → C → B). Lo gestiona Esteban.
├── modulo_a.py             # Javier
├── modulo_b.py             # Esteban ← TU TRABAJO
├── modulo_c.py             # Lucía
├── data/
│   ├── catalogo.json       # 121 muebles. Generado 10/05/2026.
│   ├── mapeos.yaml         # CSV → UI → SG.
│   └── reglas.yaml         # Opciones forzadas y facultativas por mueble.
├── assets/                 # (pendiente de crear)
│   └── logo_cubro.png      # (pendiente de subir)
├── requirements.txt
├── README.md
└── CLAUDE.md               # este archivo
```

---

## 7. Arquitectura del Módulo B (cerrada el 10/05/2026)

El Módulo B es la UI. Interviene en DOS momentos del flujo:

### Paso 1 — Selección de opciones opcionales (antes del Módulo C)
- Recibe del Módulo A: `list[dict]`, un dict por mueble con datos del CSV validados.
- Recibe del usuario: selección de opciones opcionales por mueble.
- Envía al Módulo C: `list[dict]` original + dict de opciones seleccionadas.

### Paso 2 — Revisión y export (después del Módulo C)
- Recibe del Módulo C: pedido completo con todas las opciones SG calculadas.
- Muestra al usuario para revisión final.
- Genera el archivo de export para DealHub (PENDIENTE — placeholder por ahora).

### Tres pantallas en total

**Pantalla 0 — Validación de errores del CSV** (entre A y Paso 1):
- Si hay errores (cualquier mueble con `Estado = ⚠️ REVISAR`) → tabla con `Name SKP` + `Avisos`, mensaje de cabecera, botón para volver a subir CSV, **bloqueo de avance**.
- Si no hay errores → cartel verde y avance directo al Paso 1.

**Paso 1:**
- Cabecera global: `X muebles · Y revisados · Z pendientes` (actualización en vivo) + acciones `[Expandir todas] [Colapsar todas] [☐ Solo pendientes]`.
- Cards plegables, una por mueble, en orden del CSV.
- Cabecera plegada: `[check] · Name · Designación · Gama Color · Tirador Color` (sin apertura ni reducción).
- Card abierta: bloque informativo (Apertura · Ancho · Color interior · Rodapié) → controles opcionales con tooltips → divisor → bloque op_126 (4 textos: Marca / Referencia / Altura / Tipo) → check explícito.
- Sistema de check: explícito, bloquea avance, reset al editar, auto-cierre al marcar, pre-check para muebles sin opcionales.
- Botón "Continuar al Paso 2" solo al final, avance directo.

**Paso 2:**
- Panel resumen arriba: ✅ verde si todo limpio, ❌ rojo si hay errores duros.
- Cards-resumen siempre visibles (NO plegables), una por mueble, lenguaje UI.
- Tres bloques por card: Configuración · Dimensiones · Opciones adicionales (este último solo si tiene contenido).
- Distinción de origen por bloque (no campo a campo). Marcador `⚙ automático` en líneas de "Opciones adicionales" forzadas por reglas (no elegidas por el usuario).
- Botón `[Ver detalle técnico ▾]` detrás de feature flag (`MOSTRAR_DETALLE_TECNICO = True` inicialmente).
- Botón `[Exportar a DealHub]` siempre deshabilitado por ahora con tooltip explicativo.

### Sidebar (presente en TODAS las pantallas)

1. Logo CUBRO (PNG pendiente)
2. Uploader del CSV
3. Nombre del archivo cargado
4. Fecha y hora de subida
5. Número de muebles detectados
6. Botón "Subir otro CSV"

**Comportamiento al subir CSV nuevo en medio del flujo:**
- Sin progreso → carga directa.
- Con progreso (al menos 1 check marcado o 1 opcional configurada) → modal de confirmación bloqueante.

---

## 8. Lenguaje UI — regla inviolable

**Toda etiqueta visible al usuario debe estar en español natural, nunca con códigos técnicos.**

Diccionario CSV → UI que aplica el Módulo B:

| Campo CSV | Lo que llega | Lo que muestra la UI |
|---|---|---|
| `Apertura` | `1` / `I` / `izquierda` | Izquierda |
|  | `2` / `D` / `derecha` | Derecha |
|  | `3` / `horizontal` | Lift |
| `D_Gama` | `1` / `2` / `3` / `4` | LACA / WOOD / LINOLEO / LAMINADO |
| `ColorFrente` | `Crema LACA`, `Oak WOOD`, etc. | Crema, Oak… *(sin sufijo)* |
| `Color del interior` | `Blanco mueble`, `Gris mueble`… | Blanco, Gris, Negro, Roble |
| `Tirador` | `2` / `3` / `4` / `5` / `7` / `20` / `21` | Round / Square / Curve / Line / Plantea / Touch Latch / Prise de main |
| `Trasera` (integrado) | `Laca`, `Oak WOOD`… | *(Round/Square: copiar color del frente si "Laca")*, Oak, etc. |
| `Color tir. de superficie` | `Inox`, `Brass`… | Inox, Brass… *(igual)* |
| `C_Rodapietext` | `70 mm` / `100 mm` / `0 mm` | 70 mm / 100 mm / Sin patas |
| `Ancho` | `10000 mm` / valor real | *(si 10000)* "Reducción de ancho" / valor en mm |

**Caso especial — tirador con Trasera = Laca:**
En cabecera de card y card-resumen, mostrar el color real del frente (ej. "Round **Crema**"), NO la palabra "Laca".

**Caso especial — tiradores sin color (Touch Latch, Prise de main):**
Mostrar solo el nombre del tirador, sin color.

---

## 9. Schema de los datos

### Output del Módulo A → Input del Módulo B

`list[dict]`, un dict por mueble. Columnas reales del CSV de output:

```
Name · Name SKP · Estado · Apertura · D_Gama · ColorFrente ·
Color del interior · Tirador · Trasera · Color tir. de superficie ·
C_Rodapietext · Ancho · Ancho reducido · LenZ · Avisos
```

- `Estado`: `✅ CORRECTO` o `⚠️ REVISAR`. Si REVISAR → bloquea avance.
- `Avisos`: string concatenada con ` | ` (con espacios). Códigos posibles: A02, A05, A09, A10, A11, A12, A17, A21, A22, A23, E07, CB12.
- `Name SKP`: nombre original que vino de SketchUp. Siempre presente (úsalo como identificador en UI cuando `Name` esté vacío o no resuelto).

### `data/catalogo.json`

121 muebles. Schema por entrada:

```json
{
  "B608035": {
    "name": "B608035",
    "tipo": "B",
    "familia": "Bajos",
    "subfamilia": "Almacenamiento",
    "designaciones": { "es": "Bajo 1 puerta" },
    "ancho_mm": 600,
    "alto_mm": 800,
    "fondo_mm": 350,
    "diferenciador": "Mueble bajo con 1 o 2 puertas batientes y 2 baldas fijas..."
  }
}
```

- `designaciones` es un dict (no string) → extensible a `"en"`, `"fr"`, etc. sin migrar.
- Campos opcionales `alto_variable: {min, max}` y `ancho_variable: {min, max}` cuando aplican (HR, HLVV, HPT).
- `fondo_mm: null` para frentes sin mueble (POBIF, FHABS).

### `data/mapeos.yaml`

Tablas de conversión:
- `D_Gama` → op. 100 (gama del frente)
- `ColorFrente` → op. 101 (acabado del frente)
- `Color del interior` → op. 200 (color interior)
- `Tirador` → op. 217 (apertura) y op. 300 (tipo de tirador)
- `Color tirador` / `Trasera` → op. 301 (color del tirador)
- `C_Rodapietext` → op. 402 (altura de patas)

Sección `interfaz` lista las 8 opciones opcionales que B debe presentar al usuario:
- `op_121` Sin mecanizado para tirador (checkbox, sujeto a reglas condicionales)
- `op_207_opcional` Cubos de basura (checkbox, solo BE2B y BEBTS)
- `op_220` Recorte para perfil LED (checkbox, solo H1)
- `op_222` Sensor para mando LED (radio: ninguno/derecha/izquierda, solo H1)
- `op_223` Cajón interior (checkbox)
- `op_227` Mueble de caldera (checkbox)
- `op_700_opcional` Mueble sin encolar (checkbox)
- `op_126` Electrodoméstico (bloque de 4 textos libres: marca, referencia, altura, tipo; solo BFT y AFS). El valor en `opcionales["op_126"]` es un `dict[str, str]` con las 4 keys. Los 4 campos son obligatorios para poder marcar el mueble como revisado.

### `data/reglas.yaml`

Define por mueble qué opciones están forzadas (y su valor) y qué facultativas están disponibles. **El Módulo C aplica estas reglas, no el Módulo B.** Pero B necesita conocer las facultativas aplicables a cada mueble para mostrar solo los controles relevantes.

---

## 10. Lo que el Módulo B NO hace

- **No valida el CSV** → responsabilidad de A.
- **No aplica lógica de mapeo a códigos SG** → responsabilidad de C.
- **No calcula opciones forzadas por reglas** → responsabilidad de C.
- **No filtra qué facultativas aplican a cada mueble por reglas condicionales complejas** → idealmente C expone una función para esto (ver pendientes).

El Módulo B es "tonto" — recibe datos, los presenta en lenguaje UI, recoge selección del usuario, y los pasa al siguiente módulo.

---

## 11. Pendientes

### Pendientes del Módulo B (a resolver durante implementación)

- Subir `data/catalogo.json` al repo (el archivo ya está generado).
- Subir logo CUBRO PNG a `assets/logo_cubro.png`.
- Redactar textos de tooltips de los controles opcionales (con la app delante).
- Definir contrato exacto del output del Paso 1 hacia C (coordinarse con Lucía).
- Decidir si B carga `catalogo.json` directamente o se delega en una función helper.

### Pendientes que afectan al Módulo B pero dependen de otros

| Punto | Bloquea | Responsable |
|---|---|---|
| Schema export DealHub | Solo el botón final del Paso 2 (placeholder por ahora, OK seguir) | Equipo |
| Quién filtra facultativas según reglas condicionales (op_121 etc.) | El Paso 1 | Acordar con Lucía |
| Origen de cada opción en el output de C (CSV / forzada / usuario) | El marcador `⚙ automático` del Paso 2 | Lucía |
| Confirmar contrato del campo Apertura (lenguaje natural vs códigos) | Robustez del módulo | Javier |
| Doc Módulo A — columnas no documentadas (Name SKP, Estado, LenZ, Avisos) y códigos aviso A17/A21/A22/A23 | Solo documentación | Javier |
| Doc Módulo C — copy-paste donde dice "Módulo B" en lugar de "C" | Solo documentación | Lucía |

---

## 12. Convenciones de código

- **Idioma**: identificadores en inglés cuando son técnicos (Streamlit, pandas), comentarios y strings de UI en español.
- **No usar `eval`, `exec`, ni código dinámico inseguro.**
- **Manejo de estado**: usar `st.session_state` para persistencia entre interacciones.
- **Modularidad**: si una función del Módulo B crece más de ~50 líneas, considerar dividirla.
- **Sin reinventar la rueda**: Streamlit tiene componentes nativos suficientes para todo lo decidido (no se requieren librerías externas exóticas).

---

## 13. Preferencias de Esteban

- **Idioma**: español de España. Tecnicismos en inglés permitidos, pero traducidos cuando se introducen.
- **No generar código sin que se pida explícitamente.** Antes de implementar algo, confirmar.
- **Lenguaje UI siempre** — nunca exponer `op_XXX`, códigos SG ni jerga técnica al usuario final.
- **Confirmar antes de modificar Notion o archivos compartidos** (`data/*.yaml`, `data/catalogo.json`).
- **Mantener trazabilidad**: cuando se haga un cambio significativo, dejarlo reflejado en commit message y, si toca arquitectura, plantear actualización en Notion.

---

## 14. Recursos externos — Notion

Toda la documentación detallada del proyecto vive en Notion. Para profundizar en lo que aquí solo se resume:

- **Página principal del proyecto** (Planner SKP - Plan B):
  https://www.notion.so/cubrodesign/Planner-SKP-Plan-B-2bbf687d134380549200c7e45999544d
- **Módulo B (toda la arquitectura detallada):**
  https://www.notion.so/cubrodesign/356f687d134380c5bb37d6b82295537c
- **Módulo A:**
  https://www.notion.so/cubrodesign/356f687d1343806b930deef9fbf97085
- **Módulo C:**
  https://www.notion.so/cubrodesign/356f687d134380209de4fd1efd01234e
- **Catálogo de muebles (familia, subfamilia, diferenciadores):**
  https://www.notion.so/cubrodesign/352f687d1343810587c4d57fce6ef400
- **Descripciones en español (Names canónicos):**
  https://www.notion.so/cubrodesign/357f687d134381fc9de6d548762d64c7

---

## 15. Plan de implementación sugerido

Orden razonable para arrancar `modulo_b.py` y `app.py`:

1. **Estructura general de `app.py` + sidebar** — uploader, logo placeholder, gestión de `st.session_state`.
2. **Pantalla 0** — validación de errores. La más simple, buen primer hito.
3. **Paso 1 — esqueleto** — cards plegables vacías con cabecera, sin controles dentro.
4. **Paso 1 — bloque informativo + sistema de check** — el armazón funcional sin opcionales aún.
5. **Paso 1 — controles opcionales** — checkboxes, radio, texto libre, con la lógica de qué mostrar por mueble.
6. **Paso 1 — tooltips** — redactarlos con la app delante.
7. **Paso 1 — acciones globales** — Expandir/Colapsar, filtro pendientes.
8. **Paso 2 — cards-resumen y validación** — sin export aún.
9. **Paso 2 — detalle técnico (feature flag)**.
10. **Paso 2 — botón export placeholder**.

Cada hito es un commit separado en `feature/modulo-b`.

---

## 16. Convención al cierre de una sesión

Al final de cada sesión productiva, conviene:

1. Hacer commit de los cambios con mensaje descriptivo.
2. Si se han tomado decisiones arquitectónicas nuevas, anotarlas (idealmente en Notion vía la conversación del chat, no aquí).
3. Si se ha cambiado algo del contrato con A o C, avisar al responsable.
4. Actualizar este `CLAUDE.md` si han cambiado convenciones, pendientes o estructura.
