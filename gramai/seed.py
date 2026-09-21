import sqlite3
import os
import random
import math

from datetime import date, timedelta
import bcrypt


# =========================================================
# DATABASE
# =========================================================

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "gramai.db")

random.seed(42)


# =========================================================
# STATES / UNION TERRITORIES
# =========================================================

STATES = [

    ("Andhra Pradesh", "Vijayawada", 16.5062, 80.6480),
    ("Arunachal Pradesh", "Itanagar", 27.0844, 93.6053),
    ("Assam", "Guwahati", 26.1445, 91.7362),
    ("Bihar", "Patna", 25.5941, 85.1376),
    ("Chhattisgarh", "Raipur", 21.2514, 81.6296),
    ("Goa", "Panaji", 15.4909, 73.8278),
    ("Gujarat", "Ahmedabad", 23.0225, 72.5714),
    ("Haryana", "Karnal", 29.6857, 76.9905),
    ("Himachal Pradesh", "Shimla", 31.1048, 77.1734),
    ("Jharkhand", "Ranchi", 23.3441, 85.3096),
    ("Karnataka", "Bengaluru", 12.9716, 77.5946),
    ("Kerala", "Kochi", 9.9312, 76.2673),
    ("Madhya Pradesh", "Indore", 22.7196, 75.8577),
    ("Maharashtra", "Pune", 18.5204, 73.8567),
    ("Manipur", "Imphal", 24.8170, 93.9368),
    ("Meghalaya", "Shillong", 25.5788, 91.8933),
    ("Mizoram", "Aizawl", 23.7271, 92.7176),
    ("Nagaland", "Dimapur", 25.9091, 93.7266),
    ("Odisha", "Bhubaneswar", 20.2961, 85.8245),
    ("Punjab", "Ludhiana", 30.9010, 75.8573),
    ("Rajasthan", "Jaipur", 26.9124, 75.7873),
    ("Sikkim", "Gangtok", 27.3389, 88.6065),
    ("Tamil Nadu", "Coimbatore", 11.0168, 76.9558),
    ("Telangana", "Hyderabad", 17.3850, 78.4867),
    ("Tripura", "Agartala", 23.8315, 91.2868),
    ("Uttar Pradesh", "Lucknow", 26.8467, 80.9462),
    ("Uttarakhand", "Dehradun", 30.3165, 78.0322),
    ("West Bengal", "Kolkata", 22.5726, 88.3639),

    ("Andaman and Nicobar Islands", "Port Blair", 11.6234, 92.7265),
    ("Chandigarh", "Chandigarh", 30.7333, 76.7794),
    (
        "Dadra and Nagar Haveli and Daman and Diu",
        "Daman",
        20.3974,
        72.8328
    ),
    ("Delhi", "Delhi", 28.6139, 77.2090),
    ("Jammu and Kashmir", "Jammu", 32.7266, 74.8570),
    ("Ladakh", "Leh", 34.1526, 77.5771),
    ("Lakshadweep", "Kavaratti", 10.5667, 72.6420),
    ("Puducherry", "Puducherry", 11.9416, 79.8083)

]


# =========================================================
# CROPS
# =========================================================

CROPS = [

    ("Tomato", "Vegetable", 2100),
    ("Onion", "Vegetable", 1850),
    ("Potato", "Vegetable", 1650),

    ("Wheat", "Cereal", 2450),
    ("Rice", "Cereal", 2850),
    ("Maize", "Cereal", 2250),

    ("Soybean", "Oilseed", 4650),
    ("Groundnut", "Oilseed", 5750),

    ("Cotton", "Commercial", 7200),

    ("Chilli", "Spice", 11200),
    ("Turmeric", "Spice", 9500),

    ("Banana", "Fruit", 3100)

]


# =========================================================
# IMPORTANT STATE CROPS
# Used for Link India demo listings
# =========================================================

STATE_CROPS = {

    "Maharashtra": [
        "Tomato",
        "Onion",
        "Soybean",
        "Banana"
    ],

    "Punjab": [
        "Wheat",
        "Rice",
        "Maize",
        "Potato"
    ],

    "Gujarat": [
        "Groundnut",
        "Cotton",
        "Wheat",
        "Onion"
    ],

    "Karnataka": [
        "Tomato",
        "Maize",
        "Groundnut",
        "Turmeric"
    ],

    "Tamil Nadu": [
        "Banana",
        "Rice",
        "Tomato",
        "Turmeric"
    ],

    "Telangana": [
        "Chilli",
        "Cotton",
        "Rice",
        "Maize"
    ],

    "Andhra Pradesh": [
        "Chilli",
        "Rice",
        "Groundnut",
        "Banana"
    ],

    "Madhya Pradesh": [
        "Soybean",
        "Wheat",
        "Maize",
        "Onion"
    ],

    "Uttar Pradesh": [
        "Wheat",
        "Potato",
        "Rice",
        "Tomato"
    ],

    "Haryana": [
        "Wheat",
        "Rice",
        "Potato",
        "Maize"
    ],

    "Rajasthan": [
        "Wheat",
        "Groundnut",
        "Maize",
        "Onion"
    ],

    "West Bengal": [
        "Rice",
        "Potato",
        "Tomato",
        "Maize"
    ],

    "Bihar": [
        "Maize",
        "Rice",
        "Wheat",
        "Potato"
    ],

    "Odisha": [
        "Rice",
        "Groundnut",
        "Maize",
        "Tomato"
    ],

    "Kerala": [
        "Banana",
        "Turmeric",
        "Rice",
        "Tomato"
    ],

    "Assam": [
        "Rice",
        "Banana",
        "Maize",
        "Potato"
    ]

}


# =========================================================
# PASSWORD HASH
# =========================================================

def hpw(password):

    return bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt()
    ).decode()


# =========================================================
# RESET DATABASE
# =========================================================

if os.path.exists(DB):

    os.remove(DB)


con = sqlite3.connect(DB)

cur = con.cursor()


# =========================================================
# TABLES
# =========================================================

cur.executescript("""

create table users(

    id integer primary key autoincrement,

    name text not null,

    email text unique not null,

    password text not null,

    role text not null,

    district text default '',

    state text default '',

    phone text default '',

    address text default '',

    farm_size_acres real default 0,

    preferred_language text default 'English',

    bank_account_name text default '',

    bank_account_last4 text default '',

    bank_ifsc text default '',

    upi_id text default '',

    must_change_password integer default 0

);


create table email_outbox(

    id integer primary key autoincrement,

    to_email text not null,

    subject text not null,

    body text not null,

    sent integer default 0,

    error text default '',

    created_at text not null

);


create table markets(

    id integer primary key autoincrement,

    name text,

    city text,

    district text,

    state text,

    lat real,

    lon real,

    market_fee_pct real,

    facilities text

);


create table crops(

    id integer primary key autoincrement,

    name text unique,

    category text

);


create table prices(

    id integer primary key autoincrement,

    market_id integer,

    crop text,

    price_date text,

    modal_price real,

    arrivals_qtl real,

    temperature_c real,

    rainfall_mm real,

    demand_index real

);


create table buyers(

    id integer primary key autoincrement,

    name text,

    state text,

    district text,

    crops text,

    rating real,

    verified integer,

    payment_score integer,

    completed_orders integer,

    avg_payment_days real,

    phone text

);


create table transporters(

    id integer primary key autoincrement,

    name text,

    state text,

    vehicle_type text,

    capacity_qtl real,

    rate_per_km real,

    rating real,

    verified integer,

    phone text,

    gps_enabled integer

);


create table listings(

    id integer primary key autoincrement,

    seller_id integer not null,

    crop text not null,

    variety text default 'Standard',

    grade text default 'A',

    quantity_qtl real not null,

    ask_price real not null,

    district text,

    state text,

    harvest_date text,

    packaging text default 'Bags / crates',

    min_order_qtl real default 1,

    seller_transport integer default 0,

    transport_cost_per_km real default 0,

    delivery_radius_km real default 0,

    loading_included integer default 0,

    quality_notes text default '',

    image_url text default '',

    status text default 'OPEN',

    created_at text

);


create table orders(

    id integer primary key autoincrement,

    buyer_id integer,

    listing_id integer,

    quantity_qtl real,

    produce_total real default 0,

    transport_total real default 0,

    platform_fee real default 0,

    total real default 0,

    delivery_mode text,

    status text,

    created_at text

);


create table negotiations(

    id integer primary key autoincrement,

    user_id integer,

    listing_id integer,

    offer_price real,

    message text,

    status text,

    created_at text

);


create table notifications(

    id integer primary key autoincrement,

    user_id integer,

    title text,

    message text,

    severity text,

    created_at text

);


create table audit_logs(

    id integer primary key autoincrement,

    user_id integer,

    action text,

    details text,

    created_at text

);


create index idx_users_email
on users(email);


create index idx_prices_crop_market_date
on prices(crop, market_id, price_date);


create index idx_listings_status
on listings(status);


create index idx_listings_state
on listings(state);


create index idx_markets_state
on markets(state);

""")


# =========================================================
# MAIN DEMO ACCOUNTS
# =========================================================

users = [

    (
        "Demo Farmer",
        "farmer@gram.ai",
        hpw("Farmer@123"),
        "farmer",
        "Coimbatore",
        "Tamil Nadu",
        "9876543210",
        "Coimbatore, Tamil Nadu",
        7.5,
        "English",
        "Demo Farmer",
        "4321",
        "SBIN0001234",
        "farmer@upi",
        0
    ),

    (
        "Demo Buyer",
        "buyer@gram.ai",
        hpw("Buyer@123"),
        "buyer",
        "Chennai",
        "Tamil Nadu",
        "9876500000",
        "Chennai, Tamil Nadu",
        0,
        "English",
        "Demo Buyer",
        "6789",
        "HDFC0001111",
        "buyer@upi",
        0
    ),

    (
        "Mission Admin",
        "admin@gram.ai",
        hpw("Admin@123"),
        "admin",
        "Delhi",
        "Delhi",
        "9999999999",
        "New Delhi",
        0,
        "English",
        "",
        "",
        "",
        "",
        0
    )

]


cur.executemany("""

insert into users(

    name,
    email,
    password,
    role,
    district,
    state,
    phone,
    address,
    farm_size_acres,
    preferred_language,
    bank_account_name,
    bank_account_last4,
    bank_ifsc,
    upi_id,
    must_change_password

)

values(
    ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
)

""", users)


# =========================================================
# ADD CROPS
# =========================================================

cur.executemany(

    "insert into crops(name,category) values(?,?)",

    [
        (crop, category)

        for crop, category, base_price
        in CROPS
    ]

)


# =========================================================
# BASE PRICE LOOKUP
# =========================================================

BASE_PRICE = {

    crop: base

    for crop, category, base
    in CROPS

}


# =========================================================
# CREATE ALL INDIA MARKETS + 30 DAY PRICE HISTORY
# =========================================================

market_ids = {}


for si, (
    state,
    city,
    lat,
    lon
) in enumerate(STATES):


    market_ids[state] = []


    for j in range(2):


        market_name = (

            f"{city} Central APMC"

            if j == 0

            else

            f"{city} Regional Mandi"

        )


        mlat = (
            lat +
            (j * 0.19 - 0.07)
        )


        mlon = (
            lon +
            (j * 0.16 - 0.05)
        )


        fee = round(

            0.7 +
            (si % 6) * 0.22 +
            j * 0.12,

            2

        )


        facilities = (

            "e-auction, digital weighing, storage, "
            "quality testing, digital payments, loading bay"

        )


        cur.execute("""

            insert into markets(

                name,
                city,
                district,
                state,
                lat,
                lon,
                market_fee_pct,
                facilities

            )

            values(
                ?,?,?,?,?,?,?,?
            )

        """, (

            market_name,
            city,
            city,
            state,
            mlat,
            mlon,
            fee,
            facilities

        ))


        market_id = cur.lastrowid


        market_ids[state].append(
            market_id
        )


        # =============================================
        # PRICE HISTORY FOR ML FORECASTING
        # =============================================

        for (
            crop,
            category,
            base_price
        ) in CROPS:


            state_factor = (

                1 +

                (
                    (si % 9) - 4
                ) * 0.018

                +

                j * 0.012

            )


            for days_ago in range(30):


                d = (

                    date.today()

                    -

                    timedelta(
                        days=days_ago
                    )

                )


                seasonal = (

                    1 +

                    0.035 *

                    math.sin(

                        (
                            si +
                            days_ago +
                            j
                        ) * 0.55

                    )

                )


                price_noise = (

                    1 +

                    random.uniform(
                        -0.028,
                        0.028
                    )

                )


                arrival_cycle = (

                    1 +

                    0.18 *

                    math.sin(

                        (
                            days_ago +
                            si
                        ) * 0.41

                    )

                )


                arrivals = max(

                    45,

                    (
                        250 +

                        (
                            (
                                si * 31 +

                                j * 47 +

                                len(crop) * 23

                            ) % 420
                        )

                    )

                    * arrival_cycle

                    +

                    random.uniform(
                        -35,
                        35
                    )

                )


                demand = max(

                    20,

                    min(

                        100,

                        62 +

                        18 *

                        math.sin(

                            (
                                si +
                                days_ago
                            ) * 0.33

                        )

                        +

                        random.uniform(
                            -8,
                            8
                        )

                    )

                )


                temperature = (

                    20 +

                    (si % 10)

                    +

                    4 *

                    math.sin(
                        days_ago * 0.2
                    )

                )


                rainfall = max(

                    0,

                    12 *

                    math.sin(

                        (
                            days_ago +
                            si
                        ) * 0.27

                    )

                    +

                    random.uniform(
                        -3,
                        5
                    )

                )


                scarcity = (

                    1 +

                    max(

                        -0.04,

                        min(

                            0.06,

                            (
                                450 -
                                arrivals
                            ) / 9000

                        )

                    )

                )


                demand_factor = (

                    1 +

                    (
                        demand -
                        60
                    ) / 900

                )


                price = round(

                    base_price

                    * state_factor

                    * seasonal

                    * price_noise

                    * scarcity

                    * demand_factor,

                    2

                )


                cur.execute("""

                    insert into prices(

                        market_id,
                        crop,
                        price_date,
                        modal_price,
                        arrivals_qtl,
                        temperature_c,
                        rainfall_mm,
                        demand_index

                    )

                    values(
                        ?,?,?,?,?,?,?,?
                    )

                """, (

                    market_id,
                    crop,
                    d.isoformat(),
                    price,
                    round(arrivals, 1),
                    round(temperature, 1),
                    round(rainfall, 1),
                    round(demand, 1)

                ))


# =========================================================
# BUYERS + TRANSPORTERS FOR EVERY STATE
# =========================================================

for i, (
    state,
    city,
    lat,
    lon
) in enumerate(STATES):


    for j in range(2):


        cur.execute("""

            insert into buyers(

                name,
                state,
                district,
                crops,
                rating,
                verified,
                payment_score,
                completed_orders,
                avg_payment_days,
                phone

            )

            values(
                ?,?,?,?,?,?,?,?,?,?
            )

        """, (

            f"{city} "
            + (
                "Fresh Foods"

                if j == 0

                else

                "Agro Procurement Co."
            ),

            state,

            city,

            "Tomato, Onion, Wheat, Rice, Maize, Soybean, Banana",

            round(
                4.1 +
                (i % 8) * 0.1 +
                j * 0.05,
                1
            ),

            1,

            min(
                99,
                82 + (i % 18)
            ),

            120 +
            i * 8 +
            j * 35,

            round(
                1.3 +
                (i % 5) * 0.3,
                1
            ),

            f"+91-9{i % 10}{j}000{i:04d}"

        ))


        cur.execute("""

            insert into transporters(

                name,
                state,
                vehicle_type,
                capacity_qtl,
                rate_per_km,
                rating,
                verified,
                phone,
                gps_enabled

            )

            values(
                ?,?,?,?,?,?,?,?,?
            )

        """, (

            f"{city} "
            + (
                "Agri Logistics"

                if j == 0

                else

                "Farm2Market Transport"
            ),

            state,

            (
                "Refrigerated Truck"

                if j == 0

                else

                "Medium Goods Vehicle"
            ),

            (
                120

                if j == 0

                else

                70
            ),

            round(

                18.5 +

                (i % 7) * 1.2 +

                j * 2.5,

                1

            ),

            round(

                min(
                    4.9,
                    4.0 +
                    (i % 9) * 0.1
                ),

                1

            ),

            1,

            f"+91-8{i % 10}{j}111{i:04d}",

            1

        ))


# =========================================================
# EXISTING TAMIL NADU DEMO LISTINGS
#
# KEEP DEMO FARMER ID = 1
# =========================================================

for idx, (
    crop,
    category,
    base_price
) in enumerate(CROPS[:8]):


    seller_transport = (

        1

        if idx % 2 == 0

        else

        0

    )


    cur.execute("""

        insert into listings(

            seller_id,
            crop,
            variety,
            grade,
            quantity_qtl,
            ask_price,
            district,
            state,
            harvest_date,
            packaging,
            min_order_qtl,
            seller_transport,
            transport_cost_per_km,
            delivery_radius_km,
            loading_included,
            quality_notes,
            image_url,
            status,
            created_at

        )

        values(
            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
            'OPEN',
            datetime('now')
        )

    """, (

        1,

        crop,

        (
            "Premium"

            if idx % 2 == 0

            else

            "Standard"
        ),

        "A",

        20 +
        idx * 5,

        round(
            base_price *
            (
                0.96 +
                idx * 0.009
            ),
            0
        ),

        "Coimbatore",

        "Tamil Nadu",

        date.today().isoformat(),

        (
            "Crates"

            if crop in (
                "Tomato",
                "Potato",
                "Banana"
            )

            else

            "Bags"
        ),

        2,

        seller_transport,

        (
            22 + idx

            if seller_transport

            else

            0
        ),

        (
            300 +
            idx * 20

            if seller_transport

            else

            0
        ),

        (
            1

            if seller_transport

            else

            0
        ),

        (
            "Fresh, cleaned, sorted and "
            "quality checked."
        ),

        ""

    ))


# =========================================================
# LINK INDIA DEMO FARMERS + LISTINGS
# =========================================================

link_india_farmer_count = 0
link_india_listing_count = 0


for state_index, (
    state,
    city,
    lat,
    lon
) in enumerate(STATES):


# Keep original Tamil Nadu Demo Farmer.
# We do not need another primary Tamil Nadu account.

    if state == "Tamil Nadu":

        continue


    # -----------------------------------------------------
    # CREATE A DEMO FARMER USER FOR THIS STATE
    # -----------------------------------------------------

    safe_city = (

        city.lower()

        .replace(" ", "")

        .replace("-", "")

    )


    email = (
        f"farmer.{safe_city}@gram.ai"
    )


    farmer_name = (
        f"{city} Network Farmer"
    )


    phone = (
        f"98{state_index:08d}"[-10:]
    )


    cur.execute("""

        insert into users(

            name,
            email,
            password,
            role,
            district,
            state,
            phone,
            address,
            farm_size_acres,
            preferred_language,
            bank_account_name,
            bank_account_last4,
            bank_ifsc,
            upi_id,
            must_change_password

        )

        values(
            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
        )

    """, (

        farmer_name,

        email,

        hpw("Farmer@123"),

        "farmer",

        city,

        state,

        phone,

        f"{city}, {state}",

        round(
            4.5 +
            (
                state_index % 8
            ) * 0.8,
            1
        ),

        "English",

        farmer_name,

        f"{3000 + state_index}"[-4:],

        "SBIN0001234",

        f"{safe_city}.farmer@upi",

        0

    ))


    farmer_id = cur.lastrowid


    link_india_farmer_count += 1


    # -----------------------------------------------------
    # CHOOSE CROPS
    # -----------------------------------------------------

    selected_crops = (

        STATE_CROPS.get(
            state
        )

        or

        [
            CROPS[
                (
                    state_index +
                    shift
                ) % len(CROPS)
            ][0]

            for shift in range(4)
        ]

    )


    # -----------------------------------------------------
    # CREATE PRODUCE LISTINGS
    # -----------------------------------------------------

    for listing_index, crop in enumerate(
        selected_crops[:4]
    ):


        base_price = BASE_PRICE.get(
            crop,
            2500
        )


        quantity = (

            15

            +

            (
                (
                    state_index * 7
                )

                +

                listing_index * 11

            ) % 70

        )


        state_price_factor = (

            0.94

            +

            (
                state_index % 8
            ) * 0.018

        )


        ask_price = round(

            base_price

            *

            state_price_factor

            *

            (
                1 +

                listing_index *
                0.012
            ),

            0

        )


        grade = (

            "A"

            if listing_index < 2

            else

            "B"

        )


        seller_transport = (

            1

            if listing_index % 2 == 0

            else

            0

        )


        transport_rate = (

            round(

                19 +

                (
                    state_index % 7
                ) * 1.4

                +

                listing_index,

                1

            )

            if seller_transport

            else

            0

        )


        delivery_radius = (

            180 +

            (
                state_index % 6
            ) * 40

            if seller_transport

            else

            0

        )


        packaging = (

            "Crates"

            if crop in (
                "Tomato",
                "Potato",
                "Banana"
            )

            else

            "Bags"
        )


        harvest_date = (

            date.today()

            +

            timedelta(
                days=listing_index + 1
            )

        ).isoformat()


        cur.execute("""

            insert into listings(

                seller_id,
                crop,
                variety,
                grade,
                quantity_qtl,
                ask_price,
                district,
                state,
                harvest_date,
                packaging,
                min_order_qtl,
                seller_transport,
                transport_cost_per_km,
                delivery_radius_km,
                loading_included,
                quality_notes,
                image_url,
                status,
                created_at

            )

            values(
                ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
                'OPEN',
                datetime('now')
            )

        """, (

            farmer_id,

            crop,

            (
                "Premium"

                if listing_index % 2 == 0

                else

                "Standard"
            ),

            grade,

            quantity,

            ask_price,

            city,

            state,

            harvest_date,

            packaging,

            2,

            seller_transport,

            transport_rate,

            delivery_radius,

            (
                1

                if seller_transport

                else

                0
            ),

            (
                f"GRAM AI Link India demo produce "
                f"from {city}, {state}. "
                f"Sorted and market-ready."
            ),

            ""

        ))


        link_india_listing_count += 1


# =========================================================
# NOTIFICATIONS
# =========================================================

notes = [

    (
        None,
        "National market network online",
        "All-India seeded market coverage is active.",
        "info"
    ),

    (
        None,
        "GPS logistics active",
        "Verified transport providers are available across states.",
        "success"
    ),

    (
        1,
        "Tomato price opportunity",
        "GRAM AI detected higher expected farmer realization in nearby markets.",
        "success"
    ),

    (
        1,
        "Demand signal",
        "Onion demand strengthened across western India.",
        "warning"
    ),

    (
        2,
        "Buyer verification",
        "Buyer profile is verified for digital procurement.",
        "success"
    )

]


for notification in notes:

    cur.execute("""

        insert into notifications(

            user_id,
            title,
            message,
            severity,
            created_at

        )

        values(
            ?,?,?,?,
            datetime('now')
        )

    """, notification)


# =========================================================
# COMMIT
# =========================================================

con.commit()


# =========================================================
# FINAL COUNTS
# =========================================================

market_count = cur.execute(
    "select count(*) from markets"
).fetchone()[0]


listing_count = cur.execute(
    "select count(*) from listings"
).fetchone()[0]


farmer_count = cur.execute(
    """
    select count(*)
    from users
    where role='farmer'
    """
).fetchone()[0]


buyer_count = cur.execute(
    "select count(*) from buyers"
).fetchone()[0]


transporter_count = cur.execute(
    "select count(*) from transporters"
).fetchone()[0]


price_count = cur.execute(
    "select count(*) from prices"
).fetchone()[0]


con.close()


# =========================================================
# DONE
# =========================================================

print()
print("==============================================")
print("GRAM AI DATABASE SEEDED SUCCESSFULLY")
print("==============================================")

print(
    f"States / UTs           : {len(STATES)}"
)

print(
    f"Markets                : {market_count}"
)

print(
    f"Crop types             : {len(CROPS)}"
)

print(
    f"Market price rows       : {price_count}"
)

print(
    f"Farmer accounts         : {farmer_count}"
)

print(
    f"Link India demo farmers : {link_india_farmer_count}"
)

print(
    f"Produce listings        : {listing_count}"
)

print(
    f"Link India listings     : {link_india_listing_count}"
)

print(
    f"Buyer organisations     : {buyer_count}"
)

print(
    f"Transport providers     : {transporter_count}"
)

print()
print("Main Demo Accounts")
print("----------------------------------------------")
print("Farmer : farmer@gram.ai / Farmer@123")
print("Buyer  : buyer@gram.ai  / Buyer@123")
print("Admin  : admin@gram.ai  / Admin@123")
print("----------------------------------------------")