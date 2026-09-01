from __future__ import annotations

import json
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from flask import Flask, g, redirect, render_template, request, url_for

ROOT = Path(__file__).resolve().parent
DB = ROOT / "bookings.db"

CITIES = [
    {"id": "lagos", "name": "Lagos", "state": "Lagos", "code": "LOS",
     "blurb": "The commercial heart: lagoon, markets, nightlife.",
    "best": "November to March",
    "image": "https://images.unsplash.com/photo-1543783207-ec64e4d95325?auto=format&fit=crop&w=1200&q=80"},
   {"id": "abuja", "name": "Abuja", "state": "FCT", "code": "ABV",
    "blurb": "Planned capital under Aso Rock.",
    "best": "November to February",
    "image": "https://images.unsplash.com/photo-1521295121783-8a321d551ad2?auto=format&fit=crop&w=1200&q=80"},
   {"id": "portharcourt", "name": "Port Harcourt", "state": "Rivers", "code": "PHC",
    "blurb": "Garden City of the Niger Delta.",
    "best": "December to March",
    "image": "https://images.unsplash.com/photo-1493246507139-91e8fad9978e?auto=format&fit=crop&w=1200&q=80"},
   {"id": "calabar", "name": "Calabar", "state": "Cross River", "code": "CBQ",
    "blurb": "Carnival capital and rainforest edge.",
    "best": "December, or June to September",
    "image": "https://images.unsplash.com/photo-1470770841072-f978cf4d019e?auto=format&fit=crop&w=1200&q=80"},
   {"id": "obudu", "name": "Obudu", "state": "Cross River", "code": "OBU",
    "blurb": "Highland ranch country and cool mornings.",
    "best": "November to April",
    "image": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80"},
   {"id": "yankari", "name": "Yankari", "state": "Bauchi", "code": "YKR",
    "blurb": "Savanna reserve and Wikki Warm Springs.",
    "best": "December to April",
    "image": "https://images.unsplash.com/photo-1473448912268-2022ce9509d8?auto=format&fit=crop&w=1200&q=80"},
   {"id": "enugu", "name": "Enugu", "state": "Enugu", "code": "ENU",
     "blurb": "Coal City. Hills and a stop between the East and Abuja.",
     "best": "November to March",
     "image": "https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=1200&q=80"},
   {"id": "kano", "name": "Kano", "state": "Kano", "code": "KAN",
     "blurb": "Ancient trading city of the north.",
     "best": "October to February",
     "image": "https://images.unsplash.com/photo-1523906834658-6e24ef2386f9?auto=format&fit=crop&w=1200&q=80"},
   {"id": "ibadan", "name": "Ibadan", "state": "Oyo", "code": "IBA",
     "blurb": "Largest indigenous city. Short hop from Lagos.",
     "best": "November to March",
     "image": "https://images.unsplash.com/photo-1516026672322-bc52d61a55d5?auto=format&fit=crop&w=1200&q=80"},
   {"id": "uyo", "name": "Uyo", "state": "Akwa Ibom", "code": "QUO",
     "blurb": "Quiet capital and a jump to Ibeno Beach.",
     "best": "November to April",
     "image": "https://images.unsplash.com/photo-1501594907352-04cda38ebc29?auto=format&fit=crop&w=1200&q=80"},
]

FLIGHT_OPS = ["Air Peace", "Ibom Air", "ValueJet", "Aero Contractors", "United Nigeria"]
BUS_OPS = ["GIGM", "ABC Transport", "God is Good Motors", "Cross Country"]
HOTEL_OPS = ["Marina Court", "Maitama House", "Creekview Lodge", "Tinapa Inn", "Iroko Residences"]

app = Flask(__name__)

import os
from sqlalchemy import create_engine, text

# Database configuration: prefer DATABASE_URL (Postgres/managed DB). If absent, fall back to local SQLite file.
DATABASE_URL = os.environ.get("DATABASE_URL")
engine = None
if DATABASE_URL:
    # create engine for the provided URL (e.g. postgres://... or postgresql+psycopg2://...)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def get_db():
    """Return a DB handle. If a managed DATABASE_URL is set, the module-level engine
    will be used for connections; otherwise a sqlite3 connection to the local bookings.db file is returned.
    """
    if engine:
        # Return the Engine for callers to use; higher-level functions will use engine.connect()/begin().
        return engine
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    if engine:
        # Create bookings table in managed DB if it doesn't exist
        with engine.begin() as conn:
            conn.execute(text(
                """
                CREATE TABLE IF NOT EXISTS bookings (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            ))
    else:
        db = sqlite3.connect(DB)
        db.execute(
            """CREATE TABLE IF NOT EXISTS bookings (
                id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        db.commit()
        db.close()


# Ensure the database is present before the app serves traffic under gunicorn / Vercel.
init_db()


def city_by_name(name: str):
    q = name.strip().lower()
    for c in CITIES:
        if c["name"].lower() == q or c["id"] == q or c["code"].lower() == q:
            return c
    return None


def naira(amount: int) -> str:
    return f"₦{amount:,}"


def search_offers(kind: str, origin: str, dest: str, when: str):
    a = city_by_name(origin)
    b = city_by_name(dest)
    if not a or not b:
        return []
    if kind != "hotel" and a["id"] == b["id"]:
        return []
    seed = abs(hash(f"{kind}|{a['id']}|{b['id']}|{when}"))
    rng = random.Random(seed)
    count = 4 + seed % 4
    offers = []
    for i in range(count):
        s = seed + i * 17
        if kind == "flight":
            mins = 55 + s % 70
            hour = (6 + s % 8) % 24
            minute = [0, 15, 30, 45][s % 4]
            depart = f"{hour:02d}:{minute:02d}"
            arr_m = hour * 60 + minute + mins
            arrive = f"{(arr_m // 60) % 24:02d}:{arr_m % 60:02d}"
            offers.append({
                "id": f"F-{a['code']}-{b['code']}-{s}",
                "type": "flight",
                "operator": FLIGHT_OPS[s % len(FLIGHT_OPS)],
                "from": a["name"],
                "to": b["name"],
                "depart": depart,
                "arrive": arrive,
                "duration": f"{mins // 60}h {mins % 60}m" if mins >= 60 else f"{mins}m",
                "price": 48000 + (s % 12) * 8500,
                "seats": 4 + s % 18,
                "cabin": "Business" if s % 5 == 0 else "Economy",
            })
        elif kind == "bus":
            mins = 180 + s % 360
            hour = (5 + s % 8) % 24
            minute = [0, 15, 30, 45][s % 4]
            depart = f"{hour:02d}:{minute:02d}"
            arr_m = hour * 60 + minute + mins
            arrive = f"{(arr_m // 60) % 24:02d}:{arr_m % 60:02d}"
            offers.append({
                "id": f"B-{a['code']}-{b['code']}-{s}",
                "type": "bus",
                "operator": BUS_OPS[s % len(BUS_OPS)],
                "from": a["name"],
                "to": b["name"],
                "depart": depart,
                "arrive": arrive,
                "duration": f"{mins // 60}h {mins % 60}m",
                "price": 8500 + (s % 10) * 1500,
                "seats": 8 + s % 20,
                "cabin": "VIP" if s % 3 == 0 else "Standard",
            })
        else:
            offers.append({
                "id": f"H-{b['code']}-{s}",
                "type": "hotel",
                "operator": HOTEL_OPS[s % len(HOTEL_OPS)],
                "from": b["name"],
                "to": b["name"],
                "depart": "15:00",
                "arrive": "11:00",
                "duration": "1 night",
                "price": 32000 + (s % 15) * 6500,
                "seats": 3 + s % 6,
                "cabin": "Suite" if s % 4 == 0 else "Deluxe",
            })
    offers.sort(key=lambda o: o["price"])
    return offers


@app.route("/")
def home():
    return render_template(
        "index.html",
        cities=CITIES[:6],
        tomorrow=(date.today() + timedelta(days=1)).isoformat(),
        city_names=[c["name"] for c in CITIES],
    )


@app.route("/search")
def search():
    kind = request.args.get("type", "flight")
    origin = request.args.get("from", "Lagos")
    dest = request.args.get("to", "Abuja")
    when = request.args.get("date", "")
    travelers = max(1, min(8, int(request.args.get("travelers", 1) or 1)))
    offers = search_offers(kind, origin, dest, when)
    return render_template(
        "search.html",
        offers=offers,
        kind=kind,
        origin=origin,
        dest=dest,
        when=when,
        travelers=travelers,
        naira=naira,
        tomorrow=(date.today() + timedelta(days=1)).isoformat(),
        city_names=[c["name"] for c in CITIES],
    )


@app.route("/book", methods=["GET", "POST"])
def book():
    kind = request.values.get("type", "flight")
    origin = request.values.get("from", "Lagos")
    dest = request.values.get("to", "Abuja")
    when = request.values.get("date", "")
    travelers = max(1, min(8, int(request.values.get("travelers", 1) or 1)))
    offer_id = request.values.get("offerId", "")
    offer = next((o for o in search_offers(kind, origin, dest, when) if o["id"] == offer_id), None)
    if not offer:
        return render_template("expired.html"), 404
    error = ""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        if len(name) < 2:
            error = "Enter the lead passenger name."
        elif "@" not in email:
            error = "Enter a valid email."
        elif len("".join(ch for ch in phone if ch.isdigit())) < 10:
            error = "Enter a Nigerian phone number."
        else:
            bid = f"NG-TRV-{date.today().year}-{random.randint(1000, 9999)}"
            payload = {
                "id": bid,
                "offer": offer,
                "date": when,
                "travelers": travelers,
                "name": name,
                "email": email,
                "phone": phone,
                "total": offer["price"] * travelers,
            }
            # Persist booking: use the managed DATABASE_URL if present, otherwise write to local sqlite file.
            if engine:
                with engine.begin() as conn:
                    conn.execute(text(
                        "INSERT INTO bookings (id, payload) VALUES (:id, :payload)"
                    ), {"id": bid, "payload": json.dumps(payload)})
            else:
                db = get_db()
                db.execute(
                    "INSERT INTO bookings (id, payload, created_at) VALUES (?, ?, datetime('now'))",
                    (bid, json.dumps(payload)),
                )
                db.commit()
            return redirect(url_for("confirm", id=bid))
    return render_template(
        "book.html",
        offer=offer,
        kind=kind,
        origin=origin,
        dest=dest,
        when=when,
        travelers=travelers,
        total=offer["price"] * travelers,
        naira=naira,
        error=error,
    )


@app.route("/confirm")
def confirm():
    bid = request.args.get("id", "")
    booking = None
    if engine:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT payload FROM bookings WHERE id = :id"), {"id": bid})
            row = res.fetchone()
            booking = json.loads(row[0]) if row else None
    else:
        row = get_db().execute("SELECT payload FROM bookings WHERE id = ?", (bid,)).fetchone()
        booking = json.loads(row["payload"]) if row else None
    return render_template("confirm.html", booking=booking, naira=naira)


@app.route("/destinations")
def destinations():
    return render_template("destinations.html", cities=CITIES)


@app.route("/destinations/<slug>")
def destination(slug):
    city = next((c for c in CITIES if c["id"] == slug), None)
    if not city:
        return "Not found", 404
    origin = "Abuja" if city["name"] == "Lagos" else "Lagos"
    return render_template(
        "destination.html",
        city=city,
        origin=origin,
        tomorrow=(date.today() + timedelta(days=1)).isoformat(),
    )


@app.route("/trips")
def trips():
    items = []
    if engine:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT payload FROM bookings ORDER BY created_at DESC"))
            items = [json.loads(r[0]) for r in res.fetchall()]
    else:
        rows = get_db().execute("SELECT payload FROM bookings ORDER BY created_at DESC").fetchall()
        items = [json.loads(r["payload"]) for r in rows]
    return render_template("trips.html", trips=items, naira=naira)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
