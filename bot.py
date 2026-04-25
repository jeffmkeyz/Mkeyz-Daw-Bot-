# -*- coding: utf-8 -*-
"""
Mkeyz Studio Bot — Versión limpia y funcional
"""

import os, uuid, asyncio, logging, sys, sqlite3, time
import numpy as np
import librosa
import soundfile as sf
import requests
from pydub import AudioSegment, effects
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, WebAppInfo
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters, PreCheckoutQueryHandler,
)

# ══════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════

TOKEN    = os.getenv("BOT_TOKEN", "8736753639:AAGHp-nxa4KKvUcnmhJplgBb0-asZogoiuE")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

def is_admin(user_id: int) -> bool:
    return ADMIN_ID != 0 and user_id == ADMIN_ID
EUR_RATE = 0.92

BANNER_URL = "https://i.ibb.co/Fqxk8NHZ/chromatic-haze-portrait-1f1314d5-273f-6550-a10c-a923b265cbc7-0-0.png"

LINKS = {
    "beatstars": "https://beatstars.com/jeffmkeyz",
    "tiktok":    "https://tiktok.com/@jeffmkeyz",
    "youtube":   "https://youtube.com/@jeffmkeyz",
    "instagram": "https://instagram.com/jeffmkeyzx",
    "spotify":   "https://open.spotify.com/intl-es/artist/1PTk2yExL9jgOUPYEjWF1E",
}

# ── Planes ─────────────────────────────────────────────────
PLAN_FREE   = "free"
PLAN_PRO    = "pro"
PLAN_STUDIO = "studio"

PLAN_PRICES = {PLAN_PRO: 50, PLAN_STUDIO: 150}
PLAN_LABELS = {
    PLAN_FREE:   "🆓 Free",
    PLAN_PRO:    "⭐ Pro — 50 Stars/mes",
    PLAN_STUDIO: "🎛️ Studio — 150 Stars/mes",
}

PLAN_PERMS = {
    "sec_calc":    PLAN_PRO,
    "sec_daw":     PLAN_PRO,
    "sec_analyze": PLAN_PRO,
    "sec_spotify": PLAN_FREE,
    "sec_artists": PLAN_STUDIO,
}

# ── Plataformas de streaming ───────────────────────────────
PLATAFORMAS = {
    "Spotify":          0.001106,
    "Amazon Unlimited": 0.010574,
    "Tidal":            0.003433,
    "YouTube Premium":  0.007441,
    "YouTube Ads":      0.003197,
    "Apple Music":      0.005799,
    "Pandora":          0.001705,
    "Amazon Prime":     0.001343,
    "Audiomack":        0.001144,
    "TikTok":           0.000850,
}

GENRES = ["Trap", "Pop Latino", "Afrobeats", "Lo-Fi",
          "Reggaeton", "R&B", "Hip-Hop", "Salsa/Merengue", "EDM", "Otro"]

NOTE_NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
MODES_MAP  = {0: "Mayor", 1: "Menor"}

TMP = os.path.join(os.environ.get("TEMP", "/tmp"), "mkeyz_daw")
os.makedirs(TMP, exist_ok=True)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mkeyz.db")

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s",
                    level=logging.INFO, stream=sys.stdout)
log = logging.getLogger("mkeyz")

# ── Modos ──────────────────────────────────────────────────
MODE_NONE       = "none"
MODE_DAW        = "daw"
MODE_CALC       = "calc"
MODE_ANLZ       = "analyze"
MODE_SEARCH     = "search"
MODE_REG        = "register"
MODE_IDEA       = "idea"
MODE_SHOW       = "showcase"
MODE_FB         = "feedback"
MODE_DAW_PITCH  = "daw_pitch_custom"
MODE_DAW_SPEED  = "daw_speed_custom"
MODE_DAW_TEMPO  = "daw_tempo_custom"
MODE_PROJ       = "proyeccion"
MODE_RETO       = "reto"
MODE_COTIZADOR  = "cotizador"
MODE_BATTLE     = "battle"
GAME_URL        = os.getenv("GAME_URL", "")

# ── Cotizador de licencias ─────────────────────────────────
LICENCIAS = {
    "Básica":    {"precio": 49,  "streams": "100K", "vids": "1 video", "radio": "No", "desc": "YouTube · Redes · No comercial"},
    "Premium":   {"precio": 149, "streams": "500K", "vids": "Ilimitado", "radio": "Sí", "desc": "Distribución · Radio · Uso comercial"},
    "Exclusiva": {"precio": 499, "streams": "Ilimitado", "vids": "Ilimitado", "radio": "Sí", "desc": "Derechos completos · Solo para ti"},
}

GENEROS_BEATS = ["Trap", "Pop Latino", "Afrobeats", "Reggaeton", "Lo-Fi", "R&B", "Hip-Hop", "Drill", "Dancehall", "Otro"]
MOODS_BEATS   = ["Oscuro 🌑", "Alegre ☀️", "Romántico 💜", "Agresivo 🔥", "Relajado ☁️", "Épico ⚡", "Melancólico 🌧️"]  # URL pública del servidor Flask en Railway

# ══════════════════════════════════════════════════════════
#  BASE DE DATOS
# ══════════════════════════════════════════════════════════

def db_init():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            tg_id      INTEGER PRIMARY KEY,
            plan       TEXT NOT NULL DEFAULT 'free',
            started_at INTEGER,
            expires_at INTEGER
        );
        CREATE TABLE IF NOT EXISTS battles (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id         INTEGER NOT NULL,
            name          TEXT NOT NULL,
            file_id       TEXT NOT NULL,
            file_type     TEXT NOT NULL,
            caption       TEXT,
            submitted_at  INTEGER NOT NULL,
            expires_at    INTEGER NOT NULL,
            votes_fire    INTEGER DEFAULT 0,
            votes_skip    INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS battle_votes (
            battle_id     INTEGER NOT NULL,
            voter_tg_id   INTEGER NOT NULL,
            vote          TEXT NOT NULL,
            PRIMARY KEY (battle_id, voter_tg_id),
            FOREIGN KEY (battle_id) REFERENCES battles(id)
        );
        CREATE TABLE IF NOT EXISTS artists (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id     INTEGER UNIQUE NOT NULL,
            username  TEXT,
            name      TEXT NOT NULL,
            genre     TEXT NOT NULL,
            bio       TEXT,
            ig        TEXT,
            joined_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS posts (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            artist_id INTEGER NOT NULL,
            type      TEXT NOT NULL,
            content   TEXT,
            file_id   TEXT,
            file_type TEXT,
            caption   TEXT,
            posted_at INTEGER NOT NULL,
            FOREIGN KEY (artist_id) REFERENCES artists(id)
        );
        CREATE TABLE IF NOT EXISTS feedback (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id    INTEGER NOT NULL,
            from_tg_id INTEGER NOT NULL,
            from_name  TEXT,
            text       TEXT NOT NULL,
            sent_at    INTEGER NOT NULL,
            FOREIGN KEY (post_id) REFERENCES posts(id)
        );
    """)
    con.commit()
    con.close()

# ── Suscripciones ──────────────────────────────────────────
def db_get_plan(tg_id):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT plan, expires_at FROM subscriptions WHERE tg_id=?", (tg_id,))
    row = cur.fetchone()
    con.close()
    if not row:
        return PLAN_FREE
    plan, expires_at = row
    if expires_at and int(time.time()) > expires_at:
        return PLAN_FREE
    return plan

def db_set_plan(tg_id, plan, months=1):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    now     = int(time.time())
    expires = now + (months * 30 * 24 * 3600)
    cur.execute("INSERT OR REPLACE INTO subscriptions (tg_id,plan,started_at,expires_at) VALUES (?,?,?,?)",
                (tg_id, plan, now, expires))
    con.commit()
    con.close()

def plan_allows(user_plan, required):
    order = [PLAN_FREE, PLAN_PRO, PLAN_STUDIO]
    return order.index(user_plan) >= order.index(required)

# ── Artistas ───────────────────────────────────────────────
def db_get_artist(tg_id):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM artists WHERE tg_id=?", (tg_id,))
    row = cur.fetchone()
    con.close()
    return dict(row) if row else None

def db_register(tg_id, username, name, genre, bio, ig):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("INSERT OR REPLACE INTO artists (tg_id,username,name,genre,bio,ig,joined_at) VALUES (?,?,?,?,?,?,?)",
                (tg_id, username, name, genre, bio, ig, int(time.time())))
    con.commit()
    con.close()

def db_delete_artist(tg_id):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT id FROM artists WHERE tg_id=?", (tg_id,))
    row = cur.fetchone()
    if row:
        aid = row[0]
        cur.execute("DELETE FROM feedback WHERE post_id IN (SELECT id FROM posts WHERE artist_id=?)", (aid,))
        cur.execute("DELETE FROM posts WHERE artist_id=?", (aid,))
        cur.execute("DELETE FROM artists WHERE id=?", (aid,))
        con.commit()
    con.close()

def db_all_artists(genre=None):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    if genre:
        cur.execute("SELECT * FROM artists WHERE genre=? ORDER BY joined_at DESC", (genre,))
    else:
        cur.execute("SELECT * FROM artists ORDER BY joined_at DESC")
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    return rows

def db_add_post(tg_id, ptype, content=None, file_id=None, caption=None, file_type=None):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT id FROM artists WHERE tg_id=?", (tg_id,))
    row = cur.fetchone()
    if not row:
        con.close()
        return None
    cur.execute("INSERT INTO posts (artist_id,type,content,file_id,file_type,caption,posted_at) VALUES (?,?,?,?,?,?,?)",
                (row[0], ptype, content, file_id, file_type, caption, int(time.time())))
    pid = cur.lastrowid
    con.commit()
    con.close()
    return pid

def db_get_posts(limit=10, ptype=None):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    if ptype:
        cur.execute("SELECT p.*, a.name as artist_name, a.genre, a.tg_id as artist_tg_id FROM posts p JOIN artists a ON p.artist_id=a.id WHERE p.type=? ORDER BY p.posted_at DESC LIMIT ?", (ptype, limit))
    else:
        cur.execute("SELECT p.*, a.name as artist_name, a.genre, a.tg_id as artist_tg_id FROM posts p JOIN artists a ON p.artist_id=a.id ORDER BY p.posted_at DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    return rows

def db_get_post(post_id):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT p.*, a.name as artist_name, a.tg_id as artist_tg_id FROM posts p JOIN artists a ON p.artist_id=a.id WHERE p.id=?", (post_id,))
    row = cur.fetchone()
    con.close()
    return dict(row) if row else None

def db_add_feedback(post_id, from_tg_id, from_name, text):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("INSERT INTO feedback (post_id,from_tg_id,from_name,text,sent_at) VALUES (?,?,?,?,?)",
                (post_id, from_tg_id, from_name, text, int(time.time())))
    con.commit()
    con.close()

def db_get_feedback(post_id):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM feedback WHERE post_id=? ORDER BY sent_at DESC", (post_id,))
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    return rows

# ── Battle DB ─────────────────────────────────────────────

def db_add_battle(tg_id, name, file_id, file_type, caption):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    now = int(time.time())
    cur.execute("""
        INSERT INTO battles (tg_id,name,file_id,file_type,caption,submitted_at,expires_at)
        VALUES (?,?,?,?,?,?,?)
    """, (tg_id, name, file_id, file_type, caption, now, now + 86400))
    bid = cur.lastrowid
    con.commit()
    con.close()
    return bid

def db_get_active_battles(limit=5):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM battles WHERE expires_at > ? ORDER BY votes_fire DESC LIMIT ?",
                (int(time.time()), limit))
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    return rows


TITULOS_POOL = {
    "trap": ["Dark Ritual","Midnight Trap","Phantom Bounce","Cold Nights","Street Sermon","Noir Trap","Shadow Walk","Blood Money"],
    "pop latino": ["Corazón de Fuego","Verano Eterno","Noche de Luna","Dulce Veneno","Amor Prohibido","Entre Tus Brazos","Fuego y Sal","Mil Razones"],
    "afrobeats": ["Lagos Nights","Afro Spirit","Jungle Rhythm","Golden Coast","Ancestral Groove","Sunset Tribe","Rhythm of Life","West Side Vibes"],
    "reggaeton": ["Perreo Fatal","La Calle Llama","Bajo el Sol","Ritmo Caliente","La Noche Es Nuestra","Vibra Latina","Dale Duro","Fuego en la Pista"],
    "lo-fi": ["Sunday Morning","Rainy Study","Nostalgic Drive","Bedroom Vibes","Coffee Shop","Late Night Thoughts","Soft Landing","Memory Lane"],
    "r&b": ["Velvet Soul","Midnight Silk","Sweet Obsession","Slow Burn","Satin Dreams","Smooth Criminal","Golden Hour","Tender Love"],
    "drill": ["No Cap","Grimey Streets","Block Runner","Pressure","Mob Talk","Cold Steel","Nightshift","Trap Demons"],
    "default": ["Eclipse","Phantom","Celestial","Nova","Abyss","Genesis","Solstice","Meridian"],
}

# ── Retos Semanales ───────────────────────────────────────

RETOS_POOL = [
    {"titulo": "Beat en 140 BPM", "desc": "Produce un beat a exactamente 140 BPM. Cualquier género.", "emoji": "🥁"},
    {"titulo": "Hook en C Minor", "desc": "Graba un hook o melodía en Do Menor. Mínimo 15 segundos.", "emoji": "🎵"},
    {"titulo": "Beat con solo 3 elementos", "desc": "Kick, bass y un sample. Nada más. Demuestra que menos es más.", "emoji": "🎚️"},
    {"titulo": "Freestyle 60 segundos", "desc": "60 segundos de freestyle sobre cualquier instrumental.", "emoji": "🎤"},
    {"titulo": "Beat de Afrobeats", "desc": "Produce un beat con vibras afrobeats. Sin límite de BPM.", "emoji": "🌍"},
    {"titulo": "Sample flip", "desc": "Toma cualquier sonido del día a día y conviértelo en un beat.", "emoji": "🔄"},
    {"titulo": "Lo-Fi en 2 minutos", "desc": "Produce un beat lo-fi completo en menos de 2 minutos.", "emoji": "☁️"},
    {"titulo": "Trap en 808", "desc": "Un beat de trap donde el 808 sea el protagonista.", "emoji": "🔊"},
    {"titulo": "Beat sin kick", "desc": "Produce un beat sin usar ningún kick drum.", "emoji": "🚫"},
    {"titulo": "Melodía de 8 notas", "desc": "Crea una melodía usando exactamente 8 notas distintas.", "emoji": "🎼"},
    {"titulo": "Reggaeton clásico", "desc": "Dembow puro. El patrón original, tu sello personal.", "emoji": "🌴"},
    {"titulo": "Beat en tiempo récord", "desc": "Tienes 5 minutos reales para hacer un beat. Sube el resultado.", "emoji": "⏱️"},
]

def get_current_reto():
    """Genera el reto de esta semana basado en el número de semana del año."""
    week = int(time.time()) // (7 * 24 * 3600)
    return RETOS_POOL[week % len(RETOS_POOL)]

def get_week_id():
    return int(time.time()) // (7 * 24 * 3600)

def db_add_reto_entry(tg_id, name, file_id, file_type, week_id):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reto_entries (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id     INTEGER NOT NULL,
            name      TEXT NOT NULL,
            file_id   TEXT NOT NULL,
            file_type TEXT NOT NULL,
            week_id   INTEGER NOT NULL,
            votes     INTEGER DEFAULT 0,
            posted_at INTEGER NOT NULL
        )""")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reto_votes (
            entry_id    INTEGER NOT NULL,
            voter_tg_id INTEGER NOT NULL,
            PRIMARY KEY (entry_id, voter_tg_id)
        )""")
    # Check if already submitted this week
    cur.execute("SELECT id FROM reto_entries WHERE tg_id=? AND week_id=?", (tg_id, week_id))
    if cur.fetchone():
        con.close()
        return None
    cur.execute("INSERT INTO reto_entries (tg_id,name,file_id,file_type,week_id,votes,posted_at) VALUES (?,?,?,?,?,0,?)",
                (tg_id, name, file_id, file_type, week_id, int(time.time())))
    eid = cur.lastrowid
    con.commit()
    con.close()
    return eid

def db_get_reto_entries(week_id, limit=10):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    try:
        cur.execute("SELECT * FROM reto_entries WHERE week_id=? ORDER BY votes DESC LIMIT ?",
                    (week_id, limit))
        rows = [dict(r) for r in cur.fetchall()]
    except:
        rows = []
    con.close()
    return rows

def db_vote_reto(entry_id, voter_tg_id):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    try:
        cur.execute("INSERT INTO reto_votes (entry_id, voter_tg_id) VALUES (?,?)",
                    (entry_id, voter_tg_id))
        cur.execute("UPDATE reto_entries SET votes = votes + 1 WHERE id=?", (entry_id,))
        con.commit()
        con.close()
        return True
    except sqlite3.IntegrityError:
        con.close()
        return False

# ══════════════════════════════════════════════════════════
#  AUDIO UTILS
# ══════════════════════════════════════════════════════════

def tmpf(ext="wav"):
    return os.path.join(TMP, f"{uuid.uuid4().hex}.{ext}")

def to_wav(path):
    out = tmpf("wav")
    AudioSegment.from_file(path).set_channels(1).set_frame_rate(44100).export(out, format="wav")
    return out

def to_ogg(path):
    out = tmpf("ogg")
    AudioSegment.from_wav(path).export(out, format="ogg", codec="libopus")
    return out

def to_mp3(path):
    out = tmpf("mp3")
    AudioSegment.from_wav(path).export(out, format="mp3", bitrate="320k")
    return out

def to_wav_file(path):
    out = tmpf("wav")
    AudioSegment.from_wav(path).export(out, format="wav")
    return out

def ogg_to_wav(ogg_path):
    out = tmpf("wav")
    AudioSegment.from_ogg(ogg_path).set_channels(1).set_frame_rate(44100).export(out, format="wav")
    return out

def do_pitch(wav, semitones):
    y, sr = librosa.load(wav, sr=None, mono=True)
    y2    = librosa.effects.pitch_shift(y, sr=sr, n_steps=semitones)
    out   = tmpf("wav")
    sf.write(out, y2, sr)
    return to_ogg(out)

def do_speed(wav, factor):
    factor = max(0.5, min(factor, 2.0))
    audio  = AudioSegment.from_wav(wav)
    out    = tmpf("wav")
    audio._spawn(audio.raw_data, overrides={"frame_rate": int(audio.frame_rate * factor)}) \
         .set_frame_rate(44100).export(out, format="wav")
    return to_ogg(out)

def do_tempo(wav, factor):
    factor = max(0.5, min(factor, 2.0))
    y, sr  = librosa.load(wav, sr=None, mono=True)
    y2     = librosa.effects.time_stretch(y, rate=factor)
    out    = tmpf("wav")
    sf.write(out, y2, sr)
    return to_ogg(out)

def do_bass(wav, db=6.0):
    audio = AudioSegment.from_wav(wav)
    out   = tmpf("wav")
    audio.overlay(audio.low_pass_filter(300) + min(db, 15)).export(out, format="wav")
    return to_ogg(out)

def do_normalize(wav):
    out = tmpf("wav")
    effects.normalize(AudioSegment.from_wav(wav)).export(out, format="wav")
    return to_ogg(out)

def do_reverse(wav):
    out = tmpf("wav")
    AudioSegment.from_wav(wav).reverse().export(out, format="wav")
    return to_ogg(out)

def do_fade(wav):
    audio = AudioSegment.from_wav(wav)
    out   = tmpf("wav")
    audio.fade_in(2000).fade_out(2000).export(out, format="wav")
    return to_ogg(out)

def do_echo(wav):
    audio   = AudioSegment.from_wav(wav)
    silence = AudioSegment.silent(duration=300)
    echo    = silence + (audio - 10)
    out     = tmpf("wav")
    audio.overlay(echo).export(out, format="wav")
    return to_ogg(out)

def do_reverb(wav, room=0.5, damping=0.5, wet=0.4):
    import pedalboard as pb
    y, sr = librosa.load(wav, sr=None, mono=False)
    if y.ndim == 1:
        y = y[np.newaxis, :]
    board  = pb.Pedalboard([pb.Reverb(room_size=room, damping=damping, wet_level=wet, dry_level=1-wet)])
    result = board(y, sr)
    out    = tmpf("wav")
    sf.write(out, result.T, sr)
    return to_ogg(out)

def do_eq(wav, low=0, mid=0, high=0):
    import pedalboard as pb
    y, sr = librosa.load(wav, sr=None, mono=False)
    if y.ndim == 1:
        y = y[np.newaxis, :]
    board = pb.Pedalboard([
        pb.HighpassFilter(cutoff_frequency_hz=80),
        pb.LowShelfFilter(cutoff_frequency_hz=250, gain_db=low),
        pb.PeakFilter(cutoff_frequency_hz=2000, gain_db=mid, q=0.7),
        pb.HighShelfFilter(cutoff_frequency_hz=8000, gain_db=high),
    ])
    result = board(y, sr)
    out    = tmpf("wav")
    sf.write(out, result.T, sr)
    return to_ogg(out)

def do_delay(wav, delay_ms=250, feedback=0.4, mix=0.5):
    y, sr   = librosa.load(wav, sr=None, mono=True)
    n_delay = int((delay_ms / 1000.0) * sr)
    result  = y.copy()
    delayed = y.copy()
    for i in range(6):
        delayed = np.concatenate([np.zeros(n_delay), delayed[:-n_delay]])
        result  = result + delayed * (feedback ** (i+1)) * mix
    result = result / np.max(np.abs(result) + 1e-9)
    out    = tmpf("wav")
    sf.write(out, result, sr)
    return to_ogg(out)

def do_autotune(wav, scale="C"):
    raise NotImplementedError("Autotune no disponible en esta versión")
    import pyworld as pw
    SCALES = {
        "C":[0,2,4,5,7,9,11],"C#":[1,3,5,6,8,10,0],"D":[2,4,6,7,9,11,1],
        "D#":[3,5,7,8,10,0,2],"E":[4,6,8,9,11,1,3],"F":[5,7,9,10,0,2,4],
        "F#":[6,8,10,11,1,3,5],"G":[7,9,11,0,2,4,6],"G#":[8,10,0,1,3,5,7],
        "A":[9,11,1,2,4,6,8],"A#":[10,0,2,3,5,7,9],"B":[11,1,3,4,6,8,10],
    }
    notes = SCALES.get(scale, SCALES["C"])
    y, sr  = librosa.load(wav, sr=22050, mono=True)
    y      = np.ascontiguousarray(y.astype(np.float64))
    fp     = 5.0
    dio_r  = pw.dio(y, sr, f0_floor=60.0, f0_ceil=800.0, channels_in_octave=2, frame_period=fp)
    _f0, t = (dio_r[0], dio_r[1]) if len(dio_r) == 2 else (dio_r[0], dio_r[1])
    f0     = pw.stonemask(y, _f0, t, sr)
    sp     = pw.cheaptrick(y, f0, t, sr)
    ap     = pw.d4c(y, f0, t, sr)
    corr   = f0.copy()
    for i, freq in enumerate(f0):
        if freq < 60.0:
            corr[i] = 0.0
            continue
        midi   = 12.0 * np.log2(freq / 440.0) + 69.0
        chroma = int(round(midi)) % 12
        dists  = [min(abs(n-chroma), 12-abs(n-chroma)) for n in notes]
        closest = notes[int(np.argmin(dists))]
        diff   = closest - chroma
        if diff > 6:  diff -= 12
        if diff < -6: diff += 12
        corr[i] = freq * (2.0 ** (diff / 12.0))
    y2 = pw.synthesize(corr, sp, ap, sr, frame_period=fp)
    peak = np.max(np.abs(y2))
    if peak > 0: y2 = y2 / peak
    out = tmpf("wav")
    sf.write(out, y2.astype(np.float32), int(sr))
    return to_ogg(out)

def analyze_audio(wav_path):
    y, sr    = librosa.load(wav_path, sr=None, mono=True)
    duration = round(librosa.get_duration(y=y, sr=sr), 1)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    bpm      = round(float(np.atleast_1d(tempo)[0]), 1)
    chroma   = librosa.feature.chroma_cqt(y=y, sr=sr)
    cm       = np.mean(chroma, axis=1)
    major_p  = [6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88]
    minor_p  = [6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17]
    best_s, best_k, best_m = -999, 0, 0
    for i in range(12):
        for mp, mn in [(major_p, 0), (minor_p, 1)]:
            p = np.roll(mp, i)
            s = float(np.corrcoef(cm, p)[0, 1])
            if s > best_s:
                best_s, best_k, best_m = s, i, mn
    rms  = float(np.mean(librosa.feature.rms(y=y)))
    dbfs = round(20 * np.log10(rms + 1e-9), 1)
    return {"duration": duration, "bpm": bpm,
            "key": NOTE_NAMES[best_k] + " " + MODES_MAP[best_m], "dbfs": dbfs}

def itunes_search(query):
    resp = requests.get("https://itunes.apple.com/search",
        params={"term": query, "media": "music", "limit": 5, "entity": "song"},
        headers={"User-Agent": "MkeyzStudio/1.0"}, timeout=15)
    resp.raise_for_status()
    return resp.json().get("results", [])

def format_track(t):
    dur_s   = t.get("trackTimeMillis", 0) // 1000
    url     = t.get("trackViewUrl", "")
    artwork = t.get("artworkUrl100", "").replace("100x100bb", "600x600bb")
    lines   = [
        f"🎵 *{t.get('trackName','N/A')}*",
        f"👤 {t.get('artistName','N/A')}",
        f"💿 {t.get('collectionName','N/A')} ({t.get('releaseDate','')[:4]})",
        f"🎸 {t.get('primaryGenreName','N/A')}  ·  ⏱️ {dur_s//60}:{dur_s%60:02d}",
    ]
    return "\n".join(lines), artwork, url

# ══════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════

async def typing(update):
    try: await update.effective_chat.send_action(action=ChatAction.TYPING)
    except: pass

async def upload_anim(update):
    try: await update.effective_chat.send_action(action=ChatAction.UPLOAD_VOICE)
    except: pass

async def edit(query, text, kb):
    try:
        if query.message.photo:
            await query.edit_message_caption(caption=text, parse_mode="Markdown", reply_markup=kb)
        elif query.message.text:
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
        else:
            await query.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)
    except Exception:
        await query.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

async def ask_upgrade(query, required_plan):
    perks = {
        PLAN_PRO: "🎛️ Mini DAW\n📊 Analizador\n🧮 Calculadora\n📈 Proyección",
        PLAN_STUDIO: "Todo lo Pro +\n🎤 Zona Artistas\n🤝 Colabs · Showcases",
    }
    plan_name = {PLAN_PRO: "Pro ⭐", PLAN_STUDIO: "Studio 🎛️"}.get(required_plan, required_plan)
    text = (
        f"🔒 *Esta función requiere el plan {plan_name}*\n\n"
        f"{perks.get(required_plan,'')}\n\n"
        "¿Quieres acceder? 👇"
    )
    try:
        if query.message.photo:
            await query.edit_message_caption(caption=text, parse_mode="Markdown", reply_markup=kb_planes())
        else:
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb_planes())
    except Exception:
        await query.message.reply_text(text, parse_mode="Markdown", reply_markup=kb_planes())

# ══════════════════════════════════════════════════════════
#  TECLADOS
# ══════════════════════════════════════════════════════════

def kb_main():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎵  Mis Beats",      callback_data="sec_beats"),
            InlineKeyboardButton("🧮  Calculadora",    callback_data="sec_calc"),
        ],
        [
            InlineKeyboardButton("💼  Cotizador",      callback_data="sec_cotizador"),
            InlineKeyboardButton("✏️  Títulos de Beat", callback_data="sec_titulos"),
        ],
        [
            InlineKeyboardButton("🎛️  Mini DAW",       callback_data="sec_daw"),
            InlineKeyboardButton("📊  Analizador",     callback_data="sec_analyze"),
        ],
        [
            InlineKeyboardButton("🔍  Buscar Canción", callback_data="sec_spotify"),
            InlineKeyboardButton("🎤  Zona Artistas",  callback_data="sec_artists"),
        ],
        [
            InlineKeyboardButton("📱  Redes",          callback_data="sec_redes"),
            InlineKeyboardButton("ℹ️   Sobre mí",      callback_data="sec_about"),
        ],
        [
            InlineKeyboardButton("📩  Contacto",       callback_data="sec_contact"),
            InlineKeyboardButton("💳  Mi Plan",        callback_data="sec_planes"),
        ],
        [InlineKeyboardButton("🏆  Reto Semanal",      callback_data="sec_reto")],
        [
            InlineKeyboardButton("🎮  Beat Battle  🔥",  callback_data="sec_battle"),
            InlineKeyboardButton("🥁  Adivina el BPM",   callback_data="sec_bpm"),
        ],
    ])

def kb_back():
    return InlineKeyboardMarkup([[InlineKeyboardButton("‹ Menú principal", callback_data="sec_main")]])

def kb_planes():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Pro — 50 Stars/mes (~$0.65)",    callback_data="buy_pro")],
        [InlineKeyboardButton("🎛️ Studio — 150 Stars/mes (~$2)", callback_data="buy_studio")],
        [InlineKeyboardButton("‹ Menú principal",                 callback_data="sec_main")],
    ])

def kb_cotizador_genero():
    rows, row = [], []
    for g in GENEROS_BEATS:
        row.append(InlineKeyboardButton(g, callback_data=f"cot_gen_{g}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton("‹ Menú principal", callback_data="sec_main")])
    return InlineKeyboardMarkup(rows)

def kb_cotizador_mood():
    rows = []
    for m in MOODS_BEATS:
        rows.append([InlineKeyboardButton(m, callback_data=f"cot_mood_{m}")])
    rows.append([InlineKeyboardButton("‹ Cancelar", callback_data="sec_main")])
    return InlineKeyboardMarkup(rows)

def kb_cotizador_uso():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎵 Solo streaming", callback_data="cot_uso_streaming")],
        [InlineKeyboardButton("📺 YouTube + Redes", callback_data="cot_uso_youtube")],
        [InlineKeyboardButton("📻 Radio + Comercial", callback_data="cot_uso_radio")],
        [InlineKeyboardButton("🏆 Uso exclusivo total", callback_data="cot_uso_exclusivo")],
        [InlineKeyboardButton("‹ Cancelar", callback_data="sec_main")],
    ])

def kb_beats():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒  Ver catálogo — BeatStars", url=LINKS["beatstars"])],
        [
            InlineKeyboardButton("🔥  Trap",       callback_data="beats_trap"),
            InlineKeyboardButton("🌴  Pop Latino", callback_data="beats_pop"),
        ],
        [
            InlineKeyboardButton("☁️   Lo-Fi",      callback_data="beats_lofi"),
            InlineKeyboardButton("🥁  Afrobeats",  callback_data="beats_afro"),
        ],
        [InlineKeyboardButton("‹ Menú principal",  callback_data="sec_main")],
    ])

def kb_redes():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎵  Spotify",     url=LINKS["spotify"])],
        [InlineKeyboardButton("🛍️   BeatStars",  url=LINKS["beatstars"])],
        [
            InlineKeyboardButton("📸  Instagram", url=LINKS["instagram"]),
            InlineKeyboardButton("🎬  TikTok",    url=LINKS["tiktok"]),
        ],
        [InlineKeyboardButton("▶️   YouTube",     url=LINKS["youtube"])],
        [InlineKeyboardButton("‹ Menú principal", callback_data="sec_main")],
    ])

def kb_calc():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎵  Spotify",          callback_data="calc_Spotify"),
            InlineKeyboardButton("🍎  Apple Music",      callback_data="calc_Apple Music"),
        ],
        [
            InlineKeyboardButton("📦  Amazon Unlimited", callback_data="calc_Amazon Unlimited"),
            InlineKeyboardButton("🌊  Tidal",            callback_data="calc_Tidal"),
        ],
        [
            InlineKeyboardButton("▶️   YouTube Premium",  callback_data="calc_YouTube Premium"),
            InlineKeyboardButton("📺  YouTube Ads",      callback_data="calc_YouTube Ads"),
        ],
        [
            InlineKeyboardButton("🎵  Audiomack",        callback_data="calc_Audiomack"),
            InlineKeyboardButton("🎵  TikTok",           callback_data="calc_TikTok"),
        ],
        [InlineKeyboardButton("📈  Proyección de ingresos", callback_data="calc_proyeccion")],
        [InlineKeyboardButton("‹ Menú principal",            callback_data="sec_main")],
    ])

def kb_calc_result(plat):
    rows = []
    row  = []
    for p in PLATAFORMAS.keys():
        if p == plat: continue
        row.append(InlineKeyboardButton(f"→ {p[:15]}", callback_data=f"calc_same_{p}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton(f"🔄 Otra cantidad — {plat}", callback_data=f"calc_{plat}")])
    rows.append([InlineKeyboardButton("‹ Menú principal", callback_data="sec_main")])
    return InlineKeyboardMarkup(rows)

def kb_daw():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎵  Pitch preset",    callback_data="daw_pitch_menu"),
            InlineKeyboardButton("🎵  Pitch custom",    callback_data="daw_pitch_custom"),
        ],
        [
            InlineKeyboardButton("⏩  Speed preset",    callback_data="daw_speed_menu"),
            InlineKeyboardButton("⏩  Speed custom",    callback_data="daw_speed_custom"),
        ],
        [
            InlineKeyboardButton("🥁  Tempo preset",    callback_data="daw_tempo_menu"),
            InlineKeyboardButton("🥁  Tempo custom",    callback_data="daw_tempo_custom"),
        ],
        [
            InlineKeyboardButton("🔊  Bass Boost",      callback_data="daw_bass"),
            InlineKeyboardButton("🔇  Normalizar",      callback_data="daw_norm"),
        ],
        [
            InlineKeyboardButton("🎚️  Fade in/out",     callback_data="daw_fade"),
            InlineKeyboardButton("🌊  Echo",            callback_data="daw_echo"),
        ],
        [
            InlineKeyboardButton("🌊  Reverb",          callback_data="daw_reverb_menu"),
            InlineKeyboardButton("🎚️  EQ",              callback_data="daw_eq_menu"),
        ],
        [InlineKeyboardButton("⏱️  Delay",           callback_data="daw_delay_menu")],
        [
            InlineKeyboardButton("⏮  Reverse",         callback_data="daw_rev"),
            InlineKeyboardButton("📊  Analizar",        callback_data="daw_analyze"),
        ],
        [
            InlineKeyboardButton("⬇️  MP3",             callback_data="daw_dl_mp3"),
            InlineKeyboardButton("⬇️  WAV",             callback_data="daw_dl_wav"),
        ],
        [
            InlineKeyboardButton("🔄  Nuevo audio",     callback_data="daw_reset"),
            InlineKeyboardButton("✖  Cerrar DAW",       callback_data="sec_main"),
        ],
    ])

def kb_daw_pitch():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▲ +1", callback_data="daw_pitch_1"),  InlineKeyboardButton("▼ -1", callback_data="daw_pitch_-1")],
        [InlineKeyboardButton("▲ +2", callback_data="daw_pitch_2"),  InlineKeyboardButton("▼ -2", callback_data="daw_pitch_-2")],
        [InlineKeyboardButton("▲ +3", callback_data="daw_pitch_3"),  InlineKeyboardButton("▼ -3", callback_data="daw_pitch_-3")],
        [InlineKeyboardButton("‹ Volver", callback_data="daw_back")],
    ])

def kb_daw_speed():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("×1.15", callback_data="daw_speed_1.15"), InlineKeyboardButton("×0.85", callback_data="daw_speed_0.85")],
        [InlineKeyboardButton("×1.25", callback_data="daw_speed_1.25"), InlineKeyboardButton("×0.75", callback_data="daw_speed_0.75")],
        [InlineKeyboardButton("×1.5",  callback_data="daw_speed_1.5"),  InlineKeyboardButton("×0.5",  callback_data="daw_speed_0.5")],
        [InlineKeyboardButton("‹ Volver", callback_data="daw_back")],
    ])

def kb_daw_tempo():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("+10%", callback_data="daw_tempo_1.1"), InlineKeyboardButton("-10%", callback_data="daw_tempo_0.9")],
        [InlineKeyboardButton("+20%", callback_data="daw_tempo_1.2"), InlineKeyboardButton("-20%", callback_data="daw_tempo_0.8")],
        [InlineKeyboardButton("+50%", callback_data="daw_tempo_1.5"), InlineKeyboardButton("-50%", callback_data="daw_tempo_0.5")],
        [InlineKeyboardButton("‹ Volver", callback_data="daw_back")],
    ])

def kb_daw_reverb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Sala pequeña",  callback_data="daw_reverb_0.2_0.5_0.3")],
        [InlineKeyboardButton("🏛️  Sala mediana", callback_data="daw_reverb_0.5_0.5_0.4")],
        [InlineKeyboardButton("🏟️  Sala grande",  callback_data="daw_reverb_0.8_0.3_0.5")],
        [InlineKeyboardButton("🌌 Cathedral",     callback_data="daw_reverb_0.95_0.2_0.6")],
        [InlineKeyboardButton("‹ Volver",         callback_data="daw_back")],
    ])

def kb_daw_eq():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔊 Boost Graves",  callback_data="daw_eq_6_0_0")],
        [InlineKeyboardButton("🎙️  Boost Medios", callback_data="daw_eq_0_6_0")],
        [InlineKeyboardButton("✨ Boost Agudos",  callback_data="daw_eq_0_0_6")],
        [InlineKeyboardButton("🎛️  Warm",          callback_data="daw_eq_8_2_-2")],
        [InlineKeyboardButton("💎 Bright",         callback_data="daw_eq_-2_2_8")],
        [InlineKeyboardButton("🎤 Vocal Boost",    callback_data="daw_eq_-3_6_3")],
        [InlineKeyboardButton("‹ Volver",          callback_data="daw_back")],
    ])

def kb_daw_delay():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Slapback 80ms",  callback_data="daw_delay_80_0.2_0.3")],
        [InlineKeyboardButton("🎸 Short 150ms",    callback_data="daw_delay_150_0.35_0.4")],
        [InlineKeyboardButton("🎵 Medium 250ms",   callback_data="daw_delay_250_0.45_0.5")],
        [InlineKeyboardButton("🌊 Long 400ms",     callback_data="daw_delay_400_0.5_0.5")],
        [InlineKeyboardButton("🌌 Deep 600ms",     callback_data="daw_delay_600_0.55_0.45")],
        [InlineKeyboardButton("‹ Volver",          callback_data="daw_back")],
    ])

def kb_daw_autotune():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("C",  callback_data="daw_autotune_C"),  InlineKeyboardButton("C#", callback_data="daw_autotune_C#"), InlineKeyboardButton("D",  callback_data="daw_autotune_D")],
        [InlineKeyboardButton("D#", callback_data="daw_autotune_D#"), InlineKeyboardButton("E",  callback_data="daw_autotune_E"),  InlineKeyboardButton("F",  callback_data="daw_autotune_F")],
        [InlineKeyboardButton("F#", callback_data="daw_autotune_F#"), InlineKeyboardButton("G",  callback_data="daw_autotune_G"),  InlineKeyboardButton("G#", callback_data="daw_autotune_G#")],
        [InlineKeyboardButton("A",  callback_data="daw_autotune_A"),  InlineKeyboardButton("A#", callback_data="daw_autotune_A#"), InlineKeyboardButton("B",  callback_data="daw_autotune_B")],
        [InlineKeyboardButton("‹ Volver", callback_data="daw_back")],
    ])

def kb_artists_main():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️  Mi perfil",      callback_data="art_profile"),
            InlineKeyboardButton("🤝  Buscar colabs",  callback_data="art_colabs"),
        ],
        [
            InlineKeyboardButton("💡  Compartir idea", callback_data="art_idea"),
            InlineKeyboardButton("🎵  Showcase",       callback_data="art_showcase"),
        ],
        [
            InlineKeyboardButton("📋  Feed reciente",  callback_data="art_feed"),
            InlineKeyboardButton("💬  Mi feedback",    callback_data="art_myfeed"),
        ],
        [InlineKeyboardButton("‹ Menú principal",      callback_data="sec_main")],
    ])

def kb_genres(prefix="reg_genre_"):
    rows, row = [], []
    for g in GENRES:
        row.append(InlineKeyboardButton(g, callback_data=prefix + g))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton("❌ Cancelar", callback_data="sec_artists")])
    return InlineKeyboardMarkup(rows)

# ══════════════════════════════════════════════════════════
#  COMANDOS
# ══════════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["mode"] = MODE_NONE
    u = update.effective_user
    text = (
        f"👋 Hola *{u.first_name}*\n\n"
        "Bienvenido al bot oficial de *Jeff Mkeyz* 🎛️\n"
        "Productor · Cantautor\n"
        "Pop Latino · Trap · Lo-Fi · Afrobeats\n"
        "🇩🇴 República Dominicana · 🇪🇸 España\n\n"
        "¿Qué quieres hacer hoy? 👇"
    )
    # Enviar foto, esperar 4 segundos, borrarla y mostrar menú limpio
    try:
        photo_msg = await update.message.reply_photo(photo=BANNER_URL)
        async def remove_and_show():
            await asyncio.sleep(4)
            try: await photo_msg.delete()
            except: pass
            await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb_main())
        asyncio.create_task(remove_and_show())
    except Exception:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb_main())

async def cmd_planes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    plan = db_get_plan(update.effective_user.id)
    await update.message.reply_text(
        f"💳 *Planes de Mkeyz Studio*\n\nTu plan actual: *{PLAN_LABELS.get(plan, plan)}*\n\n"
        "⭐ *Pro — 50 Stars/mes (~$0.65)*\n🎛️ DAW · 📊 Analizador · 🧮 Calculadora\n\n"
        "🎛️ *Studio — 150 Stars/mes (~$2)*\nTodo lo Pro + 🎤 Zona Artistas",
        parse_mode="Markdown", reply_markup=kb_planes())

async def cmd_mipan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    plan = db_get_plan(update.effective_user.id)
    await update.message.reply_text(
        f"👤 Tu plan: *{PLAN_LABELS.get(plan, plan)}*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Ver planes", callback_data="sec_planes")]]))

async def cmd_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    log.info(f"cmd_admin called by {uid}, ADMIN_ID={ADMIN_ID}, match={uid==ADMIN_ID}")
    if not is_admin(uid):
        await update.message.reply_text(f"❌ No autorizado. Tu ID: `{uid}`", parse_mode="Markdown")
        return
    args = ctx.args or []
    if not args:
        plan = db_get_plan(update.effective_user.id)
        await update.message.reply_text(
            f"🔧 *Panel Admin*\n\nTu plan: {PLAN_LABELS.get(plan)}\n\n"
            "`/admin studio` — activarte Studio\n"
            "`/admin pro` — activarte Pro\n"
            "`/admin free` — volver a Free\n"
            "`/admin give <id> <plan>` — dar plan\n"
            "`/admin check <id>` — ver plan",
            parse_mode="Markdown")
        return
    if args[0] in (PLAN_FREE, PLAN_PRO, PLAN_STUDIO):
        db_set_plan(update.effective_user.id, args[0], months=12)
        await update.message.reply_text(f"✅ Plan actualizado: *{PLAN_LABELS.get(args[0])}*", parse_mode="Markdown")
        return
    if args[0] == "give" and len(args) >= 3:
        try:
            db_set_plan(int(args[1]), args[2], months=1)
            await update.message.reply_text(f"✅ Usuario {args[1]} → *{args[2]}*", parse_mode="Markdown")
        except: await update.message.reply_text("Error.")
        return
    if args[0] == "check" and len(args) >= 2:
        try:
            plan = db_get_plan(int(args[1]))
            await update.message.reply_text(f"Usuario {args[1]}: *{PLAN_LABELS.get(plan)}*", parse_mode="Markdown")
        except: await update.message.reply_text("Error.")

# ══════════════════════════════════════════════════════════
#  CALLBACKS
# ══════════════════════════════════════════════════════════

async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data

    # Limpiar modo al navegar al menú
    if d in ("sec_main","sec_beats","sec_redes","sec_about","sec_contact","sec_artists"):
        ctx.user_data["mode"]     = MODE_NONE
        ctx.user_data["reg_step"] = None

    # ── Control de plan ────────────────────────────────────
    if d in PLAN_PERMS:
        required  = PLAN_PERMS[d]
        user_plan = db_get_plan(q.from_user.id)
        if required != PLAN_FREE and not plan_allows(user_plan, required):
            await ask_upgrade(q, required)
            return

    # ── Menú principal ─────────────────────────────────────
    if d == "sec_main":
        await edit(q, "👋 *Jeff Mkeyz* — Menú principal\n\nProductor · Cantautor\nPop Latino · Trap · Lo-Fi · Afrobeats 🎛️", kb_main())
        return

    # ── Simulador de Streams ───────────────────────────────
    if d == "sec_simulator":
        game_url = (GAME_URL.rstrip("/") + "/simulator") if GAME_URL else None
        if game_url:
            await edit(q,
                "📊 *Simulador de Streams*\n\n"
                "Configura cuántas canciones tienes, cuántos oyentes\n"
                "y cuántas veces repiten — ve el total en tiempo real.\n\n"
                "🎵 Canciones × 👥 Oyentes × 🔁 Repeticiones\n\n"
                "Calcula tus ganancias en todas las plataformas\ny tu progreso hacia las grandes metas.",
                InlineKeyboardMarkup([
                    [InlineKeyboardButton("📊 Abrir Simulador", web_app=WebAppInfo(url=game_url))],
                    [InlineKeyboardButton("← 𝗠𝗘𝗡Ú", callback_data="sec_main")],
                ]))
        else:
            await edit(q, "📊 Simulador no disponible.", kb_back())
        return

    # ── Cotizador ──────────────────────────────────────────
    if d == "sec_cotizador":
        ctx.user_data["cot"] = {}
        await edit(q,
            "💼 *Cotizador de Licencias*\n\n"
            "Te ayudo a encontrar la licencia perfecta para tu proyecto.\n\n"
            "Paso 1 de 3 — ¿Qué género necesitas?",
            kb_cotizador_genero())
        return

    if d.startswith("cot_gen_"):
        ctx.user_data["cot"]["genero"] = d[8:]
        await edit(q,
            f"💼 Género: *{d[8:]}* ✅\n\n"
            "Paso 2 de 3 — ¿Qué mood buscas?",
            kb_cotizador_mood())
        return

    if d.startswith("cot_mood_"):
        ctx.user_data["cot"]["mood"] = d[9:]
        await edit(q,
            f"💼 Mood: *{d[9:]}* ✅\n\n"
            "Paso 3 de 3 — ¿Para qué vas a usar el beat?",
            kb_cotizador_uso())
        return

    if d.startswith("cot_uso_"):
        uso  = d[8:]
        cot  = ctx.user_data.get("cot", {})
        genero = cot.get("genero","")
        mood   = cot.get("mood","")

        # Recommend license based on uso
        if uso == "streaming":
            rec = "Básica"
        elif uso == "youtube":
            rec = "Premium"
        elif uso in ("radio","exclusivo"):
            rec = "Exclusiva"
        else:
            rec = "Premium"

        lic = LICENCIAS[rec]
        alt = {k:v for k,v in LICENCIAS.items() if k != rec}

        text = (
            f"💼 *Tu cotización — {genero} · {mood}*\n\n"
            f"📋 Uso: {uso.replace('_',' ').title()}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✅ *Licencia recomendada: {rec}*\n"
            f"💵 `${lic['precio']} USD`\n"
            f"🎧 Hasta {lic['streams']} streams\n"
            f"🎬 {lic['vids']}\n"
            f"📻 Radio: {lic['radio']}\n"
            f"_{lic['desc']}_\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"*Otras opciones:*\n"
        )
        for nombre, l in alt.items():
            text += f"• *{nombre}* — `${l['precio']}` — {l['desc']}\n"

        await edit(q, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Ver beats en BeatStars", url=LINKS["beatstars"])],
            [InlineKeyboardButton("💬 Contactar por Telegram", url="https://t.me/jeffmkeyzx")],
            [InlineKeyboardButton("🔄 Nueva cotización", callback_data="sec_cotizador")],
            [InlineKeyboardButton("‹ Menú principal",    callback_data="sec_main")],
        ]))
        return

    # ── Generador de títulos ────────────────────────────────
    if d == "sec_titulos":
        ctx.user_data["mode"] = MODE_NONE
        await edit(q,
            "✏️ *Generador de Títulos de Beat*\n\n"
            "Escribe el género y el mood de tu beat\n"
            "y te genero 8 nombres creativos.\n\n"
            "Ejemplo: `trap oscuro agresivo`\n"
            "Ejemplo: `pop latino romántico`\n\n"
            "✏️ Descríbelo en el chat:",
            InlineKeyboardMarkup([[InlineKeyboardButton("‹ Cancelar", callback_data="sec_main")]]))
        ctx.user_data["mode"] = "titulos"
        return

    # ── Calculadora de licencias ────────────────────────────
    if d == "sec_calc_lic":
        await edit(q,
            "🧮 *Calculadora de Licencias*\n\n"
            f"*Básica — $49*\n"
            f"✅ 100K streams · 1 video\n"
            f"✅ YouTube · Redes sociales\n"
            f"❌ Radio · No exclusivo\n\n"
            f"*Premium — $149*\n"
            f"✅ 500K streams · Ilimitado\n"
            f"✅ Distribución en plataformas\n"
            f"✅ Radio · Uso comercial\n\n"
            f"*Exclusiva — $499*\n"
            f"✅ Streams ilimitados\n"
            f"✅ Derechos completos\n"
            f"✅ Solo para ti — nadie más puede comprarla",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Ir a BeatStars", url=LINKS["beatstars"])],
                [InlineKeyboardButton("‹ Menú principal",  callback_data="sec_main")],
            ]))
        return

    if d.startswith("titulo_copy_"):
        titulo = d[12:]
        await q.answer(f"✅ '{titulo}' copiado!", show_alert=True)
        return

    # ── Reto Semanal ───────────────────────────────────────
    if d == "sec_reto":
        reto    = get_current_reto()
        week_id = get_week_id()
        entries = db_get_reto_entries(week_id, limit=5)

        # Calculate days left
        secs_in_week  = 7 * 24 * 3600
        secs_this_week = int(time.time()) % secs_in_week
        days_left = 7 - (secs_this_week // 86400)

        text = (
            f"🏆 *Reto de la Semana*\n\n"
            f"{reto['emoji']} *{reto['titulo']}*\n\n"
            f"_{reto['desc']}_\n\n"
            f"⏳ Quedan *{days_left} días* para participar\n"
            f"👥 *{len(entries)}* participantes esta semana\n"
        )
        if entries:
            text += "\n*Top participantes:*\n"
            for i, e in enumerate(entries[:3]):
                medals = ["🥇","🥈","🥉"]
                text += f"{medals[i]} {e['name']} — {e['votes']} votos\n"

        kb_r = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎵 Participar — Subir audio", callback_data="reto_submit")],
            [InlineKeyboardButton("📋 Ver todos los participantes", callback_data="reto_feed")],
            [InlineKeyboardButton("← 𝗠𝗘𝗡Ú", callback_data="sec_main")],
        ])
        await edit(q, text, kb_r)
        return

    if d == "reto_submit":
        ctx.user_data["mode"] = MODE_RETO
        reto = get_current_reto()
        await edit(q,
            f"🏆 *{reto['titulo']}*\n\n"
            f"{reto['desc']}\n\n"
            f"👇 Envía tu audio para participar:\n"
            f"_Solo puedes participar una vez por semana_",
            InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="sec_reto")]]))
        return

    if d == "reto_feed":
        week_id = get_week_id()
        entries = db_get_reto_entries(week_id)
        reto    = get_current_reto()
        if not entries:
            await edit(q,
                f"🏆 *{reto['titulo']}*\n\n"
                "Aún no hay participantes esta semana.\n¡Sé el primero! 🎵",
                InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎵 Participar", callback_data="reto_submit")],
                    [InlineKeyboardButton("← Reto",        callback_data="sec_reto")],
                ]))
            return
        lines   = [f"🏆 *Participantes — {reto['titulo']}*\n"]
        buttons = []
        medals  = ["🥇","🥈","🥉"]
        for i, e in enumerate(entries):
            medal = medals[i] if i < 3 else f"{i+1}."
            lines.append(f"{medal} *{e['name']}* — {e['votes']} votos")
            buttons.append([InlineKeyboardButton(
                f"{medal} {e['name']} ({e['votes']} 🔥)",
                callback_data=f"reto_play_{e['id']}")])
        buttons.append([InlineKeyboardButton("← Reto", callback_data="sec_reto")])
        await edit(q, "\n".join(lines), InlineKeyboardMarkup(buttons))
        return

    if d.startswith("reto_play_"):
        entry_id = int(d[10:])
        entries  = db_get_reto_entries(get_week_id(), limit=20)
        entry    = next((e for e in entries if e["id"] == entry_id), None)
        if not entry:
            await q.answer("No encontrado.")
            return
        voted = db_vote_reto(entry_id, q.from_user.id)
        cap   = (
            f"🏆 *{entry['name']}*\n"
            f"🔥 {entry['votes'] + (1 if voted else 0)} votos"
        )
        kb_play = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "✅ Votado!" if voted else "🔥 Votar",
                callback_data=f"reto_play_{entry_id}")],
            [InlineKeyboardButton("← Ver todos", callback_data="reto_feed")],
        ])
        try:
            if entry["file_type"] == "voice":
                await q.message.reply_voice(voice=entry["file_id"], caption=cap,
                    parse_mode="Markdown", reply_markup=kb_play)
            else:
                await q.message.reply_audio(audio=entry["file_id"], caption=cap,
                    parse_mode="Markdown", reply_markup=kb_play)
        except Exception as e:
            await q.message.reply_text(cap, parse_mode="Markdown", reply_markup=kb_play)
        return

    # ── BPM Game ───────────────────────────────────────────
    if d == "sec_bpm":
        game_url = (GAME_URL.rstrip("/") + "/bpm") if GAME_URL else None
        if game_url:
            await edit(q,
                "🥁 *Adivina el BPM*\n\n"
                "Escucha el beat, toca al ritmo y adivina los BPM exactos.\n\n"
                "5 rondas · Hasta 550 puntos por ronda\n"
                "¡Demuestra tu oído musical! 🎯",
                InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎮 Jugar ahora", web_app=WebAppInfo(url=game_url))],
                    [InlineKeyboardButton("← 𝗠𝗘𝗡Ú", callback_data="sec_main")],
                ]))
        else:
            await edit(q,
                "🥁 *Adivina el BPM*\n\nJuego no disponible aún.",
                kb_back())
        return

    # ── Beat Battle ────────────────────────────────────────
    if d == "sec_battle":
        battles = db_get_active_battles(5)
        game_url = GAME_URL.rstrip("/") + "/game" if GAME_URL else None
        text = (
            "🎮 *Beat Battle Arena*\n\n"
            "Vota los mejores beats de la comunidad.\n"
            "Cada batalla dura *24 horas*. El más votado gana.\n\n"
        )
        if battles:
            text += f"🔥 *{len(battles)} batalla(s) activa(s) ahora*\n"
            for b in battles[:3]:
                text += f"\n• *{b['name']}* — 🔥{b['votes_fire']} votos"
        else:
            text += "_No hay batallas activas. ¡Sé el primero en subir tu beat!_"

        kb_b = []
        if game_url:
            kb_b.append([InlineKeyboardButton("🎮 Abrir Beat Battle Arena",
                         web_app=WebAppInfo(url=game_url))])
        kb_b.append([InlineKeyboardButton("🎵  Subir mi beat", callback_data="battle_submit")])
        kb_b.append([InlineKeyboardButton("‹ Menú principal", callback_data="sec_main")])
        await edit(q, text, InlineKeyboardMarkup(kb_b))
        return

    if d == "battle_submit":
        ctx.user_data["mode"] = MODE_BATTLE
        await edit(q,
            "🎵 *Subir Beat al Battle*\n\n"
            "Envía tu beat (MP3 o nota de voz).\n"
            "Estará activo durante *24 horas* para que la comunidad vote.\n\n"
            "👇 Envía el audio:",
            InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="sec_battle")]]))
        return

    if d == "battle_no_cap":
        file_id   = ctx.user_data.get("battle_file_id","")
        file_type = ctx.user_data.get("battle_file_type","audio")
        u         = q.from_user
        name      = u.first_name or u.username or "Anónimo"
        db_add_battle(u.id, name, file_id, file_type, "Beat sin nombre")
        ctx.user_data["mode"]     = MODE_NONE
        ctx.user_data["reg_step"] = None
        await edit(q,
            "✅ *¡Beat en la arena!*\n\n"
            "Tu beat está activo durante 24 horas.\n"
            "¡Comparte el bot para conseguir votos! 🔥",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 Ver el Battle", callback_data="sec_battle")],
                [InlineKeyboardButton("‹ Menú principal",          callback_data="sec_main")],
            ]))
        return

    # ── Planes ─────────────────────────────────────────────
    if d == "sec_planes":
        plan = db_get_plan(q.from_user.id)
        await edit(q,
            f"💳 *Planes de Mkeyz Studio*\n\nTu plan: *{PLAN_LABELS.get(plan)}*\n\n"
            "🆓 *Free* — Menú público · Buscar canciones\n\n"
            "⭐ *Pro — 50 Stars/mes (~$0.65)*\n"
            "✅ Mini DAW completo\n✅ Analizador\n✅ Calculadora\n✅ Proyección\n\n"
            "🎛️ *Studio — 150 Stars/mes (~$2)*\n"
            "✅ Todo lo Pro\n✅ Zona Artistas\n✅ Colabs · Showcases",
            kb_planes())
        return

    if d in ("buy_pro", "buy_studio"):
        plan  = PLAN_PRO if d == "buy_pro" else PLAN_STUDIO
        stars = PLAN_PRICES[plan]
        label = PLAN_LABELS[plan]
        invoice_msg = await q.message.reply_invoice(
            title=f"Mkeyz Studio — {label}",
            description="Acceso mensual a las herramientas profesionales de Mkeyz Studio.",
            payload=f"sub_{plan}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=label, amount=stars)],
        )
        try: await q.edit_message_text("💳 Factura enviada 👆\n\n_Se cierra en 10 seg si no completas el pago._", parse_mode="Markdown")
        except: pass

        # Auto-borrar la factura después de 10 segundos si no se pagó
        async def auto_delete():
            await asyncio.sleep(10)
            try:
                await invoice_msg.delete()
            except Exception:
                pass
        asyncio.create_task(auto_delete())
        return

    # ── Beats ──────────────────────────────────────────────
    if d == "sec_beats":
        await edit(q, "🎵 *Mis Beats*\n\nCatálogo en BeatStars:\nTrap · Pop Latino · Lo-Fi · Afrobeats\n\n✅ Licencias exclusivas y no exclusivas\n✅ Stems disponibles · Uso comercial", kb_beats())
        return

    if d in ("beats_trap","beats_pop","beats_lofi","beats_afro"):
        icons = {"beats_trap":"🔥","beats_pop":"🌴","beats_lofi":"☁️","beats_afro":"🥁"}
        names = {"beats_trap":"Trap","beats_pop":"Pop Latino","beats_lofi":"Lo-Fi","beats_afro":"Afrobeats"}
        await edit(q, f"{icons[d]} *Beats de {names[d]}*\n\nEncuéntralos en BeatStars 👇", kb_beats())
        return

    # ── Redes ──────────────────────────────────────────────
    if d == "sec_redes":
        await edit(q, "📱 *Redes y Plataformas*\n\nSígueme en todas las plataformas 👇", kb_redes())
        return

    # ── Sobre mí ───────────────────────────────────────────
    if d == "sec_about":
        text = (
            "🎛️ *Sobre Jeff Mkeyz*\n\n"
            "Productor musical y cantautor independiente\n\n"
            "🎚️ Géneros: Pop Latino · Trap · Lo-Fi · Afrobeats\n"
            "🎤 DAW: FL Studio\n"
            "🎙️ Universal Audio Volt 2 · Lewitt LCT 440 PURE\n"
            "📦 Distribución: DistroKid\n"
            "🇪🇸 España · 🇩🇴 República Dominicana"
        )
        # Mostrar foto, esperar 4 seg, borrar y mostrar info
        try:
            await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([[]]))
        except: pass
        try:
            await q.message.reply_photo(photo=BANNER_URL, caption=text,
                                         parse_mode="Markdown", reply_markup=kb_back())
        except:
            await q.message.reply_text(text, parse_mode="Markdown", reply_markup=kb_back())
        return

    # ── Contacto ───────────────────────────────────────────
    if d == "sec_contact":
        await edit(q, "📩 *Contacto*\n\n¿Colaboraciones o propuestas?\n\n📧 `jeffmkeyzmusic@gmail.com`\n\nO escríbeme por redes 👇", kb_redes())
        return

    # ── Calculadora ────────────────────────────────────────
    if d == "sec_calc":
        await edit(q, "🧮 *Calculadora de Royalties*\n\nSelecciona la plataforma:\n\n_Puedes calcular varias cantidades seguidas_", kb_calc())
        return

    if d == "calc_proyeccion":
        ctx.user_data["mode"]      = MODE_PROJ
        ctx.user_data["proj_step"] = "streams"
        await edit(q,
            "📈 *Proyección de Ingresos*\n\n"
            "Paso 1 de 3 — ¿Cuántos streams tienes al mes?\nEjemplo: `50000`",
            InlineKeyboardMarkup([[InlineKeyboardButton("‹ Calculadora", callback_data="sec_calc")]]))
        return

    if d.startswith("calc_same_"):
        plat    = d[10:]
        streams = ctx.user_data.get("calc_last_streams")
        if not streams:
            ctx.user_data["mode"]      = MODE_CALC
            ctx.user_data["calc_plat"] = plat
            await edit(q, f"🧮 *Calculadora — {plat}*\n\nEscribe el número de streams:", kb_back())
            return
        rate = PLATAFORMAS.get(plat, 0.003)
        usd  = round(streams * rate, 3)
        eur  = round(usd * EUR_RATE, 3)
        ctx.user_data["calc_plat"] = plat
        await edit(q,
            f"🧮 *{plat}*\n\n🎧 Streams: `{streams:,}`\n\n💵 USD: `${usd:,.3f}`\n💶 EUR: `€{eur:,.3f}`\n\n_Escribe otro número o compara:_",
            kb_calc_result(plat))
        return

    if d.startswith("proj_plat_"):
        plat    = d[10:]
        streams = ctx.user_data.get("proj_streams", 0)
        growth  = ctx.user_data.get("proj_growth", 10)
        rate    = PLATAFORMAS.get(plat, 0.003)
        factor  = 1 + (growth / 100)
        lines   = [f"📈 *Proyección — {plat}*", "",
                   f"Streams actuales: `{streams:,}`",
                   f"Crecimiento mensual: `{growth}%`",
                   f"Rate: `${rate:.6f}` por stream", "", "*Mes a mes:*"]
        total_usd = 0
        cur = streams
        for mes in range(1, 7):
            cur  = int(cur * factor)
            usd  = round(cur * rate, 2)
            eur  = round(usd * EUR_RATE, 2)
            total_usd += usd
            lines.append(f"Mes {mes}: `{cur:,}` → `${usd:.2f}` / `€{eur:.2f}`")
        lines += ["", f"💰 *Total 6 meses: `${total_usd:.2f}` / `€{round(total_usd*EUR_RATE,2):.2f}`*"]
        ctx.user_data["mode"] = MODE_NONE
        kb_p = InlineKeyboardMarkup([
            [InlineKeyboardButton("📈 Nueva proyección", callback_data="calc_proyeccion")],
            [InlineKeyboardButton("‹ Menú principal",    callback_data="sec_main")],
        ])
        try: await q.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_p)
        except: await q.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_p)
        return

    if d.startswith("calc_"):
        plat = d[5:]
        rate = PLATAFORMAS.get(plat, 0.003)
        ctx.user_data["mode"]      = MODE_CALC
        ctx.user_data["calc_plat"] = plat
        last = ctx.user_data.get("calc_last_streams")
        hint = f"\n\n_Último valor: {last:,} streams_" if last else ""
        text = f"🧮 *Calculadora — {plat}*\n\n💲 Rate: `${rate:.6f}` por stream\n\n✏️ Escribe el número de streams:" + hint
        kb_c = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Cambiar plataforma", callback_data="sec_calc")],
            [InlineKeyboardButton("‹ Menú principal",      callback_data="sec_main")],
        ])
        try:
            if q.message.photo: await q.edit_message_caption(caption=text, parse_mode="Markdown", reply_markup=kb_c)
            else: await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb_c)
            ctx.user_data["last_bot_msg"] = q.message.message_id
        except: pass
        return

    # ── Analizador ─────────────────────────────────────────
    if d == "sec_analyze":
        ctx.user_data["mode"] = MODE_ANLZ
        await edit(q, "📊 *Analizador de Audio*\n\nEnvíame un audio y te digo:\n\n🥁 BPM · 🎼 Key · ⏱️ Duración · 🔊 Volumen\n\n👇 Envía tu audio:", kb_back())
        return

    # ── Buscar canción ─────────────────────────────────────
    if d == "sec_spotify":
        ctx.user_data["mode"]           = MODE_SEARCH
        ctx.user_data["search_results"] = {}
        await edit(q, "🔍 *Buscador de Canciones*\n\nEscribe el nombre de la canción o artista.\nEjemplo: `Jeff Mkeyz No Me Creo`\n\n✏️ Escríbelo en el chat:", kb_back())
        return

    if d.startswith("it_track_"):
        track = ctx.user_data.get("search_results", {}).get(d[9:])
        if track:
            ctx.user_data["mode"] = MODE_SEARCH
            text, artwork, url = format_track(track)
            buttons = []
            if url:
                buttons.append([InlineKeyboardButton("🎵 Ver en Apple Music", url=url)])
            buttons.append([InlineKeyboardButton("🖼️ Descargar portada", callback_data=f"dl_cover_{d[9:]}")])
            buttons.append([InlineKeyboardButton("🔍 Buscar otra",       callback_data="sec_spotify")])
            buttons.append([InlineKeyboardButton("‹ Menú",               callback_data="sec_main")])
            kb_track = InlineKeyboardMarkup(buttons)
            try:
                await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([[]]))
            except: pass
            if artwork:
                await q.message.reply_photo(photo=artwork, caption=text,
                    parse_mode="Markdown", reply_markup=kb_track)
            else:
                await q.message.reply_text(text, parse_mode="Markdown", reply_markup=kb_track)
        return

    if d.startswith("dl_cover_"):
        idx   = d[9:]
        track = ctx.user_data.get("search_results", {}).get(idx)
        if not track:
            await q.answer("No encontrado.")
            return
        artwork = track.get("artworkUrl100","").replace("100x100bb","3000x3000bb")
        name    = track.get("trackName","cover").replace(" ","_")[:30]
        artist  = track.get("artistName","").replace(" ","_")[:20]
        try:
            await q.answer("⏳ Descargando...")
            resp = requests.get(artwork, timeout=15)
            resp.raise_for_status()
            from io import BytesIO
            img = BytesIO(resp.content)
            img.name = f"{artist}_{name}.jpg"
            await q.message.reply_document(
                document=img,
                filename=f"{artist}_{name}.jpg",
                caption=f"🖼️ *{track.get('trackName','N/A')}*\n👤 {track.get('artistName','N/A')}\n_Alta calidad · 3000×3000px_",
                parse_mode="Markdown")
        except Exception as e:
            log.error(f"Cover: {e}")
            await q.message.reply_text("❌ No se pudo descargar la portada.")
        return

    # ── Mini DAW ───────────────────────────────────────────
    if d == "sec_daw":
        ctx.user_data["mode"] = MODE_DAW
        await edit(q, "🎛️ *Mini DAW — Mkeyz Studio*\n\nEnvíame un audio (MP3, OGG, nota de voz)\ny te doy las opciones de edición 👇", kb_back())
        return

    if d == "daw_back":
        await edit(q, "🎛️ *Mini DAW*\n\n¿Qué quieres hacer?", kb_daw())
        return

    if d == "daw_reset":
        old_wav = ctx.user_data.get("wav")
        if old_wav and os.path.exists(old_wav):
            try: os.remove(old_wav)
            except: pass
        ctx.user_data["wav"]  = None
        ctx.user_data["mode"] = MODE_DAW
        await edit(q, "🎛️ *Mini DAW*\n\nAudio descartado.\nEnvíame un nuevo audio:", InlineKeyboardMarkup([[InlineKeyboardButton("‹ Menú principal", callback_data="sec_main")]]))
        return

    if d in ("daw_pitch_menu","daw_speed_menu","daw_tempo_menu","daw_reverb_menu","daw_eq_menu","daw_delay_menu","daw_autotune_menu"):
        menus = {
            "daw_pitch_menu":   ("🎵 *Pitch Shift*\n\nElige los semitonos:",   kb_daw_pitch()),
            "daw_speed_menu":   ("⏩ *Speed*\n\nElige el factor:",              kb_daw_speed()),
            "daw_tempo_menu":   ("🥁 *Tempo*\n\nElige el cambio:",             kb_daw_tempo()),
            "daw_reverb_menu":  ("🌊 *Reverb*\n\nElige el tipo de sala:",      kb_daw_reverb()),
            "daw_eq_menu":      ("🎚️ *EQ*\n\nElige un preset:",               kb_daw_eq()),
            "daw_delay_menu":   ("⏱️ *Delay*\n\nElige el tiempo:",             kb_daw_delay()),
    
        }
        text, kb = menus[d]
        await edit(q, text, kb)
        return

    if d in ("daw_pitch_custom","daw_speed_custom","daw_tempo_custom"):
        infos = {
            "daw_pitch_custom": (MODE_DAW_PITCH, "🎵 *Pitch custom*\n\nEscribe los semitonos (-12 a +12)\nEjemplo: `5` ó `-3`"),
            "daw_speed_custom": (MODE_DAW_SPEED, "⏩ *Speed custom*\n\nEscribe el factor (0.5 a 2.0)\nEjemplo: `1.5` ó `0.7`"),
            "daw_tempo_custom": (MODE_DAW_TEMPO, "🥁 *Tempo custom*\n\nEscribe el % de cambio (-50 a +100)\nEjemplo: `+25` ó `-15`"),
        }
        mode, text = infos[d]
        if not ctx.user_data.get("wav"):
            await q.message.reply_text("Envía un audio primero.", reply_markup=kb_main())
            return
        ctx.user_data["mode"] = mode
        await edit(q, text, InlineKeyboardMarkup([[InlineKeyboardButton("‹ Volver", callback_data="daw_back")]]))
        return

    # ── DAW descargas ──────────────────────────────────────
    if d in ("daw_dl_mp3","daw_dl_wav"):
        wav = ctx.user_data.get("wav")
        if not wav or not os.path.exists(wav):
            await q.message.reply_text("⚠️ No hay audio cargado.", reply_markup=kb_main())
            return
        try:
            await upload_anim(update)
            if d == "daw_dl_mp3":
                out, fname, cap = await asyncio.to_thread(to_mp3, wav), "audio_mkeyz.mp3", "MP3 320kbps"
            else:
                out, fname, cap = await asyncio.to_thread(to_wav_file, wav), "audio_mkeyz.wav", "WAV sin pérdida"
            with open(out, "rb") as f:
                await q.message.reply_document(document=f, filename=fname, caption=f"⬇️ {cap}", reply_markup=kb_daw())
            os.remove(out)
        except Exception as e:
            log.error(f"Download: {e}")
            await q.message.reply_text(f"❌ Error: {e}")
        return

    # ── DAW controles ──────────────────────────────────────
    if d.startswith("daw_"):
        wav = ctx.user_data.get("wav")
        if not wav or not os.path.exists(wav):
            await q.message.reply_text("⚠️ No hay audio. Entra al Mini DAW y envía un audio.", reply_markup=kb_main())
            return

        try: await q.edit_message_text("⏳ Procesando…")
        except: pass

        result_caption = None
        result_ogg     = None

        try:
            if d == "daw_analyze":
                await upload_anim(update)
                info = await asyncio.to_thread(analyze_audio, wav)
                await q.message.reply_text(
                    f"📊 *Análisis*\n\n⏱️ `{info['duration']}s` · 🥁 `{info['bpm']} BPM` · 🎼 `{info['key']}` · 🔊 `{info['dbfs']} dBFS`",
                    parse_mode="Markdown", reply_markup=kb_daw())
                try: await q.edit_message_text("📊 Análisis enviado ↓")
                except: pass
                return

            if d.startswith("daw_reverb_"):
                parts = d.split("_")[2:]
                room, damp, wet = float(parts[0]), float(parts[1]), float(parts[2])
                labels = {"0.2":"Sala pequeña","0.5":"Sala mediana","0.8":"Sala grande","0.95":"Cathedral"}
                result_caption = f"🌊 Reverb — {labels.get(parts[0],'Reverb')}"
                await upload_anim(update)
                result_ogg = await asyncio.to_thread(do_reverb, wav, room, damp, wet)

            elif d.startswith("daw_eq_"):
                parts = d.split("_")[2:]
                low, mid, high = float(parts[0]), float(parts[1]), float(parts[2])
                presets = {"6_0_0":"Boost Graves","0_6_0":"Boost Medios","0_0_6":"Boost Agudos",
                           "8_2_-2":"Warm","-2_2_8":"Bright","-3_6_3":"Vocal Boost"}
                label = presets.get("_".join(parts), "EQ")
                result_caption = f"🎚️ EQ — {label}"
                await upload_anim(update)
                result_ogg = await asyncio.to_thread(do_eq, wav, low, mid, high)

            elif d.startswith("daw_delay_"):
                parts = d.split("_")[2:]
                ms, fb, mix = float(parts[0]), float(parts[1]), float(parts[2])
                result_caption = f"⏱️ Delay {int(ms)}ms"
                await upload_anim(update)
                result_ogg = await asyncio.to_thread(do_delay, wav, ms, fb, mix)

            elif d.startswith("daw_autotune_"):
                scale = d[13:]
                result_caption = f"🎤 Autotune — {scale} Major"
                await upload_anim(update)
                result_ogg = await asyncio.to_thread(do_autotune, wav, scale)

            else:
                actions = {
                    "daw_pitch_1":    (do_pitch,     (wav,  1),    "🎵 Pitch ▲ +1"),
                    "daw_pitch_-1":   (do_pitch,     (wav, -1),    "🎵 Pitch ▼ -1"),
                    "daw_pitch_2":    (do_pitch,     (wav,  2),    "🎵 Pitch ▲ +2"),
                    "daw_pitch_-2":   (do_pitch,     (wav, -2),    "🎵 Pitch ▼ -2"),
                    "daw_pitch_3":    (do_pitch,     (wav,  3),    "🎵 Pitch ▲ +3"),
                    "daw_pitch_-3":   (do_pitch,     (wav, -3),    "🎵 Pitch ▼ -3"),
                    "daw_speed_1.15": (do_speed,     (wav, 1.15),  "⏩ Speed ×1.15"),
                    "daw_speed_0.85": (do_speed,     (wav, 0.85),  "⏪ Speed ×0.85"),
                    "daw_speed_1.25": (do_speed,     (wav, 1.25),  "⏩ Speed ×1.25"),
                    "daw_speed_0.75": (do_speed,     (wav, 0.75),  "⏪ Speed ×0.75"),
                    "daw_speed_1.5":  (do_speed,     (wav, 1.5),   "⏩ Speed ×1.5"),
                    "daw_speed_0.5":  (do_speed,     (wav, 0.5),   "⏪ Speed ×0.5"),
                    "daw_tempo_1.1":  (do_tempo,     (wav, 1.1),   "🥁 Tempo +10%"),
                    "daw_tempo_0.9":  (do_tempo,     (wav, 0.9),   "🥁 Tempo -10%"),
                    "daw_tempo_1.2":  (do_tempo,     (wav, 1.2),   "🥁 Tempo +20%"),
                    "daw_tempo_0.8":  (do_tempo,     (wav, 0.8),   "🥁 Tempo -20%"),
                    "daw_tempo_1.5":  (do_tempo,     (wav, 1.5),   "🥁 Tempo +50%"),
                    "daw_tempo_0.5":  (do_tempo,     (wav, 0.5),   "🥁 Tempo -50%"),
                    "daw_bass":       (do_bass,      (wav,),       "🔊 Bass boost"),
                    "daw_norm":       (do_normalize, (wav,),       "🔇 Normalizado"),
                    "daw_rev":        (do_reverse,   (wav,),       "⏮ Invertido"),
                    "daw_fade":       (do_fade,      (wav,),       "🎚️ Fade in/out"),
                    "daw_echo":       (do_echo,      (wav,),       "🌊 Echo"),
                }
                if d not in actions:
                    return
                fn, args, result_caption = actions[d]
                await upload_anim(update)
                result_ogg = await asyncio.to_thread(fn, *args)

            if result_ogg:
                result_wav = await asyncio.to_thread(ogg_to_wav, result_ogg)
                old_wav    = ctx.user_data.get("wav")
                with open(result_ogg, "rb") as f:
                    await q.message.reply_voice(voice=f,
                        caption=f"{result_caption} ✅\n_Siguiente efecto se aplica sobre este_",
                        reply_markup=kb_daw())
                os.remove(result_ogg)
                ctx.user_data["wav"] = result_wav
                if old_wav and os.path.exists(old_wav) and old_wav != result_wav:
                    try: os.remove(old_wav)
                    except: pass
                try: await q.edit_message_text(f"✅ {result_caption}")
                except: pass

        except Exception as e:
            log.error(f"DAW [{d}]: {e}")
            await q.message.reply_text(f"❌ Error: `{str(e)[:80]}`", parse_mode="Markdown", reply_markup=kb_daw())
        return

    # ── Zona Artistas ──────────────────────────────────────
    if d == "sec_artists":
        artist = db_get_artist(q.from_user.id)
        if artist:
            await edit(q,
                f"🎤 *Zona Artistas*\n\nBienvenido, *{artist['name']}* 👋\nGénero: {artist['genre']}\n\n¿Qué quieres hacer?",
                kb_artists_main())
        else:
            await edit(q,
                "🎤 *Zona Artistas*\n\nUn espacio para conectar con otros artistas:\n\n"
                "🤝 Buscar colaboraciones\n💡 Compartir ideas\n🎵 Showcases con feedback\n\n"
                "Para participar regístrate primero 👇",
                InlineKeyboardMarkup([
                    [InlineKeyboardButton("✏️ Registrarme",  callback_data="art_register")],
                    [InlineKeyboardButton("‹ Menú principal", callback_data="sec_main")],
                ]))
        return

    if d == "art_register":
        ctx.user_data["mode"]     = MODE_REG
        ctx.user_data["reg_step"] = "name"
        await edit(q, "✏️ *Registro — Paso 1 de 4*\n\n¿Cuál es tu nombre artístico?",
            InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="sec_artists")]]))
        return

    if d == "art_profile":
        artist = db_get_artist(q.from_user.id)
        if not artist:
            await q.message.reply_text("Regístrate primero.", reply_markup=kb_back())
            return
        ig = f"@{artist['ig']}" if artist.get("ig") else "No especificado"
        await edit(q,
            f"🎤 *Tu perfil*\n\n👤 *{artist['name']}*\n🎸 {artist['genre']}\n📝 {artist.get('bio') or 'Sin bio'}\n📸 {ig}",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ Editar",           callback_data="art_register")],
                [InlineKeyboardButton("🗑️ Eliminar cuenta",  callback_data="art_delete_confirm")],
                [InlineKeyboardButton("‹ Zona Artistas",     callback_data="sec_artists")],
            ]))
        return

    if d == "art_delete_confirm":
        await edit(q, "🗑️ *Eliminar cuenta*\n\n¿Estás seguro? Se borrará todo tu contenido.\n\n⚠️ No se puede deshacer.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Sí, eliminar", callback_data="art_delete_yes")],
                [InlineKeyboardButton("❌ Cancelar",     callback_data="art_profile")],
            ]))
        return

    if d == "art_delete_yes":
        db_delete_artist(q.from_user.id)
        await edit(q, "✅ Cuenta eliminada.\nPuedes registrarte de nuevo cuando quieras.",
            InlineKeyboardMarkup([[InlineKeyboardButton("‹ Zona Artistas", callback_data="sec_artists")]]))
        return

    if d == "art_colabs":
        await edit(q, "🤝 *Buscar Colaboraciones*\n\nFiltra por género:", kb_genres(prefix="colab_genre_"))
        return

    if d.startswith("colab_genre_"):
        genre   = d[12:]
        artists = db_all_artists(genre=genre)
        me      = db_get_artist(q.from_user.id)
        if not artists:
            await edit(q, f"No hay artistas en *{genre}* todavía.\n¡Sé el primero!",
                InlineKeyboardMarkup([[InlineKeyboardButton("‹ Buscar", callback_data="art_colabs")]]))
            return
        lines   = [f"🤝 *Artistas de {genre}*\n"]
        buttons = []
        for a in artists[:10]:
            if me and a["tg_id"] == me["tg_id"]: continue
            ig = f" · @{a['ig']}" if a.get("ig") else ""
            lines.append(f"• *{a['name']}*{ig}")
            if a.get("username"):
                buttons.append([InlineKeyboardButton(a["name"], url=f"https://t.me/{a['username']}")])
        buttons.append([InlineKeyboardButton("‹ Colabs", callback_data="art_colabs")])
        await edit(q, "\n".join(lines), InlineKeyboardMarkup(buttons))
        return

    if d == "art_idea":
        if not db_get_artist(q.from_user.id):
            await q.message.reply_text("Regístrate primero.", reply_markup=kb_back())
            return
        ctx.user_data["mode"] = MODE_IDEA
        await edit(q, "💡 *Compartir Idea*\n\nEnvía texto o audio:\n\n👇 Escribe o envía el audio:",
            InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="sec_artists")]]))
        return

    if d == "art_showcase":
        if not db_get_artist(q.from_user.id):
            await q.message.reply_text("Regístrate primero.", reply_markup=kb_back())
            return
        ctx.user_data["mode"] = MODE_SHOW
        await edit(q, "🎵 *Showcase*\n\nSube un preview para recibir feedback.\n\n👇 Envía el audio:",
            InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="sec_artists")]]))
        return

    if d == "art_feed":
        posts = db_get_posts(limit=8)
        if not posts:
            await edit(q, "📋 *Feed reciente*\n\nAún no hay posts.\n¡Sé el primero!", kb_artists_main())
            return
        lines   = ["📋 *Feed de la Comunidad*\n"]
        buttons = []
        for p in posts:
            ts   = time.strftime("%d/%m", time.localtime(p["posted_at"]))
            icon = "💡" if p["type"] == "idea" else "🎵"
            desc = (p["content"] or p["caption"] or "Audio")[:35]
            lines.append(f"{icon} *{p['artist_name']}* — {desc} _({ts})_")
            if p["type"] == "showcase":
                buttons.append([InlineKeyboardButton(
                    f"🎵 {p['artist_name']} — {(p['caption'] or 'Preview')[:25]}",
                    callback_data=f"feed_post_{p['id']}")])
        buttons.append([InlineKeyboardButton("‹ Zona Artistas", callback_data="sec_artists")])
        await edit(q, "\n".join(lines), InlineKeyboardMarkup(buttons))
        return

    if d.startswith("feed_post_"):
        post_id   = int(d[10:])
        post      = db_get_post(post_id)
        feedbacks = db_get_feedback(post_id)
        if not post:
            await q.answer("Post no encontrado.")
            return
        fb_text = ""
        if feedbacks:
            fb_text = f"\n\n💬 *Feedback ({len(feedbacks)}):*\n"
            for fb in feedbacks[:3]:
                fb_text += f"• *{fb['from_name']}:* {fb['text'][:60]}\n"
        cap     = f"{post.get('caption') or 'Preview'}\n_por {post['artist_name']}_" + fb_text
        kb_post = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Dejar feedback", callback_data=f"fb_write_{post_id}")],
            [InlineKeyboardButton("‹ Feed",            callback_data="art_feed")],
        ])
        ctx.user_data["fb_post_id"] = post_id
        ctx.user_data["mode"]       = MODE_FB
        ftype = post.get("file_type","audio")
        if post.get("file_id"):
            try:
                if ftype == "voice":
                    await q.message.reply_voice(voice=post["file_id"], caption=cap, parse_mode="Markdown", reply_markup=kb_post)
                else:
                    await q.message.reply_audio(audio=post["file_id"], caption=cap, parse_mode="Markdown", reply_markup=kb_post)
            except Exception as e:
                log.error(f"Feed play: {e}")
                await q.message.reply_text(cap + "\n\n⚠️ No se pudo cargar el audio.", parse_mode="Markdown", reply_markup=kb_post)
        else:
            await q.message.reply_text(cap, parse_mode="Markdown", reply_markup=kb_post)
        return

    if d.startswith("fb_write_"):
        ctx.user_data["fb_post_id"] = int(d[9:])
        ctx.user_data["mode"]       = MODE_FB
        await q.message.reply_text("💬 Escribe tu feedback:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="art_feed")]]))
        return

    if d == "art_myfeed":
        artist = db_get_artist(q.from_user.id)
        if not artist:
            await q.message.reply_text("Regístrate primero.", reply_markup=kb_back())
            return
        posts  = db_get_posts(ptype="showcase")
        all_fb = []
        for p in posts:
            if p.get("artist_tg_id") == q.from_user.id:
                all_fb.extend(db_get_feedback(p["id"]))
        if not all_fb:
            await edit(q, "💬 *Mi Feedback*\n\nAún no tienes feedback.", kb_artists_main())
            return
        lines = ["💬 *Feedback recibido*\n"]
        for fb in all_fb[:10]:
            ts = time.strftime("%d/%m", time.localtime(fb["sent_at"]))
            lines.append(f"• *{fb['from_name']}:* {fb['text'][:80]} _({ts})_")
        await edit(q, "\n".join(lines), kb_artists_main())
        return

    if d.startswith("reg_genre_"):
        genre = d[10:]
        ctx.user_data["mode"]      = MODE_REG
        ctx.user_data["reg_genre"] = genre
        ctx.user_data["reg_step"]  = "bio"
        try:
            await q.edit_message_text(
                f"✏️ *Registro — Paso 3 de 4*\n\nGénero: *{genre}* ✅\n\nEscribe tu bio corta:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="sec_artists")]]))
        except Exception:
            await q.message.chat.send_message(
                f"✏️ *Registro — Paso 3 de 4*\n\nGénero: *{genre}* ✅\n\nEscribe tu bio corta:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="sec_artists")]]))
        return

    if d == "reg_skip_ig":
        u = q.from_user
        db_register(u.id, u.username, ctx.user_data["reg_name"],
                    ctx.user_data["reg_genre"], ctx.user_data.get("reg_bio",""), "")
        ctx.user_data["mode"] = MODE_NONE
        name = ctx.user_data.get("reg_name","")
        try:
            await q.edit_message_text(f"✅ *¡Registro completado!*\n\nBienvenido, *{name}* 🎤",
                parse_mode="Markdown", reply_markup=kb_artists_main())
        except:
            await q.message.chat.send_message(f"✅ *¡Registro completado!*\n\nBienvenido, *{name}* 🎤",
                parse_mode="Markdown", reply_markup=kb_artists_main())
        return

    if d == "show_no_cap":
        file_id   = ctx.user_data.get("show_file_id","")
        file_type = ctx.user_data.get("show_file_type","audio")
        db_add_post(q.from_user.id, "showcase", file_id=file_id, caption="Preview", file_type=file_type)
        ctx.user_data["mode"]     = MODE_NONE
        ctx.user_data["reg_step"] = None
        await edit(q, "🎵 *Showcase publicado!*\n\nYa está visible en el feed.", kb_artists_main())
        return

# ══════════════════════════════════════════════════════════
#  MENSAJES DE TEXTO
# ══════════════════════════════════════════════════════════

async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    mode  = ctx.user_data.get("mode", MODE_NONE)
    texto = update.message.text.strip()

    # ── Generador de títulos ──────────────────────────────
    if mode == "titulos":
        ctx.user_data["mode"] = MODE_NONE
        import random
        texto_lower = texto.lower()
        titulos = TITULOS_POOL.get("default")
        for genero, names in TITULOS_POOL.items():
            if genero in texto_lower:
                titulos = names
                break
        seleccionados = random.sample(titulos, min(8, len(titulos)))
        lines   = ["✏️ *Títulos sugeridos para tu beat*\n", f"_Descripción: {texto}_\n"]
        buttons = []
        for i, t in enumerate(seleccionados):
            lines.append(f"{i+1}. *{t}*")
            buttons.append([InlineKeyboardButton(f"📋 {t}", callback_data=f"titulo_copy_{t[:32]}")])
        buttons.append([InlineKeyboardButton("🔄 Generar más",   callback_data="sec_titulos")])
        buttons.append([InlineKeyboardButton("‹ Menú principal", callback_data="sec_main")])
        await update.message.reply_text(
            "\n".join(lines), parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons))
        return

    # ── Battle caption ────────────────────────────────────
    if ctx.user_data.get("reg_step") == "battle_caption":
        file_id   = ctx.user_data.get("battle_file_id","")
        file_type = ctx.user_data.get("battle_file_type","audio")
        u         = update.effective_user
        name      = u.first_name or u.username or "Anónimo"
        db_add_battle(u.id, name, file_id, file_type, texto)
        ctx.user_data["mode"]     = MODE_NONE
        ctx.user_data["reg_step"] = None
        await update.message.reply_text(
            f"✅ *¡Beat en la arena!*\n\n"
            f"Nombre: *{texto}*\n"
            f"Activo durante 24 horas. ¡Consigue votos! 🔥",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 Ver el Battle", callback_data="sec_battle")],
                [InlineKeyboardButton("‹ Menú principal",          callback_data="sec_main")],
            ]))
        return

    # ── DAW valores custom ─────────────────────────────────
    if mode in (MODE_DAW_PITCH, MODE_DAW_SPEED, MODE_DAW_TEMPO):
        wav = ctx.user_data.get("wav")
        if not wav or not os.path.exists(wav):
            await update.message.reply_text("Audio no encontrado.", reply_markup=kb_main())
            ctx.user_data["mode"] = MODE_NONE
            return
        try:
            val = float(texto.replace(",",".").replace("+","").strip())
        except ValueError:
            await update.message.reply_text("⚠️ Escribe un número válido.")
            return
        if mode == MODE_DAW_PITCH:
            if not -12 <= val <= 12:
                await update.message.reply_text("⚠️ Rango: -12 a +12")
                return
            action, args = do_pitch, (wav, val)
            sign    = "▲" if val > 0 else "▼" if val < 0 else ""
            caption = f"🎵 Pitch {sign} {abs(val)} semitono(s)"
        elif mode == MODE_DAW_SPEED:
            if not 0.5 <= val <= 2.0:
                await update.message.reply_text("⚠️ Rango: 0.5 a 2.0")
                return
            action, args = do_speed, (wav, val)
            caption = f"⏩ Speed ×{val}"
        else:
            if not -50 <= val <= 100:
                await update.message.reply_text("⚠️ Rango: -50 a +100")
                return
            action, args = do_tempo, (wav, 1 + val/100)
            sign    = "▲" if val > 0 else "▼" if val < 0 else ""
            caption = f"🥁 Tempo {sign} {abs(val)}%"

        await upload_anim(update)
        status = await update.message.reply_text("⏳ Procesando…")
        try:
            result     = await asyncio.to_thread(action, *args)
            result_wav = await asyncio.to_thread(ogg_to_wav, result)
            old_wav    = ctx.user_data.get("wav")
            with open(result, "rb") as f:
                await update.message.reply_voice(voice=f, caption=f"{caption} ✅", reply_markup=kb_daw())
            os.remove(result)
            ctx.user_data["wav"]  = result_wav
            ctx.user_data["mode"] = MODE_DAW
            if old_wav and os.path.exists(old_wav) and old_wav != result_wav:
                try: os.remove(old_wav)
                except: pass
            await status.delete()
        except Exception as e:
            log.error(f"DAW custom: {e}")
            await status.edit_text(f"❌ Error: {e}")
        return

    # ── Calculadora ────────────────────────────────────────
    if mode == MODE_CALC:
        plat = ctx.user_data.get("calc_plat","Spotify")
        num  = texto.replace(",","").replace(".","").replace(" ","")
        try:
            streams = int(num)
            if streams <= 0: raise ValueError
        except ValueError:
            await update.message.reply_text("⚠️ Escribe solo el número. Ejemplo: `50000`", parse_mode="Markdown")
            return
        await typing(update)
        rate = PLATAFORMAS.get(plat, 0.003)
        usd  = round(streams * rate, 3)
        eur  = round(usd * EUR_RATE, 3)
        ctx.user_data["calc_last_streams"] = streams
        msg = await update.message.reply_text(
            f"🧮 *{plat}*\n\n🎧 Streams: `{streams:,}`\n\n💵 USD: `${usd:,.3f}`\n💶 EUR: `€{eur:,.3f}`\n\n_Escribe otro número o compara:_",
            parse_mode="Markdown", reply_markup=kb_calc_result(plat))
        return

    # ── Proyección ─────────────────────────────────────────
    if mode == MODE_PROJ:
        step = ctx.user_data.get("proj_step","streams")
        num  = texto.replace(",","").replace(" ","").replace("+","")
        if step == "streams":
            try:
                streams = int(num)
                if streams <= 0: raise ValueError
            except ValueError:
                await update.message.reply_text("⚠️ Escribe el número de streams.")
                return
            ctx.user_data["proj_streams"] = streams
            ctx.user_data["proj_step"]    = "growth"
            msg = await update.message.reply_text(
                f"📈 Streams: `{streams:,}`\n\nPaso 2 de 3 — ¿Cuánto % creces al mes?\nEjemplo: `20`",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="sec_calc")]]))
            return
        if step == "growth":
            try:
                growth = float(num)
                if growth < 0: raise ValueError
            except ValueError:
                await update.message.reply_text("⚠️ Escribe el % de crecimiento.")
                return
            ctx.user_data["proj_growth"] = growth
            ctx.user_data["proj_step"]   = "platform"
            msg = await update.message.reply_text(
                f"📈 Crecimiento: `{growth}%`\n\nPaso 3 de 3 — Selecciona la plataforma:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Spotify",    callback_data="proj_plat_Spotify"),
                     InlineKeyboardButton("Apple Music",callback_data="proj_plat_Apple Music")],
                    [InlineKeyboardButton("Tidal",      callback_data="proj_plat_Tidal"),
                     InlineKeyboardButton("YouTube",    callback_data="proj_plat_YouTube Premium")],
                    [InlineKeyboardButton("Audiomack",  callback_data="proj_plat_Audiomack"),
                     InlineKeyboardButton("TikTok",     callback_data="proj_plat_TikTok")],
                    [InlineKeyboardButton("❌ Cancelar", callback_data="sec_calc")],
                ]))
            return

    # ── Registro ───────────────────────────────────────────
    if mode == MODE_REG:
        step = ctx.user_data.get("reg_step","name")
        if step == "name":
            ctx.user_data["reg_name"] = texto
            ctx.user_data["reg_step"] = "genre"
            await update.message.reply_text(
                "✏️ *Registro — Paso 2 de 4*\n\nElige tu género:", parse_mode="Markdown", reply_markup=kb_genres())
        elif step == "bio":
            ctx.user_data["reg_bio"] = texto
            ctx.user_data["reg_step"] = "ig"
            await update.message.reply_text(
                "✏️ *Registro — Paso 4 de 4*\n\nInstagram (sin @) o escribe `skip`:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Omitir", callback_data="reg_skip_ig")]]))
        elif step == "ig":
            ig = "" if texto.lower() == "skip" else texto.replace("@","").strip()
            u  = update.effective_user
            db_register(u.id, u.username, ctx.user_data["reg_name"],
                        ctx.user_data["reg_genre"], ctx.user_data.get("reg_bio",""), ig)
            ctx.user_data["mode"] = MODE_NONE
            await update.message.reply_text(
                f"✅ *¡Registro completado!*\n\nBienvenido, *{ctx.user_data['reg_name']}* 🎤",
                parse_mode="Markdown", reply_markup=kb_artists_main())
        return

    # ── Showcase caption ───────────────────────────────────
    if ctx.user_data.get("reg_step") == "show_caption":
        file_id   = ctx.user_data.get("show_file_id","")
        file_type = ctx.user_data.get("show_file_type","audio")
        db_add_post(update.effective_user.id, "showcase", file_id=file_id, caption=texto, file_type=file_type)
        ctx.user_data["mode"]     = MODE_NONE
        ctx.user_data["reg_step"] = None
        await update.message.reply_text("🎵 *Showcase publicado!*", parse_mode="Markdown", reply_markup=kb_artists_main())
        return

    # ── Ideas ──────────────────────────────────────────────
    if mode == MODE_IDEA:
        db_add_post(update.effective_user.id, "idea", content=texto)
        ctx.user_data["mode"] = MODE_NONE
        await update.message.reply_text("💡 *Idea publicada!*", parse_mode="Markdown", reply_markup=kb_artists_main())
        return

    # ── Feedback ───────────────────────────────────────────
    if mode == MODE_FB:
        post_id = ctx.user_data.get("fb_post_id")
        if post_id:
            u = update.effective_user
            db_add_feedback(post_id, u.id, u.first_name or "Anónimo", texto)
        ctx.user_data["mode"] = MODE_NONE
        await update.message.reply_text("💬 *Feedback enviado!*", parse_mode="Markdown", reply_markup=kb_artists_main())
        return

    # ── Búsqueda ───────────────────────────────────────────
    if mode == MODE_SEARCH:
        await typing(update)
        status = await update.message.reply_text("🔍 Buscando…")
        try:
            results = await asyncio.to_thread(itunes_search, texto)
            if not results:
                await status.edit_text("No encontré resultados.")
                return
            ctx.user_data["search_results"] = {str(i): t for i, t in enumerate(results)}
            buttons = []
            lines   = [f"🔍 *{texto}*\n"]
            for i, t in enumerate(results):
                name   = t.get("trackName","N/A")[:30]
                artist = t.get("artistName","N/A")[:20]
                lines.append(f"{i+1}. {name} — {artist}")
                buttons.append([InlineKeyboardButton(f"{i+1}. {name[:22]} — {artist[:12]}", callback_data=f"it_track_{i}")])
            buttons.append([InlineKeyboardButton("🔍 Buscar otra", callback_data="sec_spotify")])
            buttons.append([InlineKeyboardButton("‹ Menú principal",             callback_data="sec_main")])
            await status.edit_text("\n".join(lines) + "\n\nSelecciona una canción:",
                parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        except Exception as e:
            log.error(f"Search: {e}")
            await status.edit_text("❌ Error en la búsqueda.")
        return

    await update.message.reply_text("Usa el menú para navegar 👇", reply_markup=kb_main())

# ══════════════════════════════════════════════════════════
#  AUDIO
# ══════════════════════════════════════════════════════════

async def on_audio(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    mode = ctx.user_data.get("mode", MODE_NONE)
    msg  = update.message
    fobj = msg.audio or msg.voice or msg.document

    # ── Reto semanal ───────────────────────────────────────
    if mode == MODE_RETO:
        status = await msg.reply_text("⏳ Subiendo tu participación…")
        raw    = os.path.join(TMP, uuid.uuid4().hex + ".bin")
        tg_file = await fobj.get_file()
        await tg_file.download_to_drive(raw)
        try:
            if msg.voice:
                sent = await msg.reply_voice(voice=msg.voice.file_id, caption="🏆 Participación recibida")
                file_id, ftype = sent.voice.file_id, "voice"
            elif msg.audio:
                sent = await msg.reply_audio(audio=msg.audio.file_id, caption="🏆 Participación recibida")
                file_id, ftype = sent.audio.file_id, "audio"
            else:
                with open(raw, "rb") as f:
                    sent = await msg.reply_audio(audio=f, caption="🏆 Participación recibida")
                file_id, ftype = sent.audio.file_id, "audio"
            u       = msg.from_user
            name    = u.first_name or u.username or "Anónimo"
            week_id = get_week_id()
            eid     = db_add_reto_entry(u.id, name, file_id, ftype, week_id)
            if eid is None:
                await status.edit_text(
                    "⚠️ Ya participaste esta semana.\nVuelve el próximo lunes!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🏆 Ver reto", callback_data="sec_reto")
                    ]]))
            else:
                reto = get_current_reto()
                ctx.user_data["mode"] = MODE_NONE
                await status.edit_text(
                    f"✅ *¡Participación enviada!*\n\n"
                    f"🏆 *{reto['titulo']}*\n\n"
                    f"La comunidad puede votar tu audio 🔥",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📋 Ver participantes", callback_data="reto_feed")],
                        [InlineKeyboardButton("← Menú", callback_data="sec_main")],
                    ]))
        except Exception as e:
            log.error(f"Reto: {e}")
            await status.edit_text(f"❌ Error: {e}")
        finally:
            if os.path.exists(raw): os.remove(raw)
        return

    if mode == MODE_BATTLE:
        status = await msg.reply_text("⏳ Recibiendo tu beat…")
        raw    = os.path.join(TMP, uuid.uuid4().hex + ".bin")
        tg     = await fobj.get_file()
        await tg.download_to_drive(raw)
        try:
            if msg.voice:
                sent = await msg.reply_voice(voice=msg.voice.file_id, caption="🎵 Beat recibido")
                file_id, ftype = sent.voice.file_id, "voice"
            elif msg.audio:
                sent = await msg.reply_audio(audio=msg.audio.file_id, caption="🎵 Beat recibido")
                file_id, ftype = sent.audio.file_id, "audio"
            else:
                with open(raw, "rb") as f:
                    sent = await msg.reply_audio(audio=f, caption="🎵 Beat recibido")
                file_id, ftype = sent.audio.file_id, "audio"

            ctx.user_data["battle_file_id"]   = file_id
            ctx.user_data["battle_file_type"]  = ftype
            ctx.user_data["reg_step"]          = "battle_caption"
            await status.edit_text(
                "✅ Beat recibido\n\n¿Cómo se llama tu beat? Escribe el nombre o toca Omitir:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Omitir", callback_data="battle_no_cap")
                ]]))
        except Exception as e:
            log.error(f"Battle upload: {e}")
            await status.edit_text(f"❌ Error: {e}")
        finally:
            if os.path.exists(raw): os.remove(raw)
        return

    if mode not in (MODE_DAW, MODE_ANLZ, MODE_SHOW, MODE_IDEA, MODE_BATTLE, MODE_RETO):
        await msg.reply_text(
            "¿Quieres editarlo? → 🎛️ Mini DAW\n¿Quieres analizarlo? → 📊 Analizador\n\nElige desde el menú 👇",
            reply_markup=kb_main())
        return

    # ── Showcase ───────────────────────────────────────────
    if mode == MODE_SHOW:
        status = await msg.reply_text("⏳ Recibiendo audio…")
        raw    = os.path.join(TMP, uuid.uuid4().hex + ".bin")
        tg     = await fobj.get_file()
        await tg.download_to_drive(raw)
        try:
            if msg.voice:
                sent = await msg.reply_voice(voice=msg.voice.file_id, caption="🎵 Preview")
                file_id, ftype = sent.voice.file_id, "voice"
            elif msg.audio:
                sent = await msg.reply_audio(audio=msg.audio.file_id, caption="🎵 Preview")
                file_id, ftype = sent.audio.file_id, "audio"
            else:
                with open(raw, "rb") as f:
                    sent = await msg.reply_audio(audio=f, caption="🎵 Preview")
                file_id, ftype = sent.audio.file_id, "audio"
            ctx.user_data["show_file_id"]   = file_id
            ctx.user_data["show_file_type"] = ftype
            ctx.user_data["reg_step"]       = "show_caption"
            await status.edit_text(
                "✅ Audio recibido\n\n¿Añadir descripción? Escríbela o toca Omitir:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Omitir", callback_data="show_no_cap")]]))
        except Exception as e:
            log.error(f"Showcase: {e}")
            await status.edit_text(f"❌ Error: {e}")
        finally:
            if os.path.exists(raw): os.remove(raw)
        return

    # ── Idea con audio ─────────────────────────────────────
    if mode == MODE_IDEA:
        raw = os.path.join(TMP, uuid.uuid4().hex + ".bin")
        tg  = await fobj.get_file()
        await tg.download_to_drive(raw)
        try:
            if msg.voice:
                sent = await msg.reply_voice(voice=msg.voice.file_id, caption="💡 Idea")
                db_add_post(update.effective_user.id, "idea", file_id=sent.voice.file_id, file_type="voice", caption="Idea")
            elif msg.audio:
                sent = await msg.reply_audio(audio=msg.audio.file_id, caption="💡 Idea")
                db_add_post(update.effective_user.id, "idea", file_id=sent.audio.file_id, file_type="audio", caption="Idea")
            ctx.user_data["mode"] = MODE_NONE
            await msg.reply_text("💡 *Idea publicada!*", parse_mode="Markdown", reply_markup=kb_artists_main())
        finally:
            if os.path.exists(raw): os.remove(raw)
        return

    # ── DAW / Analizador ───────────────────────────────────
    status = await msg.reply_text("⏳ Recibiendo audio…")
    raw    = os.path.join(TMP, uuid.uuid4().hex + ".bin")
    tg     = await fobj.get_file()
    await tg.download_to_drive(raw)

    try:
        wav = await asyncio.to_thread(to_wav, raw)
    except Exception as e:
        log.error(f"to_wav: {e}")
        await status.edit_text("❌ No pude leer ese archivo. Prueba con MP3 u OGG.")
        return
    finally:
        if os.path.exists(raw): os.remove(raw)

    if mode == MODE_DAW:
        ctx.user_data["wav"] = wav
        await status.edit_text("✅ Audio cargado")
        await msg.reply_text("🎛️ ¿Qué quieres hacer?", reply_markup=kb_daw())
        return

    if mode == MODE_ANLZ:
        await status.edit_text("🔍 Analizando…")
        try:
            info = await asyncio.to_thread(analyze_audio, wav)
            ctx.user_data["wav"]  = wav
            ctx.user_data["mode"] = MODE_DAW
            await status.edit_text("✅ Análisis completado")
            await msg.reply_text(
                f"📊 *Análisis de Audio*\n\n"
                f"⏱️ `{info['duration']}s` · 🥁 `{info['bpm']} BPM` · 🎼 `{info['key']}` · 🔊 `{info['dbfs']} dBFS`\n\n"
                f"_Audio listo para editar 🎛️_",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎛️ Editar en DAW",  callback_data="sec_daw")],
                    [InlineKeyboardButton("📊 Analizar otro",  callback_data="sec_analyze")],
                    [InlineKeyboardButton("‹ Menú principal",  callback_data="sec_main")],
                ]))
        except Exception as e:
            log.error(f"analyze: {e}")
            await status.edit_text("❌ Error analizando. Intenta con otro archivo.")

# ══════════════════════════════════════════════════════════
#  PAGOS
# ══════════════════════════════════════════════════════════

async def on_pre_checkout(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def on_payment(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    payload = update.message.successful_payment.invoice_payload
    tg_id   = update.effective_user.id
    if payload == "sub_pro":
        db_set_plan(tg_id, PLAN_PRO, months=1)
        plan_name = "⭐ Pro"
    elif payload == "sub_studio":
        db_set_plan(tg_id, PLAN_STUDIO, months=1)
        plan_name = "🎛️ Studio"
    else:
        return
    log.info(f"Pago: {tg_id} → {payload}")
    await update.message.reply_text(
        f"✅ *¡Plan {plan_name} activado!*\n\nTienes acceso completo durante 30 días 🎛️",
        parse_mode="Markdown", reply_markup=kb_main())

# ══════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════

def main():
    db_init()
    app = (ApplicationBuilder()
           .token(TOKEN)
           .connect_timeout(30)
           .read_timeout(60)
           .write_timeout(60)
           .build())

    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("menu",   cmd_start))
    app.add_handler(CommandHandler("planes", cmd_planes))
    app.add_handler(CommandHandler("mipan",  cmd_mipan))
    app.add_handler(CommandHandler("admin",  cmd_admin))
    app.add_handler(PreCheckoutQueryHandler(on_pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, on_payment))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.AUDIO | filters.VOICE | filters.Document.AUDIO, on_audio))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    log.info("✅ Mkeyz Studio Bot listo")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
