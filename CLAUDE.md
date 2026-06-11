# VERDI Gallery — Guía del Proyecto

## ¿Qué es esto?
Galería fotográfica y de video para VERDI (verdi.com.co), publicada en **galeria.verdi.com.co** vía GitHub Pages.

## Estructura del repo
```
VERDI-Gallery/
├── index.html          # Galería pública (se genera desde config_new.js via fix.py)
├── config_new.js       # FUENTE DE VERDAD — array de fotos/videos + categoryOrder
├── organizador.html    # Herramienta local para gestionar la galería
├── sw.js               # Service Worker (cache verdi-v16, videos no se cachean)
├── logo-verdi.png      # Logo splash (800px, RGBA, fondo transparente)
├── logo-verdi-header.png # Logo header (160x120px)
├── manifest.json       # PWA manifest
├── thumbs/             # Thumbnails 800px (imágenes: mismo nombre; videos: nombre.ext.jpg)
├── _scripts/
│   ├── fix.py          # Sincroniza index.html desde config_new.js
│   └── server.py       # Servidor local con upload/publish (puerto 8765)
└── CLAUDE.md           # Este archivo
```

## Reglas importantes

### config_new.js es la fuente de verdad
- **Nunca editar index.html directamente** para cambiar fotos/orden
- Editar `config_new.js` → correr `python3 _scripts/fix.py` → git push
- `fix.py` reemplaza el bloque `const CONFIG = {...}` en index.html con el contenido de config_new.js

### Nombres de archivos
- Fotos: `NNN-Nombre-Descriptivo.JPG` (ej: `123-Tapete-Casablanca.JPG`)
- Videos: misma convención o nombre descriptivo
- **Sin espacios ni %** — usar guiones. El % se escribe como `pct` (ej: `100pct-Cobre`)
- Extensiones en mayúsculas o minúsculas, ambas funcionan

### Thumbnails
- Imágenes: `thumbs/NNN-Nombre.JPG` (mismo nombre que el archivo)
- Videos: `thumbs/NNN-Nombre.MP4.jpg` (nombre del video + `.jpg`)
- Tamaño: 800px de ancho

## Comandos frecuentes

```bash
# Sincronizar index.html desde config_new.js
python3 _scripts/fix.py

# Publicar cambios
git add . && git commit -m "descripción" && git push

# Arrancar servidor local del organizador
python3 _scripts/server.py 8765
# Luego abrir: http://localhost:8765/organizador.html

# Comprimir video con buena calidad (CRF 18 = casi sin pérdida, 4K safe)
ffmpeg -i input.mov -c:v libx264 -crf 18 -preset slow \
  -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" \
  -c:a aac -b:a 192k -movflags +faststart -y output.mp4

# Comprimir video más agresivo (CRF 28 = menor tamaño, 1080p máx)
ffmpeg -i input.mov -c:v libx264 -crf 28 -preset slow \
  -vf "scale='min(1920,iw)':'min(1080,ih)':force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2" \
  -c:a aac -b:a 128k -movflags +faststart -y output.mp4

# Generar thumbnail de video
ffmpeg -ss 1 -i video.mp4 -vframes 1 -vf "scale=800:-2" -q:v 3 -y thumbs/video.mp4.jpg

# Bump service worker cache (forzar recarga en todos los browsers)
# Editar sw.js: cambiar 'verdi-vNN' al siguiente número
```

## Servidor local (_scripts/server.py)
Puerto: **8765**

Endpoints:
- `GET /` → sirve archivos estáticos (con URL decode para nombres con espacios)
- `POST /upload` → recibe imagen/video, comprime, genera thumbnail, retorna JSON
- `POST /publish` → guarda config_new.js, corre fix.py, git add/commit/push

El organizador se abre con **`Abrir Organizador.command`** (en Desktop o Documents).

## Organizador (organizador.html)
- **Doble clic en título** → editar inline (Enter guarda, Escape cancela)
- **Drag & drop en "Todas"/"General"** → reordena el array global
- **Drag & drop en otra categoría** → guarda orden en `categoryOrder` sin mover el global
- **📷 Agregar fotos** → selector de archivos, diálogo de renombrar, compresión automática
- **🚀 Publicar** → llama `/publish`, guarda y hace git push
- **＋ Categoría** → agrega categoría nueva (persiste en localStorage)

## config_new.js — estructura
```js
const CONFIG = {
  photos: [
    { src: "filename.jpg", title: "Título", category: "General" },
    { src: "filename.jpg", title: "Título", category: ["General", "Rugs"] },
    ...
  ],
  categoryOrder: {
    "Rugs": ["archivo1.jpg", "archivo2.jpg"],   // orden personalizado
    "Window Coverings": [],
    "Hospitality": [],
    "Art": [],
    "Fashion": []
  }
};
```

## Service Worker (sw.js)
- Cache actual: `verdi-v16`
- Estrategia: Network-first para todo excepto videos
- Videos (`.mp4`, `.mov`): siempre directo desde la red, nunca cacheados
- Para forzar recarga en todos los usuarios: incrementar número de versión

## GitHub
- Repo: `https://github.com/tomas-verdi/VERDI-Gallery`
- Branch: `main`
- Deploy: GitHub Pages automático
- URL pública: `galeria.verdi.com.co`

## Historial de decisiones
- Los thumbnails de videos se llaman `video.MP4.jpg` (nombre + `.jpg`)
- `%` en nombres de archivo se reemplaza por `pct` (compatibilidad URLs)
- `40-La-Macorina-Design-Miami.mov` → renombrado a `C0007.mov`
- `109-Ika-Fibra-de-Platano-y-Cobre.MOV` → renombrado a `IMG_9653.MOV`
- Videos no se comprimen con CRF < 18 para mantener calidad en 4K
