# CLAUDE.md — Proyecto HbM CUBRO × Schmidt Groupe

> Este archivo es el puente de contexto para Claude Code. Lee esto antes de tocar nada.
> Última actualización: junio 2026.

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
**Repo:** https://github.com/esteban-de-luca/CUBRO-SKP-v2
**URL pública:** https://cubro-skp-hmtqcrnptzyqww353nataj.streamlit.app

---

## 2. Equipo, propiedad de archivos y flujo de trabajo

### Equipo

| Persona | Módulo | Archivo propio | Email |
|---|---|---|---|
| Javier | A — Validación CSV | `modulo_a.py` | javier.abad@cubrodesign.com |
| Esteban | B — Interfaz y selección | `modulo_b.py` + `app.py` | esteban.deluca@cubrodesign.com |
| Lucía | C — Mapeo y cálculo | `modulo_c.py` | lucia.rodriguez@cubrodesign.com |

### Reglas de archivos

- La asignación de archivos por persona es orientativa, no una restricción operativa.
- Claude puede modificar cualquier archivo del proyecto sin pedir permiso a nadie — basta con que alguien del equipo lo pida en la sesión.
- Los archivos compartidos (`data/*.yaml`, `data/catalogo.json`) se editan directamente cuando sea necesario.

### Herramientas

| Herramienta | Para qué sirve |
|---|---|
| **GitHub** | Fuente de verdad del código — alimenta Streamlit |
| **Repositorio local** | Copia local desde donde se edita y se hace push a GitHub |

### Configuración inicial (solo una vez por persona)

```bash
git clone https://github.com/esteban-de-luca/CUBRO-SKP-v2 "C:\Users\TU_USUARIO\AppData\Local\Temp\CUBRO-SKP-v2"
cd "C:\Users\TU_USUARIO\AppData\Local\Temp\CUBRO-SKP-v2"
git config user.email "tu@cubrodesign.com"
git config user.name "TuNombre"
```

### Inicio de cada sesión de trabajo

```bash
# Verificar que el clon existe (si no, repetir la configuración inicial)
ls "C:\Users\TU_USUARIO\AppData\Local\Temp\CUBRO-SKP-v2"

# Sincronizar con GitHub antes de tocar nada
cd "C:\Users\TU_USUARIO\AppData\Local\Temp\CUBRO-SKP-v2"
git pull origin main
```

> ⚠️ La carpeta Temp puede borrarse al reiniciar el ordenador. Si no existe, repetir la configuración inicial.

### Publicar cambios

```bash
git add modulo_X.py          # solo tu archivo (o los archivos que hayas tocado)
git commit -m "descripción del cambio"
git push origin main
```

### Conflicto en `app.py`

Si hay un conflicto porque dos personas han editado `app.py` a la vez:

```bash
git pull origin main
# Git marca las líneas en conflicto con <<<<<<< y >>>>>>>
# Abrir el archivo, resolver manualmente y guardar
git add app.py
git commit -m "fix: resolver conflicto en app.py"
git push origin main
```

### Resumen del flujo diario

```
Inicio de sesión
      ↓
git pull  →  sincronizar cambios de compañeros
      ↓
Editar los archivos necesarios en el repositorio local
      ↓
git add + commit + push  →  GitHub  →  Streamlit se actualiza
      ↓
Avisar al equipo si el cambio afecta a otros módulos
```

---

## 3. Quién soy yo en este contexto

Estás interactuando con el equipo de CUBRO. Claude puede modificar cualquier archivo del proyecto — `modulo_a.py`, `modulo_b.py`, `modulo_c.py`, `app.py`, cualquier YAML/JSON — sin pedir permiso ni coordinación previa. Cuando alguien del equipo pide un cambio, se hace y punto.

---

## 4. Principio rector: separación lógica / datos

**Python contiene lógica. YAML/JSON contienen datos.**

- Si cambia una regla de negocio → se edita `data/reglas.yaml`, no `modulo_c.py`.
- Si cambia un código SG, un mapeo de colores o una etiqueta UI → se edita `data/mapeos_SKP_UI_SG.yaml`.
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
├── app.py                      # Orquestación Streamlit (A → B → C → B). Lo gestiona Esteban.
├── modulo_a.py                 # Javier
├── modulo_b.py                 # Esteban
├── modulo_c.py                 # Lucía
├── data/
│   ├── catalogo.json           # 121 muebles (descripciones y dimensiones). Generado 10/05/2026.
│   ├── mapeos_SKP_UI_SG.yaml   # Conversiones CSV → UI → SG (colores, tiradores, rodapié, etc.)
│   ├── opciones_mueble.yaml    # Qué opciones aplican a qué muebles (obligatorias, opcionales, excepciones).
│   ├── reglas.yaml             # Reglas de negocio entre opciones (módulos B y C).
│   ├── p_item_schema.yaml      # Contrato JSON con Schmidt Groupe — estructura del p_item.
│   ├── avisos.yaml             # Textos de los avisos de validación del Módulo A.
│   ├── colores_mueble.yaml     # Paleta de colores de frente por gama.
│   └── imagenes_mueble.yaml    # Rutas de imagen por mueble (para UI).
├── assets/
│   └── Logo CUBRO_positivo.png
├── requirements.txt
├── README.md
└── CLAUDE.md                   # este archivo
```

---

## 7. Arquitectura del Módulo B (cerrada el 10/05/2026)

El Módulo B es la UI. Interviene en DOS momentos del flujo:

### Paso 1 — Selección de opciones opcionales (antes del Módulo C)
- Recibe del Módulo A: `list[dict]`, un dict por mueble con datos del CSV validados.
- Recibe del usuario: selección de opciones opcionales por mueble.
- Envía al Módulo C: **Entrada Módulo C** — `list[dict]` plana de 23 columnas por mueble, ya con las transformaciones CSV→UI aplicadas (CLAUDE.md §8). Ver schema en §9. La construye `modulo_b.construir_entrada_modulo_c(muebles, selecciones, catalogo)`.

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
C_Rodapietext · Ancho · Ancho reducido · Acabado · LenZ · Avisos
```

- `Acabado`: columna obligatoria del CSV. Para tapetas contiene el color del frente con sufijo de gama tal como viene del CSV (p.ej. "Pistachio LINOLEO") — modulo_b quita el sufijo antes de pasarlo al contrato B→C. Para el resto de muebles, campo pendiente de mapeo a opciones SG.
- `Estado`: `✅ CORRECTO` o `⚠️ REVISAR`. Si REVISAR → bloquea avance.
- `Avisos`: string concatenada con ` | ` (con espacios). Códigos posibles: A02, A05, A09, A10, A11, A12, A17, A21, A22, A23, E07, CB12.
- `Name SKP`: nombre original que vino de SketchUp. Siempre presente (úsalo como identificador en UI cuando `Name` esté vacío o no resuelto).

### Output del Paso 1 → Entrada Módulo C

Contrato actualizado 2026-06-19. `list[dict]` plana, una fila por mueble, **31 keys fijas** (las mismas en todas las filas; valores `""` o `"False"` cuando no aplica). Las transformaciones CSV→UI de §8 ya están aplicadas. Lo construye `modulo_b.construir_entrada_modulo_c(muebles, selecciones, catalogo)`.

| # | Columna | Tipo | Origen |
|---|---|---|---|
| 1 | Código mueble | `str` | CSV `Name` |
| 2 | Descripción | `str` | `catalogo.json.<name>.designaciones.es` |
| 3 | Posición | `str` | Reservada (siempre `""`) |
| 4 | Summary | `str` | CSV `Summary` — identificador SKP (→ `p_item_origin_id`) |
| 5 | Apertura | `str` | UI label ("Izquierda"/"Derecha"/"Lift") o `""` |
| 6 | Gama del frente | `str` | LACA / WOOD / LINOLEO / LAMINADO |
| 7 | Acabado del frente | `str` | Color sin sufijo de gama ("Crema"). Vacío para tapetas |
| 8 | Color interior | `str` | Sin "mueble" ("Blanco"). Vacío para tapetas |
| 9 | Tirador | `str` | UI label (Round, Square, …) o `""`. Vacío para tapetas |
| 10 | Color tirador | `str` | Touch Latch/Prise de main → `""`. Trasera=Laca → color frente. Vacío para tapetas |
| 11 | Rodapié | `str` | "70 mm" / "100 mm" / "Sin patas" / `""`. Vacío para tapetas |
| 12 | Acabado del mueble abierto | `str` | Solo EOV/EOAVV (muebles sin frente). Vacío para el resto |
| 13 | Reducción de ancho | `"True"`/`"False"` | CSV `Ancho == "10000 mm"` |
| 14 | Ancho reducido | `str` | Valor cuando Reducción=True, sino `""` |
| 15 | Acabado | `str` | CSV `Acabado` sin sufijo de gama (p.ej. "Pistachio", no "Pistachio LINOLEO"). Usado por modulo_c como op_101 para tapetas; mismo lookup que "Acabado del frente" |
| 16 | Ancho CSV | `str` | Ancho del modelo SKP (vacío si hay reducción). Para Paso 2 cuando catálogo no tiene ancho_mm |
| 17 | Alto CSV | `str` | LenZ del modelo SKP. Para FF12V: alto introducido por el usuario en mm |
| 18 | Alto final tapeta | `str` | Entero en mm solo para FF12V con alto válido. Usado por modulo_c para `p_height`. Vacío para el resto |
| 19 | Sin mecanizado | `"True"`/`"False"` | op_121 |
| 20 | Cubos de basura | `"True"`/`"False"` | op_207_opcional |
| 21 | Recorte LED | `"True"`/`"False"` | op_220 |
| 22 | Sensor para mando LED | `str` | "Derecha" / "Izquierda" / `""` (op_222) |
| 23 | Cajón interior | `"True"`/`"False"` | op_223 |
| 24 | Mueble de caldera | `"True"`/`"False"` | op_227 |
| 25 | Sin encolar | `"True"`/`"False"` | op_700_opcional |
| 26 | Marca electro | `str` | op_126.marca — electro 1 |
| 27 | Referencia electro | `str` | op_126.referencia — Caso A (referencia conocida) |
| 28 | Alto electro | `str` | op_126.alto — Caso B (sin referencia, altura en mm) |
| 29 | Marca electro 2 | `str` | op_126_2.marca — electro 2 (solo AFSMO/AFSMOBT) |
| 30 | Referencia electro 2 | `str` | op_126_2.referencia — Caso A slot 2 |
| 31 | Alto electro 2 | `str` | op_126_2.alto — Caso B slot 2 |

**Electro Caso A / Caso B:** si el usuario conoce la referencia → rellena Marca + Referencia electro (genera `p_built_in_detail`). Si no → rellena Marca + Alto electro (genera `p_built_in_detail` con `p_built_in_height`). Campanas (HH) solo admiten Caso A.

**Tapetas (FF12*/FFAL10*):** Apertura, Color interior, Tirador, Color tirador, Rodapié y Acabado del mueble abierto siempre vacíos. `Acabado` contiene el color **sin sufijo de gama** ("Pistachio", no "Pistachio LINOLEO") — modulo_b lo procesa con `_ui_color_frente()` igual que "Acabado del frente". modulo_c lo usa para op_101 con el mismo índice UI→SG. Solo FF12V usa "Alto final tapeta". Dimensiones JSON: `p_width = p_depth = 0` (SG las conoce por código); `p_height = 0` salvo FF12V.

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
- `op_126` Electrodoméstico (bloque de 4 textos libres: marca, referencia, altura, tipo; solo BFT y AFS). El valor en `opcionales["op_126"]` es un `dict[str, str]` con las 4 keys. **Validación para marcar revisado** (confirmada con Lucía el 2026-05-11): Marca y Tipo siempre obligatorios; Referencia y Altura son intercambiables, al menos una de las dos debe estar rellena.

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

Cada hito es un commit separado en `main`.

---

## 16. Cierre de sesión

Al terminar cada sesión de trabajo:

1. Hacer commit y push de todos los cambios pendientes.
2. Si se han tomado decisiones arquitectónicas nuevas, anotarlas en Notion.
3. Si se ha cambiado algo del contrato entre módulos, avisar al responsable afectado.
4. Si han cambiado convenciones, pendientes o estructura, actualizar este `CLAUDE.md`.
