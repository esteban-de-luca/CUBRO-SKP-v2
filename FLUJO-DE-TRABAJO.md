# Flujo de trabajo — CUBRO × Schmidt Groupe

> Cómo trabaja el equipo con el repositorio de GitHub.  
> Última actualización: mayo 2026

---

## Contexto

| Herramienta | Para qué sirve |
|---|---|
| **GitHub** | Fuente de verdad del código — alimenta Streamlit |
| **Repositorio local** | Copia local desde donde se edita y se hace push a GitHub |

---

## Propiedad de archivos

| Persona | Archivo propio | Email |
|---|---|---|
| Javier | `modulo_a.py` | javier.abad@cubrodesign.com |
| Esteban | `modulo_b.py` + `app.py` | esteban.deluca@cubrodesign.com |
| Lucía | `modulo_c.py` | lucia.rodriguez@cubrodesign.com |

**Reglas inviolables:**
- Cada persona edita exclusivamente su archivo.
- Nadie toca el archivo de otro sin coordinación explícita previa.
- Los archivos compartidos (`data/*.yaml`, `data/catalogo.json`) requieren avisar al equipo **antes** de hacer push.

---

## 1. Configuración inicial (solo una vez por persona)

Abrir terminal y ejecutar:

```bash
git clone https://github.com/esteban-de-luca/CUBRO-SKP-v2 "C:\Users\TU_USUARIO\AppData\Local\Temp\CUBRO-SKP-v2"
cd "C:\Users\TU_USUARIO\AppData\Local\Temp\CUBRO-SKP-v2"
git config user.email "tu@cubrodesign.com"
git config user.name "TuNombre"
```

---

## 2. Inicio de cada sesión de trabajo

```bash
# Verificar que el clon existe
ls "C:\Users\TU_USUARIO\AppData\Local\Temp\CUBRO-SKP-v2"

# Si no existe → volver al paso 1 (Configuración inicial)

# Sincronizar con GitHub antes de tocar nada
cd "C:\Users\TU_USUARIO\AppData\Local\Temp\CUBRO-SKP-v2"
git pull origin main
```

> ⚠️ La carpeta Temp puede borrarse al reiniciar el ordenador. Si no existe, simplemente repite la configuración inicial.

---

## 3. Publicar cambios

```bash
cd "C:\Users\TU_USUARIO\AppData\Local\Temp\CUBRO-SKP-v2"
git add modulo_X.py          # solo tu archivo (o los archivos que hayas tocado)
git commit -m "descripción del cambio"
git push origin main
```

---

## 4. El problema de `app.py`

`app.py` es la orquestación general y **solo Esteban lo edita** por defecto. Esto elimina el conflicto en la mayoría de casos.

### Si excepcionalmente alguien más necesita tocarlo:

1. **Avisar** al equipo: *"Voy a editar app.py"*
2. **Esperar confirmación** de que nadie más lo está editando
3. **Hacer `git pull`** justo antes de empezar
4. **Editar, commit y push** lo antes posible
5. **Avisar** al terminar: *"Ya terminé con app.py"*

### Si hay un conflicto en git:

```bash
git pull origin main
# Git marca las líneas en conflicto con <<<<<<< y >>>>>>>
# Abrir el archivo, resolver manualmente y guardar
git add app.py
git commit -m "fix: resolver conflicto en app.py"
git push origin main
```

---

## 5. Cierre de sesión

Al terminar cada sesión de trabajo:

1. Hacer commit y push de todos los cambios pendientes.
2. Si se han tomado decisiones arquitectónicas nuevas, anotarlas en Notion.
3. Si se ha cambiado algo del contrato entre módulos, avisar al responsable afectado.
4. Si han cambiado convenciones, pendientes o estructura, actualizar `CLAUDE.md`.

---

## 6. Resumen del flujo diario

```
Inicio de sesión
      ↓
git pull  →  sincronizar cambios de compañeros
      ↓
Editar MI archivo en el repositorio local
      ↓
git add + commit + push  →  GitHub  →  Streamlit se actualiza
      ↓
Avisar al equipo si el cambio afecta a otros módulos
```

---

## Referencias

- **Repositorio GitHub:** https://github.com/esteban-de-luca/CUBRO-SKP-v2
- **App en Streamlit:** https://cubro-skp-hmtqcrnptzyqww353nataj.streamlit.app
- **Documentación técnica del proyecto:** ver `CLAUDE.md`
