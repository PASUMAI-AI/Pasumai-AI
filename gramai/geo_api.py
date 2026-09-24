"""PasumAI geo features.

  GET  /api/geo/reverse                 coordinates -> a place name ("Vandalur, Chengalpattu, Tamil Nadu")
  GET  /api/geo/harvest/{id}/best-options   markets and buyers ranked by what the farmer actually keeps
  POST /api/geo/harvest/{id}/photos     add more photos, each checked against the farm's GPS
  GET  /api/geo/harvest/{id}/photos     list them with their geo-tag status
  GET  /api/geo/photo/{photo_id}        the image itself
  GET  /api/geo/buyer-types             business classifications offered at sign-up
  GET  /verify/{certificate_number}     public page the certificate's QR code opens

Place names come from OpenStreetMap Nominatim and are cached; when it is unreachable the nearest known
market is used, so the app never falls back to bare latitude and longitude.
"""
from __future__ import annotations

import html
import math
import os
import re
import secrets
import statistics
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

from chatbot_api import conn, get_user_dep
from certificate_service import (UPLOAD_DIR, validity_days, validity_status, resolve_upload,
                                 certificate_details, verification_id_for_listing)

router = APIRouter(prefix="/api/geo", tags=["PasumAI Geo"])
public_router = APIRouter(tags=["PasumAI Public"])

NOMINATIM = "https://nominatim.openstreetmap.org/reverse"
USER_AGENT = "PasumAI/1.0 (farm marketplace prototype)"
ROAD_FACTOR = 1.3            # road distance is roughly 1.3x the straight line
GEO_VERIFIED_M = 1000        # a photo taken within this distance of the farm counts as geo-tag verified
NEAR_FARM_M = 5000
MAX_PHOTO_BYTES = 8 * 1024 * 1024

# Business classifications a buyer chooses at sign-up.
BUYER_TYPES = [
    {"code": "RESTAURANT", "label": "Restaurant / Hotel / Caterer", "icon": "🍽️", "note": "Buys daily in small, steady lots"},
    {"code": "RETAIL_CHAIN", "label": "Retail chain (e.g. BigBasket, supermarkets)", "icon": "🛒", "note": "Buys large lots with strict grading"},
    {"code": "WHOLESALE_TRADER", "label": "Wholesale market trader / commission agent", "icon": "🏪", "note": "Buys in bulk for mandi resale"},
    {"code": "PROCESSOR", "label": "Food processor / mill", "icon": "🏭", "note": "Buys for processing: sauce, flour, oil"},
    {"code": "EXPORTER", "label": "Exporter", "icon": "🚢", "note": "Buys export-grade produce"},
    {"code": "INSTITUTION", "label": "Institution (hostel, hospital, canteen)", "icon": "🏥", "note": "Regular contract supply"},
    {"code": "KIRANA", "label": "Kirana / local retail shop", "icon": "🏬", "note": "Small quantities, quick payment"},
    {"code": "FPO_COOP", "label": "FPO / cooperative", "icon": "🤝", "note": "Pools produce from many farmers"},
    {"code": "INDIVIDUAL", "label": "Individual / household", "icon": "🏠", "note": "Personal purchase"},
]
BUYER_TYPE_CODES = {b["code"] for b in BUYER_TYPES}


def buyer_type_label(code):
    for b in BUYER_TYPES:
        if b["code"] == code:
            return b["label"]
    return ""


def farmer_category(acres):
    """Indian agricultural census size classes (hectare limits converted to acres)."""
    try:
        a = float(acres or 0)
    except Exception:
        a = 0
    if a <= 0:
        return "Farmer"
    if a < 2.47:
        return "Marginal farmer"
    if a < 4.94:
        return "Small farmer"
    if a < 9.88:
        return "Semi-medium farmer"
    if a < 24.7:
        return "Medium farmer"
    return "Large farmer"


# --------------------------------------------------------------------------
# Schema
# --------------------------------------------------------------------------
def _add_column(c, table, col, ddl):
    have = {r["name"] for r in c.execute("PRAGMA table_info(%s)" % table)}
    if col not in have:
        c.execute("ALTER TABLE %s ADD COLUMN %s %s" % (table, col, ddl))


# Classification for the seeded buyers, chosen from their names.
_NAME_TYPES = [
    (("fresh foods", "supermarket", "mart", "retail", "fresh basket", "store"), "RETAIL_CHAIN"),
    (("restaurant", "hotel", "foods & cater", "catering", "kitchen"), "RESTAURANT"),
    (("processing", "mill", "agro industries", "foods pvt", "industries"), "PROCESSOR"),
    (("export",), "EXPORTER"),
    (("fpo", "coop", "co-op", "cooperative", "collective"), "FPO_COOP"),
    (("procurement", "trader", "traders", "commission", "mandi", "agro"), "WHOLESALE_TRADER"),
]


def _guess_type(name):
    low = (name or "").lower()
    for words, code in _NAME_TYPES:
        if any(w in low for w in words):
            return code
    return "WHOLESALE_TRADER"


def init_geo_schema():
    c = conn()
    c.execute("""CREATE TABLE IF NOT EXISTS geo_cache(
        lat3 REAL, lon3 REAL, lang TEXT, place TEXT, locality TEXT, district TEXT, state TEXT,
        source TEXT, created_at TEXT, PRIMARY KEY(lat3, lon3, lang))""")
    c.execute("""CREATE TABLE IF NOT EXISTS harvest_photos(
        id INTEGER PRIMARY KEY AUTOINCREMENT, harvest_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        path TEXT NOT NULL, latitude REAL, longitude REAL, place TEXT, distance_m REAL,
        geo_status TEXT DEFAULT 'NO_GPS', note TEXT DEFAULT '', created_at TEXT)""")
    _add_column(c, "harvests", "location_text", "TEXT DEFAULT ''")
    _add_column(c, "users", "buyer_type", "TEXT DEFAULT ''")
    _add_column(c, "users", "business_name", "TEXT DEFAULT ''")
    _add_column(c, "buyers", "buyer_type", "TEXT DEFAULT ''")
    for r in c.execute("SELECT id, name FROM buyers WHERE coalesce(buyer_type,'')=''").fetchall():
        c.execute("UPDATE buyers SET buyer_type=? WHERE id=?", (_guess_type(r["name"]), r["id"]))
    c.commit()
    c.close()


# --------------------------------------------------------------------------
# Maths
# --------------------------------------------------------------------------
def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


_CENTROIDS = {}

# Districts that have no mandi in the markets table.
_KNOWN_DISTRICTS = {"chennai": (13.0827, 80.2707), "coimbatore": (11.0168, 76.9558), "madurai": (9.9252, 78.1198)}


def district_centroid(c, state, district):
    """Average position of a district's markets, used as that district's location."""
    key = ((state or "").lower(), (district or "").lower())
    if key in _CENTROIDS:
        return _CENTROIDS[key]
    row = c.execute("SELECT avg(lat) la, avg(lon) lo FROM markets WHERE lower(district)=? AND (?='' OR lower(state)=?)",
                    (key[1], key[0], key[0])).fetchone()
    val = (row["la"], row["lo"]) if row and row["la"] is not None else None
    if val is None:
        val = _KNOWN_DISTRICTS.get(key[1])
    _CENTROIDS[key] = val
    return val


# --------------------------------------------------------------------------
# Reverse geocoding
# --------------------------------------------------------------------------
def _nearest_market_place(c, lat, lon):
    best, bd = None, 1e9
    for m in c.execute("SELECT city, district, state, lat, lon FROM markets WHERE lat IS NOT NULL").fetchall():
        d = haversine_km(lat, lon, m["lat"], m["lon"])
        if d < bd:
            best, bd = m, d
    if best is None:
        return None
    town = best["city"] or best["district"]
    parts = [("Near " + town) if bd > 3 else town, best["district"] if best["district"] != town else "", best["state"]]
    place = ", ".join(p for p in parts if p)
    return {"place": place, "locality": town, "district": best["district"], "state": best["state"], "source": "nearest-market"}


def _from_nominatim(lat, lon, lang):
    if not requests:
        return None
    try:
        r = requests.get(NOMINATIM, params={"format": "jsonv2", "lat": lat, "lon": lon, "zoom": 14,
                                            "addressdetails": 1, "accept-language": lang or "en"},
                         headers={"User-Agent": USER_AGENT}, timeout=6)
        if r.status_code != 200:
            return None
        a = (r.json() or {}).get("address") or {}
    except Exception:
        return None
    locality = next((a[k] for k in ("suburb", "neighbourhood", "village", "hamlet", "town", "city_district", "city")
                     if a.get(k)), "")
    district = next((a[k] for k in ("state_district", "county", "city") if a.get(k)), "")
    district = re.sub(r"\s+(District|district)$", "", district)
    state = a.get("state", "")
    parts = []
    for p in (locality, district, state):
        if p and p not in parts:
            parts.append(p)
    if not parts:
        return None
    return {"place": ", ".join(parts), "locality": locality or district, "district": district, "state": state,
            "source": "openstreetmap"}


def resolve_place(lat, lon, lang="en", network=True):
    """Place name for a coordinate. Cached; never returns raw coordinates."""
    if lat is None or lon is None:
        return {"place": "", "locality": "", "district": "", "state": "", "source": "none"}
    lang = (lang or "en").split("-")[0]
    lat3, lon3 = round(float(lat), 3), round(float(lon), 3)
    c = conn()
    try:
        row = c.execute("SELECT * FROM geo_cache WHERE lat3=? AND lon3=? AND lang=?", (lat3, lon3, lang)).fetchone()
        if row:
            return {k: row[k] for k in ("place", "locality", "district", "state", "source")}
        out = _from_nominatim(lat, lon, lang) if network else None
        cacheable = out is not None
        if out is None:
            out = _nearest_market_place(c, float(lat), float(lon)) or \
                {"place": "Location recorded", "locality": "", "district": "", "state": "", "source": "none"}
        if cacheable:
            c.execute("INSERT OR REPLACE INTO geo_cache VALUES(?,?,?,?,?,?,?,?,?)",
                      (lat3, lon3, lang, out["place"], out["locality"], out["district"], out["state"], out["source"],
                       datetime.now(timezone.utc).isoformat()))
            c.commit()
        return out
    finally:
        c.close()


@router.get("/reverse")
def reverse(lat: float, lon: float, lang: str = "en", u=Depends(get_user_dep())):
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise HTTPException(400, "Invalid coordinates")
    return resolve_place(lat, lon, lang)


@router.get("/buyer-types")
def buyer_types():
    return BUYER_TYPES


# --------------------------------------------------------------------------
# Best places to sell
# --------------------------------------------------------------------------
def _harvest_for(c, hid, u):
    h = c.execute("SELECT * FROM harvests WHERE id=?", (hid,)).fetchone()
    if not h:
        raise HTTPException(404, "Harvest not found")
    if u["role"] == "farmer" and h["farmer_id"] != u["id"]:
        raise HTTPException(403, "This is not your harvest")
    return h


def _transport_per_qtl_km(c, state):
    rates = []
    for t in c.execute("SELECT rate_per_km, capacity_qtl FROM transporters WHERE state=? OR ?=''", (state, state)):
        if t["rate_per_km"] and t["capacity_qtl"]:
            rates.append(float(t["rate_per_km"]) / max(float(t["capacity_qtl"]), 20.0))
    return statistics.median(rates) if rates else 0.2


RETURN_FACTOR = 1.5      # the truck usually goes back part-empty, so a trip costs about 1.5x the one-way distance
MIN_SHARED_QTL = 10      # a small lot travels on a shared pickup: it pays for at least this many quintals of the trip


def transport_quote(c, state, qty, road_km):
    """Cost of moving `qty` quintals `road_km` km, from the transporters in the database.

    The smallest vehicle that fits the lot is used (several trips if nothing fits). The farmer pays the trip
    divided by the lot size, but never less than a MIN_SHARED_QTL share, so a 30 kg lot is not priced like
    a full truck and is not priced as if it needed its own truck either."""
    rows = c.execute("SELECT vehicle_type, capacity_qtl, rate_per_km FROM transporters "
                     "WHERE (state=? OR ?='') AND rate_per_km>0 AND capacity_qtl>0", (state, state)).fetchall()
    qty = max(float(qty or 0), 0.1)
    if not rows:
        per = 0.24 * road_km
        return {"per_qtl": per, "trip_cost": per * qty, "vehicle": "truck", "capacity_qtl": None, "trips": 1}
    fits = [r for r in rows if r["capacity_qtl"] >= qty]
    if fits:
        v, trips = min(fits, key=lambda r: (r["capacity_qtl"], r["rate_per_km"])), 1
    else:
        v = max(rows, key=lambda r: r["capacity_qtl"])
        trips = math.ceil(qty / v["capacity_qtl"])
    trip_cost = float(v["rate_per_km"]) * road_km * RETURN_FACTOR * trips
    share = max(min(qty, v["capacity_qtl"] * trips), MIN_SHARED_QTL)
    return {"per_qtl": trip_cost / share, "trip_cost": trip_cost, "vehicle": v["vehicle_type"],
            "capacity_qtl": v["capacity_qtl"], "trips": trips}


def _reliability(payment_score, rating):
    return round(0.65 * float(payment_score or 60) + 0.35 * float(rating or 3) * 20, 1)


def _spoil_pct_per_100km(crop):
    return 2.0 if validity_days(crop) <= 7 else 0.5


def rank_options(c, h, radius_km=400):
    crop = h["crop"]
    qty = float(h["available_quantity_qtl"] or h["expected_quantity_qtl"] or 0)
    if h["latitude"] is not None and h["longitude"] is not None:
        lat, lon = float(h["latitude"]), float(h["longitude"])
    else:
        cen = district_centroid(c, h["state"], h["district"])
        if not cen:
            raise HTTPException(400, "This harvest has no location yet")
        lat, lon = cen
    spoil = _spoil_pct_per_100km(crop)

    def money(price, km, lot=None):
        road = km * ROAD_FACTOR
        q = transport_quote(c, h["state"], lot or qty, road)
        loss = price * spoil / 100.0 * (road / 100.0)
        money.last = q
        return round(road, 1), round(q["per_qtl"], 1), round(loss, 1)
    money.last = None

    options = []

    # 1. Markets with today's price for this crop.
    day = c.execute("SELECT max(price_date) d FROM prices WHERE crop=?", (crop,)).fetchone()["d"]
    if day:
        rows = c.execute("""SELECT m.id, m.name, m.city, m.district, m.state, m.lat, m.lon, m.market_fee_pct, m.market_type,
                                   p.modal_price, p.arrivals_qtl
                            FROM markets m JOIN prices p ON p.market_id = m.id
                            WHERE p.crop=? AND p.price_date=? AND m.lat IS NOT NULL""", (crop, day)).fetchall()
        for m in rows:
            km = haversine_km(lat, lon, m["lat"], m["lon"])
            if km > radius_km:
                continue
            road, transport, loss = money(m["modal_price"], km)
            quote = money.last
            fee = round(m["modal_price"] * float(m["market_fee_pct"] or 0) / 100.0, 1)
            net = round(m["modal_price"] - transport - fee - loss, 1)
            options.append({
                "kind": "market", "id": m["id"], "name": m["name"], "type_label": m["market_type"] or "Mandi",
                "place": ", ".join(p for p in (m["city"], m["district"], m["state"]) if p),
                "distance_km": road, "price_per_qtl": m["modal_price"], "transport_per_qtl": transport,
                "fee_per_qtl": fee, "loss_per_qtl": loss, "net_per_qtl": net, "score": net,
                "trip_cost": round(quote["trip_cost"]), "vehicle": quote["vehicle"],
                "reliability": None, "verified": True, "buyer_type": "",
                "note": "Today's modal price" + (" · %s qtl arriving" % int(m["arrivals_qtl"]) if m["arrivals_qtl"] else ""),
            })

    # Reference price for buyers without a stated price: the average of the nearest few markets.
    near_prices = sorted((o for o in options if o["kind"] == "market"), key=lambda o: o["distance_km"])[:5]
    ref_price = statistics.mean(o["price_per_qtl"] for o in near_prices) if near_prices else float(h["expected_price"] or 0)

    # 2. Buyers who have posted a demand for this crop.
    demands = c.execute("""SELECT d.*, u.name buyer_name, u.business_name, u.buyer_type, u.district u_district, u.state u_state
                           FROM buyer_preorder_demands d JOIN users u ON u.id = d.buyer_id
                           WHERE lower(d.crop)=lower(?) AND d.status IN ('OPEN','ACTIVE','PARTIAL')
                             AND coalesce(d.remaining_quantity_qtl, d.quantity_qtl) > 0""", (crop,)).fetchall()
    for d in demands:
        cen = district_centroid(c, d["delivery_state"] or d["u_state"], d["delivery_district"] or d["u_district"])
        if not cen:
            continue
        km = haversine_km(lat, lon, cen[0], cen[1])
        if km > radius_km:
            continue
        road, transport, loss = money(d["offer_price"], km, min(qty, float(d["remaining_quantity_qtl"] or d["quantity_qtl"])))
        quote = money.last
        # A buyer who collects saves the farmer the transport.
        if str(d["delivery_mode"] or "").upper() in ("BUYER_PICKUP", "PICKUP", "BUYER"):
            transport = 0.0
            quote = dict(quote, trip_cost=0, vehicle="Buyer collects")
        net = round(d["offer_price"] - transport - loss, 1)
        remain = float(d["remaining_quantity_qtl"] or d["quantity_qtl"])
        options.append({
            "kind": "demand", "id": d["id"], "name": d["business_name"] or d["buyer_name"],
            "type_label": buyer_type_label(d["buyer_type"]) or "Buyer",
            "place": ", ".join(p for p in (d["delivery_district"], d["delivery_state"]) if p),
            "distance_km": road, "price_per_qtl": d["offer_price"], "transport_per_qtl": transport,
            "fee_per_qtl": 0, "loss_per_qtl": loss, "net_per_qtl": net, "score": net,
            "trip_cost": round(quote["trip_cost"]), "vehicle": quote["vehicle"],
            "reliability": None, "verified": True, "buyer_type": d["buyer_type"] or "",
            "want_qtl": remain, "needed_by": d["required_by_date"],
            "note": "Needs %s qtl%s" % (int(remain) if remain == int(remain) else remain,
                                        " by %s" % d["required_by_date"] if d["required_by_date"] else ""),
        })

    # 3. Registered buyers who regularly buy this crop.
    buyers = c.execute("SELECT * FROM buyers WHERE crops LIKE ?", ("%" + crop + "%",)).fetchall()
    for b in buyers:
        cen = district_centroid(c, b["state"], b["district"])
        if not cen:
            continue
        km = haversine_km(lat, lon, cen[0], cen[1])
        if km > radius_km:
            continue
        road, transport, loss = money(ref_price, km)
        quote = money.last
        rel = _reliability(b["payment_score"], b["rating"])
        net = round(ref_price - transport - loss, 1)
        options.append({
            "kind": "buyer", "id": b["id"], "name": b["name"], "type_label": buyer_type_label(b["buyer_type"]) or "Buyer",
            "place": ", ".join(p for p in (b["district"], b["state"]) if p),
            "distance_km": road, "price_per_qtl": round(ref_price, 1), "transport_per_qtl": transport,
            "fee_per_qtl": 0, "loss_per_qtl": loss, "net_per_qtl": net,
            "trip_cost": round(quote["trip_cost"]), "vehicle": quote["vehicle"],
            "score": net * (0.92 + 0.08 * rel / 100.0), "reliability": rel, "verified": bool(b["verified"]),
            "buyer_type": b["buyer_type"] or "", "price_estimated": True,
            "note": "Pays in ~%s days · %s orders done" % (b["avg_payment_days"], b["completed_orders"]),
        })

    options.sort(key=lambda o: o["score"], reverse=True)
    options = options[:12]
    for i, o in enumerate(options, 1):
        o["rank"] = i
        sellable = min(qty, o["want_qtl"]) if o.get("want_qtl") else qty
        o["est_total"] = round(o["net_per_qtl"] * sellable)
        o["sellable_qtl"] = round(sellable, 2)

    if options:
        best = options[0]
        nearest = min(options, key=lambda o: o["distance_km"])
        top_price = max(options, key=lambda o: o["price_per_qtl"])
        best["tags"] = ["Best overall"]
        if nearest is not best:
            nearest.setdefault("tags", []).append("Nearest")
        else:
            best["tags"].append("Nearest")
        if top_price is not best and top_price is not nearest:
            top_price.setdefault("tags", []).append("Highest price")
        elif top_price is best:
            best["tags"].append("Highest price")
        gain = round((best["net_per_qtl"] - nearest["net_per_qtl"]) * qty) if nearest is not best else 0
        if nearest is best:
            tip = "%s is both the nearest and the best option: you keep about ₹%s per quintal after transport." % (
                best["name"], int(best["net_per_qtl"]))
        elif gain > 0:
            tip = ("Sell to %s (%s km away): you keep about ₹%s per quintal after transport, "
                   "roughly ₹%s more in total than the nearest option, %s.") % (
                best["name"], best["distance_km"], int(best["net_per_qtl"]), format(gain, ","), nearest["name"])
        else:
            tip = "Sell to %s (%s km away): about ₹%s per quintal after transport." % (
                best["name"], best["distance_km"], int(best["net_per_qtl"]))
    else:
        tip = "No markets or buyers with this crop were found within %s km." % radius_km

    place = {"place": h["location_text"]} if h["location_text"] else resolve_place(lat, lon)
    return {
        "harvest_id": h["id"], "crop": crop, "quantity_qtl": qty, "origin": {"lat": lat, "lon": lon, "place": place["place"]},
        "price_date": day, "radius_km": radius_km,
        "suggestion": tip, "options": options,
        "how": "Ranked by what you keep per quintal: price, minus transport, market fee and freshness loss. Transport is a "
               "real trip cost from our transporter rates (round trip counted at 1.5x), shared by your lot, and never "
               "less than a 10-quintal share. Small lots therefore pay more per quintal than full truckloads. "
               "Buyers with a good payment record get a small boost.",
    }


@router.get("/harvest/{hid}/best-options")
def best_options(hid: int, radius_km: int = 400, u=Depends(get_user_dep())):
    c = conn()
    try:
        h = _harvest_for(c, hid, u)
        out = rank_options(c, h, max(20, min(radius_km, 1500)))
        if not h["location_text"] and out["origin"]["place"] and h["latitude"] is not None:
            c.execute("UPDATE harvests SET location_text=? WHERE id=?", (out["origin"]["place"], hid))
            c.commit()
        return out
    finally:
        c.close()


# --------------------------------------------------------------------------
# Buyer discovery: harvests ranked by delivered cost, tuned to the buyer's business type
# --------------------------------------------------------------------------
BUYER_FOCUS = {
    "RESTAURANT": ("freshness and distance", "near"), "KIRANA": ("freshness and distance", "near"),
    "INSTITUTION": ("freshness and distance", "near"), "INDIVIDUAL": ("freshness and distance", "near"),
    "RETAIL_CHAIN": ("grade and verified quality", "quality"), "EXPORTER": ("grade and verified quality", "quality"),
    "WHOLESALE_TRADER": ("lowest delivered price", "price"), "PROCESSOR": ("lowest delivered price", "price"),
    "FPO_COOP": ("lowest delivered price", "price"),
}


@router.get("/buyer/discover")
def buyer_discover(lat: Optional[float] = None, lon: Optional[float] = None, crop: Optional[str] = None,
                   max_km: int = 800, sort: str = "auto", u=Depends(get_user_dep())):
    c = conn()
    try:
        btype = u.get("buyer_type") or ""
        focus_label, mode = BUYER_FOCUS.get(btype, ("delivered price and distance", "price"))
        if lat is not None and lon is not None:
            olat, olon = lat, lon
            oplace = resolve_place(lat, lon)["place"]
        else:
            cen = district_centroid(c, u.get("state") or "Tamil Nadu", u.get("district") or "") or (13.0827, 80.2707)
            olat, olon = cen
            oplace = ", ".join(p for p in (u.get("district"), u.get("state")) if p) or "Chennai, Tamil Nadu"
        day = c.execute("SELECT max(price_date) d FROM prices").fetchone()["d"]
        ref = {r["crop"]: r["v"] for r in c.execute(
            "SELECT p.crop, avg(p.modal_price) v FROM prices p JOIN markets m ON m.id=p.market_id "
            "WHERE p.price_date=? AND m.state='Tamil Nadu' GROUP BY p.crop", (day,))}

        rows = c.execute("""SELECT l.*, u.name seller_name, u.farm_size_acres, u.district seller_district, k.status kyc_status
                            FROM listings l JOIN users u ON u.id=l.seller_id LEFT JOIN kyc_profiles k ON k.user_id=u.id
                            WHERE l.status='OPEN' AND lower(l.state)='tamil nadu' AND (? IS NULL OR lower(l.crop)=lower(?))""",
                         (crop, crop)).fetchall()
        items = []
        for r in rows:
            vid = verification_id_for_listing(c, r) if r["quality_verified"] else None
            hv = c.execute("SELECT * FROM harvests WHERE verification_id=? ORDER BY id DESC LIMIT 1", (vid,)).fetchone() if vid else None
            ver = c.execute("SELECT * FROM quality_verifications WHERE id=?", (vid,)).fetchone() if vid else None
            if hv and hv["latitude"] is not None:
                flat, flon, exact = hv["latitude"], hv["longitude"], True
            elif ver and ver["latitude"] is not None:
                flat, flon, exact = ver["latitude"], ver["longitude"], True
            else:
                cen = district_centroid(c, r["state"], r["district"])
                if not cen:
                    continue
                flat, flon, exact = cen[0], cen[1], False
            km = haversine_km(olat, olon, flat, flon)
            if km > max_km:
                continue
            road = round(km * ROAD_FACTOR, 1)
            lot = float(r["quantity_qtl"] or 1)
            if r["seller_transport"] and r["transport_cost_per_km"]:
                transport = float(r["transport_cost_per_km"]) * road * RETURN_FACTOR / max(min(lot, 30.0), MIN_SHARED_QTL)
            else:
                transport = transport_quote(c, "Tamil Nadu", lot, road)["per_qtl"]
            ask = float(r["ask_price"] or 0)
            landed = ask + transport
            cert = certificate_details(c, vid) if vid else None
            ph = photo_summary(c, hv["id"]) if hv else {"photo_count": 0, "geo_verified_photos": 0}
            geo_ok = ph["geo_verified_photos"] + (1 if (ver and ver["latitude"] is not None) else 0)
            place = (hv["location_text"] if hv and hv["location_text"] else "") or (
                resolve_place(flat, flon, network=False)["place"] if exact
                else ", ".join(p for p in (r["district"], r["state"]) if p))
            refp = ref.get(r["crop"])
            grade_adj = {"A": 0.97, "B": 1.0, "C": 1.05}.get(str(r["grade"] or "").upper(), 1.0)
            cert_adj = 1.05 if (cert and cert["status"] == "EXPIRED") else (1.0 if cert else 1.03)
            if mode == "near":
                adj = (ask + 1.6 * transport) * cert_adj
            elif mode == "quality":
                adj = landed * grade_adj * cert_adj * (1 - 0.01 * min(geo_ok, 3))
            else:
                adj = landed * cert_adj
            items.append({
                "id": r["id"], "seller_id": r["seller_id"], "seller_name": r["seller_name"],
                "seller_class": farmer_category(r["farm_size_acres"]), "kyc_verified": r["kyc_status"] == "VERIFIED",
                "crop": r["crop"], "variety": r["variety"], "grade": r["grade"], "quantity_qtl": r["quantity_qtl"],
                "ask_price": ask, "market_price": round(refp) if refp else None,
                "vs_market_pct": round((ask - refp) / refp * 100, 1) if refp else None,
                "distance_km": road, "place": place, "location_exact": exact,
                "transport_per_qtl": round(transport, 1), "landed_per_qtl": round(landed, 1),
                "seller_transport": bool(r["seller_transport"]),
                "quality_verified": bool(r["quality_verified"]),
                "certificate": ({**cert, "number": cert["certificate_number"],
                                 "verify_url": "/verify/" + cert["certificate_number"]} if cert else None),
                "geo_verified_photos": geo_ok, "photo_count": ph["photo_count"] + (1 if ver else 0),
                "harvest_date": r["harvest_date"], "score": adj,
            })
        key = {"distance": lambda i: i["distance_km"], "price": lambda i: i["landed_per_qtl"],
               "verified": lambda i: (-i["geo_verified_photos"], i["landed_per_qtl"])}.get(sort, lambda i: i["score"])
        items.sort(key=key)
        for n, i in enumerate(items, 1):
            i["rank"] = n
            i["tags"] = []
        if items:
            items[0]["tags"].append("Best match for you" if sort == "auto" else "Top result")
            min(items, key=lambda i: i["distance_km"])["tags"].append("Nearest")
            min(items, key=lambda i: i["landed_per_qtl"])["tags"].append("Lowest delivered price")
            mv = max(items, key=lambda i: i["geo_verified_photos"])
            if mv["geo_verified_photos"] > 0:
                mv["tags"].append("Most geo-verified")
        return {"origin": {"lat": olat, "lon": olon, "place": oplace}, "buyer_type": btype,
                "buyer_type_label": buyer_type_label(btype), "focus": focus_label, "price_date": day,
                "crops": sorted({i["crop"] for i in items}), "items": items[:60],
                "how": "Delivered price = farmer's price + transport from the farm to you. "
                       "Ranking favours %s for your business type." % focus_label}
    finally:
        c.close()


# --------------------------------------------------------------------------
# Extra photos with geo-tag verification
# --------------------------------------------------------------------------
def _photo_row(r, place_map=None):
    return {"id": r["id"], "harvest_id": r["harvest_id"], "latitude": r["latitude"], "longitude": r["longitude"],
            "place": r["place"] or "", "distance_m": r["distance_m"], "geo_status": r["geo_status"],
            "note": r["note"] or "", "created_at": r["created_at"], "url": "/api/geo/photo/%s" % r["id"]}


def geo_status(distance_m):
    if distance_m is None:
        return "NO_GPS"
    if distance_m <= GEO_VERIFIED_M:
        return "GEO_VERIFIED"
    if distance_m <= NEAR_FARM_M:
        return "NEAR_FARM"
    return "FAR_FROM_FARM"


@router.post("/harvest/{hid}/photos")
async def add_photo(hid: int, photo: UploadFile = File(...), latitude: Optional[float] = Form(None),
                    longitude: Optional[float] = Form(None), note: str = Form(""), u=Depends(get_user_dep())):
    if u["role"] not in ("farmer", "admin"):
        raise HTTPException(403, "Only the farmer can add photos")
    c = conn()
    try:
        h = _harvest_for(c, hid, u)
        if not photo.content_type or not photo.content_type.startswith("image/"):
            raise HTTPException(400, "Please choose an image")
        data = await photo.read()
        if not data:
            raise HTTPException(400, "Empty photo")
        if len(data) > MAX_PHOTO_BYTES:
            raise HTTPException(400, "Photo is too large (max 8 MB)")
        ext = os.path.splitext(photo.filename or "")[1].lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            ext = ".jpg"
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        path = os.path.join(UPLOAD_DIR, "harvest_%s_%s_%s%s" % (hid, int(time.time()), secrets.token_hex(4), ext))
        with open(path, "wb") as f:
            f.write(data)

        dist = None
        place = ""
        if latitude is not None and longitude is not None and -90 <= latitude <= 90 and -180 <= longitude <= 180:
            place = resolve_place(latitude, longitude)["place"]
            if h["latitude"] is not None and h["longitude"] is not None:
                dist = round(haversine_km(latitude, longitude, h["latitude"], h["longitude"]) * 1000)
        status = geo_status(dist) if latitude is not None else "NO_GPS"
        cur = c.execute("""INSERT INTO harvest_photos(harvest_id,user_id,path,latitude,longitude,place,distance_m,geo_status,note,created_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?)""",
                        (hid, u["id"], path, latitude, longitude, place, dist, status, note[:200],
                         datetime.now(timezone.utc).isoformat()))
        c.commit()
        row = c.execute("SELECT * FROM harvest_photos WHERE id=?", (cur.lastrowid,)).fetchone()
        return _photo_row(row)
    finally:
        c.close()


@router.get("/harvest/{hid}/photos")
def list_photos(hid: int, u=Depends(get_user_dep())):
    c = conn()
    try:
        h = c.execute("SELECT * FROM harvests WHERE id=?", (hid,)).fetchone()
        if not h:
            raise HTTPException(404, "Harvest not found")
        if u["role"] == "farmer" and h["farmer_id"] != u["id"]:
            raise HTTPException(403, "This is not your harvest")
        out = []
        # The photo taken during quality verification carries the farm's GPS by definition.
        if h["verification_id"]:
            v = c.execute("SELECT * FROM quality_verifications WHERE id=?", (h["verification_id"],)).fetchone()
            if v and v["image_path"]:
                out.append({"id": 0, "harvest_id": hid, "latitude": v["latitude"], "longitude": v["longitude"],
                            "place": h["location_text"] or resolve_place(v["latitude"], v["longitude"], network=False)["place"],
                            "distance_m": 0, "geo_status": "GEO_VERIFIED", "note": "Quality-check photo",
                            "created_at": v["created_at"],
                            "url": "/api/produce/certificate/%s/photo" % v["id"]})
        for r in c.execute("SELECT * FROM harvest_photos WHERE harvest_id=? ORDER BY id", (hid,)):
            out.append(_photo_row(r))
        return {"harvest_id": hid, "photos": out,
                "verified_count": sum(1 for p in out if p["geo_status"] == "GEO_VERIFIED"),
                "rule": "A photo is geo-tag verified when it was taken within %s m of your farm's GPS location." % GEO_VERIFIED_M}
    finally:
        c.close()


@router.get("/photo/{photo_id}")
def get_photo(photo_id: int, u=Depends(get_user_dep())):
    c = conn()
    try:
        r = c.execute("SELECT p.*, h.farmer_id, h.buyer_visible FROM harvest_photos p JOIN harvests h ON h.id=p.harvest_id WHERE p.id=?",
                      (photo_id,)).fetchone()
        if not r:
            raise HTTPException(404, "Photo not found")
        if u["role"] == "farmer" and r["farmer_id"] != u["id"]:
            raise HTTPException(403, "Not allowed")
        path = resolve_upload(r["path"])
        if not path:
            raise HTTPException(404, "Photo file is missing")
        return FileResponse(path)
    finally:
        c.close()


def photo_summary(c, harvest_id):
    rows = c.execute("SELECT geo_status, count(*) n FROM harvest_photos WHERE harvest_id=? GROUP BY geo_status",
                     (harvest_id,)).fetchall()
    by = {r["geo_status"]: r["n"] for r in rows}
    return {"photo_count": sum(by.values()), "geo_verified_photos": by.get("GEO_VERIFIED", 0)}


# --------------------------------------------------------------------------
# Public certificate page (the QR code opens this)
# --------------------------------------------------------------------------
def _short_name(name):
    parts = (name or "Farmer").split()
    return parts[0] + (" " + parts[-1][0] + "." if len(parts) > 1 else "")


@public_router.get("/verify/{certificate_number}", response_class=HTMLResponse)
def verify_certificate(certificate_number: str):
    c = conn()
    try:
        q = c.execute("SELECT * FROM quality_certificates WHERE certificate_number=?", (certificate_number,)).fetchone()
        if not q:
            body = "<h1>Certificate not found</h1><p>No PasumAI certificate has this number. It may be forged or mistyped.</p>"
            return HTMLResponse(_page("Not found", body, ok=False), status_code=404)
        f = c.execute("SELECT * FROM users WHERE id=?", (q["farmer_id"],)).fetchone()
        v = c.execute("SELECT * FROM quality_verifications WHERE id=?", (q["verification_id"],)).fetchone()
        h = c.execute("SELECT * FROM harvests WHERE verification_id=? ORDER BY id DESC LIMIT 1", (q["verification_id"],)).fetchone()
        kyc = c.execute("SELECT status FROM kyc_profiles WHERE user_id=?", (q["farmer_id"],)).fetchone()
        lat, lon = q["latitude"], q["longitude"]
        place = (h["location_text"] if h and h["location_text"] else "") or resolve_place(lat, lon, network=False)["place"]
        status = validity_status(q["valid_until"])["status"]
        photos = photo_summary(c, h["id"]) if h else {"photo_count": 0, "geo_verified_photos": 0}
        fpo = c.execute("SELECT count(*) n FROM fpo_group_members WHERE farmer_id=?", (q["farmer_id"],)).fetchone()["n"]
        rows = [
            ("Crop", q["crop"]), ("Quality grade", q["grade"]),
            ("AI confidence", "%s%%" % round(float(q["confidence"] or 0) * (100 if float(q["confidence"] or 0) <= 1 else 1))),
            ("Where it was checked", place), ("Checked on", (q["scanned_at"] or q["issued_at"] or "")[:16].replace("T", " ")),
            ("Valid until", (q["valid_until"] or "")[:16].replace("T", " ")),
            ("Grower", _short_name(f["name"]) if f else "Farmer"),
            ("Grower class", farmer_category(f["farm_size_acres"] if f else 0) + (" · FPO member" if fpo else "")),
            ("Identity (KYC)", "Verified" if kyc and kyc["status"] == "VERIFIED" else "Not verified"),
            ("Geo-tagged photos", "%s of %s verified" % (photos["geo_verified_photos"] + (1 if v and v["image_path"] else 0),
                                                         photos["photo_count"] + (1 if v and v["image_path"] else 0))),
            ("Certificate no.", q["certificate_number"]),
        ]
        ok = str(status).lower() not in ("expired",)
        badge = "Valid certificate" if ok else "Expired certificate"
        table = "".join("<tr><th>%s</th><td>%s</td></tr>" % (html.escape(a), html.escape(str(b))) for a, b in rows)
        body = ('<p class="badge %s">%s</p><h1>%s · Grade %s</h1><table>%s</table>'
                '<p class="fine">Issued by PasumAI from an AI photo check and the farmer\'s GPS location. '
                'Scanning this code always shows the current status.</p>') % (
            "ok" if ok else "bad", badge, html.escape(q["crop"]), html.escape(str(q["grade"])), table)
        return HTMLResponse(_page("Certificate " + certificate_number, body, ok=ok))
    finally:
        c.close()


def _page(title, body, ok=True):
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s · PasumAI</title><link rel="icon" href="/static/brand/favicon.ico">
<style>
body{margin:0;background:#fafaf8;color:#111;font-family:Inter,system-ui,sans-serif;line-height:1.55}
main{max-width:560px;margin:0 auto;padding:28px 18px 60px}
.brand{font-family:'Instrument Serif',Georgia,serif;font-size:30px;margin-bottom:18px}
h1{font-family:'Instrument Serif',Georgia,serif;font-weight:400;font-size:38px;line-height:1.1;margin:.2em 0 .6em}
.badge{display:inline-block;padding:6px 14px;border-radius:999px;font-weight:700;font-size:14px;margin:0}
.badge.ok{background:#DCFF00;color:#111}.badge.bad{background:#fdecec;color:#b42318}
table{width:100%%;border-collapse:collapse;background:#fff;border:1px solid #0000001a;border-radius:16px;overflow:hidden}
th,td{text-align:left;padding:12px 16px;border-bottom:1px solid #0000000d;vertical-align:top}
th{width:42%%;color:#6F6F6F;font-weight:600;font-size:14px}
.fine{color:#6F6F6F;font-size:13px;margin-top:18px}
</style></head><body><main><div class="brand"><img src="/static/brand/logo-128.png" width="46" height="46" alt="PasumAI logo" style="border-radius:50%%;vertical-align:middle;margin-right:10px">PasumAI<sup style="font-size:12px">®</sup></div>%s</main></body></html>""" % (html.escape(title), body)
