# Medicine Expiry & Stock Alert System

A simple tool for local pharmacies. Scan a medicine strip's barcode (or type the details),
and get an instant alert if it is near expiry or already expired.

**Scan -> Check -> Alert**

## How it works (matches the poster)
1. **Scan / Enter** - phone camera, USB barcode scanner, or manual typing (`/scan`).
2. **Fetch details** - a known barcode auto-fills name and batch from your saved records.
3. **Check & Alert** - red (expired), orange (within 7 days), yellow (within 30 days), green (safe).
4. **Update stock** - same batch adds to the count; a new batch creates a new entry.
5. **View reports** - dashboard, inventory with search/filter, expiry reports, CSV export.

## Tech stack
Python + Flask (backend) - SQLite (database) - HTML/CSS/JS (frontend) - Phone camera or USB scanner (input)

## Run it
```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python seed_demo.py            # optional sample data
python app.py
```
Open http://127.0.0.1:5000

## Using the barcode scanner
- **USB scanner**: click the Barcode box and scan. The scanner "types" the number and presses Enter.
- **Phone camera**: the browser camera needs `https` or `localhost`. Easiest ways:
  - Chrome on Android: open `chrome://flags`, search "Insecure origins treated as secure",
    add `http://<your-pc-ip>:5000`, enable, relaunch. Then browse to that address on the same Wi-Fi.
  - Or deploy to any https host (PythonAnywhere, Render).
  - Camera scanning uses the browser `BarcodeDetector` (Chrome/Edge on Android). If missing, use manual entry.
- Many Indian medicine strips carry batch and expiry as printed text, not in the barcode.
  So the barcode identifies the product; you enter batch and expiry once per batch.

## Settings
Edit `CRITICAL_DAYS` and `NEAR_DAYS` at the top of `app.py` to change alert windows.
Change `app.secret_key` before real use.

## Files
```
app.py            routes, alert logic, SQLite
seed_demo.py      sample data
templates/        dashboard, scan, inventory, reports
static/           style.css, app.js (camera + live alert)
```
