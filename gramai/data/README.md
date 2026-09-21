# Tamil Nadu market infrastructure dataset

Curated from the Department of Agricultural Marketing & Agri Business, Government of Tamil Nadu:

| Source page | What it lists | Rows |
|---|---|---|
| https://www.agrimark.tn.gov.in/index.php/Infra | Regulated Markets (APMC), with storage godowns and capacity | 138 |
| https://www.agrimark.tn.gov.in/index.php/Infra/us_details | Uzhavar Santhai (farmers' markets), with shop count and hours | 194 |

These pages describe **market infrastructure only**. They contain no crop prices or arrivals.

## How the app uses it

On startup, `market_infra.py` loads every row with `coords_usable = True` into the `markets` table. That is 318 markets, and reloading updates them in place. They appear in Link India → Tamil Nadu (market cards, map and details popup), in the forecast market dropdown and in the "markets near you" comparison.

Names, locations, facilities, working hours and market fees are real. As with every other market in this prototype, the **price history is demo data**: each market gets the existing Tamil Nadu demo series for each crop and day, shifted by a fixed per-market factor. Replace it with AGMARKNET / e-NAM prices before using forecasts for real decisions.

## Files

| File | Contents |
|---|---|
| `tn_markets.csv` | Both sources combined (332 rows) |
| `tn_regulated_markets.csv` | Regulated Markets only |
| `tn_uzhavar_santhai.csv` | Uzhavar Santhai only |
| `tn_markets_quality.json` | Flag counts, plus every row whose coordinates needed attention |
| `raw/*.html` | Snapshot of the two source pages that the CSVs were built from |
| `curate_tn_markets.py` | The curation script |

To rebuild the CSVs:

```
python data/curate_tn_markets.py            # from the saved snapshot
python data/curate_tn_markets.py --refresh  # download the pages again first
```

## Columns

| Column | Meaning |
|---|---|
| `source_id` | `rm-<S.No>` or `us-<S.No>`, using the row number on the source page |
| `site_id` | The site's own id, taken from the Map View link (sometimes missing) |
| `market_type` | `Regulated Market` or `Uzhavar Santhai` |
| `name` | Market name, as spelled on the source page |
| `district` | District (Uzhavar Santhai only) |
| `market_committee` | Market Committee (Regulated Markets only). A committee can cover more than one district, e.g. Karur is listed under Tiruchirapalli |
| `latitude`, `longitude` | Cleaned coordinates. Empty when `coords_usable` is false |
| `coords_usable` | `True` if the coordinates passed validation |
| `coord_flags` | Why a row needs attention (see below). `ok` means no issues |
| `storage_godowns` | Number of storage godowns (Regulated Markets) |
| `storage_capacity` | Godown capacity. The page does not state the unit (likely metric tonnes). A `0` on the page is stored as empty, meaning "not reported" |
| `shops` | Number of shops (Uzhavar Santhai) |
| `opens`, `closes` | Working hours (Uzhavar Santhai) |
| `raw_lat`, `raw_lon` | Coordinates exactly as they appear in the source link |
| `image_url`, `source_url`, `retrieved_on` | Where each row came from, and when |

## Coordinate quality

The source coordinates are hand-entered and inconsistent. Each row is checked against Tamil Nadu's bounding box and the distance to its district headquarters. Nothing is guessed: coordinates that fail are left empty, and the original text stays in `raw_lat`/`raw_lon`.

| Flag | Meaning | Usable? |
|---|---|---|
| `ok` | Clean decimal coordinates | Yes |
| `repaired_format` | Stray `N`/`E`/`°`, a trailing comma, or a missing decimal point was fixed | Yes |
| `low_precision` | Only 2 decimal places (roughly 1 km) | Yes |
| `duplicate_coordinates` | Identical to another market, so at least one of them is a copy | Yes, but approximate |
| `review_distance_<N>km` | 60–100 km from the district HQ. Often correct in large districts, sometimes a data-entry error | Yes, review before relying on it |
| `far_from_district_hq_<N>km` | More than 100 km from the district HQ | No |
| `unreadable` | Not a decimal coordinate (e.g. `35.2c`, `9.32.70.04° N`) | No |
| `missing` | No coordinates in the source | No |

At the snapshot of 2026-09-21: 318 of 332 rows have usable coordinates. The 14 unusable rows are 6 `missing`, 4 `unreadable` and 4 `far_from_district_hq`. Another 15 rows are marked `review_distance`. `tn_markets_quality.json` lists every flagged row.
