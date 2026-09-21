"""Load the curated Tamil Nadu market infrastructure into the markets table.

Source: data/tn_markets.csv, built by data/curate_tn_markets.py from
agrimark.tn.gov.in (Regulated Markets + Uzhavar Santhai).

Names, locations and facilities are real. The source has no prices, so each
market is given demo price history derived from the existing Tamil Nadu demo
series (like every other price in this prototype). Only rows with usable
coordinates are loaded. PRICED_SQL filters to markets that have prices.
"""
from __future__ import annotations

import csv
import os
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "gramai.db")
CSV_PATH = os.path.join(BASE, "data", "tn_markets.csv")
SOURCE = "agrimark.tn.gov.in"

# The page states that traders pay 1% of sale value at Regulated Markets and
# that farmers pay nothing; Uzhavar Santhai charge no market fee.
FEE_PCT = {"Regulated Market": 1.0, "Uzhavar Santhai": 0.0}

NEW_COLUMNS = {
    "market_type": "text", "market_committee": "text",
    "storage_godowns": "integer", "storage_capacity": "real",
    "shops": "integer", "opens": "text", "closes": "text",
    "image_url": "text", "source": "text", "source_id": "text",
}

# SQL condition (alias "m") for markets that have price history.
PRICED_SQL = "EXISTS (SELECT 1 FROM prices px WHERE px.market_id=m.id)"


def _facilities(r: dict) -> str:
    if r["market_type"] == "Regulated Market":
        parts = []
        if r["storage_godowns"]:
            parts.append(f"{r['storage_godowns']} storage godowns")
        if r["storage_capacity"]:
            parts.append(f"capacity {r['storage_capacity']}")
        return ", ".join(parts) or "Regulated market yard"
    parts = []
    if r["shops"]:
        parts.append(f"{r['shops']} shops")
    if r["opens"] and r["closes"]:
        parts.append(f"open {r['opens']} - {r['closes']}")
    return ", ".join(parts) or "Farmers' market"


def _int(v):
    return int(float(v)) if v not in (None, "") else None


def init_market_infra(db_path: str = DB) -> int:
    """Add the extra columns and upsert usable rows. Safe to run on every start."""
    if not os.path.exists(CSV_PATH) or not os.path.exists(db_path):
        return 0
    c = sqlite3.connect(db_path, timeout=30)
    try:
        if not c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='markets'").fetchone():
            return 0
        have = {r[1] for r in c.execute("PRAGMA table_info(markets)")}
        for col, typ in NEW_COLUMNS.items():
            if col not in have:
                c.execute(f"ALTER TABLE markets ADD COLUMN {col} {typ}")
        c.execute("CREATE INDEX IF NOT EXISTS idx_prices_market ON prices(market_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_markets_source ON markets(source, source_id)")

        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if r["coords_usable"] == "True"]

        loaded = 0
        for r in rows:
            r["storage_godowns"] = _int(r["storage_godowns"])
            r["storage_capacity"] = _int(r["storage_capacity"])
            r["shops"] = _int(r["shops"])
            # Regulated Market rows name their Market Committee, which is also a district name.
            district = r["district"] or r["market_committee"]
            vals = {
                "name": r["name"], "city": r["name"], "district": district, "state": r["state"],
                "lat": float(r["latitude"]), "lon": float(r["longitude"]),
                "market_fee_pct": FEE_PCT.get(r["market_type"], 0.0),
                "facilities": _facilities(r),
                "market_type": r["market_type"], "market_committee": r["market_committee"] or None,
                "storage_godowns": r["storage_godowns"], "storage_capacity": r["storage_capacity"],
                "shops": r["shops"], "opens": r["opens"] or None, "closes": r["closes"] or None,
                "image_url": r["image_url"] or None, "source": SOURCE, "source_id": r["source_id"],
            }
            existing = c.execute("SELECT id FROM markets WHERE source=? AND source_id=?",
                                 (SOURCE, r["source_id"])).fetchone()
            if existing:
                c.execute("UPDATE markets SET " + ",".join(f"{k}=?" for k in vals) + " WHERE id=?",
                          (*vals.values(), existing[0]))
            else:
                c.execute(f"INSERT INTO markets({','.join(vals)}) VALUES({','.join('?' * len(vals))})",
                          tuple(vals.values()))
            loaded += 1

        # Drop rows that the latest curation no longer marks usable.
        keep = [r["source_id"] for r in rows]
        c.execute(f"DELETE FROM prices WHERE market_id IN (SELECT id FROM markets WHERE source=? "
                  f"AND source_id NOT IN ({','.join('?' * len(keep))}))", (SOURCE, *keep))
        c.execute(f"DELETE FROM markets WHERE source=? AND source_id NOT IN ({','.join('?' * len(keep))})",
                  (SOURCE, *keep))
        _seed_demo_prices(c)
        c.commit()
        return loaded
    finally:
        c.close()


def _seed_demo_prices(c) -> None:
    """Give curated markets demo price history so forecasts can use them.

    agrimark.tn.gov.in publishes no prices, and every price series in this
    prototype is synthetic (see seed.py). Each curated market gets the
    average of the existing Tamil Nadu demo series for the same crop and day,
    shifted by a fixed per-market factor and small daily noise. Markets that
    already have prices are left alone.
    """
    todo = c.execute("SELECT m.id, m.source_id FROM markets m WHERE m.source=? AND NOT "
                     + PRICED_SQL, (SOURCE,)).fetchall()
    if not todo:
        return
    ref = c.execute(
        "SELECT p.crop, p.price_date, avg(p.modal_price), avg(p.arrivals_qtl), avg(p.temperature_c), "
        "avg(p.rainfall_mm), avg(p.demand_index) FROM prices p JOIN markets m ON m.id=p.market_id "
        "WHERE m.state='Tamil Nadu' AND coalesce(m.source,'')<>? GROUP BY p.crop, p.price_date",
        (SOURCE,)).fetchall()
    if not ref:
        return
    import random
    batch = []
    for market_id, source_id in todo:
        rnd = random.Random(source_id)          # same series on every rebuild
        level = rnd.uniform(0.94, 1.06)         # this market's price level
        size = rnd.uniform(0.35, 0.9)           # smaller than the demo APMC yards
        for crop, day, price, arr, temp, rain, demand in ref:
            batch.append((market_id, crop, day,
                          round(price * level * rnd.uniform(0.985, 1.015), 2),
                          round(arr * size * rnd.uniform(0.9, 1.1), 1),
                          round(temp + rnd.uniform(-1.5, 1.5), 1),
                          round(max(0.0, rain + rnd.uniform(-2, 2)), 1),
                          round(max(20.0, min(100.0, demand + rnd.uniform(-6, 6))), 1)))
    c.executemany("INSERT INTO prices(market_id,crop,price_date,modal_price,arrivals_qtl,"
                  "temperature_c,rainfall_mm,demand_index) VALUES(?,?,?,?,?,?,?,?)", batch)


if __name__ == "__main__":
    print("Loaded", init_market_infra(), "Tamil Nadu markets")
