"""Medicine Expiry & Stock Alert System - Flask + SQLite backend."""
import csv
import io
import sqlite3
from datetime import date, datetime
from pathlib import Path

from flask import (Flask, Response, flash, g, jsonify, redirect,
                   render_template, request, url_for)

BASE = Path(__file__).parent
DB_PATH = BASE / "medicine.db"
CRITICAL_DAYS = 7    # red/orange alert window
NEAR_DAYS = 30       # yellow alert window

app = Flask(__name__)
app.secret_key = "change-this-secret-key"


# ---------- database ----------
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    conn = g.pop("db", None)
    if conn:
        conn.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL,
            batch_no TEXT NOT NULL DEFAULT '',
            expiry_date TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            added_on TEXT NOT NULL
        )""")
    conn.commit()
    conn.close()


# ---------- core logic: check & alert ----------
def status_of(expiry_str):
    """Return colour-coded status for an expiry date (YYYY-MM-DD)."""
    days = (datetime.strptime(expiry_str, "%Y-%m-%d").date() - date.today()).days
    if days < 0:
        return {"key": "expired", "label": f"Expired {-days} day(s) ago", "days": days}
    if days <= CRITICAL_DAYS:
        return {"key": "critical", "label": f"Expires in {days} day(s)", "days": days}
    if days <= NEAR_DAYS:
        return {"key": "near", "label": f"Near expiry - {days} days left", "days": days}
    return {"key": "ok", "label": f"Safe - {days} days left", "days": days}


def enrich(rows):
    out = []
    for r in rows:
        d = dict(r)
        d["status"] = status_of(d["expiry_date"])
        out.append(d)
    return out


def all_medicines():
    return enrich(db().execute(
        "SELECT * FROM medicines ORDER BY expiry_date ASC, name ASC").fetchall())


def total_stock(name):
    row = db().execute(
        "SELECT COALESCE(SUM(quantity),0) AS t FROM medicines WHERE lower(name)=lower(?)",
        (name,)).fetchone()
    return row["t"]


# ---------- pages ----------
@app.route("/")
def dashboard():
    meds = [m for m in all_medicines() if m["quantity"] > 0]
    counts = {k: sum(1 for m in meds if m["status"]["key"] == k)
              for k in ("expired", "critical", "near", "ok")}
    urgent = [m for m in meds if m["status"]["key"] != "ok"][:8]
    return render_template("dashboard.html", counts=counts, urgent=urgent,
                           total=sum(m["quantity"] for m in meds),
                           critical_days=CRITICAL_DAYS, near_days=NEAR_DAYS)


@app.route("/scan", methods=["GET", "POST"])
def scan():
    """Step 1-4: scan/enter -> fetch details -> check & alert -> update stock."""
    if request.method == "GET":
        return render_template("scan.html", result=None)

    barcode = request.form.get("barcode", "").strip()
    name = request.form.get("name", "").strip()
    batch = request.form.get("batch_no", "").strip()
    expiry = request.form.get("expiry_date", "").strip()
    try:
        qty = int(request.form.get("quantity", "0"))
        datetime.strptime(expiry, "%Y-%m-%d")
    except ValueError:
        flash("Please enter a valid expiry date and quantity.", "error")
        return render_template("scan.html", result=None), 400
    if not name or qty <= 0:
        flash("Medicine name and a quantity above 0 are required.", "error")
        return render_template("scan.html", result=None), 400

    conn = db()
    existing = conn.execute(
        "SELECT id FROM medicines WHERE lower(name)=lower(?) AND batch_no=? AND expiry_date=?",
        (name, batch, expiry)).fetchone()
    if existing:   # same batch -> just add strips
        conn.execute("UPDATE medicines SET quantity=quantity+?, barcode=COALESCE(NULLIF(?,''),barcode) WHERE id=?",
                     (qty, barcode, existing["id"]))
    else:
        conn.execute(
            "INSERT INTO medicines (barcode,name,batch_no,expiry_date,quantity,added_on) VALUES (?,?,?,?,?,?)",
            (barcode, name, batch, expiry, qty, datetime.now().isoformat(timespec="seconds")))
    conn.commit()

    result = {"name": name, "batch_no": batch, "expiry": expiry, "added": qty,
              "total": total_stock(name), "status": status_of(expiry)}
    return render_template("scan.html", result=result)


@app.route("/inventory")
def inventory():
    q = request.args.get("q", "").strip().lower()
    flt = request.args.get("filter", "all")
    meds = all_medicines()
    if q:
        meds = [m for m in meds if q in m["name"].lower() or q in m["barcode"] or q in m["batch_no"].lower()]
    if flt != "all":
        meds = [m for m in meds if m["status"]["key"] == flt]
    return render_template("inventory.html", meds=meds, q=q, flt=flt)


@app.route("/reports")
def reports():
    """Step 5: view expiry list, stock status and alerts."""
    meds = [m for m in all_medicines() if m["quantity"] > 0]
    groups = {
        "expired": [m for m in meds if m["status"]["key"] == "expired"],
        "critical": [m for m in meds if m["status"]["key"] == "critical"],
        "near": [m for m in meds if m["status"]["key"] == "near"],
        "ok": [m for m in meds if m["status"]["key"] == "ok"],
    }
    return render_template("reports.html", groups=groups,
                           critical_days=CRITICAL_DAYS, near_days=NEAR_DAYS)


@app.post("/sell/<int:med_id>")
def sell(med_id):
    try:
        qty = max(1, int(request.form.get("quantity", "1")))
    except ValueError:
        qty = 1
    conn = db()
    row = conn.execute("SELECT * FROM medicines WHERE id=?", (med_id,)).fetchone()
    if row:
        new_qty = max(0, row["quantity"] - qty)
        conn.execute("UPDATE medicines SET quantity=? WHERE id=?", (new_qty, med_id))
        conn.commit()
        flash(f"{row['name']}: stock is now {new_qty} strips.", "success")
    return redirect(request.referrer or url_for("inventory"))


@app.post("/delete/<int:med_id>")
def delete(med_id):
    db().execute("DELETE FROM medicines WHERE id=?", (med_id,))
    db().commit()
    flash("Entry removed.", "success")
    return redirect(request.referrer or url_for("inventory"))


@app.get("/export.csv")
def export_csv():
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Name", "Barcode", "Batch", "Expiry", "Quantity", "Status"])
    for m in all_medicines():
        w.writerow([m["name"], m["barcode"], m["batch_no"], m["expiry_date"],
                    m["quantity"], m["status"]["label"]])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=medicine_stock.csv"})


# ---------- JSON API used by the scan page ----------
@app.get("/api/lookup")
def api_lookup():
    """Step 2: fetch saved details for a scanned barcode."""
    code = request.args.get("barcode", "").strip()
    rows = db().execute(
        "SELECT * FROM medicines WHERE barcode=? AND barcode!='' ORDER BY id DESC", (code,)).fetchall()
    if not rows:
        return jsonify(found=False)
    latest = rows[0]
    return jsonify(found=True, name=latest["name"],
                   batches=[{"batch_no": r["batch_no"], "expiry": r["expiry_date"],
                             "quantity": r["quantity"]} for r in rows])


@app.get("/api/check")
def api_check():
    """Step 3: instant alert for an expiry date."""
    try:
        return jsonify(status_of(request.args.get("expiry", "")))
    except ValueError:
        return jsonify(error="Invalid date"), 400


init_db()

if __name__ == "__main__":
    # host 0.0.0.0 lets a phone on the same Wi-Fi open the app
    app.run(host="0.0.0.0", port=5000, debug=True)
