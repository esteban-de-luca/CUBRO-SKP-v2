# Flujo de trabajo — CUBRO × Schmidt Groupe

> Cómo trabaja el equipo con GitHub + Google Drive.  
> Última actualización: mayo 2026

---

## Contexto

| Herramienta | Para qué sirve |
|---|---|
| **Google Drive** | Sincroniza archivos entre compañeros en tiempo real |
| **GitHub** | Fuente de verdad del código — alimenta Streamlit |
| **Temp/clon** | Repositorio git local desde donde se hace push a GitHub |

---

## Propiedad de archivos

| Persona | Archivo propio | ¿Puede tocar `app.py`? |
|---|---|---|
| Javier | `modulo_a.py` | ❌ No |
| Esteban | `modulo_b.py` | ✅ Sí (es su responsabilidad) |
| Lucía | `modulo_c.py` | ❌ No |

> **Regla de oro:** cada persona edita exclusivamente su archivo. Nadie toca el archivo de otro sin coordinación explícita previa.

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

# Sincronizar con GitHub
cd "C:\Users\TU_USUARIO\AppData\Local\Temp\CUBRO-SKP-v2"
git pull origin main
```

> ⚠️ La carpeta Temp puede borrarse al reiniciar el ordenador. Si no existe, simplemente repite la configuración inicial.

---

## 3. Publicar cambios

```bash
cd "C:\Users\TU_USUARIO\AppData\Local\Temp\CUBRO-SKP-v2"
git add modulo_X.py          # solo tu archivo
git commit -m "descripción del cambio"
git push origin main
```

Después de hacer push, copiar el archivo modificado al Drive para que los compañeros lo vean:

```
Temp\CUBRO-SKP-v2\modulo_X.py  →  copiar a  →  Drive\CUBRO-SKP\modulo_X.py
```

---

## 4. El problema de `app.py`

`app.py` es la orquestación general y **solo Esteban lo edita**. Esto elimina el conflicto en la mayoría de casos.

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

## 5. Resumen del flujo diario

```
Inicio de sesión
      ↓
git pull  →  sincronizar cambios de compañeros
      ↓
Editar MI archivo en el clon (Temp)
      ↓
git add + commit + push  →  GitHub  →  Streamlit se actualiza
      ↓
Copiar archivo al Drive  →  compañeros ven el cambio
```

---

## Referencias

- **Repositorio GitHub:** https://github.com/esteban-de-luca/CUBRO-SKP-v2
- **App en Streamlit:** https://cubro-skp-hmtqcrnptzyqww353nataj.streamlit.app
- **Documentación del proyecto:** ver `CLAUDE.md`
