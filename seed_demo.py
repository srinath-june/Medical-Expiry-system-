"""Optional: load sample medicines so you can see the alerts working."""
from datetime import date, timedelta
import sqlite3
from app import init_db, DB_PATH

init_db()
conn = sqlite3.connect(DB_PATH)
today = date.today()
rows = [
    ("8901030000011", "Paracetamol 500mg", "B7421", today + timedelta(days=20), 48),
    ("8901030000028", "Amoxicillin 250mg", "A1190", today - timedelta(days=10), 12),
    ("8901030000035", "Cetirizine 10mg", "C5523", today + timedelta(days=5), 30),
    ("8901030000042", "ORS Powder", "D8841", today + timedelta(days=200), 102),
    ("8901030000059", "Azithromycin 500mg", "E3310", today + timedelta(days=75), 25),
]
for bc, n, b, e, q in rows:
    conn.execute("INSERT INTO medicines (barcode,name,batch_no,expiry_date,quantity,added_on) VALUES (?,?,?,?,?,?)",
                 (bc, n, b, e.isoformat(), q, today.isoformat()))
conn.commit()
print("Demo data added.")
