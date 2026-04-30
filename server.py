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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
