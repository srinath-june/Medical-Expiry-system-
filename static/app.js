// Scan page: camera/USB barcode -> fetch details -> live expiry alert.
const $ = (id) => document.getElementById(id);
const barcode = $("barcode"), nameEl = $("name"), batch = $("batch"),
      expiry = $("expiry"), live = $("live"), found = $("found"),
      video = $("video"), camBtn = $("camBtn"), stopBtn = $("stopBtn"), camMsg = $("camMsg");

let stream = null, timer = null;

function setStep(n) {
  document.querySelectorAll("#progress li").forEach((li) =>
    li.classList.toggle("on", Number(li.dataset.s) <= n));
}

// Step 2: fetch saved details for this barcode
async function lookup() {
  const code = barcode.value.trim();
  if (!code) return;
  const r = await fetch("/api/lookup?barcode=" + encodeURIComponent(code));
  const data = await r.json();
  if (data.found) {
    nameEl.value = data.name;
    const b = data.batches[0];
    if (b && !batch.value) batch.value = b.batch_no;
    found.hidden = false;
    found.textContent = "Found in your records: " + data.name + " (" +
      data.batches.length + " batch" + (data.batches.length > 1 ? "es" : "") + " saved).";
    setStep(2);
    (batch.value ? expiry : batch).focus();
  } else {
    found.hidden = false;
    found.textContent = "New barcode. Enter the name once and it will be remembered.";
    setStep(2);
    nameEl.focus();
  }
}

// Step 3: instant alert as soon as expiry date is chosen
async function check() {
  if (!expiry.value) { live.hidden = true; return; }
  const r = await fetch("/api/check?expiry=" + expiry.value);
  const s = await r.json();
  if (s.error) return;
  const title = { expired: "Expired!", critical: "Near expiry!", near: "Near expiry!", ok: "Safe to sell" }[s.key];
  live.className = "alert-box live " + s.key;
  live.innerHTML = title + "<small>" + s.label + "</small>";
  live.hidden = false;
  setStep(3);
}

barcode.addEventListener("keydown", (e) => {   // USB scanners press Enter after scanning
  if (e.key === "Enter") { e.preventDefault(); lookup(); }
});
barcode.addEventListener("change", lookup);
expiry.addEventListener("change", check);
$("qty").addEventListener("focus", () => setStep(4));

// Camera scanning (Chrome / Edge / Android browsers support BarcodeDetector)
async function startCamera() {
  if (!("BarcodeDetector" in window)) {
    camMsg.textContent = "Camera scanning is not supported in this browser. Use Chrome on Android, a USB scanner, or type the barcode.";
    return;
  }
  if (!navigator.mediaDevices) {
    camMsg.textContent = "Camera needs https or localhost. See the README for phone setup.";
    return;
  }
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
  } catch (e) {
    camMsg.textContent = "Camera blocked. Allow camera access and try again.";
    return;
  }
  const detector = new BarcodeDetector({
    formats: ["ean_13", "ean_8", "upc_a", "upc_e", "code_128", "code_39", "qr_code", "data_matrix"],
  });
  video.srcObject = stream; video.hidden = false; await video.play();
  camBtn.hidden = true; stopBtn.hidden = false;
  camMsg.textContent = "Point the camera at the barcode on the strip.";
  timer = setInterval(async () => {
    try {
      const codes = await detector.detect(video);
      if (codes.length) {
        barcode.value = codes[0].rawValue;
        stopCamera();
        navigator.vibrate && navigator.vibrate(80);
        lookup();
      }
    } catch (_) {}
  }, 300);
}

function stopCamera() {
  clearInterval(timer);
  if (stream) stream.getTracks().forEach((t) => t.stop());
  stream = null; video.hidden = true; camBtn.hidden = false; stopBtn.hidden = true;
  camMsg.textContent = "Barcode captured.";
}

camBtn.addEventListener("click", startCamera);
stopBtn.addEventListener("click", stopCamera);
barcode.focus();
