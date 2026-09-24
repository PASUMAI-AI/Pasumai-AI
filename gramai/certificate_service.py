import io
import os
import sqlite3
from datetime import datetime, timedelta, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage
)


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

CERTIFICATE_DIR = os.path.join(
    BASE_DIR,
    "certificates"
)

UPLOAD_DIR = os.path.join(
    BASE_DIR,
    "uploads"
)

os.makedirs(
    CERTIFICATE_DIR,
    exist_ok=True
)

IST = timezone(timedelta(hours=5, minutes=30))

# How long a quality grade stays trustworthy after the photo was scanned.
# Based on typical post-harvest shelf life under ordinary farm storage:
# perishables lose grade within days, dry grains and fibre keep for months.
VALIDITY_DAYS = {
    "tomato": 5,
    "banana": 5,
    "mango": 5,
    "grapes": 4,
    "chilli": 7,
    "cauliflower": 4,
    "cabbage": 7,
    "brinjal": 5,
    "okra": 3,
    "potato": 30,
    "onion": 30,
    "garlic": 60,
    "maize": 90,
    "groundnut": 120,
    "soybean": 180,
    "wheat": 180,
    "rice": 180,
    "cotton": 180,
    "turmeric": 180,
}
DEFAULT_VALIDITY_DAYS = 15

# A certificate is flagged "expiring soon" inside this many days.
EXPIRING_SOON_DAYS = 2


def validity_days(crop):
    return VALIDITY_DAYS.get(
        str(crop or "").strip().lower(),
        DEFAULT_VALIDITY_DAYS
    )


def parse_db_time(value):
    """SQLite datetime('now') strings are UTC without a zone marker."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).replace("T", " ").replace("Z", "")[:19]
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def db_time(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def validity_window(crop, scanned_at):
    """Return (scanned_at, valid_until, days) as UTC datetimes."""
    scanned = parse_db_time(scanned_at) or datetime.now(timezone.utc)
    days = validity_days(crop)
    return scanned, scanned + timedelta(days=days), days


def validity_status(valid_until, now=None):
    """VALID / EXPIRING / EXPIRED plus whole days left (never negative)."""
    until = parse_db_time(valid_until)
    if not until:
        return {"status": "UNKNOWN", "days_left": None}
    now = now or datetime.now(timezone.utc)
    seconds = (until - now).total_seconds()
    if seconds <= 0:
        return {"status": "EXPIRED", "days_left": 0}
    days_left = int(seconds // 86400)
    status = "EXPIRING" if days_left < EXPIRING_SOON_DAYS else "VALID"
    return {"status": status, "days_left": days_left}


def resolve_upload(path):
    """Stored image paths are absolute and may come from another machine.
    Fall back to finding the same file name anywhere under uploads/."""
    if not path:
        return None
    if os.path.exists(path):
        return path
    name = os.path.basename(str(path).replace("\\", "/"))
    for root, _dirs, files in os.walk(UPLOAD_DIR):
        if name in files:
            return os.path.join(root, name)
    return None


def ensure_validity_columns(db_path):
    """Add scanned_at / valid_until to quality_certificates and backfill
    rows issued before validity existed. Safe to run on every start."""
    c = sqlite3.connect(db_path)
    try:
        cols = {r[1] for r in c.execute("PRAGMA table_info(quality_certificates)")}
        if not cols:
            return
        if "scanned_at" not in cols:
            c.execute("ALTER TABLE quality_certificates ADD COLUMN scanned_at TEXT")
        if "valid_until" not in cols:
            c.execute("ALTER TABLE quality_certificates ADD COLUMN valid_until TEXT")
        rows = c.execute(
            """
            SELECT q.id, q.crop, COALESCE(v.created_at, q.issued_at)
            FROM quality_certificates q
            LEFT JOIN quality_verifications v ON v.id = q.verification_id
            WHERE q.valid_until IS NULL OR q.scanned_at IS NULL
            """
        ).fetchall()
        for cert_id, crop, scanned in rows:
            start, until, _days = validity_window(crop, scanned)
            c.execute(
                "UPDATE quality_certificates SET scanned_at=?, valid_until=? WHERE id=?",
                (db_time(start), db_time(until), cert_id)
            )
        c.commit()
    finally:
        c.close()


def apply_validity(conn, verification_id):
    """Stamp scan time and expiry on a freshly inserted certificate row,
    using the verification's own timestamp so PDF and database agree."""
    row = conn.execute(
        "SELECT crop, created_at FROM quality_verifications WHERE id=?",
        (verification_id,)
    ).fetchone()
    if not row:
        return None
    start, until, _days = validity_window(row[0], row[1])
    conn.execute(
        "UPDATE quality_certificates SET scanned_at=?, valid_until=? WHERE verification_id=?",
        (db_time(start), db_time(until), verification_id)
    )
    return db_time(until)


def _photo_flowable(image_path, max_w=80 * mm, max_h=65 * mm):
    path = resolve_upload(image_path)
    if not path:
        return None
    try:
        from PIL import Image as PILImage
        with PILImage.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((1200, 1200))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=85)
        buf.seek(0)
        w, h = ImageReader(buf).getSize()
        buf.seek(0)
        scale = min(max_w / w, max_h / h)
        return RLImage(buf, width=w * scale, height=h * scale)
    except Exception:
        return None


def _ist(dt):
    return dt.astimezone(IST).strftime("%d %b %Y, %I:%M %p IST")


def generate_quality_certificate(
    certificate_number,
    farmer_name,
    crop,
    grade,
    confidence,
    latitude,
    longitude,
    location_source,
    image_hash,
    model_name,
    image_path=None,
    scanned_at=None,
    place="",
    verify_url="",
    farmer_class="",
    geo_photos=0
):

    filename = (
        f"{certificate_number}.pdf"
    )

    path = os.path.join(
        CERTIFICATE_DIR,
        filename
    )

    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm
    )

    styles = getSampleStyleSheet()

    story = []

    logo_path = os.path.join(BASE_DIR, "static", "brand", "logo-256.png")
    if os.path.exists(logo_path):
        head = Table(
            [[RLImage(logo_path, width=22 * mm, height=22 * mm), Paragraph("PasumAI", styles["Title"])]],
            colWidths=[26 * mm, 140 * mm]
        )
        head.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, 0), "LEFT"),
        ]))
        story.append(head)
    else:
        story.append(
            Paragraph(
                "PasumAI",
                styles["Title"]
            )
        )

    story.append(
        Paragraph(
            "Produce Quality & Geolocation Certificate",
            styles["Heading2"]
        )
    )

    story.append(
        Spacer(
            1,
            6 * mm
        )
    )

    scanned, valid_until, days = validity_window(crop, scanned_at)
    state = validity_status(valid_until)
    status_text = {
        "VALID": f"VALID - {state['days_left']} day(s) left",
        "EXPIRING": f"VALID - expires soon ({state['days_left']} day(s) left)",
        "EXPIRED": "EXPIRED - re-inspect the produce before sale",
    }.get(state["status"], "UNKNOWN")
    status_color = {
        "VALID": "#1F6B45",
        "EXPIRING": "#A65F14",
        "EXPIRED": "#B83232",
    }.get(state["status"], "#555555")

    photo = _photo_flowable(image_path)
    if photo:
        story.append(photo)
        story.append(
            Paragraph(
                "<para alignment='center'><font size=8 color='#666666'>Produce photo scanned for this certificate</font></para>",
                styles["BodyText"]
            )
        )
        story.append(
            Spacer(
                1,
                5 * mm
            )
        )

    issued_at = datetime.now(
        timezone.utc
    )

    data = [
        ["Certificate Number", certificate_number],
        ["Farmer", farmer_name],
        ["Crop", crop],
        ["Automatic Grade", f"Grade {grade}"],
        ["YOLO Confidence", f"{confidence * 100:.2f}%"],
        ["Photo Scanned On", _ist(scanned)],
        ["Valid Until", _ist(valid_until)],
        ["Validity Period", f"{days} day(s) for {crop}"],
        ["Status", Paragraph(f"<b><font color='{status_color}'>{status_text}</font></b>", styles["BodyText"])],
        ["Location", Paragraph(
            f"<b>{place or 'Location recorded'}</b><br/><font size=7 color='#666666'>"
            f"GPS {latitude:.5f}, {longitude:.5f} ({str(location_source or '').upper()})</font>",
            styles["BodyText"])],
        *([["Grower Class", farmer_class]] if farmer_class else []),
        ["Geo-tagged Photos", f"{geo_photos} verified"],
        ["YOLO Model", model_name],
        ["PDF Generated At", _ist(issued_at)],
        ["Image SHA-256", Paragraph(f"<font size=7>{image_hash}</font>", styles["BodyText"])]
    ]

    table = Table(
        data,
        colWidths=[
            55 * mm,
            110 * mm
        ]
    )

    table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.HexColor("#EAF4ED")
            ),
            (
                "FONTNAME",
                (0, 0),
                (0, -1),
                "Helvetica-Bold"
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),
            (
                "PADDING",
                (0, 0),
                (-1, -1),
                7
            )
        ])
    )

    story.append(
        table
    )

    if verify_url:
        qr_size = 34 * mm
        widget = QrCodeWidget(verify_url)
        x1, y1, x2, y2 = widget.getBounds()
        drawing = Drawing(qr_size, qr_size, transform=[qr_size / (x2 - x1), 0, 0, qr_size / (y2 - y1), 0, 0])
        drawing.add(widget)
        qr_row = Table(
            [[Paragraph(
                "<b>Scan to verify this certificate</b><br/>"
                "The code opens a live page showing the crop, grade, place, validity, "
                "grower class and geo-tagged photos, so a buyer can check it is genuine "
                f"and not expired.<br/><font size=7 color='#666666'>{verify_url}</font>",
                styles["BodyText"]), drawing]],
            colWidths=[125 * mm, 40 * mm]
        )
        qr_row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F6FFC2")),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(Spacer(1, 5 * mm))
        story.append(qr_row)

    story.append(
        Spacer(
            1,
            6 * mm
        )
    )

    story.append(
        Paragraph(
            "This certificate records the automatic PasumAI "
            "quality classification and the location linked "
            "to the produce image during inspection. "
            f"The grade is valid for {days} day(s) from the scan date, "
            "the typical time this crop keeps its quality. "
            "After that the produce must be photographed and graded again.",
            styles["BodyText"]
        )
    )

    doc.build(
        story
    )

    return path


def _basename(path):
    return os.path.basename(str(path or "").replace("\\", "/"))


def certificate_details(conn, verification_id):
    """Everything a buyer needs to judge a certificate, or None."""
    row = conn.execute(
        """
        SELECT v.id verification_id, v.crop, v.predicted_grade grade, v.confidence,
               v.image_path, v.latitude, v.longitude, v.location_source, v.model_name,
               v.created_at, v.certificate_path, u.name farmer_name, u.district, u.state,
               q.certificate_number, q.issued_at, q.scanned_at, q.valid_until
        FROM quality_verifications v
        LEFT JOIN users u ON u.id = v.user_id
        LEFT JOIN quality_certificates q ON q.verification_id = v.id
        WHERE v.id = ?
        """,
        (verification_id,)
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    scanned, until, days = validity_window(d["crop"], d["scanned_at"] or d["created_at"])
    if d.get("valid_until"):
        until = parse_db_time(d["valid_until"]) or until
    state = validity_status(until)
    vid = d["verification_id"]
    return {
        "verification_id": vid,
        "certificate_number": d["certificate_number"] or f"GRAMAI-QC-{vid:06d}",
        "farmer_name": d["farmer_name"],
        "district": d["district"],
        "state": d["state"],
        "crop": d["crop"],
        "grade": d["grade"],
        "confidence": d["confidence"],
        "location_source": d["location_source"],
        "latitude": d["latitude"],
        "longitude": d["longitude"],
        "model_name": d["model_name"],
        "scanned_at": db_time(scanned),
        "valid_until": db_time(until),
        "validity_days": days,
        "status": state["status"],
        "days_left": state["days_left"],
        "has_photo": bool(resolve_upload(d["image_path"])),
        "photo_url": f"/api/produce/certificate/{vid}/photo",
        "pdf_url": f"/api/produce/certificate/{vid}",
        "details_url": f"/api/produce/certificate/{vid}/details",
    }


def verification_id_for_listing(conn, listing):
    """Listings store the certificate PDF and photo paths, not the id.
    Paths may come from another machine, so match on file names."""
    listing = dict(listing)
    cert = _basename(listing.get("quality_certificate"))
    if cert:
        row = conn.execute(
            "SELECT verification_id FROM quality_certificates WHERE certificate_number=?",
            (cert.rsplit(".", 1)[0],)
        ).fetchone()
        if row and row[0]:
            return row[0]
    image = _basename(listing.get("quality_image") or listing.get("image_url"))
    if image:
        row = conn.execute(
            "SELECT id FROM quality_verifications WHERE image_path LIKE ? ORDER BY id DESC LIMIT 1",
            ("%" + image,)
        ).fetchone()
        if row:
            return row[0]
    return None


def attach_certificate(conn, item, verification_id):
    """Add a compact certificate summary to a listing/harvest dict."""
    info = certificate_details(conn, verification_id) if verification_id else None
    item["certificate"] = info
    if info:
        item["certificate_url"] = info["pdf_url"]
    return item
