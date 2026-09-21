"""Curate Tamil Nadu market infrastructure data from agrimark.tn.gov.in.

Sources (Department of Agricultural Marketing & Agri Business, Govt. of Tamil Nadu):
  - Regulated Markets  : https://www.agrimark.tn.gov.in/index.php/Infra
  - Uzhavar Santhai    : https://www.agrimark.tn.gov.in/index.php/Infra/us_details

  python data/curate_tn_markets.py            # use cached HTML in data/raw/
  python data/curate_tn_markets.py --refresh  # download the pages again first

Writes to data/:
  tn_regulated_markets.csv, tn_uzhavar_santhai.csv, tn_markets.csv (both combined)
  tn_markets_quality.json (counts + every row whose coordinates were flagged)

Coordinates come from each row's "Map View" link. They are cleaned where the
intent is unambiguous (stray N/E/degree marks, a trailing comma, a missing
decimal point) and then checked against Tamil Nadu's bounding box and the
distance to the row's district headquarters. Nothing is guessed: a coordinate
that cannot be read or fails the checks is kept in raw_lat/raw_lon, flagged,
and left empty in latitude/longitude.
"""
from __future__ import annotations

import csv
import html
import json
import math
import os
import re
import sys
import urllib.parse
from collections import Counter
from datetime import date

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "raw")
SOURCES = {
    "regulated_market": ("https://www.agrimark.tn.gov.in/index.php/Infra", "Infra.html"),
    "uzhavar_santhai": ("https://www.agrimark.tn.gov.in/index.php/Infra/us_details", "Infra_us_details.html"),
}

# Tamil Nadu bounding box (with a small margin).
LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = 8.0, 13.6, 76.2, 80.4

# Approximate district headquarters, used only to sanity-check coordinates.
DISTRICT_HQ = {
    "Ariyalur": (11.14, 79.08), "Chengalpattu": (12.69, 79.98), "Chennai": (13.08, 80.27),
    "Coimbatore": (11.02, 76.96), "Cuddalore": (11.75, 79.75), "Dharmapuri": (12.13, 78.16),
    "Dindigul": (10.36, 77.98), "Erode": (11.34, 77.72), "Kallakurichi": (11.74, 78.96),
    "Kancheepuram": (12.83, 79.70), "Kanniyakumari": (8.18, 77.41), "Karur": (10.96, 78.08),
    "Krishnagiri": (12.52, 78.21), "Madurai": (9.93, 78.12), "Mayiladuthurai": (11.10, 79.65),
    "Nagapattinam": (10.77, 79.84), "Namakkal": (11.22, 78.17), "The Nilgiris": (11.41, 76.70),
    "Perambalur": (11.23, 78.88), "Pudukkottai": (10.38, 78.82), "Ramanathapuram": (9.37, 78.83),
    "Ranipet": (12.93, 79.33), "Salem": (11.66, 78.15), "Sivagangai": (9.85, 78.48),
    "Tenkasi": (8.96, 77.30), "Thanjavur": (10.79, 79.14), "Theni": (10.01, 77.48),
    "Thoothukudi": (8.76, 78.13), "Tiruchirapalli": (10.80, 78.69), "Tirunelveli": (8.71, 77.76),
    "Tirupattur": (12.50, 78.57), "Tiruppur": (11.11, 77.34), "Tiruvallur": (13.14, 79.91),
    "Thiruvannamalai": (12.23, 79.07), "Tiruvarur": (10.77, 79.64), "Vellore": (12.92, 79.13),
    "Villupuram": (11.94, 79.49), "Virudhunagar": (9.58, 77.96),
}
DISTRICT_ALIASES = {"TheNilgiris": "The Nilgiris", "Tiruvannamalai": "Thiruvannamalai"}

# Distance from the district HQ. Beyond REVIEW_KM the point is kept but marked
# for review (large districts such as Thiruvannamalai or Erode legitimately
# reach this far). Beyond REJECT_KM it is treated as wrong. Regulated Market
# rows name a Market Committee, which can span neighbouring districts.
REVIEW_KM = {"uzhavar_santhai": 60, "regulated_market": 90}
REJECT_KM = 100


def fetch(refresh: bool) -> dict[str, str]:
    os.makedirs(RAW, exist_ok=True)
    pages = {}
    for kind, (url, fname) in SOURCES.items():
        path = os.path.join(RAW, fname)
        if refresh or not os.path.exists(path):
            import requests
            r = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            with open(path, "w", encoding="utf-8") as f:
                f.write(r.text)
        with open(path, encoding="utf-8", errors="replace") as f:
            pages[kind] = f.read()
    return pages


def cell_text(s: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s)).split())


def rows(page: str):
    """Yield (cells, map_link, image_link) for each numbered data row."""
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S | re.I):
        cells = [cell_text(td) for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S | re.I)]
        if not cells or not cells[0].isdigit():
            continue
        m = re.search(r"""href=["']([^"']*map_view[^"']*)["']""", tr)
        img = re.search(r"""<img[^>]+src=["']([^"']*)["']""", tr)
        yield cells, (m.group(1) if m else ""), (img.group(1) if img else "")


def parse_map_link(link: str):
    m = re.search(r"map_view/([^/]*)/([^/]*)/(rm|us)/(\d+)", link)
    if not m:
        return "", "", ""
    lat, lon = (urllib.parse.unquote(x).strip() for x in m.group(1, 2))
    return lat, lon, m.group(4)


def clean_coord(raw: str, lo: float, hi: float):
    """Return (value, repaired) or (None, False) when the text can't be trusted."""
    s = raw.strip().rstrip(",")
    s2 = re.sub(r"^[NE]\s*|\s*°?\s*[NE]$|°", "", s).strip()
    if re.fullmatch(r"0?\d{1,2}\.\d+", s2):
        return float(s2), s2 != raw.strip()
    # Missing decimal point, e.g. "9418036" -> 9.418036. Accept only if exactly
    # one placement lands inside the expected range.
    if re.fullmatch(r"\d{6,11}", s2):
        fits = [float(s2[:k] + "." + s2[k:]) for k in (1, 2) if lo <= float(s2[:k] + "." + s2[k:]) <= hi]
        if len(fits) == 1:
            return fits[0], True
    return None, False


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def to_int(s: str):
    s = s.replace(",", "").strip()
    return int(s) if s.isdigit() else None


def build(pages: dict[str, str]) -> list[dict]:
    today = date.today().isoformat()
    out = []
    for kind, page in pages.items():
        url = SOURCES[kind][0]
        for cells, link, img in rows(page):
            raw_lat, raw_lon, site_id = parse_map_link(link)
            if kind == "regulated_market":
                # S.No | Committee | Market | Godowns | Capacity | Image | Map
                district = cells[1]
                rec = {
                    "market_type": "Regulated Market",
                    "name": cells[2],
                    "district": "",
                    "market_committee": cells[1],
                    "storage_godowns": to_int(cells[3]),
                    # 0 on the source page means "not reported", not an empty godown.
                    "storage_capacity": to_int(cells[4]) or None,
                    "shops": None, "opens": "", "closes": "",
                }
            else:
                # S.No | District | Uzhavar Santhai | Shops | From | To | Image | Map
                district = DISTRICT_ALIASES.get(cells[1], cells[1])
                rec = {
                    "market_type": "Uzhavar Santhai",
                    "name": cells[2],
                    "district": district,
                    "market_committee": "",
                    "storage_godowns": None, "storage_capacity": None,
                    "shops": to_int(cells[3]), "opens": cells[4], "closes": cells[5],
                }
            lat, lat_fix = clean_coord(raw_lat, LAT_MIN, LAT_MAX) if raw_lat else (None, False)
            lon, lon_fix = clean_coord(raw_lon, LON_MIN, LON_MAX) if raw_lon else (None, False)

            flags = []
            if not raw_lat or not raw_lon:
                flags.append("missing")
            elif lat is None or lon is None:
                flags.append("unreadable")
            else:
                if lat_fix or lon_fix:
                    flags.append("repaired_format")
                if not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
                    flags.append("outside_tamil_nadu")
                elif district in DISTRICT_HQ:
                    d = km((lat, lon), DISTRICT_HQ[district])
                    if d > REJECT_KM:
                        flags.append(f"far_from_district_hq_{round(d)}km")
                    elif d > REVIEW_KM[kind]:
                        flags.append(f"review_distance_{round(d)}km")
                if len(raw_lat.split(".")[-1]) <= 2 and len(raw_lon.split(".")[-1]) <= 2:
                    flags.append("low_precision")
            bad = any(f in ("missing", "unreadable", "outside_tamil_nadu") or f.startswith("far_") for f in flags)
            rec.update({
                # S.No is unique per page; the site's own id is sometimes missing or reused.
                "source_id": f"{'rm' if kind == 'regulated_market' else 'us'}-{cells[0]}",
                "site_id": site_id,
                "state": "Tamil Nadu",
                "latitude": None if bad else round(lat, 6),
                "longitude": None if bad else round(lon, 6),
                "coords_usable": not bad,
                "coord_flags": ";".join(flags) or "ok",
                "raw_lat": raw_lat, "raw_lon": raw_lon,
                "image_url": img if re.search(r"\.(jpe?g|png)$", img, re.I) else "",
                "source_url": url, "retrieved_on": today,
            })
            out.append(rec)

    # Two different markets sharing identical coordinates means at least one is a copy-paste.
    seen = Counter((r["latitude"], r["longitude"]) for r in out if r["coords_usable"])
    for r in out:
        if r["coords_usable"] and seen[(r["latitude"], r["longitude"])] > 1:
            r["coord_flags"] = "duplicate_coordinates" if r["coord_flags"] == "ok" else r["coord_flags"] + ";duplicate_coordinates"
    return out


COLUMNS = ["source_id", "site_id", "market_type", "name", "district", "market_committee", "state",
           "latitude", "longitude", "coords_usable", "coord_flags",
           "storage_godowns", "storage_capacity", "shops", "opens", "closes",
           "raw_lat", "raw_lon", "image_url", "source_url", "retrieved_on"]


def write_csv(path, recs):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in recs:
            w.writerow({k: ("" if r[k] is None else r[k]) for k in COLUMNS})


def main():
    recs = build(fetch("--refresh" in sys.argv))
    rm = [r for r in recs if r["market_type"] == "Regulated Market"]
    us = [r for r in recs if r["market_type"] == "Uzhavar Santhai"]
    write_csv(os.path.join(BASE, "tn_regulated_markets.csv"), rm)
    write_csv(os.path.join(BASE, "tn_uzhavar_santhai.csv"), us)
    write_csv(os.path.join(BASE, "tn_markets.csv"), recs)

    flag_counts = Counter(re.sub(r"_(hq_)?\d+km$", "", f) for r in recs for f in r["coord_flags"].split(";"))
    report = {
        "retrieved_on": date.today().isoformat(),
        "regulated_markets": len(rm), "uzhavar_santhai": len(us), "total": len(recs),
        "coords_usable": sum(r["coords_usable"] for r in recs),
        "flag_counts": dict(flag_counts),
        "flagged_rows": [{k: r[k] for k in ("source_id", "market_type", "name", "district",
                                            "market_committee", "raw_lat", "raw_lon", "coord_flags")}
                         for r in recs if r["coord_flags"] not in ("ok",)],
    }
    with open(os.path.join(BASE, "tn_markets_quality.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps({k: v for k, v in report.items() if k != "flagged_rows"}, indent=2))


if __name__ == "__main__":
    main()
