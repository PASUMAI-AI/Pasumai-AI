# Load .env before any module reads os.environ (GROQ_API_KEY, SMTP, Razorpay).
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    Request,
    UploadFile,
    File,
    Form
)
from quality_model import analyze_produce_image

from certificate_service import (
    generate_quality_certificate,
    ensure_validity_columns,
    apply_validity,
    certificate_details,
    verification_id_for_listing,
    attach_certificate,
    resolve_upload
)
from otp_service import (
    generate_otp,
    verify_otp,
    normalize_phone
)

from messaging_service import (
    send_otp_sms
)
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from jose import jwt, JWTError
import bcrypt, sqlite3, os, time, math, secrets, string, smtplib, hashlib
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
from typing import Optional
from ml_engine import forecast_market, compare_markets

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "gramai.db")
UPLOAD_DIR = os.path.join(
    BASE,
    "uploads"
)

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)
SECRET = os.environ.get("GRAMAI_SECRET","CHANGE-ME-IN-PRODUCTION-GRAMAI-2026")
ALG = "HS256"
TOKEN_MINUTES = 180

SMTP_HOST=os.environ.get("GRAMAI_SMTP_HOST","")
SMTP_PORT=int(os.environ.get("GRAMAI_SMTP_PORT","587"))
SMTP_USER=os.environ.get("GRAMAI_SMTP_USER","")
SMTP_PASSWORD=os.environ.get("GRAMAI_SMTP_PASSWORD","")
SMTP_FROM=os.environ.get("GRAMAI_SMTP_FROM",SMTP_USER or "no-reply@gramai.local")

app=FastAPI(title="GRAM AI Whole Project API",version="1.0.0")
try:
    ensure_validity_columns(DB)
except Exception as e:
    print("Certificate validity migration skipped:", e)
app.mount("/static",StaticFiles(directory=os.path.join(BASE,"static")),name="static")
security=HTTPBearer(auto_error=False)

RATE={}
RATE_LIMIT=120
RATE_WINDOW=60

def db():
    c=sqlite3.connect(DB)
    c.row_factory=sqlite3.Row
    return c

@app.middleware("http")
async def security_headers(request:Request,call_next):
    ip=request.client.host if request.client else "unknown"
    now=time.time()
    bucket=[x for x in RATE.get(ip,[]) if now-x<RATE_WINDOW]
    if len(bucket)>=RATE_LIMIT:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=429,content={"detail":"Too many requests"})
    bucket.append(now); RATE[ip]=bucket
    response=await call_next(request)
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["X-Frame-Options"]="DENY"
    response.headers["Referrer-Policy"]="strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"]="geolocation=(self)"
    response.headers["Cache-Control"]="no-store"
    return response

class Login(BaseModel):
    email: EmailStr
    password: str=Field(min_length=8,max_length=128)
    login_as: Optional[str]=Field(default=None, pattern="^(farmer|buyer|admin)$")
class PhoneOTPRequest(BaseModel):
    phone: str = Field(
        min_length=10,
        max_length=15
    )


class PhoneOTPVerify(BaseModel):
    login_as: Optional[str] = Field(default=None, pattern="^(farmer|buyer|admin)$")

    phone: str = Field(
        min_length=10,
        max_length=15
    )

    otp: str = Field(
        min_length=6,
        max_length=6
    )

class Register(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    phone: str = Field(min_length=10, max_length=15)
    role: str = Field(default="farmer", pattern="^(farmer|buyer)$")
    district: str = Field(default="", max_length=80)
    state: str = Field(default="", max_length=80)

class ProfileIn(BaseModel):
    name:str
    phone:str=""
    district:str=""
    state:str=""
    address:str=""
    farm_size_acres:float=0
    preferred_language:str="English"
    bank_account_name:str=""
    bank_account_last4:str=""
    bank_ifsc:str=""
    upi_id:str=""

class PasswordIn(BaseModel):
    current_password:str=Field(min_length=8,max_length=128)
    new_password:str=Field(min_length=8,max_length=128)

class ListingIn(BaseModel):

    verification_id: int

    variety: str = "Standard"

    quantity_qtl: float = Field(
        gt=0
    )

    ask_price: float = Field(
        gt=0
    )

    harvest_date: Optional[str] = None

    packaging: str = "Bags / crates"

    min_order_qtl: float = Field(
        default=1,
        gt=0
    )

    seller_transport: bool = False

    transport_cost_per_km: float = Field(
        default=0,
        ge=0
    )

    delivery_radius_km: float = Field(
        default=0,
        ge=0
    )

    loading_included: bool = False

    quality_notes: str = ""

class OrderIn(BaseModel):
    listing_id:int
    quantity_qtl:float=Field(gt=0)
    delivery_mode:str=Field(default="SELF_PICKUP",pattern="^(SELF_PICKUP|SELLER_TRANSPORT)$")
    buyer_lat:Optional[float]=None
    buyer_lon:Optional[float]=None

class NegotiationIn(BaseModel):
    listing_id:int
    offer_price:float=Field(gt=0)
    message:str=Field(min_length=2,max_length=300)

def hpw(p):
    return bcrypt.hashpw(p.encode(),bcrypt.gensalt()).decode()

def vpw(p,h):
    try:return bcrypt.checkpw(p.encode(),h.encode())
    except:return False

def token(row):
    return jwt.encode({"sub":str(row["id"]),"role":row["role"],"email":row["email"],
                       "exp":datetime.now(timezone.utc)+timedelta(minutes=TOKEN_MINUTES)},SECRET,algorithm=ALG)

def user(creds:HTTPAuthorizationCredentials=Depends(security)):
    if not creds: raise HTTPException(401,"Authentication required")
    try:
        d=jwt.decode(creds.credentials,SECRET,algorithms=[ALG])
        uid=int(d["sub"])
    except (JWTError,ValueError,KeyError):
        raise HTTPException(401,"Invalid or expired token")
    c=db(); r=c.execute("select * from users where id=?",(uid,)).fetchone(); c.close()
    if not r: raise HTTPException(401,"User not found")
    return dict(r)

def roles(*allowed):
    def dep(u=Depends(user)):
        if u["role"] not in allowed: raise HTTPException(403,"Insufficient role permissions")
        return u
    return dep

def audit(uid,action,details=""):
    c=db(); c.execute("insert into audit_logs(user_id,action,details,created_at) values(?,?,?,datetime('now'))",(uid,action,details)); c.commit(); c.close()

def temp_password():
    alphabet=string.ascii_letters+string.digits+"@#%!"
    while True:
        p="".join(secrets.choice(alphabet) for _ in range(12))
        if any(x.isupper() for x in p) and any(x.islower() for x in p) and any(x.isdigit() for x in p):
            return p

def normalize_phone_number(phone: str) -> str:
    phone = "".join(ch for ch in phone if ch.isdigit())

    if len(phone) == 10:
        return "91" + phone

    if len(phone) == 12 and phone.startswith("91"):
        return phone

    raise HTTPException(
        status_code=400,
        detail="Enter a valid 10-digit Indian mobile number"
    )

def send_or_queue(to,subject,body):
    sent=0; err=""
    if SMTP_HOST and SMTP_USER and SMTP_PASSWORD:
        try:
            msg=EmailMessage();msg["From"]=SMTP_FROM;msg["To"]=to;msg["Subject"]=subject;msg.set_content(body)
            with smtplib.SMTP(SMTP_HOST,SMTP_PORT,timeout=15) as s:
                s.starttls();s.login(SMTP_USER,SMTP_PASSWORD);s.send_message(msg)
            sent=1
        except Exception as e: err=str(e)[:500]
    c=db();c.execute("insert into email_outbox(to_email,subject,body,sent,error,created_at) values(?,?,?,?,?,datetime('now'))",(to,subject,body,sent,err));c.commit();c.close()
    return bool(sent)

@app.get("/")
def home():
    return FileResponse(os.path.join(BASE,"static","index.html"))

@app.post("/auth/login")
def login(x:Login):
    c=db();r=c.execute("select * from users where lower(email)=lower(?)",(x.email,)).fetchone();c.close()
    if not r or not vpw(x.password,r["password"]):raise HTTPException(401,"Invalid email or password")
    if x.login_as and r["role"] != x.login_as: raise HTTPException(403,f"This account is registered as {r['role']}, not {x.login_as}")
    audit(r["id"],"login","success")
    return {"access_token":token(r),"token_type":"bearer","role":r["role"],"name":r["name"]}

@app.post("/auth/otp/request")
def request_phone_otp(
    x: PhoneOTPRequest
):

    try:
        phone = normalize_phone(
            x.phone
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


    c = db()

    account = c.execute(
        """
        SELECT *
        FROM users
        WHERE phone=?
        """,
        (
            phone,
        )
    ).fetchone()

    c.close()


    if not account:
        raise HTTPException(
            status_code=404,
            detail=(
                "No GRAM AI account is linked "
                "with this mobile number."
            )
        )


    otp_result = generate_otp(
        phone
    )


    sms_result = send_otp_sms(
        otp_result["phone"],
        otp_result["otp"]
    )


    response = {
        "message":
            "OTP generated successfully",

        "phone":
            phone,

        "expires_in":
            otp_result["expires_in"]
    }


    # For local/demo testing only.
    if (
        sms_result.get("provider")
        ==
        "DEMO"
    ):
        response["development_otp"] = (
            otp_result["otp"]
        )


    return response

@app.post("/auth/otp/verify")
def verify_phone_otp(
    x: PhoneOTPVerify
):

    try:
        phone = normalize_phone(
            x.phone
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


    result = verify_otp(
        phone,
        x.otp
    )


    if not result.get(
        "success"
    ):
        raise HTTPException(
            status_code=401,
            detail=result.get(
                "message",
                "OTP verification failed"
            )
        )


    c = db()

    account = c.execute(
        """
        SELECT *
        FROM users
        WHERE phone=?
        """,
        (
            phone,
        )
    ).fetchone()

    c.close()


    if not account:
        raise HTTPException(
            status_code=404,
            detail="User account not found"
        )


    if x.login_as and account["role"] != x.login_as:
        raise HTTPException(403, f"This account is registered as {account['role']}, not {x.login_as}")

    audit(
        account["id"],
        "phone_otp_login",
        "Mobile OTP login successful"
    )


    return {
        "access_token":
            token(account),

        "token_type":
            "bearer",

        "role":
            account["role"],

        "name":
            account["name"]
    }

@app.post("/auth/register")
def register(x: Register):

    phone = normalize_phone_number(x.phone)

    c = db()

    # Check duplicate email
    if c.execute(
        "SELECT 1 FROM users WHERE lower(email)=lower(?)",
        (x.email,)
    ).fetchone():

        c.close()

        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    # Check duplicate phone
    if c.execute(
        "SELECT 1 FROM users WHERE phone=?",
        (phone,)
    ).fetchone():

        c.close()

        raise HTTPException(
            status_code=409,
            detail="Mobile number already registered"
        )

    p = temp_password()

    cur = c.execute(
        """
        INSERT INTO users(
            name,
            email,
            password,
            role,
            district,
            state,
            phone,
            must_change_password
        )
        VALUES(
            ?,?,?,?,?,?,?,1
        )
        """,
        (
            x.name,
            x.email.lower(),
            hpw(p),
            x.role,
            x.district,
            x.state,
            phone
        )
    )

    c.commit()

    r = c.execute(
        "SELECT * FROM users WHERE id=?",
        (cur.lastrowid,)
    ).fetchone()

    c.close()

    body = (
        f"Welcome to GRAM AI, {x.name}.\n\n"
        f"Email: {x.email.lower()}\n"
        f"Temporary password: {p}\n"
        f"Registered mobile: +{phone}\n\n"
        f"Change your password after login."
    )

    sent = send_or_queue(
        x.email.lower(),
        "Your GRAM AI login password",
        body
    )

    audit(
        cur.lastrowid,
        "register",
        f"{x.role};phone={phone};email_sent={sent}"
    )

    return {
        "message":
            "Registration successful. "
            "You can now login with email/password "
            "or mobile OTP.",

        "email_sent":
            sent,

        "development_password":
            None if sent else p,

        "access_token":
            token(r),

        "token_type":
            "bearer"
    }

@app.get("/auth/me")
def me(u=Depends(user)):
    keys=["id","name","email","role","district","state","phone","address","farm_size_acres","preferred_language","bank_account_name","bank_account_last4","bank_ifsc","upi_id"]
    return {k:u.get(k) for k in keys}

@app.get("/api/profile")
def profile(u=Depends(user)):
    return me(u)

@app.patch("/api/profile")
def update_profile(x:ProfileIn,u=Depends(user)):
    c=db()
    c.execute("""update users set name=?,phone=?,district=?,state=?,address=?,farm_size_acres=?,
                 preferred_language=?,bank_account_name=?,bank_account_last4=?,bank_ifsc=?,upi_id=? where id=?""",
              (x.name,x.phone,x.district,x.state,x.address,x.farm_size_acres,x.preferred_language,
               x.bank_account_name,x.bank_account_last4[-4:],x.bank_ifsc,x.upi_id,u["id"]))
    c.commit();c.close();audit(u["id"],"profile_update","profile changed")
    return {"message":"Profile updated"}

@app.post("/api/password-reset")
def password_reset(x:PasswordIn,u=Depends(user)):
    if not vpw(x.current_password,u["password"]):raise HTTPException(400,"Current password is incorrect")
    c=db();c.execute("update users set password=?,must_change_password=0 where id=?",(hpw(x.new_password),u["id"]));c.commit();c.close()
    audit(u["id"],"password_reset","password changed")
    return {"message":"Password changed successfully"}

@app.get("/api/summary")
def summary(u=Depends(user)):
    c=db()
    out={
        "markets":c.execute("select count(*) n from markets").fetchone()["n"],
        "states":c.execute("select count(distinct state) n from markets").fetchone()["n"],
        "buyers":c.execute("select count(*) n from buyers where verified=1").fetchone()["n"],
        "transporters":c.execute("select count(*) n from transporters where verified=1").fetchone()["n"],
        "listings":c.execute("select count(*) n from listings where status='OPEN'").fetchone()["n"]
    };c.close();return out

@app.get("/api/public/prices")
def public_prices():
    """Latest average mandi price per crop for the public landing page (no login)."""
    c=db()
    latest=c.execute("select max(price_date) d from prices").fetchone()["d"]
    rows=c.execute("""select p.crop,avg(p.modal_price) price,max(p.modal_price) best,
                      (select avg(q.modal_price) from prices q where q.crop=p.crop and q.price_date=date(?,'-7 day')) week_ago,
                      (select m.name||', '||m.state from prices q join markets m on m.id=q.market_id
                        where q.crop=p.crop and q.price_date=? order by q.modal_price desc limit 1) best_market
                      from prices p where p.price_date=? group by p.crop order by p.crop""",(latest,latest,latest)).fetchall()
    c.close()
    return {"date":latest,"crops":[{"crop":r["crop"],"price":round(r["price"]),"best":round(r["best"]),
            "best_market":r["best_market"],
            "change_pct":round((r["price"]-r["week_ago"])/r["week_ago"]*100,1) if r["week_ago"] else 0} for r in rows]}

@app.get("/api/crops")
def crops(u=Depends(user)):
    c=db();rows=c.execute("select * from crops order by name").fetchall();c.close();return [dict(r) for r in rows]

@app.get("/api/markets")
def markets(state:Optional[str]=None,priced:bool=False,u=Depends(user)):
    # priced=true keeps only markets with price history (needed for forecasts).
    from market_infra import PRICED_SQL
    sql="select m.* from markets m where (? is null or m.state=?)"+(" and "+PRICED_SQL if priced else "")+" order by m.state,m.name"
    c=db();rows=c.execute(sql,(state,state)).fetchall();c.close();return [dict(r) for r in rows]

@app.get("/api/demand")
def demand(crop:str="Tomato",u=Depends(user)):
    c=db()
    rows=c.execute("""select m.state,avg(p.demand_index) demand,avg(p.modal_price) price,avg(p.arrivals_qtl) arrivals
                      from prices p join markets m on m.id=p.market_id
                      where p.crop=? and p.price_date=(select max(price_date) from prices)
                      group by m.state order by demand desc""",(crop,)).fetchall();c.close()
    return [{**dict(r),"signal":"HIGH" if r["demand"]>=70 else "MEDIUM" if r["demand"]>=50 else "LOW"} for r in rows]

@app.get("/api/buyers")
def buyers(state:Optional[str]=None,u=Depends(user)):
    c=db();rows=c.execute("select * from buyers where (? is null or state=?) order by verified desc,rating desc",(state,state)).fetchall();c.close();return [dict(r) for r in rows]

@app.get("/api/transport")
def transport(state:Optional[str]=None,u=Depends(user)):
    c=db();rows=c.execute("select * from transporters where (? is null or state=?) order by verified desc,rating desc",(state,state)).fetchall();c.close();return [dict(r) for r in rows]

@app.get("/api/listings")
def listings(u=Depends(user)):
    c=db();rows=c.execute("""select l.*,u.name seller_name from listings l join users u on u.id=l.seller_id
                             where l.status='OPEN' order by l.created_at desc""").fetchall()
    out=[attach_certificate(c,dict(r),verification_id_for_listing(c,r)) if r["quality_verified"] else dict(r) for r in rows]
    c.close();return out

@app.get("/api/my-produce")
def my_produce(u=Depends(user)):
    c=db();rows=c.execute("select * from listings where seller_id=? order by created_at desc",(u["id"],)).fetchall();c.close();return [dict(r) for r in rows]

@app.post("/api/produce/inspect")
async def inspect_produce(
    crop: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    location_source: str = Form(...),
    photo: UploadFile = File(...),
    u=Depends(user)
):

    if u["role"] not in {
        "farmer",
        "admin"
    }:
        raise HTTPException(
            403,
            "Only farmers can inspect produce"
        )

    if not (-90 <= latitude <= 90):
        raise HTTPException(
            400,
            "Valid latitude is required"
        )

    if not (-180 <= longitude <= 180):
        raise HTTPException(
            400,
            "Valid longitude is required"
        )

    if location_source not in {
        "gps",
        "manual"
    }:
        raise HTTPException(
            400,
            "Location source must be gps or manual"
        )

    if not photo.content_type or not photo.content_type.startswith("image/"):
        raise HTTPException(
            400,
            "Produce photo is required"
        )

    extension = os.path.splitext(
        photo.filename or ""
    )[1].lower()

    if extension not in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp"
    }:
        extension = ".jpg"

    filename = (
        f"produce_{u['id']}_"
        f"{int(time.time())}_"
        f"{secrets.token_hex(4)}"
        f"{extension}"
    )

    image_path = os.path.join(
        UPLOAD_DIR,
        filename
    )

    contents = await photo.read()

    if not contents:
        raise HTTPException(
            400,
            "Uploaded image is empty"
        )

    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            400,
            "Image must be below 10 MB"
        )

    with open(
        image_path,
        "wb"
    ) as f:
        f.write(
            contents
        )

    try:
        result = analyze_produce_image(
            image_path,
            crop
        )
    except Exception as e:
        if os.path.exists(image_path):
            os.remove(image_path)

        raise HTTPException(
            400,
            f"YOLO grading failed: {e}"
        )

    c = db()

    cur = c.execute(
        """
        INSERT INTO quality_verifications(
            user_id,
            crop,
            predicted_grade,
            confidence,
            image_path,
            latitude,
            longitude,
            location_source,
            model_name,
            created_at
        )
        VALUES(
            ?,?,?,?,?,?,?,?,?,
            datetime('now')
        )
        """,
        (
            u["id"],
            crop,
            result["grade"],
            result["confidence"],
            image_path,
            latitude,
            longitude,
            location_source,
            result["model"]
        )
    )

    verification_id = cur.lastrowid

    certificate_number = (
        f"GRAMAI-QC-{verification_id:06d}"
    )

    certificate_path = generate_quality_certificate(
        certificate_number=
            certificate_number,
        farmer_name=
            u["name"],
        crop=
            crop,
        grade=
            result["grade"],
        confidence=
            result["confidence"],
        latitude=
            latitude,
        longitude=
            longitude,
        location_source=
            location_source,
        image_hash=
            result["image_sha256"],
        model_name=
            result["model"],
        image_path=
            image_path,
        scanned_at=
            c.execute(
                "SELECT created_at FROM quality_verifications WHERE id=?",
                (verification_id,)
            ).fetchone()["created_at"]
    )

    c.execute(
        """
        UPDATE quality_verifications
        SET certificate_path=?
        WHERE id=?
        """,
        (
            certificate_path,
            verification_id
        )
    )

    c.execute(
        """
        INSERT INTO quality_certificates(
            verification_id,
            certificate_number,
            farmer_id,
            crop,
            grade,
            confidence,
            latitude,
            longitude,
            certificate_path,
            issued_at
        )
        VALUES(
            ?,?,?,?,?,?,?,?,?,
            datetime('now')
        )
        """,
        (
            verification_id,
            certificate_number,
            u["id"],
            crop,
            result["grade"],
            result["confidence"],
            latitude,
            longitude,
            certificate_path
        )
    )

    valid_until = apply_validity(
        c,
        verification_id
    )

    c.commit()
    c.close()

    return {
        "valid_until":
            valid_until,
        "verification_id":
            verification_id,
        "certificate_number":
            certificate_number,
        "crop":
            crop,
        "grade":
            result["grade"],
        "confidence":
            result["confidence"],
        "confidence_percent":
            result["confidence_percent"],
        "validated_crop_model":
            result.get("validated_crop_model", True),
        "model_label":
            result.get("model", "YOLO"),
        "latitude":
            latitude,
        "longitude":
            longitude,
        "location_source":
            location_source,
        "certificate_url":
            f"/api/produce/certificate/{verification_id}"
    }

@app.get("/api/produce/certificate/{verification_id}/details")
def get_quality_certificate_details(
    verification_id: int,
    u=Depends(user)
):
    """Certificate summary for farmers and buyers: grade, scan date,
    validity window and links to the produce photo and PDF."""
    c = db()
    info = certificate_details(c, verification_id)
    c.close()
    if not info:
        raise HTTPException(404, "Verification not found")
    return info


@app.get("/api/produce/certificate/{verification_id}/photo")
def get_quality_certificate_photo(
    verification_id: int,
    u=Depends(user)
):
    c = db()
    row = c.execute(
        "SELECT image_path FROM quality_verifications WHERE id=?",
        (verification_id,)
    ).fetchone()
    c.close()
    path = resolve_upload(row["image_path"]) if row else None
    if not path:
        raise HTTPException(404, "Produce photo not found")
    return FileResponse(path)


@app.get("/api/produce/certificate/{verification_id}")
def get_quality_certificate(
    verification_id: int,
    u=Depends(user)
):
    """Rebuild the PDF from the stored record on every download, so the
    status line (valid / expired) is current and older certificates pick
    up the produce photo and validity period."""
    c = db()
    row = c.execute(
        """
        SELECT v.*, u.name farmer_name, q.certificate_number, q.scanned_at
        FROM quality_verifications v
        LEFT JOIN users u ON u.id = v.user_id
        LEFT JOIN quality_certificates q ON q.verification_id = v.id
        WHERE v.id=?
        """,
        (verification_id,)
    ).fetchone()
    c.close()

    if not row:
        raise HTTPException(
            404,
            "Verification not found"
        )

    image = resolve_upload(row["image_path"])
    image_hash = "unavailable"
    if image:
        with open(image, "rb") as f:
            image_hash = hashlib.sha256(f.read()).hexdigest()

    try:
        path = generate_quality_certificate(
            certificate_number=row["certificate_number"] or f"GRAMAI-QC-{verification_id:06d}",
            farmer_name=row["farmer_name"] or "Farmer",
            crop=row["crop"],
            grade=row["predicted_grade"],
            confidence=row["confidence"] or 0,
            latitude=row["latitude"] or 0.0,
            longitude=row["longitude"] or 0.0,
            location_source=row["location_source"] or "",
            image_hash=image_hash,
            model_name=row["model_name"] or "YOLO",
            image_path=row["image_path"],
            scanned_at=row["scanned_at"] or row["created_at"]
        )
    except Exception:
        path = row["certificate_path"]

    if not path or not os.path.exists(path):
        raise HTTPException(
            404,
            "Certificate not found"
        )

    return FileResponse(
        path,
        media_type="application/pdf",
        filename=os.path.basename(path)
    )


@app.post("/api/listings")
def create_listing(
    x: ListingIn,
    u=Depends(user)
):

    if u["role"] not in {
        "farmer",
        "admin"
    }:
        raise HTTPException(
            403,
            "Only farmers can sell produce"
        )

    c = db()

    # Marketplace security gate: farmer must be GRAM Verified (KYC + live-photo check).
    try:
        kyc = c.execute("SELECT status,coalesce(live_check,0) live_check FROM kyc_profiles WHERE user_id=?", (u["id"],)).fetchone()
    except Exception:
        kyc = None
    if u["role"] != "admin" and (not kyc or kyc["status"] != "VERIFIED" or not kyc["live_check"]):
        c.close()
        raise HTTPException(403, "GRAM Verified KYC + live photo is required before selling")

    # Get the verified YOLO inspection
    verification = c.execute(
        """
        SELECT *
        FROM quality_verifications
        WHERE id=?
          AND user_id=?
        """,
        (
            x.verification_id,
            u["id"]
        )
    ).fetchone()

    if not verification:
        c.close()

        raise HTTPException(
            400,
            "Valid automatic quality verification is required before selling"
        )

    # Prevent the same verification/photo from being reused
    existing = c.execute(
        """
        SELECT id
        FROM listings
        WHERE quality_image=?
          AND seller_id=?
        LIMIT 1
        """,
        (
            verification["image_path"],
            u["id"]
        )
    ).fetchone()

    if existing:
        c.close()

        raise HTTPException(
            409,
            "This inspected produce photo has already been listed"
        )

    latitude = float(
        verification["latitude"]
    )

    longitude = float(
        verification["longitude"]
    )

    # Find nearest seeded market so your current
    # district/state display keeps working
    markets = c.execute(
        """
        SELECT district,state,lat,lon
        FROM markets
        """
    ).fetchall()

    nearest = None
    nearest_distance = None

    for market in markets:

        distance = (
            (latitude - market["lat"]) ** 2
            +
            (longitude - market["lon"]) ** 2
        )

        if (
            nearest_distance is None
            or
            distance < nearest_distance
        ):
            nearest_distance = distance
            nearest = market

    district = (
        nearest["district"]
        if nearest
        else ""
    )

    state = (
        nearest["state"]
        if nearest
        else ""
    )

    cur = c.execute(
        """
        INSERT INTO listings(
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
            created_at,
            quality_grade,
            quality_confidence,
            quality_verified,
            quality_certificate,
            quality_image,
            latitude,
            longitude,
            location_verified,
            location_source
        )
        VALUES(
            ?,?,?,?,?,?,?,?,?,?,
            ?,?,?,?,?,?,?,
            'OPEN',
            datetime('now'),
            ?,?,?,?,?,?,?,?,?
        )
        """,
        (
            u["id"],
            verification["crop"],
            x.variety,
            verification["predicted_grade"],
            x.quantity_qtl,
            x.ask_price,
            district,
            state,
            x.harvest_date,
            x.packaging,
            x.min_order_qtl,
            int(x.seller_transport),
            x.transport_cost_per_km,
            x.delivery_radius_km,
            int(x.loading_included),
            x.quality_notes,
            verification["image_path"],
            verification["predicted_grade"],
            verification["confidence"],
            1,
            verification["certificate_path"],
            verification["image_path"],
            latitude,
            longitude,
            1,
            verification["location_source"]
        )
    )

    listing_id = cur.lastrowid

    c.commit()
    c.close()

    audit(
        u["id"],
        "create_verified_listing",
        f"listing={listing_id};verification={x.verification_id}"
    )

    return {
        "id": listing_id,
        "status": "OPEN",
        "crop": verification["crop"],
        "grade": verification["predicted_grade"],
        "quality_verified": True
    }

@app.get("/api/listings/{listing_id}/quote")
def quote(listing_id:int,quantity_qtl:float=1,buyer_lat:Optional[float]=None,buyer_lon:Optional[float]=None,u=Depends(user)):
    c=db()
    l=c.execute("""select l.*,u.name seller_name from listings l join users u on u.id=l.seller_id where l.id=?""",(listing_id,)).fetchone()
    if not l:c.close();raise HTTPException(404,"Listing not found")
    qty=max(quantity_qtl,l["min_order_qtl"])
    produce=qty*l["ask_price"]
    fee=produce*0.005
    distance=0;transport=0
    if buyer_lat is not None and buyer_lon is not None:
        m=c.execute("select lat,lon from markets where state=? order by id limit 1",(l["state"],)).fetchone()
        if m:
            distance=111*math.sqrt((buyer_lat-m["lat"])**2+((buyer_lon-m["lon"])*math.cos(math.radians(buyer_lat)))**2)
    if l["seller_transport"] and distance>0:
        transport=distance*l["transport_cost_per_km"]
    c.close()
    return {"listing_id":listing_id,"crop":l["crop"],"seller":l["seller_name"],"quantity_qtl":qty,
            "price_per_qtl":l["ask_price"],"produce_cost":round(produce,2),"platform_fee":round(fee,2),
            "seller_transport_available":bool(l["seller_transport"]),"transport_cost_per_km":l["transport_cost_per_km"],
            "delivery_radius_km":l["delivery_radius_km"],"loading_included":bool(l["loading_included"]),
            "estimated_distance_km":round(distance,1),"estimated_transport_cost":round(transport,2),
            "self_pickup_total":round(produce+fee,2),"seller_delivery_total":round(produce+fee+transport,2),
            "grade":l["grade"],"variety":l["variety"],"packaging":l["packaging"],"quality_notes":l["quality_notes"]}

@app.post("/api/orders")
def place_order(x:OrderIn,u=Depends(user)):
    c=db()
    try:
        kyc=c.execute("SELECT status,coalesce(live_check,0) live_check FROM kyc_profiles WHERE user_id=?",(u["id"],)).fetchone()
    except Exception:
        kyc=None
    if u["role"] != "admin" and (not kyc or kyc["status"] != "VERIFIED" or not kyc["live_check"]):
        c.close(); raise HTTPException(403,"GRAM Verified KYC + live photo is required before placing orders")
    l=c.execute("select * from listings where id=? and status='OPEN'",(x.listing_id,)).fetchone()
    if not l:c.close();raise HTTPException(404,"Listing unavailable")
    qty=min(max(x.quantity_qtl,l["min_order_qtl"]),l["quantity_qtl"])
    produce=qty*l["ask_price"];transport=0
    if x.delivery_mode=="SELLER_TRANSPORT":
        if not l["seller_transport"]:c.close();raise HTTPException(400,"Seller transport not available")
        if x.buyer_lat is not None and x.buyer_lon is not None:
            m=c.execute("select lat,lon from markets where state=? order by id limit 1",(l["state"],)).fetchone()
            if m:
                km=111*math.sqrt((x.buyer_lat-m["lat"])**2+((x.buyer_lon-m["lon"])*math.cos(math.radians(x.buyer_lat)))**2)
                if l["delivery_radius_km"] and km>l["delivery_radius_km"]:
                    c.close();raise HTTPException(400,"Outside seller delivery radius")
                transport=km*l["transport_cost_per_km"]
    fee=produce*.005;total=produce+transport+fee
    cur=c.execute("""insert into orders(buyer_id,listing_id,quantity_qtl,produce_total,transport_total,platform_fee,total,delivery_mode,status,created_at)
                     values(?,?,?,?,?,?,?,?, 'PLACED',datetime('now'))""",
                  (u["id"],l["id"],qty,produce,transport,fee,total,x.delivery_mode))
    c.commit();c.close();audit(u["id"],"order",str(cur.lastrowid))
    return {"order_id":cur.lastrowid,"produce_total":round(produce,2),"transport_total":round(transport,2),
            "platform_fee":round(fee,2),"total":round(total,2),"status":"PLACED"}

@app.get("/api/orders")
def orders(u=Depends(user)):
    c=db()
    rows=c.execute("""select o.*,l.crop,l.state,l.district from orders o join listings l on l.id=o.listing_id
                      where o.buyer_id=? or l.seller_id=? order by o.created_at desc""",(u["id"],u["id"])).fetchall()
    c.close();return [dict(r) for r in rows]

@app.post("/api/negotiate")
def negotiate(x:NegotiationIn,u=Depends(user)):
    c=db();cur=c.execute("""insert into negotiations(user_id,listing_id,offer_price,message,status,created_at)
                            values(?,?,?,?, 'OPEN',datetime('now'))""",(u["id"],x.listing_id,x.offer_price,x.message))
    c.commit();c.close();audit(u["id"],"negotiate",str(cur.lastrowid))
    return {"negotiation_id":cur.lastrowid,"status":"OPEN"}

@app.get("/api/revenue")
def revenue(u=Depends(user)):
    c=db()
    total=c.execute("""select coalesce(sum(o.total),0) s from orders o join listings l on l.id=o.listing_id
                       where o.buyer_id=? or l.seller_id=?""",(u["id"],u["id"])).fetchone()["s"]
    c.close()
    months=["Apr","May","Jun","Jul","Aug","Sep"]
    return {"total":round(total,2),"monthly":[{"month":m,"revenue":round(total*(.08+i*.025),2)} for i,m in enumerate(months)]}

@app.get("/api/notifications")
def notifications(u=Depends(user)):
    c=db();rows=c.execute("select * from notifications where user_id is null or user_id=? order by created_at desc limit 20",(u["id"],)).fetchall();c.close();return [dict(r) for r in rows]

@app.get("/api/ml/forecast")
def ml_forecast(crop:str="Tomato",market_id:int=1,u=Depends(user)):
    try:return forecast_market(crop,market_id)
    except Exception as e:raise HTTPException(400,f"ML forecast failed: {e}")

@app.get("/api/ml/compare")
def ml_compare(crop:str="Tomato",quantity_qtl:float=10,lat:float=11.0168,lon:float=76.9558,horizon:int=7,u=Depends(user)):
    if horizon not in (1,3,7):raise HTTPException(400,"Horizon must be 1, 3 or 7")
    try:return compare_markets(crop,quantity_qtl,lat,lon,horizon)
    except Exception as e:raise HTTPException(400,f"Market comparison failed: {e}")

@app.get("/api/mission")
def mission(u=Depends(roles("admin"))):
    c=db()
    users={r["role"]:r["n"] for r in c.execute("select role,count(*) n from users group by role").fetchall()}
    logs=[dict(r) for r in c.execute("""select a.*,u.email from audit_logs a left join users u on u.id=a.user_id order by a.id desc limit 30""").fetchall()]
    orders=c.execute("select count(*) n,coalesce(sum(total),0) value from orders").fetchone()
    c.close()
    return {"users":users,"orders":dict(orders),"audit_logs":logs,
            "system":{"api":"healthy","database":"healthy","ml":"XGBoost + LightGBM enabled","security":"JWT + bcrypt + RBAC + rate limit"}}


# SIH 2026 innovation layer: non-destructive extensions to the existing application.
from innovation_api import router as innovation_router
app.include_router(innovation_router)


# Multilingual interface: free, key-less machine translation with a SQLite cache.
from i18n_service import router as i18n_router, init_i18n_schema
init_i18n_schema()
app.include_router(i18n_router)

# GRAM Saathi: Groq-backed assistant with read-only, role-scoped access to platform data.
from chatbot_api import router as chatbot_router, init_chatbot_schema
init_chatbot_schema()
app.include_router(chatbot_router)

# GRAM Saathi voice: Groq Whisper speech-to-text, gTTS speech-out, and the
# hands-free voice agent (intent, price hints).
from voice_api import router as voice_router
app.include_router(voice_router)

# India-wide crop market price comparison, backed by live AGMARKNET data
# (data.gov.in) - not the locally seeded demo prices used elsewhere.
from market_price_api import router as market_price_router
app.include_router(market_price_router)

# KISANSETU WhatsApp bridge: Meta Cloud API webhook -> YOLO -> certificate -> inventory.
from whatsapp_api import router as whatsapp_router, init_whatsapp_schema
init_whatsapp_schema()
app.include_router(whatsapp_router)

# Real Tamil Nadu Regulated Markets + Uzhavar Santhai (data/tn_markets.csv).
from market_infra import init_market_infra
init_market_infra()
