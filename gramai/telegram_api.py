"""KISANSETU Telegram bot bridge.

Flow:
    farmer -> Telegram -> Bot API -> POST /telegram/webhook
        text  : parse crop + quantity, hold as a pending declaration; anything
                else goes to GRAM Saathi (chatbot_api.py)
        voice : Groq Whisper speech-to-text (voice_service.py), then handled
                exactly like text - plus a gTTS voice reply
        photo : download the largest photo size, run the EXISTING YOLO grader,
                issue the EXISTING certificate, write inventory, reply in chat

Reuses whatsapp_api.parse_produce_message / .process_produce_image, GRAM
Saathi's tool-calling assistant, and the existing voice/translation services -
no second parsing, grading, AI or speech pipeline. Telegram chat ids are not
phone numbers, so farmers are matched/created in their own namespace (phone
stored as "tg<chat_id>") instead of the WhatsApp digit-matching scheme.

Multilingual: every reply is answered in the farmer's language. GRAM Saathi
already replies in whatever language the question was asked in; the fixed
template messages (welcome, declaration confirmations, photo results) are
translated with i18n_service's cached, key-less machine translation. Once a
language is detected (from script, from Telegram's client language, or from
a voice note), it is saved on the farmer's profile so later replies default
to it even for ambiguous Latin-script text.

Webhook work runs in a background task so Telegram always gets its 200
quickly; Telegram retries the delivery if the response is slow.
"""
from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Depends
from functools import lru_cache
import os, secrets, sqlite3, bcrypt

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

# router and init_telegram_schema are defined before the cross-module imports
# below: those modules' own routes use FastAPI's Depends(get_user_dep())
# default-argument pattern, which runs at *import* time and can reenter
# app.py before it finishes loading. If that reentrant chain needs these two
# names while this module is still mid-import, they must already exist.
router = APIRouter(tags=["KISANSETU Telegram"])


def init_telegram_schema():
    """No dedicated schema: declarations reuse whatsapp_pending_produce /
    whatsapp_inventory (see store_declaration below) so process_produce_image,
    reused unmodified from whatsapp_api, finds them under the same key.
    Kept as a function so app.py's init call stays symmetric with the other
    bridges even though there is nothing extra to create here.
    """
    pass


from whatsapp_api import parse_produce_message, process_produce_image
from chatbot_api import answer_with_tools, detect_language, legacy_answer, save_turn, LANG_NAMES
from i18n_service import translate_batch
import voice_service

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "gramai.db")
UPLOAD_DIR = os.path.join(BASE, "uploads", "telegram")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --------------------------------------------------------------------------
# Config. Secrets come from the environment only and are never logged.
# --------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "").strip()
API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
FILE_URL = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}"

DEFAULT_STATE = "Tamil Nadu"
DEFAULT_DISTRICT = "Coimbatore"


def log(stage, msg):
    print(f"[{stage}] {msg}", flush=True)


def db():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    return c


# --------------------------------------------------------------------------
# Farmer identification. Telegram chat ids live in their own namespace
# ("tg<chat_id>") so they can never collide with a real 10-digit phone number
# that the WhatsApp bridge or in-app signup already matches on.
# --------------------------------------------------------------------------
def telegram_key(chat_id):
    return f"tg{chat_id}"


def resolve_farmer(chat_id, display_name=""):
    key = telegram_key(chat_id)
    c = db()
    row = c.execute("SELECT * FROM users WHERE phone=? LIMIT 1", (key,)).fetchone()
    if row:
        c.close()
        log("TELEGRAM", f"Farmer matched: id={row['id']} name={row['name']}")
        return dict(row)

    name = (display_name or "").strip() or f"Telegram Farmer {str(chat_id)[-4:]}"
    email = f"{key}@kisansetu.local"
    pw = bcrypt.hashpw(secrets.token_urlsafe(16).encode(), bcrypt.gensalt()).decode()
    try:
        cur = c.execute(
            "INSERT INTO users(name,email,password,role,district,state,phone) "
            "VALUES(?,?,?,?,?,?,?)",
            (name, email, pw, "farmer", DEFAULT_DISTRICT, DEFAULT_STATE, key),
        )
        c.commit()
        uid = cur.lastrowid
        row = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        log("TELEGRAM", f"Farmer auto-created: id={uid} name={name}")
        out = dict(row)
    except Exception as e:
        log("TELEGRAM", f"Farmer create failed: {e}")
        out = None
    c.close()
    return out


def get_lang(farmer):
    """The farmer's remembered reply language, or English if none is set yet."""
    lang = (farmer or {}).get("preferred_language")
    return lang if lang in LANG_NAMES else "en"


def set_lang(farmer_id, lang):
    """Remember a confidently-detected language so future replies default to
    it - a Telegram farmer typing in Latin script or sending a voice note
    still gets consistent replies without re-detecting every message.
    """
    if not farmer_id or lang not in LANG_NAMES:
        return
    c = db()
    c.execute("UPDATE users SET preferred_language=? WHERE id=?", (lang, farmer_id))
    c.commit()
    c.close()


# --------------------------------------------------------------------------
# Explicit language switching. Script/voice detection covers most messages,
# but a farmer typing in Latin script (or wanting a language different from
# what they just typed) needs a direct way to choose - "/language Tamil",
# "/language ta", or just the language's name on its own.
# --------------------------------------------------------------------------
_LANG_NAME_TO_CODE = {name.lower(): code for code, name in LANG_NAMES.items()}
_LANG_NATIVE_ALIASES = {
    "tamil": "ta", "தமிழ்": "ta", "hindi": "hi", "हिन्दी": "hi", "हिंदी": "hi",
    "telugu": "te", "తెలుగు": "te", "kannada": "kn", "ಕನ್ನಡ": "kn",
    "malayalam": "ml", "മലയാളം": "ml", "marathi": "mr", "मराठी": "mr",
    "bengali": "bn", "বাংলা": "bn", "gujarati": "gu", "ગુજરાતી": "gu",
    "punjabi": "pa", "ਪੰਜਾਬੀ": "pa", "urdu": "ur", "اردو": "ur", "english": "en",
}
_LANGUAGE_COMMAND_WORDS = ("/language", "/lang", "language", "change language",
                          "switch language", "select language")


def resolve_lang_arg(text):
    t = (text or "").strip().lower()
    if not t:
        return None
    return (t if t in LANG_NAMES else None) or _LANG_NAME_TO_CODE.get(t) \
        or _LANG_NATIVE_ALIASES.get(t)


def language_menu(lang):
    heading = _tr1(STATIC_MSG["language_menu_heading"], lang)
    names = sorted(LANG_NAMES.values())[:16]
    return f"{heading}\n\n" + "\n".join(f"• {n}" for n in names)


def try_language_command(chat_id, farmer, stripped):
    """Handles a language-switch request. Returns True if it handled the
    message (caller should stop processing it as a normal message).
    """
    low = stripped.lower()

    for prefix in ("/language ", "/lang "):
        if low.startswith(prefix):
            target = resolve_lang_arg(stripped.split(None, 1)[1] if " " in stripped else "")
            current = get_lang(farmer)
            if target:
                if farmer:
                    set_lang(farmer["id"], target)
                telegram_send_text(chat_id, _tr1(STATIC_MSG["language_updated"], target))
            else:
                telegram_send_text(chat_id, language_menu(current))
            return True

    if low in _LANGUAGE_COMMAND_WORDS:
        telegram_send_text(chat_id, language_menu(get_lang(farmer)))
        return True

    direct = resolve_lang_arg(stripped)
    if direct:
        if farmer:
            set_lang(farmer["id"], direct)
        telegram_send_text(chat_id, _tr1(STATIC_MSG["language_updated"], direct))
        return True

    return False


# --------------------------------------------------------------------------
# Reply translation. Static template strings and short labels are translated
# with the app's own free, cached machine-translation service - the same one
# the web interface uses - so a Telegram farmer sees the bot in their own
# language without a second translation provider. Dynamic values (numbers,
# certificate ids, crop names) are left untouched and spliced in afterwards,
# both because they read fine in any language and because translating a
# unique string per message (a certificate number) would defeat the cache.
# --------------------------------------------------------------------------
@lru_cache(maxsize=512)
def _tr1(text, lang):
    if lang == "en" or not text:
        return text
    try:
        return translate_batch([text], lang)[0]
    except Exception:
        return text


def _labels(lang, keys):
    return {k: _tr1(k, lang) for k in keys}


STATIC_MSG = {
    "welcome": (
        "🌾 Welcome to KISANSETU!\n\n"
        "Tell me what you have, then send a photo:\n"
        "• I have 30 kg rice\n"
        "• Wheat 50 kg\n"
        "• I harvested 2 tonnes maize\n\n"
        "After you declare a crop, send a clear photo of it to get a quality "
        "grade and certificate.\n\n"
        "You can also just ask me things, by text or voice note, like "
        "\"tomato prices today\" or \"should I sell now or wait?\" - GRAM "
        "Saathi will answer.\n\n"
        "Type /language to change the language I reply in."
    ),
    "unsupported_type": (
        "KISANSETU accepts text, voice notes and photos.\n\n"
        "Send: I have 30 kg rice\n"
        "Then send a photo of the produce."
    ),
    "no_farmer": "Could not link your Telegram account to KISANSETU.",
    "language_updated": "✅ Language updated. I will reply in this language from now on.",
    "language_menu_heading": "🌐 Reply with one of these language names, or /language followed "
                             "by the name, for example \"/language Tamil\":",
    "photo_download_failed": "❌ Could not download that photo. Please send it again.",
    "voice_download_failed": "❌ Could not download that voice note. Please try again.",
    "voice_not_understood": (
        "❌ Could not understand that voice note. Please try again, or type "
        "your message instead."
    ),
    "no_declaration": (
        "📸 Photo received, but I do not know the crop yet.\n\n"
        "Please send the details first, for example:\n"
        "• I have 30 kg rice"
    ),
    "yolo_failed": "❌ Photo received, but quality inspection failed.",
    "photo_error": "❌ Something went wrong processing that photo.",
}


def declared_message(parsed, lang):
    l = _labels(lang, ["KISANSETU inventory updated!", "Crop", "Quantity",
                       "Now send a clear photo of the produce to verify its quality."])
    return (
        f"✅ {l['KISANSETU inventory updated!']}\n\n"
        f"🌾 {l['Crop']}: {parsed['crop']}\n"
        f"⚖️ {l['Quantity']}: {parsed['quantity']:g} {parsed['unit']}\n\n"
        f"📸 {l['Now send a clear photo of the produce to verify its quality.']}"
    )


def result_message(result, lang):
    if not result or not result.get("ok"):
        reason = (result or {}).get("reason")
        if reason == "no_declaration":
            return _tr1(STATIC_MSG["no_declaration"], lang)
        if reason == "no_farmer":
            return _tr1(STATIC_MSG["no_farmer"], lang)
        if reason == "yolo_failed":
            msg = _tr1(STATIC_MSG["yolo_failed"], lang)
            err = (result or {}).get("error", "")
            return f"{msg}\n\n{err[:180]}" if err else msg
        return _tr1(STATIC_MSG["photo_error"], lang)

    if result.get("verification_status") == "mismatch":
        l = _labels(lang, ["Image verification result", "You declared", "Image suggests",
                           "Confidence", "Please check the crop information in KISANSETU."])
        return (
            f"⚠️ {l['Image verification result']}\n\n"
            f"{l['You declared']}: {result['crop']}\n"
            f"{l['Image suggests']}: {result.get('detected_crop')}\n"
            f"{l['Confidence']}: {result['confidence_percent']}%\n\n"
            f"{l['Please check the crop information in KISANSETU.']}"
        )

    l = _labels(lang, ["Image received and inspected!", "Crop", "Quantity", "Quality grade",
                       "Confidence", "Certificate", "Your KISANSETU inventory has been updated."])
    return (
        f"📸 {l['Image received and inspected!']}\n\n"
        f"🌾 {l['Crop']}: {result['crop']}\n"
        f"⚖️ {l['Quantity']}: {result['quantity']:g} {result['unit']}\n"
        f"🏅 {l['Quality grade']}: {result['grade']}\n"
        f"🎯 {l['Confidence']}: {result['confidence_percent']}%\n"
        f"📄 {l['Certificate']}: {result['certificate_number']}\n\n"
        f"✅ {l['Your KISANSETU inventory has been updated.']}"
    )


# --------------------------------------------------------------------------
# Telegram Bot API
# --------------------------------------------------------------------------
def telegram_send_text(chat_id, message):
    if not TELEGRAM_BOT_TOKEN:
        log("TELEGRAM", "Reply skipped: TELEGRAM_BOT_TOKEN is not configured")
        return None
    if not requests:
        return None
    try:
        r = requests.post(
            f"{API_URL}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=30,
        )
        log("TELEGRAM", f"Reply sent to {chat_id}: HTTP {r.status_code}")
        return r.status_code < 300
    except Exception as e:
        log("TELEGRAM", f"Reply failed: {e}")
        return None


def telegram_send_voice(chat_id, mp3_bytes):
    """Sent via sendAudio (not sendVoice): gTTS outputs mp3, and Telegram's
    sendVoice expects an ogg/OPUS voice note specifically. sendAudio accepts
    mp3 directly with no extra transcoding step or dependency.
    """
    if not TELEGRAM_BOT_TOKEN or not requests:
        return None
    try:
        r = requests.post(
            f"{API_URL}/sendAudio",
            data={"chat_id": chat_id},
            files={"audio": ("reply.mp3", mp3_bytes, "audio/mpeg")},
            timeout=60,
        )
        log("TELEGRAM", f"Voice reply sent to {chat_id}: HTTP {r.status_code}")
        return r.status_code < 300
    except Exception as e:
        log("TELEGRAM", f"Voice reply failed: {e}")
        return None


def download_telegram_file(file_id, default_ext=".bin"):
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
    if not requests:
        raise RuntimeError("requests is not installed")

    log("TELEGRAM", f"Requesting file metadata for id={file_id}")
    meta = requests.get(f"{API_URL}/getFile", params={"file_id": file_id}, timeout=30)
    meta.raise_for_status()
    file_path = (meta.json().get("result") or {}).get("file_path")
    if not file_path:
        raise RuntimeError("Telegram returned no file_path for this file id")

    log("TELEGRAM", "Downloading file bytes")
    resp = requests.get(f"{FILE_URL}/{file_path}", timeout=60)
    resp.raise_for_status()

    ext = os.path.splitext(file_path)[1] or default_ext
    path = os.path.join(UPLOAD_DIR, f"tg_{file_id}_{secrets.token_hex(4)}{ext}")
    with open(path, "wb") as f:
        f.write(resp.content)
    log("TELEGRAM", f"File saved ({len(resp.content)} bytes)")
    return path, resp.content


def download_telegram_photo(file_id):
    path, _content = download_telegram_file(file_id, ".jpg")
    return path


# --------------------------------------------------------------------------
# Message handlers
# --------------------------------------------------------------------------
def store_declaration(chat_id, display_name, parsed):
    log("INVENTORY", f"Parsed crop={parsed['crop']} "
                     f"quantity={parsed['quantity']} {parsed['unit']} "
                     f"({parsed['quantity_kg']} kg)")

    farmer = resolve_farmer(chat_id, display_name)
    key = telegram_key(chat_id)

    # Written into whatsapp_pending_produce (not a telegram-specific table) so
    # that process_produce_image - reused unmodified from whatsapp_api - finds
    # this declaration under the same key when the photo arrives.
    c = db()
    c.execute(
        "INSERT INTO whatsapp_pending_produce"
        "(whatsapp_number,crop,quantity,unit,quantity_kg,created_at) "
        "VALUES(?,?,?,?,?,datetime('now')) "
        "ON CONFLICT(whatsapp_number) DO UPDATE SET "
        "crop=excluded.crop,quantity=excluded.quantity,unit=excluded.unit,"
        "quantity_kg=excluded.quantity_kg,created_at=excluded.created_at",
        (key, parsed["crop"], parsed["quantity"], parsed["unit"], parsed["quantity_kg"]),
    )
    c.execute(
        "INSERT INTO whatsapp_inventory"
        "(user_id,whatsapp_number,crop,quantity,unit,quantity_kg,declared_crop,"
        "verification_status,certificate_status,created_at,updated_at) "
        "VALUES(?,?,?,?,?,?,?,'awaiting_image','pending',datetime('now'),datetime('now'))",
        (farmer["id"] if farmer else None, key, parsed["crop"],
         parsed["quantity"], parsed["unit"], parsed["quantity_kg"], parsed["crop"]),
    )
    c.commit()
    c.close()
    log("INVENTORY", f"Declaration stored for {key}")
    return farmer


def handle_text(chat_id, display_name, text, tg_lang_hint="en"):
    log("TELEGRAM", f"Text from {chat_id}: {text!r}")
    stripped = text.strip()

    farmer = resolve_farmer(chat_id, display_name)

    if try_language_command(chat_id, farmer, stripped):
        return

    lang = detect_language(stripped, get_lang(farmer) if farmer else tg_lang_hint)
    if farmer:
        set_lang(farmer["id"], lang)

    if stripped.lower() in ("/start", "/help"):
        telegram_send_text(chat_id, _tr1(STATIC_MSG["welcome"], lang))
        return

    parsed = parse_produce_message(text)
    if not parsed:
        ask_gram_saathi(chat_id, display_name, text, farmer=farmer, lang=lang)
        return

    store_declaration(chat_id, display_name, parsed)
    telegram_send_text(chat_id, declared_message(parsed, lang))


def ask_gram_saathi(chat_id, display_name, text, farmer=None, lang=None):
    """Anything that isn't a recognized crop declaration goes to GRAM Saathi -
    the same tool-calling assistant the in-app chat uses (chatbot_api.py) -
    so a Telegram farmer can ask about prices, forecasts or markets too, in
    their own language. Falls back to the keyword bot on any Groq failure,
    same as the app route. Returns the answer text so a voice caller can also
    speak it back.
    """
    farmer = farmer or resolve_farmer(chat_id, display_name)
    if not farmer:
        msg = _tr1(STATIC_MSG["no_farmer"], lang or "en")
        telegram_send_text(chat_id, msg)
        return msg

    session_id = telegram_key(chat_id)
    question = text.strip()
    lang = lang or detect_language(question, get_lang(farmer))
    state = farmer.get("state") or DEFAULT_STATE
    save_turn(farmer["id"], session_id, "user", question, lang)

    used = []
    try:
        answer, used, _ = answer_with_tools(farmer, question, lang, state, session_id)
        if not answer:
            raise RuntimeError("Empty completion")
    except Exception as e:
        log("TELEGRAM", f"GRAM Saathi failed, using fallback: {e}")
        answer = legacy_answer(farmer, question, lang, state)

    answer = answer[:4000]
    save_turn(farmer["id"], session_id, "assistant", answer, lang, ",".join(used))
    telegram_send_text(chat_id, answer)
    return answer


def handle_voice(chat_id, display_name, file_id, tg_lang_hint="en"):
    """Speech-to-text (Groq Whisper via voice_service.py), then handled
    exactly like a typed message, plus a spoken reply (gTTS) so voice-first
    farmers never need to read or type.
    """
    log("TELEGRAM", f"Voice from {chat_id}, file id={file_id}")
    farmer = resolve_farmer(chat_id, display_name)
    hint_lang = get_lang(farmer) if farmer else tg_lang_hint

    try:
        _path, content = download_telegram_file(file_id, ".ogg")
    except Exception as e:
        log("TELEGRAM", f"Voice download failed: {e}")
        telegram_send_text(chat_id, _tr1(STATIC_MSG["voice_download_failed"], hint_lang))
        return

    try:
        stt = voice_service.transcribe(content, "voice.ogg",
                                       hint_lang if hint_lang != "en" else None)
    except voice_service.VoiceError as e:
        log("TELEGRAM", f"Transcription failed: {e}")
        telegram_send_text(chat_id, _tr1(STATIC_MSG["voice_not_understood"], hint_lang))
        return

    text, lang = stt["text"], stt.get("language") or hint_lang
    log("TELEGRAM", f"Transcribed ({lang}): {text!r}")

    if try_language_command(chat_id, farmer, text.strip()):
        return

    if farmer:
        set_lang(farmer["id"], lang)

    parsed = parse_produce_message(text)
    if parsed:
        store_declaration(chat_id, display_name, parsed)
        reply = declared_message(parsed, lang)
        telegram_send_text(chat_id, reply)
    else:
        reply = ask_gram_saathi(chat_id, display_name, text, farmer=farmer, lang=lang)

    try:
        audio = voice_service.synthesize(reply, lang)
        telegram_send_voice(chat_id, audio)
    except voice_service.VoiceError as e:
        # Voice output is a bonus, not required - the text reply already went out.
        log("TELEGRAM", f"Voice reply skipped: {e}")


def handle_photo(chat_id, display_name, file_id):
    log("TELEGRAM", f"Photo from {chat_id}, file id={file_id}")
    farmer = resolve_farmer(chat_id, display_name)
    lang = get_lang(farmer)

    try:
        image_path = download_telegram_photo(file_id)
    except Exception as e:
        log("TELEGRAM", f"Photo download failed: {e}")
        telegram_send_text(chat_id, _tr1(STATIC_MSG["photo_download_failed"], lang))
        return

    key = telegram_key(chat_id)
    result = process_produce_image(key, display_name, image_path, notify=False)
    telegram_send_text(chat_id, result_message(result, lang))


def process_update(update):
    """Handle a single Telegram Update object."""
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return
    sender = message.get("from") or {}
    display_name = sender.get("first_name", "")
    tg_lang_hint = (sender.get("language_code") or "en").split("-")[0].lower()
    if tg_lang_hint not in LANG_NAMES:
        tg_lang_hint = "en"

    try:
        if "photo" in message and message["photo"]:
            # Telegram sends multiple resolutions; the last is the largest.
            file_id = message["photo"][-1]["file_id"]
            handle_photo(chat_id, display_name, file_id)
        elif "voice" in message:
            handle_voice(chat_id, display_name, message["voice"]["file_id"], tg_lang_hint)
        elif "audio" in message:
            handle_voice(chat_id, display_name, message["audio"]["file_id"], tg_lang_hint)
        elif "text" in message:
            handle_text(chat_id, display_name, message["text"], tg_lang_hint)
        else:
            farmer = resolve_farmer(chat_id, display_name)
            telegram_send_text(chat_id,
                _tr1(STATIC_MSG["unsupported_type"],
                     get_lang(farmer) if farmer else tg_lang_hint))
    except Exception as e:
        log("TELEGRAM", f"Handler error: {type(e).__name__}: {e}")


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
@router.post("/telegram/webhook")
async def receive_webhook(request: Request, background: BackgroundTasks):
    """Acknowledge immediately; YOLO and media download run in the background."""
    if TELEGRAM_WEBHOOK_SECRET:
        header = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if header != TELEGRAM_WEBHOOK_SECRET:
            raise HTTPException(403, "Invalid secret token")
    try:
        update = await request.json()
    except Exception:
        return {"status": "ignored"}
    background.add_task(process_update, update)
    return {"status": "received"}


def get_user_dep():
    # Late import mirrors whatsapp_api/chatbot_api and avoids a circular import.
    from app import user
    return user


@router.get("/api/telegram/status")
def telegram_status(u=Depends(get_user_dep())):
    return {
        "configured": bool(TELEGRAM_BOT_TOKEN),
        "webhook_secret_set": bool(TELEGRAM_WEBHOOK_SECRET),
    }


@router.post("/api/telegram/set-webhook")
def set_webhook(url: str, u=Depends(get_user_dep())):
    """Admin-only helper: register this server's public URL as the bot's webhook."""
    if u["role"] != "admin":
        raise HTTPException(403, "Admin only")
    if not TELEGRAM_BOT_TOKEN:
        raise HTTPException(400, "TELEGRAM_BOT_TOKEN is not configured")
    if not requests:
        raise HTTPException(500, "requests is not installed")
    payload = {"url": url}
    if TELEGRAM_WEBHOOK_SECRET:
        payload["secret_token"] = TELEGRAM_WEBHOOK_SECRET
    r = requests.post(f"{API_URL}/setWebhook", json=payload, timeout=30)
    return r.json()
