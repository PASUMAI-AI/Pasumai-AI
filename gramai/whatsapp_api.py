"""KISANSETU WhatsApp Cloud API bridge (prototype).

Flow:
    farmer -> WhatsApp -> Meta Cloud API -> POST /webhook
        text  : parse crop + quantity, hold as a pending declaration
        image : download media, run the EXISTING YOLO grader, issue the
                EXISTING certificate, write inventory, reply on WhatsApp

Reuses quality_model.analyze_produce_image and
certificate_service.generate_quality_certificate - no second YOLO pipeline.

Webhook work runs in a background task so Meta always gets its 200 quickly;
Meta retries the delivery if the response is slow.
"""
from __future__ import annotations

from fastapi import (APIRouter, Request, HTTPException, BackgroundTasks, Depends,
                      UploadFile, File, Form)
from fastapi.responses import PlainTextResponse
import os, re, sqlite3, secrets, bcrypt

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

router = APIRouter(tags=["KISANSETU WhatsApp"])

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "gramai.db")
UPLOAD_DIR = os.path.join(BASE, "uploads", "whatsapp")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --------------------------------------------------------------------------
# Config. Secrets come from the environment only and are never logged.
# --------------------------------------------------------------------------
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "").strip()
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "").strip()
WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "kisansetu_webhook_2026").strip()
GRAPH_VERSION = os.environ.get("WHATSAPP_GRAPH_VERSION", "v23.0").strip()
GRAPH_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"

DEFAULT_STATE = "Tamil Nadu"
DEFAULT_DISTRICT = "Coimbatore"


def log(stage, msg):
    print(f"[{stage}] {msg}", flush=True)


def db():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    return c


def init_whatsapp_schema():
    c = db()
    c.executescript(
        """
        -- A text declaration waiting for its photo.
        CREATE TABLE IF NOT EXISTS whatsapp_pending_produce(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          whatsapp_number TEXT UNIQUE NOT NULL,
          crop TEXT NOT NULL,
          quantity REAL NOT NULL,
          unit TEXT NOT NULL DEFAULT 'kg',
          quantity_kg REAL NOT NULL,
          created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS whatsapp_inventory(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER,
          whatsapp_number TEXT NOT NULL,
          crop TEXT NOT NULL,
          quantity REAL NOT NULL,
          unit TEXT NOT NULL DEFAULT 'kg',
          quantity_kg REAL NOT NULL,
          declared_crop TEXT,
          detected_crop TEXT,
          detected_class TEXT,
          grade TEXT,
          confidence REAL,
          verification_status TEXT DEFAULT 'awaiting_image',
          certificate_status TEXT DEFAULT 'pending',
          certificate_number TEXT,
          verification_id INTEGER,
          image_path TEXT,
          created_at TEXT DEFAULT (datetime('now')),
          updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_wa_inv_user ON whatsapp_inventory(user_id, id);
        """
    )
    c.commit()
    c.close()


# --------------------------------------------------------------------------
# Text parsing
# --------------------------------------------------------------------------
UNIT_ALIASES = {
    "kg": "kg", "kgs": "kg", "kilo": "kg", "kilos": "kg",
    "kilogram": "kg", "kilograms": "kg",
    "g": "g", "gram": "g", "grams": "g", "gm": "g",
    "ton": "tonne", "tons": "tonne", "tonne": "tonne", "tonnes": "tonne",
    "quintal": "quintal", "quintals": "quintal", "qtl": "quintal",
}

TO_KG = {"kg": 1.0, "g": 0.001, "tonne": 1000.0, "quintal": 100.0}

# Crop vocabulary. Aliases map to the canonical name used elsewhere in GRAM AI.
CROP_ALIASES = {
    "rice": "Rice", "paddy": "Rice",
    "wheat": "Wheat", "gehu": "Wheat",
    "maize": "Maize", "corn": "Maize",
    "tomato": "Tomato", "tomatoes": "Tomato",
    "potato": "Potato", "potatoes": "Potato",
    "onion": "Onion", "onions": "Onion",
    "cotton": "Cotton", "sugarcane": "Sugarcane",
    "groundnut": "Groundnut", "peanut": "Groundnut",
    "soybean": "Soybean", "soyabean": "Soybean",
    "banana": "Banana", "mango": "Mango",
    "chilli": "Chilli", "chili": "Chilli", "chillies": "Chilli",
    "turmeric": "Turmeric", "millet": "Millet", "bajra": "Millet",
}

_QTY = re.compile(
    r"(\d+(?:\.\d+)?)\s*"
    r"(kgs?|kilo(?:gram)?s?|kilos?|gm|grams?|g|tonnes?|tons?|quintals?|qtl)\b",
    re.I,
)


def parse_produce_message(text):
    """Return {'crop','quantity','unit','quantity_kg'} or None. Never guesses."""
    if not text:
        return None
    low = text.lower().strip()

    m = _QTY.search(low)
    if not m:
        return None
    quantity = float(m.group(1))
    unit = UNIT_ALIASES.get(m.group(2).lower())
    if not unit:
        return None

    crop = None
    for alias in sorted(CROP_ALIASES, key=len, reverse=True):
        if re.search(r"\b" + re.escape(alias) + r"\b", low):
            crop = CROP_ALIASES[alias]
            break
    if not crop:
        return None

    return {
        "crop": crop,
        "quantity": quantity,
        "unit": unit,
        "quantity_kg": round(quantity * TO_KG[unit], 3),
    }


# --------------------------------------------------------------------------
# Farmer identification
# --------------------------------------------------------------------------
def resolve_farmer(wa_id, profile_name=""):
    """Match a sender id to a farmer, creating one if unknown.

    wa_id arrives with a country code ("916382713089") while users.phone holds
    a local 10-digit number ("9876543210"), so both forms are tried. It may
    also be a non-phone key from another channel (Telegram's "tg<chat_id>",
    the in-app chat's "app<user_id>") - those are matched exactly first, so
    every caller that resolves a farmer by sender id (WhatsApp, Telegram,
    in-app chat) lands on the same row instead of each creating its own.
    """
    c = db()
    exact = c.execute("SELECT * FROM users WHERE phone=? LIMIT 1", (str(wa_id),)).fetchone()
    if exact:
        c.close()
        log("WHATSAPP", f"Farmer matched (exact): id={exact['id']} name={exact['name']}")
        return dict(exact)

    digits = "".join(ch for ch in str(wa_id) if ch.isdigit())
    local = digits[-10:] if len(digits) >= 10 else digits

    row = c.execute(
        "SELECT * FROM users WHERE phone=? OR phone=? OR phone=? LIMIT 1",
        (local, digits, "+" + digits),
    ).fetchone()
    if row:
        c.close()
        log("WHATSAPP", f"Farmer matched: id={row['id']} name={row['name']}")
        return dict(row)

    # Unknown number: create a minimal farmer so the prototype works for anyone.
    name = (profile_name or "").strip() or f"WhatsApp Farmer {local[-4:]}"
    email = f"wa{local}@kisansetu.local"
    pw = bcrypt.hashpw(secrets.token_urlsafe(16).encode(), bcrypt.gensalt()).decode()
    try:
        cur = c.execute(
            "INSERT INTO users(name,email,password,role,district,state,phone) "
            "VALUES(?,?,?,?,?,?,?)",
            (name, email, pw, "farmer", DEFAULT_DISTRICT, DEFAULT_STATE, local),
        )
        c.commit()
        uid = cur.lastrowid
        row = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        log("WHATSAPP", f"Farmer auto-created: id={uid} name={name}")
        out = dict(row)
    except Exception as e:
        log("WHATSAPP", f"Farmer create failed: {e}")
        out = None
    c.close()
    return out


# --------------------------------------------------------------------------
# Meta Cloud API
# --------------------------------------------------------------------------
def whatsapp_send_text(to, message):
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        log("WHATSAPP", "Reply skipped: WhatsApp credentials are not configured")
        return None
    if not requests:
        return None
    try:
        r = requests.post(
            f"{GRAPH_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages",
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}",
                     "Content-Type": "application/json"},
            json={"messaging_product": "whatsapp", "recipient_type": "individual",
                  "to": to, "type": "text", "text": {"body": message}},
            timeout=30,
        )
        # Status only - the body can echo request context, never log the header.
        log("WHATSAPP", f"Reply sent to {to}: HTTP {r.status_code}")
        return r.status_code < 300
    except Exception as e:
        log("WHATSAPP", f"Reply failed: {e}")
        return None


def download_whatsapp_image(media_id):
    """Resolve a media id to a download URL, then save the bytes locally."""
    if not WHATSAPP_TOKEN:
        raise RuntimeError("WHATSAPP_ACCESS_TOKEN is not configured")
    if not requests:
        raise RuntimeError("requests is not installed")

    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}

    log("WHATSAPP", f"Requesting media metadata for id={media_id}")
    meta = requests.get(f"{GRAPH_URL}/{media_id}", headers=headers, timeout=30)
    meta.raise_for_status()
    url = meta.json().get("url")
    if not url:
        raise RuntimeError("Meta returned no download URL for this media id")

    log("WHATSAPP", "Downloading media bytes")
    # The lookaside URL also requires the bearer token.
    img = requests.get(url, headers=headers, timeout=60)
    img.raise_for_status()

    path = os.path.join(UPLOAD_DIR, f"wa_{media_id}_{secrets.token_hex(4)}.jpg")
    with open(path, "wb") as f:
        f.write(img.content)
    log("WHATSAPP", f"Media saved ({len(img.content)} bytes)")
    return path


# --------------------------------------------------------------------------
# Message handlers
# --------------------------------------------------------------------------
def store_declaration(sender, profile_name, parsed):
    """Record a crop declaration awaiting its photo.

    Shared by the WhatsApp webhook and the in-app GRAM Saathi assistant, so
    both write the same rows and both surface on the same dashboard section.
    """
    log("INVENTORY", f"Parsed crop={parsed['crop']} "
                     f"quantity={parsed['quantity']} {parsed['unit']} "
                     f"({parsed['quantity_kg']} kg)")

    farmer = resolve_farmer(sender, profile_name)

    c = db()
    c.execute(
        "INSERT INTO whatsapp_pending_produce"
        "(whatsapp_number,crop,quantity,unit,quantity_kg,created_at) "
        "VALUES(?,?,?,?,?,datetime('now')) "
        "ON CONFLICT(whatsapp_number) DO UPDATE SET "
        "crop=excluded.crop,quantity=excluded.quantity,unit=excluded.unit,"
        "quantity_kg=excluded.quantity_kg,created_at=excluded.created_at",
        (sender, parsed["crop"], parsed["quantity"], parsed["unit"],
         parsed["quantity_kg"]),
    )
    # Record the declaration immediately so the dashboard shows it before the photo.
    c.execute(
        "INSERT INTO whatsapp_inventory"
        "(user_id,whatsapp_number,crop,quantity,unit,quantity_kg,declared_crop,"
        "verification_status,certificate_status,created_at,updated_at) "
        "VALUES(?,?,?,?,?,?,?,'awaiting_image','pending',datetime('now'),datetime('now'))",
        (farmer["id"] if farmer else None, sender, parsed["crop"],
         parsed["quantity"], parsed["unit"], parsed["quantity_kg"], parsed["crop"]),
    )
    c.commit()
    c.close()
    log("INVENTORY", f"Declaration stored for {sender}")
    return farmer


def handle_text(sender, profile_name, text):
    """WhatsApp path: parse, store, and reply over WhatsApp."""
    log("WHATSAPP", f"Text from {sender}: {text!r}")
    parsed = parse_produce_message(text)

    if not parsed:
        whatsapp_send_text(sender,
            "🌾 KISANSETU could not read a crop and quantity in that message.\n\n"
            "Try one of these:\n"
            "• I have 30 kg rice\n"
            "• Wheat 50 kg\n"
            "• I harvested 2 tonnes maize")
        return

    store_declaration(sender, profile_name, parsed)

    whatsapp_send_text(sender,
        "✅ KISANSETU inventory updated!\n\n"
        f"🌾 Crop: {parsed['crop']}\n"
        f"⚖️ Quantity: {parsed['quantity']:g} {parsed['unit']}\n\n"
        "📸 Now send a clear photo of the produce to verify its quality.")


def handle_image(sender, profile_name, media_id):
    """Real WhatsApp path: resolve the media id through Meta, then process it."""
    log("WHATSAPP", f"Image from {sender}, media id={media_id}")
    try:
        image_path = download_whatsapp_image(media_id)
    except Exception as e:
        log("WHATSAPP", f"Media download failed: {e}")
        whatsapp_send_text(sender, "❌ Could not download that photo. Please send it again.")
        return
    process_produce_image(sender, profile_name, image_path)


def process_produce_image(sender, profile_name, image_path, notify=True):
    """Everything from a saved image file onward - YOLO, certificate, inventory.

    Shared by the WhatsApp webhook, the simulator, and the in-app assistant.
    notify=False suppresses the WhatsApp reply and returns the result instead,
    so the in-app chat can render it directly.
    """
    def out(payload):
        return payload

    c = db()
    pending = c.execute(
        "SELECT * FROM whatsapp_pending_produce WHERE whatsapp_number=?",
        (sender,)).fetchone()
    c.close()

    if not pending:
        if notify:
            whatsapp_send_text(sender,
                "📸 Photo received, but I do not know the crop yet.\n\n"
                "Please send the details first, for example:\n"
                "• I have 30 kg rice")
        return out({"ok": False, "reason": "no_declaration"})

    crop = pending["crop"]
    quantity = pending["quantity"]
    unit = pending["unit"]
    quantity_kg = pending["quantity_kg"]

    farmer = resolve_farmer(sender, profile_name)
    if not farmer:
        if notify:
            whatsapp_send_text(sender, "Could not link your number to a KISANSETU account.")
        return out({"ok": False, "reason": "no_farmer"})

    # Existing YOLO grader - not a second pipeline.
    log("YOLO", "Running prediction")
    try:
        from quality_model import analyze_produce_image
        result = analyze_produce_image(image_path, crop)
    except Exception as e:
        log("YOLO", f"Prediction failed: {e}")
        if notify:
            whatsapp_send_text(sender,
                "❌ Photo received, but quality inspection failed.\n\n"
                f"{str(e)[:180]}")
        return out({"ok": False, "reason": "yolo_failed", "error": str(e)[:180]})

    log("YOLO", f"Grade={result['grade']} confidence={result['confidence_percent']}% "
                f"class={result['class_name']}")

    # This model grades quality (A/B/C); it is not a crop classifier. The raw
    # class is kept as a weak signal and only contradicts the farmer when it
    # clearly names a different known crop.
    detected_class = str(result.get("class_name", ""))
    verification_status = "verified"
    detected_crop = None
    low = detected_class.lower().replace("_", " ")
    for alias, canon in CROP_ALIASES.items():
        if re.search(r"\b" + re.escape(alias) + r"\b", low):
            detected_crop = canon
            break
    if detected_crop and detected_crop != crop:
        verification_status = "mismatch"
    log("YOLO", f"Declared={crop} detected_class={detected_class} "
                f"status={verification_status}")

    c = db()
    cur = c.execute(
        "INSERT INTO quality_verifications"
        "(user_id,crop,predicted_grade,confidence,image_path,latitude,longitude,"
        "location_source,model_name,created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,datetime('now'))",
        (farmer["id"], crop, result["grade"], result["confidence"], image_path,
         0.0, 0.0, "whatsapp", result["model"]),
    )
    verification_id = cur.lastrowid
    certificate_number = f"GRAMAI-QC-{verification_id:06d}"

    certificate_status = "issued"
    try:
        from certificate_service import generate_quality_certificate
        certificate_path = generate_quality_certificate(
            certificate_number=certificate_number,
            farmer_name=farmer["name"],
            crop=crop,
            grade=result["grade"],
            confidence=result["confidence"],
            latitude=0.0,
            longitude=0.0,
            location_source="whatsapp",
            image_hash=result["image_sha256"],
            model_name=result["model"],
            image_path=image_path,
            scanned_at=c.execute("SELECT created_at FROM quality_verifications WHERE id=?",
                                 (verification_id,)).fetchone()["created_at"],
        )
        c.execute("UPDATE quality_verifications SET certificate_path=? WHERE id=?",
                  (certificate_path, verification_id))
        c.execute(
            "INSERT INTO quality_certificates"
            "(verification_id,certificate_number,farmer_id,crop,grade,confidence,"
            "latitude,longitude,certificate_path,issued_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,datetime('now'))",
            (verification_id, certificate_number, farmer["id"], crop,
             result["grade"], result["confidence"], 0.0, 0.0, certificate_path),
        )
        from certificate_service import apply_validity
        apply_validity(c, verification_id)
        log("CERTIFICATE", f"Issued {certificate_number}")
    except Exception as e:
        certificate_status = "failed"
        log("CERTIFICATE", f"Generation failed: {e}")

    # Attach the result to the declaration this farmer is waiting on.
    row = c.execute(
        "SELECT id FROM whatsapp_inventory WHERE whatsapp_number=? "
        "AND verification_status='awaiting_image' ORDER BY id DESC LIMIT 1",
        (sender,)).fetchone()
    fields = (farmer["id"], detected_class, detected_crop, result["grade"],
              result["confidence"], verification_status, certificate_status,
              certificate_number, verification_id, image_path)
    if row:
        c.execute(
            "UPDATE whatsapp_inventory SET user_id=?,detected_class=?,detected_crop=?,"
            "grade=?,confidence=?,verification_status=?,certificate_status=?,"
            "certificate_number=?,verification_id=?,image_path=?,"
            "updated_at=datetime('now') WHERE id=?",
            fields + (row["id"],))
    else:
        c.execute(
            "INSERT INTO whatsapp_inventory"
            "(whatsapp_number,crop,quantity,unit,quantity_kg,declared_crop,user_id,"
            "detected_class,detected_crop,grade,confidence,verification_status,"
            "certificate_status,certificate_number,verification_id,image_path,"
            "created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),datetime('now'))",
            (sender, crop, quantity, unit, quantity_kg, crop) + fields)

    c.execute("DELETE FROM whatsapp_pending_produce WHERE whatsapp_number=?", (sender,))
    c.commit()
    c.close()
    log("INVENTORY", f"Updated crop record for farmer id={farmer['id']}")

    if notify:
        if verification_status == "mismatch":
            whatsapp_send_text(sender,
                "⚠️ Image verification result\n\n"
                f"You declared: {crop}\n"
                f"Image suggests: {detected_crop}\n"
                f"Confidence: {result['confidence_percent']}%\n\n"
                "Please check the crop information in KISANSETU.")
        else:
            whatsapp_send_text(sender,
                "📸 Image received and inspected!\n\n"
                f"🌾 Crop: {crop}\n"
                f"⚖️ Quantity: {quantity:g} {unit}\n"
                f"🏅 Quality grade: {result['grade']}\n"
                f"🎯 Confidence: {result['confidence_percent']}%\n"
                f"📄 Certificate: {certificate_number}\n\n"
                "✅ Your KISANSETU inventory has been updated.")

    return out({
        "ok": True,
        "crop": crop,
        "quantity": quantity,
        "unit": unit,
        "grade": result["grade"],
        "confidence_percent": result["confidence_percent"],
        "detected_class": detected_class,
        "detected_crop": detected_crop,
        "verification_status": verification_status,
        "certificate_status": certificate_status,
        "certificate_number": certificate_number,
    })


def process_payload(payload):
    """Walk a webhook payload. Ignores status callbacks and unknown types."""
    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            value = change.get("value", {}) or {}

            if value.get("statuses"):
                log("WHATSAPP", f"Status callback ignored "
                                f"({len(value['statuses'])} update(s))")
                continue

            messages = value.get("messages") or []
            if not messages:
                continue

            contacts = value.get("contacts") or []
            profile_name = ""
            if contacts:
                profile_name = (contacts[0].get("profile") or {}).get("name", "")

            for message in messages:
                sender = message.get("from")
                mtype = message.get("type")
                if not sender:
                    continue
                log("WHATSAPP", f"Incoming message from={sender} type={mtype}")
                try:
                    if mtype == "text":
                        handle_text(sender, profile_name,
                                    (message.get("text") or {}).get("body", ""))
                    elif mtype == "image":
                        media_id = (message.get("image") or {}).get("id")
                        if media_id:
                            handle_image(sender, profile_name, media_id)
                    else:
                        whatsapp_send_text(sender,
                            "KISANSETU accepts text and photos.\n\n"
                            "Send: I have 30 kg rice\n"
                            "Then send a photo of the produce.")
                except Exception as e:
                    log("WHATSAPP", f"Handler error: {type(e).__name__}: {e}")


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
@router.get("/webhook", response_class=PlainTextResponse)
def verify_webhook(request: Request):
    """Meta's subscription handshake. Must echo hub.challenge as plain text."""
    p = request.query_params
    if p.get("hub.mode") == "subscribe" and p.get("hub.verify_token") == WHATSAPP_VERIFY_TOKEN:
        log("WHATSAPP", "Webhook verification succeeded")
        return PlainTextResponse(p.get("hub.challenge", ""))
    log("WHATSAPP", "Webhook verification failed: token mismatch")
    raise HTTPException(403, "Verification failed")


@router.post("/webhook")
async def receive_webhook(request: Request, background: BackgroundTasks):
    """Acknowledge immediately; YOLO and media download run in the background."""
    try:
        payload = await request.json()
    except Exception:
        return {"status": "ignored"}
    background.add_task(process_payload, payload)
    return {"status": "received"}


def get_user_dep():
    # Late import mirrors innovation_api/chatbot_api and avoids a circular import.
    from app import user
    return user


@router.get("/api/whatsapp/status")
def whatsapp_status(u=Depends(get_user_dep())):
    return {
        "configured": bool(WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID),
        "phone_number_id_set": bool(WHATSAPP_PHONE_NUMBER_ID),
        "verify_token_set": bool(WHATSAPP_VERIFY_TOKEN),
        "graph_version": GRAPH_VERSION,
    }


@router.get("/api/whatsapp/inventory")
def whatsapp_inventory(u=Depends(get_user_dep())):
    """Crops this farmer declared over WhatsApp, newest first."""
    c = db()
    if u["role"] == "admin":
        rows = c.execute(
            "SELECT * FROM whatsapp_inventory ORDER BY id DESC LIMIT 50").fetchall()
    else:
        digits = "".join(ch for ch in str(u.get("phone") or "") if ch.isdigit())
        local = digits[-10:] if len(digits) >= 10 else digits
        rows = c.execute(
            "SELECT * FROM whatsapp_inventory WHERE user_id=? OR "
            "(? != '' AND whatsapp_number LIKE ?) ORDER BY id DESC LIMIT 50",
            (u["id"], local, "%" + local)).fetchall()
    c.close()
    return {"count": len(rows), "items": [dict(r) for r in rows]}


# --------------------------------------------------------------------------
# On-stage simulator: exercises the exact same code path as the real Meta
# webhook (handle_text / process_produce_image) without needing WhatsApp,
# Meta, a token, or a public URL. Useful when the live integration is being
# demoed but a mobile network or an expired temporary Meta token is unreliable.
# --------------------------------------------------------------------------
@router.post("/api/whatsapp/simulate")
async def whatsapp_simulate(
    background: BackgroundTasks,
    message: str = Form(default=""),
    photo: UploadFile | None = File(default=None),
    u=Depends(get_user_dep()),
):
    """Acts as the signed-in farmer's own WhatsApp number for demo purposes."""
    digits = "".join(ch for ch in str(u.get("phone") or "") if ch.isdigit())
    sender = digits or f"demo{u['id']}"
    name = u.get("name", "Demo Farmer")

    if message.strip():
        background.add_task(handle_text, sender, name, message.strip())
        log("SIMULATE", f"Text queued for {sender}: {message.strip()!r}")

    if photo is not None and photo.filename:
        contents = await photo.read()
        ext = os.path.splitext(photo.filename)[1] or ".jpg"
        path = os.path.join(UPLOAD_DIR, f"sim_{u['id']}_{secrets.token_hex(4)}{ext}")
        with open(path, "wb") as f:
            f.write(contents)
        background.add_task(process_produce_image, sender, name, path)
        log("SIMULATE", f"Image queued for {sender}: {path}")

    if not message.strip() and (photo is None or not photo.filename):
        raise HTTPException(400, "Send a message, a photo, or both")

    return {"status": "queued", "sender": sender}
