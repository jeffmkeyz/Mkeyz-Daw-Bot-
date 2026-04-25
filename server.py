# -*- coding: utf-8 -*-
"""
Mkeyz Studio — Game Server (Flask)
Corre en paralelo con el bot en Railway
"""
from flask import Flask, jsonify, request, send_from_directory
import sqlite3, os, time

app = Flask(__name__, static_folder="static")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mkeyz.db")

def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
