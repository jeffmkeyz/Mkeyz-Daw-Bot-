# 🎛️ Mkeyz Studio Bot

> El primer estudio musical que cabe en Telegram.
> Desarrollado por **Jeff Mkeyz** — Productor · Cantautor · 🇩🇴 República Dominicana · 🇪🇸 España

---

## ¿Qué es Mkeyz Studio?

Mkeyz Studio es un bot de Telegram diseñado para artistas independientes y productores musicales. Centraliza en un solo lugar las herramientas esenciales para producir, analizar, gestionar y conectar con otros artistas — con juegos interactivos incluidos.

---

## 💳 Planes

| Plan | Precio | Funciones |
|------|--------|-----------|
| 🆓 **Free** | Gratis | Menú público · Buscar canciones · Beat Battle · Adivina el BPM |
| ⭐ **Pro** | 50 Stars/mes (~$0.65) | Todo Free + DAW · Analizador · Calculadora · Proyección |
| 🎛️ **Studio** | 150 Stars/mes (~$2) | Todo Pro + Zona Artistas · Colabs · Showcases |

Pagos con **Telegram Stars** — nativo, sin tarjeta ni configuración externa.

---

## ✨ Funcionalidades

### 🎛️ Mini DAW
Editor de audio completo directamente en el chat. Los efectos se encadenan — cada resultado se convierte en el nuevo audio de trabajo.

| Efecto | Descripción |
|--------|-------------|
| 🎵 Pitch Shift | Presets ±1/±2/±3 o valor custom (-12 a +12 semitonos) |
| ⏩ Speed | Presets ×0.5–×1.5 o valor custom sin cambio de pitch |
| 🥁 Tempo | Presets ±10/20/50% o valor custom sin cambio de pitch |
| 🔊 Bass Boost | Realza frecuencias bajas |
| 🔇 Normalizar | Iguala volumen al máximo sin clipping |
| ⏮ Reverse | Invierte el audio |
| 🎚️ Fade | Fade in/out automático |
| 🌊 Echo | Efecto eco con delay |
| 🌊 Reverb | Sala pequeña · Mediana · Grande · Cathedral |
| 🎚️ EQ | Boost Graves · Medios · Agudos · Warm · Bright · Vocal |
| ⏱️ Delay | Slapback 80ms · Short 150ms · Medium 250ms · Long 400ms · Deep 600ms |
| ⬇️ Descarga | MP3 320kbps o WAV sin pérdida |

---

### 📊 Analizador de Audio
Envía cualquier audio y obtén al instante:
- 🥁 BPM exacto
- 🎼 Tonalidad y modo (Mayor / Menor)
- ⏱️ Duración
- 🔊 Nivel de volumen (dBFS)

---

### 🧮 Calculadora de Royalties
Calcula cuánto ganarías en streaming en USD y EUR con rates reales de la industria.

**Plataformas:** Spotify · Apple Music · Amazon Unlimited · Tidal · YouTube Premium · YouTube Ads · Audiomack · TikTok · Pandora · Amazon Prime

**Extra:**
- Comparación instantánea entre plataformas con los mismos streams
- 📈 Proyección de ingresos a 6 meses con % de crecimiento mensual

---

### 🔍 Buscador de Canciones
Busca cualquier canción vía iTunes API — nombre, artista, álbum, género, duración y link a Apple Music.

---

### 🎮 Beat Battle Arena
Juego interactivo HTML5 accesible desde Telegram:
- Batallas de beats activas durante 24 horas
- Vota 🔥 Fuego o 💀 Skip con animaciones
- Barra de votación en tiempo real
- Tabla de clasificación global por score (votos fuego - votos skip)
- Cualquier usuario puede subir su beat al battle

---

### 🥁 Adivina el BPM
Juego interactivo de oído musical:
- El bot reproduce el ritmo con audio generado en el navegador
- Tap al ritmo para detectar el BPM automáticamente
- Slider para ajuste manual
- 5 rondas · 15 segundos por ronda · Bonus por rapidez
- Hasta 550 puntos por ronda perfecta
- Clasificaciones: Novato → Aprendiz → Pro → Maestro → Legendario 👑
- Leaderboard global con mejores puntuaciones

---

### 🎤 Zona Artistas *(plan Studio)*
Comunidad privada para artistas independientes.

| Función | Descripción |
|---------|-------------|
| ✏️ Registro | Perfil con nombre artístico, género, bio e Instagram |
| 🤝 Buscar colabs | Filtra artistas por género con link directo a Telegram |
| 💡 Compartir ideas | Publica ideas en texto o audio |
| 🎵 Showcase | Sube previews de tus tracks y recibe feedback |
| 📋 Feed reciente | Ve los últimos posts de la comunidad |
| 💬 Mi feedback | Revisa el feedback recibido en tus showcases |
| 🗑️ Eliminar cuenta | Borra tu perfil y todos tus datos |

---

## 🔧 Panel Admin

Comandos exclusivos para el administrador del bot:

```
/admin              — Ver panel de control
/admin studio       — Activarse plan Studio (12 meses)
/admin pro          — Activarse plan Pro (12 meses)
/admin free         — Volver a Free
/admin give <id> <plan>  — Dar plan a un usuario
/admin check <id>        — Ver plan de un usuario
```

---

## 🚀 Stack tecnológico

| Componente | Tecnología |
|------------|------------|
| Bot framework | python-telegram-bot 21.6 |
| Análisis de audio | librosa 0.10 |
| Efectos de audio | pedalboard (Spotify) |
| Procesamiento base | pydub + ffmpeg |
| Servidor web | Flask + Gunicorn |
| Juegos | HTML5 + Telegram Mini Apps |
| Base de datos | SQLite |
| Búsqueda musical | iTunes Search API |
| Pagos | Telegram Stars |
| Deploy | Railway |

---

## 📦 Instalación local

```bash
# Clonar el repositorio
git clone https://github.com/jeffmkeyz/mkeyz-daw-bot.git
cd mkeyz-daw-bot

# Instalar ffmpeg (requerido)
sudo apt install ffmpeg -y   # Linux

# Instalar dependencias Python
pip install -r requirements.txt

# Variables de entorno
export BOT_TOKEN="tu_token"
export ADMIN_ID="tu_telegram_id"
export GAME_URL="http://localhost:8080"

# Correr servidor y bot
gunicorn server:app --bind 0.0.0.0:8080 & python bot.py
```

---

## ⚙️ Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `BOT_TOKEN` | Token de BotFather |
| `ADMIN_ID` | Tu Telegram ID para el panel admin |
| `GAME_URL` | URL pública del servidor Flask (para los juegos) |

---

## 📁 Estructura del proyecto

```
mkeyz-daw-bot/
├── bot.py              ← Bot de Telegram
├── server.py           ← Servidor Flask (API + juegos)
├── requirements.txt    ← Dependencias Python
├── Procfile            ← Configuración Railway
├── runtime.txt         ← Versión de Python
├── README.md           ← Este archivo
└── static/
    ├── index.html      ← Beat Battle Arena
    └── bpm_game.html   ← Adivina el BPM
```

---

## 🎵 Sobre Jeff Mkeyz

Productor musical y cantautor independiente con distribución en Spotify, Apple Music, Tidal, Amazon Music y más plataformas.

- 🛍️ Beats: [beatstars.com/jeffmkeyz](https://beatstars.com/jeffmkeyz)
- 🎵 Spotify: [open.spotify.com/artist/5GnCPMWUzBJCxbBRPgxJEo](https://open.spotify.com/artist/5GnCPMWUzBJCxbBRPgxJEo)
- 📸 Instagram: [@jeffmkeyz](https://instagram.com/jeffmkeyz)
- 🎬 TikTok: [@jeffmkeyz](https://tiktok.com/@jeffmkeyz)
- ▶️ YouTube: [@jeffmkeyz](https://youtube.com/@jeffmkeyz)
- 📧 Contacto: jeffmkeyzmusic@gmail.com

---

## 📄 Licencia

Este proyecto es privado y de uso exclusivo. No está permitida su redistribución o uso comercial sin autorización del autor.

---

*Mkeyz Studio — Tu estudio. En tu bolsillo.* 🎛️
