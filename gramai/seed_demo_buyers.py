"""Demo buyers for the "best places to sell" ranking.

Adds, to the existing demo database:
  * Tamil Nadu buyers in the `buyers` table, each with a business classification
  * six verified buyer accounts (password Buyer@123) with open demands for common crops,
    priced from today's mandi prices

The businesses are fictional. Safe to run more than once: anything already present is skipped.

    python seed_demo_buyers.py
"""
import bcrypt
import sqlite3
from datetime import datetime, timedelta, timezone

import app  # noqa: F401  loading the app also creates the geo columns this script needs

DB = "gramai.db"

TN_BUYERS = [
    # name, district, type, crops, rating, payment_score, orders, pay_days
    ("Adyar Family Restaurants", "Chennai", "RESTAURANT", "Tomato, Onion, Potato, Rice", 4.6, 88, 214, 1.5),
    ("Chennai Central Fresh Mart", "Chennai", "RETAIL_CHAIN", "Tomato, Onion, Potato, Banana", 4.7, 91, 402, 1.2),
    ("Kancheepuram Fresh Traders", "Kancheepuram", "WHOLESALE_TRADER", "Tomato, Onion, Banana, Chilli", 4.3, 80, 265, 2.6),
    ("Chengalpattu Agro Procurement", "Chengalpattu", "WHOLESALE_TRADER", "Tomato, Onion, Rice, Maize", 4.4, 83, 188, 2.2),
    ("Tiruvallur Kirana Supply", "Tiruvallur", "KIRANA", "Tomato, Onion, Potato", 4.1, 76, 96, 1.8),
    ("Vellore Sauce & Pickles", "Vellore", "PROCESSOR", "Tomato, Chilli, Turmeric", 4.5, 85, 143, 3.0),
    ("Madurai Meenakshi Caterers", "Madurai", "RESTAURANT", "Tomato, Onion, Rice, Banana", 4.5, 87, 176, 1.4),
    ("Trichy Grain & Pulse Mill", "Tiruchirapalli", "PROCESSOR", "Rice, Maize, Groundnut", 4.4, 82, 231, 3.4),
    ("Salem Turmeric Exporters", "Salem", "EXPORTER", "Turmeric, Chilli, Groundnut", 4.8, 92, 158, 2.0),
    ("Erode Farmers Producer Company", "Erode", "FPO_COOP", "Turmeric, Banana, Maize", 4.6, 89, 122, 2.8),
    ("Tirunelveli Fresh Basket", "Tirunelveli", "RETAIL_CHAIN", "Tomato, Onion, Banana, Potato", 4.6, 90, 310, 1.3),
    ("Thanjavur Rice Traders", "Thanjavur", "WHOLESALE_TRADER", "Rice, Groundnut, Maize", 4.2, 79, 205, 2.9),
]

# email, name, business, type, district, phone, demands: (crop, qtl, price factor vs. market, mode, days)
ACCOUNTS = [
    ("marina.kitchens@gram.ai", "Anitha Ravi", "Marina Kitchens Hotel Group", "RESTAURANT", "Chennai", "9876510001",
     [("Tomato", 15, 1.05, "FARMER_TRANSPORT", 6), ("Onion", 20, 1.04, "FARMER_TRANSPORT", 6)]),
    ("greencart.retail@gram.ai", "Suresh Kumar", "GreenCart Fresh Retail", "RETAIL_CHAIN", "Chengalpattu", "9876510002",
     [("Tomato", 60, 1.04, "BUYER_PICKUP", 8), ("Onion", 80, 1.03, "BUYER_PICKUP", 8), ("Potato", 50, 1.03, "BUYER_PICKUP", 8)]),
    ("koyambedu.traders@gram.ai", "Mohamed Ismail", "Koyambedu Traders & Co", "WHOLESALE_TRADER", "Tiruvallur", "9876510003",
     [("Tomato", 120, 0.99, "BUYER_PICKUP", 5), ("Onion", 100, 0.99, "BUYER_PICKUP", 5), ("Banana", 50, 1.0, "BUYER_PICKUP", 7)]),
    ("madurai.foods@gram.ai", "Lakshmi Narayanan", "Madurai Masala Foods", "PROCESSOR", "Madurai", "9876510004",
     [("Tomato", 200, 0.96, "FLEXIBLE", 10), ("Chilli", 40, 1.02, "FLEXIBLE", 10)]),
    ("trichy.canteens@gram.ai", "Priya Devi", "Trichy Campus Canteens", "INSTITUTION", "Tiruchirapalli", "9876510005",
     [("Rice", 90, 1.02, "FARMER_TRANSPORT", 12), ("Onion", 30, 1.03, "FARMER_TRANSPORT", 12), ("Potato", 25, 1.03, "FARMER_TRANSPORT", 12)]),
    ("salem.exports@gram.ai", "Karthik Subramani", "Salem Spice Exports", "EXPORTER", "Salem", "9876510006",
     [("Turmeric", 60, 1.06, "BUYER_PICKUP", 14), ("Chilli", 45, 1.05, "BUYER_PICKUP", 14)]),
]


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row

    added_b = 0
    for name, district, btype, crops, rating, pay, orders, days in TN_BUYERS:
        if c.execute("SELECT 1 FROM buyers WHERE name=?", (name,)).fetchone():
            continue
        c.execute("""INSERT INTO buyers(name,state,district,crops,rating,verified,payment_score,completed_orders,avg_payment_days,phone,buyer_type)
                     VALUES(?,?,?,?,?,1,?,?,?,?,?)""",
                  (name, "Tamil Nadu", district, crops, rating, pay, orders, days, "+91-9300000%03d" % (added_b + 1), btype))
        added_b += 1

    day = c.execute("SELECT max(price_date) d FROM prices").fetchone()["d"]
    price_of = {}
    for r in c.execute("""SELECT p.crop, avg(p.modal_price) v FROM prices p JOIN markets m ON m.id=p.market_id
                          WHERE p.price_date=? AND m.state='Tamil Nadu' GROUP BY p.crop""", (day,)):
        price_of[r["crop"]] = r["v"]

    added_u = added_d = 0
    for email, name, biz, btype, district, phone, demands in ACCOUNTS:
        u = c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if not u:
            pw = bcrypt.hashpw(b"Buyer@123", bcrypt.gensalt()).decode()
            cur = c.execute("""INSERT INTO users(name,email,password,role,district,state,phone,must_change_password,buyer_type,business_name)
                               VALUES(?,?,?,?,?,?,?,0,?,?)""", (name, email, pw, "buyer", district, "Tamil Nadu", phone, btype, biz))
            uid = cur.lastrowid
            c.execute("""INSERT INTO kyc_profiles(user_id,method,document_type,masked_document,aadhaar_last4,consent,status,selfie_path,live_check,submitted_at,verified_at)
                         VALUES(?,?,?,?,?,1,'VERIFIED','DEMO_LIVE_SELFIE',1,?,?)""",
                      (uid, "AADHAAR", "AADHAAR", "XXXX-XXXX-%04d" % (1000 + uid), "%04d" % (1000 + uid), now(), now()))
            added_u += 1
        else:
            uid = u["id"]
        for crop, qtl, factor, mode, due in demands:
            if c.execute("SELECT 1 FROM buyer_preorder_demands WHERE buyer_id=? AND crop=?", (uid, crop)).fetchone():
                continue
            base = price_of.get(crop)
            if not base:
                continue
            c.execute("""INSERT INTO buyer_preorder_demands(buyer_id,crop,variety,grade_required,quantity_qtl,remaining_quantity_qtl,offer_price,
                            required_by_date,delivery_district,delivery_state,delivery_mode,token_offer,special_requirements,status,created_at,updated_at)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,'OPEN',?,?)""",
                      (uid, crop, "Any", "Any", qtl, qtl, round(base * factor, 0),
                       (datetime.now() + timedelta(days=due)).date().isoformat(), district, "Tamil Nadu", mode, 0,
                       "Grade A/B preferred" if btype in ("RETAIL_CHAIN", "RESTAURANT", "EXPORTER") else "", now(), now()))
            added_d += 1
    c.commit()
    c.close()
    print("Added %d buyers, %d buyer accounts, %d open demands." % (added_b, added_u, added_d))
    print("Demo buyer logins (password Buyer@123): " + ", ".join(a[0] for a in ACCOUNTS))


if __name__ == "__main__":
    main()
