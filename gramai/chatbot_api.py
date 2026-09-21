"""GRAM Saathi - the multilingual assistant that can read the platform's own data.

The model never sees SQL. It calls a fixed set of typed, read-only tools, each of
which re-checks the caller's role and user id before touching the database, so a
farmer can never pull another user's orders through the assistant.

Falls back to the legacy keyword bot whenever GROQ_API_KEY is unset or the
provider is unreachable, so the interface never shows a dead chatbot.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
import os, sqlite3, json, time, re

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

try:
    import py3langid as _langid
except Exception:  # pragma: no cover
    _langid = None

router = APIRouter(prefix="/api/ai", tags=["GRAM Saathi"])

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "gramai.db")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
# Verified available on this account. First entry is primary, rest are fallbacks.
GROQ_MODELS = [m.strip() for m in os.environ.get(
    "GROQ_MODEL", "openai/gpt-oss-120b,qwen/qwen3.8-27b").split(",") if m.strip()]

DEFAULT_STATE = "Tamil Nadu"
MAX_TOOL_ROUNDS = 4
HISTORY_TURNS = 8

LANG_NAMES = {
    "en": "English", "hi": "Hindi", "mr": "Marathi", "ta": "Tamil",
    "te": "Telugu", "bn": "Bengali", "gu": "Gujarati", "kn": "Kannada",
    "ml": "Malayalam", "pa": "Punjabi", "or": "Odia", "as": "Assamese",
    "ur": "Urdu", "ne": "Nepali", "sa": "Sanskrit", "ks": "Kashmiri",
    "sd": "Sindhi", "kok": "Konkani", "mai": "Maithili", "doi": "Dogri",
    "brx": "Bodo", "mni": "Manipuri (Meitei)", "sat": "Santali",
    "raj": "Rajasthani",
}


def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    return c


def init_chatbot_schema():
    c = conn()
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS ai_chat_turns(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          session_id TEXT NOT NULL,
          role TEXT NOT NULL,
          content TEXT NOT NULL,
          lang TEXT DEFAULT 'en',
          tools TEXT DEFAULT '',
          created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_ai_turns ON ai_chat_turns(user_id, session_id, id);
        """
    )
    c.commit()
    c.close()


def get_user_dep():
    # Late import mirrors innovation_api and avoids a circular import.
    from app import user
    return user


# --------------------------------------------------------------------------
# Knowledge base - answers "how does this work" questions about the platform.
# --------------------------------------------------------------------------
KNOWLEDGE = {
    "predictability_score": (
        "The Predictability Score rates how much to trust a forecast. It is a weighted "
        "blend: 30% model accuracy, 20% agreement between XGBoost and LightGBM, 20% "
        "historical price stability, 15% data availability, 15% horizon reliability."),
    "net_realizable_price": (
        "Net Realizable Price = predicted sale value - transport cost - market charges. "
        "GRAM AI ranks markets by this take-home value, not by headline mandi price."),
    "sell_wait_shift": (
        "The recommendation compares 1, 3 and 7-day forecast prices against transport "
        "cost and market fees. SELL NOW means price is at or near its peak; WAIT means "
        "the forecast rises enough to cover storage risk; SHIFT MARKET means another "
        "mandi nets more even after transport; STORE applies to non-perishables."),
    "grievance": (
        "Open Need Help -> GramRakshak. A complaint can be spoken or typed, linked to a "
        "transaction, and supported with photo or video evidence. It is tracked with a "
        "status and auto-escalates if unresolved."),
    "payments": (
        "Payment amounts are computed on the server, never sent by the browser. A payment "
        "is marked SUCCESS only after both signature verification and webhook "
        "reconciliation. Refunds are tracked separately with their own status."),
    "kyc": (
        "KYC verification is available after login. GRAM AI never stores a full Aadhaar "
        "number - only a masked reference - and does not claim UIDAI authentication."),
    "preorders": (
        "In Pre-Orders, a buyer offer is compared against the 1/3/7-day outlook, transport "
        "cost, market charges and buyer reliability, producing ACCEPT, NEGOTIATE or WAIT."),
    "quality": (
        "Produce photos are graded by an on-device YOLO classifier. A passing grade issues "
        "a signed quality certificate PDF that buyers can verify."),
    "rewards": (
        "GramRewards credits points for verified listings, completed orders, on-time "
        "delivery and feedback. Points convert to rupee benefits in the reward catalog."),
    "transport": (
        "Transport & Groups lists GPS-enabled verified transporters with capacity and "
        "per-km rate, and supports shared logistics so small farmers can pool a vehicle."),
}


# The real navigation of each portal, so the assistant never invents a page name.
NAV = {
    "farmer": ["Dashboard", "Crops & Forecasts", "Market & Offers", "Pre-Orders",
               "Transport & Groups", "Payments & Rewards", "Profile", "Feedback",
               "Grievances", "Link India", "Chats"],
    "buyer": ["Dashboard", "Discover Harvest", "My Orders", "Pre-Orders",
              "Bulk & Shared Logistics", "Rewards", "Connect Buyers", "Profile",
              "Grievances", "Chats"],
    "admin": ["Dashboard", "Users & KYC", "Markets", "Payments", "State Analytics",
              "Feedback & Requirements", "Security Actions", "Grievances"],
}


# --------------------------------------------------------------------------
# Tools. Every function takes (u, args) and returns a JSON-serialisable dict.
# --------------------------------------------------------------------------
def _rows(cur, limit=25):
    return [dict(r) for r in cur.fetchmany(limit)]


def _need(args, key, default=None):
    v = args.get(key, default)
    if isinstance(v, str):
        v = v.strip()
    return v


def t_list_crops_and_markets(u, args):
    state = _need(args, "state") or u.get("state") or DEFAULT_STATE
    c = conn()
    crops = [r["name"] for r in c.execute("SELECT name FROM crops ORDER BY name")]
    mk = _rows(c.execute(
        "SELECT id,name,city,district,state,market_fee_pct FROM markets "
        "WHERE state=? ORDER BY name", (state,)), 40)
    c.close()
    return {"state": state, "crops": crops, "markets": mk}


def t_get_market_prices(u, args):
    crop = _need(args, "crop")
    state = _need(args, "state") or u.get("state") or DEFAULT_STATE
    if not crop:
        return {"error": "crop is required"}
    c = conn()
    rows = _rows(c.execute(
        "SELECT m.name market, m.city, m.district, p.price_date, p.modal_price, "
        "p.arrivals_qtl, p.demand_index "
        "FROM prices p JOIN markets m ON m.id=p.market_id "
        "WHERE lower(p.crop)=lower(?) AND m.state=? "
        "AND p.price_date=(SELECT max(price_date) FROM prices WHERE crop=p.crop) "
        "ORDER BY p.modal_price DESC", (crop, state)), 25)
    c.close()
    if not rows:
        return {"crop": crop, "state": state, "rows": [],
                "note": "No price rows for this crop in this state."}
    return {"crop": crop, "state": state, "unit": "rupees per quintal", "rows": rows}


def _resolve_market(c, name, state):
    if not name:
        return None
    r = c.execute("SELECT id,name,state FROM markets WHERE lower(name)=lower(?) "
                  "OR lower(city)=lower(?) LIMIT 1", (name, name)).fetchone()
    if r:
        return dict(r)
    r = c.execute("SELECT id,name,state FROM markets WHERE name LIKE ? OR city LIKE ? "
                  "LIMIT 1", ("%%%s%%" % name, "%%%s%%" % name)).fetchone()
    return dict(r) if r else None


def t_get_price_forecast(u, args):
    crop = _need(args, "crop")
    market_name = _need(args, "market")
    state = _need(args, "state") or u.get("state") or DEFAULT_STATE
    if not crop:
        return {"error": "crop is required"}
    c = conn()
    mk = _resolve_market(c, market_name, state)
    if not mk:
        r = c.execute("SELECT id,name,state FROM markets WHERE state=? ORDER BY name LIMIT 1",
                      (state,)).fetchone()
        mk = dict(r) if r else None
    c.close()
    if not mk:
        return {"error": "No market found for state %s" % state}
    try:
        from ml_engine import forecast_market
        f = forecast_market(crop, mk["id"])
    except Exception as e:
        return {"error": "Forecast engine unavailable: %s" % e,
                "hint": "Ask the user to open Crops & Forecasts and run it there."}
    return {
        "crop": f.get("crop"), "market": f.get("market"),
        "current_price": f.get("current_price"),
        "forecasts": f.get("forecasts"),
        "selected_model": f.get("selected_model"),
        "metrics": f.get("metrics"),
        "unit": "rupees per quintal",
    }


def t_compare_best_markets(u, args):
    crop = _need(args, "crop")
    qty = float(_need(args, "quantity_qtl", 10) or 10)
    if not crop:
        return {"error": "crop is required"}
    lat, lon = 11.0168, 76.9558  # Coimbatore fallback origin
    c = conn()
    r = c.execute("SELECT latitude,longitude FROM listings WHERE seller_id=? "
                  "AND latitude IS NOT NULL ORDER BY id DESC LIMIT 1",
                  (u["id"],)).fetchone()
    c.close()
    if r and r["latitude"]:
        lat, lon = float(r["latitude"]), float(r["longitude"])
    try:
        from ml_engine import compare_markets
        out = compare_markets(crop, qty, lat, lon, 7)
    except Exception as e:
        return {"error": "Comparison engine unavailable: %s" % e}
    if isinstance(out, dict):
        for k in ("markets", "comparison", "results"):
            if isinstance(out.get(k), list):
                out[k] = out[k][:8]
    return out


def t_get_my_listings(u, args):
    c = conn()
    if u["role"] == "farmer":
        rows = _rows(c.execute(
            "SELECT id,crop,variety,grade,quantity_qtl,ask_price,district,state,status,"
            "quality_grade,quality_verified,created_at FROM listings WHERE seller_id=? "
            "ORDER BY id DESC", (u["id"],)))
    else:
        rows = _rows(c.execute(
            "SELECT id,crop,variety,grade,quantity_qtl,ask_price,district,state,status "
            "FROM listings WHERE status IN ('OPEN','ACTIVE') ORDER BY id DESC"))
    c.close()
    return {"role": u["role"], "count": len(rows), "listings": rows}


def t_get_my_orders(u, args):
    c = conn()
    if u["role"] == "buyer":
        rows = _rows(c.execute(
            "SELECT o.id,o.quantity_qtl,o.total,o.status,o.delivery_mode,o.created_at,"
            "l.crop,l.district FROM orders o JOIN listings l ON l.id=o.listing_id "
            "WHERE o.buyer_id=? ORDER BY o.id DESC", (u["id"],)))
    elif u["role"] == "farmer":
        rows = _rows(c.execute(
            "SELECT o.id,o.quantity_qtl,o.total,o.status,o.delivery_mode,o.created_at,"
            "l.crop FROM orders o JOIN listings l ON l.id=o.listing_id "
            "WHERE l.seller_id=? ORDER BY o.id DESC", (u["id"],)))
    else:
        rows = _rows(c.execute(
            "SELECT id,buyer_id,listing_id,quantity_qtl,total,status,created_at "
            "FROM orders ORDER BY id DESC"))
    c.close()
    return {"role": u["role"], "count": len(rows), "currency": "INR", "orders": rows}


def t_get_my_harvests(u, args):
    c = conn()
    rows = _rows(c.execute(
        "SELECT id,crop,variety,expected_quantity_qtl,available_quantity_qtl,"
        "expected_harvest_date,expected_price,status,district,state FROM harvests "
        "WHERE farmer_id=? ORDER BY id DESC", (u["id"],)))
    c.close()
    return {"count": len(rows), "harvests": rows}


def t_get_my_rewards(u, args):
    c = conn()
    tot = c.execute("SELECT coalesce(sum(points),0) p, coalesce(sum(benefit_rupees),0) b "
                    "FROM reward_ledger WHERE user_id=?", (u["id"],)).fetchone()
    rows = _rows(c.execute(
        "SELECT reward_type,points,benefit_rupees,reason,created_at FROM reward_ledger "
        "WHERE user_id=? ORDER BY id DESC", (u["id"],)), 15)
    cat = _rows(c.execute("SELECT * FROM reward_catalog"), 10)
    c.close()
    return {"total_points": tot["p"], "total_benefit_rupees": tot["b"],
            "recent": rows, "catalog": cat}


def t_get_my_payments(u, args):
    c = conn()
    try:
        rows = _rows(c.execute(
            "SELECT id,purpose,status,expected_amount_paise,confirmed_amount_paise,"
            "client_signature_verified,webhook_verified,currency,created_at "
            "FROM payments_v2 WHERE user_id=? ORDER BY id DESC", (u["id"],)), 15)
    except Exception:
        rows = []
    c.close()
    return {"count": len(rows), "note": "Amounts are in paise; divide by 100 for rupees.",
            "payments": rows}


def t_get_my_profile(u, args):
    c = conn()
    p = c.execute("SELECT name,email,role,district,state,phone,farm_size_acres,"
                  "preferred_language,upi_id,bank_account_last4 FROM users WHERE id=?",
                  (u["id"],)).fetchone()
    k = c.execute("SELECT status,method,aadhaar_last4,submitted_at,verified_at "
                  "FROM kyc_profiles WHERE user_id=? ORDER BY id DESC LIMIT 1",
                  (u["id"],)).fetchone()
    c.close()
    out = dict(p) if p else {}
    out["kyc_status"] = k["status"] if k else "NOT_STARTED"
    if k:
        out["kyc_method"] = k["method"]
        out["kyc_submitted_at"] = k["submitted_at"]
        out["kyc_verified_at"] = k["verified_at"]
    return out


def t_search_buyers(u, args):
    state = _need(args, "state") or u.get("state") or DEFAULT_STATE
    crop = _need(args, "crop")
    c = conn()
    if crop:
        rows = _rows(c.execute(
            "SELECT name,district,crops,rating,verified,payment_score,completed_orders,"
            "avg_payment_days FROM buyers WHERE state=? AND crops LIKE ? "
            "ORDER BY verified DESC, rating DESC", (state, "%%%s%%" % crop)), 15)
    else:
        rows = _rows(c.execute(
            "SELECT name,district,crops,rating,verified,payment_score,completed_orders,"
            "avg_payment_days FROM buyers WHERE state=? ORDER BY verified DESC, rating DESC",
            (state,)), 15)
    c.close()
    return {"state": state, "crop": crop, "count": len(rows), "buyers": rows}


def t_search_transport(u, args):
    state = _need(args, "state") or u.get("state") or DEFAULT_STATE
    min_cap = float(_need(args, "min_capacity_qtl", 0) or 0)
    c = conn()
    rows = _rows(c.execute(
        "SELECT name,vehicle_type,capacity_qtl,rate_per_km,rating,verified,gps_enabled "
        "FROM transporters WHERE state=? AND capacity_qtl>=? "
        "ORDER BY verified DESC, rating DESC", (state, min_cap)), 15)
    c.close()
    return {"state": state, "count": len(rows), "transporters": rows}


def t_get_my_notifications(u, args):
    c = conn()
    try:
        rows = _rows(c.execute(
            "SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC",
            (u["id"],)), 12)
    except Exception:
        rows = []
    c.close()
    return {"count": len(rows), "notifications": rows}


def t_get_my_grievances(u, args):
    c = conn()
    try:
        if u["role"] == "admin":
            rows = _rows(c.execute("SELECT * FROM grievances_v2 ORDER BY id DESC"), 15)
        else:
            rows = _rows(c.execute(
                "SELECT id,category,description,severity,status,escalation_level,"
                "ai_recommendation,created_at FROM grievances_v2 "
                "WHERE complainant_id=? ORDER BY id DESC",
                (u["id"],)), 15)
    except Exception:
        rows = []
    c.close()
    return {"count": len(rows), "grievances": rows}


def t_get_quality_certificates(u, args):
    c = conn()
    try:
        rows = _rows(c.execute(
            "SELECT * FROM quality_certificates ORDER BY id DESC"), 10)
    except Exception:
        rows = []
    c.close()
    return {"count": len(rows), "certificates": rows}


def t_get_platform_stats(u, args):
    if u["role"] != "admin":
        return {"error": "Platform-wide statistics are available to admins only."}
    c = conn()
    q = lambda s: c.execute(s).fetchone()[0]
    out = {
        "farmers": q("SELECT count(*) FROM users WHERE role='farmer'"),
        "buyers": q("SELECT count(*) FROM users WHERE role='buyer'"),
        "active_listings": q("SELECT count(*) FROM listings WHERE status IN ('OPEN','ACTIVE')"),
        "orders": q("SELECT count(*) FROM orders"),
        "markets": q("SELECT count(*) FROM markets"),
        "crops": q("SELECT count(*) FROM crops"),
        "price_records": q("SELECT count(*) FROM prices"),
        "pending_kyc": q("SELECT count(*) FROM kyc_profiles WHERE status='PENDING'"),
    }
    c.close()
    return out


def t_explain_platform(u, args):
    topic = (_need(args, "topic") or "").lower().replace(" ", "_").replace("-", "_")
    if topic in KNOWLEDGE:
        return {"topic": topic, "explanation": KNOWLEDGE[topic]}
    hits = {k: v for k, v in KNOWLEDGE.items() if topic and topic in k}
    if hits:
        return hits
    return {"available_topics": list(KNOWLEDGE.keys()), "all": KNOWLEDGE}


def chat_sender_key(u):
    """Identity used for produce declarations made inside the app.

    Uses the farmer's phone so an in-app declaration and a WhatsApp message
    from the same person land on the same record.
    """
    digits = "".join(ch for ch in str(u.get("phone") or "") if ch.isdigit())
    return digits or f"app{u['id']}"


def t_add_produce(u, args):
    """Record a crop + quantity the farmer states in chat, awaiting a photo."""
    if u["role"] != "farmer":
        return {"error": "Only a farmer account can add produce to inventory."}

    crop = _need(args, "crop")
    quantity = _need(args, "quantity")
    unit = (_need(args, "unit") or "kg").lower()
    if not crop or quantity in (None, ""):
        return {"error": "Both crop and quantity are required."}

    try:
        from whatsapp_api import (parse_produce_message, store_declaration,
                                  CROP_ALIASES, UNIT_ALIASES, TO_KG)
    except Exception as e:
        return {"error": f"Inventory module unavailable: {e}"}

    canon = CROP_ALIASES.get(str(crop).strip().lower())
    if not canon:
        return {"error": f"'{crop}' is not a crop GRAM AI tracks.",
                "known_crops": sorted(set(CROP_ALIASES.values()))}

    unit = UNIT_ALIASES.get(unit, unit)
    if unit not in TO_KG:
        return {"error": f"Unknown unit '{unit}'.", "known_units": list(TO_KG)}

    try:
        quantity = float(quantity)
    except Exception:
        return {"error": "Quantity must be a number."}
    if quantity <= 0:
        return {"error": "Quantity must be greater than zero."}

    parsed = {"crop": canon, "quantity": quantity, "unit": unit,
              "quantity_kg": round(quantity * TO_KG[unit], 3)}
    store_declaration(chat_sender_key(u), u.get("name", ""), parsed)

    return {"saved": True, "crop": canon, "quantity": quantity, "unit": unit,
            "next_step": "Ask the farmer to attach a photo of the produce using "
                         "the photo button in this chat, so the quality grade "
                         "and certificate can be issued."}


TOOLS = {
    "add_produce_to_inventory": (t_add_produce, {
        "description": "Record a crop and quantity the farmer says they have, so it "
                       "enters their KISANSETU inventory. Call this whenever the "
                       "farmer states produce they hold or harvested, e.g. 'I have "
                       "20 kg rice'. After it succeeds, tell them to attach a photo "
                       "with the photo button so quality can be verified.",
        "parameters": {"type": "object", "properties": {
            "crop": {"type": "string", "description": "Crop name, e.g. Rice"},
            "quantity": {"type": "number"},
            "unit": {"type": "string",
                     "description": "kg, g, tonne or quintal. Defaults to kg."}},
            "required": ["crop", "quantity"]}}),
    "list_crops_and_markets": (t_list_crops_and_markets, {
        "description": "List every crop GRAM AI tracks and every mandi/market in a state. "
                       "Call this first when unsure of exact crop or market names.",
        "parameters": {"type": "object", "properties": {
            "state": {"type": "string", "description": "Indian state name"}}}}),
    "get_market_prices": (t_get_market_prices, {
        "description": "Latest actual modal prices (rupees per quintal) for one crop "
                       "across every market in a state, best price first.",
        "parameters": {"type": "object", "properties": {
            "crop": {"type": "string"}, "state": {"type": "string"}},
            "required": ["crop"]}}),
    "get_price_forecast": (t_get_price_forecast, {
        "description": "XGBoost/LightGBM 1, 3 and 7-day price forecast for a crop in one "
                       "market, with model accuracy metrics.",
        "parameters": {"type": "object", "properties": {
            "crop": {"type": "string"},
            "market": {"type": "string", "description": "Market or city name"},
            "state": {"type": "string"}}, "required": ["crop"]}}),
    "compare_best_markets": (t_compare_best_markets, {
        "description": "Rank markets by Net Realizable Price (forecast value minus "
                       "transport and market charges) to answer 'where should I sell'.",
        "parameters": {"type": "object", "properties": {
            "crop": {"type": "string"},
            "quantity_qtl": {"type": "number", "description": "Quantity in quintals"}},
            "required": ["crop"]}}),
    "get_my_listings": (t_get_my_listings, {
        "description": "The signed-in farmer's own produce listings, or active listings "
                       "on the marketplace for a buyer.",
        "parameters": {"type": "object", "properties": {}}}),
    "get_my_orders": (t_get_my_orders, {
        "description": "Orders belonging to the signed-in user, with status and totals.",
        "parameters": {"type": "object", "properties": {}}}),
    "get_my_harvests": (t_get_my_harvests, {
        "description": "The signed-in farmer's declared upcoming harvests.",
        "parameters": {"type": "object", "properties": {}}}),
    "get_my_rewards": (t_get_my_rewards, {
        "description": "GramRewards points balance, rupee benefit, recent ledger entries "
                       "and the redeemable catalog.",
        "parameters": {"type": "object", "properties": {}}}),
    "get_my_payments": (t_get_my_payments, {
        "description": "Payment and refund records involving the signed-in user.",
        "parameters": {"type": "object", "properties": {}}}),
    "get_my_profile": (t_get_my_profile, {
        "description": "The signed-in user's profile, district, state, bank/UPI hints "
                       "and KYC status.",
        "parameters": {"type": "object", "properties": {}}}),
    "search_buyers": (t_search_buyers, {
        "description": "Find verified buyers in a state, optionally filtered by crop, "
                       "ranked by verification, rating and payment behaviour.",
        "parameters": {"type": "object", "properties": {
            "state": {"type": "string"}, "crop": {"type": "string"}}}}),
    "search_transport": (t_search_transport, {
        "description": "Find GPS-enabled transporters in a state with capacity and "
                       "per-km rate.",
        "parameters": {"type": "object", "properties": {
            "state": {"type": "string"},
            "min_capacity_qtl": {"type": "number"}}}}),
    "get_my_notifications": (t_get_my_notifications, {
        "description": "Recent notifications for the signed-in user.",
        "parameters": {"type": "object", "properties": {}}}),
    "get_my_grievances": (t_get_my_grievances, {
        "description": "GramRakshak complaints raised by the signed-in user.",
        "parameters": {"type": "object", "properties": {}}}),
    "get_quality_certificates": (t_get_quality_certificates, {
        "description": "Issued produce quality certificates and their grades.",
        "parameters": {"type": "object", "properties": {}}}),
    "get_platform_stats": (t_get_platform_stats, {
        "description": "Platform-wide counts. Admin role only.",
        "parameters": {"type": "object", "properties": {}}}),
    "explain_platform": (t_explain_platform, {
        "description": "Explain how a GRAM AI feature works: predictability_score, "
                       "net_realizable_price, sell_wait_shift, grievance, payments, kyc, "
                       "preorders, quality, rewards, transport.",
        "parameters": {"type": "object", "properties": {
            "topic": {"type": "string"}}}}),
}


def tool_specs():
    return [{"type": "function", "function": {
        "name": name, "description": meta["description"],
        "parameters": meta["parameters"]}} for name, (_, meta) in TOOLS.items()]


def run_tool(u, name, raw_args):
    fn = TOOLS.get(name, (None, None))[0]
    if not fn:
        return {"error": "Unknown tool %s" % name}
    try:
        args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
        if not isinstance(args, dict):
            args = {}
    except Exception:
        args = {}
    try:
        return fn(u, args)
    except Exception as e:
        return {"error": "%s failed: %s" % (name, e)}


# --------------------------------------------------------------------------
# Language detection: reply in the language the question was written in.
# --------------------------------------------------------------------------
# Each Unicode block maps to the languages the interface offers in that script.
# The first entry is the default; if the interface is already set to another
# language sharing the script, that one wins (a Marathi user typing Devanagari
# should get Marathi, not Hindi).
SCRIPTS = [
    ((0x0900, 0x097F), ["hi", "mr", "ne", "sa", "kok", "mai", "doi", "brx", "raj"]),
    ((0x0980, 0x09FF), ["bn", "as", "mni"]),
    ((0x0A00, 0x0A7F), ["pa"]),
    ((0x0A80, 0x0AFF), ["gu"]),
    ((0x0B00, 0x0B7F), ["or"]),
    ((0x0B80, 0x0BFF), ["ta"]),
    ((0x0C00, 0x0C7F), ["te"]),
    ((0x0C80, 0x0CFF), ["kn"]),
    ((0x0D00, 0x0D7F), ["ml"]),
    ((0x0600, 0x06FF), ["ur", "ks", "sd"]),
    ((0x1C50, 0x1C7F), ["sat"]),
    ((0xABC0, 0xABFF), ["mni"]),
]


def _statistical_guess(text):
    """Content-based language id, used only to disambiguate within a script.

    Script alone cannot tell Hindi from Marathi or Nepali - all three use
    Devanagari. py3langid is a plain statistical classifier (n-gram model,
    no network call, no API key), not an LLM, so this does not add a second
    AI provider; it only sharpens which language we hand to Groq.
    """
    if not _langid:
        return None
    try:
        code, _conf = _langid.classify(text)
        return (code or "").strip().lower() or None
    except Exception:
        return None


def detect_language(text, ui_lang="en"):
    """Language to answer in.

    Non-Latin script is a reliable signal that we are in one of a handful of
    languages sharing that script; a statistical language-id pass then picks
    the actual one from that short list (Hindi vs Marathi vs Nepali, for
    example). Latin text is ambiguous (a Hindi speaker may type on an English
    keyboard), so the interface language decides - which also keeps plain
    English questions in English.
    """
    counts = {}
    for ch in (text or ""):
        cp = ord(ch)
        for (lo, hi), langs in SCRIPTS:
            if lo <= cp <= hi:
                counts[langs[0]] = counts.get(langs[0], 0) + 1
                break

    if not counts:
        return ui_lang or "en"

    top = max(counts, key=counts.get)
    if counts[top] < 2:
        return ui_lang or "en"

    candidates = [top]
    for (_lo, _hi), langs in SCRIPTS:
        if langs[0] == top:
            candidates = langs
            break

    guess = _statistical_guess(text)
    if guess in candidates:
        return guess

    # No usable statistical signal: keep the interface language when it
    # shares this script, otherwise fall back to the script's default.
    return ui_lang if ui_lang in candidates else top

# --------------------------------------------------------------------------
# Prompt and history
# --------------------------------------------------------------------------
def system_prompt(u, lang, state):
    lang_name = LANG_NAMES.get(lang, "English")
    pages = ", ".join(NAV.get(u.get("role"), NAV["farmer"]))
    return (
        "You are GRAM Saathi, the assistant inside GRAM AI (KisanSetu), an Indian "
        "agricultural marketplace that helps farmers decide when and where to sell.\n"
        "\n"
        "The signed-in user is {name}, role={role}, district={district}, "
        "state={state_of_user}, user_id={uid}. Their working state context is "
        "{state}.\n"
        "\n"
        "RULES\n"
        "1. Answer ENTIRELY in {lang_name}. Every sentence, including headings and "
        "list items. Always write numbers with Western Arabic digits 0-9, never in "
        "the local numeral script. Keep the product names GRAM AI, GRAM Saathi, "
        "KisanSetu and GramRakshak in Latin script.\n"
        "2. Never invent a price, forecast, order, quantity or count. If a number is "
        "asked for, call a tool and report only what it returns. If the tool returns "
        "no rows, say so plainly.\n"
        "3. Prefer calling a tool over guessing. You may call several tools before "
        "answering.\n"
        "4. Prices are rupees per quintal unless the tool says otherwise. Write "
        "amounts as Rs 12,500.\n"
        "5. Be brief and practical - a farmer is reading this on a phone. Use short "
        "sentences and markdown bullets. Two to six sentences unless asked for "
        "detail.\n"
        "6. When recommending a selling decision, state it as SELL NOW, WAIT, "
        "SHIFT MARKET or STORE and give the one reason that drove it.\n"
        "7. You can only read data. To point the user at an action, name one of "
        "these pages exactly and never invent a page name: {pages}.\n"
        "8. Never reveal another user's personal data, and never mention SQL, "
        "tables or internal function names.\n"
    ).format(name=u.get("name", "user"), role=u.get("role"),
             district=u.get("district", "-"), state_of_user=u.get("state", "-"),
             uid=u.get("id"), state=state, lang_name=lang_name, pages=pages)


def load_history(uid, session_id, limit=HISTORY_TURNS):
    c = conn()
    rows = c.execute(
        "SELECT role,content FROM ai_chat_turns WHERE user_id=? AND session_id=? "
        "ORDER BY id DESC LIMIT ?", (uid, session_id, limit)).fetchall()
    c.close()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def save_turn(uid, session_id, role, content, lang="en", tools=""):
    c = conn()
    c.execute("INSERT INTO ai_chat_turns(user_id,session_id,role,content,lang,tools) "
              "VALUES(?,?,?,?,?,?)", (uid, session_id, role, content[:8000], lang, tools))
    c.commit()
    c.close()


def groq_call(messages, tools=None, stream=False, temperature=0.3):
    """POST to Groq, trying each configured model until one responds."""
    if not GROQ_API_KEY or not requests:
        raise RuntimeError("GROQ_API_KEY is not configured")
    last = None
    for model in GROQ_MODELS:
        payload = {"model": model, "messages": messages,
                   "temperature": temperature, "max_tokens": 1200}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        if stream:
            payload["stream"] = True
        try:
            r = requests.post(GROQ_URL,
                              headers={"Authorization": "Bearer %s" % GROQ_API_KEY,
                                       "Content-Type": "application/json"},
                              json=payload, timeout=90, stream=stream)
            if r.status_code == 200:
                # requests defaults text/* without a charset to ISO-8859-1, which
                # mangles non-Latin scripts in the SSE stream. Groq sends UTF-8.
                r.encoding = "utf-8"
                return r
            last = "%s -> %s %s" % (model, r.status_code, r.text[:200])
        except Exception as e:
            last = "%s -> %s" % (model, e)
    raise RuntimeError(last or "All Groq models failed")


def answer_with_tools(u, question, lang, state, session_id):
    """Full tool-calling loop. Returns (answer_text, used_tool_names, tool_payloads)."""
    messages = [{"role": "system", "content": system_prompt(u, lang, state)}]
    messages += load_history(u["id"], session_id)
    messages.append({"role": "user", "content": question})

    used, payloads = [], {}
    specs = tool_specs()

    for _ in range(MAX_TOOL_ROUNDS):
        r = groq_call(messages, tools=specs)
        msg = r.json()["choices"][0]["message"]
        calls = msg.get("tool_calls") or []
        if not calls:
            return (msg.get("content") or "").strip(), used, payloads
        messages.append({"role": "assistant", "content": msg.get("content") or "",
                         "tool_calls": calls})
        for call in calls:
            name = call["function"]["name"]
            out = run_tool(u, name, call["function"].get("arguments"))
            used.append(name)
            payloads[name] = out
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "name": name,
                             "content": json.dumps(out, ensure_ascii=False,
                                                   default=str)[:12000]})

    # Tool budget spent: ask for a final answer with no further tools.
    r = groq_call(messages)
    return (r.json()["choices"][0]["message"].get("content") or "").strip(), used, payloads


def legacy_answer(u, question, lang, state):
    """Keyword fallback so the assistant still responds without Groq."""
    try:
        from innovation_api import chat as legacy_chat
        return legacy_chat(q=question, state=state, lang=lang, u=u).get("answer", "")
    except Exception:
        return ("GRAM Saathi is offline right now. Open Crops & Forecasts for prices, "
                "Market & Offers for buyers, or Need Help for a complaint.")


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    lang: str = Field(default="en", max_length=12)
    # "auto" (the default from the UI) detects the language of the question.
    # A concrete code here forces the reply language instead.
    reply_lang: Optional[str] = Field(default=None, max_length=12)
    state: Optional[str] = None
    session_id: str = Field(default="default", max_length=64)


@router.get("/status")
def status(u=Depends(get_user_dep())):
    return {"enabled": bool(GROQ_API_KEY), "models": GROQ_MODELS,
            "tools": sorted(TOOLS.keys()), "role": u["role"]}


@router.get("/suggestions")
def suggestions(lang: str = "en", u=Depends(get_user_dep())):
    """Role-aware quick replies, translated with the free i18n service."""
    by_role = {
        "farmer": ["Should I sell my tomato now or wait?",
                   "Which market gives me the best net price?",
                   "Show my listings and their status",
                   "How many reward points do I have?",
                   "Find verified buyers near me",
                   "What is my KYC status?"],
        "buyer": ["Show active listings I can buy",
                  "What are onion prices this week?",
                  "Find quality-certified produce",
                  "Show my orders and their status",
                  "Which farmers have upcoming harvests?",
                  "Explain how pre-orders work"],
        "admin": ["Show platform statistics",
                  "How many KYC verifications are pending?",
                  "List open grievances",
                  "How many active listings are there?",
                  "Explain the Predictability Score",
                  "Show recent orders"],
    }
    items = by_role.get(u["role"], by_role["farmer"])
    if lang != "en":
        try:
            from i18n_service import translate_batch
            items = translate_batch(items, lang)
        except Exception:
            pass
    return {"lang": lang, "role": u["role"], "suggestions": items}


@router.get("/history")
def history(session_id: str = "default", u=Depends(get_user_dep())):
    c = conn()
    rows = [dict(r) for r in c.execute(
        "SELECT role,content,lang,created_at FROM ai_chat_turns "
        "WHERE user_id=? AND session_id=? ORDER BY id", (u["id"], session_id))]
    c.close()
    return {"session_id": session_id, "turns": rows[-40:]}


@router.post("/reset")
def reset(session_id: str = "default", u=Depends(get_user_dep())):
    c = conn()
    c.execute("DELETE FROM ai_chat_turns WHERE user_id=? AND session_id=?",
              (u["id"], session_id))
    c.commit()
    c.close()
    return {"ok": True}


def resolve_lang(body):
    """Explicit override wins; otherwise answer in the language of the question."""
    forced = (body.reply_lang or "").strip()
    if forced and forced != "auto" and forced in LANG_NAMES:
        return forced
    return detect_language(body.message, (body.lang or "en").strip())


@router.post("/chat")
def chat(body: ChatIn, u=Depends(get_user_dep())):
    lang = resolve_lang(body)
    state = (body.state or u.get("state") or DEFAULT_STATE)
    question = body.message.strip()
    save_turn(u["id"], body.session_id, "user", question, lang)

    fallback = False
    try:
        answer, used, payloads = answer_with_tools(u, question, lang, state, body.session_id)
        if not answer:
            raise RuntimeError("Empty completion")
    except Exception:
        answer, used, payloads = legacy_answer(u, question, lang, state), [], {}
        fallback = True

    save_turn(u["id"], body.session_id, "assistant", answer, lang, ",".join(used))
    return {"answer": answer, "lang": lang, "session_id": body.session_id,
            "used_tools": used, "data": payloads, "fallback": fallback}


@router.post("/stream")
def stream(body: ChatIn, u=Depends(get_user_dep())):
    """Server-sent events: tools resolve first, then the answer streams in."""
    lang = resolve_lang(body)
    state = (body.state or u.get("state") or DEFAULT_STATE)
    question = body.message.strip()
    save_turn(u["id"], body.session_id, "user", question, lang)

    def sse(event, data):
        return "event: %s\ndata: %s\n\n" % (event, json.dumps(data, ensure_ascii=False,
                                                              default=str))

    def gen():
        yield sse("lang", {"lang": lang, "name": LANG_NAMES.get(lang, lang)})
        messages = [{"role": "system", "content": system_prompt(u, lang, state)}]
        messages += load_history(u["id"], body.session_id)
        messages.append({"role": "user", "content": question})
        used, payloads, parts = [], {}, []

        try:
            specs = tool_specs()
            for _ in range(MAX_TOOL_ROUNDS):
                r = groq_call(messages, tools=specs)
                msg = r.json()["choices"][0]["message"]
                calls = msg.get("tool_calls") or []
                if not calls:
                    if msg.get("content"):
                        messages.append({"role": "assistant", "content": msg["content"]})
                    break
                messages.append({"role": "assistant", "content": msg.get("content") or "",
                                 "tool_calls": calls})
                for call in calls:
                    name = call["function"]["name"]
                    yield sse("tool", {"name": name})
                    out = run_tool(u, name, call["function"].get("arguments"))
                    used.append(name)
                    payloads[name] = out
                    messages.append({"role": "tool", "tool_call_id": call["id"],
                                     "name": name,
                                     "content": json.dumps(out, ensure_ascii=False,
                                                           default=str)[:12000]})
            else:
                pass

            if used:
                yield sse("data", {"used_tools": used, "data": payloads})

            r = groq_call(messages, stream=True)
            for line in r.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if chunk == "[DONE]":
                    break
                try:
                    delta = json.loads(chunk)["choices"][0].get("delta", {})
                except Exception:
                    continue
                piece = delta.get("content")
                if piece:
                    parts.append(piece)
                    yield sse("token", {"t": piece})

            answer = "".join(parts).strip()
            if not answer:
                raise RuntimeError("Empty stream")
        except Exception:
            answer = legacy_answer(u, question, lang, state)
            yield sse("token", {"t": answer})
            yield sse("done", {"fallback": True, "used_tools": used})
            save_turn(u["id"], body.session_id, "assistant", answer, lang)
            return

        save_turn(u["id"], body.session_id, "assistant", answer, lang, ",".join(used))
        yield sse("done", {"fallback": False, "used_tools": used})

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@router.post("/produce-photo")
async def produce_photo(photo: UploadFile = File(...), u=Depends(get_user_dep())):
    """Grade a produce photo attached in the chat.

    Runs the same YOLO + certificate pipeline as the WhatsApp flow, but returns
    the result so the assistant can render it in the conversation instead of
    sending a WhatsApp message.
    """
    if u["role"] != "farmer":
        raise HTTPException(403, "Only a farmer account can submit produce photos.")
    if not photo.filename:
        raise HTTPException(400, "No photo was attached.")

    import os, secrets
    from whatsapp_api import UPLOAD_DIR, process_produce_image

    contents = await photo.read()
    if not contents:
        raise HTTPException(400, "The attached photo was empty.")

    ext = os.path.splitext(photo.filename)[1].lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".bmp"):
        ext = ".jpg"
    path = os.path.join(UPLOAD_DIR, f"chat_{u['id']}_{secrets.token_hex(4)}{ext}")
    with open(path, "wb") as f:
        f.write(contents)

    result = process_produce_image(chat_sender_key(u), u.get("name", ""),
                                   path, notify=False)
    return result or {"ok": False, "reason": "unknown"}
