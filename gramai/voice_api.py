"""GRAM Saathi Voice - the server half of the hands-free voice agent.

The browser owns the screen: it navigates, highlights and fills forms by
running fixed task recipes (static/voice-agent.js). This module only does the
parts that need the server:

  POST /api/voice/interpret   what did the user mean? (intent + details, JSON)
  POST /api/voice/transcribe  speech to text with Groq Whisper, for browsers
                              without built-in speech recognition
  POST /api/voice/speak       text to speech (gTTS) for the chat widget
  GET  /api/voice/price       today's price for a crop, to suggest a sale price
  GET  /api/voice/status      is the AI side available?

The model never performs an action. It returns a structured intent; the
browser decides what to do, and anything that writes data asks the user to
confirm first. Permissions stay where they were: every write goes through
the normal app endpoints with the user's own token.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

from chatbot_api import (
    GROQ_API_KEY,
    GROQ_MODELS,
    LANG_NAMES,
    answer_with_tools,
    conn,
    get_user_dep,
    legacy_answer,
    save_turn,
)
import voice_service

router = APIRouter(prefix="/api/voice", tags=["GRAM Saathi Voice"])

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
STT_MODEL = os.environ.get("GROQ_STT_MODEL", "whisper-large-v3")

# Page keys exactly as app.js routes them, with what each page is for.
PAGES = {
    "farmer": {
        "dashboard": "home summary, income, notifications, recommendation",
        "crops": "my crops, add crop, quality certificates, price forecasts",
        "market": "buyer offers on my crops, accept / decline / negotiate, top buyers",
        "preorders": "pre-orders from buyers before harvest",
        "transport": "book a truck / shared transport",
        "paymentsRewards": "payments received, reward points",
        "profile": "my profile, bank details, KYC",
        "feedback": "give feedback",
        "grievances": "complaints and problems",
        "linkIndia": "markets in other states",
        "chats": "messages with buyers",
    },
    "buyer": {
        "dashboard": "home summary",
        "discover": "browse verified harvests to buy, quality certificates",
        "preorders": "my pre-order demands",
        "orders": "my orders and deliveries",
        "bulk": "bulk buying and shared logistics",
        "rewards": "reward points",
        "profile": "my profile",
        "feedback": "give feedback",
        "grievances": "complaints",
        "connectBuyers": "markets in other states",
        "chats": "messages with farmers",
    },
    "admin": {
        "dashboard": "platform overview",
        "usersKyc": "users and KYC checks",
        "markets": "markets",
        "payments": "payments",
        "grievances": "complaints",
        "stateAnalytics": "state analytics",
        "feedbackReq": "feedback and requirements",
        "securityActions": "security actions",
    },
}

NUMBER_WORDS = (
    "Spoken Indian quantity words: aadha/ardha/arai = 0.5, paav/pav = 0.25, "
    "sawa/savva = 1.25 (or +0.25), dedh/didh/deed = 1.5, dhai/adhai/adich = 2.5, "
    "saadhe X = X + 0.5, paune X = X - 0.25, ek = 1, do/don/rendu = 2, teen/moonu = 3, "
    "char/naalu = 4, paanch/anju = 5, das/daha/pathu = 10, bees/vees/irupathu = 20, "
    "tees/tis/muppathu = 30, chaalis = 40, pachaas = 50, sau/shambhar/nooru = 100, "
    "hazaar = 1000. 'kilo' means kg; 'quintal/kuintal/kwintal' = 100 kg; 'ton' = 1000 kg."
)

INTENTS = {
    "navigate": "open a page. Set page.",
    "sell_produce": "farmer has produce to sell / wants to add a crop or listing. "
                    "Set crop, quantity, unit if said.",
    "show_offers": "farmer wants to hear or see buyer offers.",
    "accept_offer": "accept a buyer offer. Set offer_ref.",
    "decline_offer": "decline a buyer offer. Set offer_ref.",
    "book_transport": "farmer needs a truck / transport. Set crop, pickup, dropoff if said.",
    "show_certificates": "see quality certificates / grade / validity.",
    "check_price": "asks the price or forecast of a crop. Set crop.",
    "read_page": "read the current screen aloud.",
    "tour": "wants to learn how to use the app / a tutorial / 'teach me'. "
            "Set topic: app, sell, offers, certificates, transport.",
    "change_language": "wants to talk in another language. Set language code.",
    "question": "any other question about their data, farming or the app.",
    "help": "asks what they can say.",
    "stop": "stop, cancel, bye, be quiet.",
    "logout": "log out / sign out.",
}

EXPECT_HELP = {
    "number": "value = the number said, as a JSON number (convert number words in "
              "any language, e.g. 'tees' -> 30, 'dedh' -> 1.5).",
    "quantity": "value = {\"quantity\": number, \"unit\": \"kg|quintal|tonne\"}. "
                "Default unit kg if none said.",
    "price": "value = rupees per quintal as a number, or \"market\" if they want "
             "today's market / best / suggested price.",
    "yesno": "value = true for yes / okay / do it / haan / ho / aamaam / sari, "
             "false for no / nahi / venda / cancel.",
    "crop": "value = crop name in English, e.g. Tomato, Onion.",
    "choice": "value = the index (1-based) of the option they picked from the "
              "options listed, or null.",
    "text": "value = the place or text they said, cleaned up, in English letters.",
}


# --------------------------------------------------------------------------
# Groq helpers
# --------------------------------------------------------------------------
def _groq_json(messages, max_tokens=500):
    if not GROQ_API_KEY or not requests:
        raise RuntimeError("GROQ_API_KEY is not configured")
    last = None
    for model in GROQ_MODELS:
        payload = {"model": model, "messages": messages, "temperature": 0,
                   "max_tokens": max_tokens,
                   "response_format": {"type": "json_object"}}
        if "gpt-oss" in model:
            payload["reasoning_effort"] = "low"
        try:
            r = requests.post(GROQ_CHAT_URL, json=payload, timeout=25, headers={
                "Authorization": "Bearer %s" % GROQ_API_KEY})
            if r.status_code != 200:
                last = "%s -> %s %s" % (model, r.status_code, r.text[:200])
                continue
            r.encoding = "utf-8"
            text = r.json()["choices"][0]["message"].get("content") or "{}"
            m = re.search(r"\{.*\}", text, re.S)
            return json.loads(m.group(0) if m else text)
        except Exception as e:
            last = "%s -> %s" % (model, e)
    raise RuntimeError(last or "Groq unavailable")


def _crop_names():
    names = set()
    try:
        c = conn()
        names |= {r["name"] for r in c.execute("SELECT name FROM crops")}
        c.close()
    except Exception:
        pass
    try:
        from whatsapp_api import CROP_ALIASES
        names |= set(CROP_ALIASES.values())
    except Exception:
        pass
    return sorted(names)


def canonical_crop(name):
    if not name:
        return None
    low = str(name).strip().lower()
    try:
        from whatsapp_api import CROP_ALIASES
        if low in CROP_ALIASES:
            return CROP_ALIASES[low]
    except Exception:
        pass
    for n in _crop_names():
        if n.lower() == low:
            return n
    return str(name).strip().title()


def to_quintal(quantity, unit):
    try:
        q = float(quantity)
    except Exception:
        return None
    unit = str(unit or "kg").lower()
    if unit.startswith("q"):
        return round(q, 3)
    if unit.startswith("t"):
        return round(q * 10, 3)
    if unit in ("g", "gram", "grams"):
        return round(q / 100000, 5)
    return round(q / 100, 3)  # kg


# --------------------------------------------------------------------------
# Interpret
# --------------------------------------------------------------------------
class InterpretIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    lang: str = Field(default="en", max_length=12)
    page: str = Field(default="dashboard", max_length=40)
    # When a task is waiting for one answer, e.g. {"type":"price"}.
    expect: Optional[dict] = None
    # Short description of what is on screen, e.g. the offers read out.
    screen: Optional[str] = Field(default=None, max_length=3000)
    session_id: str = Field(default="voice", max_length=64)


def _intent_prompt(u, body):
    role = u.get("role", "farmer")
    pages = PAGES.get(role, PAGES["farmer"])
    lines = [
        "You convert what a user said to GRAM AI (an Indian farm marketplace app) "
        "into JSON. Users are often farmers speaking Hindi, Marathi, Tamil, Telugu "
        "or other Indian languages, sometimes mixed with English, and speech "
        "recognition may be imperfect - infer the most likely meaning.",
        "User role: %s. Name: %s. Current page: %s. Interface language: %s."
        % (role, u.get("name"), body.page, LANG_NAMES.get(body.lang, body.lang)),
        "",
    ]
    if body.expect:
        etype = body.expect.get("type", "text")
        lines += [
            "The app just asked the user a question and is waiting for ONE answer.",
            "Question: %s" % body.expect.get("question", ""),
            "Answer type: %s. %s" % (etype, EXPECT_HELP.get(etype, EXPECT_HELP["text"])),
        ]
        if body.expect.get("options"):
            lines.append("Options: " + "; ".join(
                "%d) %s" % (i + 1, o) for i, o in enumerate(body.expect["options"])))
        lines += [
            "If the user clearly answered, return {\"kind\":\"answer\",\"value\":...}.",
            "If they instead asked to stop/cancel, return {\"kind\":\"command\","
            "\"intent\":\"stop\"}. If they asked to repeat, {\"kind\":\"command\","
            "\"intent\":\"repeat\"}. If they asked something unrelated, return "
            "{\"kind\":\"intent\", ...the intent object below...}. If it is "
            "unclear, return {\"kind\":\"unclear\"}.",
            "",
        ]
    lines += [
        "Intent object: {\"kind\":\"intent\",\"intent\":<one of the intents>, "
        "\"page\":<page key or null>, \"crop\":<English crop name or null>, "
        "\"quantity\":<number or null>, \"unit\":<kg|quintal|tonne or null>, "
        "\"price\":<number or null>, \"offer_ref\":<1-based offer number, crop name "
        "or buyer name, or null>, \"pickup\":<text or null>, \"dropoff\":<text or null>, "
        "\"topic\":<text or null>, \"language\":<language code or null>}",
        "Intents:",
    ]
    lines += ["- %s: %s" % (k, v) for k, v in INTENTS.items()]
    lines += ["", "Page keys for this role:"]
    lines += ["- %s: %s" % (k, v) for k, v in pages.items()]
    lines += [
        "",
        NUMBER_WORDS,
        "Known crops: " + ", ".join(_crop_names()),
        "Language codes: " + ", ".join("%s=%s" % kv for kv in LANG_NAMES.items()),
    ]
    if body.screen:
        lines += ["", "On screen now:", body.screen]
    lines.append("\nReturn only the JSON object.")
    return "\n".join(lines)


def _fallback_intent(text, role):
    """Keyword intent when Groq is unavailable. Deliberately small."""
    t = text.lower()
    table = [
        (("sell", "bech", "vik", "tamatar", "tomato", "onion", "pyaz", "kanda",
          "have", "hai", "kilo", "quintal"), {"intent": "sell_produce"}),
        (("offer", "buyer", "kharid", "khareed"), {"intent": "show_offers"}),
        (("price", "bhav", "rate", "daam", "dam", "kimat"), {"intent": "check_price"}),
        (("truck", "transport", "gaadi", "gadi", "vahan"), {"intent": "book_transport"}),
        (("certificate", "grade", "pramaan"), {"intent": "show_certificates"}),
        (("teach", "sikha", "tutorial", "how to", "kaise"), {"intent": "tour", "topic": "app"}),
        (("read", "padh", "suna"), {"intent": "read_page"}),
        (("help", "madad", "madat"), {"intent": "help"}),
    ]
    for words, intent in table:
        if any(w in t for w in words):
            if intent["intent"] == "sell_produce" and role != "farmer":
                continue
            m = re.search(r"(\d+(?:\.\d+)?)\s*(kg|kilo|quintal|qtl|tonne|ton)?", t)
            out = dict(intent, kind="intent")
            if m and intent["intent"] == "sell_produce":
                out["quantity"] = float(m.group(1))
                out["unit"] = (m.group(2) or "kg").replace("qtl", "quintal")
            return out
    for key in PAGES.get(role, {}):
        if key.lower() in t.replace(" ", ""):
            return {"kind": "intent", "intent": "navigate", "page": key}
    return {"kind": "intent", "intent": "question"}


@router.post("/interpret")
def interpret(body: InterpretIn, u=Depends(get_user_dep())):
    started = time.time()
    ai = True
    try:
        out = _groq_json([
            {"role": "system", "content": _intent_prompt(u, body)},
            {"role": "user", "content": body.text},
        ])
    except Exception:
        ai = False
        out = _fallback_intent(body.text, u.get("role"))

    if not isinstance(out, dict):
        out = {"kind": "unclear"}
    out.setdefault("kind", "intent")

    # Normalise the details the browser relies on.
    if out.get("crop"):
        out["crop"] = canonical_crop(out["crop"])
    if out.get("quantity") is not None:
        out["quantity_qtl"] = to_quintal(out["quantity"], out.get("unit"))
    if out.get("page") and out["page"] not in PAGES.get(u.get("role"), {}):
        out["page"] = None
    if out.get("kind") == "answer" and isinstance(out.get("value"), dict) \
            and "quantity" in out["value"]:
        v = out["value"]
        v["quantity_qtl"] = to_quintal(v.get("quantity"), v.get("unit"))
    if out.get("kind") == "answer" and (body.expect or {}).get("type") == "crop":
        out["value"] = canonical_crop(out.get("value"))

    # Free questions get a real answer from the existing tool-using assistant,
    # so "what is the onion price in Dindigul" reads live data.
    if out.get("kind") == "intent" and out.get("intent") in ("question", "check_price"):
        question = body.text
        if out.get("intent") == "check_price" and out.get("crop"):
            question = "%s (Give today's price and the best market for %s, very briefly.)" \
                       % (body.text, out["crop"])
        voice_rule = ("\n\n(Answer for a voice assistant: at most 3 short spoken sentences, "
                      "no markdown, no tables, no bullet points.)")
        try:
            if not ai:
                raise RuntimeError("offline")
            answer, used, _ = answer_with_tools(u, question + voice_rule, body.lang,
                                                u.get("state") or "Tamil Nadu",
                                                body.session_id)
        except Exception:
            answer = legacy_answer(u, question, body.lang, u.get("state") or "Tamil Nadu")
        out["answer"] = re.sub(r"[*#`|_>]+", " ", answer or "").strip()
        try:
            save_turn(u["id"], body.session_id, "user", body.text, body.lang)
            save_turn(u["id"], body.session_id, "assistant", out["answer"], body.lang)
        except Exception:
            pass

    out["ai"] = ai
    out["ms"] = int((time.time() - started) * 1000)
    return out


# --------------------------------------------------------------------------
# Speech to text (Groq Whisper)
# --------------------------------------------------------------------------
@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...), lang: Optional[str] = Form(None),
                     language: Optional[str] = Form(None), u=Depends(get_user_dep())):
    # The voice agent sends "lang", the chat widget's mic sends "language".
    data = await audio.read()
    if not data:
        raise HTTPException(400, "Empty recording")
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(400, "Recording too long")
    hint = (language or lang or "").split("-")[0].lower() or None
    try:
        return voice_service.transcribe(data, audio.filename or "speech.webm", hint)
    except voice_service.VoiceError as e:
        raise HTTPException(400, str(e))


# --------------------------------------------------------------------------
# Text to speech (gTTS), used by the chat widget to read answers aloud
# --------------------------------------------------------------------------
class SpeakIn(BaseModel):
    text: str = Field(min_length=1, max_length=1200)
    lang: str = Field(default="en", max_length=12)


@router.post("/speak")
def speak(body: SpeakIn, u=Depends(get_user_dep())):
    try:
        audio = voice_service.synthesize(body.text, body.lang)
    except voice_service.VoiceError as e:
        raise HTTPException(400, str(e))
    return Response(content=audio, media_type="audio/mpeg",
                    headers={"Cache-Control": "no-store"})


# --------------------------------------------------------------------------
# Price suggestion for the sell task
# --------------------------------------------------------------------------
@router.get("/price")
def price(crop: str, u=Depends(get_user_dep())):
    crop = canonical_crop(crop)
    state = u.get("state") or "Tamil Nadu"
    c = conn()
    latest = c.execute("SELECT max(price_date) d FROM prices WHERE lower(crop)=lower(?)",
                       (crop,)).fetchone()["d"]
    if not latest:
        c.close()
        return {"crop": crop, "found": False}
    rows = c.execute(
        "SELECT m.name market, m.state, p.modal_price FROM prices p "
        "JOIN markets m ON m.id=p.market_id WHERE lower(p.crop)=lower(?) "
        "AND p.price_date=? ORDER BY (m.state=?) DESC, p.modal_price DESC",
        (crop, latest, state)).fetchall()
    c.close()
    in_state = [r for r in rows if r["state"] == state] or rows
    avg = sum(r["modal_price"] for r in in_state) / len(in_state)
    best = max(in_state, key=lambda r: r["modal_price"])
    return {"crop": crop, "found": True, "date": latest, "state": in_state[0]["state"],
            "average": round(avg), "best": round(best["modal_price"]),
            "best_market": best["market"], "suggested": int(round(avg / 10.0) * 10)}


@router.get("/status")
def status(u=Depends(get_user_dep())):
    return {"ai": bool(GROQ_API_KEY), "server_stt": bool(GROQ_API_KEY),
            "stt_model": STT_MODEL, "role": u.get("role")}
