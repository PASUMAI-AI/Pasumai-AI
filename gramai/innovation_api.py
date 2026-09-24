"""GRAM AI SIH innovation layer.

Adds Tamil Nadu-first state context, KYC/Aadhaar-ready verification, pre-orders,
Razorpay test-mode payment reconciliation, GramRewards, GramRakshak grievances,
feedback, group selling and admin analytics without replacing legacy tables/routes.

Aadhaar note: this prototype NEVER stores a full Aadhaar number and does not claim
UIDAI authentication. Production Aadhaar/eKYC requires an authorised KUA/AUA/KSA
or approved KYC provider and explicit consent.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta, timezone
import os, sqlite3, json, hashlib, hmac, secrets, math, re
from certificate_service import attach_certificate, verification_id_for_listing

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

router = APIRouter(prefix="/api/v2", tags=["GRAM AI SIH 2026"])
BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "gramai.db")
EVIDENCE_DIR = os.path.join(BASE, "uploads", "grievances")
os.makedirs(EVIDENCE_DIR, exist_ok=True)

DEFAULT_STATE = "Tamil Nadu"
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")
PAYMENT_DEMO_MODE = os.environ.get("GRAMAI_PAYMENT_DEMO", "1") == "1"


def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def rowdict(r):
    return dict(r) if r else None


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def init_innovation_schema():
    c = conn()
    # Non-destructive: all legacy tables are retained.
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS kyc_profiles(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER UNIQUE NOT NULL,
          method TEXT NOT NULL DEFAULT 'KYC',
          document_type TEXT NOT NULL DEFAULT 'AADHAAR',
          masked_document TEXT NOT NULL DEFAULT '',
          aadhaar_last4 TEXT NOT NULL DEFAULT '',
          provider_ref TEXT NOT NULL DEFAULT '',
          consent INTEGER NOT NULL DEFAULT 0,
          status TEXT NOT NULL DEFAULT 'NOT_STARTED',
          risk_note TEXT NOT NULL DEFAULT '',
          submitted_at TEXT,
          verified_at TEXT,
          verified_by INTEGER
        );

        CREATE TABLE IF NOT EXISTS feedback(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          category TEXT NOT NULL,
          rating INTEGER NOT NULL DEFAULT 5,
          message TEXT NOT NULL,
          voice_transcript TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT 'OPEN',
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS harvests(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          farmer_id INTEGER NOT NULL,
          crop TEXT NOT NULL,
          variety TEXT NOT NULL DEFAULT 'Standard',
          expected_quantity_qtl REAL NOT NULL,
          available_quantity_qtl REAL NOT NULL,
          expected_harvest_date TEXT NOT NULL,
          expected_price REAL NOT NULL DEFAULT 0,
          district TEXT NOT NULL DEFAULT '',
          state TEXT NOT NULL DEFAULT 'Tamil Nadu',
          grade_expected TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT 'OPEN',
          group_id INTEGER,
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS preorder_requests(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          buyer_id INTEGER NOT NULL,
          harvest_id INTEGER NOT NULL,
          quantity_qtl REAL NOT NULL,
          offer_price REAL NOT NULL,
          recommended_action TEXT NOT NULL DEFAULT 'NEGOTIATE',
          fair_low REAL NOT NULL DEFAULT 0,
          fair_high REAL NOT NULL DEFAULT 0,
          predicted_1d REAL NOT NULL DEFAULT 0,
          predicted_3d REAL NOT NULL DEFAULT 0,
          predicted_7d REAL NOT NULL DEFAULT 0,
          transport_cost REAL NOT NULL DEFAULT 0,
          market_charges REAL NOT NULL DEFAULT 0,
          net_farmer_value REAL NOT NULL DEFAULT 0,
          deposit_percent REAL NOT NULL DEFAULT 15,
          deposit_amount REAL NOT NULL DEFAULT 0,
          status TEXT NOT NULL DEFAULT 'PENDING',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS fpo_groups(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          state TEXT NOT NULL DEFAULT 'Tamil Nadu',
          district TEXT NOT NULL DEFAULT '',
          crop TEXT NOT NULL DEFAULT '',
          owner_id INTEGER NOT NULL,
          status TEXT NOT NULL DEFAULT 'ACTIVE',
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS fpo_group_members(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          group_id INTEGER NOT NULL,
          farmer_id INTEGER NOT NULL,
          quantity_qtl REAL NOT NULL DEFAULT 0,
          joined_at TEXT NOT NULL,
          UNIQUE(group_id, farmer_id)
        );

        CREATE TABLE IF NOT EXISTS payments_v2(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          purpose TEXT NOT NULL,
          reference_type TEXT NOT NULL,
          reference_id INTEGER NOT NULL,
          expected_amount_paise INTEGER NOT NULL,
          gateway_order_id TEXT NOT NULL DEFAULT '',
          gateway_payment_id TEXT NOT NULL DEFAULT '',
          client_signature_verified INTEGER NOT NULL DEFAULT 0,
          webhook_verified INTEGER NOT NULL DEFAULT 0,
          confirmed_amount_paise INTEGER NOT NULL DEFAULT 0,
          overpayment_paise INTEGER NOT NULL DEFAULT 0,
          currency TEXT NOT NULL DEFAULT 'INR',
          status TEXT NOT NULL DEFAULT 'CREATED',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS payment_events(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          payment_id INTEGER,
          gateway_event_id TEXT NOT NULL DEFAULT '',
          event_type TEXT NOT NULL,
          payload_hash TEXT NOT NULL DEFAULT '',
          details TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS refunds_v2(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          payment_id INTEGER NOT NULL,
          amount_paise INTEGER NOT NULL,
          gateway_refund_id TEXT NOT NULL DEFAULT '',
          reason TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'PROCESSING',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reward_ledger(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          reward_type TEXT NOT NULL,
          points INTEGER NOT NULL DEFAULT 0,
          benefit_rupees REAL NOT NULL DEFAULT 0,
          reason TEXT NOT NULL,
          reference_type TEXT NOT NULL DEFAULT '',
          reference_id INTEGER,
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS trust_scores(
          user_id INTEGER PRIMARY KEY,
          buyer_reliability REAL NOT NULL DEFAULT 50,
          harvest_commitment REAL NOT NULL DEFAULT 50,
          instant_payment REAL NOT NULL DEFAULT 50,
          zero_cancel_streak INTEGER NOT NULL DEFAULT 0,
          grievance_adjustment REAL NOT NULL DEFAULT 0,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ai_decision_protection(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          farmer_id INTEGER NOT NULL,
          recommendation_type TEXT NOT NULL,
          recommendation_snapshot TEXT NOT NULL,
          eligible INTEGER NOT NULL DEFAULT 0,
          outcome_value REAL,
          benchmark_value REAL,
          benefit_type TEXT NOT NULL DEFAULT '',
          benefit_value REAL NOT NULL DEFAULT 0,
          status TEXT NOT NULL DEFAULT 'TRACKING',
          created_at TEXT NOT NULL,
          resolved_at TEXT
        );

        CREATE TABLE IF NOT EXISTS grievances_v2(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          complainant_id INTEGER NOT NULL,
          against_user_id INTEGER,
          order_id INTEGER,
          payment_id INTEGER,
          category TEXT NOT NULL,
          description TEXT NOT NULL,
          voice_transcript TEXT NOT NULL DEFAULT '',
          severity TEXT NOT NULL DEFAULT 'MEDIUM',
          severity_score INTEGER NOT NULL DEFAULT 50,
          ai_recommendation TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT 'OPEN',
          escalation_level INTEGER NOT NULL DEFAULT 0,
          due_at TEXT NOT NULL,
          satisfaction TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS grievance_evidence(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          grievance_id INTEGER NOT NULL,
          file_path TEXT NOT NULL,
          media_type TEXT NOT NULL,
          sha256 TEXT NOT NULL,
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS risk_alerts(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER,
          risk_type TEXT NOT NULL,
          score INTEGER NOT NULL,
          details TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'OPEN',
          created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_harvest_state_crop ON harvests(state,crop,status);
        CREATE INDEX IF NOT EXISTS idx_preorders_harvest ON preorder_requests(harvest_id,status);
        CREATE INDEX IF NOT EXISTS idx_payments_ref ON payments_v2(reference_type,reference_id);
        CREATE INDEX IF NOT EXISTS idx_grievances_status ON grievances_v2(status,severity);
        """
    )
    # Tamil Nadu becomes default for empty legacy user profiles, without overriding existing states.
        # Tamil Nadu becomes default for empty legacy user profiles,
    # without overriding existing states.
    c.execute(
        "UPDATE users SET state=? WHERE trim(coalesce(state,''))=''",
        (DEFAULT_STATE,)
    )

    # ============================================================
    # ADVANCED FARMER / BUYER FEEDBACK MIGRATION
    # ============================================================
    # Existing GRAM AI databases already contain the basic
    # feedback table. Add new columns only when they do not exist.
    #
    # This keeps old feedback records safe and prevents us from
    # deleting/recreating the database.
    # ============================================================

    existing_feedback_columns = {
        row["name"]
        for row in c.execute("PRAGMA table_info(feedback)").fetchall()
    }

    feedback_columns = {
        "price_forecast_rating": "INTEGER NOT NULL DEFAULT 0",
        "buyer_experience_rating": "INTEGER NOT NULL DEFAULT 0",
        "payment_rating": "INTEGER NOT NULL DEFAULT 0",
        "transport_rating": "INTEGER NOT NULL DEFAULT 0",
        "quality_grade_rating": "INTEGER NOT NULL DEFAULT 0",
        "ease_of_use_rating": "INTEGER NOT NULL DEFAULT 0",

        "recommendation_followed": "TEXT NOT NULL DEFAULT ''",
        "recommendation_useful": "TEXT NOT NULL DEFAULT ''",

        "expected_price": "REAL NOT NULL DEFAULT 0",
        "actual_selling_price": "REAL NOT NULL DEFAULT 0",
        "alternative_price": "REAL NOT NULL DEFAULT 0",
        "outcome": "TEXT NOT NULL DEFAULT ''",
        "profit_impact": "REAL NOT NULL DEFAULT 0",

        "local_requirements": "TEXT NOT NULL DEFAULT '[]'",
        "feature_votes": "TEXT NOT NULL DEFAULT '[]'",

        "anonymous": "INTEGER NOT NULL DEFAULT 0",
        "callback_requested": "INTEGER NOT NULL DEFAULT 0",

        "review_status": "TEXT NOT NULL DEFAULT 'SUBMITTED'",
        "admin_response": "TEXT NOT NULL DEFAULT ''",
        "reviewed_at": "TEXT",
        "implemented_at": "TEXT",

        "updated_at": "TEXT"
    }

    for column_name, column_definition in feedback_columns.items():
        if column_name not in existing_feedback_columns:
            c.execute(
                f"ALTER TABLE feedback "
                f"ADD COLUMN {column_name} {column_definition}"
            )

    c.commit()
    c.close()


class FeedbackIn(BaseModel):

    # ============================================================
    # BASIC FEEDBACK
    # ============================================================

    category: str = Field(
        default="FEEDBACK",
        max_length=40
    )

    rating: int = Field(
        default=5,
        ge=1,
        le=5
    )

    message: str = Field(
        default="Farmer feedback submitted through GRAM AI",
        max_length=4000
    )

    voice_transcript: str = Field(
        default="",
        max_length=4000
    )

    # ============================================================
    # QUICK EXPERIENCE CHECK
    # 0 means farmer did not rate that section.
    # ============================================================

    price_forecast_rating: int = Field(default=0, ge=0, le=5)

    buyer_experience_rating: int = Field(default=0, ge=0, le=5)

    payment_rating: int = Field(default=0, ge=0, le=5)

    transport_rating: int = Field(default=0, ge=0, le=5)

    quality_grade_rating: int = Field(default=0, ge=0, le=5)

    ease_of_use_rating: int = Field(default=0, ge=0, le=5)

    # ============================================================
    # AI RECOMMENDATION LEARNING
    # ============================================================

    recommendation_followed: str = Field(
        default="",
        max_length=40
    )

    recommendation_useful: str = Field(
        default="",
        max_length=40
    )

    expected_price: float = Field(
        default=0,
        ge=0
    )

    actual_selling_price: float = Field(
        default=0,
        ge=0
    )

    alternative_price: float = Field(
        default=0,
        ge=0
    )

    outcome: str = Field(
        default="",
        max_length=100
    )

    # ============================================================
    # FARMER CO-DESIGN / LOCAL REQUIREMENTS
    # ============================================================

    local_requirements: list[str] = Field(
        default_factory=list
    )

    feature_votes: list[str] = Field(
        default_factory=list
    )

    # ============================================================
    # PRIVACY + FOLLOW-UP
    # ============================================================

    anonymous: bool = False

    callback_requested: bool = False


class KYCIn(BaseModel):
    method: str = Field(default="AADHAAR", pattern="^(AADHAAR|KYC)$")
    document_type: str = Field(default="AADHAAR", max_length=30)
    aadhaar_last4: str = Field(default="", max_length=4)
    provider_ref: str = Field(default="", max_length=120)
    consent: bool


class KYCDecision(BaseModel):
    status: str = Field(pattern="^(VERIFIED|REJECTED|NEEDS_REVIEW)$")
    risk_note: str = Field(default="", max_length=500)


class HarvestIn(BaseModel):
    crop: str = Field(min_length=2, max_length=60)
    variety: str = Field(default="Standard", max_length=60)
    expected_quantity_qtl: float = Field(gt=0, le=100000)
    expected_harvest_date: str
    expected_price: float = Field(default=0, ge=0)
    district: str = Field(default="", max_length=80)
    state: str = Field(default=DEFAULT_STATE, max_length=80)
    grade_expected: str = Field(default="", max_length=20)
    group_id: Optional[int] = None


class PreorderIn(BaseModel):
    harvest_id: int
    quantity_qtl: float = Field(gt=0)
    offer_price: float = Field(gt=0)
    buyer_lat: Optional[float] = None
    buyer_lon: Optional[float] = None


class PreorderDecision(BaseModel):
    status: str = Field(pattern="^(ACCEPTED|NEGOTIATING|DECLINED|WAIT)$")
    counter_price: Optional[float] = Field(default=None, gt=0)


class GroupIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    state: str = Field(default=DEFAULT_STATE, max_length=80)
    district: str = Field(default="", max_length=80)
    crop: str = Field(default="", max_length=60)
    area: str = Field(default="", max_length=80)
    quantity_qtl: float = Field(default=0, ge=0)
    target_quantity_qtl: float = Field(default=0, ge=0)
    expected_price: float = Field(default=0, ge=0)
    expected_harvest_date: Optional[str] = None
    description: str = Field(default="", max_length=1000)
    shared_transport: bool = Field(default=False)
    max_members: int = Field(default=20, ge=2)


class GroupJoinIn(BaseModel):
    quantity_qtl: float = Field(default=0, ge=0)


class GroupJoinRequestIn(BaseModel):
    join_code: str = Field(default="", max_length=40)
    quantity_qtl: float = Field(default=0, ge=0)
    message: str = Field(default="", max_length=500)


class JoinRequestActionIn(BaseModel):
    action: str = Field(pattern="^(ACCEPT|DECLINE)$")


class TransportGroupIn(BaseModel):
    route_from: str = Field(min_length=2, max_length=100)
    route_to: str = Field(min_length=2, max_length=100)
    distance_km: float = Field(default=0, ge=0)
    vehicle_type: str = Field(default="Mini Truck", max_length=60)
    capacity_qtl: float = Field(default=0, gt=0)
    crop: str = Field(default="", max_length=60)
    cost_per_qtl: float = Field(default=0, ge=0)
    district: str = Field(default="", max_length=80)
    state: str = Field(default=DEFAULT_STATE, max_length=80)
    departure_date: Optional[str] = None
    quantity_qtl: float = Field(default=0, ge=0)


class TransportGroupJoinIn(BaseModel):
    quantity_qtl: float = Field(gt=0)
    crop: str = Field(default="", max_length=60)


class PaymentCreate(BaseModel):
    reference_type: str = Field(pattern="^(ORDER|PREORDER)$")
    reference_id: int
    purpose: str = Field(default="BOOKING_TOKEN", max_length=50)


class PaymentVerify(BaseModel):
    gateway_order_id: str
    gateway_payment_id: str
    gateway_signature: str


class GrievanceIn(BaseModel):
    category: str = Field(default="OTHER", max_length=60)
    description: str = Field(min_length=2, max_length=4000)
    voice_transcript: str = Field(default="", max_length=4000)
    order_id: Optional[int] = None
    payment_id: Optional[int] = None
    against_user_id: Optional[int] = None


class SatisfactionIn(BaseModel):
    satisfaction: str = Field(pattern="^(SATISFIED|NOT_SATISFIED)$")


def require_role(u, *allowed):
    if u["role"] not in allowed:
        raise HTTPException(403, "This action is not available for your portal role")


def get_user_dep():
    # Late import avoids circular import while preserving the existing auth implementation.
    from app import user
    return user


def audit_event(uid, action, details=""):
    c = conn()
    c.execute("INSERT INTO audit_logs(user_id,action,details,created_at) VALUES(?,?,?,datetime('now'))",
              (uid, action, details[:1000]))
    c.commit(); c.close()


def trust_for(c, uid):
    r = c.execute("SELECT * FROM trust_scores WHERE user_id=?", (uid,)).fetchone()
    if not r:
        c.execute("INSERT OR IGNORE INTO trust_scores(user_id,updated_at) VALUES(?,?)", (uid, now_iso()))
        r = c.execute("SELECT * FROM trust_scores WHERE user_id=?", (uid,)).fetchone()
    return dict(r)


def buyer_reliability(c, buyer_id):
    t = trust_for(c, buyer_id)
    # Blend native buyer records when available with live trust ledger.
    u = c.execute("SELECT state,district,phone,name FROM users WHERE id=?", (buyer_id,)).fetchone()
    buyer = None
    if u:
        buyer = c.execute("SELECT * FROM buyers WHERE phone=? LIMIT 1", (u["phone"],)).fetchone()
    legacy = float(buyer["payment_score"] if buyer and buyer["payment_score"] is not None else 70)
    score = 0.55 * float(t["buyer_reliability"]) + 0.30 * float(t["instant_payment"]) + 0.15 * legacy
    return round(clamp(score + float(t["grievance_adjustment"]), 0, 100), 1)


def deposit_percent_for(score):
    if score >= 90: return 5.0
    if score >= 80: return 8.0
    if score >= 65: return 12.0
    if score >= 50: return 18.0
    return 25.0


def approximate_market_prediction(c, crop, state):
    # Uses latest seeded/public-like series as a safe fallback when market-specific ML lookup is unavailable.
    rows = c.execute(
        """SELECT p.modal_price,p.price_date FROM prices p JOIN markets m ON m.id=p.market_id
           WHERE p.crop=? AND m.state=? ORDER BY p.price_date DESC LIMIT 21""", (crop, state)
    ).fetchall()
    if not rows:
        rows = c.execute("SELECT modal_price,price_date FROM prices WHERE crop=? ORDER BY price_date DESC LIMIT 21", (crop,)).fetchall()
    vals = [float(r["modal_price"]) for r in rows if r["modal_price"]]
    if not vals:
        return {1: 0.0, 3: 0.0, 7: 0.0, "confidence": "LOW"}
    recent = vals[0]
    older = vals[min(len(vals)-1, 6)]
    daily = (recent - older) / max(1, min(len(vals)-1, 6))
    return {
        1: round(max(0, recent + daily), 2),
        3: round(max(0, recent + 3*daily), 2),
        7: round(max(0, recent + 7*daily), 2),
        "confidence": "GOOD" if len(vals) >= 14 else "MODERATE"
    }


def preorder_advice(c, harvest, buyer_id, quantity, offer, buyer_lat=None, buyer_lon=None):
    pred = approximate_market_prediction(c, harvest["crop"], harvest["state"])
    expected_market = max(float(pred[1] or 0), float(pred[3] or 0), float(pred[7] or 0), float(harvest["expected_price"] or 0))
    # Conservative transparent prototype rules, not a guaranteed market outcome.
    market_charge_pct = 1.0
    market_charges = quantity * expected_market * market_charge_pct / 100
    transport = 0.0
    market = c.execute("SELECT lat,lon FROM markets WHERE state=? ORDER BY id LIMIT 1", (harvest["state"],)).fetchone()
    if market and buyer_lat is not None and buyer_lon is not None:
        km = 111 * math.sqrt((buyer_lat-market["lat"])**2 + ((buyer_lon-market["lon"])*math.cos(math.radians(buyer_lat)))**2)
        tr = c.execute("SELECT avg(rate_per_km) r FROM transporters WHERE state=? AND verified=1", (harvest["state"],)).fetchone()
        rate = float(tr["r"] or 18)
        transport = km * rate
    per_qtl_cost = (transport + market_charges) / max(quantity, 1)
    fair_mid = max(offer, expected_market - per_qtl_cost)
    fair_low = round(fair_mid * 0.97, 2)
    fair_high = round(fair_mid * 1.03, 2)
    net = quantity * offer - transport - market_charges
    reliability = buyer_reliability(c, buyer_id)
    dep_pct = deposit_percent_for(reliability)
    # ACCEPT if close to fair value; NEGOTIATE if moderately below; WAIT when materially below future outlook.
    if offer >= fair_low:
        action = "ACCEPT"
    elif offer >= fair_low * 0.92:
        action = "NEGOTIATE"
    else:
        action = "WAIT"
    return {
        "action": action, "fair_low": fair_low, "fair_high": fair_high,
        "predicted_1d": pred[1], "predicted_3d": pred[3], "predicted_7d": pred[7],
        "transport_cost": round(transport,2), "market_charges": round(market_charges,2),
        "net_farmer_value": round(net,2), "buyer_reliability": reliability,
        "deposit_percent": dep_pct, "deposit_amount": round(float(harvest["token_amount"] or 0) if "token_amount" in harvest.keys() and float(harvest["token_amount"] or 0)>0 else quantity*offer*dep_pct/100,2),
        "forecast_confidence": pred["confidence"]
    }


def severity_for(category, description, amount=0):
    txt = f"{category} {description}".lower()
    score = 25
    critical = ["fraud", "scam", "identity", "threat", "stolen"]
    high = ["payment", "not paid", "delayed", "damage", "cancel", "fake", "quality dispute"]
    if any(k in txt for k in critical): score += 55
    elif any(k in txt for k in high): score += 35
    if amount >= 50000: score += 15
    elif amount >= 10000: score += 8
    score = int(clamp(score, 0, 100))
    label = "CRITICAL" if score >= 80 else "HIGH" if score >= 60 else "MEDIUM" if score >= 35 else "LOW"
    return score, label


def resolution_advice(category, severity):
    base = {
        "PAYMENT": "Verify gateway/order evidence, keep funds/status under review and contact the buyer before release.",
        "DELAYED_PAYMENT": "Confirm agreed payment date, send a formal reminder and escalate if the SLA expires.",
        "CANCELLATION": "Check cancellation terms, harvest commitment and eligible compensation/reward rules.",
        "DELIVERY": "Compare delivery evidence, GPS/logistics record and condition photos before resolution.",
        "QUALITY": "Compare AI grade certificate, listing evidence and delivery photos; request manual review if evidence conflicts.",
    }
    text = base.get(category.upper(), "Review linked order/payment evidence and contact both parties for documented resolution.")
    if severity in ("HIGH", "CRITICAL"):
        text += " Priority escalation to an administrator is recommended."
    return text


def auto_escalate(c):
    rows = c.execute("SELECT id,severity,escalation_level FROM grievances_v2 WHERE status IN ('OPEN','IN_REVIEW') AND due_at < ?", (now_iso(),)).fetchall()
    for r in rows:
        new_level = min(3, int(r["escalation_level"])+1)
        c.execute("UPDATE grievances_v2 SET escalation_level=?,status='ESCALATED',updated_at=? WHERE id=?", (new_level, now_iso(), r["id"]))


@router.get("/config")
def config(u=Depends(get_user_dep())):
    c=conn(); states=[r[0] for r in c.execute("SELECT DISTINCT state FROM markets WHERE trim(state)<>'' ORDER BY CASE WHEN state=? THEN 0 ELSE 1 END,state",(DEFAULT_STATE,)).fetchall()]; c.close()
    return {"default_state":DEFAULT_STATE,"states":states,"payment_mode":"RAZORPAY_TEST" if RAZORPAY_KEY_ID else "DEMO_TEST","aadhaar_mode":"PROVIDER_READY_MASKED_ONLY"}


@router.get("/state-overview")
def state_overview(state: str = DEFAULT_STATE, u=Depends(get_user_dep())):
    c=conn()
    markets=c.execute("SELECT count(*) n FROM markets WHERE state=?",(state,)).fetchone()["n"]
    buyers=c.execute("SELECT count(*) n FROM buyers WHERE state=? AND verified=1",(state,)).fetchone()["n"]
    transport=c.execute("SELECT count(*) n FROM transporters WHERE state=? AND verified=1",(state,)).fetchone()["n"]
    harvests=c.execute("SELECT count(*) n FROM harvests WHERE state=? AND status='OPEN'",(state,)).fetchone()["n"]
    demand=c.execute("""SELECT p.crop,round(avg(p.demand_index),1) demand FROM prices p JOIN markets m ON m.id=p.market_id
                        WHERE m.state=? AND p.price_date=(SELECT max(price_date) FROM prices) GROUP BY p.crop ORDER BY demand DESC LIMIT 5""",(state,)).fetchall()
    c.close()
    return {"state":state,"markets":markets,"verified_buyers":buyers,"transporters":transport,"upcoming_harvests":harvests,"top_demand":[dict(r) for r in demand]}


@router.post("/feedback")
def add_feedback(
    x: FeedbackIn,
    u=Depends(get_user_dep())
):

    c = conn()

    try:

        profit_impact = 0.0

        if (
            float(x.actual_selling_price or 0) > 0
            and float(x.alternative_price or 0) > 0
        ):
            profit_impact = round(
                float(x.actual_selling_price)
                - float(x.alternative_price),
                2
            )

        elif (
            float(x.actual_selling_price or 0) > 0
            and float(x.expected_price or 0) > 0
        ):
            profit_impact = round(
                float(x.actual_selling_price)
                - float(x.expected_price),
                2
            )

        detailed_ratings = [
            x.price_forecast_rating,
            x.buyer_experience_rating,
            x.payment_rating,
            x.transport_rating,
            x.quality_grade_rating,
            x.ease_of_use_rating
        ]

        valid_ratings = [
            int(r)
            for r in detailed_ratings
            if int(r or 0) > 0
        ]

        overall_rating = int(x.rating)

        if valid_ratings:
            overall_rating = int(
                round(
                    sum(valid_ratings)
                    / len(valid_ratings)
                )
            )

        overall_rating = max(1, min(5, overall_rating))

        cur = c.execute(
            """
            INSERT INTO feedback(
                user_id,
                category,
                rating,
                message,
                voice_transcript,

                price_forecast_rating,
                buyer_experience_rating,
                payment_rating,
                transport_rating,
                quality_grade_rating,
                ease_of_use_rating,

                recommendation_followed,
                recommendation_useful,

                expected_price,
                actual_selling_price,
                alternative_price,
                outcome,
                profit_impact,

                local_requirements,
                feature_votes,

                anonymous,
                callback_requested,

                status,
                review_status,

                created_at,
                updated_at
            )

            VALUES(
                ?,?,?,?,?,
                ?,?,?,?,?,?,
                ?,?,
                ?,?,?,?,?,
                ?,?,
                ?,?,
                'OPEN',
                'SUBMITTED',
                ?,?
            )
            """,
            (
                u["id"],
                x.category,
                overall_rating,

                x.message.strip()
                if x.message.strip()
                else "Farmer feedback submitted through GRAM AI",

                x.voice_transcript.strip(),

                x.price_forecast_rating,
                x.buyer_experience_rating,
                x.payment_rating,
                x.transport_rating,
                x.quality_grade_rating,
                x.ease_of_use_rating,

                x.recommendation_followed.strip(),
                x.recommendation_useful.strip(),

                float(x.expected_price or 0),
                float(x.actual_selling_price or 0),
                float(x.alternative_price or 0),

                x.outcome.strip(),
                profit_impact,

                json.dumps(
                    x.local_requirements,
                    ensure_ascii=False
                ),

                json.dumps(
                    x.feature_votes,
                    ensure_ascii=False
                ),

                1 if x.anonymous else 0,
                1 if x.callback_requested else 0,

                now_iso(),
                now_iso()
            )
        )

        feedback_id = cur.lastrowid

        c.commit()

    except Exception:
        c.rollback()
        c.close()
        raise

    c.close()

    audit_event(
        u["id"],
        "feedback_created",
        f"feedback_id={feedback_id}"
    )

    return {
        "success": True,
        "id": feedback_id,
        "feedback_id": feedback_id,
        "status": "SUBMITTED",
        "review_status": "SUBMITTED",
        "profit_impact": profit_impact,
        "message": "Feedback submitted successfully."
    }

@router.get("/feedback")
def feedback_list(
    u=Depends(get_user_dep())
):

    c = conn()

    # ============================================================
    # ADMIN
    # Admin can view every feedback submission.
    # ============================================================

    if u["role"] == "admin":

        rows = c.execute(
            """
            SELECT
                f.*,

                CASE
                    WHEN f.anonymous = 1
                    THEN 'Anonymous Farmer'
                    ELSE u.name
                END AS name,

                u.role

            FROM feedback f

            JOIN users u
                ON u.id = f.user_id

            ORDER BY f.id DESC

            LIMIT 200
            """
        ).fetchall()

    # ============================================================
    # FARMER / BUYER
    # Only their own previous submissions.
    # ============================================================

    else:

        rows = c.execute(
            """
            SELECT *
            FROM feedback

            WHERE user_id=?

            ORDER BY id DESC

            LIMIT 100
            """,
            (
                u["id"],
            )
        ).fetchall()

    result = []

    for row in rows:

        item = dict(row)

        # Convert stored JSON back into arrays.

        try:
            item["local_requirements"] = json.loads(
                item.get("local_requirements") or "[]"
            )
        except Exception:
            item["local_requirements"] = []

        try:
            item["feature_votes"] = json.loads(
                item.get("feature_votes") or "[]"
            )
        except Exception:
            item["feature_votes"] = []

        result.append(item)

    c.close()

    return result

@router.post("/kyc")
def submit_kyc(x: KYCIn, u=Depends(get_user_dep())):
    if not x.consent: raise HTTPException(400,"Explicit consent is required for KYC verification")
    last4=re.sub(r"\D","",x.aadhaar_last4 or "")
    if x.method=="AADHAAR" and len(last4)!=4: raise HTTPException(400,"Enter only the last 4 Aadhaar digits. Full Aadhaar numbers must not be stored here.")
    masked="XXXX-XXXX-"+last4 if last4 else "PROVIDER-KYC"
    c=conn(); c.execute("""INSERT INTO kyc_profiles(user_id,method,document_type,masked_document,aadhaar_last4,provider_ref,consent,status,submitted_at)
                           VALUES(?,?,?,?,?,?,1,'PENDING',?) ON CONFLICT(user_id) DO UPDATE SET method=excluded.method,document_type=excluded.document_type,
                           masked_document=excluded.masked_document,aadhaar_last4=excluded.aadhaar_last4,provider_ref=excluded.provider_ref,consent=1,status='PENDING',submitted_at=excluded.submitted_at""",
                       (u["id"],x.method,x.document_type,masked,last4,x.provider_ref,now_iso())); c.commit(); c.close()
    audit_event(u["id"],"kyc_submitted",f"method={x.method};masked={masked}")
    return {"status":"PENDING","masked_document":masked,"note":"Prototype KYC submitted. Live Aadhaar authentication requires an authorised provider; full Aadhaar is never stored."}


@router.get("/kyc/me")
def my_kyc(u=Depends(get_user_dep())):
    c=conn(); r=c.execute("SELECT id,method,document_type,masked_document,status,risk_note,submitted_at,verified_at FROM kyc_profiles WHERE user_id=?",(u["id"],)).fetchone(); c.close()
    return rowdict(r) or {"status":"NOT_STARTED"}


@router.get("/kyc/admin")
def kyc_admin(u=Depends(get_user_dep())):
    require_role(u,"admin"); c=conn(); rows=c.execute("""SELECT k.id,k.user_id,u.name,u.email,u.role,k.method,k.document_type,k.masked_document,k.status,k.risk_note,k.submitted_at,k.verified_at
                  FROM kyc_profiles k JOIN users u ON u.id=k.user_id ORDER BY CASE k.status WHEN 'PENDING' THEN 0 ELSE 1 END,k.id DESC""").fetchall(); c.close(); return [dict(r) for r in rows]


@router.patch("/kyc/{kyc_id}")
def decide_kyc(kyc_id:int,x:KYCDecision,u=Depends(get_user_dep())):
    require_role(u,"admin"); c=conn(); r=c.execute("SELECT * FROM kyc_profiles WHERE id=?",(kyc_id,)).fetchone()
    if not r: c.close(); raise HTTPException(404,"KYC record not found")
    verified_at=now_iso() if x.status=="VERIFIED" else None
    c.execute("UPDATE kyc_profiles SET status=?,risk_note=?,verified_at=?,verified_by=? WHERE id=?",(x.status,x.risk_note,verified_at,u["id"],kyc_id)); c.commit(); c.close()
    audit_event(u["id"],"kyc_decision",f"kyc={kyc_id};status={x.status}"); return {"status":x.status}


@router.post("/harvests")
def create_harvest(x:HarvestIn,u=Depends(get_user_dep())):
    require_role(u,"farmer","admin"); state=x.state or u.get("state") or DEFAULT_STATE; district=x.district or u.get("district") or ""
    c=conn(); cur=c.execute("""INSERT INTO harvests(farmer_id,crop,variety,expected_quantity_qtl,available_quantity_qtl,expected_harvest_date,expected_price,district,state,grade_expected,status,group_id,created_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,'OPEN',?,?)""",(u["id"],x.crop,x.variety,x.expected_quantity_qtl,x.expected_quantity_qtl,x.expected_harvest_date,x.expected_price,district,state,x.grade_expected,x.group_id,now_iso())); c.commit(); c.close()
    return {"id":cur.lastrowid,"status":"OPEN","available_quantity_qtl":x.expected_quantity_qtl}


@router.get("/harvests")
def list_harvests(state:str=DEFAULT_STATE,crop:Optional[str]=None,u=Depends(get_user_dep())):
    c=conn(); params=[state,state,crop,crop]
    base="""SELECT h.*,u.name farmer_name,coalesce(k.status,'NOT_STARTED') kyc_status FROM harvests h JOIN users u ON u.id=h.farmer_id LEFT JOIN kyc_profiles k ON k.user_id=h.farmer_id WHERE (?='' OR h.state=?) AND (? IS NULL OR h.crop=?)"""
    if u["role"]=="farmer": base += " AND h.farmer_id=?"; params.append(u["id"])
    base += " ORDER BY h.expected_harvest_date,h.id DESC"
    rows=c.execute(base,tuple(params)).fetchall(); c.close(); return [dict(r) for r in rows]


@router.get("/harvests/{harvest_id}/matches")
def harvest_matches(harvest_id:int,u=Depends(get_user_dep())):
    require_role(u,"farmer","admin"); c=conn(); h=c.execute("SELECT * FROM harvests WHERE id=?",(harvest_id,)).fetchone()
    if not h: c.close(); raise HTTPException(404,"Harvest not found")
    buyers=c.execute("SELECT * FROM buyers WHERE state=? AND (crops LIKE ? OR crops='') ORDER BY verified DESC,payment_score DESC,rating DESC LIMIT 20",(h["state"],f"%{h['crop']}%" )).fetchall()
    result=[]
    for b in buyers:
        rel=round(0.65*float(b["payment_score"] or 60)+0.35*float(b["rating"] or 3)*20,1)
        result.append({**dict(b),"match_score":round(clamp(rel + (5 if b["verified"] else -10),0,100),1)})
    c.close(); return sorted(result,key=lambda x:x["match_score"],reverse=True)


@router.post("/preorders")
def create_preorder(x:PreorderIn,u=Depends(get_user_dep())):
    require_role(u,"buyer","admin"); c=conn(); ensure_verified(c,u,"place a pre-order"); h=c.execute("SELECT * FROM harvests WHERE id=? AND status='OPEN'",(x.harvest_id,)).fetchone()
    if not h: c.close(); raise HTTPException(404,"Harvest is not available")
    qty=min(x.quantity_qtl,float(h["available_quantity_qtl"]));
    if qty<=0: c.close(); raise HTTPException(409,"No quantity is available")
    advice=preorder_advice(c,h,u["id"],qty,x.offer_price,x.buyer_lat,x.buyer_lon)
    cur=c.execute("""INSERT INTO preorder_requests(buyer_id,harvest_id,quantity_qtl,offer_price,recommended_action,fair_low,fair_high,predicted_1d,predicted_3d,predicted_7d,transport_cost,market_charges,net_farmer_value,deposit_percent,deposit_amount,status,created_at,updated_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'PENDING',?,?)""",(u["id"],h["id"],qty,x.offer_price,advice["action"],advice["fair_low"],advice["fair_high"],advice["predicted_1d"],advice["predicted_3d"],advice["predicted_7d"],advice["transport_cost"],advice["market_charges"],advice["net_farmer_value"],advice["deposit_percent"],advice["deposit_amount"],now_iso(),now_iso()))
    pid=cur.lastrowid
    if x.offer_price >= advice["fair_low"]:
        c.execute("INSERT INTO reward_ledger(user_id,reward_type,points,benefit_rupees,reason,reference_type,reference_id,created_at) VALUES(?,'FAIR_BUYER',15,0,'Offer is within/above the AI fair farmer range','PREORDER',?,?)",(u["id"],pid,now_iso()))
    c.commit(); c.close(); return {"preorder_id":pid,"quantity_qtl":qty,**advice}


@router.get("/preorders")
def list_preorders(state:str=DEFAULT_STATE,u=Depends(get_user_dep())):
    c=conn(); q="""SELECT p.*,h.crop,h.expected_harvest_date,h.state,h.district,h.farmer_id,uf.name farmer_name,ub.name buyer_name
      FROM preorder_requests p JOIN harvests h ON h.id=p.harvest_id JOIN users uf ON uf.id=h.farmer_id JOIN users ub ON ub.id=p.buyer_id WHERE h.state=?"""; params=[state]
    if u["role"]=="farmer": q+=" AND h.farmer_id=?";params.append(u["id"])
    elif u["role"]=="buyer": q+=" AND p.buyer_id=?";params.append(u["id"])
    q+=" ORDER BY p.id DESC"; rows=c.execute(q,tuple(params)).fetchall(); c.close(); return [dict(r) for r in rows]


@router.patch("/preorders/{preorder_id}")
def decide_preorder(preorder_id:int,x:PreorderDecision,u=Depends(get_user_dep())):
    c=conn(); p=c.execute("""SELECT p.*,h.farmer_id,h.available_quantity_qtl FROM preorder_requests p JOIN harvests h ON h.id=p.harvest_id WHERE p.id=?""",(preorder_id,)).fetchone()
    if not p: c.close(); raise HTTPException(404,"Pre-order not found")
    if u["role"]!="admin" and p["farmer_id"]!=u["id"]: c.close(); raise HTTPException(403,"Only the farmer can decide this pre-order")
    status=x.status
    if status=="ACCEPTED":
        if p["quantity_qtl"]>p["available_quantity_qtl"]: c.close(); raise HTTPException(409,"Harvest quantity is no longer available")
        c.execute("UPDATE harvests SET available_quantity_qtl=available_quantity_qtl-? WHERE id=?",(p["quantity_qtl"],p["harvest_id"]))
    if x.counter_price:
        c.execute("UPDATE preorder_requests SET offer_price=?,status=?,updated_at=? WHERE id=?",(x.counter_price,status,now_iso(),preorder_id))
    else: c.execute("UPDATE preorder_requests SET status=?,updated_at=? WHERE id=?",(status,now_iso(),preorder_id))
    c.commit(); c.close(); return {"id":preorder_id,"status":status,"counter_price":x.counter_price}


def gen_group_code(district:str)->str:
    tag = "".join(ch for ch in (district or "GRP").upper() if ch.isalpha())[:3] or "GRP"
    return f"GT-{tag}-{secrets.randbelow(9000)+1000}"


def group_row_out(c, g):
    d = dict(g)
    owner = c.execute("SELECT name FROM users WHERE id=?", (d["owner_id"],)).fetchone()
    d["owner_name"] = owner["name"] if owner else "Group Owner"
    members = c.execute(
        """SELECT m.farmer_id user_id, coalesce(NULLIF(m.farmer_name,''),u.name,'Farmer') name,
                  coalesce(NULLIF(m.farmer_district,''),u.district,'') district, m.quantity_qtl
           FROM fpo_group_members m LEFT JOIN users u ON u.id=m.farmer_id
           WHERE m.group_id=? ORDER BY m.id""",
        (d["id"],)
    ).fetchall()
    d["members"] = [dict(r) for r in members]
    d["member_count"] = len(d["members"])
    d["current_quantity_qtl"] = round(sum(r["quantity_qtl"] or 0 for r in d["members"]), 2)
    pending = c.execute("SELECT count(*) n FROM group_join_requests WHERE group_id=? AND status='PENDING'", (d["id"],)).fetchone()
    d["pending_requests"] = pending["n"] if pending else 0
    return d


@router.post("/groups")
def create_group(x:GroupIn,u=Depends(get_user_dep())):
    require_role(u,"farmer","admin"); c=conn()
    code = gen_group_code(x.district)
    cur=c.execute(
        """INSERT INTO fpo_groups(name,state,district,crop,owner_id,status,created_at,
                area,target_quantity_qtl,expected_price,expected_harvest_date,description,
                shared_transport,max_members,join_code)
           VALUES(?,?,?,?,?,'ACTIVE',?,?,?,?,?,?,?,?,?)""",
        (x.name,x.state,x.district,x.crop,u["id"],now_iso(),x.area,x.target_quantity_qtl,
         x.expected_price,x.expected_harvest_date or "",x.description,int(x.shared_transport),
         x.max_members,code)
    ); gid=cur.lastrowid
    c.execute(
        "INSERT INTO fpo_group_members(group_id,farmer_id,quantity_qtl,joined_at) VALUES(?,?,?,?)",
        (gid,u["id"],x.quantity_qtl,now_iso())
    )
    c.commit()
    row = c.execute("SELECT * FROM fpo_groups WHERE id=?", (gid,)).fetchone()
    out = group_row_out(c, row); c.close(); return out


@router.get("/groups")
def list_groups(state:str=DEFAULT_STATE,u=Depends(get_user_dep())):
    c=conn(); rows=c.execute("""SELECT g.*,count(m.id) members,round(coalesce(sum(m.quantity_qtl),0),2) committed_qtl FROM fpo_groups g LEFT JOIN fpo_group_members m ON m.group_id=g.id WHERE g.state=? AND g.status='ACTIVE' GROUP BY g.id ORDER BY committed_qtl DESC""",(state,)).fetchall()
    out = [group_row_out(c, r) for r in rows]
    c.close(); return out


@router.get("/groups/my-groups")
def my_groups(u=Depends(get_user_dep())):
    c=conn()
    rows=c.execute(
        """SELECT g.* FROM fpo_groups g WHERE g.status='ACTIVE' AND
             (g.owner_id=? OR EXISTS(SELECT 1 FROM fpo_group_members m WHERE m.group_id=g.id AND m.farmer_id=?))
           ORDER BY g.id DESC""",
        (u["id"], u["id"])
    ).fetchall()
    out = [group_row_out(c, r) for r in rows]
    c.close(); return out


@router.get("/groups/by-code/{code}")
def group_by_code(code:str,u=Depends(get_user_dep())):
    c=conn(); g=c.execute("SELECT * FROM fpo_groups WHERE join_code=? AND status='ACTIVE'",(code.strip().upper(),)).fetchone()
    if not g: c.close(); raise HTTPException(404,"No group found for this code")
    out = group_row_out(c, g); c.close(); return out


@router.get("/groups/{group_id}")
def group_detail(group_id:int,u=Depends(get_user_dep())):
    c=conn(); g=c.execute("SELECT * FROM fpo_groups WHERE id=?",(group_id,)).fetchone()
    if not g: c.close(); raise HTTPException(404,"Group not found")
    out = group_row_out(c, g); c.close(); return out


@router.post("/groups/{group_id}/join")
def join_group(group_id:int,x:GroupJoinIn,u=Depends(get_user_dep())):
    require_role(u,"farmer","admin"); c=conn(); g=c.execute("SELECT id FROM fpo_groups WHERE id=? AND status='ACTIVE'",(group_id,)).fetchone()
    if not g:c.close();raise HTTPException(404,"Group not found")
    c.execute("INSERT INTO fpo_group_members(group_id,farmer_id,quantity_qtl,joined_at) VALUES(?,?,?,?) ON CONFLICT(group_id,farmer_id) DO UPDATE SET quantity_qtl=excluded.quantity_qtl",(group_id,u["id"],x.quantity_qtl,now_iso()));c.commit();c.close();return {"group_id":group_id,"quantity_qtl":x.quantity_qtl}


@router.post("/groups/{group_id}/join-request")
def group_join_request(group_id:int,x:GroupJoinRequestIn,u=Depends(get_user_dep())):
    require_role(u,"farmer","admin"); c=conn()
    g=c.execute("SELECT * FROM fpo_groups WHERE id=? AND status='ACTIVE'",(group_id,)).fetchone()
    if not g: c.close(); raise HTTPException(404,"Group not found")
    if x.join_code and x.join_code.strip().upper()!=(g["join_code"] or "").upper():
        c.close(); raise HTTPException(400,"Joining code does not match this group")
    already=c.execute("SELECT 1 FROM fpo_group_members WHERE group_id=? AND farmer_id=?",(group_id,u["id"])).fetchone()
    if already: c.close(); raise HTTPException(409,"You are already a member of this group")
    cur=c.execute(
        "INSERT INTO group_join_requests(group_id,farmer_id,farmer_name,district,quantity_qtl,message,status,created_at,updated_at) VALUES(?,?,?,?,?,?,'PENDING',?,?)",
        (group_id,u["id"],u["name"],u["district"],x.quantity_qtl,x.message,now_iso(),now_iso())
    ); c.commit(); rid=cur.lastrowid; c.close()
    return {"id":rid,"status":"PENDING"}


@router.get("/groups/{group_id}/join-requests")
def list_join_requests(group_id:int,u=Depends(get_user_dep())):
    c=conn(); g=c.execute("SELECT owner_id FROM fpo_groups WHERE id=?",(group_id,)).fetchone()
    if not g: c.close(); raise HTTPException(404,"Group not found")
    if g["owner_id"]!=u["id"] and u["role"]!="admin": c.close(); raise HTTPException(403,"Only the group owner can view join requests")
    rows=c.execute("SELECT * FROM group_join_requests WHERE group_id=? ORDER BY (status='PENDING') DESC, id DESC",(group_id,)).fetchall()
    c.close(); return [dict(r) for r in rows]


@router.patch("/groups/join-requests/{request_id}")
def respond_join_request(request_id:int,x:JoinRequestActionIn,u=Depends(get_user_dep())):
    c=conn(); r=c.execute("SELECT * FROM group_join_requests WHERE id=?",(request_id,)).fetchone()
    if not r: c.close(); raise HTTPException(404,"Join request not found")
    g=c.execute("SELECT * FROM fpo_groups WHERE id=?",(r["group_id"],)).fetchone()
    if not g or (g["owner_id"]!=u["id"] and u["role"]!="admin"): c.close(); raise HTTPException(403,"Only the group owner can respond to this request")
    if r["status"]!="PENDING": c.close(); raise HTTPException(409,"This request was already handled")
    status = "ACCEPTED" if x.action=="ACCEPT" else "DECLINED"
    if x.action=="ACCEPT":
        c.execute(
            "INSERT INTO fpo_group_members(group_id,farmer_id,farmer_name,farmer_district,quantity_qtl,joined_at) VALUES(?,?,?,?,?,?) ON CONFLICT(group_id,farmer_id) DO UPDATE SET quantity_qtl=excluded.quantity_qtl",
            (r["group_id"],r["farmer_id"],r["farmer_name"],r["district"],r["quantity_qtl"],now_iso())
        )
    c.execute("UPDATE group_join_requests SET status=?,updated_at=? WHERE id=?",(status,now_iso(),request_id))
    c.commit(); c.close(); return {"id":request_id,"status":status}


# =========================================================
# TRANSPORT GROUPS — shared-lorry routes farmers can join
# =========================================================

def transport_group_row_out(c, g):
    d = dict(g)
    owner = c.execute("SELECT name FROM users WHERE id=?", (d["owner_id"],)).fetchone()
    d["owner_name"] = owner["name"] if owner else "Route Owner"
    members = c.execute(
        """SELECT m.farmer_id user_id, coalesce(NULLIF(m.farmer_name,''),u.name,'Farmer') name,
                  coalesce(NULLIF(m.farmer_district,''),u.district,'') district,
                  coalesce(NULLIF(m.crop,''),?) crop, m.quantity_qtl
           FROM transport_group_members m LEFT JOIN users u ON u.id=m.farmer_id
           WHERE m.group_id=? ORDER BY m.id""",
        (d["crop"], d["id"])
    ).fetchall()
    d["members"] = [dict(r) for r in members]
    d["member_count"] = len(d["members"])
    used = round(sum(r["quantity_qtl"] or 0 for r in d["members"]), 2)
    d["used_qtl"] = used
    d["space_left_qtl"] = max(round(d["capacity_qtl"] - used, 2), 0)
    return d


@router.post("/transport-groups")
def create_transport_group(x:TransportGroupIn,u=Depends(get_user_dep())):
    require_role(u,"farmer","admin"); c=conn()
    cur=c.execute(
        """INSERT INTO transport_groups(route_from,route_to,distance_km,vehicle_type,capacity_qtl,
                crop,cost_per_qtl,owner_id,state,district,departure_date,status,created_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,'ACTIVE',?)""",
        (x.route_from,x.route_to,x.distance_km,x.vehicle_type,x.capacity_qtl,x.crop,x.cost_per_qtl,
         u["id"],x.state,x.district,x.departure_date or "",now_iso())
    ); gid=cur.lastrowid
    if x.quantity_qtl>0:
        c.execute(
            "INSERT INTO transport_group_members(group_id,farmer_id,crop,quantity_qtl,joined_at) VALUES(?,?,?,?,?)",
            (gid,u["id"],x.crop,x.quantity_qtl,now_iso())
        )
    c.commit()
    row=c.execute("SELECT * FROM transport_groups WHERE id=?",(gid,)).fetchone()
    out=transport_group_row_out(c, row); c.close(); return out


@router.get("/transport-groups")
def list_transport_groups(state:str=DEFAULT_STATE,u=Depends(get_user_dep())):
    c=conn()
    rows=c.execute("SELECT * FROM transport_groups WHERE state=? AND status='ACTIVE' ORDER BY id DESC",(state,)).fetchall()
    out=[transport_group_row_out(c, r) for r in rows]
    c.close(); return out


@router.post("/transport-groups/{group_id}/join")
def join_transport_group(group_id:int,x:TransportGroupJoinIn,u=Depends(get_user_dep())):
    require_role(u,"farmer","admin"); c=conn()
    g=c.execute("SELECT * FROM transport_groups WHERE id=? AND status='ACTIVE'",(group_id,)).fetchone()
    if not g: c.close(); raise HTTPException(404,"Transport group not found")
    used=c.execute("SELECT coalesce(sum(quantity_qtl),0) s FROM transport_group_members WHERE group_id=?",(group_id,)).fetchone()["s"]
    if used + x.quantity_qtl > g["capacity_qtl"] + 1e-6:
        c.close(); raise HTTPException(409,f"Only {round(g['capacity_qtl']-used,2)} qtl of space left on this lorry")
    c.execute(
        "INSERT INTO transport_group_members(group_id,farmer_id,crop,quantity_qtl,joined_at) VALUES(?,?,?,?,?) ON CONFLICT(group_id,farmer_id) DO UPDATE SET quantity_qtl=excluded.quantity_qtl,crop=excluded.crop",
        (group_id,u["id"],x.crop or g["crop"],x.quantity_qtl,now_iso())
    )
    c.commit()
    row=c.execute("SELECT * FROM transport_groups WHERE id=?",(group_id,)).fetchone()
    out=transport_group_row_out(c, row); c.close()
    return {"group_id":group_id,"quantity_qtl":x.quantity_qtl,"cost":round(x.quantity_qtl*g["cost_per_qtl"],2),"group":out}


def reference_amount_paise(c, ref_type, ref_id, user_id):

    # =========================================================
    # NORMAL ORDER PAYMENT
    # =========================================================
    if ref_type == "ORDER":

        r = c.execute(
            """
            SELECT total, buyer_id
            FROM orders
            WHERE id=?
            """,
            (ref_id,)
        ).fetchone()

        if not r:
            raise HTTPException(
                404,
                "Order not found"
            )

        if r["buyer_id"] != user_id:
            raise HTTPException(
                403,
                "This order does not belong to this buyer"
            )

        return int(
            round(
                float(r["total"]) * 100
            )
        )


    # =========================================================
    # PRE-ORDER TOKEN PAYMENT
    # =========================================================
    if ref_type == "PREORDER":

        p = c.execute(
            """
            SELECT
                buyer_id,
                deposit_amount,
                status
            FROM preorder_requests
            WHERE id=?
            """,
            (ref_id,)
        ).fetchone()

        if not p:
            raise HTTPException(
                404,
                "Pre-order not found"
            )

        if p["buyer_id"] != user_id:
            raise HTTPException(
                403,
                "This pre-order does not belong to this buyer"
            )

        # Buyer can pay token only after farmer accepts.
        if p["status"] not in (
            "AWAITING_TOKEN",
            "ACCEPTED"
        ):
            raise HTTPException(
                409,
                "Token payment is available only after the farmer accepts the pre-order"
            )

        deposit_amount = float(
            p["deposit_amount"] or 0
        )

        if deposit_amount <= 0:
            raise HTTPException(
                409,
                "This pre-order does not have a valid token amount"
            )

        return int(
            round(
                deposit_amount * 100
            )
        )


    # =========================================================
    # INVALID REFERENCE TYPE
    # =========================================================
    raise HTTPException(
        400,
        "Unsupported payment reference type"
    )


def razorpay_request(method,path,payload=None):
    if not requests or not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise RuntimeError("Razorpay credentials are not configured")
    url="https://api.razorpay.com/v1"+path
    r=requests.request(method,url,auth=(RAZORPAY_KEY_ID,RAZORPAY_KEY_SECRET),json=payload,timeout=20)
    if r.status_code>=400: raise RuntimeError(f"Razorpay error {r.status_code}: {r.text[:300]}")
    return r.json()


@router.post("/payments/create")
def create_payment(x:PaymentCreate,u=Depends(get_user_dep())):
    require_role(u,"buyer","admin"); c=conn(); amount=reference_amount_paise(c,x.reference_type,x.reference_id,u["id"])
    if amount<=0: c.close(); raise HTTPException(400,"Payable amount must be greater than zero")
    receipt=f"gram-{x.reference_type.lower()}-{x.reference_id}-{secrets.token_hex(3)}"
    if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET and not PAYMENT_DEMO_MODE:
        try: ro=razorpay_request("POST","/orders",{"amount":amount,"currency":"INR","receipt":receipt,"notes":{"reference_type":x.reference_type,"reference_id":str(x.reference_id)}}); goid=ro["id"]
        except Exception as e: c.close(); raise HTTPException(502,str(e))
    else: goid="order_demo_"+secrets.token_hex(8)
    cur=c.execute("""INSERT INTO payments_v2(user_id,purpose,reference_type,reference_id,expected_amount_paise,gateway_order_id,status,created_at,updated_at)
      VALUES(?,?,?,?,?,?,'CREATED',?,?)""",(u["id"],x.purpose,x.reference_type,x.reference_id,amount,goid,now_iso(),now_iso())); c.commit(); pid=cur.lastrowid;c.close()
    return {"payment_record_id":pid,"gateway_order_id":goid,"amount_paise":amount,"amount_rupees":round(amount/100,2),"currency":"INR","key_id":RAZORPAY_KEY_ID if RAZORPAY_KEY_ID else "rzp_test_demo","mode":"RAZORPAY_TEST" if RAZORPAY_KEY_ID else "DEMO_TEST","note":"Amount is derived by the backend from the order/pre-order record."}


@router.post("/payments/{payment_id}/verify")
def verify_payment(payment_id:int,x:PaymentVerify,u=Depends(get_user_dep())):
    c=conn(); p=c.execute("SELECT * FROM payments_v2 WHERE id=? AND user_id=?",(payment_id,u["id"])).fetchone()
    if not p:c.close();raise HTTPException(404,"Payment record not found")
    if p["gateway_order_id"]!=x.gateway_order_id:c.close();raise HTTPException(400,"Gateway order mismatch")
    if x.gateway_order_id.startswith("order_demo_"):
        ok = PAYMENT_DEMO_MODE and x.gateway_signature=="DEMO_SIGNATURE"
    else:
        digest=hmac.new(RAZORPAY_KEY_SECRET.encode(),f"{x.gateway_order_id}|{x.gateway_payment_id}".encode(),hashlib.sha256).hexdigest()
        ok=hmac.compare_digest(digest,x.gateway_signature)
    if not ok:c.close();raise HTTPException(400,"Payment signature verification failed")
    final_status = "SUCCESS" if p["webhook_verified"] else "CLIENT_VERIFIED"
    c.execute("UPDATE payments_v2 SET gateway_payment_id=?,client_signature_verified=1,status=?,updated_at=? WHERE id=?",(x.gateway_payment_id,final_status,now_iso(),payment_id));
    c.execute("INSERT INTO payment_events(payment_id,event_type,details,created_at) VALUES(?, 'CLIENT_SIGNATURE_VERIFIED',?,?)",(payment_id,"Both checks complete" if final_status=="SUCCESS" else "Awaiting trusted webhook confirmation",now_iso()));c.commit();c.close()
    return {"status":final_status,"message":"Payment verified by both client signature and webhook." if final_status=="SUCCESS" else "Signature verified. Payment will be marked successful only after webhook reconciliation."}


def create_excess_refund(c,payment_id,amount_paise,gateway_payment_id):
    existing=c.execute("SELECT * FROM refunds_v2 WHERE payment_id=? AND amount_paise=? ORDER BY id DESC LIMIT 1",(payment_id,amount_paise)).fetchone()
    if existing:return dict(existing)
    rid=""
    status="PROCESSING"
    if gateway_payment_id.startswith("pay_demo_") or PAYMENT_DEMO_MODE:
        rid="rfnd_demo_"+secrets.token_hex(7); status="PROCESSING"
    else:
        try:
            out=razorpay_request("POST",f"/payments/{gateway_payment_id}/refund",{"amount":amount_paise,"notes":{"reason":"GRAM AI automatic overpayment refund"}})
            rid=out.get("id",""); status="REFUNDED" if out.get("status")=="processed" else "PROCESSING"
        except Exception as e:
            status="FAILED"; rid="error:"+str(e)[:80]
    cur=c.execute("INSERT INTO refunds_v2(payment_id,amount_paise,gateway_refund_id,reason,status,created_at,updated_at) VALUES(?,?,?,'AUTOMATIC_OVERPAYMENT_REFUND',?,?,?)",(payment_id,amount_paise,rid,status,now_iso(),now_iso()))
    return {"id":cur.lastrowid,"status":status,"gateway_refund_id":rid,"amount_paise":amount_paise}


@router.post("/payments/webhook")
async def razorpay_webhook(request:Request):
    raw=await request.body(); sig=request.headers.get("X-Razorpay-Signature","")
    if RAZORPAY_WEBHOOK_SECRET:
        digest=hmac.new(RAZORPAY_WEBHOOK_SECRET.encode(),raw,hashlib.sha256).hexdigest()
        if not hmac.compare_digest(digest,sig): raise HTTPException(400,"Invalid webhook signature")
    elif not PAYMENT_DEMO_MODE:
        raise HTTPException(503,"Webhook secret is not configured")
    try: event=json.loads(raw.decode() or "{}")
    except Exception: raise HTTPException(400,"Invalid webhook JSON")
    et=event.get("event",""); entity=((event.get("payload") or {}).get("payment") or {}).get("entity") or {}
    goid=entity.get("order_id",""); gpid=entity.get("id",""); amount=int(entity.get("amount") or 0)
    c=conn(); p=c.execute("SELECT * FROM payments_v2 WHERE gateway_order_id=?",(goid,)).fetchone()
    if not p: c.close(); return {"ok":True,"ignored":True}
    phash=hashlib.sha256(raw).hexdigest(); c.execute("INSERT INTO payment_events(payment_id,gateway_event_id,event_type,payload_hash,details,created_at) VALUES(?,?,?,?,?,?)",(p["id"],event.get("id","") or "",et,phash,"Trusted webhook received",now_iso()))
    if et in ("payment.captured","order.paid"):
        over=max(0,amount-int(p["expected_amount_paise"])); status="SUCCESS" if p["client_signature_verified"] else "WEBHOOK_VERIFIED_WAITING_CLIENT"
        c.execute("UPDATE payments_v2 SET gateway_payment_id=?,webhook_verified=1,confirmed_amount_paise=?,overpayment_paise=?,status=?,updated_at=? WHERE id=?",(gpid,amount,over,status,now_iso(),p["id"]))
        refund=None
        if over>0: refund=create_excess_refund(c,p["id"],over,gpid)
    elif et=="payment.failed":
        c.execute("UPDATE payments_v2 SET status='FAILED',webhook_verified=1,updated_at=? WHERE id=?",(now_iso(),p["id"])); refund=None
    else: refund=None
    c.commit(); c.close(); return {"ok":True,"payment_status":status if et in ("payment.captured","order.paid") else et,"refund":refund}


@router.post("/payments/{payment_id}/demo-webhook")
def demo_webhook(payment_id:int,confirmed_amount_rupees:Optional[float]=None,u=Depends(get_user_dep())):
    # SIH/local-only helper to demonstrate the complete signature+webhook+overpayment flow without real money.
    c=conn(); p=c.execute("SELECT * FROM payments_v2 WHERE id=? AND user_id=?",(payment_id,u["id"])).fetchone()
    if not p:c.close();raise HTTPException(404,"Payment not found")
    if not PAYMENT_DEMO_MODE:c.close();raise HTTPException(403,"Demo webhook is disabled")
    amount=int(round((confirmed_amount_rupees*100) if confirmed_amount_rupees is not None else p["expected_amount_paise"]))
    over=max(0,amount-int(p["expected_amount_paise"])); status="SUCCESS" if p["client_signature_verified"] else "WEBHOOK_VERIFIED_WAITING_CLIENT"
    gpid=p["gateway_payment_id"] or "pay_demo_"+secrets.token_hex(7)
    c.execute("UPDATE payments_v2 SET gateway_payment_id=?,webhook_verified=1,confirmed_amount_paise=?,overpayment_paise=?,status=?,updated_at=? WHERE id=?",(gpid,amount,over,status,now_iso(),p["id"]))
    c.execute("INSERT INTO payment_events(payment_id,event_type,details,created_at) VALUES(?, 'DEMO_WEBHOOK_VERIFIED',?,?)",(p["id"],f"confirmed={amount}",now_iso()))
    refund=create_excess_refund(c,p["id"],over,gpid) if over else None; c.commit();c.close();return {"status":status,"overpayment_rupees":round(over/100,2),"refund":refund}


@router.get("/payments")
def payments(u=Depends(get_user_dep())):
    c=conn();
    if u["role"]=="admin": rows=c.execute("SELECT p.*,u.name user_name FROM payments_v2 p JOIN users u ON u.id=p.user_id ORDER BY p.id DESC LIMIT 200").fetchall()
    else: rows=c.execute("SELECT * FROM payments_v2 WHERE user_id=? ORDER BY id DESC",(u["id"],)).fetchall()
    out=[]
    for r in rows:
        d=dict(r);d["expected_amount_rupees"]=round(d["expected_amount_paise"]/100,2);d["confirmed_amount_rupees"]=round(d["confirmed_amount_paise"]/100,2);d["overpayment_rupees"]=round(d["overpayment_paise"]/100,2);d["refunds"]=[dict(x) for x in c.execute("SELECT * FROM refunds_v2 WHERE payment_id=? ORDER BY id DESC",(d["id"],)).fetchall()];out.append(d)
    c.close();return out


@router.get("/rewards/me")
def rewards_me(u=Depends(get_user_dep())):
    c=conn(); t=trust_for(c,u["id"]); rows=c.execute("SELECT * FROM reward_ledger WHERE user_id=? ORDER BY id DESC LIMIT 100",(u["id"],)).fetchall(); pts=sum(int(r["points"]) for r in rows); benefit=sum(float(r["benefit_rupees"]) for r in rows)
    # Profit improvement is deliberately labelled estimated: compare fulfilled order price to latest same-state crop reference where possible.
    if u["role"]=="farmer":
        order_rows=c.execute("""SELECT o.quantity_qtl,l.ask_price,l.crop,l.state FROM orders o JOIN listings l ON l.id=o.listing_id WHERE l.seller_id=? AND o.status IN ('PLACED','PAID','COMPLETED')""",(u["id"],)).fetchall()
        improvement=0.0
        for o in order_rows:
            ref=c.execute("""SELECT avg(p.modal_price) p FROM prices p JOIN markets m ON m.id=p.market_id WHERE p.crop=? AND m.state=? AND p.price_date=(SELECT max(price_date) FROM prices)""",(o["crop"],o["state"])).fetchone()["p"] or o["ask_price"]
            improvement += max(0,(float(o["ask_price"])-float(ref))*float(o["quantity_qtl"]))
    else: improvement=0.0
    c.close();return {"points":pts,"benefit_rupees":round(benefit,2),"estimated_profit_improvement_rupees":round(improvement,2),"trust":t,"history":[dict(r) for r in rows],"rules":{"fair_buyer":"Rewards offers near/above AI fair range","shared_logistics":"Credits for shared/optimized transport","zero_cancellation":"Streak improves matching priority","data_contribution":"Verified local data can unlock premium insights","collective_selling":"FPO/group fulfilment earns a multiplier","gram_guarantee":"Only pre-declared eligible recommendations qualify; benefits are platform credits/fee waivers, not guaranteed investment returns"}}


@router.get("/rewards/admin")
def rewards_admin(u=Depends(get_user_dep())):
    require_role(u,"admin"); c=conn(); rows=c.execute("SELECT r.*,u.name,u.role FROM reward_ledger r JOIN users u ON u.id=r.user_id ORDER BY r.id DESC LIMIT 200").fetchall(); c.close(); return [dict(r) for r in rows]


@router.post("/grievances")
def create_grievance(x:GrievanceIn,u=Depends(get_user_dep())):
    c=conn(); amount=0
    if x.payment_id:
        p=c.execute("SELECT confirmed_amount_paise,expected_amount_paise FROM payments_v2 WHERE id=?",(x.payment_id,)).fetchone(); amount=(p["confirmed_amount_paise"] or p["expected_amount_paise"])/100 if p else 0
    score,label=severity_for(x.category,x.description+" "+x.voice_transcript,amount); advice=resolution_advice(x.category,label)
    hours=4 if label=="CRITICAL" else 12 if label=="HIGH" else 24 if label=="MEDIUM" else 48; due=(datetime.now(timezone.utc)+timedelta(hours=hours)).isoformat()
    cur=c.execute("""INSERT INTO grievances_v2(complainant_id,against_user_id,order_id,payment_id,category,description,voice_transcript,severity,severity_score,ai_recommendation,status,escalation_level,due_at,created_at,updated_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,'OPEN',0,?,?,?)""",(u["id"],x.against_user_id,x.order_id,x.payment_id,x.category,x.description,x.voice_transcript,label,score,advice,due,now_iso(),now_iso())); gid=cur.lastrowid
    if x.against_user_id and label in ("HIGH","CRITICAL"):
        c.execute("INSERT INTO risk_alerts(user_id,risk_type,score,details,status,created_at) VALUES(?, 'GRIEVANCE_PATTERN',?,?, 'OPEN',?)",(x.against_user_id,score,f"Grievance #{gid}: {x.category}",now_iso()))
    if x.payment_id and label in ("HIGH","CRITICAL"):
        c.execute("UPDATE payments_v2 SET status='DISPUTE_HOLD',updated_at=? WHERE id=? AND status IN ('SUCCESS','CLIENT_VERIFIED','WEBHOOK_VERIFIED_WAITING_CLIENT')",(now_iso(),x.payment_id))
    c.commit();c.close();return {"id":gid,"severity":label,"severity_score":score,"ai_recommendation":advice,"due_at":due,"payment_hold":"INTERNAL_DISPUTE_HOLD" if x.payment_id and label in ("HIGH","CRITICAL") else "NONE"}


@router.post("/grievances/{grievance_id}/evidence")
async def grievance_evidence(grievance_id:int,file:UploadFile=File(...),u=Depends(get_user_dep())):
    c=conn(); g=c.execute("SELECT * FROM grievances_v2 WHERE id=?",(grievance_id,)).fetchone()
    if not g:c.close();raise HTTPException(404,"Grievance not found")
    if u["role"]!="admin" and g["complainant_id"]!=u["id"]:c.close();raise HTTPException(403,"Not your grievance")
    ext=os.path.splitext(file.filename or "evidence.bin")[1].lower(); allowed={".jpg",".jpeg",".png",".webp",".mp4",".mov",".pdf"}
    if ext not in allowed:c.close();raise HTTPException(400,"Allowed evidence: JPG, PNG, WEBP, MP4, MOV, PDF")
    data=await file.read();
    if len(data)>15*1024*1024:c.close();raise HTTPException(400,"Evidence file must be <= 15 MB")
    digest=hashlib.sha256(data).hexdigest(); name=f"g{grievance_id}_{secrets.token_hex(6)}{ext}"; path=os.path.join(EVIDENCE_DIR,name)
    with open(path,"wb") as f:f.write(data)
    c.execute("INSERT INTO grievance_evidence(grievance_id,file_path,media_type,sha256,created_at) VALUES(?,?,?,?,?)",(grievance_id,os.path.relpath(path,BASE),file.content_type or "",digest,now_iso()));c.commit();c.close();return {"message":"Evidence attached","sha256":digest}


@router.get("/grievances")
def grievances(u=Depends(get_user_dep())):
    c=conn();auto_escalate(c);c.commit()
    q="""SELECT g.*,uc.name complainant_name,ua.name against_name FROM grievances_v2 g JOIN users uc ON uc.id=g.complainant_id LEFT JOIN users ua ON ua.id=g.against_user_id""";params=[]
    if u["role"]!="admin":q+=" WHERE g.complainant_id=? OR g.against_user_id=?";params=[u["id"],u["id"]]
    q+=" ORDER BY CASE g.severity WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,g.id DESC";rows=c.execute(q,tuple(params)).fetchall();c.close();return [dict(r) for r in rows]


@router.post("/grievances/{grievance_id}/satisfaction")
def grievance_satisfaction(grievance_id:int,x:SatisfactionIn,u=Depends(get_user_dep())):
    c=conn();g=c.execute("SELECT * FROM grievances_v2 WHERE id=? AND complainant_id=?",(grievance_id,u["id"])).fetchone()
    if not g:c.close();raise HTTPException(404,"Grievance not found")
    status="CLOSED" if x.satisfaction=="SATISFIED" else "REOPENED"
    c.execute("UPDATE grievances_v2 SET satisfaction=?,status=?,updated_at=? WHERE id=?",(x.satisfaction,status,now_iso(),grievance_id))
    if g["against_user_id"]:
        trust_for(c,g["against_user_id"])
        delta = -2 if x.satisfaction=="SATISFIED" else -8
        c.execute("UPDATE trust_scores SET grievance_adjustment=max(-30,min(10,grievance_adjustment+?)),updated_at=? WHERE user_id=?",(delta,now_iso(),g["against_user_id"]))
    c.commit();c.close();return {"status":status}


@router.get("/community-alerts")
def community_alerts(state:str=DEFAULT_STATE,u=Depends(get_user_dep())):
    c=conn()
    rows=c.execute("""SELECT r.risk_type,r.score,r.details,r.created_at FROM risk_alerts r LEFT JOIN users u ON u.id=r.user_id WHERE r.status='OPEN' AND (u.state=? OR u.state IS NULL OR u.state='') AND r.score>=60 ORDER BY r.score DESC,r.id DESC LIMIT 20""",(state,)).fetchall()
    c.close()
    # No complainant or flagged-user identity is exposed.
    return [{"risk_type":r["risk_type"],"risk_level":"CRITICAL" if r["score"]>=80 else "HIGH","message":"Community risk pattern detected in this market area. Verify buyer/seller details and use protected platform flows.","created_at":r["created_at"]} for r in rows]

@router.get("/risk-alerts")
def risk_alerts(u=Depends(get_user_dep())):
    require_role(u,"admin");c=conn();rows=c.execute("SELECT r.*,u.name FROM risk_alerts r LEFT JOIN users u ON u.id=r.user_id ORDER BY score DESC,id DESC LIMIT 200").fetchall();c.close();return [dict(r) for r in rows]


@router.get("/heatmaps/demand")
def demand_heatmap(state:str=DEFAULT_STATE,crop:Optional[str]=None,u=Depends(get_user_dep())):
    c=conn(); rows=c.execute("""SELECT h.district,h.state,h.crop,round(sum(p.quantity_qtl),2) preorder_qtl,round(avg(p.offer_price),2) avg_offer,count(*) preorder_count
      FROM preorder_requests p JOIN harvests h ON h.id=p.harvest_id WHERE h.state=? AND (? IS NULL OR h.crop=?) GROUP BY h.district,h.state,h.crop ORDER BY preorder_qtl DESC""",(state,crop,crop)).fetchall()
    if not rows:
        rows=c.execute("""SELECT m.district,m.state,p.crop,round(avg(p.demand_index),1) preorder_qtl,round(avg(p.modal_price),2) avg_offer,count(*) preorder_count FROM prices p JOIN markets m ON m.id=p.market_id WHERE m.state=? AND (? IS NULL OR p.crop=?) GROUP BY m.district,m.state,p.crop ORDER BY preorder_qtl DESC LIMIT 50""",(state,crop,crop)).fetchall()
    c.close();return [dict(r) for r in rows]


@router.get("/heatmaps/grievances")
def grievance_heatmap(state:str=DEFAULT_STATE,u=Depends(get_user_dep())):
    require_role(u,"admin");c=conn();rows=c.execute("""SELECT coalesce(NULLIF(usr.district,''),'Unknown') district,coalesce(NULLIF(usr.state,''),?) state,count(*) grievance_count,round(avg(g.severity_score),1) avg_severity
      FROM grievances_v2 g JOIN users usr ON usr.id=g.complainant_id WHERE coalesce(NULLIF(usr.state,''),?)=? GROUP BY district,state ORDER BY grievance_count DESC,avg_severity DESC""",(DEFAULT_STATE,DEFAULT_STATE,state)).fetchall();c.close();return [dict(r) for r in rows]


@router.post("/admin/scan-protection")
def scan_protection(u=Depends(get_user_dep())):
    require_role(u,"admin")
    c=conn(); created=0
    # Failed payments become automatically detected payment-protection cases when no case exists.
    failed=c.execute("SELECT * FROM payments_v2 WHERE status='FAILED'").fetchall()
    for p in failed:
        ex=c.execute("SELECT id FROM grievances_v2 WHERE payment_id=? AND category='PAYMENT_FAILURE'",(p["id"],)).fetchone()
        if ex: continue
        score,label=severity_for('PAYMENT_FAILURE','Gateway payment failed',p["expected_amount_paise"]/100)
        due=(datetime.now(timezone.utc)+timedelta(hours=12 if label=='HIGH' else 24)).isoformat()
        c.execute("""INSERT INTO grievances_v2(complainant_id,payment_id,category,description,severity,severity_score,ai_recommendation,status,escalation_level,due_at,created_at,updated_at) VALUES(?,?,'PAYMENT_FAILURE','Automatically detected payment failure',?,?,?,'OPEN',0,?,?,?)""",(p["user_id"],p["id"],label,score,resolution_advice('PAYMENT',label),due,now_iso(),now_iso()));created+=1
    c.commit();c.close();return {"auto_detected_cases_created":created}

@router.get("/admin/overview")
def admin_overview(state:str=DEFAULT_STATE,u=Depends(get_user_dep())):
    require_role(u,"admin");c=conn();auto_escalate(c);c.commit()
    counts={
      "farmers":c.execute("SELECT count(*) n FROM users WHERE role='farmer' AND coalesce(NULLIF(state,''),?)=?",(DEFAULT_STATE,state)).fetchone()["n"],
      "buyers":c.execute("SELECT count(*) n FROM users WHERE role='buyer' AND coalesce(NULLIF(state,''),?)=?",(DEFAULT_STATE,state)).fetchone()["n"],
      "pending_kyc":c.execute("SELECT count(*) n FROM kyc_profiles WHERE status='PENDING'").fetchone()["n"],
      "open_grievances":c.execute("SELECT count(*) n FROM grievances_v2 WHERE status NOT IN ('CLOSED','RESOLVED')").fetchone()["n"],
      "risk_alerts":c.execute("SELECT count(*) n FROM risk_alerts WHERE status='OPEN'").fetchone()["n"],
      "payments":c.execute("SELECT count(*) n FROM payments_v2").fetchone()["n"],
      "payment_value_rupees":round((c.execute("SELECT coalesce(sum(confirmed_amount_paise),0) s FROM payments_v2 WHERE status='SUCCESS'").fetchone()["s"] or 0)/100,2),
      "refunds_processing":c.execute("SELECT count(*) n FROM refunds_v2 WHERE status='PROCESSING'").fetchone()["n"]
    }
    c.close();return {"state":state,"counts":counts,"security":{"auth":"JWT + bcrypt + role checks","kyc":"Masked Aadhaar/KYC provider-ready; no full Aadhaar stored","payments":"Backend amount + client signature + webhook reconciliation","audit":"Existing audit log + payment/grievance event trails"}}


@router.get("/chat")
def chat(q:str,state:str=DEFAULT_STATE,lang:str="en",u=Depends(get_user_dep())):
    text=(q or "").lower(); role=u["role"]
    intents = {
      "payment": any(k in text for k in ["payment","refund","money","पैसे","भुगतान","पेमेंट","refund","கட்டணம்","செலுத்த","చెల్లింపు","పేమెంట్"]),
      "preorder": any(k in text for k in ["preorder","pre-order","harvest","फसल","कटाई","पीक","कापणी","அறுவடை","பயிர்","పంట","కోత"]),
      "grievance": any(k in text for k in ["grievance","complaint","help","तक्रार","शिकायत","புகார்","உதவி","ఫిర్యాదు","సహాయం"]),
      "market": any(k in text for k in ["market","sell","price","wait","shift","store","भाव","बाजार","बेच","विक्री","बाजार","भाव","சந்தை","விலை","விற்க","మార్కెట్","ధర","అమ్మ"]),
    }
    if intents["payment"]: key="payment"
    elif intents["preorder"]: key="preorder"
    elif intents["grievance"]: key="grievance"
    elif intents["market"]: key="market"
    else: key="generic"
    T={
      "en":{
        "market":f"For {state}, I can help you decide SELL NOW, WAIT, SHIFT MARKET or STORE. Open Crops & Forecasts, choose crop and market, then run Forecast + Best Market. GRAM AI compares 1/3/7-day prices with transport and market charges.",
        "preorder":"In Pre-Orders, GRAM AI compares the buyer offer with the 1/3/7-day outlook, transport, charges and buyer reliability, then suggests ACCEPT, NEGOTIATE or WAIT.",
        "payment":"Payments use backend-calculated amounts. A payment is marked successful only after signature and webhook verification. Refund status is tracked separately.",
        "grievance":"Open Need Help → GramRakshak. You can speak or type the complaint, link the transaction, and upload photo/video evidence.",
        "generic":f"I am your GRAM Saathi for {state}. Ask me about crop price, SELL/WAIT/SHIFT/STORE, best market, pre-orders, buyers, payments, transport, rewards, KYC or grievances."
      },
      "hi":{
        "market":f"{state} के लिए मैं SELL NOW, WAIT, SHIFT MARKET या STORE का निर्णय समझा सकता हूँ। Crops & Forecasts में फसल और मंडी चुनकर Forecast + Best Market चलाएँ। सिस्टम 1/3/7 दिन के भाव, परिवहन और मंडी शुल्क की तुलना करता है।",
        "preorder":"Pre-Orders में GRAM AI खरीदार के ऑफर की 1/3/7 दिन के अनुमान, परिवहन लागत, बाजार शुल्क और खरीदार विश्वसनीयता से तुलना करके ACCEPT, NEGOTIATE या WAIT सुझाता है।",
        "payment":"भुगतान राशि backend से तय होती है। Signature और webhook verification दोनों के बाद ही भुगतान सफल माना जाता है। Refund की स्थिति अलग से ट्रैक होती है।",
        "grievance":"Need Help → GramRakshak खोलें। शिकायत बोलकर या लिखकर दें और फोटो/वीडियो प्रमाण जोड़ें।",
        "generic":f"मैं {state} के लिए आपका GRAM Saathi हूँ। फसल भाव, SELL/WAIT/SHIFT/STORE, मंडी, प्री-ऑर्डर, खरीदार, भुगतान, परिवहन, रिवॉर्ड, KYC या शिकायत पूछें।"
      },
      "mr":{
        "market":f"{state} साठी मी SELL NOW, WAIT, SHIFT MARKET किंवा STORE निर्णय समजावू शकतो. Crops & Forecasts मध्ये पीक आणि बाजार निवडा व Forecast + Best Market चालवा. 1/3/7 दिवसांचे भाव, वाहतूक आणि बाजार शुल्क तुलना केले जातात.",
        "preorder":"Pre-Orders मध्ये GRAM AI खरेदीदाराची ऑफर 1/3/7 दिवसांचा अंदाज, वाहतूक, बाजार शुल्क आणि खरेदीदार विश्वसनीयतेशी तुलना करून ACCEPT, NEGOTIATE किंवा WAIT सुचवतो.",
        "payment":"पेमेंटची रक्कम backend ठरवतो. Signature आणि webhook verification दोन्ही झाल्यावरच पेमेंट यशस्वी मानले जाते. Refund स्थिती स्वतंत्रपणे ट्रॅक केली जाते.",
        "grievance":"Need Help → GramRakshak उघडा. तक्रार बोला किंवा लिहा आणि फोटो/व्हिडिओ पुरावा जोडा.",
        "generic":f"मी {state} साठी तुमचा GRAM Saathi आहे. पीक भाव, SELL/WAIT/SHIFT/STORE, सर्वोत्तम बाजार, प्री-ऑर्डर, खरेदीदार, पेमेंट, वाहतूक, रिवॉर्ड, KYC किंवा तक्रार विचारा."
      },
      "ta":{
        "market":f"{state} மாநிலத்திற்கு SELL NOW, WAIT, SHIFT MARKET அல்லது STORE முடிவை நான் உதவிசெய்யலாம். Crops & Forecasts-ல் பயிர் மற்றும் சந்தையைத் தேர்வு செய்து Forecast + Best Market இயக்கவும். 1/3/7 நாள் விலை, போக்குவரத்து மற்றும் சந்தை கட்டணங்கள் ஒப்பிடப்படும்.",
        "preorder":"Pre-Orders பகுதியில் வாங்குபவர் சலுகை, 1/3/7 நாள் கணிப்பு, போக்குவரத்து செலவு, சந்தை கட்டணம் மற்றும் வாங்குபவர் நம்பகத்தன்மை ஆகியவற்றை GRAM AI ஒப்பிட்டு ACCEPT, NEGOTIATE அல்லது WAIT பரிந்துரைக்கும்.",
        "payment":"கட்டணத் தொகை backend-ல் கணக்கிடப்படுகிறது. Signature மற்றும் webhook verification இரண்டும் முடிந்த பிறகே payment successful ஆகும். Refund நிலை தனியாக கண்காணிக்கப்படும்.",
        "grievance":"Need Help → GramRakshak திறக்கவும். புகாரை பேசலாம் அல்லது எழுதலாம்; photo/video ஆதாரத்தையும் சேர்க்கலாம்.",
        "generic":f"நான் {state} மாநிலத்திற்கான உங்கள் GRAM Saathi. பயிர் விலை, SELL/WAIT/SHIFT/STORE, சிறந்த சந்தை, pre-order, buyer, payment, transport, rewards, KYC அல்லது grievance பற்றி கேளுங்கள்."
      },
      "te":{
        "market":f"{state} కోసం SELL NOW, WAIT, SHIFT MARKET లేదా STORE నిర్ణయానికి నేను సహాయం చేస్తాను. Crops & Forecasts లో పంట, మార్కెట్ ఎంచుకుని Forecast + Best Market నడపండి. 1/3/7 రోజుల ధరలు, రవాణా మరియు మార్కెట్ ఛార్జీలు పోల్చబడతాయి.",
        "preorder":"Pre-Orders లో కొనుగోలుదారుడి ఆఫర్‌ను 1/3/7 రోజుల అంచనా, రవాణా ఖర్చు, మార్కెట్ ఛార్జీలు మరియు buyer reliability తో పోల్చి ACCEPT, NEGOTIATE లేదా WAIT సూచిస్తుంది.",
        "payment":"చెల్లింపు మొత్తం backend నుంచి వస్తుంది. Signature మరియు webhook verification రెండూ పూర్తయిన తర్వాత మాత్రమే payment successful అవుతుంది. Refund స్థితి విడిగా ట్రాక్ అవుతుంది.",
        "grievance":"Need Help → GramRakshak తెరవండి. ఫిర్యాదును మాట్లాడి లేదా టైప్ చేసి, photo/video ఆధారాలను జోడించవచ్చు.",
        "generic":f"నేను {state} కోసం మీ GRAM Saathi. పంట ధర, SELL/WAIT/SHIFT/STORE, ఉత్తమ మార్కెట్, pre-orders, buyers, payments, transport, rewards, KYC లేదా grievances గురించి అడగండి."
      }
    }
    generic_by_lang={
      "bn":"আমি আপনার GRAM Saathi। ফসলের দাম, সেরা বাজার, বিক্রি/অপেক্ষা/বাজার বদল, প্রি-অর্ডার, পেমেন্ট ও অভিযোগ সম্পর্কে জিজ্ঞাসা করুন।",
      "gu":"હું તમારો GRAM Saathi છું. પાક ભાવ, શ્રેષ્ઠ બજાર, વેચો/રાહ જુઓ/બજાર બદલો, પ્રી-ઓર્ડર, ચુકવણી અને ફરિયાદ વિશે પૂછો.",
      "kn":"ನಾನು ನಿಮ್ಮ GRAM Saathi. ಬೆಳೆ ಬೆಲೆ, ಉತ್ತಮ ಮಾರುಕಟ್ಟೆ, ಮಾರಾಟ/ಕಾಯಿರಿ/ಮಾರುಕಟ್ಟೆ ಬದಲಿಸಿ, ಪೂರ್ವ-ಆರ್ಡರ್, ಪಾವತಿ ಮತ್ತು ದೂರುಗಳ ಬಗ್ಗೆ ಕೇಳಿ.",
      "ml":"ഞാൻ നിങ്ങളുടെ GRAM Saathi ആണ്. വിളവില, മികച്ച മാർക്കറ്റ്, വിൽക്കുക/കാത്തിരിക്കുക/മാർക്കറ്റ് മാറ്റുക, പ്രീ-ഓർഡർ, പേയ്മെന്റ്, പരാതി എന്നിവയെക്കുറിച്ച് ചോദിക്കുക.",
      "pa":"ਮੈਂ ਤੁਹਾਡਾ GRAM Saathi ਹਾਂ। ਫਸਲ ਭਾਅ, ਸਭ ਤੋਂ ਵਧੀਆ ਮਾਰਕੀਟ, ਵੇਚੋ/ਉਡੀਕੋ/ਮਾਰਕੀਟ ਬਦਲੋ, ਪ੍ਰੀ-ਆਰਡਰ, ਭੁਗਤਾਨ ਅਤੇ ਸ਼ਿਕਾਇਤ ਬਾਰੇ ਪੁੱਛੋ।",
      "or":"ମୁଁ ଆପଣଙ୍କ GRAM Saathi। ଫସଲ ଦର, ଶ୍ରେଷ୍ଠ ବଜାର, ବିକ୍ରି/ଅପେକ୍ଷା/ବଜାର ବଦଳ, ପ୍ରି-ଅର୍ଡର, ପେମେଣ୍ଟ ଓ ଅଭିଯୋଗ ବିଷୟରେ ପଚାରନ୍ତୁ।",
      "as":"মই আপোনাৰ GRAM Saathi। শস্যৰ দাম, শ্ৰেষ্ঠ বজাৰ, বিক্ৰী/অপেক্ষা/বজাৰ সলনি, প্ৰি-অৰ্ডাৰ, পেমেণ্ট আৰু অভিযোগৰ বিষয়ে সোধক।",
      "ur":"میں آپ کا GRAM Saathi ہوں۔ فصل کی قیمت، بہترین بازار، فروخت/انتظار/بازار تبدیل، پری آرڈر، ادائیگی اور شکایت کے بارے میں پوچھیں۔",
      "ne":"म तपाईंको GRAM Saathi हुँ। बालीको मूल्य, उत्तम बजार, बेच्ने/पर्खने/बजार बदल्ने, प्रि-अर्डर, भुक्तानी र गुनासोबारे सोध्नुहोस्।",
      "sa":"अहं भवतः GRAM Saathi अस्मि। सस्यमूल्यं, श्रेष्ठविपणिः, विक्रयः/प्रतीक्षा/विपणिपरिवर्तनं, पूर्वादेशः, भुगतानं, शिकायतां च पृच्छतु।",
      "ks":"بیٚیہِ چھُس تُہند GRAM Saathi. فصل قیمت، بہترین بازار، فروخت/انتظار/بازار تبدیلی، پری آرڈر، ادائیگی یا شکایت متعلق پُچھِو۔",
      "sd":"مان توهان جو GRAM Saathi آهيان. فصل جي قيمت، بهترين مارڪيٽ، وڪرو/انتظار/مارڪيٽ بدلائڻ، پري آرڊر، ادائگي ۽ شڪايت بابت پڇو.",
      "kok":"हांव तुमचो GRAM Saathi. पिकाचो भाव, बरो बाजार, विक्री/रावप/बाजार बदलप, प्री-ऑर्डर, पेमेंट आनी तक्रार हाचे विशीं विचारात.",
      "mai":"हम अहाँक GRAM Saathi छी। फसल भाव, श्रेष्ठ बाजार, बेचू/रुकू/बाजार बदलू, प्री-ऑर्डर, भुगतान आ शिकायतक विषयमे पूछू।",
      "doi":"मैं तुंदा GRAM Saathi आं। फसल भाव, सबे शा चंगा बजार, बेचो/रुको/बजार बदलो, प्री-ऑर्डर, भुगतान ते शिकायत बारे पुच्छो।",
      "brx":"आं नोंथांनि GRAM Saathi. आबादनि दाम, साबसिन बाजार, फानाय/थानाय/बाजार सोलायनाय, प्रि-अर्डार, पेमेंट आरो अजदनि सोमोन्दै सों।",
      "mni":"ঐ নখোয়গী GRAM Saathi। লৌউগী মমল, ফজবা কৈথেল, য়োনবা/ঙাইবা/কৈথেল হোংবা, প্রী-অর্ডর, শেল পীবা নত্রগা অভিযোগগী মতাংদা হংবিয়ু।",
      "sat":"ᱤᱧ ᱟᱢᱟᱜ GRAM Saathi. ᱪᱟᱥ ᱫᱟᱢ, ᱥᱟᱨᱮᱥ ᱦᱟᱴ, ᱟᱠᱨᱤᱧ/ᱛᱟᱹᱝᱜᱤ/ᱦᱟᱴ ᱵᱚᱫᱚᱞ, ᱯᱨᱤ-ᱚᱨᱰᱟᱨ, ᱯᱮᱢᱮᱱᱴ ᱟᱨ ᱟᱨᱡᱤ ᱵᱟᱵᱚᱫ ᱠᱩᱞᱤᱭᱟᱹᱧ।",
      "raj":"म्हूं थारो GRAM Saathi हूं। फसल भाव, सगळै सूं अच्छो बाजार, बेचण/रुकण/मंडी बदलण, प्री-ऑर्डर, भुगतान अर शिकायत बारे पूछो।"
    }
    if lang in T: ans=T[lang].get(key,T[lang]["generic"])
    elif lang in generic_by_lang: ans=generic_by_lang[lang]
    else: ans=T["en"].get(key,T["en"]["generic"])
    return {"answer":ans,"language":lang,"state":state,"role":role,"intent":key}



def seed_innovation_demo():
    """Seed only new SIH tables when empty; never touches legacy records."""
    c=conn()
    if c.execute("SELECT count(*) FROM harvests").fetchone()[0]==0:
        samples=[
          (1,'Tomato','Premium',80,80,'2026-09-05',2450,'Coimbatore','Tamil Nadu','A'),
          (1,'Onion','Small Onion',120,120,'2026-09-12',2200,'Dindigul','Tamil Nadu','A'),
          (1,'Banana','Nendran',60,60,'2026-10-01',2600,'Theni','Tamil Nadu','B')
        ]
        for r in samples:
            c.execute("""INSERT INTO harvests(farmer_id,crop,variety,expected_quantity_qtl,available_quantity_qtl,expected_harvest_date,expected_price,district,state,grade_expected,status,created_at)
                         VALUES(?,?,?,?,?,?,?,?,?,?,'OPEN',?)""",(*r,now_iso()))
    c.execute("INSERT OR IGNORE INTO trust_scores(user_id,buyer_reliability,harvest_commitment,instant_payment,zero_cancel_streak,grievance_adjustment,updated_at) VALUES(2,84,70,88,6,0,?)",(now_iso(),))
    c.execute("INSERT OR IGNORE INTO trust_scores(user_id,buyer_reliability,harvest_commitment,instant_payment,zero_cancel_streak,grievance_adjustment,updated_at) VALUES(1,70,86,70,4,0,?)",(now_iso(),))
    if c.execute("SELECT count(*) FROM reward_ledger").fetchone()[0]==0:
        c.execute("INSERT INTO reward_ledger(user_id,reward_type,points,benefit_rupees,reason,reference_type,created_at) VALUES(1,'DATA_CONTRIBUTION',40,0,'Verified local crop information contribution','PROFILE',?)",(now_iso(),))
        c.execute("INSERT INTO reward_ledger(user_id,reward_type,points,benefit_rupees,reason,reference_type,created_at) VALUES(2,'INSTANT_PAYMENT',60,50,'Fast payment streak benefit','BUYER_TRUST',?)",(now_iso(),))
    c.commit();c.close()

# Initialize on import so existing seed DB is upgraded without destructive replacement.
init_innovation_schema()
seed_innovation_demo()

# ============================================================
# GRAM AI V3 - role-complete prototype extensions
# ============================================================

def init_v3_schema():
    c=conn()
    # Safe additive columns.
    alters={
      'kyc_profiles':[
        ('selfie_path','TEXT NOT NULL DEFAULT ""'),('live_check','INTEGER NOT NULL DEFAULT 0')],
      'harvests':[
        ('verification_id','INTEGER'),('token_amount','REAL NOT NULL DEFAULT 0'),('latitude','REAL'),('longitude','REAL'),('photo_path','TEXT NOT NULL DEFAULT ""'),('certificate_path','TEXT NOT NULL DEFAULT ""'),('quality_confidence','REAL NOT NULL DEFAULT 0'),('buyer_visible','INTEGER NOT NULL DEFAULT 1'),('transport_rate_per_km','REAL NOT NULL DEFAULT 0'),('transport_radius_km','REAL NOT NULL DEFAULT 0')],
      'preorder_requests':[
    ('token_payment_status','TEXT NOT NULL DEFAULT "UNPAID"'),
    ('farmer_decision','TEXT NOT NULL DEFAULT "PENDING"'),
    ('buyer_decision','TEXT NOT NULL DEFAULT "PENDING"'),
    ('buyer_demand_id','INTEGER'),
    ('special_requirements','TEXT NOT NULL DEFAULT ""'),
    ('delivery_location','TEXT NOT NULL DEFAULT ""'),
    ('delivery_mode','TEXT NOT NULL DEFAULT "BUYER_PICKUP"')]
    }
    for table, cols in alters.items():
        existing={r['name'] for r in c.execute(f'PRAGMA table_info({table})').fetchall()}
        for name, spec in cols:
            if name not in existing:
                c.execute(f'ALTER TABLE {table} ADD COLUMN {name} {spec}')
    c.executescript('''
        CREATE TABLE IF NOT EXISTS buyer_preorder_demands(
      id INTEGER PRIMARY KEY AUTOINCREMENT,

      buyer_id INTEGER NOT NULL,

      crop TEXT NOT NULL,
      variety TEXT NOT NULL DEFAULT 'Any',
      grade_required TEXT NOT NULL DEFAULT 'Any',

      quantity_qtl REAL NOT NULL,
      remaining_quantity_qtl REAL NOT NULL,

      offer_price REAL NOT NULL,

      required_by_date TEXT NOT NULL,

      delivery_district TEXT NOT NULL DEFAULT '',
      delivery_state TEXT NOT NULL DEFAULT 'Tamil Nadu',

      delivery_mode TEXT NOT NULL DEFAULT 'BUYER_PICKUP',

      token_offer REAL NOT NULL DEFAULT 0,

      special_requirements TEXT NOT NULL DEFAULT '',

      status TEXT NOT NULL DEFAULT 'OPEN',

      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );


    CREATE TABLE IF NOT EXISTS buyer_preorder_responses(
      id INTEGER PRIMARY KEY AUTOINCREMENT,

      demand_id INTEGER NOT NULL,

      farmer_id INTEGER NOT NULL,

      harvest_id INTEGER,

      quantity_qtl REAL NOT NULL DEFAULT 0,

      farmer_price REAL,

      action TEXT NOT NULL DEFAULT 'INTERESTED',

      message TEXT NOT NULL DEFAULT '',

      linked_preorder_id INTEGER,

      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,

      UNIQUE(demand_id, farmer_id)
    );


    CREATE INDEX IF NOT EXISTS idx_buyer_demand_status
    ON buyer_preorder_demands(status, delivery_state, crop);


    CREATE INDEX IF NOT EXISTS idx_buyer_demand_buyer
    ON buyer_preorder_demands(buyer_id, status);


    CREATE INDEX IF NOT EXISTS idx_buyer_demand_response
    ON buyer_preorder_responses(demand_id, farmer_id);

    CREATE TABLE IF NOT EXISTS buyer_offers(
      id INTEGER PRIMARY KEY AUTOINCREMENT, buyer_user_id INTEGER NOT NULL, listing_id INTEGER NOT NULL,
      offer_price REAL NOT NULL, quantity_qtl REAL NOT NULL, pitch TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'OPEN',
      farmer_action TEXT NOT NULL DEFAULT 'PENDING', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS chat_threads(
      id INTEGER PRIMARY KEY AUTOINCREMENT, farmer_id INTEGER NOT NULL, buyer_id INTEGER NOT NULL, listing_id INTEGER,
      preorder_id INTEGER, last_message TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL,
      UNIQUE(farmer_id,buyer_id,listing_id,preorder_id));
    CREATE TABLE IF NOT EXISTS chat_messages(
      id INTEGER PRIMARY KEY AUTOINCREMENT, thread_id INTEGER NOT NULL, sender_id INTEGER NOT NULL,
      message TEXT NOT NULL, offer_price REAL, created_at TEXT NOT NULL, read_at TEXT);
    CREATE TABLE IF NOT EXISTS order_feedback(
      id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, from_user_id INTEGER NOT NULL,
      target_type TEXT NOT NULL, target_id INTEGER, rating INTEGER NOT NULL, comments TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
      UNIQUE(order_id,from_user_id,target_type));
    CREATE TABLE IF NOT EXISTS transport_bookings(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, transporter_id INTEGER, order_id INTEGER,
      listing_id INTEGER, crop TEXT NOT NULL DEFAULT '', pickup TEXT NOT NULL DEFAULT '', dropoff TEXT NOT NULL DEFAULT '',
      distance_km REAL NOT NULL DEFAULT 0, quoted_cost REAL NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'REQUESTED',
      shared INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS reward_catalog(
      id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL, role TEXT NOT NULL, title TEXT NOT NULL,
      points_cost INTEGER NOT NULL, benefit_rupees REAL NOT NULL DEFAULT 0, description TEXT NOT NULL, valid_days INTEGER NOT NULL DEFAULT 30, active INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS reward_redemptions(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, reward_code TEXT NOT NULL,
      points_used INTEGER NOT NULL, benefit_rupees REAL NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'ACTIVE',
      expires_at TEXT NOT NULL, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS user_actions(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, action TEXT NOT NULL,
      reason TEXT NOT NULL DEFAULT '', active INTEGER NOT NULL DEFAULT 1, admin_id INTEGER NOT NULL,
      created_at TEXT NOT NULL, resolved_at TEXT);
    CREATE TABLE IF NOT EXISTS network_profiles(
      id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT NOT NULL, name TEXT NOT NULL, state TEXT NOT NULL, district TEXT NOT NULL,
      lat REAL NOT NULL, lon REAL NOT NULL, crops TEXT NOT NULL DEFAULT '', verified INTEGER NOT NULL DEFAULT 1,
      rating REAL NOT NULL DEFAULT 4.5, phone_masked TEXT NOT NULL DEFAULT '', volume_qtl REAL NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS buyer_pools(
      id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER NOT NULL, name TEXT NOT NULL, crop TEXT NOT NULL,
      district TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'Tamil Nadu', target_qtl REAL NOT NULL, current_qtl REAL NOT NULL DEFAULT 0,
      status TEXT NOT NULL DEFAULT 'OPEN', created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS buyer_pool_members(
      id INTEGER PRIMARY KEY AUTOINCREMENT, pool_id INTEGER NOT NULL, buyer_id INTEGER NOT NULL, quantity_qtl REAL NOT NULL,
      created_at TEXT NOT NULL, UNIQUE(pool_id,buyer_id));
    CREATE TABLE IF NOT EXISTS order_tracking(
      id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, status TEXT NOT NULL, note TEXT NOT NULL DEFAULT '',
      location_text TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);

        CREATE TABLE IF NOT EXISTS buyer_pool_invites(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      pool_id INTEGER NOT NULL,
      from_buyer_id INTEGER NOT NULL,
      to_buyer_id INTEGER NOT NULL,
      proposed_quantity_qtl REAL NOT NULL DEFAULT 0,
      message TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL DEFAULT 'PENDING',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      UNIQUE(pool_id,to_buyer_id)
    );

    CREATE TABLE IF NOT EXISTS logistics_route_bids(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      buyer_id INTEGER NOT NULL,
      transporter_id INTEGER NOT NULL,
      pool_id INTEGER,
      crop TEXT NOT NULL DEFAULT '',
      quantity_qtl REAL NOT NULL,
      pickup_location TEXT NOT NULL,
      delivery_location TEXT NOT NULL,
      pickup_date TEXT NOT NULL,
      pickup_time TEXT NOT NULL DEFAULT '',
      proposed_bid REAL NOT NULL,
      estimated_distance_km REAL NOT NULL DEFAULT 0,
      estimated_cost REAL NOT NULL DEFAULT 0,
      special_instructions TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL DEFAULT 'PENDING',
      confirmation_code TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_pool_invites_buyer
    ON buyer_pool_invites(to_buyer_id,status);

    CREATE INDEX IF NOT EXISTS idx_route_bids_buyer
    ON logistics_route_bids(buyer_id,status);
    ''')

    # =========================================================
    # BUYER BULK ORDER / SHARED LOGISTICS V4 COLUMNS
    # =========================================================

    bulk_columns = [
        ("join_code", "TEXT"),
        ("variety", "TEXT NOT NULL DEFAULT 'Any'"),
        ("grade_required", "TEXT NOT NULL DEFAULT 'Any'"),
        ("target_price", "REAL NOT NULL DEFAULT 0"),
        ("required_by_date", "TEXT NOT NULL DEFAULT ''"),
        ("delivery_location", "TEXT NOT NULL DEFAULT ''"),
        ("transport_preference", "TEXT NOT NULL DEFAULT 'FLEXIBLE'"),
        ("special_requirements", "TEXT NOT NULL DEFAULT ''"),
        ("updated_at", "TEXT")
    ]

    existing_pool_columns = {
        row["name"]
        for row in c.execute(
            "PRAGMA table_info(buyer_pools)"
        ).fetchall()
    }

    for column_name, definition in bulk_columns:

        if column_name not in existing_pool_columns:

            c.execute(
                f"""
                ALTER TABLE buyer_pools
                ADD COLUMN {column_name} {definition}
                """
            )


    # Generate join codes for older buyer pools.
    old_pools = c.execute(
        """
        SELECT id
        FROM buyer_pools
        WHERE join_code IS NULL
           OR trim(join_code)=''
        """
    ).fetchall()

    for pool in old_pools:

        code = (
            "GB-"
            + secrets.token_hex(3).upper()
        )

        c.execute(
            """
            UPDATE buyer_pools
            SET join_code=?,
                updated_at=?
            WHERE id=?
            """,
            (
                code,
                now_iso(),
                pool["id"]
            )
        )

    c.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_buyer_pool_join_code
        ON buyer_pools(join_code)
        """
    )


    # Reward catalogue
    rewards=[
      ('FARM_TRANSPORT_100','farmer','₹100 Transport Cashback',120,100,'Use on an eligible shared/verified transport booking.',45),
      ('FARM_FEE_WAIVER','farmer','Platform Fee Waiver',200,150,'Waives up to ₹150 of eligible platform fees.',30),
      ('FARM_PRIORITY_MATCH','farmer','Priority Buyer Matching',150,0,'Priority matching badge for 30 days.',30),
      ('BUY_PREMIUM_30','buyer','Premium Harvest Access',180,0,'Early access to upcoming verified harvests for 30 days.',30),
      ('BUY_TRANSPORT_150','buyer','₹150 Logistics Coupon',160,150,'Use on eligible shared transport.',45),
      ('BUY_FEE_WAIVER','buyer','Buyer Fee Waiver',220,200,'Waives up to ₹200 of eligible platform fees.',30)]
    for r in rewards:
        c.execute('INSERT OR IGNORE INTO reward_catalog(code,role,title,points_cost,benefit_rupees,description,valid_days) VALUES(?,?,?,?,?,?,?)',r)
    # Demo network across India with Tamil Nadu dense coverage.
    if c.execute('SELECT count(*) n FROM network_profiles').fetchone()['n']==0:
        points=[
          ('farmer','Kongu Tomato Farm','Tamil Nadu','Coimbatore',11.0168, 76.9558,'Tomato, Onion',1,4.8,'******4210',90),
          ('farmer','Dindigul Fresh Growers','Tamil Nadu','Dindigul',10.3673,77.9803,'Onion, Grapes, Tomato',1,4.9,'******1182',160),
          ('farmer','Erode Farm Collective','Tamil Nadu','Erode',11.3410,77.7172,'Sugarcane, Turmeric, Chilli',1,4.7,'******4509',210),
          ('farmer','Madurai Banana Growers','Tamil Nadu','Madurai',9.9252,78.1198,'Banana, Maize',1,4.6,'******3321',140),
          ('buyer','Chennai FreshMart','Tamil Nadu','Chennai',13.0827,80.2707,'Tomato, Onion, Banana',1,4.9,'******7812',300),
          ('buyer','Coimbatore Food Hub','Tamil Nadu','Coimbatore',11.0168, 76.9558,'Tomato, Potato, Onion',1,4.8,'******8822',220),
          ('buyer','Dindigul Procurement','Tamil Nadu','Dindigul',10.3673,77.9803,'Onion, Tomato, Banana',1,4.7,'******9901',250),
          ('farmer','Pollachi Growers','Tamil Nadu','Pollachi',10.6609,77.0048,'Tomato, Banana',1,4.7,'******2701',100),
          ('farmer','Punjab Grain Collective','Punjab','Ludhiana',30.9010,75.8573,'Wheat, Maize',1,4.8,'******5502',300),
          ('buyer','Bengaluru Produce Hub','Karnataka','Bengaluru',12.9716,77.5946,'Tomato, Banana, Onion',1,4.8,'******6603',260),
          ('buyer','Ahmedabad Agri Buyers','Gujarat','Ahmedabad',23.0225,72.5714,'Groundnut, Cotton, Onion',1,4.6,'******7711',290)]
        c.executemany('INSERT INTO network_profiles(role,name,state,district,lat,lon,crops,verified,rating,phone_masked,volume_qtl) VALUES(?,?,?,?,?,?,?,?,?,?,?)',points)
    # Demo accounts are pre-verified only so every SIH screen is demonstrable. Newly registered users remain gated until KYC + live photo is verified.
    for uid,last4 in ((1,'4321'),(2,'6789')):
        if not c.execute('SELECT 1 FROM kyc_profiles WHERE user_id=?',(uid,)).fetchone():
            c.execute("INSERT INTO kyc_profiles(user_id,method,document_type,masked_document,aadhaar_last4,consent,status,selfie_path,live_check,submitted_at,verified_at,verified_by) VALUES(?, 'AADHAAR','AADHAAR',?, ?,1,'VERIFIED','DEMO_LIVE_SELFIE',1,?,?,3)",(uid,'XXXX-XXXX-'+last4,last4,now_iso(),now_iso()))

    # Demo buyer offers and chats on legacy listings.
    if c.execute('SELECT count(*) n FROM buyer_offers').fetchone()['n']==0:
        c.execute("INSERT INTO buyer_offers(buyer_user_id,listing_id,offer_price,quantity_qtl,pitch,status,created_at,updated_at) VALUES(2,1,2250,8,'I can pick up within 24 hours. Fast payment and reusable crates available.','OPEN',?,?)",(now_iso(),now_iso()))
        c.execute("INSERT INTO buyer_offers(buyer_user_id,listing_id,offer_price,quantity_qtl,pitch,status,created_at,updated_at) VALUES(2,2,2050,12,'Buying for Chennai retail demand. Token payment can be made immediately.','OPEN',?,?)",(now_iso(),now_iso()))
    # Seed farmer points high enough to demonstrate redemption.
    pts=c.execute('SELECT coalesce(sum(points),0) p FROM reward_ledger WHERE user_id=1').fetchone()['p']
    if pts<180:
        c.execute("INSERT INTO reward_ledger(user_id,reward_type,points,benefit_rupees,reason,reference_type,created_at) VALUES(1,'SIH_DEMO_BONUS',180,0,'Prototype demo reward balance','DEMO',?)",(now_iso(),))
    pts2=c.execute('SELECT coalesce(sum(points),0) p FROM reward_ledger WHERE user_id=2').fetchone()['p']
    if pts2<200:
        c.execute("INSERT INTO reward_ledger(user_id,reward_type,points,benefit_rupees,reason,reference_type,created_at) VALUES(2,'SIH_DEMO_BONUS',200,0,'Prototype demo reward balance','DEMO',?)",(now_iso(),))
    c.commit();c.close()


def kyc_status(c,uid):
    r=c.execute('SELECT * FROM kyc_profiles WHERE user_id=?',(uid,)).fetchone()
    return rowdict(r) if r else {'status':'NOT_STARTED','live_check':0,'masked_document':''}

def ensure_verified(c,u,action='use marketplace'):
    if u['role']=='admin': return
    k=kyc_status(c,u['id'])
    if k.get('status')!='VERIFIED' or not int(k.get('live_check') or 0):
        raise HTTPException(403,f'GRAM Verified KYC + live photo is required before you can {action}. Complete Profile → KYC first.')
    active=c.execute("SELECT action FROM user_actions WHERE user_id=? AND active=1 AND action IN ('BLOCK','TERMINATE') ORDER BY id DESC LIMIT 1",(u['id'],)).fetchone()
    if active: raise HTTPException(403,f"Account is {active['action'].lower()}ed by platform administration.")

@router.get('/v3/me-status')
def v3_me_status(u=Depends(get_user_dep())):
    c=conn(); k=kyc_status(c,u['id'])
    actions=[rowdict(r) for r in c.execute('SELECT * FROM user_actions WHERE user_id=? AND active=1 ORDER BY id DESC',(u['id'],)).fetchall()]
    points=c.execute('SELECT coalesce(sum(points),0) p FROM reward_ledger WHERE user_id=?',(u['id'],)).fetchone()['p']
    used=c.execute("SELECT coalesce(sum(points_used),0) p FROM reward_redemptions WHERE user_id=? AND status!='CANCELLED'",(u['id'],)).fetchone()['p']
    c.close(); return {'kyc':k,'verified':k.get('status')=='VERIFIED' and bool(k.get('live_check')),'actions':actions,'reward_points':max(0,points-used)}

@router.post('/v3/kyc-live')
async def v3_kyc_live(method:str=Form('AADHAAR'),aadhaar_last4:str=Form(''),consent:bool=Form(...),selfie:UploadFile=File(...),u=Depends(get_user_dep())):
    if not consent: raise HTTPException(400,'Consent is required')
    if method=='AADHAAR' and (not re.fullmatch(r'\d{4}',aadhaar_last4 or '')): raise HTTPException(400,'Enter only the last 4 Aadhaar digits')
    if not selfie.content_type or not selfie.content_type.startswith('image/'): raise HTTPException(400,'Live selfie image is required')
    folder=os.path.join(BASE,'uploads','kyc');os.makedirs(folder,exist_ok=True)
    data=await selfie.read()
    if not data or len(data)>8*1024*1024: raise HTTPException(400,'Selfie must be an image below 8 MB')
    path=os.path.join(folder,f'kyc_{u["id"]}_{secrets.token_hex(6)}.jpg');open(path,'wb').write(data)
    masked='XXXX-XXXX-'+(aadhaar_last4 if aadhaar_last4 else 'KYC')
    c=conn(); existing=c.execute('SELECT id FROM kyc_profiles WHERE user_id=?',(u['id'],)).fetchone()
    if existing:
      c.execute("UPDATE kyc_profiles SET method=?,document_type=?,masked_document=?,aadhaar_last4=?,consent=1,status='PENDING',selfie_path=?,live_check=1,submitted_at=? WHERE user_id=?",(method,method,masked,aadhaar_last4,path,now_iso(),u['id']))
    else:
      c.execute("INSERT INTO kyc_profiles(user_id,method,document_type,masked_document,aadhaar_last4,consent,status,selfie_path,live_check,submitted_at) VALUES(?,?,?,?,?,1,'PENDING',?,1,?)",(u['id'],method,method,masked,aadhaar_last4,path,now_iso()))
    c.commit();c.close();return {'status':'PENDING','masked_document':masked,'live_photo_received':True}

@router.post('/v3/harvest-from-verification')
def v3_harvest_from_verification(verification_id:int,quantity_qtl:float,harvest_date:str,variety:str='Standard',ask_price:float=0,token_amount:float=0,buyer_visible:bool=True,transport_rate_per_km:float=0,transport_radius_km:float=0,u=Depends(get_user_dep())):
    require_role(u,'farmer');c=conn();ensure_verified(c,u,'publish a harvest')
    v=c.execute('SELECT * FROM quality_verifications WHERE id=? AND user_id=?',(verification_id,u['id'])).fetchone()
    if not v:c.close();raise HTTPException(404,'YOLO/GPS verification not found')
    # nearest market resolves district/state from verified GPS
    m=c.execute('SELECT *, ((lat-?)*(lat-?)+(lon-?)*(lon-?)) d FROM markets ORDER BY d LIMIT 1',(v['latitude'],v['latitude'],v['longitude'],v['longitude'])).fetchone()
    cur=c.execute('''INSERT INTO harvests(farmer_id,crop,variety,expected_quantity_qtl,available_quantity_qtl,expected_harvest_date,expected_price,district,state,grade_expected,status,created_at,verification_id,token_amount,latitude,longitude,photo_path,certificate_path,quality_confidence,buyer_visible,transport_rate_per_km,transport_radius_km)
      VALUES(?,?,?,?,?,?,?,?,?,?,'OPEN',?,?,?,?,?,?,?,?,?,?,?)''',(u['id'],v['crop'],variety,quantity_qtl,quantity_qtl,harvest_date,ask_price,m['district'] if m else u['district'],m['state'] if m else 'Tamil Nadu',v['predicted_grade'],now_iso(),verification_id,token_amount,v['latitude'],v['longitude'],v['image_path'],v['certificate_path'],v['confidence'],int(buyer_visible),transport_rate_per_km,transport_radius_km))
    hid=cur.lastrowid
    try:
      from geo_api import resolve_place
      place=resolve_place(v['latitude'],v['longitude'])['place']
      c.execute('UPDATE harvests SET location_text=? WHERE id=?',(place,hid))
    except Exception:
      place=''
    c.commit();c.close();return {'id':hid,'status':'OPEN','buyer_visible':buyer_visible,'grade':v['predicted_grade'],'certificate_url':f'/api/produce/certificate/{verification_id}','place':place}

@router.get('/v3/harvests')
def v3_harvests(state:str='Tamil Nadu',u=Depends(get_user_dep())):
    c=conn();
    if u['role']=='farmer':
      rows=c.execute('''SELECT h.*,q.certificate_number FROM harvests h LEFT JOIN quality_certificates q ON q.verification_id=h.verification_id WHERE h.farmer_id=? ORDER BY h.created_at DESC''',(u['id'],)).fetchall()
    else:
      rows=c.execute('''SELECT h.*,us.name farmer_name,k.status kyc_status,q.certificate_number FROM harvests h JOIN users us ON us.id=h.farmer_id LEFT JOIN kyc_profiles k ON k.user_id=h.farmer_id LEFT JOIN quality_certificates q ON q.verification_id=h.verification_id WHERE h.state=? AND h.status='OPEN' AND h.buyer_visible=1 ORDER BY h.expected_harvest_date''',(state,)).fetchall()
    out=[]
    for r in rows:
      d=rowdict(r);d['certificate_url']=f"/api/produce/certificate/{d['verification_id']}" if d.get('verification_id') else ''
      try:
        from geo_api import resolve_place,photo_summary
        if not d.get('location_text') and d.get('latitude') is not None:d['location_text']=resolve_place(d['latitude'],d['longitude'],network=False)['place']
        ps=photo_summary(c,d['id']);d['photo_count']=ps['photo_count']+(1 if d.get('photo_path') else 0);d['geo_verified_photos']=ps['geo_verified_photos']+(1 if d.get('latitude') is not None and d.get('photo_path') else 0)
      except Exception:
        pass
      if d.get('verification_id'):attach_certificate(c,d,d['verification_id'])
      out.append(d)
    c.close();return out

@router.get('/v3/offers')
def v3_offers(u=Depends(get_user_dep())):
    c=conn()
    if u['role']=='farmer':
      rows=c.execute('''SELECT o.*,l.crop,l.variety,l.grade,l.seller_id,bu.name buyer_name,bu.business_name buyer_business,bu.buyer_type buyer_type,bu.district buyer_district,bu.state buyer_state,ts.buyer_reliability,ts.instant_payment,ts.zero_cancel_streak
        FROM buyer_offers o JOIN listings l ON l.id=o.listing_id JOIN users bu ON bu.id=o.buyer_user_id LEFT JOIN trust_scores ts ON ts.user_id=o.buyer_user_id WHERE l.seller_id=? ORDER BY o.created_at DESC''',(u['id'],)).fetchall()
    else:
      rows=c.execute('''SELECT o.*,l.crop,l.variety,l.grade,fu.name farmer_name FROM buyer_offers o JOIN listings l ON l.id=o.listing_id JOIN users fu ON fu.id=l.seller_id WHERE o.buyer_user_id=? ORDER BY o.created_at DESC''',(u['id'],)).fetchall()
    c.close();return [rowdict(r) for r in rows]

class OfferAction(BaseModel):
    action:str=Field(pattern='^(ACCEPT|DECLINE|WAIT|NEGOTIATE)$')
    counter_price:Optional[float]=None
    message:str=''
@router.patch('/v3/offers/{offer_id}')
def v3_offer_action(offer_id:int,x:OfferAction,u=Depends(get_user_dep())):
    require_role(u,'farmer');c=conn();o=c.execute('''SELECT o.*,l.seller_id FROM buyer_offers o JOIN listings l ON l.id=o.listing_id WHERE o.id=?''',(offer_id,)).fetchone()
    if not o or o['seller_id']!=u['id']:c.close();raise HTTPException(404,'Offer not found')
    c.execute('UPDATE buyer_offers SET farmer_action=?,status=?,updated_at=? WHERE id=?',(x.action,'NEGOTIATING' if x.action=='NEGOTIATE' else x.action,now_iso(),offer_id))
    if x.action=='NEGOTIATE':
      thread=get_or_create_thread(c,u['id'],o['buyer_user_id'],o['listing_id'],None)
      c.execute('INSERT INTO chat_messages(thread_id,sender_id,message,offer_price,created_at) VALUES(?,?,?,?,?)',(thread,u['id'],x.message or 'Counter offer',x.counter_price,now_iso()))
      c.execute('UPDATE chat_threads SET last_message=?,updated_at=? WHERE id=?',(x.message or f'Counter offer ₹{x.counter_price}',now_iso(),thread))
    c.commit();c.close();return {'status':x.action}

def get_or_create_thread(c,farmer_id,buyer_id,listing_id=None,preorder_id=None):
    r=c.execute('SELECT id FROM chat_threads WHERE farmer_id=? AND buyer_id=? AND coalesce(listing_id,0)=coalesce(?,0) AND coalesce(preorder_id,0)=coalesce(?,0)',(farmer_id,buyer_id,listing_id,preorder_id)).fetchone()
    if r:return r['id']
    cur=c.execute('INSERT INTO chat_threads(farmer_id,buyer_id,listing_id,preorder_id,updated_at) VALUES(?,?,?,?,?)',(farmer_id,buyer_id,listing_id,preorder_id,now_iso()));return cur.lastrowid

class ChatIn(BaseModel):
    other_user_id:int
    message:str=Field(min_length=1,max_length=2000)
    listing_id:Optional[int]=None
    preorder_id:Optional[int]=None
    offer_price:Optional[float]=None
@router.post('/v3/chats')
def v3_chat_send(x:ChatIn,u=Depends(get_user_dep())):
    c=conn();other=c.execute('SELECT * FROM users WHERE id=?',(x.other_user_id,)).fetchone()
    if not other:c.close();raise HTTPException(404,'User not found')
    farmer_id=u['id'] if u['role']=='farmer' else x.other_user_id;buyer_id=u['id'] if u['role']=='buyer' else x.other_user_id
    thread=get_or_create_thread(c,farmer_id,buyer_id,x.listing_id,x.preorder_id)
    c.execute('INSERT INTO chat_messages(thread_id,sender_id,message,offer_price,created_at) VALUES(?,?,?,?,?)',(thread,u['id'],x.message,x.offer_price,now_iso()))
    c.execute('UPDATE chat_threads SET last_message=?,updated_at=? WHERE id=?',(x.message,now_iso(),thread));c.commit();c.close();return {'thread_id':thread}
@router.get('/v3/chats')
def v3_chats(u=Depends(get_user_dep())):
    c=conn();rows=c.execute('''SELECT t.*,f.name farmer_name,b.name buyer_name,(SELECT count(*) FROM chat_messages m WHERE m.thread_id=t.id) message_count FROM chat_threads t JOIN users f ON f.id=t.farmer_id JOIN users b ON b.id=t.buyer_id WHERE t.farmer_id=? OR t.buyer_id=? ORDER BY t.updated_at DESC''',(u['id'],u['id'])).fetchall();c.close();return [rowdict(r) for r in rows]
@router.get('/v3/chats/{thread_id}')
def v3_chat_messages(thread_id:int,u=Depends(get_user_dep())):
    c=conn();t=c.execute('SELECT * FROM chat_threads WHERE id=?',(thread_id,)).fetchone()
    if not t or u['id'] not in (t['farmer_id'],t['buyer_id']):c.close();raise HTTPException(404,'Chat not found')
    rows=c.execute('''SELECT m.*,us.name sender_name FROM chat_messages m JOIN users us ON us.id=m.sender_id WHERE m.thread_id=? ORDER BY m.created_at''',(thread_id,)).fetchall();c.close();return [rowdict(r) for r in rows]

@router.get('/v3/network')
def v3_network(role:str,state:str='ALL',u=Depends(get_user_dep())):
    if role not in ('farmer','buyer'):raise HTTPException(400,'role must be farmer or buyer')
    c=conn();sql='SELECT * FROM network_profiles WHERE role=?';args=[role]
    if state!='ALL':sql+=' AND state=?';args.append(state)
    rows=c.execute(sql+' ORDER BY verified DESC,rating DESC',args).fetchall();c.close();return [rowdict(r) for r in rows]

@router.get('/v3/transports')
def v3_transports(u=Depends(get_user_dep())):
    c=conn();rows=c.execute('SELECT * FROM transport_bookings WHERE user_id=? ORDER BY created_at DESC',(u['id'],)).fetchall();c.close();return [rowdict(r) for r in rows]

class TransportRequest(BaseModel):
    transporter_id:Optional[int]=None;order_id:Optional[int]=None;listing_id:Optional[int]=None;crop:str='';pickup:str;dropoff:str;distance_km:float=0;quoted_cost:float=0;shared:bool=False
@router.post('/v3/transports')
def v3_transport_create(x:TransportRequest,u=Depends(get_user_dep())):
    c=conn();cur=c.execute('''INSERT INTO transport_bookings(user_id,transporter_id,order_id,listing_id,crop,pickup,dropoff,distance_km,quoted_cost,status,shared,created_at) VALUES(?,?,?,?,?,?,?,?,?,'REQUESTED',?,?)''',(u['id'],x.transporter_id,x.order_id,x.listing_id,x.crop,x.pickup,x.dropoff,x.distance_km,x.quoted_cost,int(x.shared),now_iso()));c.commit();c.close();return {'id':cur.lastrowid,'status':'REQUESTED'}

@router.get('/v3/reward-catalog')
def v3_reward_catalog(u=Depends(get_user_dep())):
    c=conn();rows=c.execute('SELECT * FROM reward_catalog WHERE role=? AND active=1 ORDER BY points_cost',(u['role'],)).fetchall();c.close();return [rowdict(r) for r in rows]
@router.post('/v3/rewards/{code}/redeem')
def v3_reward_redeem(code:str,u=Depends(get_user_dep())):
    c=conn();r=c.execute('SELECT * FROM reward_catalog WHERE code=? AND role=? AND active=1',(code,u['role'])).fetchone()
    if not r:c.close();raise HTTPException(404,'Reward not found')
    earned=c.execute('SELECT coalesce(sum(points),0) p FROM reward_ledger WHERE user_id=?',(u['id'],)).fetchone()['p'];used=c.execute("SELECT coalesce(sum(points_used),0) p FROM reward_redemptions WHERE user_id=? AND status!='CANCELLED'",(u['id'],)).fetchone()['p']
    if earned-used<r['points_cost']:c.close();raise HTTPException(400,'Not enough GramPoints')
    expires=(datetime.now(timezone.utc)+timedelta(days=r['valid_days'])).isoformat();c.execute('INSERT INTO reward_redemptions(user_id,reward_code,points_used,benefit_rupees,status,expires_at,created_at) VALUES(?,?,?,?,?,?,?)',(u['id'],code,r['points_cost'],r['benefit_rupees'],'ACTIVE',expires,now_iso()));c.commit();c.close();return {'status':'ACTIVE','expires_at':expires,'benefit_rupees':r['benefit_rupees']}
@router.get('/v3/reward-redemptions')
def v3_reward_redemptions(u=Depends(get_user_dep())):
    c=conn();rows=c.execute('SELECT rr.*,rc.title,rc.description FROM reward_redemptions rr JOIN reward_catalog rc ON rc.code=rr.reward_code WHERE rr.user_id=? ORDER BY rr.created_at DESC',(u['id'],)).fetchall();c.close();return [rowdict(r) for r in rows]

class OrderFeedbackIn(BaseModel):
    target_type:str=Field(pattern='^(FARMER|BUYER|TRANSPORT)$');target_id:Optional[int]=None;rating:int=Field(ge=1,le=5);comments:str=''
@router.post('/v3/orders/{order_id}/feedback')
def v3_order_feedback(order_id:int,x:OrderFeedbackIn,u=Depends(get_user_dep())):
    c=conn();o=c.execute('''SELECT o.*,l.seller_id FROM orders o JOIN listings l ON l.id=o.listing_id WHERE o.id=?''',(order_id,)).fetchone()
    if not o or u['id'] not in (o['buyer_id'],o['seller_id']):c.close();raise HTTPException(404,'Order not found')
    c.execute('INSERT OR REPLACE INTO order_feedback(order_id,from_user_id,target_type,target_id,rating,comments,created_at) VALUES(?,?,?,?,?,?,?)',(order_id,u['id'],x.target_type,x.target_id,x.rating,x.comments,now_iso()));c.commit();c.close();return {'status':'RECORDED'}

@router.get('/v3/dashboard')
def v3_dashboard(u=Depends(get_user_dep())):
    c=conn();k=kyc_status(c,u['id']);points=c.execute('SELECT coalesce(sum(points),0) p FROM reward_ledger WHERE user_id=?',(u['id'],)).fetchone()['p']
    if u['role']=='farmer':
      today=c.execute("SELECT coalesce(sum(o.total),0) s FROM orders o JOIN listings l ON l.id=o.listing_id WHERE l.seller_id=? AND date(o.created_at)=date('now')",(u['id'],)).fetchone()['s']
      total=c.execute('SELECT coalesce(sum(o.total),0) s FROM orders o JOIN listings l ON l.id=o.listing_id WHERE l.seller_id=?',(u['id'],)).fetchone()['s']
      offers=c.execute('''SELECT count(*) n FROM buyer_offers bo JOIN listings l ON l.id=bo.listing_id WHERE l.seller_id=? AND bo.status IN ('OPEN','NEGOTIATING')''',(u['id'],)).fetchone()['n']
      harvests=c.execute("SELECT count(*) n FROM harvests WHERE farmer_id=? AND status='OPEN'",(u['id'],)).fetchone()['n']
      recommendation='Onion demand is strengthening around Tamil Nadu. Run a 1/3/7-day forecast before committing today; compare Coimbatore and Dindigul after transport cost.'
      out={'today_income':today,'total_income':total,'open_offers':offers,'open_harvests':harvests,'reward_points':points,'kyc':k,'recommendation':recommendation}
    elif u['role']=='buyer':
      orders_n=c.execute('SELECT count(*) n FROM orders WHERE buyer_id=?',(u['id'],)).fetchone()['n'];spend=c.execute('SELECT coalesce(sum(total),0) s FROM orders WHERE buyer_id=?',(u['id'],)).fetchone()['s'];pre=c.execute('SELECT count(*) n FROM preorder_requests WHERE buyer_id=?',(u['id'],)).fetchone()['n']
      out={'district':u['district'],'state':u['state'] or 'Tamil Nadu','orders':orders_n,'spend':spend,'preorders':pre,'reward_points':points,'kyc':k,'recommendation':'Verified tomato harvests are available around Coimbatore. Shared logistics can reduce delivery cost on compatible routes.'}
    else:
      users=c.execute('SELECT role,count(*) n FROM users GROUP BY role').fetchall();ud={r['role']:r['n'] for r in users};revenue=c.execute("SELECT coalesce(sum(confirmed_amount_paise),0)/100.0 s FROM payments_v2 WHERE status='SUCCESS'").fetchone()['s'];g=c.execute("SELECT count(*) n FROM grievances_v2 WHERE status NOT IN ('RESOLVED','CLOSED')").fetchone()['n'];pk=c.execute("SELECT count(*) n FROM kyc_profiles WHERE status='PENDING'").fetchone()['n'];out={'revenue':revenue,'farmers':ud.get('farmer',0),'buyers':ud.get('buyer',0),'open_grievances':g,'pending_kyc':pk,'reward_points':0}
    c.close();return out

@router.get('/v3/admin/users')
def v3_admin_users(u=Depends(get_user_dep())):
    require_role(u,'admin');c=conn();rows=c.execute('''SELECT us.id,us.name,us.email,us.role,us.district,us.state,us.phone,k.id kyc_id,k.status kyc_status,k.masked_document,k.live_check,(SELECT action FROM user_actions ua WHERE ua.user_id=us.id AND ua.active=1 ORDER BY ua.id DESC LIMIT 1) account_action FROM users us LEFT JOIN kyc_profiles k ON k.user_id=us.id ORDER BY us.role,us.name''').fetchall();c.close();return [rowdict(r) for r in rows]
class AdminActionIn(BaseModel): action:str=Field(pattern='^(BLOCK|UNBLOCK|TERMINATE|WARN)$');reason:str=Field(default='',max_length=500)
@router.post('/v3/admin/users/{user_id}/action')
def v3_admin_action(user_id:int,x:AdminActionIn,u=Depends(get_user_dep())):
    require_role(u,'admin');c=conn()
    if x.action=='UNBLOCK':c.execute("UPDATE user_actions SET active=0,resolved_at=? WHERE user_id=? AND action='BLOCK' AND active=1",(now_iso(),user_id))
    else:c.execute('INSERT INTO user_actions(user_id,action,reason,active,admin_id,created_at) VALUES(?,?,?,?,?,?)',(user_id,x.action,x.reason,1,u['id'],now_iso()))
    c.commit();c.close();return {'status':x.action}

@router.get('/v3/admin/state-analytics')
def v3_admin_state_analytics(state:str='Tamil Nadu',u=Depends(get_user_dep())):
    require_role(u,'admin');c=conn();markets=c.execute('SELECT count(*) n FROM markets WHERE state=?',(state,)).fetchone()['n'];listings=c.execute("SELECT count(*) n FROM listings WHERE state=?",(state,)).fetchone()['n'];harvests=c.execute('SELECT count(*) n FROM harvests WHERE state=?',(state,)).fetchone()['n'];network=c.execute('SELECT role,count(*) n FROM network_profiles WHERE state=? GROUP BY role',(state,)).fetchall();n={r['role']:r['n'] for r in network};crops=[rowdict(r) for r in c.execute('''SELECT crop,count(*) n,round(avg(ask_price),0) avg_price FROM listings WHERE state=? GROUP BY crop ORDER BY n DESC LIMIT 8''',(state,)).fetchall()];c.close();return {'state':state,'markets':markets,'listings':listings,'harvests':harvests,'farmers':n.get('farmer',0),'buyers':n.get('buyer',0),'crops':crops}

# initialize v3 on import
init_v3_schema()

# ============================================================
# Group selling (fpo_groups) + shared transport groups
# ============================================================

def init_groups_v2_schema():
    c = conn()
    alters = {
        'fpo_groups': [
            ('area', "TEXT NOT NULL DEFAULT ''"),
            ('target_quantity_qtl', "REAL NOT NULL DEFAULT 0"),
            ('expected_price', "REAL NOT NULL DEFAULT 0"),
            ('expected_harvest_date', "TEXT NOT NULL DEFAULT ''"),
            ('description', "TEXT NOT NULL DEFAULT ''"),
            ('shared_transport', "INTEGER NOT NULL DEFAULT 0"),
            ('max_members', "INTEGER NOT NULL DEFAULT 20"),
            ('join_code', "TEXT NOT NULL DEFAULT ''"),
        ],
        'fpo_group_members': [
            ('farmer_name', "TEXT NOT NULL DEFAULT ''"),
            ('farmer_district', "TEXT NOT NULL DEFAULT ''"),
        ],
    }
    for table, cols in alters.items():
        existing = {r['name'] for r in c.execute(f'PRAGMA table_info({table})').fetchall()}
        for name, spec in cols:
            if name not in existing:
                c.execute(f'ALTER TABLE {table} ADD COLUMN {name} {spec}')

    c.executescript("""
        CREATE TABLE IF NOT EXISTS group_join_requests(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          group_id INTEGER NOT NULL,
          farmer_id INTEGER NOT NULL,
          farmer_name TEXT NOT NULL DEFAULT '',
          district TEXT NOT NULL DEFAULT '',
          quantity_qtl REAL NOT NULL DEFAULT 0,
          message TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT 'PENDING',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS transport_groups(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          route_from TEXT NOT NULL,
          route_to TEXT NOT NULL,
          distance_km REAL NOT NULL DEFAULT 0,
          vehicle_type TEXT NOT NULL DEFAULT 'Mini Truck',
          capacity_qtl REAL NOT NULL DEFAULT 0,
          crop TEXT NOT NULL DEFAULT '',
          cost_per_qtl REAL NOT NULL DEFAULT 0,
          owner_id INTEGER NOT NULL,
          state TEXT NOT NULL DEFAULT 'Tamil Nadu',
          district TEXT NOT NULL DEFAULT '',
          departure_date TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT 'ACTIVE',
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS transport_group_members(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          group_id INTEGER NOT NULL,
          farmer_id INTEGER NOT NULL DEFAULT 0,
          farmer_name TEXT NOT NULL DEFAULT '',
          farmer_district TEXT NOT NULL DEFAULT '',
          crop TEXT NOT NULL DEFAULT '',
          quantity_qtl REAL NOT NULL DEFAULT 0,
          joined_at TEXT NOT NULL,
          UNIQUE(group_id, farmer_id)
        );
    """)
    c.commit(); c.close()


def seed_groups_v2_demo():
    """Seed a couple of realistic, already-running groups so the pages are never empty."""
    c = conn()

    if c.execute("SELECT count(*) n FROM transport_groups").fetchone()['n'] == 0:
        routes = [
            ('Vandalur', 'Tambaram', 9.5, 'Tata 407 Mini Lorry', 60, 'Tomato', 45, 'Chengalpattu', '2026-09-24'),
            ('Oddanchatram', 'Dindigul', 18, 'Ashok Leyland Truck', 120, 'Onion', 35, 'Dindigul', '2026-09-25'),
            ('Pollachi', 'Coimbatore', 40, 'Eicher Mini Truck', 80, 'Banana', 40, 'Coimbatore', '2026-09-26'),
        ]
        for route_from, route_to, km, vehicle, cap, crop, cost, district, dep in routes:
            cur = c.execute(
                """INSERT INTO transport_groups(route_from,route_to,distance_km,vehicle_type,capacity_qtl,
                        crop,cost_per_qtl,owner_id,state,district,departure_date,status,created_at)
                   VALUES(?,?,?,?,?,?,?,1,'Tamil Nadu',?,?,'ACTIVE',?)""",
                (route_from, route_to, km, vehicle, cap, crop, cost, district, dep, now_iso())
            )
            gid = cur.lastrowid
            for seat, (name, district2, qty) in enumerate([
                ('Ramesh Kumar', district, cap * 0.28),
                ('Selvi Murugan', district, cap * 0.2),
                ('Karthik Raja', district, cap * 0.15),
            ], start=1):
                c.execute(
                    "INSERT INTO transport_group_members(group_id,farmer_id,farmer_name,farmer_district,crop,quantity_qtl,joined_at) VALUES(?,?,?,?,?,?,?)",
                    (gid, -seat, name, district2, crop, round(qty, 1), now_iso())
                )

    if c.execute("SELECT count(*) n FROM fpo_groups").fetchone()['n'] == 0:
        groups = [
            ('Coimbatore Tomato Farmers', 'Coimbatore', 'Tomato', 100, 2400, '2026-10-02',
             'Farmers combining Grade A tomato harvest for bulk buyers near Coimbatore APMC.'),
            ('Dindigul Onion Collective', 'Dindigul', 'Onion', 150, 2150, '2026-10-05',
             'Small onion growers pooling harvest to negotiate a better mandi rate together.'),
        ]
        for name, district, crop, target, price, date, desc in groups:
            cur = c.execute(
                """INSERT INTO fpo_groups(name,state,district,crop,owner_id,status,created_at,
                        area,target_quantity_qtl,expected_price,expected_harvest_date,description,
                        shared_transport,max_members,join_code)
                   VALUES(?,'Tamil Nadu',?,?,1,'ACTIVE',?,?,?,?,?,?,1,20,?)""",
                (name, district, crop, now_iso(), district, target, price, date, desc, gen_group_code(district))
            )
            gid = cur.lastrowid
            for seat, (fname, qty) in enumerate([('Ramesh Kumar', target * 0.18), ('Lakshmi Devi', target * 0.12), ('Suresh Babu', target * 0.1)], start=1):
                c.execute(
                    "INSERT INTO fpo_group_members(group_id,farmer_id,farmer_name,farmer_district,quantity_qtl,joined_at) VALUES(?,?,?,?,?,?)",
                    (gid, -seat, fname, district, round(qty, 1), now_iso())
                )

    c.commit(); c.close()


init_groups_v2_schema()
seed_groups_v2_demo()


class BuyerDemandPreorderIn(BaseModel):

    crop: str = Field(
        min_length=2,
        max_length=60
    )

    variety: str = Field(
        default="Any",
        max_length=60
    )

    grade_required: str = Field(
        default="Any",
        max_length=20
    )

    quantity_qtl: float = Field(
        gt=0,
        le=100000
    )

    offer_price: float = Field(
        gt=0
    )

    required_by_date: str

    delivery_district: str = Field(
        default="",
        max_length=80
    )

    delivery_state: str = Field(
        default="Tamil Nadu",
        max_length=80
    )

    delivery_mode: str = Field(
        default="BUYER_PICKUP",
        pattern="^(BUYER_PICKUP|FARMER_TRANSPORT|FLEXIBLE)$"
    )

    token_offer: float = Field(
        default=0,
        ge=0
    )

    special_requirements: str = Field(
        default="",
        max_length=1500
    )

class FarmerBuyerDemandAction(BaseModel):

    action: str = Field(
        pattern="^(ACCEPT|DECLINE|NEGOTIATE|INTERESTED)$"
    )

    harvest_id: Optional[int] = None

    quantity_qtl: Optional[float] = Field(
        default=None,
        gt=0
    )

    counter_price: Optional[float] = Field(
        default=None,
        gt=0
    )

    message: str = Field(
        default="",
        max_length=1000
    )

@router.post('/v3/buyer-preorders')

def v3_create_buyer_preorder(
    x: BuyerDemandPreorderIn,
    u=Depends(get_user_dep())
):

    require_role(
        u,
        'buyer'
    )

    c = conn()

    ensure_verified(
        c,
        u,
        'publish a pre-order requirement'
    )


    # Validate required date.
    try:

        required_date = datetime.fromisoformat(
            x.required_by_date
        ).date()

    except Exception:

        c.close()

        raise HTTPException(
            400,
            'Required-by date must be a valid YYYY-MM-DD date'
        )


    if required_date < datetime.now().date():

        c.close()

        raise HTTPException(
            400,
            'Required-by date cannot be in the past'
        )


    district = (
        x.delivery_district
        or u.get('district')
        or ''
    )


    state = (
        x.delivery_state
        or u.get('state')
        or DEFAULT_STATE
    )


    cur = c.execute(
        '''
        INSERT INTO buyer_preorder_demands(
            buyer_id,
            crop,
            variety,
            grade_required,
            quantity_qtl,
            remaining_quantity_qtl,
            offer_price,
            required_by_date,
            delivery_district,
            delivery_state,
            delivery_mode,
            token_offer,
            special_requirements,
            status,
            created_at,
            updated_at
        )
        VALUES(
            ?,?,?,?,?,?,?,?,?,?,?,?,?, 'OPEN', ?,?
        )
        ''',
        (
            u['id'],
            x.crop.strip(),
            x.variety.strip() or 'Any',
            x.grade_required.strip() or 'Any',
            x.quantity_qtl,
            x.quantity_qtl,
            x.offer_price,
            x.required_by_date,
            district,
            state,
            x.delivery_mode,
            x.token_offer,
            x.special_requirements.strip(),
            now_iso(),
            now_iso()
        )
    )


    demand_id = cur.lastrowid


    # Notify farmers in the same state.
    farmers = c.execute(
        '''
        SELECT id
        FROM users
        WHERE role='farmer'
          AND coalesce(NULLIF(state,''),?)=?
        ''',
        (
            DEFAULT_STATE,
            state
        )
    ).fetchall()


    for farmer in farmers:

        c.execute(
            '''
            INSERT INTO notifications(
                user_id,
                title,
                message,
                severity,
                created_at
            )
            VALUES(
                ?,?,?, 'info', datetime('now')
            )
            ''',
            (
                farmer['id'],
                'New buyer pre-order requirement',
                (
                    f'{u["name"]} needs '
                    f'{x.quantity_qtl:g} qtl of {x.crop} '
                    f'at ₹{x.offer_price:.0f}/qtl '
                    f'by {x.required_by_date}.'
                )
            )
        )


    c.commit()

    c.close()


    audit_event(
        u['id'],
        'buyer_preorder_created',
        f'demand={demand_id};crop={x.crop};quantity={x.quantity_qtl}'
    )


    return {
        'id': demand_id,
        'status': 'OPEN',
        'remaining_quantity_qtl': x.quantity_qtl,
        'message': 'Pre-order requirement published to matching farmers.'
    }
@router.get('/v3/buyer-preorders/mine')
def v3_my_buyer_preorders(
    u=Depends(get_user_dep())
):

    require_role(
        u,
        'buyer'
    )


    c = conn()


    rows = c.execute(
        '''
        SELECT
            d.*,

            (
                SELECT count(*)
                FROM buyer_preorder_responses r
                WHERE r.demand_id=d.id
                  AND r.action!='DECLINE'
            ) AS farmer_responses,

            (
                SELECT count(*)
                FROM buyer_preorder_responses r
                WHERE r.demand_id=d.id
                  AND r.action='ACCEPT'
            ) AS accepted_farmers

        FROM buyer_preorder_demands d

        WHERE d.buyer_id=?

        ORDER BY d.created_at DESC
        ''',
        (
            u['id'],
        )
    ).fetchall()


    out = []


    for row in rows:

        item = rowdict(
            row
        )


        responses = c.execute(
            '''
            SELECT
                r.*,
                uf.name farmer_name,
                uf.district farmer_district,
                uf.state farmer_state,
                h.crop harvest_crop,
                h.variety harvest_variety,
                h.grade_expected,
                h.expected_harvest_date,
                h.available_quantity_qtl

            FROM buyer_preorder_responses r

            JOIN users uf
              ON uf.id=r.farmer_id

            LEFT JOIN harvests h
              ON h.id=r.harvest_id

            WHERE r.demand_id=?

            ORDER BY r.updated_at DESC
            ''',
            (
                row['id'],
            )
        ).fetchall()


        item['responses'] = [
            rowdict(r)
            for r in responses
        ]


        out.append(
            item
        )


    c.close()


    return out

@router.get('/v3/buyer-preorders/available')
def v3_available_buyer_preorders(
    u=Depends(get_user_dep())
):

    require_role(
        u,
        'farmer'
    )


    c = conn()


    state = (
        u.get('state')
        or DEFAULT_STATE
    )


    rows = c.execute(
        '''
        SELECT
            d.*,

            ub.name buyer_name,
            ub.district buyer_home_district,
            ub.state buyer_home_state,

            ts.buyer_reliability,
            ts.instant_payment,
            ts.zero_cancel_streak,

            br.id response_id,
            br.action farmer_response,
            br.quantity_qtl farmer_quantity_qtl,
            br.farmer_price,
            br.message farmer_message,
            br.linked_preorder_id

        FROM buyer_preorder_demands d

        JOIN users ub
          ON ub.id=d.buyer_id

        LEFT JOIN trust_scores ts
          ON ts.user_id=d.buyer_id

        LEFT JOIN buyer_preorder_responses br
          ON br.demand_id=d.id
         AND br.farmer_id=?

        WHERE d.delivery_state=?

          AND d.status IN(
              'OPEN',
              'PARTIALLY_FILLED'
          )

          AND d.remaining_quantity_qtl > 0

        ORDER BY
            d.required_by_date,
            d.created_at DESC
        ''',
        (
            u['id'],
            state
        )
    ).fetchall()


    out = []


    for row in rows:

        item = rowdict(
            row
        )


        prediction = approximate_market_prediction(
            c,
            row['crop'],
            row['delivery_state']
        )


        item['predicted_1d'] = prediction[1]

        item['predicted_3d'] = prediction[3]

        item['predicted_7d'] = prediction[7]

        item['forecast_confidence'] = prediction[
            'confidence'
        ]


        reliability = buyer_reliability(
            c,
            row['buyer_id']
        )


        item[
            'buyer_reliability_score'
        ] = reliability


        out.append(
            item
        )


    c.close()


    return out

@router.patch(
    '/v3/buyer-preorders/{demand_id}/farmer-response'
)
def v3_farmer_respond_buyer_preorder(
    demand_id: int,
    x: FarmerBuyerDemandAction,
    u=Depends(get_user_dep())
):

    require_role(
        u,
        'farmer'
    )


    c = conn()


    ensure_verified(
        c,
        u,
        'respond to buyer pre-orders'
    )


    demand = c.execute(
        '''
        SELECT *
        FROM buyer_preorder_demands
        WHERE id=?
        ''',
        (
            demand_id,
        )
    ).fetchone()


    if not demand:

        c.close()

        raise HTTPException(
            404,
            'Buyer pre-order requirement not found'
        )


    if demand['status'] not in (
        'OPEN',
        'PARTIALLY_FILLED'
    ):

        c.close()

        raise HTTPException(
            409,
            'This buyer requirement is no longer open'
        )


    if float(
        demand['remaining_quantity_qtl']
        or 0
    ) <= 0:

        c.close()

        raise HTTPException(
            409,
            'This requirement has already been fulfilled'
        )


    # ============================================
    # DECLINE
    # ============================================

    if x.action == 'DECLINE':

        c.execute(
            '''
            INSERT INTO buyer_preorder_responses(
                demand_id,
                farmer_id,
                quantity_qtl,
                action,
                message,
                created_at,
                updated_at
            )
            VALUES(
                ?,?,0,'DECLINE',?,?,?
            )

            ON CONFLICT(demand_id,farmer_id)

            DO UPDATE SET
                action='DECLINE',
                message=excluded.message,
                updated_at=excluded.updated_at
            ''',
            (
                demand_id,
                u['id'],
                x.message or
                'Farmer is unable to fulfil this requirement.',
                now_iso(),
                now_iso()
            )
        )


        c.execute(
            '''
            INSERT INTO notifications(
                user_id,
                title,
                message,
                severity,
                created_at
            )
            VALUES(
                ?,?,?, 'info', datetime('now')
            )
            ''',
            (
                demand['buyer_id'],
                'Farmer response to your pre-order',
                (
                    f'A farmer declined your '
                    f'{demand["crop"]} requirement. '
                    f'Your request remains open for other farmers.'
                )
            )
        )


        c.commit()

        c.close()


        return {
            'status': 'DECLINED',
            'demand_status': demand['status']
        }


    # ============================================
    # INTERESTED / NEGOTIATE
    # ============================================

    if x.action in (
        'INTERESTED',
        'NEGOTIATE'
    ):

        quantity = min(
            float(
                x.quantity_qtl
                or demand['remaining_quantity_qtl']
            ),
            float(
                demand['remaining_quantity_qtl']
            )
        )


        farmer_price = (
            x.counter_price
            if x.counter_price
            else demand['offer_price']
        )


        c.execute(
            '''
            INSERT INTO buyer_preorder_responses(
                demand_id,
                farmer_id,
                harvest_id,
                quantity_qtl,
                farmer_price,
                action,
                message,
                created_at,
                updated_at
            )

            VALUES(
                ?,?,?,?,?,?,?,?,?
            )

            ON CONFLICT(demand_id,farmer_id)

            DO UPDATE SET
                harvest_id=excluded.harvest_id,
                quantity_qtl=excluded.quantity_qtl,
                farmer_price=excluded.farmer_price,
                action=excluded.action,
                message=excluded.message,
                updated_at=excluded.updated_at
            ''',
            (
                demand_id,
                u['id'],
                x.harvest_id,
                quantity,
                farmer_price,
                x.action,
                x.message,
                now_iso(),
                now_iso()
            )
        )


        c.execute(
            '''
            INSERT INTO notifications(
                user_id,
                title,
                message,
                severity,
                created_at
            )
            VALUES(
                ?,?,?, 'info', datetime('now')
            )
            ''',
            (
                demand['buyer_id'],
                (
                    'Farmer wants to negotiate'
                    if x.action == 'NEGOTIATE'
                    else
                    'Farmer interested in your pre-order'
                ),
                (
                    f'A farmer responded to your '
                    f'{demand["crop"]} requirement '
                    f'for {quantity:g} qtl '
                    f'at ₹{float(farmer_price):.0f}/qtl.'
                )
            )
        )


        c.commit()

        c.close()


        return {
            'status': x.action,
            'quantity_qtl': quantity,
            'farmer_price': farmer_price
        }


    # ============================================
    # ACCEPT
    # Farmer must select an actual harvest.
    # ============================================

    if not x.harvest_id:

        c.close()

        raise HTTPException(
            400,
            'Select one of your published harvests before accepting this pre-order'
        )


    harvest = c.execute(
        '''
        SELECT *
        FROM harvests
        WHERE id=?
          AND farmer_id=?
          AND status='OPEN'
        ''',
        (
            x.harvest_id,
            u['id']
        )
    ).fetchone()


    if not harvest:

        c.close()

        raise HTTPException(
            404,
            'Selected farmer harvest was not found'
        )


    if (
        str(harvest['crop']).strip().lower()
        !=
        str(demand['crop']).strip().lower()
    ):

        c.close()

        raise HTTPException(
            400,
            'Selected harvest crop does not match the buyer requirement'
        )


    quantity = min(
        float(
            x.quantity_qtl
            or demand['remaining_quantity_qtl']
        ),
        float(
            demand['remaining_quantity_qtl']
        ),
        float(
            harvest['available_quantity_qtl']
        )
    )


    if quantity <= 0:

        c.close()

        raise HTTPException(
            409,
            'No harvest quantity is available'
        )


    final_price = float(
        x.counter_price
        or demand['offer_price']
    )


    advice = preorder_advice(
        c,
        harvest,
        demand['buyer_id'],
        quantity,
        final_price
    )


    # Buyer-offered token can override calculated token
    # only when it is greater than zero.
    deposit_amount = (
        float(demand['token_offer'])
        if float(demand['token_offer'] or 0) > 0
        else float(advice['deposit_amount'])
    )


    cur = c.execute(
        '''
        INSERT INTO preorder_requests(
            buyer_id,
            harvest_id,
            quantity_qtl,
            offer_price,
            recommended_action,
            fair_low,
            fair_high,
            predicted_1d,
            predicted_3d,
            predicted_7d,
            transport_cost,
            market_charges,
            net_farmer_value,
            deposit_percent,
            deposit_amount,
            status,
            created_at,
            updated_at,
            token_payment_status,
            farmer_decision,
            buyer_decision,
            buyer_demand_id,
            special_requirements,
            delivery_location,
            delivery_mode
        )

        VALUES(
            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
            'AWAITING_TOKEN',
            ?,?,
            'UNPAID',
            'ACCEPT',
            'PENDING',
            ?,?,?,?
        )
        ''',
        (
            demand['buyer_id'],
            harvest['id'],
            quantity,
            final_price,

            advice['action'],
            advice['fair_low'],
            advice['fair_high'],
            advice['predicted_1d'],
            advice['predicted_3d'],
            advice['predicted_7d'],
            advice['transport_cost'],
            advice['market_charges'],
            advice['net_farmer_value'],
            advice['deposit_percent'],
            deposit_amount,

            now_iso(),
            now_iso(),

            demand_id,

            demand['special_requirements'],

            (
                f'{demand["delivery_district"]}, '
                f'{demand["delivery_state"]}'
            ),

            demand['delivery_mode']
        )
    )


    preorder_id = cur.lastrowid


    c.execute(
        '''
        INSERT INTO buyer_preorder_responses(
            demand_id,
            farmer_id,
            harvest_id,
            quantity_qtl,
            farmer_price,
            action,
            message,
            linked_preorder_id,
            created_at,
            updated_at
        )

        VALUES(
            ?,?,?,?,?, 'ACCEPT', ?,?,?,?
        )

        ON CONFLICT(demand_id,farmer_id)

        DO UPDATE SET
            harvest_id=excluded.harvest_id,
            quantity_qtl=excluded.quantity_qtl,
            farmer_price=excluded.farmer_price,
            action='ACCEPT',
            message=excluded.message,
            linked_preorder_id=excluded.linked_preorder_id,
            updated_at=excluded.updated_at
        ''',
        (
            demand_id,
            u['id'],
            harvest['id'],
            quantity,
            final_price,
            x.message or
            'Farmer accepted this buyer requirement.',
            preorder_id,
            now_iso(),
            now_iso()
        )
    )


    c.execute(
        '''
        INSERT INTO notifications(
            user_id,
            title,
            message,
            severity,
            created_at
        )

        VALUES(
            ?,?,?, 'success', datetime('now')
        )
        ''',
        (
            demand['buyer_id'],
            'Farmer accepted your pre-order',
            (
                f'{u["name"]} can supply '
                f'{quantity:g} qtl of {demand["crop"]} '
                f'at ₹{final_price:.0f}/qtl. '
                f'Pay the booking token ₹{deposit_amount:.0f} '
                f'to secure this allocation.'
            )
        )
    )


    c.commit()

    c.close()


    audit_event(
        u['id'],
        'buyer_preorder_farmer_accepted',
        (
            f'demand={demand_id};'
            f'preorder={preorder_id};'
            f'quantity={quantity}'
        )
    )


    return {
        'status': 'AWAITING_TOKEN',
        'preorder_id': preorder_id,
        'demand_id': demand_id,
        'quantity_qtl': quantity,
        'offer_price': final_price,
        'token_required': deposit_amount,
        'message': 'Buyer must pay the token before this quantity is reserved.'
    }


class BuyerOfferIn(BaseModel):
    listing_id:int;offer_price:float=Field(gt=0);quantity_qtl:float=Field(gt=0);pitch:str=Field(default='',max_length=1000)
@router.post('/v3/offers')
def v3_offer_create(x:BuyerOfferIn,u=Depends(get_user_dep())):
    require_role(u,'buyer');c=conn();ensure_verified(c,u,'send buyer offers')
    l=c.execute("SELECT * FROM listings WHERE id=? AND status='OPEN'",(x.listing_id,)).fetchone()
    if not l:c.close();raise HTTPException(404,'Harvest listing unavailable')
    cur=c.execute("INSERT INTO buyer_offers(buyer_user_id,listing_id,offer_price,quantity_qtl,pitch,status,farmer_action,created_at,updated_at) VALUES(?,?,?,?,?,'OPEN','PENDING',?,?)",(u['id'],x.listing_id,x.offer_price,x.quantity_qtl,x.pitch,now_iso(),now_iso()))
    c.execute("INSERT INTO notifications(user_id,title,message,severity,created_at) VALUES(?,?,?,'info',datetime('now'))",(l['seller_id'],'New buyer offer',f'Buyer {u["name"]} offered ₹{x.offer_price:.0f}/qtl for {l["crop"]}.'))
    c.commit();c.close();return {'id':cur.lastrowid,'status':'OPEN'}

class FarmerPreorderDecision(BaseModel):
    action:str=Field(pattern='^(ACCEPT|DECLINE|WAIT|NEGOTIATE)$');counter_price:Optional[float]=None
@router.patch('/v3/preorders/{preorder_id}/farmer')
def v3_preorder_farmer(preorder_id:int,x:FarmerPreorderDecision,u=Depends(get_user_dep())):
    require_role(u,'farmer');c=conn();p=c.execute('''SELECT p.*,h.farmer_id,h.crop FROM preorder_requests p JOIN harvests h ON h.id=p.harvest_id WHERE p.id=?''',(preorder_id,)).fetchone()
    if not p or p['farmer_id']!=u['id']:c.close();raise HTTPException(404,'Pre-order not found')
    status={'ACCEPT':'AWAITING_TOKEN','DECLINE':'DECLINED','WAIT':'WAIT','NEGOTIATE':'NEGOTIATING'}[x.action]
    c.execute('UPDATE preorder_requests SET farmer_decision=?,status=?,updated_at=? WHERE id=?',(x.action,status,now_iso(),preorder_id))
    c.execute("INSERT INTO notifications(user_id,title,message,severity,created_at) VALUES(?,?,?,'info',datetime('now'))",(p['buyer_id'],'Pre-order update',f'Farmer response for {p["crop"]}: {status}.'))
    c.commit();c.close();return {'status':status,'token_required':p['deposit_amount']}

@router.post(
    '/v3/preorders/{preorder_id}/activate-after-payment'
)
def v3_preorder_activate(
    preorder_id: int,
    u=Depends(get_user_dep())
):

    require_role(
        u,
        'buyer'
    )


    c = conn()


    p = c.execute(
        '''
        SELECT *
        FROM preorder_requests
        WHERE id=?
          AND buyer_id=?
        ''',
        (
            preorder_id,
            u['id']
        )
    ).fetchone()


    if not p:

        c.close()

        raise HTTPException(
            404,
            'Pre-order not found'
        )


    if p['status'] == 'ACCEPTED':

        c.close()

        return {
            'status': 'ACCEPTED',
            'already_activated': True
        }


    if p['status'] != 'AWAITING_TOKEN':

        c.close()

        raise HTTPException(
            409,
            'This pre-order is not awaiting token payment'
        )


    payment = c.execute(
        '''
        SELECT *
        FROM payments_v2

        WHERE reference_type='PREORDER'
          AND reference_id=?
          AND user_id=?
          AND status='SUCCESS'

        ORDER BY id DESC
        LIMIT 1
        ''',
        (
            preorder_id,
            u['id']
        )
    ).fetchone()


    if not payment:

        c.close()

        raise HTTPException(
            400,
            'Verified token payment is required before pre-order acceptance'
        )


    harvest = c.execute(
        '''
        SELECT *
        FROM harvests
        WHERE id=?
        ''',
        (
            p['harvest_id'],
        )
    ).fetchone()


    if not harvest:

        c.close()

        raise HTTPException(
            404,
            'Linked harvest no longer exists'
        )


    if (
        float(
            harvest['available_quantity_qtl']
        )
        <
        float(
            p['quantity_qtl']
        )
    ):

        c.close()

        raise HTTPException(
            409,
            'The farmer no longer has enough available quantity'
        )


    # Reserve crop ONLY after successful token payment.

    c.execute(
        '''
        UPDATE harvests

        SET available_quantity_qtl =
            available_quantity_qtl - ?

        WHERE id=?
        ''',
        (
            p['quantity_qtl'],
            p['harvest_id']
        )
    )


    c.execute(
        '''
        UPDATE preorder_requests

        SET
            status='ACCEPTED',
            buyer_decision='TOKEN_PAID',
            token_payment_status='PAID',
            updated_at=?

        WHERE id=?
        ''',
        (
            now_iso(),
            preorder_id
        )
    )


    # ==========================================
    # UPDATE BUYER OPEN DEMAND
    # ==========================================

    demand_id = (
        p['buyer_demand_id']
        if 'buyer_demand_id' in p.keys()
        else None
    )


    if demand_id:

        demand = c.execute(
            '''
            SELECT *
            FROM buyer_preorder_demands
            WHERE id=?
            ''',
            (
                demand_id,
            )
        ).fetchone()


        if demand:

            new_remaining = max(
                0,
                float(
                    demand['remaining_quantity_qtl']
                )
                -
                float(
                    p['quantity_qtl']
                )
            )


            if new_remaining <= 0:

                demand_status = 'FULFILLED'

            else:

                demand_status = 'PARTIALLY_FILLED'


            c.execute(
                '''
                UPDATE buyer_preorder_demands

                SET
                    remaining_quantity_qtl=?,
                    status=?,
                    updated_at=?

                WHERE id=?
                ''',
                (
                    new_remaining,
                    demand_status,
                    now_iso(),
                    demand_id
                )
            )


    c.execute(
        '''
        INSERT INTO notifications(
            user_id,
            title,
            message,
            severity,
            created_at
        )

        VALUES(
            ?,?,?, 'success', datetime('now')
        )
        ''',
        (
            harvest['farmer_id'],
            'Pre-order secured',
            (
                f'Token payment received. '
                f'Pre-order #{preorder_id} is now reserved.'
            )
        )
    )


    c.commit()

    c.close()


    return {
        'status': 'ACCEPTED',
        'preorder_id': preorder_id,
        'reserved_quantity_qtl': p['quantity_qtl'],
        'buyer_demand_id': demand_id
    }

@router.get('/v3/listings/{listing_id}')
def v3_listing_detail(listing_id:int,u=Depends(get_user_dep())):
    c=conn();r=c.execute('''SELECT l.*,us.name farmer_name,us.phone farmer_phone,k.status kyc_status,k.live_check,q.certificate_number
      FROM listings l JOIN users us ON us.id=l.seller_id LEFT JOIN kyc_profiles k ON k.user_id=us.id LEFT JOIN quality_certificates q ON q.certificate_path=l.quality_certificate WHERE l.id=?''',(listing_id,)).fetchone()
    if not r:c.close();raise HTTPException(404,'Listing not found')
    d=rowdict(r); d['gram_verified']=d.get('kyc_status')=='VERIFIED' and bool(d.get('live_check'));d['certificate_url']=''
    # find verification by image path so buyer can open protected certificate.
    qv=c.execute('SELECT id FROM quality_verifications WHERE image_path=? ORDER BY id DESC LIMIT 1',(d.get('quality_image') or d.get('image_url'),)).fetchone()
    if qv:d['certificate_url']=f"/api/produce/certificate/{qv['id']}"
    vid=verification_id_for_listing(c,d) or (qv['id'] if qv else None)
    if vid:attach_certificate(c,d,vid)
    c.close();return d

@router.get('/v3/order-tracking/{order_id}')
def v3_order_tracking(order_id:int,u=Depends(get_user_dep())):
    c=conn();o=c.execute('''SELECT o.*,l.seller_id FROM orders o JOIN listings l ON l.id=o.listing_id WHERE o.id=?''',(order_id,)).fetchone()
    if not o or u['id'] not in (o['buyer_id'],o['seller_id']) and u['role']!='admin':c.close();raise HTTPException(404,'Order not found')
    rows=c.execute('SELECT * FROM order_tracking WHERE order_id=? ORDER BY id',(order_id,)).fetchall()
    if not rows:
      stages=[('ORDER_PLACED','Order created in GRAM AI','Seller location'),('TOKEN_CONFIRMED','Payment/token verification checkpoint','Secure payment'),('PICKUP_SCHEDULED','Transport pickup scheduled','Farmer pickup point'),('IN_TRANSIT','Track once transporter starts route','GPS logistics'),('DELIVERED','Final delivery confirmation','Buyer destination')]
      for st,note,loc in stages:c.execute('INSERT INTO order_tracking(order_id,status,note,location_text,created_at) VALUES(?,?,?,?,?)',(order_id,st,note,loc,now_iso()))
      c.commit();rows=c.execute('SELECT * FROM order_tracking WHERE order_id=? ORDER BY id',(order_id,)).fetchall()
    c.close();return [rowdict(r) for r in rows]

class BuyerPoolIn(BaseModel):

    name: str = Field(
        min_length=2,
        max_length=100
    )

    crop: str = Field(
        min_length=2,
        max_length=60
    )

    variety: str = Field(
        default="Any",
        max_length=60
    )

    grade_required: str = Field(
        default="Any",
        max_length=20
    )

    district: str = Field(
        min_length=2,
        max_length=80
    )

    target_qtl: float = Field(
        gt=0,
        le=100000
    )

    quantity_qtl: float = Field(
        gt=0,
        le=100000
    )

    target_price: float = Field(
        default=0,
        ge=0
    )

    required_by_date: str = ""

    delivery_location: str = Field(
        default="",
        max_length=200
    )

    transport_preference: str = Field(
        default="FLEXIBLE",
        pattern="^(BUYER_PICKUP|SHARED_LOGISTICS|FARMER_TRANSPORT|FLEXIBLE)$"
    )

    special_requirements: str = Field(
        default="",
        max_length=1500
    )

class BuyerPoolJoinCodeIn(BaseModel):

    join_code: str = Field(
        min_length=4,
        max_length=30
    )

    quantity_qtl: float = Field(
        gt=0,
        le=100000
    )


class BuyerPoolInviteIn(BaseModel):

    buyer_id: int

    quantity_qtl: float = Field(
        default=0,
        ge=0
    )

    message: str = Field(
        default="",
        max_length=1000
    )


class BuyerPoolInviteDecisionIn(BaseModel):

    action: str = Field(
        pattern="^(ACCEPT|DECLINE)$"
    )

    quantity_qtl: Optional[float] = Field(
        default=None,
        gt=0
    )


class LogisticsBidIn(BaseModel):

    transporter_id: int

    pool_id: Optional[int] = None

    crop: str = Field(
        default="",
        max_length=60
    )

    quantity_qtl: float = Field(
        gt=0,
        le=100000
    )

    pickup_location: str = Field(
        min_length=2,
        max_length=200
    )

    delivery_location: str = Field(
        min_length=2,
        max_length=200
    )

    pickup_date: str

    pickup_time: str = Field(
        default="",
        max_length=20
    )

    proposed_bid: float = Field(
        gt=0
    )

    estimated_distance_km: float = Field(
        default=0,
        ge=0
    )

    special_instructions: str = Field(
        default="",
        max_length=1500
    )

@router.post('/v3/buyer-pools')
def v3_buyer_pool_create(
    x: BuyerPoolIn,
    u=Depends(get_user_dep())
):

    require_role(u, 'buyer')

    c = conn()

    ensure_verified(
        c,
        u,
        'create a bulk buyer order'
    )

    if x.quantity_qtl > x.target_qtl:

        c.close()

        raise HTTPException(
            400,
            "Your quantity cannot exceed the bulk target quantity"
        )


    join_code = None

    for _ in range(10):

        candidate = (
            "GB-"
            + secrets.token_hex(3).upper()
        )

        exists = c.execute(
            """
            SELECT id
            FROM buyer_pools
            WHERE join_code=?
            """,
            (candidate,)
        ).fetchone()

        if not exists:

            join_code = candidate
            break


    if not join_code:

        c.close()

        raise HTTPException(
            500,
            "Unable to generate bulk order join code"
        )


    cur = c.execute(
        """
        INSERT INTO buyer_pools(
            owner_id,
            name,
            crop,
            variety,
            grade_required,
            district,
            state,
            target_qtl,
            current_qtl,
            target_price,
            required_by_date,
            delivery_location,
            transport_preference,
            special_requirements,
            join_code,
            status,
            created_at,
            updated_at
        )
        VALUES(
            ?,?,?,?,?,?,
            'Tamil Nadu',
            ?,?,?,?,?,?,?,?,
            ?,
            'OPEN',
            ?,?
        )
        """,
        (
            u['id'],
            x.name,
            x.crop,
            x.variety,
            x.grade_required,
            x.district,
            x.target_qtl,
            x.quantity_qtl,
            x.target_price,
            x.required_by_date,
            x.delivery_location,
            x.transport_preference,
            x.special_requirements,
            join_code,
            now_iso(),
            now_iso()
        )
    )

    pool_id = cur.lastrowid


    c.execute(
        """
        INSERT INTO buyer_pool_members(
            pool_id,
            buyer_id,
            quantity_qtl,
            created_at
        )
        VALUES(?,?,?,?)
        """,
        (
            pool_id,
            u['id'],
            x.quantity_qtl,
            now_iso()
        )
    )


    c.commit()
    c.close()


    audit_event(
        u['id'],
        'buyer_bulk_order_created',
        f'pool={pool_id};join_code={join_code}'
    )


    return {
        "id": pool_id,
        "join_code": join_code,
        "status": "OPEN",
        "current_qtl": x.quantity_qtl,
        "target_qtl": x.target_qtl,
        "remaining_qtl": round(
            x.target_qtl - x.quantity_qtl,
            2
        ),
        "message": "Bulk order created successfully"
    }

@router.get('/v3/buyer-pools')
def v3_buyer_pools(
    u=Depends(get_user_dep())
):

    require_role(u, 'buyer', 'admin')

    c = conn()

    rows = c.execute(
        """
        SELECT
            bp.*,
            us.name owner_name,

            (
                SELECT count(*)
                FROM buyer_pool_members m
                WHERE m.pool_id=bp.id
            ) members

        FROM buyer_pools bp

        JOIN users us
          ON us.id=bp.owner_id

        WHERE bp.state='Tamil Nadu'

        ORDER BY
            CASE
                WHEN bp.owner_id=? THEN 0
                ELSE 1
            END,
            bp.created_at DESC
        """,
        (u['id'],)
    ).fetchall()


    result = []

    for row in rows:

        item = rowdict(row)

        item["remaining_qtl"] = round(
            max(
                0,
                float(item["target_qtl"] or 0)
                -
                float(item["current_qtl"] or 0)
            ),
            2
        )

        item["is_owner"] = (
            item["owner_id"] == u["id"]
        )

        member = c.execute(
            """
            SELECT quantity_qtl
            FROM buyer_pool_members
            WHERE pool_id=?
              AND buyer_id=?
            """,
            (
                item["id"],
                u["id"]
            )
        ).fetchone()

        item["joined"] = bool(member)

        item["my_quantity_qtl"] = (
            float(member["quantity_qtl"])
            if member
            else 0
        )

        result.append(item)


    c.close()

    return result

@router.get('/v3/buyer-pools/{pool_id}')
def v3_buyer_pool_detail(
    pool_id: int,
    u=Depends(get_user_dep())
):

    require_role(u, 'buyer', 'admin')

    c = conn()

    pool = c.execute(
        """
        SELECT
            bp.*,
            us.name owner_name,
            us.district owner_district,
            us.state owner_state
        FROM buyer_pools bp
        JOIN users us
          ON us.id=bp.owner_id
        WHERE bp.id=?
        """,
        (pool_id,)
    ).fetchone()

    if not pool:

        c.close()

        raise HTTPException(
            404,
            "Bulk order not found"
        )


    members = c.execute(
        """
        SELECT
            m.*,
            us.name buyer_name,
            us.district,
            us.state
        FROM buyer_pool_members m
        JOIN users us
          ON us.id=m.buyer_id
        WHERE m.pool_id=?
        ORDER BY m.created_at
        """,
        (pool_id,)
    ).fetchall()


    data = rowdict(pool)

    data["members_detail"] = [
        rowdict(r)
        for r in members
    ]

    data["remaining_qtl"] = round(
        max(
            0,
            float(data["target_qtl"] or 0)
            -
            float(data["current_qtl"] or 0)
        ),
        2
    )


    c.close()

    return data

@router.post('/v3/buyer-pools/join-by-code')
def v3_buyer_pool_join_code(
    x: BuyerPoolJoinCodeIn,
    u=Depends(get_user_dep())
):

    require_role(u, 'buyer')

    c = conn()

    ensure_verified(
        c,
        u,
        'join a bulk buyer order'
    )


    code = x.join_code.strip().upper()


    pool = c.execute(
        """
        SELECT *
        FROM buyer_pools
        WHERE upper(join_code)=?
          AND status IN ('OPEN','PARTIALLY_FILLED')
        """,
        (code,)
    ).fetchone()


    if not pool:

        c.close()

        raise HTTPException(
            404,
            "Bulk order join code is invalid or no longer open"
        )


    remaining = max(
        0,
        float(pool["target_qtl"])
        -
        float(pool["current_qtl"])
    )


    if remaining <= 0:

        c.close()

        raise HTTPException(
            409,
            "This bulk order is already full"
        )


    if x.quantity_qtl > remaining:

        c.close()

        raise HTTPException(
            409,
            f"Only {round(remaining,2)} qtl is still available"
        )


    c.execute(
        """
        INSERT INTO buyer_pool_members(
            pool_id,
            buyer_id,
            quantity_qtl,
            created_at
        )
        VALUES(?,?,?,?)

        ON CONFLICT(pool_id,buyer_id)
        DO UPDATE SET
            quantity_qtl=excluded.quantity_qtl
        """,
        (
            pool["id"],
            u["id"],
            x.quantity_qtl,
            now_iso()
        )
    )


    total = c.execute(
        """
        SELECT coalesce(sum(quantity_qtl),0) total
        FROM buyer_pool_members
        WHERE pool_id=?
        """,
        (pool["id"],)
    ).fetchone()["total"]


    status = (
        "FULL"
        if float(total) >= float(pool["target_qtl"])
        else "PARTIALLY_FILLED"
    )


    c.execute(
        """
        UPDATE buyer_pools
        SET current_qtl=?,
            status=?,
            updated_at=?
        WHERE id=?
        """,
        (
            total,
            status,
            now_iso(),
            pool["id"]
        )
    )


    c.commit()
    c.close()


    return {
        "status": "JOINED",
        "pool_id": pool["id"],
        "join_code": code,
        "my_quantity_qtl": x.quantity_qtl,
        "bulk_status": status,
        "message": "You successfully joined the bulk order"
    }

@router.post('/v3/buyer-pools/{pool_id}/join')
def v3_buyer_pool_join(
    pool_id: int,
    quantity_qtl: float,
    u=Depends(get_user_dep())
):

    require_role(u, 'buyer')

    c = conn()

    pool = c.execute(
        """
        SELECT *
        FROM buyer_pools
        WHERE id=?
        """,
        (pool_id,)
    ).fetchone()


    if not pool:

        c.close()

        raise HTTPException(
            404,
            "Bulk order not found"
        )


    if pool["status"] not in (
        "OPEN",
        "PARTIALLY_FILLED"
    ):

        c.close()

        raise HTTPException(
            409,
            "Bulk order is no longer accepting buyers"
        )


    if quantity_qtl <= 0:

        c.close()

        raise HTTPException(
            400,
            "Quantity must be greater than zero"
        )


    old = c.execute(
        """
        SELECT quantity_qtl
        FROM buyer_pool_members
        WHERE pool_id=?
          AND buyer_id=?
        """,
        (
            pool_id,
            u["id"]
        )
    ).fetchone()


    old_qty = (
        float(old["quantity_qtl"])
        if old
        else 0
    )


    remaining = (
        float(pool["target_qtl"])
        -
        float(pool["current_qtl"])
        +
        old_qty
    )


    if quantity_qtl > remaining:

        c.close()

        raise HTTPException(
            409,
            f"Maximum available quantity is {round(remaining,2)} qtl"
        )


    c.execute(
        """
        INSERT INTO buyer_pool_members(
            pool_id,
            buyer_id,
            quantity_qtl,
            created_at
        )
        VALUES(?,?,?,?)

        ON CONFLICT(pool_id,buyer_id)
        DO UPDATE SET
            quantity_qtl=excluded.quantity_qtl
        """,
        (
            pool_id,
            u["id"],
            quantity_qtl,
            now_iso()
        )
    )


    total = c.execute(
        """
        SELECT coalesce(sum(quantity_qtl),0) total
        FROM buyer_pool_members
        WHERE pool_id=?
        """,
        (pool_id,)
    ).fetchone()["total"]


    status = (
        "FULL"
        if float(total) >= float(pool["target_qtl"])
        else "PARTIALLY_FILLED"
    )


    c.execute(
        """
        UPDATE buyer_pools
        SET current_qtl=?,
            status=?,
            updated_at=?
        WHERE id=?
        """,
        (
            total,
            status,
            now_iso(),
            pool_id
        )
    )


    c.commit()
    c.close()


    return {
        "status": "JOINED",
        "pool_id": pool_id,
        "quantity_qtl": quantity_qtl,
        "bulk_status": status
    }

@router.post('/v3/buyer-pools/{pool_id}/invite')
def v3_buyer_pool_invite(
    pool_id: int,
    x: BuyerPoolInviteIn,
    u=Depends(get_user_dep())
):

    require_role(u, 'buyer')

    c = conn()


    pool = c.execute(
        """
        SELECT *
        FROM buyer_pools
        WHERE id=?
        """,
        (pool_id,)
    ).fetchone()


    if not pool:

        c.close()

        raise HTTPException(
            404,
            "Bulk order not found"
        )


    if pool["owner_id"] != u["id"]:

        c.close()

        raise HTTPException(
            403,
            "Only the bulk order creator can invite buyers"
        )


    if x.buyer_id == u["id"]:

        c.close()

        raise HTTPException(
            400,
            "You are already the organizer of this bulk order"
        )


    buyer = c.execute(
        """
        SELECT id,name,role,state,district
        FROM users
        WHERE id=?
          AND role='buyer'
        """,
        (x.buyer_id,)
    ).fetchone()


    if not buyer:

        c.close()

        raise HTTPException(
            404,
            "Buyer not found"
        )


    c.execute(
        """
        INSERT INTO buyer_pool_invites(
            pool_id,
            from_buyer_id,
            to_buyer_id,
            proposed_quantity_qtl,
            message,
            status,
            created_at,
            updated_at
        )
        VALUES(
            ?,?,?,?,?,
            'PENDING',
            ?,?
        )

        ON CONFLICT(pool_id,to_buyer_id)
        DO UPDATE SET
            proposed_quantity_qtl=excluded.proposed_quantity_qtl,
            message=excluded.message,
            status='PENDING',
            updated_at=excluded.updated_at
        """,
        (
            pool_id,
            u["id"],
            x.buyer_id,
            x.quantity_qtl,
            x.message,
            now_iso(),
            now_iso()
        )
    )


    c.execute(
        """
        INSERT INTO notifications(
            user_id,
            title,
            message,
            severity,
            created_at
        )
        VALUES(
            ?,
            'Bulk Purchase Invitation',
            ?,
            'info',
            datetime('now')
        )
        """,
        (
            x.buyer_id,
            f"{u['name']} invited you to join bulk order "
            f"{pool['name']} ({pool['join_code']})."
        )
    )


    c.commit()
    c.close()


    return {
        "status": "INVITED",
        "buyer_id": x.buyer_id,
        "buyer_name": buyer["name"],
        "join_code": pool["join_code"],
        "message": "Buyer invitation sent successfully"
    }

@router.get('/v3/buyer-pool-invites')
def v3_buyer_pool_invites(
    u=Depends(get_user_dep())
):

    require_role(u, 'buyer')

    c = conn()


    rows = c.execute(
        """
        SELECT
            i.*,
            bp.name pool_name,
            bp.crop,
            bp.variety,
            bp.grade_required,
            bp.target_qtl,
            bp.current_qtl,
            bp.target_price,
            bp.required_by_date,
            bp.delivery_location,
            bp.join_code,
            uf.name invited_by_name

        FROM buyer_pool_invites i

        JOIN buyer_pools bp
          ON bp.id=i.pool_id

        JOIN users uf
          ON uf.id=i.from_buyer_id

        WHERE i.to_buyer_id=?

        ORDER BY
            CASE i.status
                WHEN 'PENDING' THEN 0
                ELSE 1
            END,
            i.created_at DESC
        """,
        (u["id"],)
    ).fetchall()


    c.close()

    return [
        rowdict(r)
        for r in rows
    ]


@router.patch('/v3/buyer-pool-invites/{invite_id}')
def v3_buyer_pool_invite_decision(
    invite_id: int,
    x: BuyerPoolInviteDecisionIn,
    u=Depends(get_user_dep())
):

    require_role(u, 'buyer')

    c = conn()


    invite = c.execute(
        """
        SELECT
            i.*,
            bp.target_qtl,
            bp.current_qtl,
            bp.status
        FROM buyer_pool_invites i
        JOIN buyer_pools bp
          ON bp.id=i.pool_id
        WHERE i.id=?
          AND i.to_buyer_id=?
        """,
        (
            invite_id,
            u["id"]
        )
    ).fetchone()


    if not invite:

        c.close()

        raise HTTPException(
            404,
            "Bulk order invitation not found"
        )


    if invite["status"] != "PENDING":

        c.close()

        raise HTTPException(
            409,
            "This invitation has already been decided"
        )


    if x.action == "DECLINE":

        c.execute(
            """
            UPDATE buyer_pool_invites
            SET status='DECLINED',
                updated_at=?
            WHERE id=?
            """,
            (
                now_iso(),
                invite_id
            )
        )

        c.commit()
        c.close()

        return {
            "status": "DECLINED"
        }


    qty = float(
        x.quantity_qtl
        or invite["proposed_quantity_qtl"]
        or 0
    )


    if qty <= 0:

        c.close()

        raise HTTPException(
            400,
            "Enter the quantity you want to combine"
        )


    remaining = max(
        0,
        float(invite["target_qtl"])
        -
        float(invite["current_qtl"])
    )


    if qty > remaining:

        c.close()

        raise HTTPException(
            409,
            f"Only {round(remaining,2)} qtl remains in this bulk order"
        )


    c.execute(
        """
        INSERT INTO buyer_pool_members(
            pool_id,
            buyer_id,
            quantity_qtl,
            created_at
        )
        VALUES(?,?,?,?)

        ON CONFLICT(pool_id,buyer_id)
        DO UPDATE SET
            quantity_qtl=excluded.quantity_qtl
        """,
        (
            invite["pool_id"],
            u["id"],
            qty,
            now_iso()
        )
    )


    total = c.execute(
        """
        SELECT coalesce(sum(quantity_qtl),0) total
        FROM buyer_pool_members
        WHERE pool_id=?
        """,
        (invite["pool_id"],)
    ).fetchone()["total"]


    pool_status = (
        "FULL"
        if float(total) >= float(invite["target_qtl"])
        else "PARTIALLY_FILLED"
    )


    c.execute(
        """
        UPDATE buyer_pools
        SET current_qtl=?,
            status=?,
            updated_at=?
        WHERE id=?
        """,
        (
            total,
            pool_status,
            now_iso(),
            invite["pool_id"]
        )
    )


    c.execute(
        """
        UPDATE buyer_pool_invites
        SET status='ACCEPTED',
            proposed_quantity_qtl=?,
            updated_at=?
        WHERE id=?
        """,
        (
            qty,
            now_iso(),
            invite_id
        )
    )


    c.commit()
    c.close()


    return {
        "status": "ACCEPTED",
        "pool_id": invite["pool_id"],
        "quantity_qtl": qty,
        "bulk_status": pool_status
    }

@router.get('/v3/nearby-buyers')
def v3_nearby_buyers(
    u=Depends(get_user_dep())
):

    require_role(u, 'buyer')

    c = conn()


    rows = c.execute(
        """
        SELECT
            us.id,
            us.name,
            us.district,
            us.state,
            us.phone,
            coalesce(ts.buyer_reliability,50)
                buyer_reliability,
            coalesce(ts.instant_payment,50)
                instant_payment,
            coalesce(ts.zero_cancel_streak,0)
                zero_cancel_streak

        FROM users us

        LEFT JOIN trust_scores ts
          ON ts.user_id=us.id

        WHERE us.role='buyer'
          AND us.id<>?
          AND coalesce(
                NULLIF(us.state,''),
                'Tamil Nadu'
              )='Tamil Nadu'

        ORDER BY
            CASE
                WHEN us.district=? THEN 0
                ELSE 1
            END,
            buyer_reliability DESC,
            us.name

        LIMIT 50
        """,
        (
            u["id"],
            u.get("district") or ""
        )
    ).fetchall()


    c.close()

    return [
        rowdict(r)
        for r in rows
    ]

@router.get('/v3/route-share-options')
def v3_route_share_options(
    u=Depends(get_user_dep())
):

    require_role(u, 'buyer')

    c = conn()


    rows = c.execute(
        """
        SELECT *
        FROM transporters
        WHERE verified=1
          AND state='Tamil Nadu'
        ORDER BY
            rating DESC,
            rate_per_km ASC
        LIMIT 50
        """
    ).fetchall()


    result = []

    for row in rows:

        item = rowdict(row)

        capacity = float(
            item.get("capacity_qtl")
            or 0
        )

        item["available_capacity_qtl"] = capacity

        item["route_share_status"] = (
            "AVAILABLE"
            if capacity > 0
            else "CHECK_AVAILABILITY"
        )

        result.append(item)


    c.close()

    return result

@router.post('/v3/logistics-bids')
def v3_create_logistics_bid(
    x: LogisticsBidIn,
    u=Depends(get_user_dep())
):

    require_role(u, 'buyer')

    c = conn()

    ensure_verified(
        c,
        u,
        'bid for shared logistics'
    )


    transporter = c.execute(
        """
        SELECT *
        FROM transporters
        WHERE id=?
          AND verified=1
        """,
        (x.transporter_id,)
    ).fetchone()


    if not transporter:

        c.close()

        raise HTTPException(
            404,
            "Verified transporter not found"
        )


    if x.pool_id:

        pool = c.execute(
            """
            SELECT id
            FROM buyer_pools
            WHERE id=?
            """,
            (x.pool_id,)
        ).fetchone()

        if not pool:

            c.close()

            raise HTTPException(
                404,
                "Linked bulk order not found"
            )


    rate = float(
        transporter["rate_per_km"]
        or 0
    )


    estimated_cost = round(
        max(
            0,
            x.estimated_distance_km
        )
        *
        max(
            0,
            rate
        ),
        2
    )


    confirmation_code = (
        "LB-"
        + secrets.token_hex(4).upper()
    )


    cur = c.execute(
        """
        INSERT INTO logistics_route_bids(
            buyer_id,
            transporter_id,
            pool_id,
            crop,
            quantity_qtl,
            pickup_location,
            delivery_location,
            pickup_date,
            pickup_time,
            proposed_bid,
            estimated_distance_km,
            estimated_cost,
            special_instructions,
            status,
            confirmation_code,
            created_at,
            updated_at
        )
        VALUES(
            ?,?,?,?,?,?,?,?,?,?,?,?,?,
            'PENDING',
            ?,?,?
        )
        """,
        (
            u["id"],
            x.transporter_id,
            x.pool_id,
            x.crop,
            x.quantity_qtl,
            x.pickup_location,
            x.delivery_location,
            x.pickup_date,
            x.pickup_time,
            x.proposed_bid,
            x.estimated_distance_km,
            estimated_cost,
            x.special_instructions,
            confirmation_code,
            now_iso(),
            now_iso()
        )
    )


    bid_id = cur.lastrowid


    c.commit()
    c.close()


    audit_event(
        u["id"],
        "shared_logistics_bid_created",
        f"bid={bid_id};transporter={x.transporter_id}"
    )


    return {
        "id": bid_id,
        "status": "PENDING",
        "confirmation_code": confirmation_code,
        "transporter_name": transporter["name"],
        "vehicle_type": transporter["vehicle_type"],
        "rate_per_km": transporter["rate_per_km"],
        "estimated_cost": estimated_cost,
        "proposed_bid": x.proposed_bid,
        "message": "Route-share bid submitted successfully"
    }

@router.get('/v3/logistics-bids')
def v3_my_logistics_bids(
    u=Depends(get_user_dep())
):

    require_role(u, 'buyer', 'admin')

    c = conn()


    if u["role"] == "admin":

        rows = c.execute(
            """
            SELECT
                lb.*,
                t.name transporter_name,
                t.vehicle_type,
                
                t.rate_per_km,
                t.rating,
                us.name buyer_name
            FROM logistics_route_bids lb
            JOIN transporters t
              ON t.id=lb.transporter_id
            JOIN users us
              ON us.id=lb.buyer_id
            ORDER BY lb.id DESC
            """
        ).fetchall()

    else:

        rows = c.execute(
            """
            SELECT
                lb.*,
                t.name transporter_name,
                t.vehicle_type,
                
                t.rate_per_km,
                t.rating
            FROM logistics_route_bids lb
            JOIN transporters t
              ON t.id=lb.transporter_id
            WHERE lb.buyer_id=?
            ORDER BY lb.id DESC
            """,
            (u["id"],)
        ).fetchall()


    c.close()

    return [
        rowdict(r)
        for r in rows
    ]

@router.get('/v3/logistics-bids/{bid_id}')
def v3_logistics_bid_detail(
    bid_id: int,
    u=Depends(get_user_dep())
):

    require_role(u, 'buyer', 'admin')

    c = conn()


    row = c.execute(
        """
        SELECT
            lb.*,
            t.name transporter_name,
            t.vehicle_type,
            
            t.capacity_qtl,
            t.rate_per_km,
            t.rating,
            t.phone transporter_phone

        FROM logistics_route_bids lb

        JOIN transporters t
          ON t.id=lb.transporter_id

        WHERE lb.id=?
        """,
        (bid_id,)
    ).fetchone()


    if not row:

        c.close()

        raise HTTPException(
            404,
            "Logistics bid not found"
        )


    if (
        u["role"] != "admin"
        and row["buyer_id"] != u["id"]
    ):

        c.close()

        raise HTTPException(
            403,
            "This logistics bid does not belong to you"
        )


    result = rowdict(row)

    c.close()

    return result


class AdminMessageIn(BaseModel):
    message:str=Field(min_length=2,max_length=1000);severity:str='info'
@router.post('/v3/admin/users/{user_id}/message')
def v3_admin_message(user_id:int,x:AdminMessageIn,u=Depends(get_user_dep())):
    require_role(u,'admin');c=conn();c.execute("INSERT INTO notifications(user_id,title,message,severity,created_at) VALUES(?,?,?,?,datetime('now'))",(user_id,'Message from GRAM AI Admin',x.message,x.severity));c.commit();c.close();return {'status':'SENT'}
