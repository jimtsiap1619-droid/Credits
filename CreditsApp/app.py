from flask import Flask, render_template_string, request, redirect
import sqlite3
import datetime
import qrcode
import os
import uuid

app = Flask(__name__)

DB = "cards.db"

# ------------------ DATABASE ------------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS cards (
        id INTEGER PRIMARY KEY,
        username TEXT,
        card_code TEXT,
        credits INTEGER,
        created_at TEXT,
        next_refill TEXT
    )''')
    conn.commit()
    conn.close()

# ------------------ REFILL ------------------
def check_refill(card):
    now = datetime.datetime.now()
    next_refill = datetime.datetime.fromisoformat(card[5])

    if now >= next_refill:
        conn = sqlite3.connect(DB)
        c = conn.cursor()

        new_credits = card[3] + 2
        new_date = next_refill + datetime.timedelta(days=30)

        c.execute("UPDATE cards SET credits=?, next_refill=? WHERE id=?",
                  (new_credits, new_date.isoformat(), card[0]))
        conn.commit()
        conn.close()

# ------------------ CREATE CARD ------------------
@app.route("/create", methods=["POST"])
def create():
    username = request.form["username"]

    code = str(uuid.uuid4())[:8]

    created = datetime.datetime.now()
    next_refill = created + datetime.timedelta(days=30)

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO cards VALUES (NULL,?,?,?,?,?)",
              (username, code, 0, created.isoformat(), next_refill.isoformat()))
    conn.commit()
    conn.close()

    # QR
    url = f"https://YOUR-APP.onrender.com/card/{code}"
    img = qrcode.make(url)
    if not os.path.exists("static"):
        os.mkdir("static")
    img.save(f"static/{code}.png")

    return redirect("/")

# ------------------ HOME (ADMIN) ------------------
@app.route("/")
def home():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    cards = c.execute("SELECT * FROM cards").fetchall()
    conn.close()

    html = """
    <h1>ADMIN PANEL</h1>

    <form method="POST" action="/create">
        Username: <input name="username">
        <button>Create Card</button>
    </form>

    <hr>

    {% for c in cards %}
        <div style="border:1px solid black; padding:10px; margin:10px;">
            <b>{{c[1]}}</b><br>
            Code: {{c[2]}}<br>
            Credits: {{c[3]}}<br>

            <img src="/static/{{c[2]}}.png" width="100"><br>

            <a href="/add/{{c[2]}}">+1</a>
            <a href="/remove/{{c[2]}}">-1</a>
            <a href="/delete/{{c[0]}}">Delete</a>
        </div>
    {% endfor %}
    """

    return render_template_string(html, cards=cards)

# ------------------ ADD ------------------
@app.route("/add/<code>")
def add(code):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE cards SET credits = credits + 1 WHERE card_code=?", (code,))
    conn.commit()
    conn.close()
    return redirect("/")

# ------------------ REMOVE ------------------
@app.route("/remove/<code>")
def remove(code):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE cards SET credits = credits - 1 WHERE card_code=?", (code,))
    conn.commit()
    conn.close()
    return redirect("/")

# ------------------ DELETE ------------------
@app.route("/delete/<id>")
def delete(id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM cards WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/")

# ------------------ CARD VIEW ------------------
@app.route("/card/<code>")
def card(code):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    card = c.execute("SELECT * FROM cards WHERE card_code=?", (code,)).fetchone()
    conn.close()

    if not card:
        return "Card not found"

    check_refill(card)

    html = f"""
    <h1>Card Info</h1>
    Username: {card[1]}<br>
    Credits: {card[3]}<br>
    Created: {card[4]}<br>
    Next refill: {card[5]}<br>
    """

    return html

# ------------------
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
