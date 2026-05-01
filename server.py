# -*- coding: utf-8 -*-
"""
Mkeyz Studio - Game Server (Flask)
Corre en paralelo con el bot en Railway
"""
from flask import Flask, jsonify, request, send_from_directory
import sqlite3, os, time, logging

logging.basicConfig(level=logging.WARNING)  # Reduce log noise

app = Flask(__name__, static_folder="static")
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 3600  # Cache static files 1 hour


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mkeyz.db")

def get_db():
    con = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")   # Faster concurrent reads
    con.execute("PRAGMA synchronous=NORMAL") # Faster writes
    return con

# ── API endpoints ──────────────────────────────────────────

@app.route("/api/battles/active")
def active_battles():
    con = get_db()
    cur = con.cursor()
    cur.execute("""
        SELECT id, name, file_id, caption, votes_fire, votes_skip,
               expires_at, submitted_at
        FROM battles WHERE expires_at > ?
        ORDER BY submitted_at DESC LIMIT 20
    """, (int(time.time()),))
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    return jsonify(rows)

@app.route("/api/battles/top")
def top_battles():
    con = get_db()
    cur = con.cursor()
    cur.execute("""
        SELECT id, name, caption, votes_fire, votes_skip,
               (votes_fire - votes_skip) as score
        FROM battles
        ORDER BY score DESC LIMIT 20
    """)
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    return jsonify(rows)

@app.route("/api/battles/vote", methods=["POST"])
def vote():
    data      = request.json or {}
    battle_id = data.get("battle_id")
    voter_id  = str(data.get("voter_id", ""))
    vote      = data.get("vote")  # "fire" or "skip"

    if not all([battle_id, voter_id, vote in ("fire","skip")]):
        return jsonify({"ok": False, "error": "invalid params"}), 400

    con = get_db()
    cur = con.cursor()

    # Check already voted
    cur.execute("SELECT 1 FROM battle_votes WHERE battle_id=? AND voter_tg_id=?",
                (battle_id, voter_id))
    if cur.fetchone():
        cur.execute("SELECT votes_fire, votes_skip FROM battles WHERE id=?", (battle_id,))
        row = cur.fetchone()
        con.close()
        return jsonify({"ok": False, "already_voted": True,
                        "votes_fire": row["votes_fire"], "votes_skip": row["votes_skip"]})

    # Register vote
    try:
        cur.execute("INSERT INTO battle_votes (battle_id, voter_tg_id, vote) VALUES (?,?,?)",
                    (battle_id, voter_id, vote))
        if vote == "fire":
            cur.execute("UPDATE battles SET votes_fire = votes_fire + 1 WHERE id=?", (battle_id,))
        else:
            cur.execute("UPDATE battles SET votes_skip = votes_skip + 1 WHERE id=?", (battle_id,))
        con.commit()
    except Exception as e:
        con.close()
        return jsonify({"ok": False, "error": str(e)}), 500

    cur.execute("SELECT votes_fire, votes_skip FROM battles WHERE id=?", (battle_id,))
    row = cur.fetchone()
    con.close()
    return jsonify({"ok": True, "votes_fire": row["votes_fire"], "votes_skip": row["votes_skip"]})

@app.route("/api/battles/submit", methods=["POST"])
def submit_battle():
    data      = request.json or {}
    tg_id     = data.get("tg_id")
    name      = data.get("name", "Anónimo")
    file_id   = data.get("file_id")
    file_type = data.get("file_type", "audio")
    caption   = data.get("caption", "Mi beat")

    if not all([tg_id, file_id]):
        return jsonify({"ok": False, "error": "missing params"}), 400

    con = get_db()
    cur = con.cursor()
    now = int(time.time())
    cur.execute("""
        INSERT INTO battles (tg_id,name,file_id,file_type,caption,submitted_at,expires_at)
        VALUES (?,?,?,?,?,?,?)
    """, (tg_id, name, file_id, file_type, caption, now, now + 86400))
    bid = cur.lastrowid
    con.commit()
    con.close()
    return jsonify({"ok": True, "battle_id": bid})

# ── Serve game ─────────────────────────────────────────────

# ── BPM Game API ──────────────────────────────────────────

@app.route("/api/bpm/score", methods=["POST"])
def bpm_score():
    data    = request.json or {}
    user_id = str(data.get("user_id",""))
    name    = str(data.get("name","Anónimo"))[:30]
    score   = int(data.get("score", 0))
    if not user_id: return jsonify({"ok":False}), 400
    con = get_db()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bpm_scores (
            user_id TEXT PRIMARY KEY,
            name    TEXT,
            score   INTEGER,
            updated_at INTEGER
        )""")
    cur.execute("""
        INSERT INTO bpm_scores (user_id,name,score,updated_at) VALUES (?,?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET
          name=excluded.name,
          score=MAX(score, excluded.score),
          updated_at=excluded.updated_at
    """, (user_id, name, score, int(time.time())))
    con.commit()
    con.close()
    return jsonify({"ok":True})

@app.route("/api/bpm/leaderboard")
def bpm_leaderboard():
    con = get_db()
    cur = con.cursor()
    try:
        cur.execute("SELECT name, score FROM bpm_scores ORDER BY score DESC LIMIT 10")
        rows = [dict(r) for r in cur.fetchall()]
    except:
        rows = []
    con.close()
    return jsonify(rows)

@app.route("/")
@app.route("/game")
def serve_game():
    return send_from_directory("static", "index.html")

@app.route("/bpm")
def serve_bpm():
    return send_from_directory("static", "bpm_game.html")

@app.route("/simulator")
def serve_simulator():
    return send_from_directory("static", "stream_sim.html")

@app.route("/scale")
def serve_scale():
    return send_from_directory("static", "scale_detector.html")

@app.route("/freq")
def serve_freq():
    return send_from_directory("static", "freq_visualizer.html")

@app.route("/compare")
def serve_compare():
    return send_from_directory("static", "artist_compare.html")

@app.route("/card")
def serve_card():
    return send_from_directory("static", "artist_card.html")

@app.route("/chords")
def serve_chords():
    return send_from_directory("static", "chord_gen.html")

@app.route("/voice")
def serve_voice():
    return send_from_directory("static", "voice_studio.html")

@app.route("/qr")
def serve_qr():
    return send_from_directory("static", "qr.html")

@app.route("/showcase")
def serve_showcase():
    return send_from_directory("static", "showcase.html")

@app.route("/intro")
def serve_intro():
    return send_from_directory("static", "intro.html")

@app.route("/playlist")
def serve_playlist():
    return send_from_directory("static", "playlist_gen.html")

@app.route("/game2")
def serve_game2():
    return send_from_directory("static", "studio_game.html")

@app.route("/about")
def serve_about():
    return send_from_directory("static", "about.html")

@app.route("/views")
def serve_views():
    return send_from_directory("static", "views_tracker.html")

# ── Views Tracker — persistencia por usuario ───────────────

def _ensure_views_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS views_tracker (
            tg_id      INTEGER PRIMARY KEY,
            entries    TEXT    DEFAULT '[]',
            songs      TEXT    DEFAULT '[]',
            payments   TEXT    DEFAULT '[]',
            updated_at INTEGER DEFAULT 0
        )
    """)

@app.route("/api/views/load")
def views_load():
    tg_id = request.args.get("tg_id")
    if not tg_id:
        return jsonify({"ok": False, "error": "no tg_id"}), 400
    con = get_db()
    cur = con.cursor()
    _ensure_views_table(cur)
    con.commit()
    cur.execute("SELECT entries, songs, payments FROM views_tracker WHERE tg_id=?", (int(tg_id),))
    row = cur.fetchone()
    con.close()
    if row:
        return jsonify({"ok": True, "entries": row["entries"], "songs": row["songs"], "payments": row["payments"]})
    return jsonify({"ok": True, "entries": "[]", "songs": "[]", "payments": "[]"})

@app.route("/api/views/save", methods=["POST"])
def views_save():
    data  = request.json or {}
    tg_id = data.get("tg_id")
    if not tg_id:
        return jsonify({"ok": False, "error": "no tg_id"}), 400
    entries  = data.get("entries",  "[]")
    songs    = data.get("songs",    "[]")
    payments = data.get("payments", "[]")
    con = get_db()
    cur = con.cursor()
    _ensure_views_table(cur)
    cur.execute("""
        INSERT INTO views_tracker (tg_id, entries, songs, payments, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(tg_id) DO UPDATE SET
            entries    = excluded.entries,
            songs      = excluded.songs,
            payments   = excluded.payments,
            updated_at = excluded.updated_at
    """, (int(tg_id), entries, songs, payments, int(time.time())))
    con.commit()
    con.close()
    return jsonify({"ok": True})

# ── MKEYZ Token Economy ────────────────────────────────────────
TOTAL_SUPPLY = 21_000_000  # Like Bitcoin — fixed supply

@app.route("/api/mkeyz/supply")
def mkeyz_supply():
    """Returns global mining stats."""
    con = get_db()
    cur = con.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mkeyz_rewards (
                tg_id      INTEGER NOT NULL,
                action     TEXT NOT NULL,
                amount     INTEGER NOT NULL,
                claimed    INTEGER DEFAULT 0,
                created_at INTEGER NOT NULL
            )""")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mkeyz_game (
                tg_id      INTEGER PRIMARY KEY,
                total_mined INTEGER DEFAULT 0,
                updated_at  INTEGER
            )""")
        con.commit()
        cur.execute("SELECT COALESCE(SUM(total_mined),0) FROM mkeyz_game")
        total = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(DISTINCT tg_id) FROM mkeyz_game WHERE total_mined > 0")
        miners = cur.fetchone()[0] or 0
    except Exception as e:
        total, miners = 0, 0
    con.close()
    return jsonify({
        "total_supply": TOTAL_SUPPLY,
        "total_mined":  int(total),
        "remaining":    TOTAL_SUPPLY - int(total),
        "miners":       int(miners),
        "pct_mined":    round(int(total) / TOTAL_SUPPLY * 100, 4)
    })

@app.route("/api/mkeyz/rewards")
def get_rewards():
    """Get pending rewards for a user."""
    tg_id = request.args.get("tg_id")
    if not tg_id: return jsonify([])
    con = get_db()
    cur = con.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mkeyz_rewards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER NOT NULL, action TEXT NOT NULL,
                amount INTEGER NOT NULL, claimed INTEGER DEFAULT 0,
                created_at INTEGER NOT NULL)""")
        cur.execute("SELECT id, action, amount FROM mkeyz_rewards WHERE tg_id=? AND claimed=0",
                    (int(tg_id),))
        rows = [{"id":r[0],"action":r[1],"amount":r[2]} for r in cur.fetchall()]
    except: rows = []
    con.close()
    return jsonify(rows)

@app.route("/api/mkeyz/claim", methods=["POST"])
def claim_rewards():
    """Mark rewards as claimed and update mined total."""
    data  = request.json or {}
    tg_id = data.get("tg_id")
    ids   = data.get("ids", [])
    total = data.get("total_claimed", 0)
    if not tg_id: return jsonify({"ok":False})
    con = get_db()
    cur = con.cursor()
    try:
        for rid in ids:
            cur.execute("UPDATE mkeyz_rewards SET claimed=1 WHERE id=?", (rid,))
        cur.execute("""
            INSERT INTO mkeyz_game (tg_id, total_mined, updated_at)
            VALUES (?,?,?) ON CONFLICT(tg_id) DO UPDATE SET
            total_mined=total_mined+excluded.total_mined, updated_at=excluded.updated_at
        """, (int(tg_id), int(total), int(time.time())))
        con.commit()
    except Exception as e:
        con.close()
        return jsonify({"ok":False,"error":str(e)})
    con.close()
    return jsonify({"ok":True})

@app.route("/api/mkeyz/award", methods=["POST"])
def award_coins():
    """Award coins to a user for using a bot tool."""
    data   = request.json or {}
    tg_id  = data.get("tg_id")
    action = data.get("action","")
    amount = data.get("amount", 0)
    if not all([tg_id, action, amount]): return jsonify({"ok":False})
    con = get_db()
    cur = con.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mkeyz_rewards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER NOT NULL, action TEXT NOT NULL,
                amount INTEGER NOT NULL, claimed INTEGER DEFAULT 0,
                created_at INTEGER NOT NULL)""")
        # Check if already awarded this action today
        today = int(time.time()) - 86400
        cur.execute("SELECT COUNT(*) FROM mkeyz_rewards WHERE tg_id=? AND action=? AND created_at>?",
                    (int(tg_id), action, today))
        if cur.fetchone()[0] > 0:
            con.close()
            return jsonify({"ok":False, "reason":"already_awarded_today"})
        cur.execute("INSERT INTO mkeyz_rewards (tg_id,action,amount,created_at) VALUES (?,?,?,?)",
                    (int(tg_id), action, int(amount), int(time.time())))
        con.commit()
    except Exception as e:
        con.close()
        return jsonify({"ok":False,"error":str(e)})
    con.close()
    return jsonify({"ok":True, "awarded":amount})

@app.route("/api/artist/profile")
def api_artist_profile():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "no user_id"}), 400
    con = get_db()
    cur = con.cursor()
    try:
        cur.execute("SELECT name, genre, bio, ig FROM artists WHERE tg_id=?", (int(user_id),))
        row = cur.fetchone()
        con.close()
        if row:
            return jsonify({"name": row["name"], "genre": row["genre"], "bio": row["bio"], "ig": row["ig"]})
        return jsonify({}), 404
    except Exception as e:
        con.close()
        return jsonify({"error": str(e)}), 500

# ── VPS Simulator ─────────────────────────────────────────────────────────────
# Pega este bloque al final de server.py, antes del if __name__ == "__main__"
# ──────────────────────────────────────────────────────────────────────────────

import json, random, uuid as _uuid, os

PROFILE_NAMES = [
    "Shadow Fox","Neon Wolf","Ghost Hawk","Cyber Bear","Phantom Cat",
    "Iron Lynx","Dark Eagle","Stealth Owl","Rogue Tiger","Silent Viper",
    "Black Mamba","Storm Raven","Void Shark","Apex Cobra","Digital Puma",
    "Chrome Falcon","Onyx Drake","Lunar Panther","Obsidian Kite","Nova Hound"
]
BROWSERS  = ["Chrome 120","Chrome 119","Firefox 121","Edge 120"]
OS_LIST   = ["Windows 11","Windows 10","macOS 14","Ubuntu 22.04"]
STATUSES  = ["idle","active","active","warming"]
PROFILE_COST = {"cpu": 0.5, "ram": 512, "storage": 2}

# ── Platform profiles ─────────────────────────────────────
PLATFORMS = {
    "youtube": {
        "name": "YouTube", "icon": "▶️",
        "cpu": 0.6, "ram": 700, "storage": 2, "bandwidth_gb": 15,
        "proxy": "Residencial EU/US", "proxy_type": "res",
        "geo": "Global", "risk": "bajo",
        "browser": "Chrome 120", "os": "Windows 11",
        "note": "Alta resolución — necesita proxy rápido"
    },
    "spotify": {
        "name": "Spotify", "icon": "🎵",
        "cpu": 0.3, "ram": 300, "storage": 2, "bandwidth_gb": 3,
        "proxy": "Datacenter EU", "proxy_type": "dc",
        "geo": "Global", "risk": "bajo",
        "browser": "Chrome 120", "os": "Windows 10",
        "note": "Bajo consumo — ideal para múltiples perfiles"
    },
    "apple_music": {
        "name": "Apple Music", "icon": "🍎",
        "cpu": 0.3, "ram": 350, "storage": 2, "bandwidth_gb": 4,
        "proxy": "Datacenter US/EU", "proxy_type": "dc",
        "geo": "Global", "risk": "bajo",
        "browser": "Safari 17", "os": "macOS 14",
        "note": "Mejor rendimiento con macOS + Safari"
    },
    "tidal": {
        "name": "Tidal", "icon": "🌊",
        "cpu": 0.4, "ram": 400, "storage": 3, "bandwidth_gb": 20,
        "proxy": "Residencial EU/US", "proxy_type": "res",
        "geo": "Global", "risk": "medio",
        "browser": "Chrome 120", "os": "Windows 11",
        "note": "HiFi/Lossless — alto consumo de banda"
    },
    "pandora": {
        "name": "Pandora", "icon": "📻",
        "cpu": 0.3, "ram": 300, "storage": 2, "bandwidth_gb": 5,
        "proxy": "Residencial US obligatorio", "proxy_type": "mob",
        "geo": "US only", "risk": "alto",
        "browser": "Chrome 120", "os": "Windows 10",
        "note": "Geo-restringido US — proxy americano obligatorio"
    },
    "general": {
        "name": "General", "icon": "🖥️",
        "cpu": 0.5, "ram": 512, "storage": 2, "bandwidth_gb": 8,
        "proxy": "Cualquiera", "proxy_type": "dc",
        "geo": "Global", "risk": "bajo",
        "browser": "Chrome 120", "os": "Windows 11",
        "note": "Configuración estándar multipropósito"
    }
}

def _is_authorized(tg_id):
    allowed = os.environ.get("VIP_IDS", "")
    ids = [x.strip() for x in allowed.replace(",", " ").split() if x.strip()]
    return str(tg_id) in ids

def _ensure_vps_tables(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vps_state (
            tg_id      INTEGER PRIMARY KEY,
            cpu        REAL    DEFAULT 1,
            ram        INTEGER DEFAULT 1024,
            storage    INTEGER DEFAULT 20,
            bandwidth  INTEGER DEFAULT 1,
            vps_name   TEXT    DEFAULT 'VPS-SIM-01',
            updated_at INTEGER DEFAULT 0
        )""")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vps_profiles (
            id          TEXT    PRIMARY KEY,
            tg_id       INTEGER NOT NULL,
            name        TEXT,
            browser     TEXT,
            os          TEXT,
            proxy       TEXT,
            status      TEXT    DEFAULT 'idle',
            fingerprint TEXT,
            platform    TEXT    DEFAULT 'general',
            last_activity INTEGER,
            created_at  INTEGER
        )""")
    # Migrate: add platform column if missing
    try:
        cur.execute("ALTER TABLE vps_profiles ADD COLUMN platform TEXT DEFAULT 'general'")
    except Exception:
        pass

def _compute_capacity(cpu, ram, storage, profiles=None):
    # Use actual platform costs if profiles provided, else default
    if profiles:
        used_cpu = sum(PLATFORMS.get(p.get("platform","general"), PLATFORMS["general"])["cpu"] for p in profiles if p.get("status") != "idle")
        used_ram = sum(PLATFORMS.get(p.get("platform","general"), PLATFORMS["general"])["ram"] for p in profiles)
        used_storage = sum(PLATFORMS.get(p.get("platform","general"), PLATFORMS["general"])["storage"] for p in profiles)
    else:
        used_cpu = used_ram = used_storage = 0

    by_cpu     = int(cpu / PROFILE_COST["cpu"])
    by_ram     = int(ram / PROFILE_COST["ram"])
    by_storage = int(storage / PROFILE_COST["storage"])
    max_p = min(by_cpu, by_ram, by_storage)
    bottleneck = min(
        [("cpu", by_cpu), ("ram", by_ram), ("storage", by_storage)],
        key=lambda x: x[1]
    )[0]
    return {
        "maxProfiles": max_p,
        "limits": {"byCPU": by_cpu, "byRAM": by_ram, "byStorage": by_storage},
        "bottleneck": bottleneck
    }

def _usage(cpu, ram, storage, profiles):
    active = [p for p in profiles if p.get("status") != "idle"]
    total  = profiles
    used_cpu     = sum(PLATFORMS.get(p.get("platform","general"), PLATFORMS["general"])["cpu"] for p in active)
    used_ram     = sum(PLATFORMS.get(p.get("platform","general"), PLATFORMS["general"])["ram"] for p in total)
    used_storage = sum(PLATFORMS.get(p.get("platform","general"), PLATFORMS["general"])["storage"] for p in total)
    used_bw      = sum(PLATFORMS.get(p.get("platform","general"), PLATFORMS["general"])["bandwidth_gb"] for p in total)
    return {
        "cpu":       min(100, round(used_cpu / cpu * 100)) if cpu > 0 else 0,
        "ram":       min(100, round(used_ram / ram * 100)) if ram > 0 else 0,
        "storage":   min(100, round(used_storage / storage * 100)) if storage > 0 else 0,
        "bandwidth_gb": round(used_bw, 1)
    }

def _gen_profile(tg_id, index):
    now = int(time.time())
    return {
        "id":            str(_uuid.uuid4()),
        "tg_id":         tg_id,
        "name":          f"{PROFILE_NAMES[index % len(PROFILE_NAMES)]} #{index+1}",
        "browser":       random.choice(BROWSERS),
        "os":            random.choice(OS_LIST),
        "proxy":         f"{random.randint(10,200)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
        "status":        random.choice(STATUSES),
        "fingerprint":   _uuid.uuid4().hex[:16].upper(),
        "last_activity": now - random.randint(0, 86400),
        "created_at":    now
    }

def _get_vps(cur, tg_id):
    cur.execute("SELECT * FROM vps_state WHERE tg_id=?", (tg_id,))
    row = cur.fetchone()
    if not row:
        cur.execute("""INSERT INTO vps_state (tg_id, updated_at) VALUES (?,?)""",
                    (tg_id, int(time.time())))
        return {"cpu":1,"ram":1024,"storage":20,"bandwidth":1,"vps_name":"VPS-MKEYZ-01"}
    return dict(row)

def _get_profiles(cur, tg_id):
    cur.execute("SELECT * FROM vps_profiles WHERE tg_id=? ORDER BY created_at", (tg_id,))
    return [dict(r) for r in cur.fetchall()]

def _fill_profiles(cur, tg_id, current_count, max_profiles):
    """Create profiles up to max_profiles if slots are available."""
    for i in range(current_count, max_profiles):
        p = _gen_profile(tg_id, i)
        cur.execute("""
            INSERT INTO vps_profiles (id,tg_id,name,browser,os,proxy,status,fingerprint,last_activity,created_at)
            VALUES (:id,:tg_id,:name,:browser,:os,:proxy,:status,:fingerprint,:last_activity,:created_at)
        """, p)

def _vps_response(cur, tg_id):
    vps      = _get_vps(cur, tg_id)
    profiles = _get_profiles(cur, tg_id)
    capacity = _compute_capacity(vps["cpu"], vps["ram"], vps["storage"], profiles)
    usage    = _usage(vps["cpu"], vps["ram"], vps["storage"], profiles)
    return {
        "name":      vps["vps_name"],
        "region":    "EU-WEST (Madrid)",
        "os":        "Ubuntu 22.04 LTS",
        "resources": {"cpu": vps["cpu"], "ram": vps["ram"], "storage": vps["storage"], "bandwidth": vps["bandwidth"]},
        "profiles":  profiles,
        "capacity":  capacity,
        "usage":     usage,
        "platforms": PLATFORMS
    }

# ── Serve page ─────────────────────────────────────────────
@app.route("/vps")
def serve_vps():
    return send_from_directory("static", "vps_simulator.html")

# ── GET /api/vps?tg_id=xxx ────────────────────────────────
@app.route("/api/vps")
def api_vps_get():
    tg_id = request.args.get("tg_id")
    if not tg_id:
        return jsonify({"error": "no tg_id"}), 400
    tg_id = int(tg_id)
    con = get_db(); cur = con.cursor()
    _ensure_vps_tables(cur); con.commit()
    data = _vps_response(cur, tg_id)
    con.close()
    return jsonify(data)

# ── POST /api/vps/upgrade ─────────────────────────────────
@app.route("/api/vps/upgrade", methods=["POST"])
def api_vps_upgrade():
    data   = request.json or {}
    tg_id  = data.get("tg_id")
    rtype  = data.get("type")   # cpu, ram, storage, bandwidth
    amount = data.get("amount", 0)
    if not all([tg_id, rtype, amount]):
        return jsonify({"error": "missing params"}), 400
    tg_id = int(tg_id)
    LIMITS = {"cpu":32,"ram":65536,"storage":2000,"bandwidth":100}
    MINS   = {"cpu":1, "ram":512, "storage":10,   "bandwidth":1}
    if rtype not in LIMITS:
        return jsonify({"error": "unknown type"}), 400

    con = get_db(); cur = con.cursor()
    _ensure_vps_tables(cur); con.commit()
    vps = _get_vps(cur, tg_id)

    new_val = min(LIMITS[rtype], vps[rtype] + float(amount) if rtype == "cpu" else vps[rtype] + int(amount))
    cur.execute(f"UPDATE vps_state SET {rtype}=?, updated_at=? WHERE tg_id=?",
                (new_val, int(time.time()), tg_id))

    # Auto-fill profiles to new capacity
    vps[rtype] = new_val
    cap = _compute_capacity(vps["cpu"], vps["ram"], vps["storage"])
    profiles = _get_profiles(cur, tg_id)
    _fill_profiles(cur, tg_id, len(profiles), cap["maxProfiles"])
    con.commit()

    result = _vps_response(cur, tg_id)
    con.close()
    return jsonify(result)

# ── POST /api/vps/reset ───────────────────────────────────
@app.route("/api/vps/reset", methods=["POST"])
def api_vps_reset():
    data  = request.json or {}
    tg_id = data.get("tg_id")
    if not tg_id:
        return jsonify({"error": "no tg_id"}), 400
    tg_id = int(tg_id)
    con = get_db(); cur = con.cursor()
    _ensure_vps_tables(cur)
    cur.execute("UPDATE vps_state SET cpu=1,ram=1024,storage=20,bandwidth=1,updated_at=? WHERE tg_id=?",
                (int(time.time()), tg_id))
    cur.execute("DELETE FROM vps_profiles WHERE tg_id=?", (tg_id,))
    cap = _compute_capacity(1, 1024, 20)
    _fill_profiles(cur, tg_id, 0, cap["maxProfiles"])
    con.commit()
    result = _vps_response(cur, tg_id)
    con.close()
    return jsonify(result)

# ── PATCH /api/vps/profile/status ────────────────────────
@app.route("/api/vps/profile/status", methods=["PATCH"])
def api_profile_status():
    data      = request.json or {}
    tg_id     = data.get("tg_id")
    profile_id = data.get("profile_id")
    status    = data.get("status")
    if status not in ("idle","active","warming"):
        return jsonify({"error": "invalid status"}), 400
    con = get_db(); cur = con.cursor()
    _ensure_vps_tables(cur)
    cur.execute("UPDATE vps_profiles SET status=?,last_activity=? WHERE id=? AND tg_id=?",
                (status, int(time.time()), profile_id, int(tg_id)))
    con.commit()
    con.close()
    return jsonify({"ok": True})

# ── GET /api/vps/profile/suggest ─────────────────────────
@app.route("/api/vps/profile/suggest")
def api_profile_suggest():
    tg_id    = request.args.get("tg_id")
    platform = request.args.get("platform", "general")
    if not tg_id or not _is_authorized(tg_id):
        return jsonify({"error": "unauthorized"}), 403
    tg_id = int(tg_id)
    if platform not in PLATFORMS:
        platform = "general"

    con = get_db(); cur = con.cursor()
    _ensure_vps_tables(cur); con.commit()
    cur.execute("SELECT COUNT(*) FROM vps_profiles WHERE tg_id=?", (tg_id,))
    count = cur.fetchone()[0]
    con.close()

    plat = PLATFORMS[platform]
    suggestion = _gen_profile(tg_id, count)
    suggestion.pop("tg_id", None)
    suggestion.pop("created_at", None)
    suggestion.pop("last_activity", None)
    suggestion["status"]   = "idle"
    suggestion["platform"] = platform

    # Override config with platform-specific values
    suggestion["browser"]  = plat.get("browser", suggestion["browser"])
    suggestion["os"]       = plat.get("os", suggestion["os"])
    suggestion["recommended_proxy"]  = plat["proxy"]
    suggestion["proxy_type"]         = plat["proxy_type"]
    suggestion["risk_level"]         = plat["risk"]
    suggestion["suggested_use"]      = plat["note"]
    suggestion["bandwidth_gb"]       = plat["bandwidth_gb"]
    suggestion["platform_name"]      = plat["name"]
    suggestion["platform_icon"]      = plat["icon"]
    suggestion["cpu_cost"]           = plat["cpu"]
    suggestion["ram_cost"]           = plat["ram"]

    return jsonify(suggestion)

# ── GET /api/vps/platforms ────────────────────────────────
@app.route("/api/vps/platforms")
def api_vps_platforms():
    tg_id = request.args.get("tg_id")
    if not tg_id or not _is_authorized(tg_id):
        return jsonify({"error": "unauthorized"}), 403
    return jsonify(PLATFORMS)

# ── POST /api/vps/profile/add ─────────────────────────────
@app.route("/api/vps/profile/add", methods=["POST"])
def api_profile_add():
    data  = request.json or {}
    tg_id = data.get("tg_id")
    if not tg_id or not _is_authorized(str(tg_id)):
        return jsonify({"error": "unauthorized"}), 403
    tg_id = int(tg_id)
    con = get_db(); cur = con.cursor()
    _ensure_vps_tables(cur); con.commit()
    vps = _get_vps(cur, tg_id)
    cap = _compute_capacity(vps["cpu"], vps["ram"], vps["storage"])
    profiles = _get_profiles(cur, tg_id)
    if len(profiles) >= cap["maxProfiles"]:
        con.close()
        return jsonify({"error": "no_capacity", "message": "Sin capacidad. Agrega más recursos."}), 400
    now = int(time.time())
    profile = {
        "id":            data.get("id", str(_uuid.uuid4())),
        "tg_id":         tg_id,
        "name":          str(data.get("name", f"Perfil #{len(profiles)+1}"))[:40],
        "browser":       data.get("browser", random.choice(BROWSERS)),
        "os":            data.get("os", random.choice(OS_LIST)),
        "proxy":         data.get("proxy", f"{random.randint(10,200)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"),
        "status":        "idle",
        "fingerprint":   data.get("fingerprint", _uuid.uuid4().hex[:16].upper()),
        "platform":      data.get("platform", "general"),
        "last_activity": now,
        "created_at":    now
    }
    cur.execute("""
        INSERT INTO vps_profiles (id,tg_id,name,browser,os,proxy,status,fingerprint,platform,last_activity,created_at)
        VALUES (:id,:tg_id,:name,:browser,:os,:proxy,:status,:fingerprint,:platform,:last_activity,:created_at)
    """, profile)
    con.commit()
    result = _vps_response(cur, tg_id)
    con.close()
    return jsonify({"ok": True, "profile": profile, "vps": result})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
